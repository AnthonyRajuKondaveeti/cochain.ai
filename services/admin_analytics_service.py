# services/admin_analytics_service.py
"""
Admin Analytics Service for CoChain.ai
Provides comprehensive analytics queries for the admin dashboard
"""
from database.connection import supabase_admin
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import defaultdict
import json
from .logging_service import get_logger

logger = get_logger('admin_analytics')


class AdminAnalyticsService:
    """
    Comprehensive analytics service for admin dashboard
    
    Provides:
    - User engagement metrics (DAU, MAU, retention)
    - Recommendation performance (CTR, position bias)
    - System health (API performance, errors)
    - User behavior analysis (funnels, cohorts)
    - ML-ready data exports
    """
    
    def __init__(self):
        self.logger = logger
    
    # ============================================================================
    # OVERVIEW METRICS - Real-time Dashboard
    # ============================================================================
    
    def get_overview_metrics(self, days: int = 7) -> Dict[str, Any]:
        """
        Get high-level overview metrics for dashboard
        
        Returns:
            - Total users
            - Active users (today, 7d, 30d)
            - Total recommendations served
            - Overall CTR
            - Average session duration
            - Platform health score
        """
        try:
            since_date = (datetime.now() - timedelta(days=days)).isoformat()
            today = datetime.now().date().isoformat()
            
            # Total users
            total_users_result = supabase_admin.table('users').select('id', count='exact').execute()
            total_users = total_users_result.count or 0
            self.logger.info(f"Total users: {total_users}")
            
            # Daily Active Users (today) - based on last_activity, not just login
            dau_result = supabase_admin.table('user_sessions').select('user_id', count='exact')\
                .gte('last_activity', today)\
                .execute()
            dau = len(set([s['user_id'] for s in dau_result.data])) if dau_result.data else 0
            self.logger.info(f"Daily active users: {dau}")
            
            # Weekly Active Users (7 days) - based on last_activity
            week_ago = (datetime.now() - timedelta(days=7)).isoformat()
            wau_result = supabase_admin.table('user_sessions').select('user_id')\
                .gte('last_activity', week_ago)\
                .execute()
            wau = len(set([s['user_id'] for s in wau_result.data])) if wau_result.data else 0
            self.logger.info(f"Weekly active users: {wau}")
            
            # Monthly Active Users (30 days) - based on last_activity
            month_ago = (datetime.now() - timedelta(days=30)).isoformat()
            mau_result = supabase_admin.table('user_sessions').select('user_id')\
                .gte('last_activity', month_ago)\
                .execute()
            mau = len(set([s['user_id'] for s in mau_result.data])) if mau_result.data else 0
            self.logger.info(f"Monthly active users: {mau}")
            
            # Total recommendations served (from recommendation_results)
            total_recs_result = supabase_admin.table('recommendation_results').select('id', count='exact')\
                .gte('created_at', since_date)\
                .execute()
            total_recommendations = total_recs_result.count or 0
            self.logger.info(f"Total recommendations: {total_recommendations}")
            
            # Click-through rate
            try:
                ctr_data = self.get_click_through_rate(days)
                overall_ctr = ctr_data.get('overall_ctr', 0)
            except Exception as e:
                self.logger.error(f"Error getting CTR: {str(e)}")
                overall_ctr = 0
            
            # Average session duration
            try:
                avg_session = self.get_average_session_duration(days)
            except Exception as e:
                self.logger.error(f"Error getting avg session: {str(e)}")
                avg_session = 0
            
            # New users (registered in last 7 days)
            new_users_result = supabase_admin.table('users').select('id', count='exact')\
                .gte('created_at', week_ago)\
                .execute()
            new_users = new_users_result.count or 0
            self.logger.info(f"New users (7d): {new_users}")
            
            return {
                'total_users': total_users,
                'daily_active_users': dau,
                'weekly_active_users': wau,
                'monthly_active_users': mau,
                'new_users_7d': new_users,
                'total_recommendations_served': total_recommendations,
                'overall_ctr': overall_ctr,
                'average_session_duration_minutes': avg_session,
                'dau_mau_ratio': round((dau / mau * 100) if mau > 0 else 0, 2),
                'period_days': days
            }
            
        except Exception as e:
            self.logger.error(f"Error getting overview metrics: {str(e)}")
            return {}
    
    # ============================================================================
    # USER ENGAGEMENT METRICS
    # ============================================================================
    
    def get_daily_active_users_trend(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get DAU trend over time"""
        try:
            since_date = (datetime.now() - timedelta(days=days)).date()
            
            # Get all sessions in the period
            sessions_result = supabase_admin.table('user_sessions')\
                .select('user_id, login_time')\
                .gte('login_time', since_date.isoformat())\
                .execute()
            
            if not sessions_result.data:
                return []
            
            # Count unique users per day
            daily_users = defaultdict(set)
            for session in sessions_result.data:
                login_date = session['login_time'][:10]  # Extract YYYY-MM-DD
                daily_users[login_date].add(session['user_id'])
            
            # Generate trend data
            trend_data = []
            for i in range(days):
                date = (since_date + timedelta(days=i)).isoformat()
                trend_data.append({
                    'date': date,
                    'active_users': len(daily_users.get(date, set()))
                })
            
            return trend_data
            
        except Exception as e:
            self.logger.error(f"Error getting DAU trend: {str(e)}")
            return []
    
    def get_user_retention_cohorts(self) -> Dict[str, Any]:
        """
        Calculate cohort retention rates
        Shows how many users return after their first session
        """
        try:
            # Get all users with their first session date
            users_result = supabase_admin.table('users').select('id, created_at').execute()
            
            if not users_result.data:
                return {}
            
            cohorts = defaultdict(lambda: {'total': 0, 'retained_7d': 0, 'retained_30d': 0})
            
            for user in users_result.data:
                user_id = user['id']
                signup_date = datetime.fromisoformat(user['created_at'].replace('Z', '+00:00'))
                cohort_month = signup_date.strftime('%Y-%m')
                
                cohorts[cohort_month]['total'] += 1
                
                # Check if user had sessions after 7 days
                sessions_7d = supabase_admin.table('user_sessions')\
                    .select('id', count='exact')\
                    .eq('user_id', user_id)\
                    .gte('login_time', (signup_date + timedelta(days=7)).isoformat())\
                    .lte('login_time', (signup_date + timedelta(days=14)).isoformat())\
                    .execute()
                
                if sessions_7d.count and sessions_7d.count > 0:
                    cohorts[cohort_month]['retained_7d'] += 1
                
                # Check if user had sessions after 30 days
                sessions_30d = supabase_admin.table('user_sessions')\
                    .select('id', count='exact')\
                    .eq('user_id', user_id)\
                    .gte('login_time', (signup_date + timedelta(days=30)).isoformat())\
                    .lte('login_time', (signup_date + timedelta(days=37)).isoformat())\
                    .execute()
                
                if sessions_30d.count and sessions_30d.count > 0:
                    cohorts[cohort_month]['retained_30d'] += 1
            
            # Calculate retention rates
            retention_data = []
            for cohort_month, data in sorted(cohorts.items()):
                retention_data.append({
                    'cohort': cohort_month,
                    'total_users': data['total'],
                    'retention_7d_count': data['retained_7d'],
                    'retention_7d_percent': round((data['retained_7d'] / data['total'] * 100) if data['total'] > 0 else 0, 2),
                    'retention_30d_count': data['retained_30d'],
                    'retention_30d_percent': round((data['retained_30d'] / data['total'] * 100) if data['total'] > 0 else 0, 2)
                })
            
            return {
                'cohorts': retention_data,
                'average_7d_retention': round(sum([c['retention_7d_percent'] for c in retention_data]) / len(retention_data) if retention_data else 0, 2),
                'average_30d_retention': round(sum([c['retention_30d_percent'] for c in retention_data]) / len(retention_data) if retention_data else 0, 2)
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating retention cohorts: {str(e)}")
            return {}
    
    def get_average_session_duration(self, days: int = 7) -> float:
        """Get average session duration in minutes"""
        try:
            since_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            sessions_result = supabase_admin.table('user_sessions')\
                .select('total_minutes')\
                .gte('login_time', since_date)\
                .not_.is_('total_minutes', 'null')\
                .execute()
            
            if not sessions_result.data:
                return 0.0
            
            durations = [s['total_minutes'] for s in sessions_result.data if s.get('total_minutes')]
            avg_duration = sum(durations) / len(durations) if durations else 0
            
            return round(avg_duration, 2)
            
        except Exception as e:
            self.logger.error(f"Error calculating average session duration: {str(e)}")
            return 0.0
    
    # ============================================================================
    # RECOMMENDATION PERFORMANCE METRICS
    # ============================================================================
    
    def get_click_through_rate(self, days: int = 7) -> Dict[str, Any]:
        """
        Calculate comprehensive CTR metrics
        
        Returns:
            - Overall CTR
            - CTR by position
            - CTR by domain
            - CTR by complexity
            - CTR trend over time
        """
        try:
            since_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            # Total recommendations shown
            total_recs_result = supabase_admin.table('recommendation_results')\
                .select('id', count='exact')\
                .gte('created_at', since_date)\
                .execute()
            total_recommendations = total_recs_result.count or 0
            
            # Total clicks
            clicks_result = supabase_admin.table('user_interactions')\
                .select('id', count='exact')\
                .eq('interaction_type', 'click')\
                .gte('interaction_time', since_date)\
                .execute()
            total_clicks = clicks_result.count or 0
            
            # Overall CTR
            overall_ctr = round((total_clicks / total_recommendations * 100) if total_recommendations > 0 else 0, 2)
            
            # CTR by position
            ctr_by_position = self.get_position_bias_analysis(days)
            
            # CTR by domain
            ctr_by_domain = self.get_ctr_by_domain(days)
            
            # CTR by complexity
            ctr_by_complexity = self.get_ctr_by_complexity(days)
            
            # Daily CTR trend
            ctr_trend = self.get_ctr_trend(days)
            
            return {
                'overall_ctr': overall_ctr,
                'total_recommendations': total_recommendations,
                'total_clicks': total_clicks,
                'ctr_by_position': ctr_by_position,
                'ctr_by_domain': ctr_by_domain,
                'ctr_by_complexity': ctr_by_complexity,
                'ctr_trend': ctr_trend,
                'period_days': days
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating CTR: {str(e)}")
            return {}
    
    def get_position_bias_analysis(self, days: int = 7) -> List[Dict[str, Any]]:
        """Analyze CTR by recommendation position to detect position bias"""
        try:
            since_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            # Get all recommendations with their positions
            recs_result = supabase_admin.table('recommendation_results')\
                .select('id, rank_position, github_reference_id')\
                .gte('created_at', since_date)\
                .execute()
            
            if not recs_result.data:
                return []
            
            # Get all clicks
            clicks_result = supabase_admin.table('user_interactions')\
                .select('github_reference_id, rank_position')\
                .eq('interaction_type', 'click')\
                .gte('interaction_time', since_date)\
                .execute()
            
            # Count recommendations by position
            position_counts = defaultdict(int)
            for rec in recs_result.data:
                pos = rec.get('rank_position', 0)
                if pos > 0:
                    position_counts[pos] += 1
            
            # Count clicks by position
            position_clicks = defaultdict(int)
            for click in clicks_result.data:
                pos = click.get('rank_position', 0)
                if pos > 0:
                    position_clicks[pos] += 1
            
            # Calculate CTR by position
            position_ctr = []
            for pos in sorted(position_counts.keys()):
                clicks = position_clicks.get(pos, 0)
                total = position_counts[pos]
                ctr = round((clicks / total * 100) if total > 0 else 0, 2)
                
                position_ctr.append({
                    'position': pos,
                    'impressions': total,
                    'clicks': clicks,
                    'ctr': ctr
                })
            
            return position_ctr
            
        except Exception as e:
            self.logger.error(f"Error analyzing position bias: {str(e)}")
            return []
    
    def get_ctr_by_domain(self, days: int = 7) -> List[Dict[str, Any]]:
        """Calculate CTR by project domain"""
        try:
            since_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            # Get recommendations with domain info
            recs_result = supabase_admin.table('recommendation_results')\
                .select('id, github_reference_id, github_references(domain)')\
                .gte('created_at', since_date)\
                .execute()
            
            if not recs_result.data:
                return []
            
            # Count by domain
            domain_counts = defaultdict(int)
            rec_to_domain = {}
            for rec in recs_result.data:
                if rec.get('github_references') and rec['github_references'].get('domain'):
                    domain = rec['github_references']['domain']
                    domain_counts[domain] += 1
                    rec_to_domain[rec['github_reference_id']] = domain
            
            # Get clicks with domain
            clicks_result = supabase_admin.table('user_interactions')\
                .select('github_reference_id')\
                .eq('interaction_type', 'click')\
                .gte('interaction_time', since_date)\
                .execute()
            
            domain_clicks = defaultdict(int)
            for click in clicks_result.data:
                ref_id = click['github_reference_id']
                if ref_id in rec_to_domain:
                    domain_clicks[rec_to_domain[ref_id]] += 1
            
            # Calculate CTR by domain
            domain_ctr = []
            for domain, count in domain_counts.items():
                clicks = domain_clicks.get(domain, 0)
                ctr = round((clicks / count * 100) if count > 0 else 0, 2)
                
                domain_ctr.append({
                    'domain': domain,
                    'impressions': count,
                    'clicks': clicks,
                    'ctr': ctr
                })
            
            # Sort by CTR descending
            domain_ctr.sort(key=lambda x: x['ctr'], reverse=True)
            
            return domain_ctr
            
        except Exception as e:
            self.logger.error(f"Error calculating CTR by domain: {str(e)}")
            return []
    
    def get_ctr_by_complexity(self, days: int = 7) -> List[Dict[str, Any]]:
        """Calculate CTR by complexity level"""
        try:
            since_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            # Get recommendations with complexity info
            recs_result = supabase_admin.table('recommendation_results')\
                .select('id, github_reference_id, github_references(complexity_level)')\
                .gte('created_at', since_date)\
                .execute()
            
            if not recs_result.data:
                return []
            
            # Count by complexity
            complexity_counts = defaultdict(int)
            rec_to_complexity = {}
            for rec in recs_result.data:
                if rec.get('github_references') and rec['github_references'].get('complexity_level'):
                    complexity = rec['github_references']['complexity_level']
                    complexity_counts[complexity] += 1
                    rec_to_complexity[rec['github_reference_id']] = complexity
            
            # Get clicks
            clicks_result = supabase_admin.table('user_interactions')\
                .select('github_reference_id')\
                .eq('interaction_type', 'click')\
                .gte('interaction_time', since_date)\
                .execute()
            
            complexity_clicks = defaultdict(int)
            for click in clicks_result.data:
                ref_id = click['github_reference_id']
                if ref_id in rec_to_complexity:
                    complexity_clicks[rec_to_complexity[ref_id]] += 1
            
            # Calculate CTR
            complexity_ctr = []
            for complexity, count in complexity_counts.items():
                clicks = complexity_clicks.get(complexity, 0)
                ctr = round((clicks / count * 100) if count > 0 else 0, 2)
                
                complexity_ctr.append({
                    'complexity': complexity,
                    'impressions': count,
                    'clicks': clicks,
                    'ctr': ctr
                })
            
            # Sort by complexity level
            level_order = {'beginner': 1, 'intermediate': 2, 'advanced': 3}
            complexity_ctr.sort(key=lambda x: level_order.get(x['complexity'].lower(), 99))
            
            return complexity_ctr
            
        except Exception as e:
            self.logger.error(f"Error calculating CTR by complexity: {str(e)}")
            return []
    
    def get_ctr_trend(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get daily CTR trend"""
        try:
            since_date = (datetime.now() - timedelta(days=days)).date()
            
            # Get recommendations by day
            recs_result = supabase_admin.table('recommendation_results')\
                .select('id, created_at')\
                .gte('created_at', since_date.isoformat())\
                .execute()
            
            daily_recs = defaultdict(int)
            for rec in recs_result.data:
                date = rec['created_at'][:10]
                daily_recs[date] += 1
            
            # Get clicks by day
            clicks_result = supabase_admin.table('user_interactions')\
                .select('id, interaction_time')\
                .eq('interaction_type', 'click')\
                .gte('interaction_time', since_date.isoformat())\
                .execute()
            
            daily_clicks = defaultdict(int)
            for click in clicks_result.data:
                date = click['interaction_time'][:10]
                daily_clicks[date] += 1
            
            # Calculate daily CTR
            ctr_trend = []
            for i in range(days):
                date = (since_date + timedelta(days=i)).isoformat()
                recs = daily_recs.get(date, 0)
                clicks = daily_clicks.get(date, 0)
                ctr = round((clicks / recs * 100) if recs > 0 else 0, 2)
                
                ctr_trend.append({
                    'date': date,
                    'recommendations': recs,
                    'clicks': clicks,
                    'ctr': ctr
                })
            
            return ctr_trend
            
        except Exception as e:
            self.logger.error(f"Error calculating CTR trend: {str(e)}")
            return []
    
    # ============================================================================
    # USER BEHAVIOR ANALYSIS
    # ============================================================================
    
    def get_engagement_funnel(self, days: int = 7) -> Dict[str, Any]:
        """
        Calculate user engagement funnel:
        View → Click → Bookmark → Feedback
        """
        try:
            since_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            # Stage 1: Recommendations shown (impressions)
            impressions_result = supabase_admin.table('recommendation_results')\
                .select('id', count='exact')\
                .gte('created_at', since_date)\
                .execute()
            impressions = impressions_result.count or 0
            
            # Stage 2: Clicks
            clicks_result = supabase_admin.table('user_interactions')\
                .select('id', count='exact')\
                .eq('interaction_type', 'click')\
                .gte('interaction_time', since_date)\
                .execute()
            clicks = clicks_result.count or 0
            
            # Stage 3: Bookmarks
            bookmarks_result = supabase_admin.table('user_bookmarks')\
                .select('id', count='exact')\
                .gte('created_at', since_date)\
                .execute()
            bookmarks = bookmarks_result.count or 0
            
            # Stage 4: Feedback
            feedback_result = supabase_admin.table('user_feedback')\
                .select('id', count='exact')\
                .gte('created_at', since_date)\
                .execute()
            feedback = feedback_result.count or 0
            
            # Calculate conversion rates
            click_rate = round((clicks / impressions * 100) if impressions > 0 else 0, 2)
            bookmark_rate = round((bookmarks / clicks * 100) if clicks > 0 else 0, 2)
            feedback_rate = round((feedback / bookmarks * 100) if bookmarks > 0 else 0, 2)
            overall_conversion = round((feedback / impressions * 100) if impressions > 0 else 0, 2)
            
            return {
                'funnel': [
                    {'stage': 'Impressions', 'count': impressions, 'rate': 100.0},
                    {'stage': 'Clicks', 'count': clicks, 'rate': click_rate},
                    {'stage': 'Bookmarks', 'count': bookmarks, 'rate': bookmark_rate},
                    {'stage': 'Feedback', 'count': feedback, 'rate': feedback_rate}
                ],
                'conversion_rates': {
                    'impression_to_click': click_rate,
                    'click_to_bookmark': bookmark_rate,
                    'bookmark_to_feedback': feedback_rate,
                    'overall_conversion': overall_conversion
                },
                'period_days': days
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating engagement funnel: {str(e)}")
            return {}
    
    def get_top_performing_projects(self, days: int = 7, limit: int = 10) -> List[Dict[str, Any]]:
        """Get most clicked/engaged projects"""
        try:
            since_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            # Get click counts by project
            clicks_result = supabase_admin.table('user_interactions')\
                .select('github_reference_id')\
                .eq('interaction_type', 'click')\
                .gte('interaction_time', since_date)\
                .execute()
            
            if not clicks_result.data:
                return []
            
            # Count clicks per project
            project_clicks = defaultdict(int)
            for click in clicks_result.data:
                project_clicks[click['github_reference_id']] += 1
            
            # Get top projects
            top_project_ids = sorted(project_clicks.items(), key=lambda x: x[1], reverse=True)[:limit]
            
            # Get project details
            project_ids = [p[0] for p in top_project_ids]
            projects_result = supabase_admin.table('github_references')\
                .select('*')\
                .in_('id', project_ids)\
                .execute()
            
            # Combine with click counts
            project_details = {p['id']: p for p in projects_result.data}
            
            top_projects = []
            for project_id, clicks in top_project_ids:
                if project_id in project_details:
                    project = project_details[project_id].copy()
                    project['clicks'] = clicks
                    
                    # Get bookmark count
                    bookmarks = supabase_admin.table('user_bookmarks')\
                        .select('id', count='exact')\
                        .eq('github_reference_id', project_id)\
                        .execute()
                    project['bookmarks'] = bookmarks.count or 0
                    
                    top_projects.append(project)
            
            return top_projects
            
        except Exception as e:
            self.logger.error(f"Error getting top performing projects: {str(e)}")
            return []
    
    # ============================================================================
    # SYSTEM HEALTH METRICS
    # ============================================================================
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get system health metrics from performance monitor"""
        try:
            from services.performance_monitor import get_performance_monitor
            
            perf_monitor = get_performance_monitor()
            summary = perf_monitor.get_performance_summary()
            
            # Determine health status
            api_stats = summary.get('api_stats', {})
            avg_response_time = api_stats.get('avg_ms', 0)
            
            if avg_response_time < 200:
                health_status = 'excellent'
            elif avg_response_time < 500:
                health_status = 'good'
            elif avg_response_time < 1000:
                health_status = 'fair'
            else:
                health_status = 'poor'
            
            return {
                'status': health_status,
                'api_performance': api_stats,
                'cache_performance': summary.get('cache_stats', {}),
                'system_resources': summary.get('system_metrics', {}),
                'timestamp': summary.get('timestamp')
            }
            
        except Exception as e:
            self.logger.error(f"Error getting system health: {str(e)}")
            return {'status': 'unknown', 'error': str(e)}
    
    # ============================================================================
    # EXPORT FUNCTIONS FOR ML
    # ============================================================================
    
    def export_interaction_data(self, days: int = 30, format: str = 'json') -> Any:
        """
        Export interaction data for ML training
        
        Args:
            days: Number of days to export
            format: 'json' or 'csv'
        
        Returns:
            Structured data ready for ML pipelines
        """
        try:
            since_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            # Get all interactions with context
            interactions = supabase_admin.table('user_interactions')\
                .select('''
                    *,
                    user_queries(project_idea, complexity_level),
                    github_references(title, domain, complexity_level, required_skills)
                ''')\
                .gte('interaction_time', since_date)\
                .execute()
            
            if format == 'json':
                return json.dumps(interactions.data, indent=2)
            elif format == 'csv':
                # Convert to CSV format
                import csv
                import io
                
                output = io.StringIO()
                if interactions.data:
                    writer = csv.DictWriter(output, fieldnames=interactions.data[0].keys())
                    writer.writeheader()
                    writer.writerows(interactions.data)
                
                return output.getvalue()
            
            return interactions.data
            
        except Exception as e:
            self.logger.error(f"Error exporting interaction data: {str(e)}")
            return None
    
    def get_recommendation_quality_metrics(self, days: int = 7) -> Dict[str, Any]:
        """
        Calculate recommendation quality metrics for ML evaluation
        
        Returns:
            - Precision@K
            - Average similarity of clicked items
            - Diversity score
            - Serendipity score
        """
        try:
            since_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            # Get clicked recommendations with similarity scores
            clicks_result = supabase_admin.table('user_interactions')\
                .select('similarity_score, rank_position')\
                .eq('interaction_type', 'click')\
                .gte('interaction_time', since_date)\
                .execute()
            
            if not clicks_result.data:
                return {}
            
            # Calculate metrics
            similarities = [c['similarity_score'] for c in clicks_result.data if c.get('similarity_score')]
            positions = [c['rank_position'] for c in clicks_result.data if c.get('rank_position')]
            
            avg_clicked_similarity = sum(similarities) / len(similarities) if similarities else 0
            avg_click_position = sum(positions) / len(positions) if positions else 0
            
            # Precision@5 (clicks in top 5 positions)
            clicks_top_5 = sum(1 for p in positions if p <= 5)
            precision_at_5 = round((clicks_top_5 / len(positions) * 100) if positions else 0, 2)
            
            # Precision@10
            clicks_top_10 = sum(1 for p in positions if p <= 10)
            precision_at_10 = round((clicks_top_10 / len(positions) * 100) if positions else 0, 2)
            
            return {
                'average_clicked_similarity': round(avg_clicked_similarity, 4),
                'average_click_position': round(avg_click_position, 2),
                'precision_at_5': precision_at_5,
                'precision_at_10': precision_at_10,
                'total_clicks_analyzed': len(positions),
                'period_days': days
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating recommendation quality: {str(e)}")
            return {}
    
    # ============================================================================
    # COMPREHENSIVE DASHBOARD DATA
    # ============================================================================
    
    def get_complete_dashboard_data(self, days: int = 7) -> Dict[str, Any]:
        """
        Get all analytics data in one call for dashboard
        Optimized to minimize database queries
        """
        try:
            self.logger.info(f"Generating complete dashboard data for last {days} days")
            
            dashboard_data = {
                'generated_at': datetime.now().isoformat(),
                'period_days': days,
                
                # Overview metrics
                'overview': self.get_overview_metrics(days),
                
                # User engagement
                'engagement': {
                    'dau_trend': self.get_daily_active_users_trend(days),
                    'retention': self.get_user_retention_cohorts(),
                    'funnel': self.get_engagement_funnel(days)
                },
                
                # Recommendation performance
                'recommendations': {
                    'ctr_analysis': self.get_click_through_rate(days),
                    'quality_metrics': self.get_recommendation_quality_metrics(days),
                    'top_projects': self.get_top_performing_projects(days, 10)
                },
                
                # System health
                'system': self.get_system_health()
            }
            
            self.logger.info("Dashboard data generated successfully")
            return dashboard_data
            
        except Exception as e:
            self.logger.error(f"Error generating complete dashboard data: {str(e)}")
            return {'error': str(e)}


# Global analytics service instance
_analytics_service = None

def get_analytics_service():
    """Get or create the global analytics service instance"""
    global _analytics_service
    if _analytics_service is None:
        _analytics_service = AdminAnalyticsService()
    return _analytics_service


# Testing
if __name__ == '__main__':
    analytics = get_analytics_service()
    
    print("Testing Admin Analytics Service...")
    print("\n1. Overview Metrics:")
    overview = analytics.get_overview_metrics(7)
    for key, value in overview.items():
        print(f"   {key}: {value}")
    
    print("\n2. Click-Through Rate:")
    ctr_data = analytics.get_click_through_rate(7)
    print(f"   Overall CTR: {ctr_data.get('overall_ctr', 0)}%")
    print(f"   Total Recommendations: {ctr_data.get('total_recommendations', 0)}")
    print(f"   Total Clicks: {ctr_data.get('total_clicks', 0)}")
    
    print("\n3. Engagement Funnel:")
    funnel = analytics.get_engagement_funnel(7)
    if funnel.get('funnel'):
        for stage in funnel['funnel']:
            print(f"   {stage['stage']}: {stage['count']} ({stage['rate']}%)")
    
    print("\n✅ Analytics service test complete!")
