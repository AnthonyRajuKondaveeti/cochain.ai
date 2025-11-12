# services/reward_calculator.py
"""
Reward Calculator for Reinforcement Learning
Converts user interactions into reward signals for training
"""
from database.connection import supabase
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from .logging_service import get_logger

logger = get_logger('reward_calculator')


class RewardCalculator:
    """
    Calculate rewards from user interactions to train RL model
    
    Reward Philosophy:
    - Positive rewards for desired behaviors (clicks, bookmarks, feedback)
    - Negative rewards for undesired behaviors (quick exits, low ratings)
    - Time-weighted rewards (recent actions matter more)
    - Position-adjusted rewards (clicks on lower positions = higher reward)
    """
    
    def __init__(self):
        self.logger = logger
        
        # Base reward values (tunable based on business goals)
        self.base_rewards = {
            'impression': 0.0,           # Just showing = no reward yet
            'hover_short': 0.3,          # Hovered 1-3 seconds
            'hover_long': 0.8,           # Hovered > 3 seconds
            'click': 5.0,                # Clicked to view details
            'bookmark': 10.0,            # Bookmarked project
            'unbookmark': -3.0,          # Removed bookmark (negative signal)
            'feedback_1': -5.0,          # 1-star rating (very bad)
            'feedback_2': -2.0,          # 2-star rating (bad)
            'feedback_3': 0.0,           # 3-star rating (neutral)
            'feedback_4': 5.0,           # 4-star rating (good)
            'feedback_5': 10.0,          # 5-star rating (excellent)
            'github_visit': 3.0,         # Visited GitHub repo
            'quick_exit': -2.0,          # Clicked but left < 10 seconds
            'return_visit': 5.0          # Came back to bookmarked project
        }
        
        # Position discount factor (reduce position bias)
        # Higher position = lower reward multiplier
        self.position_discount = {
            1: 0.8,   # Position 1 gets 80% of reward
            2: 0.85,
            3: 0.9,
            4: 0.95,
            5: 1.0,   # Position 5+ gets full reward
        }
        
        # Time decay factor (recent interactions matter more)
        self.time_decay_days = 30  # Full reward within 30 days
    
    def calculate_interaction_reward(
        self, 
        interaction_type: str,
        rank_position: Optional[int] = None,
        duration_seconds: Optional[int] = None,
        rating: Optional[int] = None,
        timestamp: Optional[datetime] = None
    ) -> float:
        """
        Calculate reward for a single interaction
        
        Args:
            interaction_type: Type of interaction ('click', 'bookmark', etc.)
            rank_position: Position in recommendation list (1-indexed)
            duration_seconds: Time spent on interaction
            rating: Feedback rating (1-5)
            timestamp: When interaction occurred
        
        Returns:
            Calculated reward value
        """
        try:
            # Get base reward
            if interaction_type == 'feedback' and rating:
                base_reward = self.base_rewards.get(f'feedback_{rating}', 0.0)
            else:
                base_reward = self.base_rewards.get(interaction_type, 0.0)
            
            # Apply position discount (encourage clicks on lower positions)
            position_multiplier = 1.0
            if rank_position and rank_position <= 5:
                # Lower positions get higher rewards (less position bias)
                position_multiplier = self.position_discount.get(rank_position, 1.0)
            elif rank_position and rank_position > 5:
                # Reward clicks on positions 6+ more (user explored)
                position_multiplier = 1.1
            
            # Apply duration bonus for clicks
            duration_multiplier = 1.0
            if interaction_type == 'click' and duration_seconds:
                if duration_seconds < 10:
                    # Quick exit - apply penalty
                    base_reward = self.base_rewards['quick_exit']
                elif duration_seconds > 60:
                    # Long engagement - bonus reward
                    duration_multiplier = 1.5
                elif duration_seconds > 30:
                    duration_multiplier = 1.2
            
            # Apply time decay
            time_multiplier = 1.0
            if timestamp:
                days_ago = (datetime.now() - timestamp).days
                if days_ago > self.time_decay_days:
                    time_multiplier = 0.5  # Older interactions worth less
                elif days_ago > self.time_decay_days / 2:
                    time_multiplier = 0.75
            
            # Calculate final reward
            final_reward = base_reward * position_multiplier * duration_multiplier * time_multiplier
            
            return round(final_reward, 2)
            
        except Exception as e:
            self.logger.error(f"Error calculating reward: {str(e)}")
            return 0.0
    
    def calculate_user_rewards(
        self, 
        user_id: str, 
        days: int = 30
    ) -> Dict[str, float]:
        """
        Calculate total rewards for a user's interactions
        
        Returns:
            Dict with rewards by project ID
        """
        try:
            since_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            # Get all user interactions
            interactions_result = supabase.table('user_interactions')\
                .select('*')\
                .eq('user_id', user_id)\
                .gte('interaction_time', since_date)\
                .execute()
            
            if not interactions_result.data:
                return {}
            
            # Calculate rewards per project
            project_rewards = {}
            
            for interaction in interactions_result.data:
                project_id = interaction['github_reference_id']
                interaction_type = interaction['interaction_type']
                rank_position = interaction.get('rank_position')
                duration = interaction.get('duration_seconds')
                
                # Parse timestamp
                timestamp = None
                if interaction.get('interaction_time'):
                    timestamp = datetime.fromisoformat(
                        interaction['interaction_time'].replace('Z', '+00:00')
                    )
                
                # Calculate reward
                reward = self.calculate_interaction_reward(
                    interaction_type=interaction_type,
                    rank_position=rank_position,
                    duration_seconds=duration,
                    timestamp=timestamp
                )
                
                # Accumulate rewards per project
                if project_id not in project_rewards:
                    project_rewards[project_id] = 0.0
                project_rewards[project_id] += reward
            
            # Get feedback rewards
            feedback_result = supabase.table('user_feedback')\
                .select('*')\
                .eq('user_id', user_id)\
                .gte('created_at', since_date)\
                .execute()
            
            for feedback in feedback_result.data or []:
                project_id = feedback['github_reference_id']
                rating = feedback.get('rating')
                
                if rating:
                    reward = self.calculate_interaction_reward(
                        interaction_type='feedback',
                        rating=rating
                    )
                    
                    if project_id not in project_rewards:
                        project_rewards[project_id] = 0.0
                    project_rewards[project_id] += reward
            
            self.logger.info(f"Calculated rewards for user {user_id}: {len(project_rewards)} projects")
            
            return project_rewards
            
        except Exception as e:
            self.logger.error(f"Error calculating user rewards: {str(e)}")
            return {}
    
    def calculate_project_rewards(
        self, 
        project_id: str, 
        days: int = 30
    ) -> Dict[str, any]:
        """
        Calculate aggregate rewards for a project across all users
        
        Returns:
            Dict with total reward, interaction counts, average reward
        """
        try:
            since_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            # Get all interactions for this project
            interactions_result = supabase.table('user_interactions')\
                .select('*')\
                .eq('github_reference_id', project_id)\
                .gte('interaction_time', since_date)\
                .execute()
            
            total_reward = 0.0
            interaction_counts = {}
            
            for interaction in interactions_result.data or []:
                interaction_type = interaction['interaction_type']
                rank_position = interaction.get('rank_position')
                duration = interaction.get('duration_seconds')
                
                timestamp = None
                if interaction.get('interaction_time'):
                    timestamp = datetime.fromisoformat(
                        interaction['interaction_time'].replace('Z', '+00:00')
                    )
                
                reward = self.calculate_interaction_reward(
                    interaction_type=interaction_type,
                    rank_position=rank_position,
                    duration_seconds=duration,
                    timestamp=timestamp
                )
                
                total_reward += reward
                interaction_counts[interaction_type] = interaction_counts.get(interaction_type, 0) + 1
            
            # Get feedback
            feedback_result = supabase.table('user_feedback')\
                .select('*')\
                .eq('github_reference_id', project_id)\
                .gte('created_at', since_date)\
                .execute()
            
            for feedback in feedback_result.data or []:
                rating = feedback.get('rating')
                if rating:
                    reward = self.calculate_interaction_reward(
                        interaction_type='feedback',
                        rating=rating
                    )
                    total_reward += reward
                    interaction_counts['feedback'] = interaction_counts.get('feedback', 0) + 1
            
            total_interactions = sum(interaction_counts.values())
            avg_reward = total_reward / total_interactions if total_interactions > 0 else 0.0
            
            return {
                'project_id': project_id,
                'total_reward': round(total_reward, 2),
                'average_reward': round(avg_reward, 2),
                'total_interactions': total_interactions,
                'interaction_counts': interaction_counts,
                'days': days
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating project rewards: {str(e)}")
            return {}
    
    def get_training_data(
        self, 
        days: int = 30,
        min_interactions: int = 1
    ) -> List[Dict]:
        """
        Get reward data for ML training
        
        Returns:
            List of training examples with features and rewards
        """
        try:
            since_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            # Get all recommendation results with interactions
            results = supabase.table('recommendation_results')\
                .select('''
                    *,
                    user_queries(project_idea, complexity_level, existing_skills, want_to_learn),
                    github_references(title, domain, complexity_level, required_skills, technologies)
                ''')\
                .gte('created_at', since_date)\
                .execute()
            
            if not results.data:
                return []
            
            training_data = []
            
            for result in results.data:
                user_query_id = result.get('user_query_id')
                project_id = result['github_reference_id']
                rank_position = result.get('rank_position')
                similarity_score = result.get('similarity_score')
                
                # Get interactions for this recommendation
                interactions = supabase.table('user_interactions')\
                    .select('*')\
                    .eq('github_reference_id', project_id)\
                    .execute()
                
                # Calculate reward
                total_reward = 0.0
                for interaction in interactions.data or []:
                    reward = self.calculate_interaction_reward(
                        interaction_type=interaction['interaction_type'],
                        rank_position=rank_position,
                        duration_seconds=interaction.get('duration_seconds')
                    )
                    total_reward += reward
                
                # Add feedback rewards
                feedback = supabase.table('user_feedback')\
                    .eq('github_reference_id', project_id)\
                    .execute()
                
                for fb in feedback.data or []:
                    if fb.get('rating'):
                        reward = self.calculate_interaction_reward(
                            interaction_type='feedback',
                            rating=fb['rating']
                        )
                        total_reward += reward
                
                # Only include if has minimum interactions
                total_interactions = len(interactions.data or []) + len(feedback.data or [])
                if total_interactions >= min_interactions:
                    training_example = {
                        'user_query_id': user_query_id,
                        'project_id': project_id,
                        'rank_position': rank_position,
                        'similarity_score': similarity_score,
                        'reward': round(total_reward, 2),
                        'interactions': total_interactions,
                        'user_context': result.get('user_queries', {}),
                        'project_features': result.get('github_references', {})
                    }
                    training_data.append(training_example)
            
            self.logger.info(f"Generated {len(training_data)} training examples from {days} days")
            
            return training_data
            
        except Exception as e:
            self.logger.error(f"Error getting training data: {str(e)}")
            return []
    
    def adjust_reward_weights(self, weight_adjustments: Dict[str, float]):
        """
        Adjust reward weights based on business needs
        
        Example:
            calculator.adjust_reward_weights({
                'click': 8.0,        # Increase click reward
                'bookmark': 15.0,    # Increase bookmark reward
                'quick_exit': -5.0   # Increase penalty for quick exits
            })
        """
        for action, new_weight in weight_adjustments.items():
            if action in self.base_rewards:
                old_weight = self.base_rewards[action]
                self.base_rewards[action] = new_weight
                self.logger.info(f"Adjusted reward for '{action}': {old_weight} → {new_weight}")
            else:
                self.logger.warning(f"Unknown action type: {action}")


# Global reward calculator instance
_reward_calculator = None

def get_reward_calculator():
    """Get or create the global reward calculator instance"""
    global _reward_calculator
    if _reward_calculator is None:
        _reward_calculator = RewardCalculator()
    return _reward_calculator


# Testing
if __name__ == '__main__':
    calculator = get_reward_calculator()
    
    print("Testing Reward Calculator...")
    
    # Test different interactions
    test_cases = [
        ('click', 1, 45, None, "Click at position 1, 45 seconds"),
        ('click', 5, 120, None, "Click at position 5, 2 minutes"),
        ('click', 1, 5, None, "Click at position 1, quick exit"),
        ('bookmark', None, None, None, "Bookmark"),
        ('feedback', None, None, 5, "5-star feedback"),
        ('feedback', None, None, 1, "1-star feedback"),
    ]
    
    print("\nReward Calculations:")
    for interaction_type, position, duration, rating, description in test_cases:
        reward = calculator.calculate_interaction_reward(
            interaction_type=interaction_type,
            rank_position=position,
            duration_seconds=duration,
            rating=rating
        )
        print(f"  {description}: {reward:.2f}")
    
    print("\n✅ Reward calculator test complete!")