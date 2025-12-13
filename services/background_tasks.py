# services/background_tasks.py
"""
Background Tasks for Reinforcement Learning (Simplified - No APScheduler)
Manual training only - trigger from admin panel
"""
from services.contextual_bandit import get_contextual_bandit
from services.reward_calculator import get_reward_calculator
from services.rl_recommendation_engine import get_rl_engine
from services.logging_service import get_logger
from database.connection import supabase_admin as supabase
from datetime import datetime, timedelta

logger = get_logger('background_tasks')


class BackgroundTaskScheduler:
    """
    Manages manual RL model training tasks
    Automatic scheduling has been disabled - all training is triggered manually
    """
    
    def __init__(self):
        self.logger = logger
        self.bandit = get_contextual_bandit()
        self.reward_calculator = get_reward_calculator()
        self.rl_engine = get_rl_engine()
        self.logger.info("Background task scheduler initialized (manual mode only)")
    
    def start(self):
        """
        Start method (no-op for manual mode)
        All training must be triggered manually from admin panel
        """
        self.logger.info("⚠️  Automatic background tasks disabled")
        self.logger.info("   Use admin panel to trigger manual training")
    
    def stop(self):
        """Stop method (no-op for manual mode)"""
        self.logger.info("Background task scheduler stopped (manual mode)")
    
    def run_manual_retrain(self, days: int = 7):
        """
        Manually trigger model retraining
        This is the primary method used from the admin panel
        
        Args:
            days: Number of days of data to process
        """
        try:
            start_time = datetime.now()
            self.logger.info(f"🔧 Manual retraining triggered for {days} days")
            
            # Run batch update - this updates the model with recent interaction data
            self.bandit.batch_update_from_interactions(days=days)
            
            # Get post-training performance
            post_performance = self.rl_engine.get_model_performance(days=days)
            post_avg_reward = post_performance.get('avg_reward', 0)
            post_positive_rate = post_performance.get('positive_interaction_rate', 0)
            total_interactions = post_performance.get('total_training_examples', 0)
            
            # Get post-training CTR
            ctr_result = supabase.table('recommendation_results')\
                .select('id', count='exact')\
                .gte('created_at', (datetime.now() - timedelta(days=days)).isoformat())\
                .execute()
            
            clicks_result = supabase.table('user_interactions')\
                .select('id', count='exact')\
                .eq('interaction_type', 'click')\
                .gte('interaction_time', (datetime.now() - timedelta(days=days)).isoformat())\
                .execute()
            
            impressions = ctr_result.count or 0
            clicks = clicks_result.count or 0
            post_ctr = (clicks / impressions * 100) if impressions > 0 else 0
            
            duration = (datetime.now() - start_time).total_seconds()
            
            # Store training history
            # Note: pre/post comparison within a session doesn't show improvement
            # because both query the same historical data. Improvement is visible
            # across training sessions as the model learns over time.
            training_record = {
                'training_date': datetime.now().date().isoformat(),
                'training_timestamp': datetime.now().isoformat(),
                'days_processed': days,
                'post_avg_reward': post_avg_reward,
                'post_positive_rate': post_positive_rate,
                'post_avg_ctr': post_ctr,
                'projects_updated': total_interactions,
                'total_interactions_processed': total_interactions,
                'exploration_rate': self.rl_engine.exploration_rate,
                'notes': f'Manual training - {days} days - Completed in {duration:.2f}s - Avg Reward: {post_avg_reward:.2f}'
            }
            
            supabase.table('rl_training_history').insert(training_record).execute()
            
            self.logger.info(
                f"✅ Manual retraining complete in {duration:.2f}s | "
                f"Avg Reward={post_avg_reward:.2f}, "
                f"Positive Rate={post_positive_rate:.2f}%, "
                f"Examples={total_interactions}"
            )
            
            return post_performance
            
        except Exception as e:
            self.logger.error(f"Error in manual retraining: {str(e)}")
            return {}
    
    def invalidate_old_caches(self):
        """
        Invalidate old recommendation caches
        Clears caches older than 24 hours
        """
        try:
            self.logger.info("🗑️ Starting cache invalidation...")
            
            cutoff_time = (datetime.now() - timedelta(hours=24)).isoformat()
            
            result = supabase.table('user_cached_recommendations')\
                .delete()\
                .lt('updated_at', cutoff_time)\
                .execute()
            
            deleted_count = len(result.data) if result.data else 0
            
            self.logger.info(f"✅ Cache invalidation complete: {deleted_count} old caches removed")
            
        except Exception as e:
            self.logger.error(f"Error in cache invalidation: {str(e)}")
    
    def monitor_performance(self):
        """
        Monitor model performance metrics
        Returns current performance data
        """
        try:
            performance = self.rl_engine.get_model_performance(days=1)
            
            avg_reward = performance.get('avg_reward', 0)
            positive_rate = performance.get('positive_interaction_rate', 0)
            
            self.logger.debug(
                f"Performance: Avg Reward={avg_reward:.2f}, "
                f"Positive Rate={positive_rate:.2f}%"
            )
            
            return performance
            
        except Exception as e:
            self.logger.error(f"Error in performance monitoring: {str(e)}")
            return {}


# Global task scheduler instance
_task_scheduler = None

def get_task_scheduler():
    """Get or create the global task scheduler instance"""
    global _task_scheduler
    if _task_scheduler is None:
        _task_scheduler = BackgroundTaskScheduler()
    return _task_scheduler


def start_background_tasks():
    """Start all background tasks (call this on app startup)"""
    scheduler = get_task_scheduler()
    scheduler.start()
    return scheduler


# Testing
if __name__ == '__main__':
    print("Testing Background Task Scheduler...")
    
    scheduler = get_task_scheduler()
    
    print("\n1. Starting scheduler...")
    scheduler.start()
    print("   ✅ Scheduler started")
    
    print("\n2. Running manual retrain...")
    performance = scheduler.run_manual_retrain(days=7)
    print(f"   Avg Reward: {performance.get('avg_reward', 0)}")
    print(f"   Training Examples: {performance.get('total_training_examples', 0)}")
    
    print("\n3. Testing cache invalidation...")
    scheduler.invalidate_old_caches()
    
    print("\n4. Testing performance monitoring...")
    scheduler.monitor_performance()
    
    print("\n5. Stopping scheduler...")
    scheduler.stop()
    print("   ✅ Scheduler stopped")
    
    print("\n✅ Background task scheduler test complete!")