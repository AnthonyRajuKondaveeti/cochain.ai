"""
Updated Project Collaboration Service
Uses existing platform_schema.sql tables for collaboration functionality
"""

import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple

try:
    from database.connection import supabase_admin as supabase
    SUPABASE_AVAILABLE = True
except ImportError:
    print("Warning: Supabase admin client not available. Collaboration service will have limited functionality.")
    supabase = None
    SUPABASE_AVAILABLE = False

try:
    from sentence_transformers import SentenceTransformer
    import numpy as np
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    print("Warning: SentenceTransformers not available. Embedding functionality disabled.")
    SentenceTransformer = None
    EMBEDDINGS_AVAILABLE = False

class CollaborationProjectService:
    """Service for managing collaborative projects using existing platform schema"""
    
    def __init__(self):
        if EMBEDDINGS_AVAILABLE and SentenceTransformer:
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        else:
            self.embedding_model = None
            print("Warning: Embedding model not available. Similarity matching disabled.")

    def create_project(self, creator_id: str, project_data: Dict) -> Optional[str]:
        """Create a new collaborative project using existing user_projects table"""
        if not SUPABASE_AVAILABLE:
            print("Error: Supabase client not available")
            return None
            
        try:
            # Create the project in user_projects table
            project_record = {
                'creator_id': creator_id,
                'title': project_data.get('title'),
                'description': project_data.get('description'),
                'detailed_requirements': project_data.get('detailed_requirements'),
                'project_goals': project_data.get('project_goals'),
                'tech_stack': project_data.get('tech_stack', []),
                'required_skills': project_data.get('required_skills', []),
                'complexity_level': project_data.get('complexity_level', 'intermediate'),
                'estimated_duration': project_data.get('estimated_duration'),
                'domain': project_data.get('domain'),
                'max_collaborators': project_data.get('max_collaborators', 5),
                'needed_roles': project_data.get('needed_roles', []),
                'github_link': project_data.get('github_link', ''),
                'start_date': project_data.get('start_date'),
                'target_completion_date': project_data.get('target_completion_date'),
                'is_open_for_collaboration': True
            }
            
            result = supabase.table('user_projects').insert(project_record).execute()
            
            if not result.data:
                print("No data returned from insert operation")
                return None
            
            project_id = result.data[0]['id']
            
            # Add creator as first team member in project_members table
            supabase.table('project_members').insert({
                'project_id': project_id,
                'user_id': creator_id,
                'role': 'Project Owner'
            }).execute()
            
            # Generate and store project embedding (if available)
            if self.embedding_model:
                project_text = f"{project_data.get('title', '')} {project_data.get('description', '')} {' '.join(project_data.get('tech_stack', []))} {' '.join(project_data.get('required_skills', []))}"
                embedding = self.embedding_model.encode(project_text)
                
                supabase.table('user_project_embeddings').insert({
                    'project_id': project_id,
                    'embedding': embedding.tolist()
                }).execute()
            
            # Notify users with matching skills
            try:
                self._notify_matching_users(project_id, project_data)
            except Exception as e:
                print(f"Failed to send notifications: {str(e)}")
                # Don't fail project creation if notifications fail
            
            return str(project_id)
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"Error creating project: {e}")
            print(f"Full error details: {error_details}")
            return None

    def update_project(self, project_id: str, creator_id: str, project_data: Dict) -> bool:
        """Update an existing project (only by creator)"""
        if not SUPABASE_AVAILABLE:
            print("Error: Supabase client not available")
            return False
            
        try:
            # Verify user is the creator
            project = self.get_project_by_id(project_id)
            if not project or project.get('creator_id') != creator_id:
                print("User is not authorized to edit this project")
                return False
            
            # Update project data
            update_data = {
                'title': project_data.get('title'),
                'description': project_data.get('description'),
                'detailed_requirements': project_data.get('detailed_requirements', ''),
                'project_goals': project_data.get('project_goals', ''),
                'tech_stack': project_data.get('tech_stack', []),
                'required_skills': project_data.get('required_skills', []),
                'complexity_level': project_data.get('complexity_level', 'intermediate'),
                'estimated_duration': project_data.get('estimated_duration', ''),
                'domain': project_data.get('domain', ''),
                'max_collaborators': project_data.get('max_collaborators', 5),
                'github_link': project_data.get('github_link', ''),
                'is_open_for_collaboration': project_data.get('is_open_for_collaboration', True),
                'updated_at': datetime.now().isoformat()
            }
            
            result = supabase.table('user_projects').update(update_data).eq('id', project_id).execute()
            
            if result.data:
                print(f"Project {project_id} updated successfully")
                return True
            return False
            
        except Exception as e:
            print(f"Error updating project: {e}")
            return False

    def can_user_join_project(self, user_id: str, project_id: str) -> Dict:
        """Check if user can join project based on profile compatibility"""
        if not SUPABASE_AVAILABLE:
            return {'can_join': False, 'reason': 'Service unavailable'}
            
        try:
            # Get project details
            project = self.get_project_by_id(project_id)
            if not project:
                return {'can_join': False, 'reason': 'Project not found'}
            
            # Check if project is open for collaboration
            if not project.get('is_open_for_collaboration'):
                return {'can_join': False, 'reason': 'Project is not accepting new members'}
            
            # Check if user is already the creator
            if project.get('creator_id') == user_id:
                return {'can_join': False, 'reason': 'You are the project creator'}
            
            # Check if user is already a member
            member_check = supabase.table('project_members').select('id').eq('project_id', project_id).eq('user_id', user_id).execute()
            if member_check.data:
                return {'can_join': False, 'reason': 'You are already a member of this project'}
            
            # Check if user already has a pending request
            pending_request = supabase.table('collaboration_requests').select('id, status').eq(
                'project_id', project_id
            ).eq('requester_id', user_id).eq('status', 'pending').execute()
            
            if pending_request.data:
                return {'can_join': False, 'reason': 'Request already sent! The project owner will review your request soon.'}
            
            # Check if team is full
            current_members = project.get('current_collaborators', 1)
            max_members = project.get('max_collaborators', 5)
            if current_members >= max_members:
                return {'can_join': False, 'reason': 'Project team is full'}
            
            # Allow any user to request to join regardless of interests or profile completeness
            # Optional: Get user profile for enhanced matching info (but don't require it)
            user_profile = supabase.table('user_profiles').select('areas_of_interest, programming_languages, frameworks_known').eq('user_id', user_id).execute()
            
            if user_profile.data:
                user_data = user_profile.data[0]
                user_interests = user_data.get('areas_of_interest', [])
                project_skills = project.get('required_skills', [])
                
                # Calculate compatibility for informational purposes
                if project_skills and user_interests:
                    matching_skills = set(user_interests) & set(project_skills)
                    if matching_skills:
                        return {'can_join': True, 'reason': f'Great match! You have skills in: {", ".join(matching_skills)}'}
                    else:
                        return {'can_join': True, 'reason': 'You can bring fresh perspectives to this project!'}
                elif user_interests:
                    return {'can_join': True, 'reason': 'Your diverse background could be valuable to this project!'}
                else:
                    return {'can_join': True, 'reason': 'Ready to collaborate and learn new skills!'}
            
            # Even without a profile, allow join
            return {'can_join': True, 'reason': 'Ready to start collaborating!'}
            
        except Exception as e:
            print(f"Error checking user join eligibility: {e}")
            return {'can_join': False, 'reason': 'Error checking eligibility'}

    def get_project_team_members(self, project_id: str) -> List[Dict]:
        """Get all team members for a project"""
        if not SUPABASE_AVAILABLE:
            return []
            
        try:
            result = supabase.table('project_members').select(
                'user_id, role, joined_at, users!user_id(full_name, email)'
            ).eq('project_id', project_id).execute()
            
            team_members = []
            for member in result.data:
                user_info = member.get('users', {}) if member.get('users') else {}
                team_members.append({
                    'user_id': member['user_id'],
                    'role': member['role'],
                    'joined_at': member['joined_at'],
                    'name': user_info.get('full_name', 'Unknown User'),
                    'email': user_info.get('email', ''),
                    'areas_of_interest': []  # Will need to be fetched separately if needed
                })
            
            return team_members
            
        except Exception as e:
            print(f"Error getting team members: {e}")
            return []

    def create_join_request_notification(self, requester_id: str, project_id: str, project_creator_id: str, message: str = '') -> bool:
        """Create a notification for project join request"""
        if not SUPABASE_AVAILABLE:
            return False
            
        try:
            # Get requester info
            requester_info = supabase.table('users').select('full_name, email').eq('id', requester_id).execute()
            requester_name = requester_info.data[0].get('full_name', 'Unknown User') if requester_info.data else 'Unknown User'
            
            # Get project info
            project = self.get_project_by_id(project_id)
            project_title = project.get('title', 'Unknown Project') if project else 'Unknown Project'
            
            # Create notification
            notification_data = {
                'user_id': project_creator_id,
                'type': 'join_request',
                'title': f'New Join Request for {project_title}',
                'message': f'{requester_name} wants to join your project "{project_title}". {message}' if message else f'{requester_name} wants to join your project "{project_title}".',
                'data': {
                    'requester_id': requester_id,
                    'project_id': project_id,
                    'project_title': project_title,
                    'requester_name': requester_name
                },
                'is_read': False,
                'created_at': datetime.now().isoformat()
            }
            
            # Notification functionality disabled - using collaboration_requests table directly
            return True
            
        except Exception as e:
            print(f"Error creating join request notification: {e}")
            return False

    def create_notification(self, user_id: str, notification_type: str, title: str, message: str, data: Dict = None, action_url: str = None) -> bool:
        """Create a notification for a user"""
        if not SUPABASE_AVAILABLE:
            return False
            
        try:
            notification_record = {
                'user_id': user_id,
                'type': notification_type,
                'title': title,
                'message': message,
                'data': data or {},
                'action_url': action_url or '/notifications',
                'is_read': False,
                'created_at': datetime.now().isoformat()
            }
            
            # Notification functionality disabled - using collaboration_requests table directly
            return True
            
        except Exception as e:
            print(f"Error creating notification: {e}")
            return False

    def get_projects_by_user_interests(self, user_id: str, limit: int = 20) -> List[Dict]:
        """Get projects from other users where required_skills match user's areas_of_interest"""
        if not SUPABASE_AVAILABLE:
            return []
            
        try:
            # Get user's areas of interest from user_profiles table
            user_profile = supabase.table('user_profiles').select('areas_of_interest, programming_languages').eq('user_id', user_id).execute()
            
            if not user_profile.data:
                print(f"No profile found for user {user_id}")
                return self._get_recent_projects_from_others(user_id, limit)
            
            user_interests = user_profile.data[0].get('areas_of_interest', []) or []
            user_languages = user_profile.data[0].get('programming_languages', []) or []
            
            # Combine interests and languages for broader matching
            all_user_interests = set(user_interests + user_languages)
            
            if not all_user_interests:
                print(f"User {user_id} has no interests or languages set")
                return self._get_recent_projects_from_others(user_id, limit)
            
            print(f"User interests: {all_user_interests}")
            
            # Get ALL open projects from other users
            projects_query = supabase.table('user_projects').select(
                'id, title, description, domain, required_skills, tech_stack, '
                'complexity_level, max_collaborators, current_collaborators, '
                'created_at, status, creator_id, is_open_for_collaboration, view_count, '
                'users!creator_id(full_name)'
            ).eq('is_public', True).eq('is_open_for_collaboration', True).neq('creator_id', user_id)
            
            projects_result = projects_query.order('created_at', desc=True).limit(200).execute()
            
            print(f"Found {len(projects_result.data)} total open projects")
            
            # Filter projects where required_skills match user's areas_of_interest
            matching_projects = []
            for project in projects_result.data:
                project_skills = project.get('required_skills', [])
                
                # Convert required_skills to set for comparison
                if isinstance(project_skills, list):
                    project_skills_set = set(project_skills)
                else:
                    project_skills_set = set()
                
                # Find matching skills between project and user
                matching_skills = all_user_interests & project_skills_set
                
                if matching_skills:
                    # Get creator name from joined users table
                    creator_info = project.get('users', {})
                    creator_name = creator_info.get('full_name', f'User {project["creator_id"][:8]}') if creator_info else f'User {project["creator_id"][:8]}'
                    
                    matching_projects.append({
                        'id': str(project['id']),
                        'title': project['title'],
                        'description': project['description'],
                        'domain': project.get('domain', ''),
                        'required_skills': list(project_skills_set),
                        'tech_stack': project.get('tech_stack', []),
                        'complexity_level': project.get('complexity_level', 'intermediate'),
                        'max_collaborators': project.get('max_collaborators', 5),
                        'current_collaborators': project.get('current_collaborators', 1),
                        'created_at': project['created_at'],
                        'status': project.get('status', 'active'),
                        'creator_name': creator_name,
                        'creator_id': project['creator_id'],
                        'is_open_for_collaboration': project.get('is_open_for_collaboration', True),
                        'view_count': project.get('view_count', 0),
                        'matching_skills': list(matching_skills)
                    })
                    
                    print(f"✅ Match: {project['title']} - Skills: {matching_skills}")
            
            print(f"Found {len(matching_projects)} matching projects")
            
            # Sort by number of matching skills (most relevant first), then by date
            matching_projects.sort(key=lambda x: (len(x['matching_skills']), x['created_at']), reverse=True)
            
            return matching_projects[:limit]
            
        except Exception as e:
            print(f"❌ Error getting projects by user interests: {e}")
            import traceback
            traceback.print_exc()
            return []

    def _get_recent_projects_from_others(self, user_id: str, limit: int) -> List[Dict]:
        """Get recent projects from other users when user has no interests set"""
        try:
            projects_result = supabase.table('user_projects').select(
                'id, title, description, domain, required_skills, tech_stack, '
                'complexity_level, max_collaborators, current_collaborators, '
                'created_at, status, creator_id, is_open_for_collaboration, view_count'
            ).eq('is_public', True).eq('is_open_for_collaboration', True).neq('creator_id', user_id).order('created_at', desc=True).limit(limit).execute()
            
            formatted_projects = []
            for project in projects_result.data:
                creator_name = f'Creator {project["creator_id"][:8]}'  # Use first 8 chars of ID as fallback
                
                formatted_projects.append({
                    'id': str(project['id']),
                    'title': project['title'],
                    'description': project['description'],
                    'domain': project.get('domain', ''),
                    'required_skills': project.get('required_skills', []),
                    'tech_stack': project.get('tech_stack', []),
                    'complexity_level': project.get('complexity_level', 'intermediate'),
                    'max_collaborators': project.get('max_collaborators', 5),
                    'current_collaborators': project.get('current_collaborators', 1),
                    'created_at': project['created_at'],
                    'status': project.get('status', 'active'),
                    'creator_name': creator_name,
                    'creator_id': project['creator_id'],
                    'is_open_for_collaboration': project.get('is_open_for_collaboration', True),
                    'matching_skills': []
                })
            
            return formatted_projects
            
        except Exception as e:
            print(f"Error getting recent projects from others: {e}")
            return []
    
    def get_all_available_projects(self, user_id: str, limit: int = 20) -> List[Dict]:
        """Get all available projects from other users"""
        if not SUPABASE_AVAILABLE:
            return []
            
        try:
            # Get all public projects from other users that are open for collaboration
            projects_result = supabase.table('user_projects').select(
                'id, title, description, domain, required_skills, tech_stack, '
                'complexity_level, max_collaborators, current_collaborators, '
                'created_at, status, creator_id, is_open_for_collaboration, view_count'
            ).eq('is_public', True).eq('is_open_for_collaboration', True).neq('creator_id', user_id).order('created_at', desc=True).limit(limit).execute()
            
            formatted_projects = []
            for project in projects_result.data:
                creator_name = f'Creator {project["creator_id"][:8]}'  # Use first 8 chars of ID as fallback
                
                formatted_projects.append({
                    'id': str(project['id']),
                    'title': project['title'],
                    'description': project['description'],
                    'domain': project.get('domain', ''),
                    'required_skills': project.get('required_skills', []),
                    'tech_stack': project.get('tech_stack', []),
                    'complexity_level': project.get('complexity_level', 'intermediate'),
                    'max_collaborators': project.get('max_collaborators', 5),
                    'current_collaborators': project.get('current_collaborators', 1),
                    'created_at': project['created_at'],
                    'status': project.get('status', 'active'),
                    'creator_name': creator_name,
                    'creator_id': project['creator_id'],
                    'is_open_for_collaboration': project.get('is_open_for_collaboration', True),
                    'view_count': project.get('view_count', 0)
                })
            
            return formatted_projects
            
        except Exception as e:
            print(f"Error getting all available projects: {e}")
            return []

    def get_project_recommendations_for_user(self, user_id: str, limit: int = 10) -> List[Dict]:
        """Get personalized project recommendations based on user profile and interests"""
        try:
            # Get user's profile to understand their interests and skills
            user_profile_result = supabase.table('user_profiles').select(
                'areas_of_interest, programming_languages, frameworks_known, overall_skill_level'
            ).eq('user_id', user_id).execute()
            
            if not user_profile_result.data:
                # If user has no profile, return recent projects
                return self._get_recent_projects(user_id, limit)
            
            user_profile = user_profile_result.data[0]
            user_interests = user_profile.get('areas_of_interest', [])
            user_languages = user_profile.get('programming_languages', [])
            user_frameworks = user_profile.get('frameworks_known', [])
            
            # Get all open projects excluding user's own
            projects_result = supabase.table('user_projects').select(
                'id, title, description, domain, required_skills, tech_stack, '
                'complexity_level, max_collaborators, current_collaborators, created_at, '
                'users!creator_id(full_name)'
            ).eq('is_open_for_collaboration', True).neq('creator_id', user_id).lt(
                'current_collaborators', supabase.table('user_projects').select('max_collaborators')
            ).in_('status', ['planning', 'active']).order('created_at', desc=True).limit(limit * 2).execute()
            
            projects = projects_result.data
            
            # Calculate compatibility scores based on profile matching
            recommendations = []
            for project in projects:
                compatibility_score = self._calculate_profile_compatibility(
                    user_interests, user_languages, user_frameworks,
                    project.get('required_skills', []), project.get('tech_stack', []), project.get('domain')
                )
                
                creator_name = project.get('users', {}).get('full_name', 'Unknown') if project.get('users') else 'Unknown'
                
                recommendations.append({
                    'id': str(project['id']),
                    'title': project['title'],
                    'description': project['description'],
                    'domain': project['domain'],
                    'required_skills': project.get('required_skills', []),
                    'tech_stack': project.get('tech_stack', []),
                    'complexity_level': project['complexity_level'],
                    'max_collaborators': project['max_collaborators'],
                    'current_collaborators': project['current_collaborators'],
                    'creator_name': creator_name,
                    'compatibility_score': compatibility_score,
                    'created_at': project['created_at']
                })
            
            # Sort by compatibility score and limit results
            recommendations.sort(key=lambda x: x['compatibility_score'], reverse=True)
            
            return recommendations[:limit]
            
        except Exception as e:
            print(f"Error getting recommendations: {e}")
            return []

    def get_all_projects(self, user_id: str = None, limit: int = 50, offset: int = 0, filters: Dict = None) -> List[Dict]:
        """Get ALL projects for Explore page - no restrictions on areas of interest"""
        try:
            # Get ALL public projects regardless of user's interests or areas of interest
            projects_query = supabase.table('user_projects').select(
                'id, title, description, domain, required_skills, tech_stack, '
                'complexity_level, max_collaborators, current_collaborators, view_count, '
                'created_at, status, creator_id, is_open_for_collaboration, '
                'users!creator_id(full_name)'
            ).eq('is_public', True)
            
            # Apply optional filters if provided
            if filters:
                if filters.get('interest_area'):
                    # Filter by required skills matching interest area
                    projects_query = projects_query.contains('required_skills', [filters['interest_area']])
                if filters.get('complexity'):
                    projects_query = projects_query.eq('complexity_level', filters['complexity'])
                if filters.get('domain'):
                    projects_query = projects_query.ilike('domain', f'%{filters["domain"]}%')
            
            # Order by creation date (newest first) and apply pagination
            projects_query = projects_query.order('created_at', desc=True).range(offset, offset + limit - 1)
            
            projects_result = projects_query.execute()
            projects = projects_result.data if projects_result.data else []
            
            # Format results
            formatted_projects = []
            for project in projects:
                creator_name = project.get('users', {}).get('full_name', 'Unknown') if project.get('users') else 'Unknown'
                
                # Calculate actual current collaborators from project_members table
                members_count_result = supabase.table('project_members').select('id', count='exact').eq(
                    'project_id', project['id']
                ).eq('is_active', True).execute()
                actual_collaborators = members_count_result.count if members_count_result.count is not None else 0
                
                formatted_projects.append({
                    'id': str(project['id']),
                    'title': project['title'],
                    'description': project['description'],
                    'domain': project['domain'],
                    'required_skills': project.get('required_skills', []),
                    'tech_stack': project.get('tech_stack', []),
                    'complexity_level': project['complexity_level'],
                    'max_collaborators': project['max_collaborators'],
                    'current_collaborators': actual_collaborators,
                    'view_count': project.get('view_count', 0),
                    'creator_name': creator_name,
                    'creator_id': str(project['creator_id']),
                    'created_at': project['created_at'],
                    'status': project['status']
                })
            
            return formatted_projects
            
        except Exception as e:
            print(f"Error getting all projects: {e}")
            return []

    def send_collaboration_request(self, requester_id: str, project_id: str, request_data: Dict) -> Optional[str]:
        """Send a collaboration request using existing collaboration_requests table"""
        try:
            # Get project details
            project_result = supabase.table('user_projects').select(
                'creator_id, title, current_collaborators, max_collaborators, is_open_for_collaboration'
            ).eq('id', project_id).execute()
            
            if not project_result.data:
                return None
            
            project = project_result.data[0]
            
            # Validate project is accepting collaborators
            if not project['is_open_for_collaboration'] or project['current_collaborators'] >= project['max_collaborators']:
                return None
            
            # Check if user already has any request for this project
            existing_request = supabase.table('collaboration_requests').select('id, status').eq(
                'project_id', project_id
            ).eq('requester_id', requester_id).execute()
            
            if existing_request.data:
                # Check if there's already a pending request
                for req in existing_request.data:
                    if req['status'] == 'pending':
                        self.logger.info(f"User {requester_id} already has pending request for project {project_id}")
                        return 'DUPLICATE_PENDING'  # Special return value
                    elif req['status'] == 'accepted':
                        self.logger.info(f"User {requester_id} already accepted to project {project_id}")
                        return 'ALREADY_MEMBER'
            
            # Check if user is already a member
            existing_member = supabase.table('project_members').select('id').eq(
                'project_id', project_id
            ).eq('user_id', requester_id).eq('is_active', True).execute()
            
            if existing_member.data:
                return 'ALREADY_MEMBER'  # Already a member
            
            # Create collaboration request
            request_record = {
                'project_id': project_id,
                'requester_id': requester_id,
                'project_owner_id': project['creator_id'],
                'requested_role': request_data.get('requested_role', ''),
                'cover_message': request_data.get('message', request_data.get('cover_message', '')),
                'why_interested': request_data.get('why_interested', ''),
                'relevant_experience': request_data.get('relevant_experience', ''),
                'status': 'pending'
            }
            
            result = supabase.table('collaboration_requests').insert(request_record).execute()
            
            if result.data:
                request_id = str(result.data[0]['id'])
                
                # Get requester name for notification
                requester_result = supabase.table('users').select('full_name').eq('id', requester_id).execute()
                requester_name = requester_result.data[0]['full_name'] if requester_result.data else 'Someone'
                
                # Note: We don't need to create a separate notification 
                # because the collaboration_requests table serves as our notification system
                # The /notifications route reads directly from collaboration_requests
                
                print(f"✅ Collaboration request sent and notification created for project owner")
                return request_id
            
            return None
            
        except Exception as e:
            print(f"Error sending collaboration request: {e}")
            return None

    def get_collaboration_requests_for_project(self, project_id: str, owner_id: str) -> List[Dict]:
        """Get collaboration requests for a project"""
        try:
            # Verify ownership
            project_result = supabase.table('user_projects').select('creator_id').eq('id', project_id).execute()
            
            if not project_result.data or project_result.data[0]['creator_id'] != owner_id:
                return []
            
            # Get requests with user information
            requests_result = supabase.table('collaboration_requests').select(
                'id, requester_id, requested_role, cover_message, why_interested, '
                'relevant_experience, status, created_at, users!requester_id(full_name, email)'
            ).eq('project_id', project_id).order('created_at', desc=True).execute()
            
            result = []
            for req in requests_result.data:
                user_info = req.get('users', {})
                result.append({
                    'id': str(req['id']),
                    'requester_id': str(req['requester_id']),
                    'requested_role': req['requested_role'],
                    'cover_message': req['cover_message'],
                    'why_interested': req['why_interested'],
                    'relevant_experience': req['relevant_experience'],
                    'status': req['status'],
                    'created_at': req['created_at'],
                    'requester_name': user_info.get('full_name', 'Unknown'),
                    'requester_email': user_info.get('email', 'Unknown')
                })
            
            return result
            
        except Exception as e:
            print(f"Error getting collaboration requests: {e}")
            return []

    def respond_to_collaboration_request(self, request_id: str, response: str, message: str = '') -> bool:
        """Accept or reject a collaboration request"""
        try:
            # Get request details
            request_result = supabase.table('collaboration_requests').select(
                'project_id, requester_id, requested_role'
            ).eq('id', request_id).eq('status', 'pending').execute()
            
            if not request_result.data:
                return False
            
            request_data = request_result.data[0]
            project_id = request_data['project_id']
            requester_id = request_data['requester_id']
            requested_role = request_data['requested_role']
            
            # Update request status (convert 'accept' to 'accepted' and 'reject' to 'rejected')
            status_value = response + 'ed' if response in ['accept', 'reject'] else response
            supabase.table('collaboration_requests').update({
                'status': status_value,
                'response_message': message,
                'responded_at': datetime.now().isoformat()
            }).eq('id', request_id).execute()
            
            # If accepted, add to project members and update count
            if response == 'accept' or response == 'accepted':
                # Check if member already exists to avoid duplicates
                existing_member = supabase.table('project_members').select('id').eq(
                    'project_id', project_id
                ).eq('user_id', requester_id).execute()
                
                if not existing_member.data:
                    supabase.table('project_members').insert({
                        'project_id': project_id,
                        'user_id': requester_id,
                        'role': requested_role
                    }).execute()
                    
                    # Get current collaborator count and increment using admin client
                    project_result = supabase.table('user_projects').select('current_collaborators').eq('id', project_id).execute()
                    if project_result.data:
                        current_count = project_result.data[0].get('current_collaborators', 1)
                        supabase.table('user_projects').update({
                            'current_collaborators': current_count + 1
                        }).eq('id', project_id).execute()
            
            return True
            
        except Exception as e:
            print(f"Error responding to collaboration request: {e}")
            return False

    def get_project_by_id(self, project_id: str) -> Optional[Dict]:
        """Get a single project by ID"""
        if not SUPABASE_AVAILABLE:
            print("Error: Supabase client not available")
            return None
            
        try:
            result = supabase.table('user_projects').select(
                'id, title, description, detailed_requirements, project_goals, '
                'domain, required_skills, tech_stack, complexity_level, '
                'max_collaborators, current_collaborators, status, '
                'created_at, estimated_duration, creator_id, is_open_for_collaboration, '
                'github_link, updated_at'
            ).eq('id', project_id).execute()
            
            if not result.data:
                return None
                
            project = result.data[0]
            return {
                'id': str(project['id']),
                'title': project['title'],
                'description': project['description'],
                'detailed_requirements': project.get('detailed_requirements', ''),
                'project_goals': project.get('project_goals', ''),
                'domain': project.get('domain', ''),
                'required_skills': project.get('required_skills', []),
                'tech_stack': project.get('tech_stack', []),
                'complexity_level': project['complexity_level'],
                'max_collaborators': project['max_collaborators'],
                'current_collaborators': project['current_collaborators'],
                'status': project['status'],
                'created_at': project['created_at'],
                'estimated_duration': project.get('estimated_duration', ''),
                'creator_id': str(project['creator_id']),
                'is_open_for_collaboration': project['is_open_for_collaboration'],
                'github_link': project.get('github_link', '')
            }
            
        except Exception as e:
            print(f"Error getting project by ID {project_id}: {e}")
            return None

    def get_user_projects(self, user_id: str) -> List[Dict]:
        """Get projects created by user"""
        try:
            projects_result = supabase.table('user_projects').select(
                'id, title, description, domain, required_skills, tech_stack, '
                'complexity_level, max_collaborators, current_collaborators, '
                'status, created_at, is_open_for_collaboration'
            ).eq('creator_id', user_id).order('created_at', desc=True).execute()
            
            result = []
            for project in projects_result.data:
                result.append({
                    'id': str(project['id']),
                    'title': project['title'],
                    'description': project['description'],
                    'domain': project['domain'],
                    'required_skills': project.get('required_skills', []),
                    'tech_stack': project.get('tech_stack', []),
                    'complexity_level': project['complexity_level'],
                    'max_collaborators': project['max_collaborators'],
                    'current_collaborators': project['current_collaborators'],
                    'status': project['status'],
                    'created_at': project['created_at'],
                    'is_open_for_collaboration': project['is_open_for_collaboration']
                })
            
            return result
            
        except Exception as e:
            print(f"Error getting user projects: {e}")
            return []

    def search_projects(self, query: str, user_id: str = None, filters: Dict = None) -> List[Dict]:
        """Search projects by text query and filters"""
        try:
            # Base query for public, open projects
            search_query = supabase.table('user_projects').select(
                'id, title, description, domain, required_skills, tech_stack, '
                'complexity_level, max_collaborators, current_collaborators, '
                'created_at, users!creator_id(full_name)'
            ).eq('is_public', True).eq('is_open_for_collaboration', True)
            
            # Text search using ilike for case-insensitive search
            search_query = search_query.or_(f'title.ilike.%{query}%,description.ilike.%{query}%,domain.ilike.%{query}%')
            
            # Exclude user's own projects
            if user_id:
                search_query = search_query.neq('creator_id', user_id)
            
            # Apply filters
            if filters:
                if filters.get('domain'):
                    search_query = search_query.eq('domain', filters['domain'])
                
                if filters.get('complexity_level'):
                    search_query = search_query.eq('complexity_level', filters['complexity_level'])
            
            # Execute query with limit
            result = search_query.order('created_at', desc=True).limit(50).execute()
            
            formatted_results = []
            for project in result.data:
                creator_name = project.get('users', {}).get('full_name', 'Unknown') if project.get('users') else 'Unknown'
                
                formatted_results.append({
                    'id': str(project['id']),
                    'title': project['title'],
                    'description': project['description'],
                    'domain': project['domain'],
                    'required_skills': project.get('required_skills', []),
                    'tech_stack': project.get('tech_stack', []),
                    'complexity_level': project['complexity_level'],
                    'max_collaborators': project['max_collaborators'],
                    'current_collaborators': project['current_collaborators'],
                    'creator_name': creator_name,
                    'created_at': project['created_at']
                })
            
            return formatted_results
            
        except Exception as e:
            print(f"Error searching projects: {e}")
            return []

    # Helper methods
    def _calculate_profile_compatibility(self, user_interests, user_languages, user_frameworks, project_skills, project_tech, project_domain):
        """Calculate compatibility score based on user profile and project requirements"""
        score = 0.0
        
        # Domain/Interest match (40% weight)
        if user_interests and project_domain:
            domain_match = any(interest.lower() in project_domain.lower() for interest in user_interests)
            if domain_match:
                score += 0.4
        
        # Programming language match (35% weight)
        if user_languages and project_tech:
            tech_list = project_tech if isinstance(project_tech, list) else []
            lang_matches = sum(1 for lang in user_languages if any(lang.lower() in tech.lower() for tech in tech_list))
            if tech_list:
                score += 0.35 * (lang_matches / len(tech_list))
        
        # Framework/Skills match (25% weight)
        if user_frameworks and project_skills:
            skill_list = project_skills if isinstance(project_skills, list) else []
            framework_matches = sum(1 for fw in user_frameworks if any(fw.lower() in skill.lower() for skill in skill_list))
            if skill_list:
                score += 0.25 * (framework_matches / len(skill_list))
        
        return min(score, 1.0)  # Cap at 1.0
    
    def _get_recent_projects(self, user_id: str, limit: int) -> List[Dict]:
        """Get recent projects when no profile data available"""
        try:
            # Get recent open projects excluding user's own
            projects_result = supabase.table('user_projects').select(
                'id, title, description, domain, required_skills, tech_stack, '
                'complexity_level, max_collaborators, current_collaborators, '
                'created_at, users!creator_id(full_name)'
            ).eq('is_open_for_collaboration', True).neq('creator_id', user_id).lt(
                'current_collaborators', supabase.table('user_projects').select('max_collaborators')
            ).in_('status', ['planning', 'active']).order('created_at', desc=True).limit(limit).execute()
            
            projects = []
            for p in projects_result.data:
                creator_name = p.get('users', {}).get('full_name', 'Unknown') if p.get('users') else 'Unknown'
                
                projects.append({
                    'id': str(p['id']), 
                    'title': p['title'], 
                    'description': p['description'],
                    'domain': p['domain'], 
                    'required_skills': p.get('required_skills', []),
                    'tech_stack': p.get('tech_stack', []), 
                    'complexity_level': p['complexity_level'],
                    'max_collaborators': p['max_collaborators'], 
                    'current_collaborators': p['current_collaborators'],
                    'creator_name': creator_name, 
                    'compatibility_score': 0.5,
                    'created_at': p['created_at']
                })
            
            return projects
            
        except Exception as e:
            print(f"Error getting recent projects: {e}")
            return []

    def is_available(self) -> bool:
        """Check if the service is available with all dependencies"""
        return SUPABASE_AVAILABLE
    
    def _notify_matching_users(self, project_id: str, project_data: Dict):
        """Notify users whose skills match the project requirements"""
        try:
            project_skills = set(skill.lower() for skill in (project_data.get('required_skills', []) or []))
            project_tech = set(tech.lower() for tech in (project_data.get('tech_stack', []) or []))
            all_project_requirements = project_skills | project_tech
            
            if not all_project_requirements:
                print("No skills specified for project, skipping notifications")
                return
            
            # Get all user profiles
            profiles_result = supabase.table('user_profiles').select(
                'user_id, programming_languages, frameworks_known, areas_of_interest'
            ).execute()
            
            if not profiles_result.data:
                return
            
            # Find matching users
            matching_users = []
            for profile in profiles_result.data:
                user_id = profile['user_id']
                
                # Skip project creator
                if user_id == project_data.get('creator_id'):
                    continue
                
                # Get user skills
                user_langs = set(lang.lower() for lang in (profile.get('programming_languages', []) or []))
                user_frameworks = set(fw.lower() for fw in (profile.get('frameworks_known', []) or []))
                user_interests = set(interest.lower() for interest in (profile.get('areas_of_interest', []) or []))
                all_user_skills = user_langs | user_frameworks | user_interests
                
                # Find matches
                matching_skills = all_user_skills & all_project_requirements
                
                if matching_skills and len(matching_skills) >= 2:  # At least 2 matching skills
                    matching_users.append({
                        'user_id': user_id,
                        'matching_skills': list(matching_skills)
                    })
            
            print(f"Found {len(matching_users)} users with matching skills")
            
            # Create notifications via collaboration_requests (as project_match_notification)
            for match in matching_users[:10]:  # Limit to top 10 matches
                try:
                    notification_record = {
                        'project_id': project_id,
                        'requester_id': match['user_id'],  # The user being notified
                        'project_owner_id': project_data.get('creator_id'),
                        'requested_role': '',
                        'cover_message': f"New project matches your skills: {', '.join(match['matching_skills'][:5])}",
                        'status': 'project_match_notification'
                    }
                    
                    supabase.table('collaboration_requests').insert(notification_record).execute()
                    print(f"✅ Notified user {match['user_id'][:8]}... about project match")
                except Exception as e:
                    print(f"Failed to notify user: {str(e)}")
                    continue
            
            print(f"✅ Sent {len(matching_users[:10])} project match notifications")
            
        except Exception as e:
            print(f"Error notifying matching users: {str(e)}")
            raise

# Create service instance
try:
    collaboration_service = CollaborationProjectService()
    print(f"✅ Collaboration service initialized (Supabase: {SUPABASE_AVAILABLE}, Embeddings: {EMBEDDINGS_AVAILABLE})")
except Exception as e:
    print(f"❌ Failed to initialize collaboration service: {e}")
    collaboration_service = None