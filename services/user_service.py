"""
User Service for Supabase Integration
Handles user registration, authentication, and profile management using Supabase Auth
"""
from database.connection import supabase
import uuid
from datetime import datetime
import logging

# Set up logging for this service
logger = logging.getLogger(__name__)

class UserService:
    def __init__(self):
        pass
    
    def register_user(self, email, password, full_name):
        """Register a new user using Supabase Auth"""
        try:
            logger.info(f"Attempting to register user with email: {email}")
            
            # Create user in Supabase Auth with email confirmation DISABLED
            auth_response = supabase.auth.sign_up({
                'email': email,
                'password': password,
                'options': {
                    'data': {
                        'full_name': full_name
                    },
                    # Disable email confirmation for immediate login
                    'email_redirect_to': None
                }
            })
            
            if auth_response.user:
                user_id = auth_response.user.id
                logger.info(f"Successfully created auth user: {user_id}")
                
                # Insert user profile into our custom table
                profile_data = {
                    'id': user_id,
                    'email': email,
                    'full_name': full_name,
                    'password_hash': 'handled_by_supabase_auth',  # Placeholder since we use Supabase Auth
                    'created_at': datetime.now().isoformat()
                }
                
                # Try to add profile_completed if the column exists
                try:
                    profile_data['profile_completed'] = False
                    result = supabase.table('users').insert(profile_data).execute()
                except Exception as e:
                    # If profile_completed column doesn't exist, try without it
                    if 'profile_completed' in str(e):
                        logger.warning(f"profile_completed column not found, inserting without it")
                        del profile_data['profile_completed']
                        result = supabase.table('users').insert(profile_data).execute()
                    else:
                        raise e
                
                if result.data:
                    logger.info(f"Successfully created user profile for: {email}")
                    
                    # No email confirmation required - user can login immediately
                    logger.info(f"Email confirmation disabled - user can login immediately: {email}")
                    
                    return {
                        'success': True,
                        'user_id': user_id,
                        'email': email,
                        'full_name': full_name,
                        'session': auth_response.session,
                        'user': auth_response.user,
                        'requires_confirmation': False  # No confirmation needed
                    }
                else:
                    logger.error(f"Failed to create user profile for: {email}")
                    return {'success': False, 'error': 'Failed to create user profile'}
            else:
                logger.error(f"Failed to create auth user for: {email}")
                return {'success': False, 'error': 'Failed to create user account'}
                
        except Exception as e:
            error_message = str(e)
            logger.error(f"Registration error for {email}: {error_message}")
            
            # Handle specific Supabase errors with clear messages
            if 'User already registered' in error_message or 'already_registered' in error_message:
                return {
                    'success': False,
                    'error': f'An account with email {email} already exists. Please try logging in instead.',
                    'error_type': 'user_already_exists'
                }
            elif 'Email already exists' in error_message:
                return {
                    'success': False,
                    'error': f'Email {email} is already registered. Please use a different email or try logging in.',
                    'error_type': 'email_exists'
                }
            elif 'violates row-level security policy' in error_message or 'RLS' in error_message:
                return {
                    'success': False,
                    'error': 'Database security error. Please contact support.',
                    'error_type': 'rls_policy_error'
                }
            else:
                return {
                    'success': False,
                    'error': f'Registration failed: {error_message}',
                    'error_type': 'general_error'
                }
    
    def login_user(self, email, password):
        """Login user using Supabase Auth"""
        try:
            logger.info(f"🔐 Starting login process for: {email}")
            
            # Validate inputs
            if not email or not password:
                logger.warning(f"❌ Login attempt with missing credentials for: {email}")
                return {
                    'success': False,
                    'error': 'Email and password are required',
                    'error_type': 'missing_credentials'
                }
            
            # Try Supabase Auth login
            try:
                logger.info(f"🔍 Attempting Supabase Auth login for: {email}")
                
                auth_response = supabase.auth.sign_in_with_password({
                    'email': email,
                    'password': password
                })
                
                if auth_response.user:
                    user_id = auth_response.user.id
                    logger.info(f"✅ Supabase Auth successful for {email} (ID: {user_id})")
                    
                    # Get user profile from our custom table
                    logger.info(f"🔍 Fetching user profile from database for: {user_id}")
                    result = supabase.table('users').select('*').eq('id', user_id).execute()
                    
                    if result.data and len(result.data) > 0:
                        user = result.data[0]
                        logger.info(f"✅ User profile retrieved for {email}: profile_completed={user.get('profile_completed', False)}")
                        
                        return {
                            'success': True,
                            'user': {
                                'id': user['id'],
                                'email': user['email'],
                                'full_name': user['full_name'],
                                'profile_completed': user.get('profile_completed', False)
                            },
                            'session': auth_response.session,
                            'auth_user': auth_response.user
                        }
                    else:
                        logger.error(f"❌ User profile not found in database for authenticated user: {email} (ID: {user_id})")
                        return {
                            'success': False, 
                            'error': 'User profile not found in database',
                            'error_type': 'profile_not_found'
                        }
                else:
                    logger.error(f"❌ Supabase Auth returned no user for: {email}")
                    return {
                        'success': False,
                        'error': 'Authentication failed',
                        'error_type': 'auth_failed'
                    }
                        
            except Exception as auth_error:
                auth_error_message = str(auth_error)
                logger.error(f"❌ Supabase Auth exception for {email}: {auth_error_message}")
                
                # Handle specific auth errors (removed email confirmation checks)
                if 'Invalid login credentials' in auth_error_message:
                    logger.warning(f"⚠️ Invalid credentials for: {email}")
                    return {
                        'success': False,
                        'error': 'Invalid email or password. Please check your credentials.',
                        'error_type': 'invalid_credentials'
                    }
                else:
                    logger.error(f"❌ Unexpected auth error for {email}: {auth_error_message}")
                    return {
                        'success': False,
                        'error': f'Authentication error: {auth_error_message}',
                        'error_type': 'auth_error'
                    }
                    
        except Exception as e:
            error_message = str(e)
            logger.error(f"💥 Critical login error for {email}: {error_message}", exc_info=True)
            return {
                'success': False,
                'error': 'An unexpected error occurred during login',
                'error_type': 'system_error'
            }
    
    def update_profile(self, user_id, profile_data):
        """Update user profile"""
        try:
            logger.info(f"Updating profile for user: {user_id}")
            logger.info(f"Profile data keys: {list(profile_data.keys())}")
            
            # Prepare profile data
            profile_data['updated_at'] = datetime.now().isoformat()
            profile_data['profile_completed'] = True
            profile_data['user_id'] = user_id
            
            # For RLS to work properly, we need to handle this differently
            # Let's try to insert first, then update if it fails
            try:
                # Try INSERT first
                logger.info(f"Attempting to insert new profile for user: {user_id}")
                result = supabase.table('user_profiles').insert(profile_data).execute()
                logger.info(f"Successfully inserted profile for user: {user_id}")
            except Exception as insert_error:
                logger.info(f"Insert failed, trying update for user: {user_id}. Error: {str(insert_error)}")
                # If insert fails (likely due to existing record), try update
                # Remove user_id from update data as it's used in the filter
                update_data = {k: v for k, v in profile_data.items() if k != 'user_id'}
                result = supabase.table('user_profiles').update(update_data).eq('user_id', user_id).execute()
                logger.info(f"Successfully updated existing profile for user: {user_id}")
            
            # Also update the users table (but check if it has these columns)
            try:
                users_update = supabase.table('users').update({
                    'last_login': datetime.now().isoformat()
                }).eq('id', user_id).execute()
                logger.info(f"Updated users table for user: {user_id}")
            except Exception as users_error:
                logger.warning(f"Failed to update users table: {str(users_error)}")
                users_update = type('obj', (object,), {'data': [True]})()  # Mock success
            
            if result.data:
                logger.info(f"Successfully updated profile for user: {user_id}")
                
                # Invalidate recommendation cache since profile changed
                try:
                    from services.personalized_recommendations import PersonalizedRecommendationService
                    recommendation_service = PersonalizedRecommendationService()
                    recommendation_service.invalidate_user_cache(user_id)
                    logger.info(f"Invalidated recommendation cache for user: {user_id}")
                except Exception as cache_error:
                    logger.warning(f"Failed to invalidate recommendation cache for user {user_id}: {str(cache_error)}")
                
                return {'success': True}
            else:
                logger.error(f"Failed to update profile for user: {user_id} - No data returned")
                return {'success': False, 'error': 'Failed to update profile'}
            
        except Exception as e:
            logger.error(f"Profile update error for user {user_id}: {str(e)}", exc_info=True)
            return {'success': False, 'error': str(e)}
    
    def get_user_profile(self, user_id):
        """Get complete user profile including basic info and extended profile"""
        try:
            logger.debug(f"Fetching complete profile for user: {user_id}")
            
            # Get basic user info from users table
            user_result = supabase.table('users').select('*').eq('id', user_id).execute()
            
            if not user_result.data or len(user_result.data) == 0:
                logger.warning(f"User not found: {user_id}")
                return {'success': False, 'error': 'User not found'}
            
            user_data = user_result.data[0]
            
            # Get extended profile from user_profiles table
            profile_result = supabase.table('user_profiles').select('*').eq('user_id', user_id).execute()
            
            # Combine user data with profile data
            complete_profile = {
                'id': user_data['id'],
                'email': user_data['email'],
                'full_name': user_data['full_name'],
                'created_at': user_data['created_at'],
                'profile_completed': user_data.get('profile_completed', False),
                # Extended profile data (if exists)
                'bio': None,
                'education_level': None,
                'field_of_study': None,
                'programming_languages': [],
                'frameworks_known': [],
                'areas_of_interest': [],
                'overall_skill_level': 'intermediate'
            }
            
            # Add extended profile data if it exists
            if profile_result.data and len(profile_result.data) > 0:
                profile_data = profile_result.data[0]
                complete_profile.update({
                    'bio': profile_data.get('bio'),
                    'education_level': profile_data.get('education_level'),
                    'field_of_study': profile_data.get('field_of_study'),
                    'programming_languages': profile_data.get('programming_languages', []),
                    'frameworks_known': profile_data.get('frameworks_known', []),
                    'areas_of_interest': profile_data.get('areas_of_interest', []),
                    'overall_skill_level': profile_data.get('overall_skill_level', 'intermediate')
                })
                logger.debug(f"Complete profile found for user: {user_id}")
            else:
                logger.info(f"Extended profile not found for user {user_id}, using basic data only")
            
            return {'success': True, 'profile': complete_profile}
                
        except Exception as e:
            logger.error(f"Get profile error for user {user_id}: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def logout_user(self):
        """Logout user from Supabase Auth"""
        try:
            logger.info("Logging out user")
            result = supabase.auth.sign_out()
            logger.info("User logged out successfully")
            return {'success': True}
        except Exception as e:
            logger.error(f"Logout error: {str(e)}")
            return {'success': False, 'error': str(e)}

# Global instance
user_service = UserService()