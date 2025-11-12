# services/analytics_service.py
"""
Analytics Service for Recommendation System
Tracks user interactions and provides model evaluation metrics
"""
from database.connection import supabase, supabase_admin
from datetime import datetime, timedelta
import uuid

class RecommendationAnalytics:
    def __init__(self):
        pass

    def track_recommendation_results(self, user_query_id, recommendations):
        """Store recommendation results for analytics"""
        try:
            results_data = []
            for i, rec in enumerate(recommendations, 1):
                result_data = {
                    'user_query_id': user_query_id,
                    'github_reference_id': rec['id'],
                    'similarity_score': rec.get('similarity', 0),
                    'rank_position': i
                }
                results_data.append(result_data)
            
            if results_data:
                result = supabase.table('recommendation_results').insert(results_data).execute()
                return [r['id'] for r in result.data] if result.data else []
            
        except Exception as e:
            print(f"Error storing recommendation results: {e}")
            return []

    def track_user_interaction(self, user_query_id, github_reference_id, interaction_type, 
                             rank_position=None, similarity_score=None, session_id=None, 
                             user_agent=None, additional_data=None):
        """Track user interaction (click, view, etc.)"""
        try:
            interaction_data = {
                'user_query_id': user_query_id,
                'github_reference_id': github_reference_id,
                'interaction_type': interaction_type,
                'rank_position': rank_position,
                'similarity_score': similarity_score,
                'session_id': session_id,
                'user_agent': user_agent,
                'additional_data': additional_data
            }
            
            # Find the recommendation_result_id if available
            if user_query_id and github_reference_id:
                rec_result = supabase.table('recommendation_results')\
                    .select('id')\
                    .eq('user_query_id', user_query_id)\
                    .eq('github_reference_id', github_reference_id)\
                    .execute()
                
                if rec_result.data:
                    interaction_data['recommendation_result_id'] = rec_result.data[0]['id']
            
            result = supabase.table('user_interactions').insert(interaction_data).execute()
            return result.data[0]['id'] if result.data else None
            
        except Exception as e:
            print(f"Error tracking user interaction: {e}")
            return None

    def track_user_feedback(self, user_query_id, github_reference_id, rating=None, 
                          feedback_text=None, is_relevant=None, is_helpful=None):
        """Track explicit user feedback"""
        try:
            feedback_data = {
                'user_query_id': user_query_id,
                'github_reference_id': github_reference_id,
                'rating': rating,
                'feedback_text': feedback_text,
                'is_relevant': is_relevant,
                'is_helpful': is_helpful
            }
            
            # Find the recommendation_result_id if available
            if user_query_id and github_reference_id:
                rec_result = supabase.table('recommendation_results')\
                    .select('id')\
                    .eq('user_query_id', user_query_id)\
                    .eq('github_reference_id', github_reference_id)\
                    .execute()
                
                if rec_result.data:
                    feedback_data['recommendation_result_id'] = rec_result.data[0]['id']
            
            result = supabase.table('user_feedback').insert(feedback_data).execute()
            return result.data[0]['id'] if result.data else None
            
        except Exception as e:
            print(f"Error tracking user feedback: {e}")
            return None

    def get_click_through_rate(self, days=30):
        """Calculate click-through rate for recommendations"""
        try:
            # Get total recommendations in the period
            since_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            total_recommendations = supabase.table('recommendation_results')\
                .select('id', count='exact')\
                .gte('created_at', since_date)\
                .execute()
            
            total_count = total_recommendations.count or 0
            
            if total_count == 0:
                return 0.0
            
            # Get clicked recommendations
            clicked_recommendations = supabase.table('user_interactions')\
                .select('recommendation_result_id', count='exact')\
                .eq('interaction_type', 'click')\
                .gte('interaction_time', since_date)\
                .execute()
            
            clicked_count = clicked_recommendations.count or 0
            
            ctr = (clicked_count / total_count) * 100
            return round(ctr, 2)
            
        except Exception as e:
            print(f"Error calculating CTR: {e}")
            return 0.0

    def get_position_bias_analysis(self, days=30):
        """Analyze click patterns by position to detect position bias"""
        try:
            since_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            # Get clicks by position
            position_clicks = supabase.table('user_interactions')\
                .select('rank_position')\
                .eq('interaction_type', 'click')\
                .gte('interaction_time', since_date)\
                .execute()
            
            if not position_clicks.data:
                return {}
            
            # Count clicks per position
            position_counts = {}
            for interaction in position_clicks.data:
                pos = interaction.get('rank_position')
                if pos:
                    position_counts[pos] = position_counts.get(pos, 0) + 1
            
            # Get total recommendations per position
            total_by_position = {}
            recommendations = supabase.table('recommendation_results')\
                .select('rank_position')\
                .gte('created_at', since_date)\
                .execute()
            
            for rec in recommendations.data:
                pos = rec.get('rank_position')
                if pos:
                    total_by_position[pos] = total_by_position.get(pos, 0) + 1
            
            # Calculate CTR by position
            position_ctr = {}
            for pos in total_by_position:
                clicks = position_counts.get(pos, 0)
                total = total_by_position[pos]
                ctr = (clicks / total) * 100 if total > 0 else 0
                position_ctr[pos] = round(ctr, 2)
            
            return position_ctr
            
        except Exception as e:
            print(f"Error analyzing position bias: {e}")
            return {}

    def get_recommendation_quality_metrics(self, days=30):
        """Calculate recommendation quality metrics"""
        try:
            since_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            # Get average similarity scores of clicked vs non-clicked recommendations
            clicked_similarities = supabase.table('user_interactions')\
                .select('similarity_score')\
                .eq('interaction_type', 'click')\
                .gte('interaction_time', since_date)\
                .execute()
            
            clicked_scores = [i.get('similarity_score', 0) for i in clicked_similarities.data if i.get('similarity_score')]
            avg_clicked_similarity = sum(clicked_scores) / len(clicked_scores) if clicked_scores else 0
            
            # Get all recommendation similarities
            all_similarities = supabase.table('recommendation_results')\
                .select('similarity_score')\
                .gte('created_at', since_date)\
                .execute()
            
            all_scores = [r.get('similarity_score', 0) for r in all_similarities.data if r.get('similarity_score')]
            avg_all_similarity = sum(all_scores) / len(all_scores) if all_scores else 0
            
            # Get explicit feedback metrics
            feedback = supabase.table('user_feedback')\
                .select('rating', 'is_relevant', 'is_helpful')\
                .gte('created_at', since_date)\
                .execute()
            
            feedback_metrics = {
                'avg_rating': 0,
                'relevance_rate': 0,
                'helpfulness_rate': 0
            }
            
            if feedback.data:
                ratings = [f.get('rating') for f in feedback.data if f.get('rating')]
                relevance = [f.get('is_relevant') for f in feedback.data if f.get('is_relevant') is not None]
                helpful = [f.get('is_helpful') for f in feedback.data if f.get('is_helpful') is not None]
                
                if ratings:
                    feedback_metrics['avg_rating'] = round(sum(ratings) / len(ratings), 2)
                if relevance:
                    feedback_metrics['relevance_rate'] = round((sum(relevance) / len(relevance)) * 100, 2)
                if helpful:
                    feedback_metrics['helpfulness_rate'] = round((sum(helpful) / len(helpful)) * 100, 2)
            
            return {
                'avg_clicked_similarity': round(avg_clicked_similarity, 4),
                'avg_all_similarity': round(avg_all_similarity, 4),
                'similarity_lift': round(avg_clicked_similarity - avg_all_similarity, 4),
                'feedback_metrics': feedback_metrics
            }
            
        except Exception as e:
            print(f"Error calculating quality metrics: {e}")
            return {}

    def get_popular_projects(self, days=30, limit=10):
        """Get most clicked/popular project recommendations"""
        try:
            since_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            # Get projects with most clicks
            popular_projects = supabase.table('user_interactions')\
                .select('github_reference_id')\
                .eq('interaction_type', 'click')\
                .gte('interaction_time', since_date)\
                .execute()
            
            if not popular_projects.data:
                return []
            
            # Count clicks per project
            project_clicks = {}
            for interaction in popular_projects.data:
                project_id = interaction.get('github_reference_id')
                if project_id:
                    project_clicks[project_id] = project_clicks.get(project_id, 0) + 1
            
            # Sort by click count
            sorted_projects = sorted(project_clicks.items(), key=lambda x: x[1], reverse=True)[:limit]
            
            # Get project details
            project_ids = [p[0] for p in sorted_projects]
            projects = supabase.table('github_references')\
                .select('*')\
                .in_('id', project_ids)\
                .execute()
            
            # Combine with click counts
            project_details = {}
            for project in projects.data:
                project_details[project['id']] = project
            
            popular_list = []
            for project_id, click_count in sorted_projects:
                if project_id in project_details:
                    project = project_details[project_id].copy()
                    project['click_count'] = click_count
                    popular_list.append(project)
            
            return popular_list
            
        except Exception as e:
            print(f"Error getting popular projects: {e}")
            return []

    def get_analytics_summary(self, days=30):
        """Get comprehensive analytics summary"""
        try:
            summary = {
                'period_days': days,
                'click_through_rate': self.get_click_through_rate(days),
                'position_bias': self.get_position_bias_analysis(days),
                'quality_metrics': self.get_recommendation_quality_metrics(days),
                'popular_projects': self.get_popular_projects(days, 5),
                'generated_at': datetime.now().isoformat()
            }
            
            # Add total counts
            since_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            total_queries = supabase.table('user_queries')\
                .select('id', count='exact')\
                .gte('created_at', since_date)\
                .execute()
            
            total_interactions = supabase.table('user_interactions')\
                .select('id', count='exact')\
                .gte('interaction_time', since_date)\
                .execute()
            
            summary['total_queries'] = total_queries.count or 0
            summary['total_interactions'] = total_interactions.count or 0
            
            return summary
            
        except Exception as e:
            print(f"Error generating analytics summary: {e}")
            return {'error': str(e)}