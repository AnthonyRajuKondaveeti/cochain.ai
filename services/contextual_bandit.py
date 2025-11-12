# services/contextual_bandit.py
"""
Contextual Bandit Algorithm for Recommendation
Uses Thompson Sampling for exploration/exploitation balance
"""
from database.connection import supabase_admin as supabase  # Use admin client for background jobs
from typing import List, Dict, Tuple, Optional
import numpy as np
from collections import defaultdict
from datetime import datetime, timedelta
from .logging_service import get_logger
from .reward_calculator import get_reward_calculator

logger = get_logger('contextual_bandit')


class ContextualBandit:
    """
    Thompson Sampling Contextual Bandit for Recommendations
    
    How it works:
    1. Maintain Beta distribution for each (user_context, project) pair
    2. Sample from distributions to select projects
    3. Update distributions based on rewards
    4. Balance exploration (try new things) vs exploitation (show known good items)
    
    Beta Distribution Parameters:
    - α (alpha): Success count + prior
    - β (beta): Failure count + prior
    - Higher α/β ratio = better performance
    """
    
    def __init__(self, alpha_prior: float = 1.0, beta_prior: float = 1.0):
        """
        Initialize contextual bandit
        
        Args:
            alpha_prior: Prior successes (higher = more optimistic)
            beta_prior: Prior failures (higher = more conservative)
        """
        self.alpha_prior = alpha_prior
        self.beta_prior = beta_prior
        self.logger = logger
        self.reward_calculator = get_reward_calculator()
        
        # In-memory cache for model parameters
        self.project_params = {}  # {project_id: {'alpha': float, 'beta': float}}
        self.last_update = None
    
    def get_project_parameters(self, project_id: str) -> Tuple[float, float]:
        """
        Get Beta distribution parameters for a project
        
        Returns:
            (alpha, beta) tuple
        """
        try:
            # Check cache first
            if project_id in self.project_params:
                return self.project_params[project_id]['alpha'], self.project_params[project_id]['beta']
            
            # Query from database (stored in project_rl_stats table)
            result = supabase.table('project_rl_stats')\
                .select('*')\
                .eq('project_id', project_id)\
                .execute()
            
            if result.data and len(result.data) > 0:
                stats = result.data[0]
                alpha = stats.get('alpha', self.alpha_prior)
                beta = stats.get('beta', self.beta_prior)
            else:
                # No data yet, use priors
                alpha = self.alpha_prior
                beta = self.beta_prior
            
            # Cache it
            self.project_params[project_id] = {'alpha': alpha, 'beta': beta}
            
            return alpha, beta
            
        except Exception as e:
            self.logger.error(f"Error getting project parameters: {str(e)}")
            return self.alpha_prior, self.beta_prior
    
    def sample_project_score(self, project_id: str, similarity_score: float) -> float:
        """
        Sample a score for a project using Thompson Sampling
        
        Combines:
        - Similarity score (exploitation - known relevance)
        - Thompson sample (exploration - learning potential)
        
        Args:
            project_id: Project ID
            similarity_score: Base similarity from embedding
        
        Returns:
            Combined score for ranking
        """
        try:
            # Get Beta distribution parameters
            alpha, beta = self.get_project_parameters(project_id)
            
            # Sample from Beta distribution
            # This gives us the estimated "quality" with uncertainty
            thompson_sample = np.random.beta(alpha, beta)
            
            # Combine similarity (exploitation) with Thompson sample (exploration)
            # Weight: 70% similarity, 30% Thompson sample
            # This balances showing relevant items with exploring new ones
            combined_score = 0.7 * similarity_score + 0.3 * thompson_sample
            
            return float(combined_score)
            
        except Exception as e:
            self.logger.error(f"Error sampling project score: {str(e)}")
            return similarity_score  # Fallback to pure similarity
    
    def rank_projects_with_bandit(
        self, 
        projects: List[Dict], 
        user_id: str,
        exploration_rate: float = 0.15
    ) -> List[Dict]:
        """
        Re-rank projects using Thompson Sampling
        
        Args:
            projects: List of projects with similarity scores
            user_id: User ID
            exploration_rate: Probability of pure exploration (0.0 - 1.0)
        
        Returns:
            Re-ranked list of projects
        """
        try:
            if not projects:
                return []
            
            # Add Thompson sample scores to each project
            for project in projects:
                project_id = project['id']
                similarity = project.get('similarity', 0.5)
                
                # Decide: exploit or explore?
                if np.random.random() < exploration_rate:
                    # Pure exploration: random Thompson sample
                    alpha, beta = self.get_project_parameters(project_id)
                    project['bandit_score'] = np.random.beta(alpha, beta)
                    project['strategy'] = 'explore'
                else:
                    # Exploitation with uncertainty: combine similarity + Thompson
                    project['bandit_score'] = self.sample_project_score(project_id, similarity)
                    project['strategy'] = 'exploit'
            
            # Sort by bandit score
            ranked_projects = sorted(projects, key=lambda x: x.get('bandit_score', 0), reverse=True)
            
            self.logger.info(f"Ranked {len(ranked_projects)} projects for user {user_id}")
            
            return ranked_projects
            
        except Exception as e:
            self.logger.error(f"Error ranking projects: {str(e)}")
            return projects  # Return original order on error
    
    def update_from_reward(
        self, 
        project_id: str, 
        reward: float,
        learning_rate: float = 1.0
    ):
        """
        Update project parameters based on observed reward
        
        Args:
            project_id: Project that was recommended
            reward: Observed reward (can be positive or negative)
            learning_rate: How much to update (0.0 - 1.0)
        """
        try:
            # Get current parameters
            alpha, beta = self.get_project_parameters(project_id)
            
            # Convert reward to success/failure update
            # Positive reward = success, negative = failure
            if reward > 0:
                # Success: increase alpha
                alpha_update = reward * learning_rate
                alpha += alpha_update
            elif reward < 0:
                # Failure: increase beta
                beta_update = abs(reward) * learning_rate
                beta += beta_update
            # reward == 0: no update
            
            # Update in database
            upsert_data = {
                'project_id': project_id,
                'alpha': alpha,
                'beta': beta,
                'total_samples': alpha + beta - self.alpha_prior - self.beta_prior,
                'estimated_quality': alpha / (alpha + beta),
                'updated_at': datetime.now().isoformat()
            }
            
            supabase.table('project_rl_stats').upsert(
                upsert_data,
                on_conflict='project_id'
            ).execute()
            
            # Update cache
            self.project_params[project_id] = {'alpha': alpha, 'beta': beta}
            
            self.logger.debug(f"Updated project {project_id}: α={alpha:.2f}, β={beta:.2f}, reward={reward:.2f}")
            
        except Exception as e:
            self.logger.error(f"Error updating from reward: {str(e)}")
    
    def batch_update_from_interactions(self, days: int = 1):
        """
        Batch update all project parameters from recent interactions
        Called daily by background job
        
        Args:
            days: Number of days of interactions to process
        """
        try:
            self.logger.info(f"Starting batch update from last {days} days")
            
            since_date = (datetime.now() - timedelta(days=days)).isoformat()
            self.logger.info(f"Looking for interactions since: {since_date}")
            
            # Get all interactions in the period
            interactions_result = supabase.table('user_interactions')\
                .select('*')\
                .gte('interaction_time', since_date)\
                .execute()
            
            self.logger.info(f"Found {len(interactions_result.data) if interactions_result.data else 0} interactions to process")
            
            if not interactions_result.data:
                self.logger.info("No interactions to process")
                return
            
            # Group by project and calculate rewards
            project_rewards = defaultdict(list)
            
            for interaction in interactions_result.data:
                project_id = interaction['github_reference_id']
                interaction_type = interaction['interaction_type']
                rank_position = interaction.get('rank_position')
                duration = interaction.get('duration_seconds')
                
                # Calculate reward
                reward = self.reward_calculator.calculate_interaction_reward(
                    interaction_type=interaction_type,
                    rank_position=rank_position,
                    duration_seconds=duration
                )
                
                project_rewards[project_id].append(reward)
            
            # Get feedback
            feedback_result = supabase.table('user_feedback')\
                .select('*')\
                .gte('created_at', since_date)\
                .execute()
            
            for feedback in feedback_result.data or []:
                project_id = feedback['github_reference_id']
                rating = feedback.get('rating')
                
                if rating:
                    reward = self.reward_calculator.calculate_interaction_reward(
                        interaction_type='feedback',
                        rating=rating
                    )
                    project_rewards[project_id].append(reward)
            
            # Update each project
            update_count = 0
            for project_id, rewards in project_rewards.items():
                total_reward = sum(rewards)
                avg_reward = total_reward / len(rewards)
                
                # Update with average reward (smoothed update)
                self.update_from_reward(project_id, avg_reward, learning_rate=0.5)
                update_count += 1
            
            self.logger.info(f"Batch update complete: updated {update_count} projects")
            
        except Exception as e:
            self.logger.error(f"Error in batch update: {str(e)}")
    
    def get_project_statistics(self, project_id: str) -> Dict:
        """
        Get statistics for a project's bandit performance
        
        Returns:
            Dict with alpha, beta, estimated quality, confidence interval
        """
        try:
            alpha, beta = self.get_project_parameters(project_id)
            
            # Calculate statistics
            total_samples = alpha + beta - self.alpha_prior - self.beta_prior
            estimated_quality = alpha / (alpha + beta)
            
            # 95% confidence interval (using normal approximation)
            variance = (alpha * beta) / ((alpha + beta) ** 2 * (alpha + beta + 1))
            std_dev = np.sqrt(variance)
            ci_lower = max(0, estimated_quality - 1.96 * std_dev)
            ci_upper = min(1, estimated_quality + 1.96 * std_dev)
            
            return {
                'project_id': project_id,
                'alpha': round(alpha, 2),
                'beta': round(beta, 2),
                'total_samples': int(total_samples),
                'estimated_quality': round(estimated_quality, 4),
                'confidence_interval': [round(ci_lower, 4), round(ci_upper, 4)],
                'uncertainty': round(std_dev, 4)
            }
            
        except Exception as e:
            self.logger.error(f"Error getting project statistics: {str(e)}")
            return {}
    
    def get_top_projects(self, limit: int = 10) -> List[Dict]:
        """
        Get top performing projects by estimated quality
        
        Returns:
            List of projects with their bandit statistics
        """
        try:
            # Get all project stats
            result = supabase.table('project_rl_stats')\
                .select('*')\
                .order('estimated_quality', desc=True)\
                .limit(limit)\
                .execute()
            
            if not result.data:
                return []
            
            # Enrich with project details
            top_projects = []
            for stats in result.data:
                project_id = stats['project_id']
                
                # Get project details
                project_result = supabase.table('github_references')\
                    .select('title, domain, complexity_level')\
                    .eq('id', project_id)\
                    .execute()
                
                if project_result.data:
                    project = project_result.data[0]
                    project.update({
                        'alpha': stats['alpha'],
                        'beta': stats['beta'],
                        'estimated_quality': stats['estimated_quality'],
                        'total_samples': stats['total_samples']
                    })
                    top_projects.append(project)
            
            return top_projects
            
        except Exception as e:
            self.logger.error(f"Error getting top projects: {str(e)}")
            return []
    
    def reset_project(self, project_id: str):
        """Reset a project's bandit parameters (for testing or resets)"""
        try:
            supabase.table('project_rl_stats').delete().eq('project_id', project_id).execute()
            
            if project_id in self.project_params:
                del self.project_params[project_id]
            
            self.logger.info(f"Reset project {project_id}")
            
        except Exception as e:
            self.logger.error(f"Error resetting project: {str(e)}")


# Global bandit instance
_bandit = None

def get_contextual_bandit():
    """Get or create the global bandit instance"""
    global _bandit
    if _bandit is None:
        _bandit = ContextualBandit(alpha_prior=2.0, beta_prior=2.0)
    return _bandit


# Testing
if __name__ == '__main__':
    bandit = get_contextual_bandit()
    
    print("Testing Contextual Bandit...")
    
    # Simulate project with different rewards
    test_project_id = 'test_project_123'
    
    print(f"\nInitial parameters for {test_project_id}:")
    stats = bandit.get_project_statistics(test_project_id)
    print(f"  α={stats['alpha']}, β={stats['beta']}")
    print(f"  Estimated Quality: {stats['estimated_quality']:.4f}")
    print(f"  Confidence Interval: {stats['confidence_interval']}")
    
    # Simulate positive interactions
    print("\nSimulating positive interactions:")
    for i in range(5):
        bandit.update_from_reward(test_project_id, reward=5.0)
    
    stats = bandit.get_project_statistics(test_project_id)
    print(f"  After positive rewards: α={stats['alpha']}, β={stats['beta']}")
    print(f"  Estimated Quality: {stats['estimated_quality']:.4f}")
    
    # Simulate negative interactions
    print("\nSimulating negative interactions:")
    for i in range(2):
        bandit.update_from_reward(test_project_id, reward=-2.0)
    
    stats = bandit.get_project_statistics(test_project_id)
    print(f"  After mixed rewards: α={stats['alpha']}, β={stats['beta']}")
    print(f"  Estimated Quality: {stats['estimated_quality']:.4f}")
    
    # Test Thompson sampling
    print("\nTesting Thompson Sampling (10 samples):")
    samples = []
    for i in range(10):
        score = bandit.sample_project_score(test_project_id, similarity_score=0.8)
        samples.append(score)
    
    print(f"  Samples: {[f'{s:.3f}' for s in samples]}")
    print(f"  Mean: {np.mean(samples):.3f}, Std: {np.std(samples):.3f}")
    
    print("\n✅ Contextual bandit test complete!")