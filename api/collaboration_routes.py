"""
API Routes for Live Project Collaboration System
Handles all collaboration-related API endpoints
"""

from flask import Blueprint, request, jsonify, session
from functools import wraps
import logging
from services.collaboration_service import collaboration_service

logger = logging.getLogger(__name__)

# Create blueprint
collaboration_bp = Blueprint('collaboration', __name__, url_prefix='/api/collaboration')

def login_required_api(f):
    """Decorator for API routes that require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function

# ==================== PROJECT MANAGEMENT ROUTES ====================

@collaboration_bp.route('/projects', methods=['POST'])
@login_required_api
def create_project():
    """Create a new collaboration project"""
    try:
        user_id = session.get('user_id')
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        # Validate required fields
        required_fields = ['title', 'description', 'domain']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'success': False, 
                    'error': f'Missing required field: {field}'
                }), 400
        
        result = collaboration_service.create_project(user_id, data)
        
        if result.get('success'):
            return jsonify(result), 201
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Error creating project: {str(e)}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@collaboration_bp.route('/projects/<project_id>', methods=['PUT'])
@login_required_api
def update_project(project_id):
    """Update a project (creator or team members only)"""
    try:
        user_id = session.get('user_id')
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        result = collaboration_service.update_project(project_id, user_id, data)
        
        if result.get('success'):
            return jsonify(result)
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Error updating project: {str(e)}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@collaboration_bp.route('/projects/by-topics', methods=['GET'])
@login_required_api
def get_projects_by_topics():
    """Get projects filtered by topics and skills - for Live Projects page"""
    try:
        user_id = session.get('user_id')
        
        # Get query parameters
        topic_filters = request.args.getlist('topics')  # Can be multiple
        skill_filters = request.args.getlist('skills')  # Can be multiple
        limit = int(request.args.get('limit', 20))
        offset = int(request.args.get('offset', 0))
        
        result = collaboration_service.get_projects_by_topics(
            user_id=user_id,
            topic_filters=topic_filters if topic_filters else None,
            skill_filters=skill_filters if skill_filters else None,
            limit=limit,
            offset=offset
        )
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error getting projects by topics: {str(e)}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@collaboration_bp.route('/projects/explore', methods=['GET'])
def get_all_projects():
    """Get all public projects - for Explore page (no authentication required for viewing)"""
    try:
        user_id = session.get('user_id')  # Optional - used for compatibility scoring if logged in
        
        # Get query parameters
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))
        sort_by = request.args.get('sort_by', 'recent')  # 'recent', 'popular', 'active'
        
        result = collaboration_service.get_all_projects(
            user_id=user_id,
            limit=limit,
            offset=offset,
            sort_by=sort_by
        )
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error getting all projects: {str(e)}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@collaboration_bp.route('/projects/recommendations', methods=['GET'])
@login_required_api
def get_project_recommendations():
    """Get personalized project recommendations for user"""
    try:
        user_id = session.get('user_id')
        limit = int(request.args.get('limit', 10))
        
        result = collaboration_service.get_project_recommendations_for_user(user_id, limit)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error getting project recommendations: {str(e)}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

# ==================== COLLABORATION REQUEST ROUTES ====================

@collaboration_bp.route('/requests', methods=['POST'])
@login_required_api
def send_collaboration_request():
    """Send a collaboration request to join a project"""
    try:
        user_id = session.get('user_id')
        data = request.get_json()
        
        if not data or not data.get('project_id'):
            return jsonify({
                'success': False, 
                'error': 'Project ID is required'
            }), 400
        
        project_id = data['project_id']
        
        # Prepare request data
        request_data = {
            'requested_role': data.get('requested_role', ''),
            'cover_message': data.get('cover_message', ''),
            'why_interested': data.get('why_interested', ''),
            'relevant_experience': data.get('relevant_experience', ''),
            'auto_matched': data.get('auto_matched', False)
        }
        
        result = collaboration_service.send_collaboration_request(
            requester_id=user_id,
            project_id=project_id,
            request_data=request_data
        )
        
        if result.get('success'):
            return jsonify(result), 201
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Error sending collaboration request: {str(e)}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@collaboration_bp.route('/requests/<request_id>/respond', methods=['POST'])
@login_required_api
def respond_to_collaboration_request(request_id):
    """Accept or reject a collaboration request"""
    try:
        user_id = session.get('user_id')
        data = request.get_json()
        
        if not data or not data.get('response'):
            return jsonify({
                'success': False, 
                'error': 'Response is required (accepted/rejected)'
            }), 400
        
        response = data['response']
        message = data.get('message', '')
        
        if response not in ['accepted', 'rejected']:
            return jsonify({
                'success': False, 
                'error': 'Invalid response. Must be "accepted" or "rejected"'
            }), 400
        
        result = collaboration_service.respond_to_collaboration_request(
            request_id=request_id,
            owner_id=user_id,
            response=response,
            message=message
        )
        
        if result.get('success'):
            return jsonify(result)
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Error responding to collaboration request: {str(e)}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@collaboration_bp.route('/requests/sent', methods=['GET'])
@login_required_api
def get_sent_requests():
    """Get collaboration requests sent by the current user"""
    try:
        user_id = session.get('user_id')
        
        # Query sent requests
        from database.connection import supabase
        
        result = supabase.table('collaboration_requests').select(
            '*, user_projects(title, creator_id), users(full_name)'
        ).eq('requester_id', user_id).order('created_at', desc=True).execute()
        
        requests = []
        for req in result.data:
            request_info = {
                'id': req['id'],
                'project_id': req['project_id'],
                'project_title': req['user_projects']['title'],
                'project_owner_name': req['users']['full_name'],
                'requested_role': req['requested_role'],
                'status': req['status'],
                'cover_message': req['cover_message'],
                'response_message': req['response_message'],
                'created_at': req['created_at'],
                'responded_at': req['responded_at']
            }
            requests.append(request_info)
        
        return jsonify({
            'success': True,
            'requests': requests
        })
        
    except Exception as e:
        logger.error(f"Error getting sent requests: {str(e)}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@collaboration_bp.route('/requests/received', methods=['GET'])
@login_required_api
def get_received_requests():
    """Get collaboration requests received by the current user (for their projects)"""
    try:
        user_id = session.get('user_id')
        
        # Query received requests
        from database.connection import supabase
        
        result = supabase.table('collaboration_requests').select(
            '*, user_projects(title), users(full_name, email)'
        ).eq('project_owner_id', user_id).order('created_at', desc=True).execute()
        
        requests = []
        for req in result.data:
            request_info = {
                'id': req['id'],
                'project_id': req['project_id'],
                'project_title': req['user_projects']['title'],
                'requester_name': req['users']['full_name'],
                'requester_email': req['users']['email'],
                'requested_role': req['requested_role'],
                'status': req['status'],
                'cover_message': req['cover_message'],
                'why_interested': req['why_interested'],
                'relevant_experience': req['relevant_experience'],
                'compatibility_score': req['compatibility_score'],
                'created_at': req['created_at'],
                'responded_at': req['responded_at']
            }
            requests.append(request_info)
        
        return jsonify({
            'success': True,
            'requests': requests
        })
        
    except Exception as e:
        logger.error(f"Error getting received requests: {str(e)}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

# ==================== TOPIC MANAGEMENT ROUTES ====================

@collaboration_bp.route('/topics', methods=['GET'])
def get_topics():
    """Get all available topics for project categorization"""
    try:
        category = request.args.get('category')
        
        result = collaboration_service.get_available_topics(category)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error getting topics: {str(e)}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@collaboration_bp.route('/user/topic-interests', methods=['POST'])
@login_required_api
def update_user_topic_interests():
    """Update user's topic interests for better recommendations"""
    try:
        user_id = session.get('user_id')
        data = request.get_json()
        
        if not data or 'topic_interests' not in data:
            return jsonify({
                'success': False, 
                'error': 'Topic interests data is required'
            }), 400
        
        topic_interests = data['topic_interests']
        
        result = collaboration_service.update_user_topic_interests(user_id, topic_interests)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error updating topic interests: {str(e)}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@collaboration_bp.route('/user/topic-interests', methods=['GET'])
@login_required_api
def get_user_topic_interests():
    """Get user's current topic interests"""
    try:
        user_id = session.get('user_id')
        
        from database.connection import supabase
        
        result = supabase.table('user_topic_interests').select(
            '*, project_topics(name, category, icon, color)'
        ).eq('user_id', user_id).execute()
        
        interests = []
        for item in result.data:
            interest = {
                'topic_id': item['topic_id'],
                'topic_name': item['project_topics']['name'],
                'category': item['project_topics']['category'],
                'icon': item['project_topics']['icon'],
                'color': item['project_topics']['color'],
                'interest_level': item['interest_level'],
                'experience_level': item['experience_level'],
                'willing_to_learn': item['willing_to_learn']
            }
            interests.append(interest)
        
        return jsonify({
            'success': True,
            'topic_interests': interests
        })
        
    except Exception as e:
        logger.error(f"Error getting user topic interests: {str(e)}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

# ==================== USER PROJECT MANAGEMENT ROUTES ====================

@collaboration_bp.route('/user/projects', methods=['GET'])
@login_required_api
def get_user_projects():
    """Get projects created by the current user"""
    try:
        user_id = session.get('user_id')
        
        from database.connection import supabase
        
        result = supabase.table('project_collaboration_details').select('*').eq(
            'creator_id', user_id
        ).order('created_at', desc=True).execute()
        
        return jsonify({
            'success': True,
            'projects': result.data
        })
        
    except Exception as e:
        logger.error(f"Error getting user projects: {str(e)}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@collaboration_bp.route('/user/joined-projects', methods=['GET'])
@login_required_api
def get_joined_projects():
    """Get projects the user has joined as a collaborator"""
    try:
        user_id = session.get('user_id')
        
        from database.connection import supabase
        
        # Get projects where user is a team member
        result = supabase.table('project_members').select(
            '*, user_projects(*)'
        ).eq('user_id', user_id).eq('is_active', True).execute()
        
        projects = []
        for member in result.data:
            project_info = member['user_projects']
            project_info['user_role'] = member['role']
            project_info['joined_at'] = member['joined_at']
            projects.append(project_info)
        
        return jsonify({
            'success': True,
            'projects': projects
        })
        
    except Exception as e:
        logger.error(f"Error getting joined projects: {str(e)}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

# ==================== PROJECT DETAILS & ACTIVITY ====================

@collaboration_bp.route('/projects/<project_id>', methods=['GET'])
def get_project_details(project_id):
    """Get detailed information about a specific project"""
    try:
        from database.connection import supabase
        
        # Get project details
        project_result = supabase.table('project_collaboration_details').select('*').eq(
            'project_id', project_id
        ).execute()
        
        if not project_result.data:
            return jsonify({'success': False, 'error': 'Project not found'}), 404
        
        project = project_result.data[0]
        
        # Get team members
        members_result = supabase.table('project_members').select(
            '*, users(full_name, email)'
        ).eq('project_id', project_id).eq('is_active', True).execute()
        
        members = []
        for member in members_result.data:
            member_info = {
                'user_id': member['user_id'],
                'name': member['users']['full_name'],
                'email': member['users']['email'],
                'role': member['role'],
                'joined_at': member['joined_at']
            }
            members.append(member_info)
        
        # Get recent activities
        activities_result = supabase.table('project_activities').select(
            '*, users(full_name)'
        ).eq('project_id', project_id).eq('is_public', True).order(
            'created_at', desc=True
        ).limit(10).execute()
        
        activities = []
        for activity in activities_result.data:
            activity_info = {
                'id': activity['id'],
                'activity_type': activity['activity_type'],
                'message': activity['activity_message'],
                'user_name': activity['users']['full_name'] if activity['users'] else None,
                'created_at': activity['created_at']
            }
            activities.append(activity_info)
        
        # Increment view count if not the creator
        user_id = session.get('user_id')
        if user_id and user_id != project['creator_id']:
            # Track project view
            supabase.table('project_views').insert({
                'project_id': project_id,
                'viewer_id': user_id,
                'session_id': session.get('session_id', ''),
                'viewed_at': 'NOW()'
            }).execute()
            
            # Update view count
            supabase.table('user_projects').update({
                'view_count': project['view_count'] + 1
            }).eq('id', project_id).execute()
        
        return jsonify({
            'success': True,
            'project': project,
            'team_members': members,
            'recent_activities': activities
        })
        
    except Exception as e:
        logger.error(f"Error getting project details: {str(e)}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

# ==================== SEARCH & FILTERING ====================

@collaboration_bp.route('/search', methods=['GET'])
def search_projects():
    """Search projects with advanced filtering"""
    try:
        from database.connection import supabase
        
        # Get search parameters
        query = request.args.get('q', '').strip()
        topics = request.args.getlist('topics')
        skills = request.args.getlist('skills')
        complexity = request.args.get('complexity')
        domain = request.args.get('domain')
        status = request.args.getlist('status') or ['planning', 'active', 'recruiting']
        limit = int(request.args.get('limit', 20))
        offset = int(request.args.get('offset', 0))
        
        # Build base query
        base_query = supabase.table('project_collaboration_details').select('*')
        base_query = base_query.eq('is_public', True)
        base_query = base_query.in_('status', status)
        
        # Apply filters
        if complexity:
            base_query = base_query.eq('complexity_level', complexity)
        
        if domain:
            base_query = base_query.eq('domain', domain)
        
        # Execute query
        result = base_query.execute()
        
        if not result.data:
            return jsonify({'success': True, 'projects': [], 'total': 0})
        
        projects = result.data
        filtered_projects = []
        
        # Apply text search and topic filtering
        for project in projects:
            # Text search in title and description
            if query:
                searchable_text = f"{project['title']} {project['description']}".lower()
                if query.lower() not in searchable_text:
                    continue
            
            # Topic filtering
            if topics:
                project_topics = project.get('topics', [])
                if isinstance(project_topics, str):
                    import json
                    project_topics = json.loads(project_topics)
                
                project_topic_names = [t.get('name', '') for t in project_topics]
                if not any(topic in project_topic_names for topic in topics):
                    continue
            
            # Skill filtering
            if skills:
                project_skills = []
                if project.get('tech_stack'):
                    project_skills.extend(project['tech_stack'])
                if project.get('required_skills'):
                    project_skills.extend(project['required_skills'])
                
                if not any(skill.lower() in [ps.lower() for ps in project_skills] for skill in skills):
                    continue
            
            filtered_projects.append(project)
        
        # Apply pagination
        total = len(filtered_projects)
        paginated_projects = filtered_projects[offset:offset + limit]
        
        # Track search for analytics
        user_id = session.get('user_id')
        if user_id:
            try:
                search_record = {
                    'user_id': user_id,
                    'search_query': query,
                    'selected_topics': topics,
                    'selected_skills': skills,
                    'filters_applied': {
                        'complexity': complexity,
                        'domain': domain,
                        'status': status
                    },
                    'results_count': total
                }
                supabase.table('project_search_history').insert(search_record).execute()
            except:
                pass  # Don't fail the search if analytics tracking fails
        
        return jsonify({
            'success': True,
            'projects': paginated_projects,
            'total': total,
            'has_more': offset + limit < total,
            'search_query': query,
            'applied_filters': {
                'topics': topics,
                'skills': skills,
                'complexity': complexity,
                'domain': domain,
                'status': status
            }
        })
        
    except Exception as e:
        logger.error(f"Error searching projects: {str(e)}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

# ==================== NOTIFICATIONS ====================

@collaboration_bp.route('/notifications', methods=['GET'])
@login_required_api
def get_user_notifications():
    """Get user's collaboration notifications"""
    try:
        user_id = session.get('user_id')
        unread_only = request.args.get('unread_only', 'false').lower() == 'true'
        limit = int(request.args.get('limit', 20))
        
        from database.connection import supabase
        
        query = supabase.table('user_notifications').select('*').eq('user_id', user_id)
        
        if unread_only:
            query = query.eq('is_read', False)
        
        result = query.order('created_at', desc=True).limit(limit).execute()
        
        return jsonify({
            'success': True,
            'notifications': result.data
        })
        
    except Exception as e:
        logger.error(f"Error getting notifications: {str(e)}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@collaboration_bp.route('/notifications/<notification_id>/mark-read', methods=['POST'])
@login_required_api
def mark_notification_read(notification_id):
    """Mark a notification as read"""
    try:
        user_id = session.get('user_id')
        
        from database.connection import supabase
        
        result = supabase.table('user_notifications').update({
            'is_read': True,
            'read_at': 'NOW()'
        }).eq('id', notification_id).eq('user_id', user_id).execute()
        
        return jsonify({'success': True})
        
    except Exception as e:
        logger.error(f"Error marking notification read: {str(e)}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500