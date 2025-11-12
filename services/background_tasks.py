# services/background_tasks.py
"""
Background Tasks for Reinforcement Learning
Handles daily model retraining and maintenance
"""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from services.contextual_bandit import get_contextual_bandit
from services.reward_calculator import get_reward_calculator
from services.rl_recommendation_engine import get_rl_engine
from services.logging_service import get_logger
from database.connection import supabase_admin as supabase  # Use admin client for background jobs
from datetime import datetime, timedelta
import atexit

logger = get_logger('background_tasks')


class BackgroundTaskScheduler:
    """
    Manages background tasks for RL model maintenance
    
    Tasks:
    1. Daily model retraining (update bandit parameters)
    2. Cache invalidation (clear old recommendation caches)
    3. Performance monitoring (track model improvements)
    4. A/B test evaluation (check test results)
    """
    
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.logger = logger
        self.bandit = get_contextual_bandit()
        self.reward_calculator = get_reward_calculator()
        self.rl_engine = get_rl_engine()
        
        # Add shutdown handler
        atexit.register(lambda: self.scheduler.shutdown())
    
    def start(self):
        """Start all background tasks"""
        try:
            # Task 1: Daily model retraining at 2 AM
            self.scheduler.add_job(
                func=self.daily_model_retrain,
                trigger=CronTrigger(hour=2, minute=0),
                id='daily_model_retrain',
                name='Daily RL Model Retraining',
                replace_existing=True
            )
            
            # Task 2: Cache invalidation every 6 hours
            self.scheduler.add_job(
                func=self.invalidate_old_caches,
                trigger=IntervalTrigger(hours=6),
                id='cache_invalidation',
                name='Cache Invalidation',
                replace_existing=True
            )
            
            # Task 3: Performance monitoring every hour
            self.scheduler.add_job(
                func=self.monitor_performance,
                trigger=IntervalTrigger(hours=1),
                id='performance_monitoring',
                name='Performance Monitoring',
                replace_existing=True
            )
            
            # Task 4: A/B test evaluation daily at 3 AM
            self.scheduler.add_job(
                func=self.evaluate_ab_tests,
                trigger=CronTrigger(hour=3, minute=0),
                id='ab_test_evaluation',
                name='A/B Test Evaluation',
                replace_existing=True
            )
            
            # Start the scheduler
            self.scheduler.start()
            
            self.logger.info("✅ Background task scheduler started")
            self.logger.info("   - Daily model retraining: 2:00 AM")
            self.logger.info("   - Cache invalidation: Every 6 hours")
            self.logger.info("   - Performance monitoring: Every hour")
            self.logger.info("   - A/B test evaluation: 3:00 AM")
            
        except Exception as e:
            self.logger.error(f"Failed to start background tasks: {str(e)}")
    
    def stop(self):
        """Stop all background tasks"""
        self.scheduler.shutdown()
        self.logger.info("Background task scheduler stopped")
    
    def daily_model_retrain(self):
        """
        Daily batch update of RL model
        Processes yesterday's interactions and updates bandit parameters
        """
        try:
            start_time = datetime.now()
            self.logger.info("🔄 Starting daily model retraining...")
            
            # Get current model performance (before training)
            pre_performance = self.rl_engine.get_model_performance(days=7)
            pre_avg_reward = pre_performance.get('avg_reward', 0)
            pre_positive_rate = pre_performance.get('positive_interaction_rate', 0)
            
            # Get pre-training CTR
            pre_ctr_result = supabase.table('recommendation_results')\
                .select('id', count='exact')\
                .gte('created_at', (datetime.now() - timedelta(days=7)).isoformat())\
                .execute()
            
            pre_clicks_result = supabase.table('user_interactions')\
                .select('id', count='exact')\
                .eq('interaction_type', 'click')\
                .gte('interaction_time', (datetime.now() - timedelta(days=7)).isoformat())\
                .execute()
            
            pre_impressions = pre_ctr_result.count or 0
            pre_clicks = pre_clicks_result.count or 0
            pre_ctr = (pre_clicks / pre_impressions * 100) if pre_impressions > 0 else 0
            
            # Run batch update (process yesterday's interactions)
            self.bandit.batch_update_from_interactions(days=1)
            
            # Get post-training performance
            post_performance = self.rl_engine.get_model_performance(days=7)
            post_avg_reward = post_performance.get('avg_reward', 0)
            post_positive_rate = post_performance.get('positive_interaction_rate', 0)
            
            # Calculate improvements
            reward_improvement = 0
            if pre_avg_reward != 0:
                reward_improvement = (post_avg_reward - pre_avg_reward) / abs(pre_avg_reward) * 100
            
            duration = (datetime.now() - start_time).total_seconds()
            
            # Store training history
            training_record = {
                'training_date': datetime.now().date().isoformat(),
                'days_processed': 1,
                'pre_avg_reward': pre_avg_reward,
                'pre_positive_rate': pre_positive_rate,
                'pre_avg_ctr': pre_ctr,
                'post_avg_reward': post_avg_reward,
                'post_positive_rate': post_positive_rate,
                'post_avg_ctr': pre_ctr,  # Will update in next cycle
                'projects_updated': post_performance.get('total_training_examples', 0),
                'exploration_rate': self.rl_engine.exploration_rate,
                'reward_improvement': reward_improvement,
                'notes': f'Completed in {duration:.2f} seconds'
            }
            
            supabase.table('rl_training_history').insert(training_record).execute()
            
            self.logger.info(
                f"✅ Daily model retraining complete in {duration:.2f}s | "
                f"Reward improvement: {reward_improvement:+.2f}%"
            )
            
        except Exception as e:
            self.logger.error(f"Error in daily model retraining: {str(e)}", exc_info=True)
    
    def invalidate_old_caches(self):
        """
        Invalidate old recommendation caches
        Clears caches older than 24 hours to ensure fresh recommendations
        """
        try:
            self.logger.info("🗑️ Starting cache invalidation...")
            
            # Delete caches older than 24 hours
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
        Tracks key metrics and alerts on anomalies
        """
        try:
            self.logger.debug("📊 Running performance monitoring...")
            
            # Get current performance
            performance = self.rl_engine.get_model_performance(days=1)
            
            avg_reward = performance.get('avg_reward', 0)
            positive_rate = performance.get('positive_interaction_rate', 0)
            
            # Check for anomalies
            if avg_reward < -5.0:
                self.logger.warning(f"⚠️ ALERT: Negative average reward detected: {avg_reward:.2f}")
            
            if positive_rate < 30.0 and performance.get('total_training_examples', 0) > 50:
                self.logger.warning(f"⚠️ ALERT: Low positive interaction rate: {positive_rate:.2f}%")
            
            # Log current stats
            self.logger.debug(
                f"Current Performance: Avg Reward={avg_reward:.2f}, "
                f"Positive Rate={positive_rate:.2f}%, "
                f"Examples={performance.get('total_training_examples', 0)}"
            )
            
        except Exception as e:
            self.logger.error(f"Error in performance monitoring: {str(e)}")
    
    def evaluate_ab_tests(self):
        """
        Evaluate active A/B tests
        Checks if tests have reached statistical significance
        """
        try:
            self.logger.info("🧪 Evaluating A/B tests...")
            
            # Get active A/B tests
            active_tests = supabase.table('rl_ab_test')\
                .select('*')\
                .eq('status', 'active')\
                .execute()
            
            if not active_tests.data:
                self.logger.info("No active A/B tests to evaluate")
                return
            
            for test in active_tests.data:
                test_id = test['id']
                test_name = test['test_name']
                
                # Check if test has run long enough (minimum 7 days)
                start_date = datetime.fromisoformat(test['start_date'].replace('Z', '+00:00'))
                days_running = (datetime.now() - start_date).days
                
                if days_running < 7:
                    self.logger.info(f"Test '{test_name}' needs more time ({days_running}/7 days)")
                    continue
                
                # Get user assignments
                assignments = supabase.table('user_ab_assignment')\
                    .select('*')\
                    .eq('ab_test_id', test_id)\
                    .execute()
                
                if not assignments.data:
                    continue
                
                # Calculate metrics for each group
                control_users = [a['user_id'] for a in assignments.data if a['group_name'] == 'control']
                treatment_users = [a['user_id'] for a in assignments.data if a['group_name'] == 'treatment']
                
                # This is simplified - in production you'd calculate proper statistics
                control_metrics = self._calculate_group_metrics(control_users)
                treatment_metrics = self._calculate_group_metrics(treatment_users)
                
                # Simple significance check (you'd use proper statistical test in production)
                ctr_diff = abs(treatment_metrics['ctr'] - control_metrics['ctr'])
                is_significant = ctr_diff > 1.0  # 1% difference threshold
                
                # Determine winner
                winner = 'inconclusive'
                if is_significant:
                    if treatment_metrics['ctr'] > control_metrics['ctr']:
                        winner = 'treatment'
                    else:
                        winner = 'control'
                
                # Update test
                update_data = {
                    'control_users': len(control_users),
                    'control_avg_ctr': control_metrics['ctr'],
                    'treatment_users': len(treatment_users),
                    'treatment_avg_ctr': treatment_metrics['ctr'],
                    'is_significant': is_significant,
                    'winner': winner,
                    'updated_at': datetime.now().isoformat()
                }
                
                supabase.table('rl_ab_test').update(update_data).eq('id', test_id).execute()
                
                self.logger.info(
                    f"Evaluated test '{test_name}': "
                    f"Control CTR={control_metrics['ctr']:.2f}%, "
                    f"Treatment CTR={treatment_metrics['ctr']:.2f}%, "
                    f"Winner={winner}"
                )
            
            self.logger.info("✅ A/B test evaluation complete")
            
        except Exception as e:
            self.logger.error(f"Error evaluating A/B tests: {str(e)}")
    
    def _calculate_group_metrics(self, user_ids: list) -> dict:
        """Calculate metrics for a group of users in A/B test"""
        try:
            if not user_ids:
                return {'ctr': 0.0, 'avg_reward': 0.0}
            
            # Get interactions for these users
            interactions = supabase.table('user_interactions')\
                .select('*')\
                .in_('user_id', user_ids)\
                .gte('interaction_time', (datetime.now() - timedelta(days=7)).isoformat())\
                .execute()
            
            # Get recommendations for these users
            recommendations = supabase.table('recommendation_results')\
                .select('*')\
                .gte('created_at', (datetime.now() - timedelta(days=7)).isoformat())\
                .execute()
            
            # Calculate CTR
            total_impressions = len(recommendations.data) if recommendations.data else 0
            total_clicks = sum(1 for i in (interactions.data or []) if i['interaction_type'] == 'click')
            
            ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0.0
            
            # Calculate average reward
            total_reward = 0.0
            for interaction in (interactions.data or []):
                reward = self.reward_calculator.calculate_interaction_reward(
                    interaction_type=interaction['interaction_type'],
                    rank_position=interaction.get('rank_position')
                )
                total_reward += reward
            
            avg_reward = total_reward / len(interactions.data) if interactions.data else 0.0
            
            return {
                'ctr': round(ctr, 2),
                'avg_reward': round(avg_reward, 2)
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating group metrics: {str(e)}")
            return {'ctr': 0.0, 'avg_reward': 0.0}
    
    def run_manual_retrain(self, days: int = 7):
        """
        Manually trigger model retraining
        Useful for testing or immediate updates
        
        Args:
            days: Number of days of data to process
        """
        try:
            start_time = datetime.now()
            self.logger.info(f"🔧 Manual retraining triggered for {days} days")
            
            # Get pre-training performance
            pre_performance = self.rl_engine.get_model_performance(days=days)
            pre_avg_reward = pre_performance.get('avg_reward', 0)
            pre_positive_rate = pre_performance.get('positive_interaction_rate', 0)
            
            # Get pre-training CTR
            pre_ctr_result = supabase.table('recommendation_results')\
                .select('id', count='exact')\
                .gte('created_at', (datetime.now() - timedelta(days=days)).isoformat())\
                .execute()
            
            pre_clicks_result = supabase.table('user_interactions')\
                .select('id', count='exact')\
                .eq('interaction_type', 'click')\
                .gte('interaction_time', (datetime.now() - timedelta(days=days)).isoformat())\
                .execute()
            
            pre_impressions = pre_ctr_result.count or 0
            pre_clicks = pre_clicks_result.count or 0
            pre_ctr = (pre_clicks / pre_impressions * 100) if pre_impressions > 0 else 0
            
            # Run batch update
            self.bandit.batch_update_from_interactions(days=days)
            
            # Get post-training performance
            post_performance = self.rl_engine.get_model_performance(days=days)
            post_avg_reward = post_performance.get('avg_reward', 0)
            post_positive_rate = post_performance.get('positive_interaction_rate', 0)
            
            # Calculate improvements
            reward_improvement = 0
            if pre_avg_reward != 0:
                reward_improvement = (post_avg_reward - pre_avg_reward) / abs(pre_avg_reward) * 100
            
            duration = (datetime.now() - start_time).total_seconds()
            
            # Store training history
            training_record = {
                'training_date': datetime.now().date().isoformat(),
                'days_processed': days,
                'pre_avg_reward': pre_avg_reward,
                'pre_positive_rate': pre_positive_rate,
                'pre_avg_ctr': pre_ctr,
                'post_avg_reward': post_avg_reward,
                'post_positive_rate': post_positive_rate,
                'post_avg_ctr': pre_ctr,  # Will update in next cycle
                'projects_updated': post_performance.get('total_training_examples', 0),
                'exploration_rate': self.rl_engine.exploration_rate,
                'reward_improvement': reward_improvement,
                'notes': f'Manual training - {days} days - Completed in {duration:.2f} seconds'
            }
            
            supabase.table('rl_training_history').insert(training_record).execute()
            
            self.logger.info(
                f"✅ Manual retraining complete in {duration:.2f}s | "
                f"Avg Reward={post_avg_reward:.2f}, "
                f"Examples={post_performance.get('total_training_examples', 0)}, "
                f"Reward improvement: {reward_improvement:+.2f}%"
            )
            
            return post_performance
            
        except Exception as e:
            self.logger.error(f"Error in manual retraining: {str(e)}")
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