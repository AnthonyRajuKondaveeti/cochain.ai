# services/ab_test_service.py
"""
A/B Testing Service for RL Recommendations
Automatically tests RL vs Baseline and decides which to use
"""

from database.connection import supabase_admin as supabase
from services.logging_service import get_logger
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import numpy as np
from scipy import stats

logger = get_logger('ab_test')


class ABTestService:
    """
    A/B Testing framework for comparing RL vs Baseline recommendations
    
    Features:
    - Automatically splits users into control (baseline) and treatment (RL) groups
    - Tracks metrics for each group (CTR, engagement, conversion)
    - Statistical significance testing
    - Automatic winner selection based on performance
    - Gradual rollout of winning variant
    """
    
    def __init__(self):
        self.logger = logger
        
        # Test configuration
        self.min_sample_size = 100  # Minimum interactions per group
        self.confidence_level = 0.95  # 95% confidence for significance
        self.minimum_effect_size = 0.05  # 5% minimum improvement to declare winner
        
    def get_user_group(self, user_id: str) -> str:
        """
        Determine which A/B test group a user belongs to
        
        Args:
            user_id: User ID
            
        Returns:
            'control' (baseline) or 'treatment' (RL)
        """
        try:
            # Get current test configuration
            test_config = self.get_active_test_config()
            
            if not test_config:
                return 'treatment'  # Default to RL if no active test
            
            # Check if user already assigned
            assignment_result = supabase.table('ab_test_assignments')\
                .select('*')\
                .eq('user_id', user_id)\
                .execute()
            
            if assignment_result.data and len(assignment_result.data) > 0:
                existing_assignment = assignment_result.data[0]
                
                # Check if assignment is for current test
                if existing_assignment['test_id'] == test_config['id']:
                    # Return existing assignment
                    return existing_assignment['group_name']
                else:
                    # Old test assignment - delete and reassign
                    self.logger.info(f"User {user_id} assigned to old test, reassigning to current test")
                    try:
                        supabase.table('ab_test_assignments')\
                            .delete()\
                            .eq('user_id', user_id)\
                            .execute()
                    except Exception as del_error:
                        self.logger.warning(f"Failed to delete old assignment: {del_error}")
                    # Continue to assign to new test
            
            # Get current test configuration
            test_config = self.get_active_test_config()
            
            if not test_config:
                return 'treatment'  # Default to RL if no active test
            
            # Assign user based on split ratio using deterministic hash
            # Convert UUID string to integer for consistent hashing
            import hashlib
            hash_object = hashlib.md5(user_id.encode())
            hash_int = int(hash_object.hexdigest(), 16)
            hash_val = hash_int % 100
            
            if hash_val < test_config['control_percentage']:
                group = 'control'
            else:
                group = 'treatment'
            
            # Save assignment
            try:
                supabase.table('ab_test_assignments').insert({
                    'user_id': user_id,
                    'test_id': test_config['id'],
                    'group_name': group,
                    'assigned_at': datetime.now().isoformat()
                }).execute()
                
                self.logger.info(f"Assigned user {user_id} to group '{group}' for test {test_config['test_name']}")
            except Exception as insert_error:
                self.logger.warning(f"Failed to save assignment (might already exist): {insert_error}")
            
            return group
            
        except Exception as e:
            self.logger.error(f"Error getting user group: {e}")
            return 'treatment'  # Default to RL on error
    
    def get_active_test_config(self) -> Optional[Dict]:
        """
        Get the currently active A/B test configuration
        
        Returns:
            Test config dict or None if no active test
        """
        try:
            result = supabase.table('ab_test_configs')\
                .select('*')\
                .eq('status', 'active')\
                .order('created_at', desc=True)\
                .limit(1)\
                .execute()
            
            if result.data:
                return result.data[0]
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting test config: {e}")
            return None
    
    def start_new_test(
        self, 
        test_name: str,
        control_percentage: int = 50,
        duration_days: int = 14,
        description: str = ""
    ) -> Dict:
        """
        Start a new A/B test
        
        Args:
            test_name: Name of the test
            control_percentage: Percentage of users in control group (0-100)
            duration_days: Test duration in days
            description: Test description
            
        Returns:
            Created test config
        """
        try:
            # End any existing active tests
            supabase.table('ab_test_configs')\
                .update({'status': 'ended'})\
                .eq('status', 'active')\
                .execute()
            
            # Create new test
            end_date = (datetime.now() + timedelta(days=duration_days)).isoformat()
            
            test_config = {
                'test_name': test_name,
                'description': description,
                'control_percentage': control_percentage,
                'treatment_percentage': 100 - control_percentage,
                'status': 'active',
                'start_date': datetime.now().isoformat(),
                'end_date': end_date,
                'created_by': 'system'
            }
            
            result = supabase.table('ab_test_configs').insert(test_config).execute()
            
            self.logger.info(f"Started new A/B test: {test_name} ({control_percentage}% control)")
            
            return result.data[0] if result.data else {}
            
        except Exception as e:
            self.logger.error(f"Error starting test: {e}")
            return {}
    
    def calculate_test_metrics(self, test_id: str, days: int = 7) -> Dict:
        """
        Calculate performance metrics for both groups
        
        Args:
            test_id: Test ID
            days: Number of days to analyze
            
        Returns:
            Dict with metrics for both groups
        """
        try:
            since_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            # Get users in each group
            assignments = supabase.table('ab_test_assignments')\
                .select('user_id, group_name')\
                .eq('test_id', test_id)\
                .execute()
            
            if not assignments.data:
                return {'error': 'No users assigned to test yet'}
            
            control_users = [a['user_id'] for a in assignments.data if a['group_name'] == 'control']
            treatment_users = [a['user_id'] for a in assignments.data if a['group_name'] == 'treatment']
            
            # Calculate metrics for each group
            control_metrics = self._calculate_group_metrics(control_users, since_date)
            treatment_metrics = self._calculate_group_metrics(treatment_users, since_date)
            
            # Statistical significance test
            significance = self._test_significance(control_metrics, treatment_metrics)
            
            return {
                'control': control_metrics,
                'treatment': treatment_metrics,
                'significance': significance,
                'winner': self._determine_winner(control_metrics, treatment_metrics, significance)
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating test metrics: {e}")
            return {'error': str(e)}
    
    def _calculate_group_metrics(self, user_ids: List[str], since_date: str) -> Dict:
        """
        Calculate metrics for a group of users
        """
        if not user_ids:
            return {
                'user_count': 0,
                'impressions': 0,
                'clicks': 0,
                'bookmarks': 0,
                'ctr': 0.0,
                'engagement_rate': 0.0,
                'avg_reward': 0.0
            }
        
        # Get recommendations shown (impressions)
        impressions = supabase.table('recommendation_results')\
            .select('id', count='exact')\
            .in_('user_id', user_ids)\
            .gte('created_at', since_date)\
            .execute()
        
        # Get interactions
        interactions = supabase.table('user_interactions')\
            .select('*')\
            .in_('user_id', user_ids)\
            .gte('interaction_time', since_date)\
            .execute()
        
        clicks = len([i for i in (interactions.data or []) if i['interaction_type'] == 'click'])
        bookmarks = len([i for i in (interactions.data or []) if i['interaction_type'] in ['bookmark', 'bookmark_add']])
        
        impression_count = impressions.count or 0
        interaction_count = len(interactions.data) if interactions.data else 0
        
        ctr = (clicks / impression_count * 100) if impression_count > 0 else 0.0
        engagement_rate = (interaction_count / impression_count * 100) if impression_count > 0 else 0.0
        
        # Calculate average reward
        from services.reward_calculator import get_reward_calculator
        reward_calc = get_reward_calculator()
        
        total_reward = 0.0
        for interaction in (interactions.data or []):
            reward = reward_calc.calculate_interaction_reward(
                interaction_type=interaction['interaction_type'],
                rank_position=interaction.get('rank_position'),
                duration_seconds=interaction.get('duration_seconds')
            )
            total_reward += reward
        
        avg_reward = total_reward / interaction_count if interaction_count > 0 else 0.0
        
        return {
            'user_count': len(user_ids),
            'impressions': impression_count,
            'clicks': clicks,
            'bookmarks': bookmarks,
            'total_interactions': interaction_count,
            'ctr': round(ctr, 2),
            'engagement_rate': round(engagement_rate, 2),
            'avg_reward': round(avg_reward, 3)
        }
    
    def _test_significance(self, control: Dict, treatment: Dict) -> Dict:
        """
        Test statistical significance of differences between groups
        Uses Two-Proportion Z-Test for CTR (Click-Through Rate)
        
        Statistical Method:
        - Null Hypothesis (H₀): CTR_treatment = CTR_control (no difference)
        - Alternative Hypothesis (H₁): CTR_treatment ≠ CTR_control (two-tailed test)
        - Test Statistic: Z-score from two-proportion test
        - Significance Level: α = 0.05 (95% confidence)
        - Decision: Reject H₀ if p-value < α
        
        Args:
            control: Control group metrics
            treatment: Treatment group metrics
            
        Returns:
            Dict with significance test results including:
            - significant: Boolean indicating if difference is statistically significant
            - p_value: Probability of observing this difference by chance
            - z_score: Standardized test statistic
            - effect_size: Relative effect size (percentage change)
            - confidence_level: Confidence level used (0.95)
        """
        try:
            # Check if we have enough data (minimum sample size requirement)
            if control['impressions'] < self.min_sample_size or treatment['impressions'] < self.min_sample_size:
                return {
                    'significant': False,
                    'reason': f'Insufficient sample size (need {self.min_sample_size} impressions per group)',
                    'p_value': None,
                    'z_score': None,
                    'effect_size': None,
                    'confidence_level': self.confidence_level,
                    'control_sample': control['impressions'],
                    'treatment_sample': treatment['impressions']
                }
            
            # Sample sizes
            n1 = control['impressions']
            n2 = treatment['impressions']
            
            # Success counts (clicks)
            x1 = control['clicks']
            x2 = treatment['clicks']
            
            # Sample proportions
            p1 = x1 / n1 if n1 > 0 else 0
            p2 = x2 / n2 if n2 > 0 else 0
            
            # Pooled proportion (under null hypothesis of no difference)
            p_pool = (x1 + x2) / (n1 + n2)
            
            # Standard error of the difference
            se = np.sqrt(p_pool * (1 - p_pool) * (1/n1 + 1/n2))
            
            # Z-score (test statistic)
            z = (p2 - p1) / se if se > 0 else 0
            
            # P-value (two-tailed test)
            # We use two-tailed because we care about ANY difference (better or worse)
            p_value = 2 * (1 - stats.norm.cdf(abs(z)))
            
            # Decision: Is the result statistically significant?
            is_significant = p_value < (1 - self.confidence_level)
            
            # Effect size (relative percentage change)
            # This tells us HOW MUCH better/worse treatment is vs control
            effect_size = abs(p2 - p1) / p1 if p1 > 0 else 0
            
            # Confidence interval for the difference
            margin_of_error = 1.96 * se  # 95% confidence
            ci_lower = (p2 - p1) - margin_of_error
            ci_upper = (p2 - p1) + margin_of_error
            
            return {
                'significant': is_significant,
                'p_value': round(p_value, 4),
                'z_score': round(z, 3),
                'effect_size': round(effect_size, 3),
                'confidence_level': self.confidence_level,
                'control_ctr': round(p1 * 100, 2),
                'treatment_ctr': round(p2 * 100, 2),
                'difference': round((p2 - p1) * 100, 2),  # Percentage point difference
                'relative_change': round(effect_size * 100, 1),  # Percentage change
                'confidence_interval': [round(ci_lower * 100, 2), round(ci_upper * 100, 2)],
                'interpretation': self._interpret_result(is_significant, effect_size, p2, p1)
            }
            
        except Exception as e:
            self.logger.error(f"Error testing significance: {e}")
            return {
                'significant': False,
                'reason': f'Error in calculation: {str(e)}',
                'p_value': None
            }
    
    def _interpret_result(self, is_significant: bool, effect_size: float, p2: float, p1: float) -> str:
        """Generate human-readable interpretation of statistical test"""
        if not is_significant:
            return "No statistically significant difference detected. Continue testing or conclude both variants perform similarly."
        
        winner = "Treatment (RL)" if p2 > p1 else "Control (Baseline)"
        magnitude = "strong" if effect_size > 0.2 else "moderate" if effect_size > 0.1 else "modest"
        
        return f"{winner} shows a {magnitude} and statistically significant improvement ({effect_size*100:.1f}% relative increase)."
    
    def _determine_winner(self, control: Dict, treatment: Dict, significance: Dict) -> Optional[str]:
        """
        Determine which group is winning based on metrics
        """
        # Need significant difference
        if not significance.get('significant'):
            return None
        
        # Need meaningful effect size
        if significance.get('effect_size', 0) < self.minimum_effect_size:
            return None
        
        # Compare primary metric (CTR)
        if treatment['ctr'] > control['ctr']:
            return 'treatment'
        elif control['ctr'] > treatment['ctr']:
            return 'control'
        
        # If CTR is tied, compare engagement
        if treatment['engagement_rate'] > control['engagement_rate']:
            return 'treatment'
        elif control['engagement_rate'] > treatment['engagement_rate']:
            return 'control'
        
        return None
    
    def should_use_rl(self, user_id: str) -> bool:
        """
        Decide whether to use RL recommendations for a user
        Takes into account A/B test assignment
        
        Args:
            user_id: User ID
            
        Returns:
            True to use RL, False to use baseline
        """
        try:
            # Check if there's an active test
            test_config = self.get_active_test_config()
            
            if not test_config:
                # No active test, use RL by default
                return True
            
            # Get user's group
            group = self.get_user_group(user_id)
            
            # Control group uses baseline, treatment uses RL
            return group == 'treatment'
            
        except Exception as e:
            self.logger.error(f"Error determining RL usage: {e}")
            return True  # Default to RL on error
    
    def end_test_and_rollout_winner(self, test_id: str) -> Dict:
        """
        End the A/B test and rollout the winning variant to all users
        
        Args:
            test_id: Test ID to end
            
        Returns:
            Dict with results and action taken
        """
        try:
            # Calculate final metrics
            metrics = self.calculate_test_metrics(test_id, days=30)
            
            winner = metrics.get('winner')
            
            if not winner:
                return {
                    'success': False,
                    'message': 'No clear winner - test inconclusive',
                    'action': 'maintain_status_quo',
                    'metrics': metrics
                }
            
            # Update test status
            supabase.table('ab_test_configs')\
                .update({
                    'status': 'ended',
                    'winner': winner,
                    'ended_at': datetime.now().isoformat()
                })\
                .eq('id', test_id)\
                .execute()
            
            # Log results
            result_record = {
                'test_id': test_id,
                'winner': winner,
                'control_ctr': metrics['control']['ctr'],
                'treatment_ctr': metrics['treatment']['ctr'],
                'p_value': metrics['significance']['p_value'],
                'effect_size': metrics['significance']['effect_size'],
                'control_users': metrics['control']['user_count'],
                'treatment_users': metrics['treatment']['user_count'],
                'recommendation': 'rollout_' + winner,
                'recorded_at': datetime.now().isoformat()
            }
            
            supabase.table('ab_test_results').insert(result_record).execute()
            
            self.logger.info(f"A/B test ended - Winner: {winner}")
            
            return {
                'success': True,
                'winner': winner,
                'action': f'rollout_{winner}',
                'metrics': metrics,
                'recommendation': 'Use RL for all users' if winner == 'treatment' else 'Use baseline for all users'
            }
            
        except Exception as e:
            self.logger.error(f"Error ending test: {e}")
            return {'success': False, 'error': str(e)}


# Global instance
_ab_test_service = None

def get_ab_test_service() -> ABTestService:
    """Get or create the global A/B test service instance"""
    global _ab_test_service
    if _ab_test_service is None:
        _ab_test_service = ABTestService()
    return _ab_test_service
