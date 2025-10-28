# services/auth_service.py
"""
Authentication and User Management Service
"""
import bcrypt
from database.connection import supabase
import uuid

class AuthService:
    @staticmethod
    def hash_password(password):
        """Hash password using bcrypt"""
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    @staticmethod
    def verify_password(password, hashed):
        """Verify password against hash"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    
    @staticmethod
    def register_user(email, password, full_name):
        """Register new user"""
        try:
            # Check if user exists
            existing = supabase.table('users').select('id').eq('email', email).execute()
            if existing.data:
                return {'error': 'User already exists'}
            
            # Create user
            hashed_password = AuthService.hash_password(password)
            user_data = {
                'email': email,
                'password_hash': hashed_password,
                'full_name': full_name
            }
            
            result = supabase.table('users').insert(user_data).execute()
            if result.data:
                return {'success': True, 'user_id': result.data[0]['id']}
            
            return {'error': 'Failed to create user'}
            
        except Exception as e:
            return {'error': str(e)}
    
    @staticmethod
    def login_user(email, password):
        """Authenticate user login"""
        try:
            # Get user
            result = supabase.table('users').select('*').eq('email', email).execute()
            if not result.data:
                return {'error': 'Invalid credentials'}
            
            user = result.data[0]
            
            # Verify password
            if not AuthService.verify_password(password, user['password_hash']):
                return {'error': 'Invalid credentials'}
            
            # Update last login
            supabase.table('users').update({'last_login': 'NOW()'}).eq('id', user['id']).execute()
            
            return {'success': True, 'user': user}
            
        except Exception as e:
            return {'error': str(e)}
    
    @staticmethod
    def create_user_profile(user_id, profile_data):
        """Create user profile with skills/interests"""
        try:
            profile_data['user_id'] = user_id
            result = supabase.table('user_profiles').insert(profile_data).execute()
            return {'success': True, 'profile': result.data[0]} if result.data else {'error': 'Failed to create profile'}
        except Exception as e:
            return {'error': str(e)}