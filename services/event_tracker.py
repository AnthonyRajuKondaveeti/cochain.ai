# services/event_tracker.py
"""
Event Tracking Service for CoChain.ai
Tracks all user interactions and stores them in database for analytics
"""
from database.connection import supabase
from .logging_service import get_logger
from datetime import datetime
import uuid
from typing import Optional, Dict, Any

logger = get_logger('event_tracker')


class EventTracker:
    """
    Tracks user events and interactions across the platform
    
    Event Types:
    - page_view: User views a page
    - recommendation_impression: Recommendation shown to user
    - recommendation_click: User clicks on a recommendation
    - bookmark_add: User bookmarks a project
    - bookmark_remove: User removes a bookmark
    - feedback_submit: User submits feedback
    - profile_update: User updates their profile
    - session_start: New session started
    - session_end: Session ended
    """
    
    def __init__(self):
        self.logger = logger
    
    def track_event(self, event_type: str, user_id: Optional[str] = None, 
                   session_id: Optional[str] = None, **kwargs) -> Optional[str]:
        """
        Generic event tracking method
        
        Args:
            event_type: Type of event (e.g., 'page_view', 'click')
            user_id: User ID if authenticated
            session_id: Session ID
            **kwargs: Additional event data
        
        Returns:
            Event ID if successful, None otherwise
        """
        try:
            event_data = {
                'event_type': event_type,
                'user_id': user_id,
                'session_id': session_id,
                'event_data': kwargs,
                'created_at': datetime.utcnow().isoformat()
            }
            
            self.logger.info(f"Event tracked: {event_type}", 
                           extra={'user_id': user_id, 'session_id': session_id})
            
            return str(uuid.uuid4())
            
        except Exception as e:
            self.logger.error(f"Failed to track event {event_type}: {str(e)}")
            return None
    
    def track_page_view(self, page_name: str, user_id: Optional[str] = None,
                       session_id: Optional[str] = None, referrer: Optional[str] = None,
                       **kwargs) -> Optional[str]:
        """Track page view and update session"""
        # Update session activity and increment pages_visited
        if session_id:
            try:
                # Get current pages_visited count
                session_result = supabase.table('user_sessions')\
                    .select('pages_visited')\
                    .eq('session_id', session_id)\
                    .execute()
                
                if session_result.data:
                    current_pages = session_result.data[0].get('pages_visited', 0)
                    
                    # Update last_activity and increment pages_visited
                    supabase.table('user_sessions').update({
                        'last_activity': datetime.utcnow().isoformat(),
                        'pages_visited': current_pages + 1
                    }).eq('session_id', session_id).execute()
            except Exception as e:
                self.logger.error(f"Failed to update session page count: {str(e)}")
        
        return self.track_event(
            'page_view',
            user_id=user_id,
            session_id=session_id,
            page_name=page_name,
            referrer=referrer,
            **kwargs
        )
    
    def track_recommendation_impression(self, user_id: str, recommendations: list,
                                      session_id: Optional[str] = None,
                                      query_id: Optional[str] = None,
                                      source: str = 'dashboard') -> bool:
        """
        Track when recommendations are shown to user
        
        Args:
            user_id: User ID
            recommendations: List of recommendation objects
            session_id: Session ID
            query_id: User query ID if from search
            source: Where recommendations were shown (dashboard, explore, etc.)
        """
        try:
            # First, store recommendations in recommendation_results table for analytics
            for idx, rec in enumerate(recommendations, 1):
                try:
                    rec_data = {
                        'github_reference_id': rec.get('id'),
                        'similarity_score': rec.get('similarity', 0.0),
                        'rank_position': idx
                    }
                    
                    # Add user_query_id if available
                    if query_id:
                        rec_data['user_query_id'] = query_id
                    
                    # Store in recommendation_results table
                    supabase.table('recommendation_results').insert(rec_data).execute()
                    
                except Exception as e:
                    self.logger.warning(f"Failed to store recommendation result: {str(e)}")
            
            # Also track as events for detailed logging
            for idx, rec in enumerate(recommendations, 1):
                self.track_event(
                    'recommendation_impression',
                    user_id=user_id,
                    session_id=session_id,
                    github_reference_id=rec.get('id'),
                    rank_position=idx,
                    similarity_score=rec.get('similarity', 0),
                    query_id=query_id,
                    source=source,
                    project_title=rec.get('title'),
                    project_domain=rec.get('domain')
                )
            
            self.logger.info(
                f"Tracked {len(recommendations)} recommendation impressions for user {user_id}",
                extra={'user_id': user_id, 'session_id': session_id}
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to track recommendation impressions: {str(e)}")
            return False
    
    def track_recommendation_click(self, user_id: str, github_reference_id: str,
                                  rank_position: int, similarity_score: float,
                                  session_id: Optional[str] = None,
                                  query_id: Optional[str] = None,
                                  user_agent: Optional[str] = None) -> Optional[str]:
        """Track when user clicks on a recommendation"""
        try:
            # Try to find the recommendation_result_id from the most recent impression
            rec_result_id = None
            try:
                # Get the most recent recommendation result for this project
                result = supabase.table('recommendation_results')\
                    .select('id')\
                    .eq('github_reference_id', github_reference_id)\
                    .order('created_at', desc=True)\
                    .limit(1)\
                    .execute()
                
                if result.data and len(result.data) > 0:
                    rec_result_id = result.data[0]['id']
                    self.logger.info(f"Found recommendation_result_id: {rec_result_id}")
            except Exception as e:
                self.logger.warning(f"Could not find recommendation_result_id: {str(e)}")
            
            # Store in user_interactions table
            interaction_data = {
                'user_id': user_id,
                'github_reference_id': github_reference_id,
                'interaction_type': 'click',
                'rank_position': rank_position,
                'similarity_score': similarity_score,
                'session_id': session_id,
                'user_agent': user_agent
            }
            
            if query_id:
                interaction_data['user_query_id'] = query_id
            
            if rec_result_id:
                interaction_data['recommendation_result_id'] = rec_result_id
            
            self.logger.info(f"Attempting to track click for user {user_id}, project {github_reference_id}, position {rank_position}")
            result = supabase.table('user_interactions').insert(interaction_data).execute()
            
            if result.data:
                interaction_id = result.data[0]['id']
                self.logger.info(
                    f"✅ User {user_id} clicked recommendation at position {rank_position} - Interaction ID: {interaction_id}",
                    extra={'user_id': user_id, 'session_id': session_id, 'interaction_id': interaction_id}
                )
                return interaction_id
            else:
                self.logger.error(f"❌ Failed to insert click interaction - no data returned")
                return None
            
        except Exception as e:
            self.logger.error(f"❌ Failed to track recommendation click: {str(e)}", exc_info=True)
            return None
    
    def track_recommendation_hover(self, user_id: str, github_reference_id: str,
                                  hover_duration_ms: int, session_id: Optional[str] = None) -> bool:
        """Track when user hovers over a recommendation"""
        try:
            self.track_event(
                'recommendation_hover',
                user_id=user_id,
                session_id=session_id,
                github_reference_id=github_reference_id,
                hover_duration_ms=hover_duration_ms
            )
            return True
        except Exception as e:
            self.logger.error(f"Failed to track hover: {str(e)}")
            return False
    
    def track_bookmark_action(self, user_id: str, github_reference_id: str,
                            action: str, session_id: Optional[str] = None,
                            notes: Optional[str] = None) -> bool:
        """
        Track bookmark add/remove
        
        Args:
            user_id: User ID
            github_reference_id: Project ID
            action: 'add' or 'remove'
            session_id: Session ID
            notes: Bookmark notes if adding
        """
        try:
            # Store in user_interactions table
            interaction_data = {
                'user_id': user_id,
                'github_reference_id': github_reference_id,
                'interaction_type': f'bookmark_{action}',
                'session_id': session_id,
                'additional_data': {'notes': notes} if notes else None
            }
            
            self.logger.info(f"Attempting to track bookmark_{action} for user {user_id}, project {github_reference_id}")
            result = supabase.table('user_interactions').insert(interaction_data).execute()
            
            if result.data:
                self.logger.info(
                    f"✅ User {user_id} {action}ed bookmark - Interaction ID: {result.data[0].get('id')}",
                    extra={'user_id': user_id, 'session_id': session_id}
                )
                return True
            else:
                self.logger.error(f"❌ Failed to insert bookmark interaction - no data returned")
                return False
            
        except Exception as e:
            self.logger.error(f"❌ Failed to track bookmark action: {str(e)}", exc_info=True)
            return False
    
    def track_feedback(self, user_id: str, github_reference_id: str,
                      rating: Optional[int] = None, feedback_text: Optional[str] = None,
                      is_relevant: Optional[bool] = None, is_helpful: Optional[bool] = None,
                      query_id: Optional[str] = None, session_id: Optional[str] = None) -> Optional[str]:
        """Track user feedback on a recommendation"""
        try:
            feedback_data = {
                'user_id': user_id,
                'github_reference_id': github_reference_id,
                'rating': rating,
                'feedback_text': feedback_text,
                'is_relevant': is_relevant,
                'is_helpful': is_helpful
            }
            
            if query_id:
                feedback_data['user_query_id'] = query_id
            
            result = supabase.table('user_feedback').insert(feedback_data).execute()
            
            feedback_id = result.data[0]['id'] if result.data else None
            
            self.logger.info(
                f"User {user_id} submitted feedback (rating: {rating})",
                extra={'user_id': user_id, 'session_id': session_id}
            )
            
            return feedback_id
            
        except Exception as e:
            self.logger.error(f"Failed to track feedback: {str(e)}")
            return None
    
    def track_session_start(self, user_id: str, session_id: str,
                           ip_address: Optional[str] = None,
                           user_agent: Optional[str] = None) -> bool:
        """Track session start"""
        try:
            session_data = {
                'user_id': user_id,
                'session_id': session_id,
                'login_time': datetime.utcnow().isoformat(),
                'last_activity': datetime.utcnow().isoformat()
            }
            
            result = supabase.table('user_sessions').insert(session_data).execute()
            
            self.logger.info(
                f"Session started for user {user_id}",
                extra={'user_id': user_id, 'session_id': session_id, 'ip_address': ip_address}
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to track session start: {str(e)}")
            return False
    
    def track_session_activity(self, session_id: str, activity_type: str,
                              github_viewed: bool = False,
                              live_project_viewed: bool = False,
                              collab_request_sent: bool = False,
                              page_viewed: bool = False) -> bool:
        """Update session activity"""
        try:
            update_data = {
                'last_activity': datetime.utcnow().isoformat()
            }
            
            # Get current session data
            result = supabase.table('user_sessions')\
                .select('github_recommendations_viewed, live_projects_viewed, collaboration_requests_sent, pages_visited')\
                .eq('session_id', session_id)\
                .execute()
            
            if result.data:
                current = result.data[0]
                
                if github_viewed:
                    update_data['github_recommendations_viewed'] = current.get('github_recommendations_viewed', 0) + 1
                
                if live_project_viewed:
                    update_data['live_projects_viewed'] = current.get('live_projects_viewed', 0) + 1
                
                if collab_request_sent:
                    update_data['collaboration_requests_sent'] = current.get('collaboration_requests_sent', 0) + 1
                
                if page_viewed:
                    update_data['pages_visited'] = current.get('pages_visited', 0) + 1
                
                supabase.table('user_sessions').update(update_data).eq('session_id', session_id).execute()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to track session activity: {str(e)}")
            return False
    
    def track_session_end(self, session_id: str) -> bool:
        """Track session end"""
        try:
            # Get session start time
            result = supabase.table('user_sessions').select('login_time').eq('session_id', session_id).execute()
            
            if result.data:
                login_time = datetime.fromisoformat(result.data[0]['login_time'].replace('Z', '+00:00'))
                logout_time = datetime.utcnow()
                duration_minutes = int((logout_time - login_time.replace(tzinfo=None)).total_seconds() / 60)
                
                update_data = {
                    'logout_time': logout_time.isoformat(),
                    'total_minutes': duration_minutes
                }
                
                supabase.table('user_sessions').update(update_data).eq('session_id', session_id).execute()
                
                self.logger.info(
                    f"Session ended (duration: {duration_minutes} minutes)",
                    extra={'session_id': session_id}
                )
                
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Failed to track session end: {str(e)}")
            return False
    
    def track_profile_update(self, user_id: str, updated_fields: list,
                           session_id: Optional[str] = None) -> bool:
        """Track profile update"""
        return self.track_event(
            'profile_update',
            user_id=user_id,
            session_id=session_id,
            updated_fields=updated_fields
        )
    
    def track_project_view(self, user_id: str, project_id: str,
                          view_duration_seconds: int = 0,
                          session_id: Optional[str] = None) -> bool:
        """Track live project view"""
        try:
            view_data = {
                'project_id': project_id,
                'viewer_id': user_id,
                'session_id': session_id,
                'view_duration_seconds': view_duration_seconds,
                'viewed_at': datetime.utcnow().isoformat()
            }
            
            result = supabase.table('project_views').insert(view_data).execute()
            
            # Update project view count
            supabase.rpc('increment_project_views', {'project_id': project_id}).execute()
            
            self.logger.info(
                f"User {user_id} viewed project {project_id}",
                extra={'user_id': user_id, 'session_id': session_id}
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to track project view: {str(e)}")
            return False
    
    def track_collaboration_shown(self, project_id: str, matched_user_id: str,
                                 similarity_score: float, discovery_method: str) -> bool:
        """Track when a collaboration match is shown"""
        try:
            analytics_data = {
                'project_id': project_id,
                'matched_user_id': matched_user_id,
                'similarity_score': similarity_score,
                'discovery_method': discovery_method,
                'viewed': False,
                'shown_at': datetime.utcnow().isoformat()
            }
            
            result = supabase.table('collaboration_analytics').insert(analytics_data).execute()
            
            self.logger.info(
                f"Collaboration match shown: project {project_id} to user {matched_user_id}",
                extra={'matched_user_id': matched_user_id}
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to track collaboration shown: {str(e)}")
            return False

    def track_notification_interaction(self, user_id: str, notification_id: str,
                                     action: str, session_id: Optional[str] = None) -> Optional[str]:
        """Track notification interactions (click, dismiss)"""
        try:
            interaction_data = {
                'user_id': user_id,
                'interaction_type': f'notification_{action}',
                'session_id': session_id,
                'interaction_time': datetime.now().isoformat(),
                'metadata': {
                    'notification_id': notification_id,
                    'action': action
                }
            }
            
            # Store in user_interactions table
            result = supabase.table('user_interactions').insert(interaction_data).execute()
            
            if result.data:
                self.logger.info(f"Notification {action} tracked for user {user_id}")
                return result.data[0]['id']
            else:
                self.logger.error(f"Failed to track notification {action}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error tracking notification interaction: {str(e)}")
            return None


# Global event tracker instance
_event_tracker = None

def get_event_tracker():
    """Get or create the global event tracker instance"""
    global _event_tracker
    if _event_tracker is None:
        _event_tracker = EventTracker()
    return _event_tracker


# Example usage
if __name__ == '__main__':
    tracker = get_event_tracker()
    
    # Test tracking various events
    print("Testing Event Tracker...")
    
    # Track page view
    tracker.track_page_view(
        page_name='dashboard',
        user_id='user123',
        session_id='session456',
        referrer='/login'
    )
    
    # Track recommendation click
    tracker.track_recommendation_click(
        user_id='user123',
        github_reference_id='github456',
        rank_position=1,
        similarity_score=0.85,
        session_id='session456'
    )
    
    # Track bookmark
    tracker.track_bookmark_action(
        user_id='user123',
        github_reference_id='github456',
        action='add',
        session_id='session456',
        notes='Interesting project for learning React'
    )
    
    # Track feedback
    tracker.track_feedback(
        user_id='user123',
        github_reference_id='github456',
        rating=5,
        feedback_text='Very helpful recommendation!',
        is_relevant=True,
        is_helpful=True
    )
    
    print("✅ Event tracking tests completed!")