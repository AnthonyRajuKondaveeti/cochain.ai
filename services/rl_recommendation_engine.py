# services/rl_recommendation_engine.py
"""
Reinforcement Learning Recommendation Engine
Combines embedding similarity with Thompson Sampling bandit
"""
from services.personalized_recommendations import PersonalizedRecommendationService
from services.contextual_bandit import get_contextual_bandit
from services.reward_calculator import get_reward_calculator
from services.logging_service import get_logger
from database.connection import supabase, supabase_admin
from typing import List, Dict, Optional
import numpy as np
from datetime import datetime

logger = get_logger('rl_recommendation')


class RLRecommendationEngine:
    """
    Intelligent recommendation engine combining:
    1. Embedding similarity (content-based filtering)
    2. Thompson Sampling (exploration/exploitation)
    3. Reward-based learning (continuous improvement)
    
    How it works:
    - Start with similarity-based recommendations (cold start)
    - Gradually incorporate bandit learning as data accumulates
    - Balance showing relevant items (exploitation) with trying new things (exploration)
    - Learn from user feedback to improve over time
    """
    
    def __init__(self, exploration_rate: float = 0.15):
        """
        Initialize RL recommendation engine
        
        Args:
            exploration_rate: Probability of pure exploration (default 15%)
        """
        # Base recommendation service (embedding similarity)
        self.base_recommender = PersonalizedRecommendationService()
        
        # Contextual bandit for learning
        self.bandit = get_contextual_bandit()
        
        # Reward calculator
        self.reward_calculator = get_reward_calculator()
        
        self.logger = logger
        self.exploration_rate = exploration_rate
        
        # Weights for combining similarity + bandit scores
        self.similarity_weight = 0.6  # 60% similarity
        self.bandit_weight = 0.4      # 40% learned quality
    
    def get_recommendations(
        self, 
        user_id: str, 
        num_recommendations: int = 10,
        use_rl: bool = True,
        offset: int = 0
    ) -> Dict:
        """
        Get personalized recommendations with RL and caching
        
        Args:
            user_id: User ID
            num_recommendations: Number of recommendations to return
            use_rl: Whether to use RL (False = pure similarity)
            offset: Pagination offset
        
        Returns:
            Dict with recommendations and metadata
        """
        try:
            start_time = datetime.now()
            
            # Step 0: Check if we have cached RL recommendations
            if use_rl:
                cached_rl_recs = self._get_cached_rl_recommendations(user_id)
                if cached_rl_recs:
                    # Use cached RL recommendations with pagination
                    total_count = len(cached_rl_recs)
                    end_index = min(offset + num_recommendations, total_count)
                    paginated_recommendations = cached_rl_recs[offset:end_index]
                    
                    duration_ms = (datetime.now() - start_time).total_seconds() * 1000
                    
                    self.logger.info(
                        f"Retrieved {len(paginated_recommendations)} cached RL recommendations for user {user_id} "
                        f"in {duration_ms:.2f}ms"
                    )
                    
                    return {
                        'success': True,
                        'recommendations': paginated_recommendations,
                        'total_count': total_count,
                        'method': 'rl_enhanced',
                        'cached': True,
                        'exploration_rate': self.exploration_rate,
                        'duration_ms': round(duration_ms, 2)
                    }
            
            # Step 1: Get base recommendations from similarity
            base_result = self.base_recommender.get_recommendations_for_user(
                user_id=user_id,
                num_recommendations=num_recommendations * 3,  # Get more to re-rank
                offset=0  # Always start from 0, we'll paginate after re-ranking
            )
            
            if not base_result.get('success'):
                self.logger.warning(f"Base recommendations failed for user {user_id}")
                return base_result
            
            base_recommendations = base_result.get('recommendations', [])
            
            if not base_recommendations:
                return {
                    'success': True,
                    'recommendations': [],
                    'method': 'no_results'
                }
            
            # Step 2: Apply RL re-ranking if enabled
            if use_rl:
                # Re-rank using Thompson Sampling
                rl_recommendations = self.bandit.rank_projects_with_bandit(
                    projects=base_recommendations,
                    user_id=user_id,
                    exploration_rate=self.exploration_rate
                )
                
                # Add RL metadata
                for rec in rl_recommendations:
                    rec['rl_score'] = rec.get('bandit_score', 0)
                    rec['recommendation_method'] = rec.get('strategy', 'unknown')
                
                final_recommendations = rl_recommendations
                method = 'rl_enhanced'
                
                self.logger.info(f"RL re-ranking applied for user {user_id}")
                
            else:
                # Use pure similarity ranking
                final_recommendations = base_recommendations
                method = 'similarity_only'
            
            # Step 3: Apply pagination
            total_count = len(final_recommendations)
            end_index = min(offset + num_recommendations, total_count)
            paginated_recommendations = final_recommendations[offset:end_index]
            
            # Step 3.5: Cache RL recommendations if using RL
            if use_rl and method == 'rl_enhanced':
                self._save_cached_rl_recommendations(user_id, final_recommendations)
            
            # Step 4: Track that we showed these recommendations
            self._track_recommendations_shown(
                user_id=user_id,
                recommendations=paginated_recommendations
            )
            
            duration_ms = (datetime.now() - start_time).total_seconds() * 1000
            
            self.logger.info(
                f"Generated {len(paginated_recommendations)} RL recommendations for user {user_id} "
                f"in {duration_ms:.2f}ms (method: {method})"
            )
            
            return {
                'success': True,
                'recommendations': paginated_recommendations,
                'total_count': total_count,
                'method': method,
                'cached': False,
                'exploration_rate': self.exploration_rate,
                'duration_ms': round(duration_ms, 2)
            }
            
        except Exception as e:
            self.logger.error(f"Error generating RL recommendations: {str(e)}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'recommendations': []
            }
    
    def _track_recommendations_shown(
        self, 
        user_id: str, 
        recommendations: List[Dict]
    ):
        """Track which recommendations were shown to user"""
        try:
            # Store in recommendation_results for analytics
            results_data = []
            for idx, rec in enumerate(recommendations, 1):
                result_data = {
                    'github_reference_id': rec['id'],
                    'rank_position': idx,
                    'similarity_score': rec.get('similarity', 0),
                    'rl_score': rec.get('rl_score', 0),
                    'recommendation_method': rec.get('recommendation_method', 'unknown')
                }
                results_data.append(result_data)
            
            # Batch insert
            if results_data:
                supabase.table('recommendation_results').insert(results_data).execute()
                
        except Exception as e:
            self.logger.error(f"Error tracking recommendations: {str(e)}")
    
    def record_interaction(
        self, 
        user_id: str, 
        project_id: str,
        interaction_type: str,
        rank_position: Optional[int] = None,
        duration_seconds: Optional[int] = None,
        rating: Optional[int] = None
    ):
        """
        Record user interaction and update RL model
        
        Args:
            user_id: User ID
            project_id: Project that was interacted with
            interaction_type: Type of interaction ('click', 'bookmark', etc.)
            rank_position: Position in recommendation list
            duration_seconds: Time spent (for clicks)
            rating: Feedback rating (1-5)
        """
        try:
            # Calculate reward
            reward = self.reward_calculator.calculate_interaction_reward(
                interaction_type=interaction_type,
                rank_position=rank_position,
                duration_seconds=duration_seconds,
                rating=rating
            )
            
            # Update bandit model
            self.bandit.update_from_reward(
                project_id=project_id,
                reward=reward,
                learning_rate=0.5  # Moderate learning rate
            )
            
            self.logger.info(
                f"Recorded {interaction_type} for project {project_id}: reward={reward:.2f}"
            )
            
        except Exception as e:
            self.logger.error(f"Error recording interaction: {str(e)}")
    
    def get_diverse_recommendations(
        self, 
        user_id: str, 
        num_recommendations: int = 10,
        diversity_factor: float = 0.3
    ) -> Dict:
        """
        Get recommendations with diversity (avoid showing similar items)
        
        Args:
            user_id: User ID
            num_recommendations: Number of recommendations
            diversity_factor: Weight for diversity (0.0 = no diversity, 1.0 = max diversity)
        
        Returns:
            Dict with diverse recommendations
        """
        try:
            # Get more recommendations than needed
            result = self.get_recommendations(
                user_id=user_id,
                num_recommendations=num_recommendations * 3,
                use_rl=True
            )
            
            if not result.get('success'):
                return result
            
            all_recommendations = result.get('recommendations', [])
            
            if not all_recommendations:
                return result
            
            # Apply diversity: select recommendations that are different from each other
            diverse_recs = []
            
            # Always add top recommendation
            diverse_recs.append(all_recommendations[0])
            
            # For remaining slots, balance quality with diversity
            for rec in all_recommendations[1:]:
                if len(diverse_recs) >= num_recommendations:
                    break
                
                # Calculate diversity score (how different from already selected)
                diversity_score = self._calculate_diversity_score(rec, diverse_recs)
                
                # Combined score: quality + diversity
                rec['diversity_score'] = diversity_score
                rec['combined_score'] = (
                    (1 - diversity_factor) * rec.get('rl_score', 0) +
                    diversity_factor * diversity_score
                )
                
                # Add if diverse enough
                if diversity_score > 0.3:  # Minimum diversity threshold
                    diverse_recs.append(rec)
            
            # Fill remaining slots if needed
            while len(diverse_recs) < num_recommendations and len(all_recommendations) > len(diverse_recs):
                for rec in all_recommendations:
                    if rec not in diverse_recs:
                        diverse_recs.append(rec)
                        if len(diverse_recs) >= num_recommendations:
                            break
            
            self.logger.info(f"Generated {len(diverse_recs)} diverse recommendations")
            
            return {
                'success': True,
                'recommendations': diverse_recs,
                'method': 'rl_diverse',
                'diversity_factor': diversity_factor
            }
            
        except Exception as e:
            self.logger.error(f"Error generating diverse recommendations: {str(e)}")
            return self.get_recommendations(user_id, num_recommendations, use_rl=True)
    
    def _calculate_diversity_score(
        self, 
        rec: Dict, 
        existing_recs: List[Dict]
    ) -> float:
        """Calculate how different a recommendation is from already selected ones"""
        try:
            # Check domain diversity
            rec_domain = rec.get('domain', '')
            existing_domains = [r.get('domain', '') for r in existing_recs]
            domain_diversity = 1.0 if rec_domain not in existing_domains else 0.5
            
            # Check complexity diversity
            rec_complexity = rec.get('complexity_level', '')
            existing_complexity = [r.get('complexity_level', '') for r in existing_recs]
            complexity_diversity = 1.0 if rec_complexity not in existing_complexity else 0.5
            
            # Average diversity score
            diversity = (domain_diversity + complexity_diversity) / 2.0
            
            return diversity
            
        except Exception as e:
            return 0.5  # Neutral diversity score on error
    
    def adjust_exploration_rate(self, new_rate: float):
        """
        Adjust exploration rate dynamically
        
        Args:
            new_rate: New exploration rate (0.0 - 1.0)
        """
        if 0.0 <= new_rate <= 1.0:
            old_rate = self.exploration_rate
            self.exploration_rate = new_rate
            self.logger.info(f"Exploration rate adjusted: {old_rate:.2f} → {new_rate:.2f}")
        else:
            self.logger.warning(f"Invalid exploration rate: {new_rate}")
    
    def get_model_performance(self, days: int = 7) -> Dict:
        """
        Get performance metrics for the RL model
        
        Returns:
            Dict with performance statistics
        """
        try:
            from database.connection import supabase_admin
            from datetime import timedelta
            
            # Get top performing projects
            top_projects = self.bandit.get_top_projects(limit=10)
            
            # Get actual interactions from last N days
            since_date = (datetime.now() - timedelta(days=days)).isoformat()
            interactions = supabase_admin.table('user_interactions')\
                .select('*')\
                .gte('interaction_time', since_date)\
                .execute()
            
            # Calculate rewards from actual interactions
            total_reward = 0
            positive_count = 0
            interaction_count = 0
            
            if interactions.data:
                for interaction in interactions.data:
                    interaction_type = interaction.get('interaction_type', 'view')
                    
                    # Skip non-recommendation interactions
                    if interaction_type in ['notification_read', 'notification_view']:
                        continue
                    
                    # Skip if no project_id
                    if not interaction.get('github_reference_id'):
                        continue
                    
                    interaction_count += 1
                    
                    # Calculate reward
                    if interaction_type == 'click':
                        reward = 5.0
                    elif interaction_type in ['bookmark', 'bookmark_add']:
                        reward = 10.0
                    elif interaction_type == 'bookmark_remove':
                        reward = -5.0
                    elif interaction_type == 'view':
                        reward = 1.0
                    else:
                        reward = 0
                    
                    total_reward += reward
                    if reward > 0:
                        positive_count += 1
            
            avg_reward = round(total_reward / max(interaction_count, 1), 2)
            positive_rate = round((positive_count / max(interaction_count, 1)) * 100, 2)
            
            return {
                'top_projects': top_projects,
                'avg_reward': avg_reward,
                'positive_interaction_rate': positive_rate,
                'total_training_examples': interaction_count,
                'exploration_rate': self.exploration_rate,
                'days_analyzed': days
            }
            
        except Exception as e:
            self.logger.error(f"Error getting model performance: {str(e)}")
            return {}
    
    def _get_cached_rl_recommendations(self, user_id: str) -> Optional[List[Dict]]:
        """Get cached RL recommendations if available and not stale"""
        try:
            result = supabase_admin.table('user_cached_recommendations').select('*').eq('user_id', user_id).execute()
            
            if result.data and len(result.data) > 0:
                cached = result.data[0]
                
                # Check if cache includes RL data (has 'rl_recommendations' field)
                rl_recs = cached.get('rl_recommendations')
                if rl_recs:
                    self.logger.info(f"Using cached RL recommendations for user {user_id}")
                    return rl_recs
                else:
                    self.logger.info(f"Cache found but no RL data for user {user_id}")
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting cached RL recommendations for user {user_id}: {str(e)}")
            return None
    
    def _save_cached_rl_recommendations(self, user_id: str, recommendations: List[Dict]):
        """Save RL recommendations to cache"""
        try:
            # Check if cache entry exists
            existing = supabase_admin.table('user_cached_recommendations')\
                .select('*')\
                .eq('user_id', user_id)\
                .execute()
            
            if existing.data and len(existing.data) > 0:
                # Update existing entry - only update rl_recommendations column
                result = supabase_admin.table('user_cached_recommendations')\
                    .update({
                        'rl_recommendations': recommendations,
                        'updated_at': datetime.now().isoformat()
                    })\
                    .eq('user_id', user_id)\
                    .execute()
            else:
                # Insert new entry - need to provide recommendations column (NOT NULL)
                # Use empty array for base recommendations since we only care about RL cache here
                cache_data = {
                    'user_id': user_id,
                    'recommendations': [],  # Empty array to satisfy NOT NULL constraint
                    'profile_hash': '',  # Empty string to satisfy NOT NULL constraint
                    'rl_recommendations': recommendations,  # RL-ranked recommendations
                    'updated_at': datetime.now().isoformat()
                }
                result = supabase_admin.table('user_cached_recommendations').insert(cache_data).execute()
            
            self.logger.info(f"Cached {len(recommendations)} RL recommendations for user {user_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error caching RL recommendations for user {user_id}: {str(e)}")
            return False
    
    def invalidate_user_cache(self, user_id: str):
        """Invalidate cached recommendations for a user (call when profile is updated)"""
        try:
            result = supabase_admin.table('user_cached_recommendations').delete().eq('user_id', user_id).execute()
            self.logger.info(f"Invalidated RL recommendation cache for user {user_id}")
            return True
        except Exception as e:
            self.logger.error(f"Error invalidating RL cache for user {user_id}: {str(e)}")
            return False


# Global RL engine instance
_rl_engine = None

def get_rl_engine():
    """Get or create the global RL engine instance"""
    global _rl_engine
    if _rl_engine is None:
        _rl_engine = RLRecommendationEngine(exploration_rate=0.15)
    return _rl_engine


# Testing
if __name__ == '__main__':
    rl_engine = get_rl_engine()
    
    print("Testing RL Recommendation Engine...")
    
    # Test user ID
    test_user_id = 'test_user_123'
    
    print(f"\n1. Getting RL recommendations for user {test_user_id}:")
    result = rl_engine.get_recommendations(test_user_id, num_recommendations=5, use_rl=True)
    
    if result.get('success'):
        recs = result['recommendations']
        print(f"   Retrieved {len(recs)} recommendations")
        print(f"   Method: {result['method']}")
        print(f"   Duration: {result['duration_ms']}ms")
        
        if recs:
            print(f"\n   Top recommendation:")
            top = recs[0]
            print(f"   - Title: {top.get('title', 'N/A')}")
            print(f"   - Similarity: {top.get('similarity', 0):.4f}")
            print(f"   - RL Score: {top.get('rl_score', 0):.4f}")
            print(f"   - Method: {top.get('recommendation_method', 'N/A')}")
    
    print(f"\n2. Testing diverse recommendations:")
    diverse_result = rl_engine.get_diverse_recommendations(test_user_id, num_recommendations=5)
    
    if diverse_result.get('success'):
        diverse_recs = diverse_result['recommendations']
        print(f"   Retrieved {len(diverse_recs)} diverse recommendations")
        domains = [r.get('domain', 'N/A') for r in diverse_recs]
        print(f"   Domains: {set(domains)}")
    
    print(f"\n3. Recording test interaction:")
    if result.get('success') and result['recommendations']:
        test_project = result['recommendations'][0]
        rl_engine.record_interaction(
            user_id=test_user_id,
            project_id=test_project['id'],
            interaction_type='click',
            rank_position=1,
            duration_seconds=45
        )
        print("   ✅ Interaction recorded and model updated")
    
    print(f"\n4. Getting model performance:")
    performance = rl_engine.get_model_performance(days=7)
    print(f"   Average Reward: {performance.get('avg_reward', 0)}")
    print(f"   Positive Rate: {performance.get('positive_interaction_rate', 0)}%")
    print(f"   Training Examples: {performance.get('total_training_examples', 0)}")
    
    print("\n✅ RL recommendation engine test complete!")