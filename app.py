# app.py
"""
CoChain.ai - Complete Platform with GitHub Inspiration + Live Collaboration
============================================================================

User Flow:
1. Register → Fill Profile (with bio)
2. Dashboard → GitHub Projects (inspiration based on bio/interests)
3. Live Projects Tab → User Projects (seeking collaboration)
4. Admin Analytics → Track engagement on both systems (ADMIN ONLY)

Version: 3.0.1 - Fixed
"""

from flask import Flask, request, jsonify, render_template, session, redirect, url_for, flash, g
from functools import wraps
from datetime import datetime
import uuid
import os
import logging
import sys
import time

# Import services
from services.logging_service import get_logging_service, get_logger
from services.event_tracker import get_event_tracker
from services.performance_monitor import get_performance_monitor, RequestTimer

# Initialize logging and monitoring
logging_service = get_logging_service()
event_tracker = get_event_tracker()
perf_monitor = get_performance_monitor()
logger = get_logger('app')

# Import business services
from services.user_project_service import project_service
from services.user_service import UserService
from services.collaboration_service import collaboration_service
from database.connection import supabase

# Initialize Flask app
app = Flask(__name__)

# Secret key: Use environment variable in production, fallback only for development
SECRET_KEY = os.getenv('SECRET_KEY')
if not SECRET_KEY:
    if os.getenv('FLASK_ENV') == 'production':
        logger.error("❌ SECRET_KEY must be set in production!")
        raise ValueError("SECRET_KEY environment variable is required in production")
    else:
        logger.warning("⚠️ Using auto-generated SECRET_KEY (development only)")
        SECRET_KEY = os.urandom(24)

app.secret_key = SECRET_KEY
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Production security headers
if os.getenv('FLASK_ENV') == 'production':
    app.config['SESSION_COOKIE_SECURE'] = True  # HTTPS only
    logger.info("✅ Production security settings enabled")

# Set Flask app logger level
app.logger.setLevel(logging.INFO)

# Initialize services
user_service = UserService()

# Import and register API blueprints
try:
    from api.collaboration_routes import collaboration_bp
    collaboration_bp_available = True
except ImportError as e:
    logger.warning(f"Could not import collaboration_bp: {e}")
    collaboration_bp = None
    collaboration_bp_available = False

# Initialize recommendation service with error handling
# USE_RL_RECOMMENDATIONS: Toggle between RL (True) and similarity-only (False)
USE_RL_RECOMMENDATIONS = True  # Enable RL-enhanced recommendations
ENABLE_AUTO_TRAINING = False  # Disable automatic training - use A/B testing results instead
recommendation_service = None
background_task_scheduler = None

try:
    if USE_RL_RECOMMENDATIONS:
        # Use RL-enhanced recommendation engine (Thompson Sampling + Embeddings)
        from services.rl_recommendation_engine import get_rl_engine
        from services.background_tasks import get_task_scheduler
        
        recommendation_service = get_rl_engine()
        logger.info("✅ RL Recommendation Engine initialized successfully")
        
        # Initialize task scheduler (but don't start automatic training)
        # This allows manual training to be triggered from admin panel
        background_task_scheduler = get_task_scheduler()
        
        if ENABLE_AUTO_TRAINING:
            # Start automatic scheduled training
            background_task_scheduler.start()
            logger.info("✅ Automatic RL training enabled")
            logger.info("   - Daily model retraining: 2:00 AM")
            logger.info("   - Cache invalidation: Every 6 hours")
            logger.info("   - Performance monitoring: Every hour")
        else:
            logger.info("ℹ️  Automatic training disabled - Use A/B testing results to trigger training")
            logger.info("   - Manual training available via /api/admin/rl/trigger-training")
    else:
        # Use similarity-only recommendation service
        from services.personalized_recommendations import PersonalizedRecommendationService
        recommendation_service = PersonalizedRecommendationService()
        logger.info("✅ Similarity-based Recommendation service initialized successfully")
        
except Exception as e:
    logger.warning(f"⚠️ Failed to initialize recommendation service: {str(e)}")

# Admin emails - Load from environment variable
ADMIN_EMAILS = os.getenv('ADMIN_EMAILS', 'admin@cochain.ai').split(',')
ADMIN_EMAILS = [email.strip() for email in ADMIN_EMAILS]  # Remove any whitespace

logger.info("CoChain.ai - Complete Platform Starting...")
print("🚀 CoChain.ai - Complete Platform Starting...")

# Register API blueprints
if collaboration_bp_available:
    app.register_blueprint(collaboration_bp)
    logger.info("✅ Collaboration API routes registered")
else:
    logger.warning("⚠️ Collaboration API routes not available")

# ==================== DECORATORS ====================

def login_required(f):
    """Decorator to require login for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            logger.warning(f"Unauthorized access attempt to {request.endpoint} from {request.remote_addr}")
            flash('Please log in to access this page', 'warning')
            return redirect(url_for('login', next=request.url))
        
        logger.debug(f"Authorized access to {request.endpoint} by user {session.get('user_id')}")
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorator to require admin access"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            logger.warning(f"Unauthorized admin access attempt to {request.endpoint} from {request.remote_addr}")
            flash('Please log in to access this page', 'warning')
            return redirect(url_for('login'))
        
        user_email = session.get('user_email')
        if user_email not in ADMIN_EMAILS:
            logger.warning(f"Non-admin user {user_email} attempted to access {request.endpoint}")
            flash('Admin access required', 'error')
            return redirect(url_for('dashboard'))
        
        logger.info(f"Admin access granted to {request.endpoint} by {user_email}")
        return f(*args, **kwargs)
    return decorated_function

@app.before_request
def before_request():
    """Track request start time and log request"""
    g.start_time = time.time()
    g.request_id = str(uuid.uuid4())
    
    logger.info(
        f"Incoming request: {request.method} {request.path}",
        extra={
            'user_id': session.get('user_id'),
            'session_id': session.get('session_id'),
            'request_id': g.request_id,
            'ip_address': request.remote_addr
        }
    )
    
    # Update session last_activity for logged-in users on non-static requests
    if session.get('session_id') and not request.path.startswith('/static'):
        try:
            from datetime import datetime, timezone
            supabase.table('user_sessions').update({
                'last_activity': datetime.now(timezone.utc).isoformat()
            }).eq('session_id', session.get('session_id')).execute()
        except Exception as e:
            # Don't fail the request if session update fails
            logger.debug(f"Failed to update session activity: {str(e)}")

@app.after_request
def after_request(response):
    """Track request duration and log response"""
    if hasattr(g, 'start_time'):
        duration_ms = (time.time() - g.start_time) * 1000
        
        perf_monitor.track_api_request(
            endpoint=request.path,
            method=request.method,
            status_code=response.status_code,
            duration_ms=duration_ms,
            user_id=session.get('user_id'),
            ip_address=request.remote_addr
        )
        
        logger.info(
            f"Request completed: {request.method} {request.path} - {response.status_code} ({duration_ms:.2f}ms)",
            extra={
                'user_id': session.get('user_id'),
                'session_id': session.get('session_id'),
                'request_id': getattr(g, 'request_id', None),
                'duration_ms': duration_ms,
                'status_code': response.status_code
            }
        )
    
    return response

# ==================== PUBLIC ROUTES ====================

@app.route('/')
def index():
    """Landing page - redirect based on login status"""
    logger.info(f"Landing page accessed from {request.remote_addr}")
    if 'user_id' in session:
        logger.debug(f"Logged in user {session.get('user_id')} redirected to dashboard")
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/login-test')
def login_test():
    """Test page for login functionality and message display"""
    logger.info(f"Login test page accessed from {request.remote_addr}")
    return render_template('login_test.html')

@app.route('/about')
def about():
    """About Us page - team and project information"""
    logger.info(f"About page accessed from {request.remote_addr}")
    return render_template('about.html')

@app.route('/test-api')
def test_embedding_api():
    """Test endpoint to verify HuggingFace API is working"""
    try:
        from services.embeddings_api import get_embedding_client
        
        client = get_embedding_client()
        test_text = "python web development"
        
        logger.info(f"Testing API with text: {test_text}")
        embedding = client.encode(test_text, use_cache=False)
        
        if embedding is not None:
            return jsonify({
                'status': 'success',
                'message': 'HuggingFace API is working correctly',
                'dimensions': len(embedding),
                'sample': embedding[:5].tolist(),
                'api_url': client.api_url
            })
        else:
            logger.error("API test failed - embedding returned None")
            return jsonify({
                'status': 'error',
                'message': 'API returned None - check logs for details'
            }), 500
            
    except Exception as e:
        logger.error(f"Test API error: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'message': str(e),
            'type': type(e).__name__
        }), 500

@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration"""
    if 'user_id' in session:
        logger.debug(f"Already logged in user {session.get('user_id')} attempted to access register")
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        data = request.json if request.is_json else request.form
        email = data.get('email')
        
        logger.info(f"Registration attempt for email: {email}")
        
        result = user_service.register_user(
            email=email,
            password=data.get('password'),
            full_name=data.get('full_name')
        )
        
        if result.get('success'):
            logger.info(f"User registered successfully: {email}")
            
            session['user_id'] = result['user_id']
            session['user_email'] = result['email']
            session['user_name'] = result['full_name']
            session['profile_completed'] = False
            
            if 'session' in result and result['session']:
                session['auth_token'] = result['session'].access_token
                session['refresh_token'] = result['session'].refresh_token
            
            if request.is_json:
                return jsonify({
                    'success': True,
                    'message': 'Registration successful! Please complete your profile.',
                    'user_id': result['user_id'],
                    'redirect': url_for('profile_setup')
                })
            
            flash('Registration successful! Please complete your profile.', 'success')
            return redirect(url_for('profile_setup'))
        else:
            error_message = result.get('error', 'Registration failed')
            error_type = result.get('error_type', 'general')
            
            logger.error(f"Registration failed for {email}: {error_message}")
            
            if request.is_json:
                return jsonify({
                    'success': False,
                    'error': error_message,
                    'error_type': error_type
                }), 400
                
            if error_type == 'user_already_exists':
                flash('⚠️ Account already exists! Please try logging in instead.', 'warning')
            elif error_type == 'email_exists':
                flash('⚠️ Email already registered! Please use a different email or login.', 'warning')
            elif error_type == 'rls_policy_error':
                flash('⚠️ Database security error. Please try again or contact support.', 'error')
            else:
                flash(f'❌ Registration failed: {error_message}', 'error')
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login with enhanced logging"""
    if 'user_id' in session:
        logger.debug(f"Already logged in user {session.get('user_id')} redirected from login")
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        data = request.json if request.is_json else request.form
        email = data.get('email', '').strip()
        password = data.get('password', '')
        
        logger.info(f"🔐 Login attempt for email: {email}", extra={'ip_address': request.remote_addr})
        
        try:
            result = user_service.login_user(email=email, password=password)
            
            if result.get('success'):
                user = result['user']
                session['user_id'] = user['id']
                session['user_email'] = user['email']
                session['user_name'] = user['full_name']
                session['profile_completed'] = user.get('profile_completed', False)
                session['session_id'] = str(uuid.uuid4())
                
                event_tracker.track_session_start(
                    user_id=user['id'],
                    session_id=session['session_id'],
                    ip_address=request.remote_addr,
                    user_agent=request.headers.get('User-Agent')
                )
                
                logger.info(f"✅ Login successful for user {email}", extra={'user_id': user['id']})
                
                if request.is_json:
                    return jsonify({
                        'success': True,
                        'message': 'Login successful!',
                        'redirect': url_for('profile_setup') if not user.get('profile_completed') else url_for('dashboard')
                    })
                
                flash('Login successful! Welcome back!', 'success')
                return redirect(url_for('dashboard'))
            else:
                error_message = result.get('error', 'Login failed')
                logger.warning(f"❌ Login failed for {email}: {error_message}")
                
                if request.is_json:
                    return jsonify({'success': False, 'error': error_message}), 401
                
                flash(f'❌ Login failed: {error_message}', 'error')
                
        except Exception as e:
            logger.error(f"💥 Login error for {email}: {str(e)}", exc_info=True)
            
            if request.is_json:
                return jsonify({'success': False, 'error': 'An unexpected error occurred'}), 500
            
            flash('💥 An unexpected error occurred. Please try again.', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """User logout with session tracking"""
    user_email = session.get('user_email')
    session_id = session.get('session_id')
    
    logger.info(f"User logout: {user_email}")
    
    if session_id:
        event_tracker.track_session_end(session_id)
    
    user_service.logout_user()
    session.clear()
    flash('You have been logged out successfully', 'success')
    return redirect(url_for('index'))

# ==================== PROFILE MANAGEMENT ====================

@app.route('/profile/setup', methods=['GET', 'POST'])
@login_required
def profile_setup():
    """Profile setup/edit page"""
    user_id = session.get('user_id')
    
    if request.method == 'POST':
        data = request.json if request.is_json else request.form
        
        logger.info(f"Profile setup attempt for user: {user_id}")
        
        profile_data = {
            'education_level': data.get('education_level'),
            'current_year': data.get('current_year'),
            'field_of_study': data.get('field_of_study'),
            'bio': data.get('bio'),
            'linkedin_url': data.get('linkedin_url'),
            'github_url': data.get('github_url'),
            'overall_skill_level': data.get('overall_skill_level', 'intermediate'),
            'areas_of_interest': data.getlist('areas_of_interest') if hasattr(data, 'getlist') else data.get('areas_of_interest', []),
            'programming_languages': data.getlist('programming_languages') if hasattr(data, 'getlist') else data.get('programming_languages', []),
            'frameworks_known': data.getlist('frameworks_known') if hasattr(data, 'getlist') else data.get('frameworks_known', []),
            'learning_goals': data.get('learning_goals'),
            'profile_completed': True
        }
        
        result = user_service.update_profile(user_id, profile_data)
        
        if result.get('success'):
            session['profile_completed'] = True
            logger.info(f"Profile updated successfully for user: {user_id}")
            
            if request.is_json:
                return jsonify({'success': True})
            
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('dashboard'))
        else:
            logger.error(f"Profile update failed for user {user_id}: {result.get('error')}")
            if request.is_json:
                return jsonify({'success': False, 'error': result.get('error')})
            flash(f'Error updating profile: {result.get("error")}', 'error')
    
    interest_areas = [
        {'name': 'web_development', 'icon': 'fa-globe', 'description': 'Build websites and web applications'},
        {'name': 'mobile_development', 'icon': 'fa-mobile-alt', 'description': 'Create mobile apps for iOS and Android'},
        {'name': 'machine_learning', 'icon': 'fa-robot', 'description': 'AI, ML, and data science projects'},
        {'name': 'data_science', 'icon': 'fa-chart-bar', 'description': 'Data analysis and visualization'},
        {'name': 'game_development', 'icon': 'fa-gamepad', 'description': 'Create games and interactive experiences'},
        {'name': 'cybersecurity', 'icon': 'fa-shield-alt', 'description': 'Security, encryption, and ethical hacking'},
        {'name': 'blockchain', 'icon': 'fa-link', 'description': 'Cryptocurrency and decentralized applications'},
        {'name': 'iot', 'icon': 'fa-microchip', 'description': 'Internet of Things and embedded systems'},
        {'name': 'devops', 'icon': 'fa-cogs', 'description': 'Deployment, CI/CD, and infrastructure'},
        {'name': 'open_source', 'icon': 'fa-code-branch', 'description': 'Contributing to open source projects'},
        {'name': 'fintech', 'icon': 'fa-coins', 'description': 'Financial technology and trading systems'},
        {'name': 'healthtech', 'icon': 'fa-heartbeat', 'description': 'Healthcare and medical technology'}
    ]
    
    return render_template('profile_setup.html', interest_areas=interest_areas)

@app.route('/profile')
@login_required
def profile():
    """View user profile"""
    user_id = session.get('user_id')
    
    try:
        user_profile = user_service.get_user_profile(user_id)
        
        if user_profile.get('success'):
            user_data = user_profile['profile']
            
            # Ensure session has the correct profile_completed status
            # This prevents losing the flag when navigating to profile page
            if user_data.get('profile_completed') and not session.get('profile_completed'):
                session['profile_completed'] = True
                logger.info(f"Restored profile_completed flag in session for user {user_id}")
            
            stats = {
                'total_queries': 0,
                'total_bookmarks': 0,
                'projects_saved': 0
            }
            
            logger.info(f"Profile page accessed by user: {user_data.get('email')}")
            
            return render_template('profile.html', 
                                 user=user_data,
                                 total_queries=stats['total_queries'],
                                 total_bookmarks=stats['total_bookmarks'],
                                 projects_saved=stats['projects_saved'])
        else:
            logger.error(f"Failed to get profile for user {user_id}: {user_profile.get('error')}")
            flash('Unable to load profile. Please try again.', 'error')
            return redirect(url_for('dashboard'))
            
    except Exception as e:
        logger.error(f"Profile page error for user {user_id}: {str(e)}")
        flash('An error occurred while loading your profile.', 'error')
        return redirect(url_for('dashboard'))

@app.route('/profile/<user_id>')
@login_required
def user_portfolio(user_id):
    """View another user's portfolio with their created and joined projects"""
    current_user_id = session.get('user_id')
    
    try:
        from database.connection import supabase_admin
        
        # Get user profile information using admin client to bypass RLS
        user_result = supabase_admin.table('users').select('*').eq('id', user_id).execute()
        
        if not user_result.data or len(user_result.data) == 0:
            flash('User profile not found', 'error')
            return redirect(url_for('explore'))
        
        user_data = user_result.data[0]
        
        # Get extended profile from user_profiles table
        profile_result = supabase_admin.table('user_profiles').select('*').eq('user_id', user_id).execute()
        
        # Combine user data with profile data
        portfolio_user = {
            'id': user_data['id'],
            'email': user_data['email'],
            'full_name': user_data['full_name'],
            'created_at': user_data['created_at'],
            'profile_completed': user_data.get('profile_completed', False),
            'bio': None,
            'linkedin_url': None,
            'github_url': None,
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
            portfolio_user.update({
                'bio': profile_data.get('bio'),
                'linkedin_url': profile_data.get('linkedin_url'),
                'github_url': profile_data.get('github_url'),
                'education_level': profile_data.get('education_level'),
                'field_of_study': profile_data.get('field_of_study'),
                'programming_languages': profile_data.get('programming_languages', []),
                'frameworks_known': profile_data.get('frameworks_known', []),
                'areas_of_interest': profile_data.get('areas_of_interest', []),
                'overall_skill_level': profile_data.get('overall_skill_level', 'intermediate')
            })
        
        # Get projects created by this user
        created_projects = supabase_admin.table('user_projects').select(
            'id, title, description, domain, tech_stack, required_skills, complexity_level, '
            'current_collaborators, max_collaborators, status, created_at, is_open_for_collaboration'
        ).eq('creator_id', user_id).order('created_at', desc=True).execute()
        
        # Get projects this user has joined (from project_members table)
        members_result = supabase_admin.table('project_members').select(
            'project_id, role, joined_at'
        ).eq('user_id', user_id).eq('is_active', True).execute()
        
        logger.info(f"Found {len(members_result.data) if members_result.data else 0} project memberships for user {user_id}")
        
        # Format joined projects by fetching full project details
        joined_projects = []
        if members_result.data:
            for member in members_result.data:
                project_id = member['project_id']
                # Get full project details
                project_result = supabase_admin.table('user_projects').select(
                    'id, title, description, domain, tech_stack, required_skills, '
                    'complexity_level, current_collaborators, max_collaborators, status, created_at, creator_id'
                ).eq('id', project_id).execute()
                
                if project_result.data and len(project_result.data) > 0:
                    project_info = project_result.data[0]
                    logger.info(f"Project {project_id}: creator={project_info.get('creator_id')}, viewing_user={user_id}")
                    # Exclude if user is the creator (those are in created_projects)
                    if project_info.get('creator_id') != user_id:
                        project_info['member_role'] = member.get('role', 'Team Member')
                        project_info['joined_at'] = member.get('joined_at')
                        joined_projects.append(project_info)
                        logger.info(f"Added joined project: {project_info['title']}")
                    else:
                        logger.info(f"Skipped project {project_id} - user is creator")
        
        # Sort joined projects by join date
        joined_projects.sort(key=lambda x: x.get('joined_at', ''), reverse=True)
        
        logger.info(f"Portfolio page accessed: {user_id} viewed by {current_user_id}")
        logger.info(f"Created projects: {len(created_projects.data) if created_projects.data else 0}, Joined projects: {len(joined_projects)}")
        
        return render_template('user_portfolio.html',
                             portfolio_user=portfolio_user,
                             created_projects=created_projects.data if created_projects.data else [],
                             joined_projects=joined_projects,
                             is_own_profile=(current_user_id == user_id))
        
    except Exception as e:
        logger.error(f"Error loading portfolio for user {user_id}: {str(e)}", exc_info=True)
        flash(f'Error loading user portfolio: {str(e)}', 'error')
        return redirect(url_for('explore'))

# ==================== MAIN USER ROUTES ====================

@app.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard with enhanced logging and event tracking"""
    user_id = session.get('user_id')
    
    with RequestTimer('dashboard_load', perf_monitor, 'page_load', user_id=user_id):
        logger.info(f"Dashboard accessed by user {user_id}")
        
        event_tracker.track_page_view(
            page_name='dashboard',
            user_id=user_id,
            session_id=session.get('session_id'),
            referrer=request.referrer
        )
        
        if not session.get('profile_completed'):
            # Double-check with database before redirecting
            # This prevents false redirects if session was lost
            try:
                profile_check = user_service.get_user_profile(user_id)
                if profile_check.get('success') and profile_check['profile'].get('profile_completed'):
                    # Profile is actually completed, restore session flag
                    session['profile_completed'] = True
                    logger.info(f"Restored profile_completed flag from database for user {user_id}")
                else:
                    # Profile truly not completed, redirect to setup
                    logger.info(f"User {user_id} redirected to profile setup")
                    flash('Please complete your profile first', 'warning')
                    return redirect(url_for('profile_setup'))
            except Exception as check_error:
                logger.error(f"Error checking profile completion for {user_id}: {str(check_error)}")
                # On error, redirect to profile setup to be safe
                logger.info(f"User {user_id} redirected to profile setup due to check error")
                flash('Please complete your profile first', 'warning')
                return redirect(url_for('profile_setup'))
        
        try:
            profile_result = user_service.get_user_profile(user_id)
            
            if profile_result.get('success'):
                user_profile = profile_result['profile']
                logger.debug(f"User profile retrieved for {user_id}")
            else:
                logger.warning(f"Could not retrieve profile for {user_id}")
                user_profile = {
                    'areas_of_interest': ['web_development'],
                    'programming_languages': ['Python'],
                    'overall_skill_level': 'intermediate'
                }
            
            recommendations = []
            if recommendation_service:
                start_time = time.time()
                
                # Check A/B test assignment to determine which recommendation method to use
                use_rl_for_user = True  # Default to RL
                ab_test_group = None
                
                if USE_RL_RECOMMENDATIONS:
                    try:
                        from services.ab_test_service import get_ab_test_service
                        ab_service = get_ab_test_service()
                        use_rl_for_user = ab_service.should_use_rl(user_id)
                        ab_test_group = ab_service.get_user_group(user_id)
                        logger.debug(f"A/B Test: User {user_id} assigned to group '{ab_test_group}', use_rl={use_rl_for_user}")
                    except Exception as e:
                        logger.warning(f"A/B test check failed, defaulting to RL: {e}")
                        use_rl_for_user = True
                
                # Use appropriate method based on A/B test assignment
                if USE_RL_RECOMMENDATIONS and use_rl_for_user:
                    # RL Engine uses get_recommendations method
                    recommendations_result = recommendation_service.get_recommendations(
                        user_id=user_id, 
                        num_recommendations=12,
                        use_rl=True,  # Enable RL re-ranking
                        offset=0
                    )
                else:
                    # Baseline: Use similarity-only recommendations (no RL re-ranking)
                    if hasattr(recommendation_service, 'base_recommender'):
                        # RL engine exists but use baseline recommender
                        recommendations_result = recommendation_service.base_recommender.get_recommendations_for_user(
                            user_id, 
                            num_recommendations=12
                        )
                    elif hasattr(recommendation_service, 'get_recommendations'):
                        # Use RL engine but disable RL re-ranking
                        recommendations_result = recommendation_service.get_recommendations(
                            user_id=user_id,
                            num_recommendations=12,
                            use_rl=False,  # Disable RL re-ranking for control group
                            offset=0
                        )
                    else:
                        # Fallback to similarity-only service
                        recommendations_result = recommendation_service.get_recommendations_for_user(
                            user_id, 
                            num_recommendations=12
                        )
                
                rec_duration_ms = (time.time() - start_time) * 1000
                
                if isinstance(recommendations_result, dict) and recommendations_result.get('success'):
                    recommendations = recommendations_result.get('recommendations', [])
                    cache_hit = recommendations_result.get('cached', False)
                    
                    perf_monitor.track_recommendation_generation(
                        user_id=user_id,
                        num_recommendations=len(recommendations),
                        duration_ms=rec_duration_ms,
                        cache_hit=cache_hit
                    )
                    
                    event_tracker.track_recommendation_impression(
                        user_id=user_id,
                        recommendations=recommendations,
                        session_id=session.get('session_id'),
                        source='dashboard'
                    )
                    
                    method_used = 'RL' if (USE_RL_RECOMMENDATIONS and use_rl_for_user) else 'Baseline'
                    logger.info(
                        f"Retrieved {len(recommendations)} recommendations for user {user_id} "
                        f"({'from cache' if cache_hit else 'fresh'}) in {rec_duration_ms:.2f}ms "
                        f"(Method: {method_used}, A/B Group: {ab_test_group or 'N/A'})"
                    )
                else:
                    logger.warning(f"No recommendations retrieved for user {user_id}")
            
            event_tracker.track_session_activity(
                session_id=session.get('session_id'),
                activity_type='dashboard_view',
                github_viewed=True
            )
            
            return render_template(
                'dashboard.html',
                recommendations=recommendations,
                user_interests=user_profile.get('areas_of_interest', [])
            )
            
        except Exception as e:
            logger.error(f"Dashboard error for user {user_id}: {str(e)}", exc_info=True)
            flash('An error occurred while loading the dashboard', 'error')
            return render_template('dashboard.html', recommendations=[])

@app.route('/debug-session')
@login_required
def debug_session():
    """Debug endpoint to check session data"""
    session_data = {
        'user_id': session.get('user_id'),
        'user_email': session.get('user_email'),
        'user_name': session.get('user_name'),
        'profile_completed': session.get('profile_completed'),
        'session_id': session.get('session_id'),
        'is_admin': session.get('user_email') in ADMIN_EMAILS
    }
    
    return jsonify({
        'success': True,
        'session': session_data,
        'admin_emails': ADMIN_EMAILS
    })

@app.route('/debug-projects')
@login_required
def debug_projects():
    """Debug projects data"""
    user_id = session.get('user_id')
    try:
        # Test all project retrieval methods
        projects1 = collaboration_service.get_projects_by_user_interests(user_id, limit=10)
        projects2 = collaboration_service.get_all_available_projects(user_id, limit=10)
        
        return jsonify({
            'user_id': user_id,
            'projects_by_interests': len(projects1),
            'all_projects': len(projects2),
            'sample_projects': projects2[:2] if projects2 else []
        })
    except Exception as e:
        return jsonify({
            'error': str(e),
            'user_id': user_id
        })

@app.route('/debug-user-profile/<user_email>')
@login_required
def debug_user_profile(user_email):
    """Debug user profile and projects"""
    try:
        from database.connection import supabase_admin
        
        # Get user by email
        user_result = supabase_admin.table('users').select('id, email, full_name').eq('email', user_email).execute()
        if not user_result.data:
            return jsonify({'error': 'User not found', 'email': user_email})
        
        user = user_result.data[0]
        user_id = user['id']
        
        # Get user profile
        profile_result = supabase_admin.table('user_profiles').select('areas_of_interest, programming_languages').eq('user_id', user_id).execute()
        profile = profile_result.data[0] if profile_result.data else None
        
        # Get all projects
        all_projects_result = supabase_admin.table('user_projects').select(
            'id, title, creator_id, required_skills, domain, is_public, is_open_for_collaboration, users!creator_id(email, full_name)'
        ).eq('is_public', True).eq('is_open_for_collaboration', True).neq('creator_id', user_id).execute()
        
        projects_info = []
        for proj in all_projects_result.data:
            creator_info = proj.get('users', {})
            projects_info.append({
                'title': proj['title'],
                'creator': creator_info.get('email', 'Unknown') if creator_info else 'Unknown',
                'creator_name': creator_info.get('full_name', 'Unknown') if creator_info else 'Unknown',
                'required_skills': proj.get('required_skills', []),
                'domain': proj.get('domain', ''),
                'matches_user': bool(set(profile.get('areas_of_interest', []) + profile.get('programming_languages', [])) & set(proj.get('required_skills', []))) if profile else False
            })
        
        return jsonify({
            'user': {
                'id': user_id,
                'email': user['email'],
                'full_name': user['full_name']
            },
            'profile': {
                'areas_of_interest': profile.get('areas_of_interest', []) if profile else [],
                'programming_languages': profile.get('programming_languages', []) if profile else []
            },
            'all_projects': projects_info
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            'error': str(e),
            'traceback': traceback.format_exc()
        })

@app.route('/debug-matching/<project_id>')
@login_required
def debug_matching(project_id):
    """Debug endpoint to test matching algorithm for a specific project"""
    try:
        # Get project details
        project = collaboration_service.get_project_by_id(project_id)
        if not project:
            return jsonify({'error': 'Project not found'})
        
        # Get project's required skills and domain
        project_skills = project.get('required_skills', [])
        project_domain = project.get('domain', '')
        
        # Convert to lowercase and create keyword sets
        project_keywords = set()
        if project_domain:
            project_keywords.update(project_domain.lower().replace('_', ' ').replace('-', ' ').split())
        for skill in project_skills:
            project_keywords.update(skill.lower().replace('_', ' ').replace('-', ' ').split())
        
        # Get all user profiles (except creator)
        profiles_result = supabase.table('user_profiles').select(
            'user_id, areas_of_interest, programming_languages'
        ).neq('user_id', project['creator_id']).execute()
        
        matching_details = []
        for profile in profiles_result.data if profiles_result.data else []:
            user_interests = profile.get('areas_of_interest', []) or []
            user_languages = profile.get('programming_languages', []) or []
            
            # Create user keywords
            user_keywords = set()
            for interest in user_interests:
                user_keywords.update(interest.lower().replace('_', ' ').replace('-', ' ').split())
            for lang in user_languages:
                user_keywords.update(lang.lower().replace('_', ' ').replace('-', ' ').split())
            
            # Check for matches
            common_keywords = project_keywords & user_keywords
            has_match = bool(common_keywords)
            
            matching_details.append({
                'user_id': profile['user_id'],
                'interests': user_interests,
                'languages': user_languages,
                'user_keywords': list(user_keywords),
                'common_keywords': list(common_keywords),
                'has_match': has_match
            })
        
        return jsonify({
            'project_id': project_id,
            'project_title': project.get('title'),
            'project_domain': project_domain,
            'project_skills': project_skills,
            'project_keywords': list(project_keywords),
            'total_users_checked': len(matching_details),
            'matching_users': [d for d in matching_details if d['has_match']],
            'non_matching_users': [d for d in matching_details if not d['has_match']]
        })
        
    except Exception as e:
        logger.error(f"Debug matching error: {str(e)}", exc_info=True)
        return jsonify({'error': str(e)})

@app.route('/live-projects')
@login_required
def live_projects():
    """Live Projects page - Topic-based collaboration projects personalized for user"""
    user_id = session.get('user_id')
    
    logger.debug(f"Live projects accessed by user: {user_id}")
    
    try:
        # Get projects from other users with similar areas of interest ONLY
        projects = collaboration_service.get_projects_by_user_interests(user_id, limit=50)
        logger.info(f"Retrieved {len(projects)} interest-based projects for user: {user_id}")
        
        # Get unique domains from projects for filtering
        domains = list(set(p.get('domain', '') for p in projects if p.get('domain')))
        domains.sort()
        topics_by_category = {'Web Development': domains[:5], 'Mobile': domains[5:10]} if domains else {}
        
        # Debug: Print project data to console
        print(f"DEBUG: Found {len(projects)} projects for user {user_id}")
        for p in projects:
            print(f"  - {p.get('title', 'No title')} by {p.get('creator_name', 'No creator')}")
        
    except Exception as e:
        logger.error(f"Error getting live projects: {str(e)}")
        print(f"DEBUG: Error getting projects: {e}")
        projects = []
        topics_by_category = {}
    
    return render_template('live_projects.html', 
                         projects=projects, 
                         topics_by_category=topics_by_category,
                         page_title="Live Projects - Find Your Next Collaboration",
                         user_id=user_id)

@app.route('/live-projects/<project_id>')
@login_required
def project_detail(project_id):
    """View detailed project information"""
    user_id = session.get('user_id')
    
    try:
        # Get project details
        project = collaboration_service.get_project_by_id(project_id)
        
        if not project:
            flash('Project not found', 'error')
            return redirect(url_for('live_projects'))
        
        # Check if user can join this project
        join_eligibility = collaboration_service.can_user_join_project(user_id, project_id)
        
        # Get team members
        team_members = collaboration_service.get_project_team_members(project_id)
        
        # Check if current user is a team member (including creator)
        is_team_member = any(member['user_id'] == user_id for member in team_members) if team_members else False
        
        # Get creator information
        creator_name = None
        creator_email = None
        if project.get('creator_id'):
            try:
                from database.connection import supabase_admin
                creator_info = supabase_admin.table('users').select('full_name, email').eq('id', project['creator_id']).execute()
                if creator_info.data:
                    creator_name = creator_info.data[0].get('full_name')
                    creator_email = creator_info.data[0].get('email')
            except Exception as e:
                logger.error(f"Error fetching creator info: {str(e)}")
        
        # Track project view
        event_tracker.track_project_view(
            user_id=user_id,
            project_id=project_id,
            session_id=session.get('session_id')
        )
        
        logger.info(f"Project detail page accessed: {project_id} by user {user_id}")
        return render_template('project_detail.html', 
                             project=project, 
                             join_eligibility=join_eligibility,
                             team_members=team_members,
                             is_team_member=is_team_member,
                             creator_name=creator_name,
                             creator_email=creator_email)
        
    except Exception as e:
        logger.error(f"Error loading project {project_id}: {str(e)}")
        flash('Error loading project details', 'error')
        return redirect(url_for('live_projects'))

@app.route('/request-join/<project_id>', methods=['POST'])
@login_required
def request_join_project(project_id):
    """Send a request to join a project"""
    user_id = session.get('user_id')
    
    try:
        # Check eligibility
        eligibility = collaboration_service.can_user_join_project(user_id, project_id)
        if not eligibility['can_join']:
            reason = eligibility["reason"]
            # Show as info if it's about a pending request, otherwise show as error
            if 'already sent' in reason.lower() or 'pending' in reason.lower():
                flash(f'✅ {reason}', 'info')
            else:
                flash(f'Cannot join project: {reason}', 'error')
            return redirect(url_for('project_detail', project_id=project_id))
        
        # Get project to find creator
        project = collaboration_service.get_project_by_id(project_id)
        if not project:
            flash('Project not found', 'error')
            return redirect(url_for('live_projects'))
        
        # Create join request
        message = request.form.get('message', '')
        request_data = {
            'project_id': project_id,
            'requester_id': user_id,
            'message': message,
            'requested_role': 'Team Member',
            'status': 'pending'
        }
        
        request_id = collaboration_service.send_collaboration_request(user_id, project_id, request_data)
        
        # Handle different response statuses
        if request_id == 'DUPLICATE_PENDING':
            flash('✅ Request already sent! The project owner will review your request soon.', 'info')
            logger.info(f"User {user_id} attempted duplicate request for project {project_id}")
        elif request_id == 'ALREADY_MEMBER':
            flash('You are already a member of this project!', 'info')
            logger.info(f"User {user_id} is already member of project {project_id}")
        elif request_id:
            # Send push notification to project creator
            send_push_notification(
                user_id=project['creator_id'],
                title=f'🤝 New Join Request',
                body=f'{session.get("user_name", "Someone")} wants to join "{project["title"]}"',
                notification_type='join_request',
                url=f'/notifications',
                icon='/static/images/collaboration-icon.png'
            )
            
            flash('✅ Join request sent successfully! You will be notified when the project owner responds.', 'success')
            logger.info(f"User {user_id} requested to join project {project_id}")
        else:
            flash('❌ Error sending join request. Please try again.', 'error')
            
    except Exception as e:
        logger.error(f"Error processing join request: {str(e)}")
        flash('❌ Error processing join request. Please try again.', 'error')
    
    return redirect(url_for('project_detail', project_id=project_id))

@app.route('/notifications')
@login_required
def notifications():
    """User notifications page - shows collaboration requests as notifications"""
    user_id = session.get('user_id')
    
    try:
        from database.connection import supabase_admin
        
        user_notifications = []
        
        # Use supabase_admin to bypass RLS and avoid infinite recursion
        # 1. Get collaboration requests for user's projects (incoming requests to projects they own)
        projects_result = supabase_admin.table('user_projects').select('id, title').eq('creator_id', user_id).execute()
        project_ids = [p['id'] for p in projects_result.data] if projects_result.data else []
        
        if project_ids:
            # Get collaboration requests for these projects with requester info
            requests_result = supabase_admin.table('collaboration_requests').select(
                '*, users!requester_id(full_name, email)'
            ).in_('project_id', project_ids).eq('status', 'pending').order('created_at', desc=True).execute()
            
            # Convert collaboration requests to notification format
            for req in requests_result.data if requests_result.data else []:
                project_title = next((p['title'] for p in projects_result.data if p['id'] == req['project_id']), 'Unknown Project')
                requester_info = req.get('users', {}) if req.get('users') else {}
                requester_name = requester_info.get('full_name', 'Someone')
                request_message = req.get('cover_message', '')
                base_message = f"{requester_name} wants to join your project '{project_title}'"
                full_message = f"{base_message}. Message: {request_message}" if request_message else base_message
                
                user_notifications.append({
                    'id': req['id'],
                    'type': 'join_request',
                    'title': f"Join Request for {project_title}",
                    'message': full_message,
                    'created_at': req['created_at'],
                    'is_read': True,  # All notifications are marked as read when page is viewed
                    'data': {
                        'request_id': req['id'],
                        'project_id': req['project_id'],
                        'requester_name': requester_name,
                        'requester_id': req['requester_id']
                    }
                })
        
        # 2. Get responses to user's own requests (notifications about accepted/rejected requests)
        responses_result = supabase_admin.table('collaboration_requests').select(
            '*, user_projects!project_id(title, creator_id)'
        ).eq('project_owner_id', user_id).in_('status', ['notification_accepted', 'notification_rejected']).order('created_at', desc=True).execute()
        
        for resp in responses_result.data if responses_result.data else []:
            project_info = resp.get('user_projects', {}) if resp.get('user_projects') else {}
            project_title = project_info.get('title', 'Unknown Project')
            message = resp.get('cover_message', '')
            status = resp['status']
            
            if status == 'notification_accepted':
                user_notifications.append({
                    'id': resp['id'],
                    'type': 'request_accepted',
                    'title': f"Request Accepted - {project_title}",
                    'message': message,
                    'created_at': resp['created_at'],
                    'is_read': True,  # All notifications are marked as read when page is viewed
                    'data': {
                        'project_id': resp['project_id'],
                        'url': f"/live-projects/{resp['project_id']}"
                    }
                })
            elif status == 'notification_rejected':
                user_notifications.append({
                    'id': resp['id'],
                    'type': 'request_rejected',
                    'title': f"Request Update - {project_title}",
                    'message': message,
                    'created_at': resp['created_at'],
                    'is_read': True,  # All notifications are marked as read when page is viewed
                    'data': {}
                })
        
        # 3. Get project match notifications
        match_notifications = supabase_admin.table('collaboration_requests').select(
            '*, user_projects!project_id(title, description, domain, creator_id)'
        ).eq('project_owner_id', user_id).eq('status', 'project_match_notification').order('created_at', desc=True).execute()
        
        for match in match_notifications.data if match_notifications.data else []:
            project_info = match.get('user_projects', {}) if match.get('user_projects') else {}
            project_title = project_info.get('title', 'New Project')
            project_domain = project_info.get('domain', 'N/A')
            
            user_notifications.append({
                'id': match['id'],
                'type': 'project_match',
                'title': f"🎯 New Project Match: {project_title}",
                'message': match.get('cover_message', f'A new project in {project_domain} matches your interests!'),
                'created_at': match['created_at'],
                'is_read': True,  # All notifications are marked as read when page is viewed
                'data': {
                    'project_id': match['project_id'],
                    'url': f"/live-projects/{match['project_id']}"
                }
            })
        
        # Sort all notifications by created_at
        user_notifications.sort(key=lambda x: x['created_at'], reverse=True)
        logger.info(f"Retrieved {len(user_notifications)} total notifications for user {user_id}")
        
        # Mark all notifications as read by inserting notification_read records
        all_notification_ids = []
        for notif in user_notifications:
            if notif.get('id'):
                all_notification_ids.append(notif['id'])
        
        if all_notification_ids:
            try:
                # Check which notifications haven't been marked as read yet
                existing_reads = supabase_admin.table('user_interactions').select('additional_data').eq(
                    'user_id', user_id
                ).eq('interaction_type', 'notification_read').execute()
                
                existing_ids = set()
                if existing_reads.data:
                    for r in existing_reads.data:
                        if r.get('additional_data', {}).get('notification_id'):
                            existing_ids.add(r['additional_data']['notification_id'])
                
                # Insert new read records
                interactions_to_insert = []
                for notification_id in all_notification_ids:
                    if notification_id not in existing_ids:
                        interactions_to_insert.append({
                            'user_id': user_id,
                            'interaction_type': 'notification_read',
                            'interaction_time': datetime.now().isoformat(),
                            'additional_data': {'notification_id': notification_id}
                        })
                
                if interactions_to_insert:
                    supabase_admin.table('user_interactions').insert(interactions_to_insert).execute()
                    logger.info(f"Marked {len(interactions_to_insert)} notifications as read for user {user_id}")
            except Exception as e:
                logger.warning(f"Failed to mark notifications as read: {str(e)}")
        
    except Exception as e:
        logger.error(f"Error retrieving notifications: {str(e)}", exc_info=True)
        user_notifications = []
        flash('Error loading notifications', 'error')
    
    return render_template('notifications.html', notifications=user_notifications)

@app.route('/respond-join-request/<request_id>/<action>')
@login_required
def respond_join_request(request_id, action):
    """Accept or reject a join request"""
    user_id = session.get('user_id')
    
    if action not in ['accept', 'reject']:
        flash('Invalid action', 'error')
        return redirect(url_for('notifications'))
    
    try:
        # Get the collaboration request directly from collaboration_requests table
        collab_result = supabase.table('collaboration_requests').select('*').eq('id', request_id).eq('project_owner_id', user_id).execute()
        
        if not collab_result.data:
            flash('Request not found', 'error')
            return redirect(url_for('notifications'))
        
        collaboration_request = collab_result.data[0]
        project_id = collaboration_request['project_id']
        requester_id = collaboration_request['requester_id']
        
        # Verify user is project owner
        project = collaboration_service.get_project_by_id(project_id)
        if not project or project['creator_id'] != user_id:
            flash('You are not authorized to respond to this request', 'error')
            return redirect(url_for('notifications'))
        
        # Update request status
        response_message = request.args.get('message', '')
        success = collaboration_service.respond_to_collaboration_request(
            request_id, action, response_message
        )
        
        if success:
            if action == 'accept':
                # Create notification record for requester (accepted)
                supabase.table('collaboration_requests').insert({
                    'project_id': project_id,
                    'requester_id': user_id,  # Project owner is now the "requester"
                    'project_owner_id': requester_id,  # Original requester receives it
                    'cover_message': f'Your request to join "{project["title"]}" has been accepted! Welcome to the team.',
                    'status': 'notification_accepted',
                    'requested_role': 'Notification'
                }).execute()
                
                flash('Join request accepted! User has been added to your project.', 'success')
            else:
                # Create notification record for requester (rejected)
                supabase.table('collaboration_requests').insert({
                    'project_id': project_id,
                    'requester_id': user_id,  # Project owner is now the "requester"
                    'project_owner_id': requester_id,  # Original requester receives it
                    'cover_message': f'Your request to join "{project["title"]}" was not accepted this time. Keep exploring other projects!',
                    'status': 'notification_rejected',
                    'requested_role': 'Notification'
                }).execute()
                
                flash('Join request rejected.', 'success')
        else:
            flash('Error processing request', 'error')
            
    except Exception as e:
        logger.error(f"Error responding to join request: {str(e)}")
        flash('Error processing request', 'error')
    
    return redirect(url_for('notifications'))

@app.route('/my-projects')
@login_required
def my_projects():
    """User's own projects"""
    user_id = session.get('user_id')
    
    logger.debug(f"My projects page accessed by user: {user_id}")
    
    try:
        from database.connection import supabase_admin
        
        # Get user's created projects
        created_projects = collaboration_service.get_user_projects(user_id)
        logger.info(f"Retrieved {len(created_projects)} created projects for user {user_id}")
        
        # Get projects where user is a member (joined projects) - use admin client to bypass RLS
        members_result = supabase_admin.table('project_members').select(
            'project_id, role, joined_at'
        ).eq('user_id', user_id).eq('is_active', True).execute()
        
        joined_projects = []
        if members_result.data:
            project_ids = [m['project_id'] for m in members_result.data]
            # Get project details for joined projects
            for member in members_result.data:
                project = collaboration_service.get_project_by_id(member['project_id'])
                if project and project['creator_id'] != user_id:  # Exclude own projects
                    project['user_role'] = member['role']
                    project['joined_at'] = member['joined_at']
                    joined_projects.append(project)
        
        logger.info(f"Retrieved {len(joined_projects)} joined projects for user {user_id}")
        
    except Exception as e:
        logger.error(f"Error retrieving projects for user {user_id}: {str(e)}")
        created_projects = []
        joined_projects = []
        flash('Error loading projects', 'error')
    
    return render_template('my_projects.html', 
                         created_projects=created_projects,
                         joined_projects=joined_projects)

@app.route('/create-project', methods=['GET', 'POST'])
@login_required
def create_project():
    """Create new project"""
    if request.method == 'POST':
        data = request.json if request.is_json else request.form
        user_id = session.get('user_id')
        
        logger.info(f"Project creation attempt by user: {user_id}")
        
        try:
            # Validate required fields
            title = data.get('title', '').strip()
            description = data.get('description', '').strip()
            
            if not title:
                raise ValueError("Project title is required")
            if not description:
                raise ValueError("Project description is required")
            
            # Handle multi-select fields properly
            tech_stack = data.getlist('tech_stack') if hasattr(data, 'getlist') else data.get('tech_stack', [])
            required_skills = data.getlist('required_skills') if hasattr(data, 'getlist') else data.get('required_skills', [])
            
            # Convert max_collaborators to integer
            max_collaborators = data.get('max_collaborators', '5')
            try:
                max_collaborators = int(max_collaborators)
            except (ValueError, TypeError):
                max_collaborators = 5
            
            project_data = {
                'title': title,
                'description': description,
                'detailed_requirements': data.get('detailed_requirements', ''),
                'project_goals': data.get('project_goals', ''),
                'tech_stack': tech_stack,
                'required_skills': required_skills,
                'complexity_level': data.get('complexity_level', 'intermediate'),
                'estimated_duration': data.get('estimated_duration', ''),
                'domain': data.get('domain', ''),
                'max_collaborators': max_collaborators,
                'needed_roles': data.getlist('needed_roles') if hasattr(data, 'getlist') else data.get('needed_roles', []),
                'github_link': data.get('github_link', '').strip(),
                'is_open_for_collaboration': True
            }
            
            logger.info(f"Project data prepared: {project_data}")
            
            # Use collaboration service to create project
            project_id = collaboration_service.create_project(user_id, project_data)
            
            result = {'success': bool(project_id), 'project_id': project_id}
            
            if request.is_json:
                return jsonify(result)
            
            if result.get('success'):
                logger.info(f"Project created successfully by user: {user_id} with ID: {project_id}")
                logger.info(f"Project details for matching: title={project_data.get('title')}, domain={project_data.get('domain')}, skills={project_data.get('required_skills')}")
                
                # Notify matching users about the new project
                try:
                    logger.info(f"🔔 Calling notify_matching_users_about_new_project for project {project_id}")
                    notify_matching_users_about_new_project(project_id, user_id, project_data)
                    logger.info(f"✅ Notification function completed for project {project_id}")
                except Exception as notify_error:
                    # Don't fail project creation if notifications fail
                    logger.error(f"❌ Failed to send match notifications: {str(notify_error)}", exc_info=True)
                
                flash('Project created successfully!', 'success')
                return redirect(url_for('my_projects'))
            else:
                logger.error(f"Project creation failed for user {user_id}: No project ID returned")
                flash('Failed to create project - please check your input', 'error')
                
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Project creation error for user {user_id}: {error_msg}")
            if request.is_json:
                return jsonify({'success': False, 'error': error_msg})
            flash(f'Error creating project: {error_msg}', 'error')
    
    return render_template('create_project.html')

@app.route('/edit-project/<project_id>', methods=['GET', 'POST'])
@login_required
def edit_project(project_id):
    """Edit existing project"""
    user_id = session.get('user_id')
    
    try:
        # Get project details
        project = collaboration_service.get_project_by_id(project_id)
        
        if not project:
            flash('Project not found', 'error')
            return redirect(url_for('my_projects'))
        
        # Verify user is the creator
        if project.get('creator_id') != user_id:
            flash('You are not authorized to edit this project', 'error')
            return redirect(url_for('project_detail', project_id=project_id))
        
        if request.method == 'POST':
            data = request.json if request.is_json else request.form
            
            logger.info(f"Project edit attempt by user: {user_id} for project: {project_id}")
            
            try:
                # Validate required fields
                title = data.get('title', '').strip()
                description = data.get('description', '').strip()
                
                if not title:
                    raise ValueError("Project title is required")
                if not description:
                    raise ValueError("Project description is required")
                
                # Handle multi-select fields properly
                tech_stack = data.getlist('tech_stack') if hasattr(data, 'getlist') else data.get('tech_stack', [])
                required_skills = data.getlist('required_skills') if hasattr(data, 'getlist') else data.get('required_skills', [])
                
                # Convert max_collaborators to integer
                max_collaborators = data.get('max_collaborators', '5')
                try:
                    max_collaborators = int(max_collaborators)
                except (ValueError, TypeError):
                    max_collaborators = 5
                
                project_data = {
                    'title': title,
                    'description': description,
                    'detailed_requirements': data.get('detailed_requirements', ''),
                    'project_goals': data.get('project_goals', ''),
                    'tech_stack': tech_stack,
                    'required_skills': required_skills,
                    'complexity_level': data.get('complexity_level', 'intermediate'),
                    'estimated_duration': data.get('estimated_duration', ''),
                    'domain': data.get('domain', ''),
                    'max_collaborators': max_collaborators,
                    'github_link': data.get('github_link', '').strip(),
                    'is_open_for_collaboration': data.get('is_open_for_collaboration') == 'true' if data.get('is_open_for_collaboration') else True
                }
                
                # Update project
                success = collaboration_service.update_project(project_id, user_id, project_data)
                
                if success:
                    logger.info(f"Project {project_id} updated successfully by user: {user_id}")
                    flash('Project updated successfully!', 'success')
                    if request.is_json:
                        return jsonify({'success': True})
                    return redirect(url_for('project_detail', project_id=project_id))
                else:
                    logger.error(f"Project update failed for project {project_id}")
                    flash('Failed to update project', 'error')
                    
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Project update error for project {project_id}: {error_msg}")
                if request.is_json:
                    return jsonify({'success': False, 'error': error_msg})
                flash(f'Error updating project: {error_msg}', 'error')
        
        return render_template('edit_project.html', project=project)
        
    except Exception as e:
        logger.error(f"Error accessing edit project page: {str(e)}")
        flash('Error loading project for editing', 'error')
        return redirect(url_for('my_projects'))

@app.route('/collaboration-requests')
@login_required
def collaboration_requests():
    """View incoming and sent collaboration requests"""
    user_id = session.get('user_id')
    
    logger.debug(f"Collaboration requests page accessed by user: {user_id}")
    
    # TODO: Implement get collaboration requests
    # received_requests = collab_service.get_received_requests(user_id)
    # sent_requests = collab_service.get_sent_requests(user_id)
    
    return render_template('collaboration_requests.html')

@app.route('/explore')
def explore():
    """Explore page - All public collaboration projects (no login required for viewing)"""
    user_id = session.get('user_id')  # Optional - used for compatibility if logged in
    logger.debug(f"Explore page accessed by user: {user_id or 'anonymous'}")
    
    # Track page view
    if user_id:
        event_tracker.track_page_view(
            page_name='explore',
            user_id=user_id,
            session_id=session.get('session_id'),
            referrer=request.referrer
        )
        
        # Track session activity - FIXED: Use event_tracker instead of undefined session_tracker
        event_tracker.track_session_activity(
            session_id=session.get('session_id'),
            activity_type='github_page_view',
            github_viewed=True
        )
    
    try:
        # Get filter parameters
        filters = {}
        interest_area = request.args.get('interest_area')
        complexity = request.args.get('complexity')
        domain = request.args.get('domain')
        
        if interest_area:
            filters['interest_area'] = interest_area
        if complexity:
            filters['complexity'] = complexity
        if domain:
            filters['domain'] = domain
        
        # Get all public projects for exploration with filters
        projects = collaboration_service.get_all_projects(
            user_id=user_id,
            limit=50,
            filters=filters if filters else None
        )
        
        # For logged in users, check if they are creators or members of projects
        if user_id:
            from database.connection import supabase_admin
            for project in projects:
                # Check if user is the creator
                project['is_creator'] = str(project.get('creator_id')) == str(user_id)
                
                # Check if user is a member (use admin client to bypass RLS)
                member_check = supabase_admin.table('project_members').select('id').eq(
                    'project_id', project['id']
                ).eq('user_id', user_id).eq('is_active', True).execute()
                project['is_member'] = bool(member_check.data)
        else:
            # For anonymous users, set flags to False
            for project in projects:
                project['is_creator'] = False
                project['is_member'] = False
        
        # Get available filter options
        interest_areas = [
            'Frontend Development', 'Backend Development', 'UI/UX Design', 
            'DevOps', 'Mobile Development', 'Data Science', 
            'Machine Learning', 'Quality Assurance'
        ]
        
        complexity_levels = ['beginner', 'intermediate', 'advanced', 'expert']
        
        # Get unique domains from all projects for domain filter
        all_projects_for_domains = collaboration_service.get_all_projects(user_id=None, limit=200)
        domains = list(set(p.get('domain', '') for p in all_projects_for_domains if p.get('domain')))
        domains.sort()
        
        logger.info(f"Retrieved {len(projects)} public projects for exploration with filters: {filters}")
        
    except Exception as e:
        logger.error(f"Error getting explore projects: {str(e)}")
        projects = []
        interest_areas = []
        complexity_levels = []
        domains = []
    
    return render_template('explore.html', 
                         projects=projects,
                         interest_areas=interest_areas,
                         complexity_levels=complexity_levels,
                         available_domains=domains,
                         current_filters={'interest_area': interest_area, 'complexity': complexity, 'domain': domain},
                         page_title="Explore Projects - Discover Collaboration Opportunities")

@app.route('/bookmarks')
@login_required
def bookmarks():
    """User's bookmarked GitHub projects"""
    user_id = session.get('user_id')
    
    try:
        from database.connection import supabase_admin
        
        logger.info(f"Fetching bookmarks for user: {user_id}")
        
        bookmarks_result = supabase_admin.table('user_bookmarks').select('''
            *,
            github_references:github_reference_id (
                id,
                title,
                description,
                domain,
                complexity_level,
                repository_url,
                original_stars,
                original_forks,
                source
            )
        ''').eq('user_id', user_id).order('created_at', desc=True).execute()
        
        bookmarks = []
        if bookmarks_result.data:
            for bookmark in bookmarks_result.data:
                if bookmark.get('github_references'):
                    project = bookmark['github_references']
                    bookmark_info = {
                        'bookmark_id': bookmark['id'],
                        'notes': bookmark.get('notes', ''),
                        'created_at': bookmark['created_at'],
                        'id': project['id'],
                        'title': project['title'],
                        'description': project['description'],
                        'domain': project['domain'],
                        'complexity_level': project['complexity_level'],
                        'repository_url': project['repository_url'],
                        'original_stars': project.get('original_stars', 0),
                        'original_forks': project.get('original_forks', 0),
                        'source': project.get('source', 'GitHub')
                    }
                    bookmarks.append(bookmark_info)
        
        logger.info(f"Found {len(bookmarks)} bookmarks for user {user_id}")
        
        user_result = user_service.get_user_profile(user_id)
        user = user_result if user_result.get('success') else None
        
        return render_template('bookmarks.html', 
                             bookmarks=bookmarks,
                             user=user)
                             
    except Exception as e:
        logger.error(f"Error fetching bookmarks for user {user_id}: {str(e)}")
        flash('Error loading bookmarks', 'error')
        return render_template('bookmarks.html', bookmarks=[], user=None)

# ==================== API ENDPOINTS ====================

@app.route('/api/github/recommend', methods=['POST'])
@login_required
def api_github_recommend():
    """Get GitHub project recommendations"""
    user_id = session.get('user_id')
    data = request.json
    
    logger.debug(f"API recommendation request from user {user_id}")
    
    # TODO: Implement custom recommendation generation based on request data
    # recommendations = recommendation_service.get_custom_recommendations(user_id, data)
    
    return jsonify({'success': False, 'error': 'Not yet implemented'})

@app.route('/api/projects/send-request', methods=['POST'])
@login_required
def api_send_collaboration_request():
    """Send collaboration request"""
    user_id = session.get('user_id')
    data = request.json
    
    logger.info(f"Collaboration request sent by user {user_id}")
    
    request_data = {
        'requester_id': user_id,
        'project_id': data.get('project_id'),
        'requested_role': data.get('role'),
        'cover_message': data.get('cover_message'),
        'why_interested': data.get('why_interested'),
        'relevant_experience': data.get('relevant_experience')
    }
    
    # TODO: Implement send collaboration request
    # result = collab_service.send_request(request_data)
    
    # Track in collaboration_analytics
    # TODO: Insert into collaboration_analytics table
    
    return jsonify({'success': False, 'error': 'Not yet implemented'})

@app.route('/api/projects/respond-request', methods=['POST'])
@login_required
def api_respond_to_request():
    """Accept/reject collaboration request"""
    user_id = session.get('user_id')
    data = request.json
    
    logger.info(f"Collaboration request response by user {user_id}")
    
    # TODO: Implement respond to request
    # result = collab_service.respond_to_request(
    #     request_id=data.get('request_id'),
    #     response=data.get('response'),  # 'accepted' or 'rejected'
    #     message=data.get('message')
    # )
    
    # Update collaboration_analytics
    
    return jsonify({'success': False, 'error': 'Not yet implemented'})

@app.route('/api/projects/<project_id>', methods=['DELETE'])
@login_required
def api_delete_project(project_id):
    """Delete a project (only by creator)"""
    user_id = session.get('user_id')
    
    try:
        from database.connection import supabase_admin
        
        # Get project to verify ownership
        project = collaboration_service.get_project_by_id(project_id)
        
        if not project:
            logger.warning(f"Project {project_id} not found for deletion")
            return jsonify({'success': False, 'error': 'Project not found'}), 404
        
        # Verify user is the creator
        if str(project.get('creator_id')) != str(user_id):
            logger.warning(f"User {user_id} attempted to delete project {project_id} owned by {project.get('creator_id')}")
            return jsonify({'success': False, 'error': 'Only project creator can delete the project'}), 403
        
        # Delete project using admin client (CASCADE will handle related records)
        logger.info(f"Attempting to delete project {project_id} by user {user_id}")
        result = supabase_admin.table('user_projects').delete().eq('id', project_id).execute()
        
        # Check if deletion was successful
        if result.data:
            logger.info(f"✅ Project {project_id} successfully deleted from database by user {user_id}")
            return jsonify({'success': True, 'message': 'Project deleted successfully'})
        else:
            logger.error(f"❌ Project {project_id} deletion returned no data: {result}")
            return jsonify({'success': False, 'error': 'Project deletion failed - no data returned'}), 500
        
    except Exception as e:
        logger.error(f"❌ Exception deleting project {project_id}: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/project/view', methods=['POST'])
@login_required
def api_track_project_view():
    """Track user viewing a live project"""
    user_id = session.get('user_id')
    data = request.json
    
    logger.debug(f"Tracking project view by user {user_id}")
    
    # TODO: Implement project view tracking
    # track_service.track_project_view(
    #     project_id=data.get('project_id'),
    #     viewer_id=user_id,
    #     session_id=session.get('session_id')
    # )
    
    return jsonify({'success': True})

@app.route('/api/recommendation/click', methods=['POST'])
@login_required
def api_track_recommendation_click():
    """Track user clicking on a recommended project (View Project button)"""
    user_id = session.get('user_id')
    data = request.json
    
    try:
        github_reference_id = data.get('github_reference_id')
        rank_position = data.get('position', 0)
        similarity_score = data.get('similarity', 0.0)
        
        if not github_reference_id:
            logger.warning(f"Click tracking attempt without project ID by user {user_id}")
            return jsonify({'success': False, 'error': 'Project ID required'}), 400
        
        logger.info(f"Recommendation click for user {user_id}, project {github_reference_id}, position {rank_position}")
        
        # Track the click event for RL
        event_tracker.track_recommendation_click(
            user_id=user_id,
            github_reference_id=github_reference_id,
            rank_position=rank_position,
            similarity_score=similarity_score,
            session_id=session.get('session_id'),
            user_agent=request.headers.get('User-Agent')
        )
        
        # Update session github_projects_clicked counter
        session_id = session.get('session_id')
        if session_id:
            try:
                # Get current click count
                session_result = supabase.table('user_sessions')\
                    .select('github_projects_clicked')\
                    .eq('session_id', session_id)\
                    .execute()
                
                if session_result.data:
                    current_clicks = session_result.data[0].get('github_projects_clicked', 0)
                    supabase.table('user_sessions').update({
                        'github_projects_clicked': current_clicks + 1,
                        'last_activity': datetime.now().isoformat()
                    }).eq('session_id', session_id).execute()
                    logger.info(f"Updated session click count for user {user_id}")
            except Exception as e:
                logger.warning(f"Failed to update session click count: {str(e)}")
        
        # Also store in user_interactions table
        interaction_data = {
            'user_id': user_id,
            'github_reference_id': github_reference_id,
            'interaction_type': 'click',
            'session_id': session.get('session_id'),
            'user_agent': request.headers.get('User-Agent')
        }
        
        result = supabase.table('user_interactions').insert(interaction_data).execute()
        
        # Update RL model with interaction ONLY if:
        # 1. RL is enabled
        # 2. User is in TREATMENT group (not control group)
        # 3. No active A/B test OR A/B test has declared RL as winner
        if USE_RL_RECOMMENDATIONS and recommendation_service:
            try:
                from services.ab_test_service import get_ab_test_service
                ab_service = get_ab_test_service()
                
                # Check if user should contribute to RL training
                should_train_rl = False
                active_test = ab_service.get_active_test_config()
                
                if active_test:
                    # During A/B test: ONLY train on treatment group
                    user_group = ab_service.get_user_group(user_id)
                    if user_group == 'treatment':
                        should_train_rl = True
                        logger.debug(f"A/B Test active: User {user_id} in treatment group, will update RL model")
                    else:
                        logger.debug(f"A/B Test active: User {user_id} in control group, skipping RL update")
                else:
                    # No active test: Train RL normally
                    should_train_rl = True
                    logger.debug(f"No active A/B test, updating RL model normally")
                
                if should_train_rl:
                    recommendation_service.record_interaction(
                        user_id=user_id,
                        project_id=github_reference_id,
                        interaction_type='click',
                        rank_position=rank_position
                    )
                    logger.debug(f"RL interaction recorded for project {github_reference_id}")
                
            except Exception as rl_error:
                logger.warning(f"Failed to record RL interaction: {str(rl_error)}")
        
        if result.data:
            logger.info(f"Click interaction recorded for user {user_id}")
            return jsonify({'success': True, 'message': 'Click tracked successfully'})
        else:
            logger.error(f"Failed to insert click interaction for user {user_id}")
            return jsonify({'success': False, 'error': 'Database insert failed'}), 500
            
    except Exception as e:
        logger.error(f"Error tracking recommendation click: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/bookmark', methods=['POST'])
@login_required
def api_add_bookmark():
    """Bookmark a GitHub project with event tracking"""
    user_id = session.get('user_id')
    data = request.json
    
    try:
        from database.connection import supabase_admin
        
        github_reference_id = data.get('github_reference_id')
        notes = data.get('notes', '')
        
        if not github_reference_id:
            logger.warning(f"Bookmark attempt without project ID by user {user_id}")
            return jsonify({'success': False, 'error': 'Project ID required'}), 400
        
        logger.info(f"Bookmark action for user {user_id}, project {github_reference_id}")
        
        existing = supabase_admin.table('user_bookmarks').select('*')\
            .eq('user_id', user_id)\
            .eq('github_reference_id', github_reference_id)\
            .execute()
        
        if existing.data and len(existing.data) > 0:
            result = supabase_admin.table('user_bookmarks').delete()\
                .eq('user_id', user_id)\
                .eq('github_reference_id', github_reference_id)\
                .execute()
            
            # Track bookmark removal as interaction for RL
            try:
                event_tracker.track_bookmark_action(
                    user_id=user_id,
                    github_reference_id=github_reference_id,
                    action='remove',
                    session_id=session.get('session_id')
                )
                logger.info(f"Bookmark removal interaction tracked for user {user_id}")
            except Exception as track_error:
                logger.warning(f"Failed to track bookmark removal: {str(track_error)}")
            
            logger.info(f"Bookmark removed by user {user_id}")
            return jsonify({'success': True, 'action': 'removed'})
        else:
            bookmark_data = {
                'user_id': user_id,
                'github_reference_id': github_reference_id,
                'notes': notes
            }
            
            result = supabase_admin.table('user_bookmarks').insert(bookmark_data).execute()
            
            if result.data:
                # Track bookmark addition as interaction for RL
                try:
                    event_tracker.track_bookmark_action(
                        user_id=user_id,
                        github_reference_id=github_reference_id,
                        action='add',
                        session_id=session.get('session_id'),
                        notes=notes
                    )
                    logger.info(f"Bookmark addition interaction tracked for user {user_id}")
                    
                    # Update RL model ONLY if user is in treatment group (prevents A/B test contamination)
                    if USE_RL_RECOMMENDATIONS and recommendation_service:
                        try:
                            from services.ab_test_service import get_ab_test_service
                            ab_service = get_ab_test_service()
                            
                            should_train_rl = False
                            active_test = ab_service.get_active_test_config()
                            
                            if active_test:
                                user_group = ab_service.get_user_group(user_id)
                                if user_group == 'treatment':
                                    should_train_rl = True
                            else:
                                should_train_rl = True
                            
                            if should_train_rl:
                                recommendation_service.record_interaction(
                                    user_id=user_id,
                                    project_id=github_reference_id,
                                    interaction_type='bookmark',
                                    rank_position=None
                                )
                                logger.debug(f"RL model updated for bookmark (treatment group)")
                            else:
                                logger.debug(f"RL update skipped for bookmark (control group)")
                                
                        except Exception as rl_error:
                            logger.warning(f"Failed to update RL for bookmark: {str(rl_error)}")
                    
                except Exception as track_error:
                    logger.warning(f"Failed to track bookmark addition: {str(track_error)}")
                
                logger.info(f"Bookmark added by user {user_id}")
                return jsonify({'success': True, 'action': 'added'})
            else:
                logger.error(f"Failed to add bookmark for user {user_id}")
                return jsonify({'success': False, 'error': 'Failed to add bookmark'}), 500
                
    except Exception as e:
        logger.error(f"Bookmark error for user {user_id}: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@app.route('/api/bookmark/notes', methods=['PUT'])
@login_required
def api_update_bookmark_notes():
    """Update bookmark notes without toggling bookmark status"""
    try:
        from database.connection import supabase_admin
        
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'error': 'User not logged in'}), 401
            
        data = request.get_json()
        github_reference_id = data.get('github_reference_id')
        notes = data.get('notes', '')
        
        if not github_reference_id:
            return jsonify({'success': False, 'error': 'Project ID required'}), 400
            
        # Check if bookmark exists
        result = supabase_admin.table('user_bookmarks').select('*').eq('user_id', user_id).eq('github_reference_id', github_reference_id).execute()
        
        if not result.data:
            logger.warning(f"Bookmark not found for user {user_id}, project {github_reference_id}")
            return jsonify({'success': False, 'error': 'Bookmark not found'}), 404
            
        # Update notes
        update_result = supabase_admin.table('user_bookmarks').update({
            'notes': notes
        }).eq('user_id', user_id).eq('github_reference_id', github_reference_id).execute()
        
        if update_result.data:
            logger.info(f"Updated notes for bookmark user {user_id}, project {github_reference_id}")
            return jsonify({'success': True, 'message': 'Notes updated successfully'})
        else:
            logger.error(f"Failed to update notes for user {user_id}, project {github_reference_id}")
            return jsonify({'success': False, 'error': 'Failed to update notes'}), 500
            
    except Exception as e:
        logger.error(f"Error updating bookmark notes for user {user_id}: {str(e)}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@app.route('/api/bookmark/<github_reference_id>', methods=['DELETE'])
@login_required
def api_remove_bookmark(github_reference_id):
    """Remove bookmark completely"""
    try:
        from database.connection import supabase_admin
        
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'error': 'User not logged in'}), 401
        
        # Check if bookmark exists
        result = supabase_admin.table('user_bookmarks').select('*').eq('user_id', user_id).eq('github_reference_id', github_reference_id).execute()
        
        if not result.data:
            return jsonify({'success': False, 'error': 'Bookmark not found'}), 404
            
        # Remove bookmark completely
        delete_result = supabase_admin.table('user_bookmarks').delete().eq('user_id', user_id).eq('github_reference_id', github_reference_id).execute()
        
        if delete_result.data is not None:  # Supabase returns None for successful deletes
            logger.info(f"Removed bookmark for user {user_id}, project {github_reference_id}")
            return jsonify({'success': True, 'action': 'removed'})
        else:
            logger.error(f"Failed to remove bookmark for user {user_id}, project {github_reference_id}")
            return jsonify({'success': False, 'error': 'Failed to remove bookmark'}), 500
                
    except Exception as e:
        logger.error(f"Error removing bookmark for user {user_id}: {str(e)}")
        return jsonify({'success': False, 'error': 'Internal server error'}), 500

@app.route('/api/recommendations/load-more', methods=['POST'])
@login_required
def api_load_more_recommendations():
    """Load 3 more recommendations (total cap at 15)"""
    user_id = session.get('user_id')
    
    try:
        data = request.json or {}
        current_count = data.get('current_count', 0)
        filter_interest = data.get('filter')
        
        logger.info(f"Loading more recommendations for user {user_id}, current count: {current_count}, filter: {filter_interest}")
        
        if current_count >= 15:
            return jsonify({
                'success': True,
                'recommendations': [],
                'has_more': False,
                'message': 'Maximum recommendations reached'
            })
        
        remaining = 15 - current_count
        num_to_load = min(3, remaining)
        
        new_recommendations = []
        if recommendation_service:
            # Use appropriate method based on recommendation service type
            if USE_RL_RECOMMENDATIONS:
                # RL Engine uses get_recommendations method
                recommendations_result = recommendation_service.get_recommendations(
                    user_id=user_id,
                    num_recommendations=30,
                    use_rl=True,  # Enable RL re-ranking
                    offset=0
                )
            else:
                # Similarity service uses get_recommendations_for_user method
                recommendations_result = recommendation_service.get_recommendations_for_user(
                    user_id, 
                    num_recommendations=30,
                    offset=0
                )
            
            if isinstance(recommendations_result, dict) and recommendations_result.get('success'):
                all_recommendations = recommendations_result.get('recommendations', [])
                
                if filter_interest and filter_interest != 'all':
                    filtered_recommendations = []
                    filter_text = filter_interest.replace('_', ' ').lower()
                    
                    for rec in all_recommendations:
                        match_found = False
                        
                        if rec.get('technologies'):
                            if filter_text in rec['technologies'].lower():
                                match_found = True
                        
                        if rec.get('domain'):
                            if filter_text in rec['domain'].lower():
                                match_found = True
                        
                        title_text = (rec.get('title') or '').lower()
                        desc_text = (rec.get('description') or '').lower()
                        if filter_text in title_text or filter_text in desc_text:
                            match_found = True
                        
                        if match_found:
                            filtered_recommendations.append(rec)
                    
                    all_recommendations = filtered_recommendations
                
                new_recommendations = all_recommendations[current_count:current_count + num_to_load]
        
        has_more = (current_count + len(new_recommendations)) < 15 and len(new_recommendations) > 0
        
        logger.info(f"Loaded {len(new_recommendations)} more recommendations. Has more: {has_more}")
        
        return jsonify({
            'success': True,
            'recommendations': new_recommendations,
            'has_more': has_more
        })
        
    except Exception as e:
        logger.error(f"Error loading more recommendations for user {user_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to load more recommendations'
        }), 500
#===================== Frontend Events =================
@app.route('/api/events/track', methods=['POST'])
def api_track_event():
    """
    Receive and process events from frontend
    This endpoint handles all client-side event tracking
    """
    try:
        data = request.json
        
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        event_type = data.get('event_type')
        user_id = data.get('user_id') or session.get('user_id')
        session_id = data.get('session_id')
        
        # Log the event
        logger.debug(f"Frontend event received: {event_type}", extra={
            'user_id': user_id,
            'session_id': session_id
        })
        
        # Route to appropriate handler based on event type
        if event_type == 'recommendation_impression':
            # Track impression in database
            project_id = data.get('project_id')
            position = data.get('position')
            similarity = data.get('similarity')
            
            # Store in user_interactions or separate impressions table
            # For now, just log it
            logger.info(
                f"Recommendation impression: user={user_id}, project={project_id}, pos={position}",
                extra={'user_id': user_id, 'session_id': session_id}
            )
        
        elif event_type == 'recommendation_hover':
            project_id = data.get('project_id')
            hover_duration = data.get('hover_duration_ms')
            
            # Track hover event
            event_tracker.track_recommendation_hover(
                user_id=user_id,
                github_reference_id=project_id,
                hover_duration_ms=hover_duration,
                session_id=session_id
            )
        
        elif event_type == 'recommendation_click':
            # This is handled by separate /api/interactions/click endpoint
            pass
        
        elif event_type == 'page_view':
            page_name = data.get('page_name')
            referrer = data.get('referrer')
            
            event_tracker.track_page_view(
                page_name=page_name,
                user_id=user_id,
                session_id=session_id,
                referrer=referrer
            )
        
        elif event_type == 'page_exit':
            total_time = data.get('total_time_ms')
            active_time = data.get('active_time_ms')
            
            logger.info(
                f"Page exit: total={total_time}ms, active={active_time}ms",
                extra={'user_id': user_id, 'session_id': session_id}
            )
        
        elif event_type == 'scroll_depth':
            depth = data.get('depth')
            page = data.get('page')
            
            logger.debug(f"Scroll depth {depth}% on {page}", extra={
                'user_id': user_id,
                'session_id': session_id
            })
        
        elif event_type == 'user_inactive':
            time_until_inactive = data.get('time_until_inactive_ms')
            logger.info(
                f"User became inactive after {time_until_inactive}ms",
                extra={'user_id': user_id, 'session_id': session_id}
            )
        
        return jsonify({'success': True})
        
    except Exception as e:
        logger.error(f"Error tracking frontend event: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': 'Failed to track event'}), 500


@app.route('/api/interactions/click', methods=['POST'])
def api_track_click():
    """
    Track recommendation click interaction
    This is a dedicated endpoint for click tracking that stores in database
    """
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'error': 'User not authenticated'}), 401
        
        data = request.json
        github_reference_id = data.get('github_reference_id')
        rank_position = data.get('rank_position')
        similarity_score = data.get('similarity_score')
        session_id = data.get('session_id')
        
        if not github_reference_id:
            return jsonify({'success': False, 'error': 'Project ID required'}), 400
        
        # Track click in database
        interaction_id = event_tracker.track_recommendation_click(
            user_id=user_id,
            github_reference_id=github_reference_id,
            rank_position=rank_position,
            similarity_score=similarity_score,
            session_id=session_id,
            user_agent=request.headers.get('User-Agent')
        )
        
        # Update session activity
        if session_id:
            event_tracker.track_session_activity(
                session_id=session_id,
                activity_type='recommendation_click',
                github_viewed=True
            )
        
        logger.info(
            f"Click tracked: user={user_id}, project={github_reference_id}, pos={rank_position}",
            extra={'user_id': user_id, 'session_id': session_id}
        )
        
        return jsonify({
            'success': True,
            'interaction_id': interaction_id
        })
        
    except Exception as e:
        logger.error(f"Error tracking click: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': 'Failed to track click'}), 500


@app.route('/api/interactions/feedback', methods=['POST'])
def api_submit_feedback():
    """
    Submit user feedback on a recommendation
    """
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'error': 'User not authenticated'}), 401
        
        data = request.json
        github_reference_id = data.get('github_reference_id')
        rating = data.get('rating')
        feedback_text = data.get('feedback_text')
        is_relevant = data.get('is_relevant')
        is_helpful = data.get('is_helpful')
        query_id = data.get('query_id')
        
        if not github_reference_id:
            return jsonify({'success': False, 'error': 'Project ID required'}), 400
        
        # Track feedback
        feedback_id = event_tracker.track_feedback(
            user_id=user_id,
            github_reference_id=github_reference_id,
            rating=rating,
            feedback_text=feedback_text,
            is_relevant=is_relevant,
            is_helpful=is_helpful,
            query_id=query_id,
            session_id=session.get('session_id')
        )
        
        logger.info(
            f"Feedback submitted: user={user_id}, project={github_reference_id}, rating={rating}",
            extra={'user_id': user_id}
        )
        
        return jsonify({
            'success': True,
            'feedback_id': feedback_id,
            'message': 'Thank you for your feedback!'
        })
        
    except Exception as e:
        logger.error(f"Error submitting feedback: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': 'Failed to submit feedback'}), 500


@app.route('/api/performance/stats', methods=['GET'])
@login_required
def api_performance_stats():
    """
    Get performance statistics (for debugging/admin)
    """
    try:
        if session.get('user_email') not in ADMIN_EMAILS:
            return jsonify({'success': False, 'error': 'Admin access required'}), 403
        
        stats = perf_monitor.get_performance_summary()
        
        return jsonify({
            'success': True,
            'stats': stats
        })
        
    except Exception as e:
        logger.error(f"Error getting performance stats: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== PUSH NOTIFICATION ENDPOINTS ====================

@app.route('/api/notifications/subscribe', methods=['POST'])
@login_required
def api_subscribe_push_notifications():
    """Subscribe user to push notifications"""
    try:
        user_id = session.get('user_id')
        data = request.json
        
        subscription = data.get('subscription')
        user_agent = data.get('user_agent', '')
        timezone = data.get('timezone', 'UTC')
        
        if not subscription:
            return jsonify({'success': False, 'error': 'Subscription data required'}), 400
        
        logger.info(f"Push notification subscription for user {user_id}")
        
        # Store subscription in user_profiles metadata
        # Using existing user_profiles table to avoid creating new table
        profile_result = supabase.table('user_profiles').select('*').eq('user_id', user_id).execute()
        
        if profile_result.data:
            # Update existing profile with push subscription data
            current_profile = profile_result.data[0]
            metadata = current_profile.get('metadata', {}) if current_profile.get('metadata') else {}
            
            metadata['push_subscription'] = {
                'endpoint': subscription.get('endpoint'),
                'keys': subscription.get('keys'),
                'user_agent': user_agent,
                'timezone': timezone,
                'subscribed_at': datetime.now().isoformat(),
                'enabled': True
            }
            
            supabase.table('user_profiles').update({
                'metadata': metadata
            }).eq('user_id', user_id).execute()
            
            logger.info(f"Push subscription saved for user {user_id}")
            
            return jsonify({
                'success': True,
                'message': 'Push notifications enabled successfully'
            })
        else:
            return jsonify({'success': False, 'error': 'User profile not found'}), 404
            
    except Exception as e:
        logger.error(f"Error subscribing to push notifications: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': 'Failed to enable push notifications'}), 500


@app.route('/api/notifications/unsubscribe', methods=['POST'])
@login_required
def api_unsubscribe_push_notifications():
    """Unsubscribe user from push notifications"""
    try:
        user_id = session.get('user_id')
        
        logger.info(f"Push notification unsubscription for user {user_id}")
        
        # Update user profile to disable push notifications
        profile_result = supabase.table('user_profiles').select('*').eq('user_id', user_id).execute()
        
        if profile_result.data:
            current_profile = profile_result.data[0]
            metadata = current_profile.get('metadata', {}) if current_profile.get('metadata') else {}
            
            if 'push_subscription' in metadata:
                metadata['push_subscription']['enabled'] = False
                metadata['push_subscription']['unsubscribed_at'] = datetime.now().isoformat()
                
                supabase.table('user_profiles').update({
                    'metadata': metadata
                }).eq('user_id', user_id).execute()
            
            logger.info(f"Push subscription disabled for user {user_id}")
            
            return jsonify({
                'success': True,
                'message': 'Push notifications disabled successfully'
            })
        else:
            return jsonify({'success': False, 'error': 'User profile not found'}), 404
            
    except Exception as e:
        logger.error(f"Error unsubscribing from push notifications: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': 'Failed to disable push notifications'}), 500


@app.route('/api/notifications/unread-count', methods=['GET'])
@login_required
def api_unread_notifications_count():
    """Get count of pending collaboration requests as unread notifications"""
    try:
        user_id = session.get('user_id')
        
        # Count pending collaboration requests for user's projects
        try:
            # First get user's projects
            projects_result = supabase.table('user_projects').select('id').eq('creator_id', user_id).execute()
            project_ids = [p['id'] for p in projects_result.data] if projects_result.data else []
            
            if project_ids:
                # Count pending requests for these projects
                result = supabase.table('collaboration_requests')\
                    .select('id', count='exact')\
                    .in_('project_id', project_ids)\
                    .eq('status', 'pending')\
                    .execute()
                
                count = result.count or 0
            else:
                count = 0
                
        except Exception:
            # If there's any error, return 0
            count = 0
        
        return jsonify({
            'success': True,
            'count': count
        })
        
    except Exception as e:
        logger.error(f"Error getting unread count: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/notifications/track-click', methods=['POST'])
@login_required
def api_track_notification_click():
    """Track notification click/dismiss actions"""
    try:
        user_id = session.get('user_id')
        data = request.json
        
        notification_id = data.get('notification_id')
        action = data.get('action', 'click')
        
        # Log the interaction
        event_tracker.track_notification_interaction(
            user_id=user_id,
            notification_id=notification_id,
            action=action,
            session_id=session.get('session_id')
        )
        
        logger.info(f"Notification {action} tracked for user {user_id}")
        
        return jsonify({'success': True})
        
    except Exception as e:
        logger.error(f"Error tracking notification click: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/notifications/sync', methods=['GET'])
def api_sync_notifications():
    """Background sync endpoint for service worker"""
    try:
        # This would be called by service worker for background sync
        # Return any pending notifications that need to be shown
        
        return jsonify({
            'success': True,
            'notifications': []  # Could return pending notifications here
        })
        
    except Exception as e:
        logger.error(f"Error in notification sync: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== NOTIFICATION HELPER FUNCTIONS ====================

def send_push_notification(user_id, title, body, notification_type='general', url=None, icon=None):
    """
    Send push notification to a specific user
    Uses existing notification table for tracking
    """
    try:
        # Get user's push subscription from profile metadata
        profile_result = supabase.table('user_profiles').select('metadata').eq('user_id', user_id).execute()
        
        if not profile_result.data:
            logger.warning(f"No profile found for user {user_id}")
            return False
        
        metadata = profile_result.data[0].get('metadata', {})
        push_subscription = metadata.get('push_subscription')
        
        if not push_subscription or not push_subscription.get('enabled'):
            logger.info(f"Push notifications not enabled for user {user_id}")
            return False
        
        # Send push notification (no database record needed - using collaboration_requests as notifications)
        logger.info(f"Push notification prepared for user {user_id}: {title}")
        return True
            
    except Exception as e:
        logger.error(f"Error sending push notification: {str(e)}", exc_info=True)
        return False

def notify_matching_users_about_new_project(project_id, creator_id, project_data):
    """
    Notify users with matching interests about new project
    Uses collaboration_requests table with special status 'project_match_notification'
    Uses improved word-level matching for better accuracy
    """
    try:
        from database.connection import supabase_admin
        
        logger.info(f"Finding matching users for new project {project_id}")
        
        # Get project's required skills and domain
        project_skills = project_data.get('required_skills', [])
        project_domain = project_data.get('domain', '')
        project_title = project_data.get('title', '')
        
        # Convert to lowercase and create keyword sets for case-insensitive matching
        project_keywords = set()
        if project_domain:
            # Split on spaces, underscores, and hyphens
            project_keywords.update(project_domain.lower().replace('_', ' ').replace('-', ' ').split())
        for skill in project_skills:
            project_keywords.update(skill.lower().replace('_', ' ').replace('-', ' ').split())
        
        if not project_keywords:
            logger.info("No skills or domain specified, skipping notifications")
            return
        
        logger.info(f"Project keywords: {project_keywords}")
        
        # Find users with matching interests (exclude creator) - use admin client
        matching_users = []
        
        # Query all user profiles using admin client to bypass RLS
        profiles_result = supabase_admin.table('user_profiles').select(
            'user_id, areas_of_interest, programming_languages'
        ).neq('user_id', creator_id).execute()
        
        logger.info(f"Checking {len(profiles_result.data) if profiles_result.data else 0} user profiles for matches")
        
        for profile in profiles_result.data if profiles_result.data else []:
            user_interests = profile.get('areas_of_interest', []) or []
            user_languages = profile.get('programming_languages', []) or []
            
            # Create a set of user keywords
            user_keywords = set()
            for interest in user_interests:
                # Split on spaces, underscores, and hyphens
                user_keywords.update(interest.lower().replace('_', ' ').replace('-', ' ').split())
            for lang in user_languages:
                user_keywords.update(lang.lower().replace('_', ' ').replace('-', ' ').split())
            
            # Check if there's ANY overlap between project and user keywords
            has_match = bool(project_keywords & user_keywords)
            
            # Additional fuzzy matching for common terms (e.g., "develop" in "development")
            if not has_match:
                for proj_word in project_keywords:
                    for user_word in user_keywords:
                        # If words share a significant portion (substring matching for related terms)
                        if len(proj_word) >= 4 and len(user_word) >= 4:
                            if proj_word in user_word or user_word in proj_word:
                                has_match = True
                                logger.debug(f"Fuzzy match: '{proj_word}' matched with '{user_word}' for user {profile['user_id']}")
                                break
                    if has_match:
                        break
            
            if has_match:
                matching_users.append(profile['user_id'])
                logger.debug(f"✅ Match found for user {profile['user_id']}")
        
        logger.info(f"Found {len(matching_users)} matching users for project {project_id}")
        
        # Create notification records using collaboration_requests table
        # with special status 'project_match_notification' - use admin client
        notifications_to_insert = []
        for user_id in matching_users:
            notifications_to_insert.append({
                'project_id': project_id,
                'requester_id': creator_id,  # Creator is the "requester"
                'project_owner_id': user_id,  # Matched user receives it
                'cover_message': f'New project "{project_title}" matches your interests! Domain: {project_domain}. Check it out and request to join if interested.',
                'status': 'project_match_notification',
                'requested_role': 'Notification'
            })
        
        # Bulk insert notifications using admin client (batch of 100 at a time to avoid limits)
        if notifications_to_insert:
            batch_size = 100
            for i in range(0, len(notifications_to_insert), batch_size):
                batch = notifications_to_insert[i:i+batch_size]
                supabase_admin.table('collaboration_requests').insert(batch).execute()
            
            logger.info(f"✅ Created {len(notifications_to_insert)} project match notifications")
        else:
            logger.info("⚠️ No matching users found for this project")
        
    except Exception as e:
        logger.error(f"Error notifying matching users: {str(e)}", exc_info=True)
        # Don't fail project creation if notifications fail
        pass

# ==================== ADMIN ROUTES ====================
from services.admin_analytics_service import get_analytics_service
from flask import send_file
import io
import csv

# Initialize analytics service
analytics_service = get_analytics_service()

@app.route('/admin/analytics')
@admin_required
def admin_analytics():
    """
    Admin analytics dashboard - Main page
    Shows comprehensive platform metrics and visualizations
    """
    logger.info(f"Admin analytics dashboard accessed by {session.get('user_email')}")
    
    return render_template('admin/analytics.html')

@app.route('/api/admin/analytics/dashboard', methods=['GET'])
@admin_required
def api_admin_dashboard_data():
    """
    API endpoint to get complete dashboard data
    
    Query params:
        days (int): Number of days to analyze (default: 7)
    """
    try:
        days = request.args.get('days', 7, type=int)
        
        logger.info(f"Admin requesting dashboard data for {days} days")
        
        # Get complete dashboard data
        dashboard_data = analytics_service.get_complete_dashboard_data(days)
        
        if dashboard_data.get('error'):
            return jsonify({
                'success': False,
                'error': dashboard_data['error']
            }), 500
        
        return jsonify({
            'success': True,
            'data': dashboard_data
        })
        
    except Exception as e:
        logger.error(f"Error getting dashboard data: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to load dashboard data'
        }), 500


@app.route('/api/admin/analytics/rl-metrics', methods=['GET'])
@admin_required
def api_admin_rl_metrics():
    """
    Simplified RL-focused metrics endpoint
    Returns only the data we're actually tracking for reinforcement learning
    """
    try:
        # Use admin client to bypass RLS and see ALL users' data
        from database.connection import supabase_admin
        
        logger.info("Fetching analytics data from database using admin client...")
        
        # Total users (all users, not just current user)
        users_result = supabase_admin.table('users').select('id', count='exact').execute()
        total_users = users_result.count or 0
        logger.info(f"Total users: {total_users}")
        
        # Total bookmarks (all users' bookmarks)
        bookmarks_result = supabase_admin.table('user_bookmarks').select('id', count='exact').execute()
        total_bookmarks = bookmarks_result.count or 0
        logger.info(f"Total bookmarks: {total_bookmarks}")
        
        # Total interactions (clicks + bookmarks from all users)
        interactions_result = supabase_admin.table('user_interactions').select('id, interaction_type', count='exact').execute()
        total_interactions = interactions_result.count or 0
        logger.info(f"Total interactions: {total_interactions}")
        
        # Get recommendation results for CTR calculation (all users)
        recommendations_result = supabase_admin.table('recommendation_results').select('id', count='exact').execute()
        total_recommendations = recommendations_result.count or 0
        logger.info(f"Total recommendations: {total_recommendations}")
        
        # Calculate CTR (clicks / recommendations * 100)
        clicks_result = supabase_admin.table('user_interactions').select('id', count='exact').eq('interaction_type', 'click').execute()
        total_clicks = clicks_result.count or 0
        overall_ctr = (total_clicks / total_recommendations * 100) if total_recommendations > 0 else 0
        
        # CTR by position - Get actual data from recommendation_results joined with interactions
        ctr_by_position = []
        try:
            # Get all recommendation results with positions (limit to prevent timeout)
            recs = supabase_admin.table('recommendation_results')\
                .select('rank_position, github_reference_id')\
                .limit(1000)\
                .execute()
            
            # Get all clicks at once
            all_clicks = supabase_admin.table('user_interactions')\
                .select('github_reference_id')\
                .eq('interaction_type', 'click')\
                .execute()
            
            clicked_ids = set(click['github_reference_id'] for click in (all_clicks.data or []))
            
            # Count by position
            position_stats = {}
            for rec in (recs.data or []):
                pos = rec.get('rank_position') or 1
                if 1 <= pos <= 10:  # Only positions 1-10
                    if pos not in position_stats:
                        position_stats[pos] = {'shown': 0, 'clicked': 0}
                    position_stats[pos]['shown'] += 1
                    if rec.get('github_reference_id') in clicked_ids:
                        position_stats[pos]['clicked'] += 1
            
            # Calculate CTR for each position
            for pos in range(1, 11):
                if pos in position_stats:
                    stats = position_stats[pos]
                    ctr = (stats['clicked'] / stats['shown'] * 100) if stats['shown'] > 0 else 0
                    ctr_by_position.append({'position': pos, 'ctr': round(ctr, 2)})
                else:
                    ctr_by_position.append({'position': pos, 'ctr': 0})
            
            logger.info(f"CTR by position calculated: {len(ctr_by_position)} positions")
        except Exception as e:
            logger.warning(f"Error calculating CTR by position: {str(e)}")
            ctr_by_position = [{'position': i+1, 'ctr': 0} for i in range(10)]
        
        # CTR by domain - Simplified to avoid timeout
        ctr_by_domain = []
        try:
            # Get all recommendations with project details in one query
            recs_with_projects = supabase_admin.table('recommendation_results')\
                .select('github_reference_id')\
                .limit(1000)\
                .execute()
            
            # Get unique project IDs
            project_ids = list(set(rec['github_reference_id'] for rec in (recs_with_projects.data or [])))[:50]
            
            if project_ids:
                # Get projects with domains
                projects = supabase_admin.table('github_references')\
                    .select('id, domain')\
                    .in_('id', project_ids)\
                    .execute()
                
                # Get all clicks for these projects
                clicks = supabase_admin.table('user_interactions')\
                    .select('github_reference_id')\
                    .eq('interaction_type', 'click')\
                    .in_('github_reference_id', project_ids)\
                    .execute()
                
                # Count by domain
                domain_stats = {}
                project_domains = {p['id']: p.get('domain', 'Unknown') for p in (projects.data or [])}
                
                for rec in (recs_with_projects.data or []):
                    proj_id = rec['github_reference_id']
                    domain = project_domains.get(proj_id, 'Unknown')
                    if domain not in domain_stats:
                        domain_stats[domain] = {'shown': 0, 'clicked': 0}
                    domain_stats[domain]['shown'] += 1
                
                for click in (clicks.data or []):
                    proj_id = click['github_reference_id']
                    domain = project_domains.get(proj_id, 'Unknown')
                    if domain in domain_stats:
                        domain_stats[domain]['clicked'] += 1
                
                # Calculate CTR
                for domain, stats in domain_stats.items():
                    ctr = (stats['clicked'] / stats['shown'] * 100) if stats['shown'] > 0 else 0
                    ctr_by_domain.append({'domain': domain, 'ctr': round(ctr, 2)})
                
                ctr_by_domain = sorted(ctr_by_domain, key=lambda x: x['ctr'], reverse=True)[:10]
            
            if not ctr_by_domain:
                ctr_by_domain = [
                    {'domain': 'Web Development', 'ctr': 0},
                    {'domain': 'Machine Learning', 'ctr': 0},
                    {'domain': 'Data Science', 'ctr': 0},
                    {'domain': 'Mobile Development', 'ctr': 0},
                    {'domain': 'DevOps', 'ctr': 0}
                ]
            
            logger.info(f"CTR by domain calculated: {len(ctr_by_domain)} domains")
        except Exception as e:
            logger.warning(f"Error calculating CTR by domain: {str(e)}")
            ctr_by_domain = [
                {'domain': 'Web Development', 'ctr': 0},
                {'domain': 'Machine Learning', 'ctr': 0},
                {'domain': 'Data Science', 'ctr': 0},
                {'domain': 'Mobile Development', 'ctr': 0},
                {'domain': 'DevOps', 'ctr': 0}
            ]
        
        # Top projects - Simplified to avoid timeout
        top_projects = []
        try:
            # Get all interactions grouped
            clicks_by_project = supabase_admin.table('user_interactions')\
                .select('github_reference_id')\
                .eq('interaction_type', 'click')\
                .limit(500)\
                .execute()
            
            bookmarks_by_project = supabase_admin.table('user_bookmarks')\
                .select('github_reference_id')\
                .limit(500)\
                .execute()
            
            # Count interactions per project
            project_scores = {}
            for click in (clicks_by_project.data or []):
                proj_id = click['github_reference_id']
                if proj_id not in project_scores:
                    project_scores[proj_id] = {'clicks': 0, 'bookmarks': 0}
                project_scores[proj_id]['clicks'] += 1
            
            for bookmark in (bookmarks_by_project.data or []):
                proj_id = bookmark['github_reference_id']
                if proj_id not in project_scores:
                    project_scores[proj_id] = {'clicks': 0, 'bookmarks': 0}
                project_scores[proj_id]['bookmarks'] += 1
            
            # Get project details for top engaged projects
            if project_scores:
                top_project_ids = sorted(
                    project_scores.keys(), 
                    key=lambda x: project_scores[x]['clicks'] + project_scores[x]['bookmarks'] * 5,
                    reverse=True
                )[:10]
                
                projects = supabase_admin.table('github_references')\
                    .select('id, title, description, domain')\
                    .in_('id', top_project_ids)\
                    .execute()
                
                for proj in (projects.data or []):
                    proj_id = proj['id']
                    stats = project_scores.get(proj_id, {'clicks': 0, 'bookmarks': 0})
                    total_score = stats['clicks'] + (stats['bookmarks'] * 5)
                    
                    top_projects.append({
                        'title': proj.get('title', 'Untitled')[:50],
                        'description': (proj.get('description') or '')[:100],
                        'domain': proj.get('domain', 'N/A'),
                        'clicks': stats['clicks'],
                        'bookmarks': stats['bookmarks'],
                        'total_score': total_score
                    })
                
                # Sort by total score
                top_projects = sorted(top_projects, key=lambda x: x['total_score'], reverse=True)
            
            logger.info(f"Top projects calculated: {len(top_projects)} projects")
        except Exception as e:
            logger.warning(f"Error getting top projects: {str(e)}")
            top_projects = []
        
        return jsonify({
            'success': True,
            'data': {
                'total_users': total_users,
                'total_bookmarks': total_bookmarks,
                'total_interactions': total_interactions,
                'overall_ctr': overall_ctr,
                'ctr_by_position': ctr_by_position,
                'ctr_by_domain': ctr_by_domain,
                'top_projects': top_projects if top_projects else [{
                    'title': 'No data yet',
                    'description': 'Start using the platform to see recommendations',
                    'domain': 'N/A',
                    'clicks': 0,
                    'bookmarks': 0,
                    'total_score': 0
                }]
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting RL metrics: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/admin/analytics/overview', methods=['GET'])
@admin_required
def api_admin_overview():
    """Get overview metrics only"""
    try:
        days = request.args.get('days', 7, type=int)
        overview = analytics_service.get_overview_metrics(days)
        
        return jsonify({
            'success': True,
            'data': overview
        })
        
    except Exception as e:
        logger.error(f"Error getting overview: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/admin/analytics/user-engagement', methods=['GET'])
@admin_required
def api_admin_user_engagement():
    """Get user engagement metrics"""
    try:
        days = request.args.get('days', 7, type=int)
        
        engagement_data = {
            'dau_trend': analytics_service.get_daily_active_users_trend(days),
            'retention': analytics_service.get_user_retention_cohorts(),
            'avg_session_duration': analytics_service.get_average_session_duration(days),
            'funnel': analytics_service.get_engagement_funnel(days)
        }
        
        return jsonify({
            'success': True,
            'data': engagement_data
        })
        
    except Exception as e:
        logger.error(f"Error getting user engagement: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/admin/analytics/recommendations', methods=['GET'])
@admin_required
def api_admin_recommendations():
    """Get recommendation performance metrics"""
    try:
        days = request.args.get('days', 7, type=int)
        
        rec_data = {
            'ctr_analysis': analytics_service.get_click_through_rate(days),
            'quality_metrics': analytics_service.get_recommendation_quality_metrics(days),
            'top_projects': analytics_service.get_top_performing_projects(days, 10)
        }
        
        return jsonify({
            'success': True,
            'data': rec_data
        })
        
    except Exception as e:
        logger.error(f"Error getting recommendation metrics: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/admin/analytics/system-health', methods=['GET'])
@admin_required
def api_admin_system_health():
    """Get system health metrics"""
    try:
        health_data = analytics_service.get_system_health()
        
        return jsonify({
            'success': True,
            'data': health_data
        })
        
    except Exception as e:
        logger.error(f"Error getting system health: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/admin/analytics/export', methods=['GET'])
@admin_required
def api_admin_export_data():
    """
    Export analytics data
    
    Query params:
        days (int): Number of days to export
        format (str): 'json' or 'csv'
    """
    try:
        days = request.args.get('days', 30, type=int)
        format_type = request.args.get('format', 'json')
        
        logger.info(f"Admin exporting {format_type} data for {days} days")
        
        # Get complete dashboard data
        data = analytics_service.get_complete_dashboard_data(days)
        
        if format_type == 'json':
            # Return as JSON file
            output = io.BytesIO()
            output.write(json.dumps(data, indent=2).encode('utf-8'))
            output.seek(0)
            
            return send_file(
                output,
                mimetype='application/json',
                as_attachment=True,
                download_name=f'cochain_analytics_{datetime.now().strftime("%Y%m%d")}.json'
            )
            
        elif format_type == 'csv':
            # Convert overview metrics to CSV
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write overview metrics
            writer.writerow(['Metric', 'Value'])
            overview = data.get('overview', {})
            for key, value in overview.items():
                writer.writerow([key, value])
            
            # Convert to bytes
            output_bytes = io.BytesIO()
            output_bytes.write(output.getvalue().encode('utf-8'))
            output_bytes.seek(0)
            
            return send_file(
                output_bytes,
                mimetype='text/csv',
                as_attachment=True,
                download_name=f'cochain_analytics_{datetime.now().strftime("%Y%m%d")}.csv'
            )
        
        else:
            return jsonify({'success': False, 'error': 'Invalid format'}), 400
            
    except Exception as e:
        logger.error(f"Error exporting data: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': 'Export failed'}), 500


@app.route('/api/admin/analytics/export-ml', methods=['GET'])
@admin_required
def api_admin_export_ml_data():
    """
    Export interaction data for ML training
    
    Query params:
        days (int): Number of days to export (default: 30)
    """
    try:
        days = request.args.get('days', 30, type=int)
        
        logger.info(f"Admin exporting ML training data for {days} days")
        
        # Export interaction data
        ml_data = analytics_service.export_interaction_data(days, format='json')
        
        if ml_data is None:
            return jsonify({'success': False, 'error': 'Export failed'}), 500
        
        # Return as downloadable file
        output = io.BytesIO()
        output.write(ml_data.encode('utf-8'))
        output.seek(0)
        
        return send_file(
            output,
            mimetype='application/json',
            as_attachment=True,
            download_name=f'cochain_ml_data_{datetime.now().strftime("%Y%m%d")}.json'
        )
        
    except Exception as e:
        logger.error(f"Error exporting ML data: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': 'Export failed'}), 500


@app.route('/api/admin/analytics/users', methods=['GET'])
@admin_required
def api_admin_users_list():
    """
    Get list of users with engagement stats
    
    Query params:
        limit (int): Number of users to return (default: 50)
        offset (int): Pagination offset (default: 0)
        sort (str): Sort field (default: 'total_sessions')
        order (str): Sort order 'asc' or 'desc' (default: 'desc')
    """
    try:
        from database.connection import supabase_admin
        
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        sort_field = request.args.get('sort', 'created_at')
        sort_order = request.args.get('order', 'desc')
        
        # Simplified approach: Just get users first, then aggregate stats separately
        # This avoids the slow user_engagement_summary view
        
        # Get users with basic info
        users_result = supabase_admin.table('users')\
            .select('id, email, full_name, created_at, last_login')\
            .order('created_at', desc=(sort_order == 'desc'))\
            .range(offset, offset + limit - 1)\
            .execute()
        
        if not users_result.data:
            return jsonify({
                'success': True,
                'data': {
                    'users': [],
                    'total': 0,
                    'limit': limit,
                    'offset': offset
                }
            })
        
        user_ids = [u['id'] for u in users_result.data]
        
        # Get session stats for these users only (much faster than view)
        from datetime import datetime, timedelta
        cutoff_time = (datetime.utcnow() - timedelta(hours=24)).isoformat()
        
        sessions = supabase_admin.table('user_sessions')\
            .select('user_id, total_minutes, logout_time, login_time')\
            .in_('user_id', user_ids)\
            .execute()
        
        # Aggregate stats per user
        user_stats = {}
        cutoff_time = (datetime.utcnow() - timedelta(hours=24)).isoformat()
        
        for session in (sessions.data or []):
            uid = session['user_id']
            if uid not in user_stats:
                user_stats[uid] = {
                    'total_sessions': 0,
                    'total_minutes_on_platform': 0,
                    'is_active': False
                }
            user_stats[uid]['total_sessions'] += 1
            user_stats[uid]['total_minutes_on_platform'] += session.get('total_minutes') or 0
            
            # Check if active: session must be recent (within 24h) AND not logged out
            login_time = session.get('login_time', '')
            logout_time = session.get('logout_time')
            
            # User is active only if they have a recent session without logout
            # Use string comparison since both are ISO format (works correctly for chronological order)
            if login_time and login_time >= cutoff_time and not logout_time:
                user_stats[uid]['is_active'] = True
        
        # Get click and bookmark counts for these users
        clicks_result = supabase_admin.table('user_interactions')\
            .select('user_id')\
            .eq('interaction_type', 'click')\
            .in_('user_id', user_ids)\
            .execute()
        
        bookmarks_result = supabase_admin.table('user_interactions')\
            .select('user_id')\
            .eq('interaction_type', 'bookmark_add')\
            .in_('user_id', user_ids)\
            .execute()
        
        # Get recommendation impressions (views) for these users
        views_result = supabase_admin.table('recommendation_results')\
            .select('user_id')\
            .in_('user_id', user_ids)\
            .execute()
        
        # Get project views for these users
        project_views_result = supabase_admin.table('project_views')\
            .select('viewer_id')\
            .in_('viewer_id', user_ids)\
            .execute()
        
        # Get collaboration requests sent by these users (exclude project match notifications)
        collab_requests_result = supabase_admin.table('collaboration_requests')\
            .select('requester_id')\
            .in_('requester_id', user_ids)\
            .neq('status', 'project_match_notification')\
            .execute()
        
        # Get projects created by these users
        projects_created_result = supabase_admin.table('user_projects')\
            .select('creator_id')\
            .in_('creator_id', user_ids)\
            .execute()
        
        # Get projects joined by these users (from project_members)
        projects_joined_result = supabase_admin.table('project_members')\
            .select('user_id')\
            .in_('user_id', user_ids)\
            .execute()
        
        # Count interactions per user
        click_counts = {}
        for click in (clicks_result.data or []):
            uid = click['user_id']
            click_counts[uid] = click_counts.get(uid, 0) + 1
        
        bookmark_counts = {}
        for bookmark in (bookmarks_result.data or []):
            uid = bookmark['user_id']
            bookmark_counts[uid] = bookmark_counts.get(uid, 0) + 1
        
        view_counts = {}
        for view in (views_result.data or []):
            uid = view['user_id']
            view_counts[uid] = view_counts.get(uid, 0) + 1
        
        project_view_counts = {}
        for pv in (project_views_result.data or []):
            uid = pv['viewer_id']
            project_view_counts[uid] = project_view_counts.get(uid, 0) + 1
        
        collab_request_counts = {}
        for cr in (collab_requests_result.data or []):
            uid = cr['requester_id']
            collab_request_counts[uid] = collab_request_counts.get(uid, 0) + 1
        
        project_created_counts = {}
        for pc in (projects_created_result.data or []):
            uid = pc['creator_id']
            project_created_counts[uid] = project_created_counts.get(uid, 0) + 1
        
        project_joined_counts = {}
        for pj in (projects_joined_result.data or []):
            uid = pj['user_id']
            project_joined_counts[uid] = project_joined_counts.get(uid, 0) + 1
        
        # Enrich users with stats
        for user in users_result.data:
            uid = user['id']
            stats = user_stats.get(uid, {
                'total_sessions': 0,
                'total_minutes_on_platform': 0,
                'is_active': False
            })
            user['user_id'] = uid  # Add user_id field for consistency
            user['total_sessions'] = stats['total_sessions']
            user['total_minutes_on_platform'] = stats['total_minutes_on_platform']
            user['is_active'] = stats['is_active']
            
            # Set actual engagement metrics from database
            user['github_views'] = view_counts.get(uid, 0)
            user['github_clicks'] = click_counts.get(uid, 0)
            user['live_project_views'] = project_view_counts.get(uid, 0)
            user['collab_requests_sent'] = collab_request_counts.get(uid, 0)
            user['projects_created'] = project_created_counts.get(uid, 0)
            user['projects_joined'] = project_joined_counts.get(uid, 0)
        
        # Get total count (approximate for speed)
        count_result = supabase_admin.table('users')\
            .select('id', count='estimated')\
            .limit(1)\
            .execute()
        
        return jsonify({
            'success': True,
            'data': {
                'users': users_result.data,
                'total': count_result.count or 0,
                'limit': limit,
                'offset': offset
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting users list: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/admin/analytics/user/<user_id>', methods=['GET'])
@admin_required
def api_admin_user_detail(user_id):
    """Get detailed analytics for a specific user"""
    try:
        from database.connection import supabase_admin
        
        # Get user info (using admin client to see all users)
        user_result = supabase_admin.table('users')\
            .select('*')\
            .eq('id', user_id)\
            .execute()
        
        if not user_result.data:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        
        user = user_result.data[0]
        
        # Check if user is currently logged in (has active session within 24h without logout)
        from datetime import datetime, timedelta
        cutoff_time = (datetime.utcnow() - timedelta(hours=24)).isoformat()
        
        active_session = supabase_admin.table('user_sessions')\
            .select('id, login_time')\
            .eq('user_id', user_id)\
            .is_('logout_time', 'null')\
            .gte('login_time', cutoff_time)\
            .limit(1)\
            .execute()
        
        user['is_active'] = len(active_session.data) > 0 if active_session.data else False
        
        # Get user profile
        profile_result = supabase_admin.table('user_profiles')\
            .select('*')\
            .eq('user_id', user_id)\
            .execute()
        
        profile = profile_result.data[0] if profile_result.data else None
        
        # Get user engagement stats - calculate directly instead of using slow view
        # Get sessions for this user
        sessions_result = supabase_admin.table('user_sessions')\
            .select('*')\
            .eq('user_id', user_id)\
            .order('login_time', desc=True)\
            .execute()
        
        # Calculate engagement stats from sessions
        total_sessions = len(sessions_result.data) if sessions_result.data else 0
        total_minutes = sum(s.get('total_minutes', 0) or 0 for s in (sessions_result.data or []))
        
        # Get actual engagement metrics from database
        clicks_result = supabase_admin.table('user_interactions')\
            .select('id', count='exact')\
            .eq('user_id', user_id)\
            .eq('interaction_type', 'click')\
            .execute()
        
        bookmarks_result = supabase_admin.table('user_interactions')\
            .select('id', count='exact')\
            .eq('user_id', user_id)\
            .eq('interaction_type', 'bookmark_add')\
            .execute()
        
        views_result = supabase_admin.table('recommendation_results')\
            .select('id', count='exact')\
            .eq('user_id', user_id)\
            .execute()
        
        project_views_result = supabase_admin.table('project_views')\
            .select('id', count='exact')\
            .eq('viewer_id', user_id)\
            .execute()
        
        collab_requests_result = supabase_admin.table('collaboration_requests')\
            .select('id', count='exact')\
            .eq('requester_id', user_id)\
            .neq('status', 'project_match_notification')\
            .execute()
        
        projects_created_result = supabase_admin.table('user_projects')\
            .select('id', count='exact')\
            .eq('creator_id', user_id)\
            .execute()
        
        projects_joined_result = supabase_admin.table('project_members')\
            .select('id', count='exact')\
            .eq('user_id', user_id)\
            .execute()
        
        engagement = {
            'user_id': user_id,
            'total_sessions': total_sessions,
            'total_minutes_on_platform': total_minutes,
            'github_views': views_result.count or 0,
            'github_clicks': clicks_result.count or 0,
            'github_bookmarks': bookmarks_result.count or 0,
            'live_project_views': project_views_result.count or 0,
            'collab_requests_sent': collab_requests_result.count or 0,
            'projects_created': projects_created_result.count or 0,
            'projects_joined': projects_joined_result.count or 0
        }
        
        # Get recent activity (last 10 sessions)
        recent_sessions = sessions_result.data[:10] if sessions_result.data else []
        
        return jsonify({
            'success': True,
            'data': {
                'user': user,
                'profile': profile,
                'engagement': engagement,
                'recent_sessions': recent_sessions
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting user detail for {user_id}: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/admin/analytics/realtime', methods=['GET'])
@admin_required
def api_admin_realtime_stats():
    """
    Get real-time statistics
    Updated every few seconds for live dashboard
    """
    try:
        # Get current active users (sessions in last 5 minutes)
        five_min_ago = (datetime.now() - timedelta(minutes=5)).isoformat()
        
        active_sessions = supabase.table('user_sessions')\
            .select('user_id', count='exact')\
            .gte('last_activity', five_min_ago)\
            .execute()
        
        # Get today's metrics
        today = datetime.now().date().isoformat()
        
        today_users = supabase.table('user_sessions')\
            .select('user_id')\
            .gte('login_time', today)\
            .execute()
        
        today_recs = supabase.table('recommendation_results')\
            .select('id', count='exact')\
            .gte('created_at', today)\
            .execute()
        
        today_clicks = supabase.table('user_interactions')\
            .select('id', count='exact')\
            .eq('interaction_type', 'click')\
            .gte('interaction_time', today)\
            .execute()
        
        # Calculate today's CTR
        today_ctr = round(
            (today_clicks.count / today_recs.count * 100) if today_recs.count > 0 else 0,
            2
        )
        
        return jsonify({
            'success': True,
            'data': {
                'active_users_now': len(set([s['user_id'] for s in active_sessions.data])) if active_sessions.data else 0,
                'today_unique_users': len(set([s['user_id'] for s in today_users.data])) if today_users.data else 0,
                'today_recommendations': today_recs.count or 0,
                'today_clicks': today_clicks.count or 0,
                'today_ctr': today_ctr,
                'timestamp': datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting realtime stats: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


# Add this at the end of your ADMIN ROUTES section
logger.info("✅ Admin analytics routes initialized")

@app.route('/api/admin/analytics/rl-performance', methods=['GET'])
@admin_required
def api_admin_rl_performance():
    """
    Get RL recommendation engine performance metrics
    
    Query params:
        days (int): Number of days to analyze (default: 7)
    """
    try:
        days = request.args.get('days', 7, type=int)
        from database.connection import supabase_admin
        from datetime import timedelta
        
        # Always return RL enabled status based on app configuration
        rl_enabled = USE_RL_RECOMMENDATIONS
        
        if not rl_enabled:
            return jsonify({
                'success': False,
                'error': 'RL recommendations not enabled',
                'rl_enabled': False
            })
        
        if not recommendation_service:
            return jsonify({
                'success': False,
                'error': 'Recommendation service not initialized',
                'rl_enabled': True
            })
        
        # Calculate date range
        since_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        # Optimize: Only fetch interaction_type column instead of all columns
        try:
            interactions = supabase_admin.table('user_interactions')\
                .select('interaction_type, github_reference_id')\
                .gte('interaction_time', since_date)\
                .limit(10000)\
                .execute()
        except Exception as db_error:
            logger.error(f"Error fetching interactions: {str(db_error)}")
            return jsonify({
                'success': False,
                'error': 'Database query failed. Please try again.',
                'rl_enabled': True
            }), 500
        
        # Calculate metrics from real data
        total_interactions = len(interactions.data) if interactions.data else 0
        
        # Calculate rewards from interactions
        total_reward = 0
        positive_count = 0
        if interactions.data:
            for interaction in interactions.data:
                interaction_type = interaction.get('interaction_type', 'view')
                
                # Skip non-recommendation interactions
                if interaction_type in ['notification_read', 'notification_view']:
                    continue
                
                # Reward calculation
                if interaction_type == 'click':
                    reward = 5.0
                elif interaction_type in ['bookmark', 'bookmark_add']:
                    reward = 10.0
                elif interaction_type == 'bookmark_remove':
                    reward = -5.0  # Negative reward for removing bookmark
                elif interaction_type == 'view':
                    reward = 1.0
                else:
                    reward = 0
                
                total_reward += reward
                if reward > 0:
                    positive_count += 1
        
        avg_reward = round(total_reward / max(total_interactions, 1), 2)
        
        # Calculate positive rate (exclude notifications from denominator)
        recommendation_interactions = total_interactions - sum(
            1 for i in (interactions.data or []) 
            if i.get('interaction_type') in ['notification_read', 'notification_view']
        )
        positive_rate = round((positive_count / max(recommendation_interactions, 1)) * 100, 2)
        
        # Get top projects from actual interactions
        top_projects_data = []
        if interactions.data:
            # Count interactions per project (exclude notifications)
            project_stats = {}
            for interaction in interactions.data:
                interaction_type = interaction.get('interaction_type', 'view')
                
                # Skip non-recommendation interactions
                if interaction_type in ['notification_read', 'notification_view']:
                    continue
                
                project_id = interaction.get('github_reference_id')
                if project_id:
                    if project_id not in project_stats:
                        project_stats[project_id] = {
                            'clicks': 0,
                            'views': 0,
                            'bookmarks': 0,
                            'total': 0
                        }
                    
                    project_stats[project_id]['total'] += 1
                    if interaction_type == 'click':
                        project_stats[project_id]['clicks'] += 1
                    elif interaction_type in ['bookmark', 'bookmark_add']:
                        project_stats[project_id]['bookmarks'] += 1
                    elif interaction_type == 'view':
                        project_stats[project_id]['views'] += 1
            
            # Get top 10 projects
            sorted_projects = sorted(
                project_stats.items(), 
                key=lambda x: (x[1]['clicks'], x[1]['total']), 
                reverse=True
            )[:10]
            
            # Batch fetch project details in single query
            if sorted_projects:
                project_ids = [p[0] for p in sorted_projects]
                try:
                    projects_result = supabase_admin.table('github_references')\
                        .select('id, title, domain')\
                        .in_('id', project_ids)\
                        .execute()
                    
                    # Create lookup dict for fast access
                    projects_lookup = {p['id']: p for p in (projects_result.data or [])}
                    
                    # Enrich with project details
                    for project_id, stats in sorted_projects:
                        project = projects_lookup.get(project_id)
                        if project:
                            success_rate = round((stats['clicks'] / max(stats['total'], 1)) * 100, 1)
                            avg_project_reward = (
                                stats['clicks'] * 5.0 + 
                                stats['views'] * 1.0 + 
                                stats['bookmarks'] * 10.0
                            )
                            avg_project_reward = round(avg_project_reward / max(stats['total'], 1), 2)
                            
                            top_projects_data.append({
                                'id': project_id,
                                'title': project['title'],
                                'domain': project.get('domain', 'N/A'),
                                'success_rate': success_rate,
                                'total_interactions': stats['total'],
                                'avg_reward': avg_project_reward,
                                'clicks': stats['clicks'],
                                'views': stats['views']
                            })
                except Exception as proj_error:
                    logger.warning(f"Error fetching project details: {str(proj_error)}")
                    # Continue without project details
        
        # Get training history with error handling
        training_history_data = []
        try:
            training_history = supabase_admin.table('rl_training_history')\
                .select('*')\
                .order('training_timestamp', desc=True)\
                .limit(30)\
                .execute()
            training_history_data = training_history.data if training_history and training_history.data else []
        except Exception as th_error:
            logger.warning(f"Error fetching training history: {str(th_error)}")
            # Continue without training history
            training_history_data = []
        
        # Calculate improvement trends (compare with previous training session)
        reward_trend = 0
        positive_rate_trend = 0
        ctr_trend = 0
        
        if training_history_data and len(training_history_data) > 1:
            recent = training_history_data[0]
            previous = training_history_data[1]  # Compare with immediately previous session, not oldest
            
            # Only calculate trend if both values are non-zero and reasonable
            recent_reward = recent.get('post_avg_reward', 0)
            previous_reward = previous.get('post_avg_reward', 0)
            
            if previous_reward != 0 and recent_reward != 0:
                reward_trend = ((recent_reward - previous_reward) / abs(previous_reward)) * 100
            
            # Positive rate trend
            recent_positive_rate = recent.get('post_positive_rate', 0)
            previous_positive_rate = previous.get('post_positive_rate', 0)
            
            if previous_positive_rate and recent_positive_rate and previous_positive_rate != 0:
                positive_rate_trend = ((recent_positive_rate - previous_positive_rate) / abs(previous_positive_rate)) * 100
                # Cap at reasonable values
                positive_rate_trend = max(-100, min(100, positive_rate_trend))
            
            # CTR trend - but cap at reasonable range (-100% to +200%)
            recent_ctr = recent.get('post_avg_ctr', 0)
            previous_ctr = previous.get('post_avg_ctr', 0)
            
            if previous_ctr != 0 and recent_ctr != 0 and abs(previous_ctr - recent_ctr) < previous_ctr * 2:
                ctr_trend = ((recent_ctr - previous_ctr) / abs(previous_ctr)) * 100
                # Cap trend at reasonable values
                ctr_trend = max(-100, min(200, ctr_trend))
        
        # Build performance object
        performance = {
            'avg_reward': avg_reward,
            'positive_interaction_rate': positive_rate,
            'total_training_examples': total_interactions,
            'top_projects': top_projects_data,
            'exploration_rate': 0.15,
            'days_analyzed': days
        }
        
        return jsonify({
            'success': True,
            'rl_enabled': rl_enabled,  # Always reflect actual app configuration
            'data': {
                'performance': performance,
                'training_history': training_history_data,
                'trends': {
                    'reward_improvement': round(reward_trend, 2),
                    'positive_rate_improvement': round(positive_rate_trend, 2),
                    'ctr_improvement': round(ctr_trend, 2)
                },
                'system_info': {
                    'exploration_rate': recommendation_service.exploration_rate,
                    'similarity_weight': recommendation_service.similarity_weight,
                    'bandit_weight': recommendation_service.bandit_weight
                }
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting RL performance: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'rl_enabled': USE_RL_RECOMMENDATIONS
        }), 500


@app.route('/api/admin/rl/trigger-training', methods=['POST'])
@admin_required
def api_admin_trigger_rl_training():
    """
    Manually trigger RL model retraining
    This should only be called after reviewing A/B testing results
    
    Body params:
        days (int): Number of days of data to process (default: 7)
    """
    try:
        if not USE_RL_RECOMMENDATIONS:
            return jsonify({
                'success': False,
                'error': 'RL recommendations not enabled'
            }), 400
        
        if not background_task_scheduler:
            return jsonify({
                'success': False,
                'error': 'Background task scheduler not initialized'
            }), 500
        
        data = request.get_json() or {}
        days = data.get('days', 7)
        
        logger.info(f"🎯 Admin {session.get('user_email')} triggered manual RL training for {days} days")
        logger.info(f"   Training should only be triggered after A/B testing shows positive results")
        
        # Run manual retraining
        performance = background_task_scheduler.run_manual_retrain(days=days)
        
        logger.info(f"✅ Manual RL training completed successfully")
        
        return jsonify({
            'success': True,
            'message': f'RL training completed for {days} days of data',
            'performance': performance,
            'note': 'Model has been updated with latest user interaction data'
        })
        
    except Exception as e:
        logger.error(f"❌ Error triggering RL training: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/admin/rl-performance')
@admin_required
def admin_rl_dashboard():
    """
    Admin RL Performance Monitoring Dashboard
    Shows comprehensive RL metrics, training history, and top projects
    """
    logger.info(f"Admin RL dashboard accessed by {session.get('user_email')}")
    return render_template('admin/rl_dashboard.html')


@app.route('/admin/ab-testing')
@admin_required
def admin_ab_testing():
    """
    Admin A/B Testing Dashboard
    Compare RL vs Baseline recommendation performance
    """
    logger.info(f"Admin A/B testing dashboard accessed by {session.get('user_email')}")
    return render_template('admin/ab_testing.html')


@app.route('/api/admin/ab-testing/dashboard', methods=['GET'])
@admin_required
def api_admin_ab_testing_dashboard():
    """
    Get A/B testing dashboard data
    Returns active test, metrics, and past tests
    """
    try:
        from services.ab_test_service import get_ab_test_service
        
        ab_test_service = get_ab_test_service()
        
        # Get active test
        active_test = ab_test_service.get_active_test_config()
        
        # Get metrics if there's an active test
        metrics = None
        if active_test:
            metrics = ab_test_service.calculate_test_metrics(active_test['id'], days=7)
        
        # Get past tests
        past_tests_result = supabase_admin.table('ab_test_configs')\
            .select('*')\
            .eq('status', 'ended')\
            .order('created_at', desc=True)\
            .limit(10)\
            .execute()
        
        past_tests = past_tests_result.data or []
        
        return jsonify({
            'success': True,
            'active_test': active_test,
            'metrics': metrics,
            'past_tests': past_tests
        })
        
    except Exception as e:
        logger.error(f"Error getting A/B test dashboard data: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/admin/ab-testing/start', methods=['POST'])
@admin_required
def api_admin_ab_testing_start():
    """
    Start a new A/B test
    """
    try:
        from services.ab_test_service import get_ab_test_service
        
        data = request.get_json()
        
        test_name = data.get('test_name')
        description = data.get('description', '')
        control_percentage = data.get('control_percentage', 50)
        duration_days = data.get('duration_days', 14)
        
        if not test_name:
            return jsonify({
                'success': False,
                'error': 'Test name is required'
            }), 400
        
        ab_test_service = get_ab_test_service()
        
        test_config = ab_test_service.start_new_test(
            test_name=test_name,
            control_percentage=control_percentage,
            duration_days=duration_days,
            description=description
        )
        
        logger.info(f"Admin {session.get('user_email')} started A/B test: {test_name}")
        
        return jsonify({
            'success': True,
            'test': test_config
        })
        
    except Exception as e:
        logger.error(f"Error starting A/B test: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/admin/ab-testing/end/<test_id>', methods=['POST'])
@admin_required
def api_admin_ab_testing_end(test_id):
    """
    End an A/B test and rollout winner
    """
    try:
        from services.ab_test_service import get_ab_test_service
        
        ab_test_service = get_ab_test_service()
        
        result = ab_test_service.end_test_and_rollout_winner(test_id)
        
        logger.info(f"Admin {session.get('user_email')} ended A/B test: {test_id}")
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error ending A/B test: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/admin/users')
@admin_required
def admin_users():
    """Admin user management"""
    logger.info("Admin users page accessed")
    
    # TODO: Implement get all users with stats
    # users = user_service.get_all_users_with_stats()
    
    return render_template('admin/users.html')

@app.route('/admin/projects')
@admin_required
def admin_projects():
    """Admin project management"""
    logger.info("Admin projects page accessed")
    
    # TODO: Implement get all user projects
    # projects = project_service.get_all_projects_with_stats()
    
    return render_template('admin/projects.html')

@app.route('/api/admin/analytics/github', methods=['GET'])
@admin_required
def api_admin_github_analytics():
    """API: Get GitHub recommendation analytics"""
    days = request.args.get('days', 30, type=int)
    
    logger.info(f"Admin GitHub analytics API called for {days} days")
    
    # TODO: Implement query analytics
    # data = {
    #     'ctr': analytics_service.get_github_ctr(days),
    #     'position_bias': analytics_service.get_position_bias(days),
    #     'popular_projects': analytics_service.get_popular_github_projects(days)
    # }
    
    return jsonify({'success': False, 'error': 'Not yet implemented'})

@app.route('/api/admin/analytics/collaboration', methods=['GET'])
@admin_required
def api_admin_collaboration_analytics():
    """API: Get collaboration analytics"""
    days = request.args.get('days', 30, type=int)
    
    logger.info(f"Admin collaboration analytics API called for {days} days")
    
    # TODO: Implement query collaboration_analytics view
    # data = {
    #     'conversion_rate': ...,
    #     'successful_matches': ...,
    #     'acceptance_rate': ...
    # }
    
    return jsonify({'success': False, 'error': 'Not yet implemented'})

@app.route('/api/admin/performance/live', methods=['GET'])
@admin_required
def api_admin_performance_live():
    """Get live performance metrics"""
    try:
        summary = perf_monitor.get_performance_summary()
        logger.info("Admin accessed live performance metrics")
        return jsonify({'success': True, 'metrics': summary})
    except Exception as e:
        logger.error(f"Error getting performance metrics: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/admin/migrate-skills', methods=['POST'])
@admin_required
def api_admin_migrate_skills():
    """Migrate old skill values to new standardized format"""
    try:
        from database.connection import supabase_admin
        
        # Mapping of old values to new standardized values
        SKILL_MAPPING = {
            'Frontend Development': 'web_development',
            'Backend Development': 'web_development',
            'UI/UX Design': 'web_development',
            'Mobile Development': 'mobile_development',
            'Data Science': 'data_science',
            'Machine Learning': 'machine_learning',
            'DevOps': 'devops',
            'Quality Assurance': 'open_source',
            'Blockchain': 'blockchain',
            'Cybersecurity': 'cybersecurity',
            'Game Development': 'game_development',
        }
        
        # Get all projects
        result = supabase_admin.table('user_projects').select('id, title, required_skills').execute()
        
        if not result.data:
            return jsonify({'success': True, 'message': 'No projects found', 'updated': 0})
        
        updated_projects = []
        updated_count = 0
        
        for project in result.data:
            old_skills = project.get('required_skills', [])
            if not old_skills:
                continue
            
            # Convert old skills to new format
            new_skills = []
            for skill in old_skills:
                new_skill = SKILL_MAPPING.get(skill, skill)  # Use mapping or keep original
                if new_skill not in new_skills:  # Avoid duplicates
                    new_skills.append(new_skill)
            
            # Only update if skills changed
            if set(old_skills) != set(new_skills):
                logger.info(f"Updating project '{project['title']}': {old_skills} -> {new_skills}")
                
                # Update the project
                supabase_admin.table('user_projects').update({
                    'required_skills': new_skills
                }).eq('id', project['id']).execute()
                
                updated_projects.append({
                    'title': project['title'],
                    'old_skills': old_skills,
                    'new_skills': new_skills
                })
                updated_count += 1
        
        return jsonify({
            'success': True,
            'message': f'Successfully migrated {updated_count} projects',
            'updated': updated_count,
            'projects': updated_projects
        })
        
    except Exception as e:
        logger.error(f"Error during skill migration: {str(e)}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== ERROR HANDLERS ====================

@app.errorhandler(404)
def not_found(error):
    logger.warning(f"404 error: {request.url} from {request.remote_addr}")
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Endpoint not found'}), 404
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"500 error: {request.url} from {request.remote_addr} - {str(error)}")
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Internal server error'}), 500
    return render_template('500.html'), 500

@app.errorhandler(403)
def forbidden(error):
    logger.warning(f"403 error: {request.url} from {request.remote_addr}")
    if request.path.startswith('/api/'):
        return jsonify({'error': 'Forbidden'}), 403
    flash('You do not have permission to access this page', 'error')
    return redirect(url_for('dashboard'))

# ==================== TEMPLATE FILTERS ====================

@app.template_filter('datetime')
def format_datetime(value):
    """Format datetime for display"""
    if isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
            return dt.strftime('%B %d, %Y at %I:%M %p')
        except:
            return value
    return value

@app.template_filter('timeago')
def time_ago(value):
    """Convert datetime to relative time"""
    if isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
            now = datetime.now(dt.tzinfo) if dt.tzinfo else datetime.now()
            diff = now - dt
            
            seconds = diff.total_seconds()
            if seconds < 60:
                return "just now"
            elif seconds < 3600:
                minutes = int(seconds / 60)
                return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
            elif seconds < 86400:
                hours = int(seconds / 3600)
                return f"{hours} hour{'s' if hours != 1 else ''} ago"
            else:
                days = int(seconds / 86400)
                return f"{days} day{'s' if days != 1 else ''} ago"
        except:
            return value
    return value

@app.template_filter('format_skill')
def format_skill(value):
    """Format skill name from snake_case to Title Case"""
    if not value:
        return value
    # Replace underscores with spaces and capitalize each word
    return value.replace('_', ' ').title()

# ==================== CONTEXT PROCESSORS ====================

@app.context_processor
def inject_user():
    """Inject user info into all templates"""
    user_id = session.get('user_id')
    unread_notifications_count = 0
    
    if user_id:
        try:
            from database.connection import supabase_admin
            
            # Get IDs of notifications the user has already read from user_interactions
            read_interactions = supabase_admin.table('user_interactions').select('additional_data').eq(
                'user_id', user_id
            ).eq('interaction_type', 'notification_read').execute()
            
            read_notification_ids = set()
            if read_interactions.data:
                for interaction in read_interactions.data:
                    if interaction.get('additional_data', {}).get('notification_id'):
                        read_notification_ids.add(interaction['additional_data']['notification_id'])
            
            # Count all current notifications
            all_notification_ids = []
            
            # 1. Pending join requests to user's projects
            projects_result = supabase_admin.table('user_projects').select('id').eq('creator_id', user_id).execute()
            project_ids = [p['id'] for p in projects_result.data] if projects_result.data else []
            
            if project_ids:
                result = supabase_admin.table('collaboration_requests').select('id').in_('project_id', project_ids).eq('status', 'pending').execute()
                all_notification_ids.extend([r['id'] for r in result.data] if result.data else [])
            
            # 2. Response notifications (accepted/rejected)
            result = supabase_admin.table('collaboration_requests').select('id').eq('project_owner_id', user_id).in_('status', ['notification_accepted', 'notification_rejected']).execute()
            all_notification_ids.extend([r['id'] for r in result.data] if result.data else [])
            
            # 3. Project match notifications
            result = supabase_admin.table('collaboration_requests').select('id').eq('project_owner_id', user_id).eq('status', 'project_match_notification').execute()
            all_notification_ids.extend([r['id'] for r in result.data] if result.data else [])
            
            # Calculate unread (notifications not in read list)
            unread_notification_ids = [nid for nid in all_notification_ids if nid not in read_notification_ids]
            unread_notifications_count = len(unread_notification_ids)
            
        except Exception as e:
            logger.error(f"Error getting notification count: {e}")
            unread_notifications_count = 0
    
    return dict(
        user_id=user_id,
        user_email=session.get('user_email'),
        user_name=session.get('user_name'),
        profile_completed=session.get('profile_completed', False),
        is_admin=session.get('user_email') in ADMIN_EMAILS,
        unread_notifications_count=unread_notifications_count
    )

# ==================== HEALTH CHECK ====================

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'services': {
            'github_recommendations': 'active',
            'live_projects': 'active',
            'collaboration': 'active',
            'analytics': 'active'
        }
    })

# ==================== APPLICATION STARTUP ====================

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🚀 CoChain.ai - Complete Platform")
    print("="*60)
    print("\n📱 User Routes:")
    print("   /register → Sign up")
    print("   /login → Log in")
    print("   /dashboard → GitHub inspiration projects")
    print("   /live-projects → User collaboration projects")
    print("   /my-projects → Your projects")
    print("   /create-project → Create new project")
    print("   /collaboration-requests → Manage requests")
    print("   /explore → Browse GitHub projects")
    print("   /bookmarks → Saved GitHub projects")
    print("   /profile → User profile")
    print("   /profile/setup → Profile setup/edit")
    print("\n🔧 Admin Routes:")
    print("   /admin/analytics → Platform analytics")
    print("   /admin/users → User management")
    print("   /admin/projects → Project management")
    print("\n📊 API Endpoints:")
    print("   POST /api/github/recommend")
    print("   POST /api/projects/send-request")
    print("   POST /api/projects/respond-request")
    print("   POST /api/bookmark")
    print("   PUT  /api/bookmark/notes")
    print("   DELETE /api/bookmark/<id>")
    print("   POST /api/recommendations/load-more")
    print("   POST /api/project/view")
    print("   GET  /api/admin/analytics/github")
    print("   GET  /api/admin/analytics/collaboration")
    print("   GET  /api/admin/performance/live")
    print("="*60 + "\n")
    
    logger.info("🚀 Starting Flask application...")
    
    # Get configuration from environment
    port = int(os.getenv('PORT', 5000))
    debug_mode = os.getenv('FLASK_ENV') != 'production'
    host = '0.0.0.0'
    
    if debug_mode:
        logger.warning("⚠️ Running in DEVELOPMENT mode with debug=True")
        logger.warning("⚠️ DO NOT use debug mode in production!")
        app.run(debug=True, port=port, host=host)
    else:
        logger.info("✅ Running in PRODUCTION mode")
        logger.info(f"✅ Listening on {host}:{port}")
        logger.info("ℹ️  For production deployment, use: gunicorn app:app")
        # In production, gunicorn will serve the app (not app.run)
        # This block is here for local testing with production settings
        app.run(debug=False, port=port, host=host)