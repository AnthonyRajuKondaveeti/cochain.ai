# services/rl_performance_service.py
"""
Optimized RL Performance Service
Provides fast performance metrics for the RL dashboard
"""
from database.connection import supabase_admin as supabase
from services.logging_service import get_logger
from datetime import datetime, timedelta
from typing import Dict, List, Optional

logger = get_logger('rl_performance_service')


class RLPerformanceService:
    """Service for retrieving RL performance metrics efficiently"""
    
    def __init__(self):
        self.logger = logger
    
    def get_performance_data(self, days: int = 7) -> Dict:
        """
        Get RL performance data for the dashboard
        Optimized to minimize database queries
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Dict with performance metrics, training history, and trends
        """
        try:
            since_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            # 1. Get training history (fast, indexed query)
            training_history = self._get_training_history(limit=30)
            
            # 2. Get current performance from latest training record
            if training_history:
                latest = training_history[0]
                performance = {
                    'avg_reward': latest.get('post_avg_reward', 0),
                    'positive_interaction_rate': latest.get('post_positive_rate', 0),
                    'total_training_examples': latest.get('total_interactions_processed', 0),
                    'exploration_rate': latest.get('exploration_rate', 0.15),
                    'days_analyzed': days
                }
            else:
                # Fallback to calculating from interactions (slower)
                performance = self._calculate_performance_from_interactions(since_date, days)
            
            # 3. Get top projects from project_rl_stats (fast, pre-aggregated)
            top_projects = self._get_top_projects(limit=10)
            performance['top_projects'] = top_projects
            
            # 4. Calculate trends from training history
            trends = self._calculate_trends(training_history)
            
            # 5. Get system info
            system_info = {
                'exploration_rate': 0.15,
                'similarity_weight': 0.6,
                'bandit_weight': 0.4
            }
            
            return {
                'performance': performance,
                'training_history': training_history,
                'trends': trends,
                'system_info': system_info
            }
            
        except Exception as e:
            self.logger.error(f"Error getting RL performance data: {str(e)}", exc_info=True)
            raise
    
    def _get_training_history(self, limit: int = 30) -> List[Dict]:
        """Get training history from database"""
        try:
            result = supabase.table('rl_training_history')\
                .select('*')\
                .order('training_timestamp', desc=True)\
                .limit(limit)\
                .execute()
            
            return result.data if result.data else []
        except Exception as e:
            self.logger.warning(f"Error fetching training history: {str(e)}")
            return []
    
    def _get_top_projects(self, limit: int = 10) -> List[Dict]:
        """Get top performing projects from pre-aggregated stats"""
        try:
            # Use project_rl_stats view for fast aggregated data
            result = supabase.table('project_rl_stats')\
                .select('*')\
                .order('total_clicks', desc=True)\
                .limit(limit)\
                .execute()
            
            if not result.data:
                return []
            
            # Transform to expected format
            top_projects = []
            for project in result.data:
                impressions = project.get('total_impressions', 0)
                clicks = project.get('total_clicks', 0)
                success_rate = round((clicks / impressions * 100) if impressions > 0 else 0, 1)
                
                # Calculate avg reward (simplified)
                avg_reward = round((clicks * 5.0) / max(impressions, 1), 2)
                
                top_projects.append({
                    'id': project.get('github_reference_id'),
                    'title': project.get('title', 'Unknown'),
                    'domain': project.get('domain', 'N/A'),
                    'success_rate': success_rate,
                    'total_interactions': impressions,
                    'avg_reward': avg_reward,
                    'clicks': clicks,
                    'views': impressions - clicks
                })
            
            return top_projects
            
        except Exception as e:
            self.logger.warning(f"Error fetching top projects: {str(e)}")
            return []
    
    def _calculate_performance_from_interactions(self, since_date: str, days: int) -> Dict:
        """Fallback: Calculate performance from raw interactions (slower)"""
        try:
            # Get interaction counts by type
            interactions = supabase.table('user_interactions')\
                .select('interaction_type', count='exact')\
                .gte('interaction_time', since_date)\
                .execute()
            
            total = interactions.count or 0
            
            # Simplified calculation
            return {
                'avg_reward': 2.5,  # Default estimate
                'positive_interaction_rate': 50.0,  # Default estimate
                'total_training_examples': total,
                'exploration_rate': 0.15,
                'days_analyzed': days
            }
        except Exception as e:
            self.logger.warning(f"Error calculating performance from interactions: {str(e)}")
            return {
                'avg_reward': 0,
                'positive_interaction_rate': 0,
                'total_training_examples': 0,
                'exploration_rate': 0.15,
                'days_analyzed': days
            }
    
    def _calculate_trends(self, training_history: List[Dict]) -> Dict:
        """Calculate improvement trends from training history"""
        if not training_history or len(training_history) < 2:
            return {
                'reward_improvement': 0,
                'positive_rate_improvement': 0,
                'ctr_improvement': 0
            }
        
        recent = training_history[0]
        previous = training_history[1]
        
        # Calculate reward improvement
        recent_reward = recent.get('post_avg_reward', 0)
        previous_reward = previous.get('post_avg_reward', 0)
        reward_improvement = 0
        if previous_reward != 0:
            reward_improvement = round(((recent_reward - previous_reward) / abs(previous_reward)) * 100, 2)
        
        # Calculate positive rate improvement
        recent_positive = recent.get('post_positive_rate', 0)
        previous_positive = previous.get('post_positive_rate', 0)
        positive_improvement = 0
        if previous_positive != 0:
            positive_improvement = round(((recent_positive - previous_positive) / abs(previous_positive)) * 100, 2)
            positive_improvement = max(-100, min(100, positive_improvement))  # Cap at reasonable range
        
        # Calculate CTR improvement
        recent_ctr = recent.get('post_avg_ctr', 0)
        previous_ctr = previous.get('post_avg_ctr', 0)
        ctr_improvement = 0
        if previous_ctr != 0:
            ctr_improvement = round(((recent_ctr - previous_ctr) / abs(previous_ctr)) * 100, 2)
            ctr_improvement = max(-100, min(200, ctr_improvement))  # Cap at reasonable range
        
        return {
            'reward_improvement': reward_improvement,
            'positive_rate_improvement': positive_improvement,
            'ctr_improvement': ctr_improvement
        }


# Global service instance
_rl_performance_service = None

def get_rl_performance_service():
    """Get or create the global RL performance service instance"""
    global _rl_performance_service
    if _rl_performance_service is None:
        _rl_performance_service = RLPerformanceService()
    return _rl_performance_service
