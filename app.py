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
from database.connection import supabase

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', os.urandom(24))
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Set Flask app logger level
app.logger.setLevel(logging.INFO)

# Initialize services
user_service = UserService()

# Initialize recommendation service with error handling
recommendation_service = None
try:
    from services.personalized_recommendations import PersonalizedRecommendationService
    recommendation_service = PersonalizedRecommendationService()
    logger.info("✅ Recommendation service initialized successfully")
except Exception as e:
    logger.warning(f"⚠️ Failed to initialize recommendation service: {str(e)}")

# Admin emails
ADMIN_EMAILS = [
    'admin@cochain.ai', 
    'analytics@cochain.ai',
    'anthony.raju@msds.christuniversity.in',
    'tonykondaveetijmj98@gmail.com'  # Add your email here
]

logger.info("CoChain.ai - Complete Platform Starting...")
print("🚀 CoChain.ai - Complete Platform Starting...")

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
            logger.info(f"User {user_id} redirected to profile setup")
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
                    
                    logger.info(
                        f"Retrieved {len(recommendations)} recommendations for user {user_id} "
                        f"({'from cache' if cache_hit else 'fresh'}) in {rec_duration_ms:.2f}ms"
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

@app.route('/live-projects')
@login_required
def live_projects():
    """Live Projects page - User-created projects seeking collaboration"""
    user_id = session.get('user_id')
    
    logger.debug(f"Live projects accessed by user: {user_id}")
    
    try:
        projects = project_service.get_open_projects(limit=20)
        logger.info(f"Retrieved {len(projects)} open projects for user: {user_id}")
    except Exception as e:
        logger.error(f"Error getting live projects: {str(e)}")
        projects = []
    
    return render_template('live_projects.html', projects=projects)

@app.route('/live-projects/<project_id>')
@login_required
def project_detail(project_id):
    """View detailed project information"""
    user_id = session.get('user_id')
    
    # TODO: Implement project detail page
    # project = project_service.get_project(project_id)
    # creator_profile = user_service.get_user_profile(project.creator_id)
    # team_members = project_service.get_team_members(project_id)
    
    # Track project view
    event_tracker.track_project_view(
        user_id=user_id,
        project_id=project_id,
        session_id=session.get('session_id')
    )
    
    logger.info(f"Project detail page accessed: {project_id} by user {user_id}")
    return render_template('project_detail.html')

@app.route('/my-projects')
@login_required
def my_projects():
    """User's own projects"""
    user_id = session.get('user_id')
    
    logger.debug(f"My projects page accessed by user: {user_id}")
    
    # TODO: Implement get user's created and joined projects
    # my_projects = project_service.get_user_projects(user_id)
    # joined_projects = project_service.get_joined_projects(user_id)
    
    return render_template('my_projects.html')

@app.route('/create-project', methods=['GET', 'POST'])
@login_required
def create_project():
    """Create new project"""
    if request.method == 'POST':
        data = request.json if request.is_json else request.form
        user_id = session.get('user_id')
        
        logger.info(f"Project creation attempt by user: {user_id}")
        
        project_data = {
            'creator_id': user_id,
            'creator_name': session.get('user_name'),
            'title': data.get('title'),
            'description': data.get('description'),
            'detailed_requirements': data.get('detailed_requirements'),
            'project_goals': data.get('project_goals'),
            'tech_stack': data.getlist('tech_stack') if hasattr(data, 'getlist') else data.get('tech_stack', []),
            'required_skills': data.getlist('required_skills') if hasattr(data, 'getlist') else data.get('required_skills', []),
            'complexity_level': data.get('complexity_level', 'intermediate'),
            'estimated_duration': data.get('estimated_duration'),
            'domain': data.get('domain'),
            'max_collaborators': data.get('max_collaborators', 5),
            'needed_roles': data.getlist('needed_roles') if hasattr(data, 'getlist') else data.get('needed_roles', []),
            'is_open_for_collaboration': data.get('is_open_for_collaboration', True)
        }
        
        try:
            # TODO: Implement project creation
            # result = project_service.create_project(project_data)
            
            # Temporary response
            result = {'success': False, 'error': 'Project creation not yet implemented'}
            
            if request.is_json:
                return jsonify(result)
            
            if result.get('success'):
                logger.info(f"Project created successfully by user: {user_id}")
                flash('Project created successfully!', 'success')
                return redirect(url_for('my_projects'))
            else:
                logger.error(f"Project creation failed for user {user_id}: {result.get('error', 'Unknown error')}")
                flash('Failed to create project', 'error')
        except Exception as e:
            logger.error(f"Project creation error for user {user_id}: {str(e)}")
            if request.is_json:
                return jsonify({'success': False, 'error': str(e)})
            flash('Error creating project', 'error')
    
    return render_template('create_project.html')

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
@login_required
def explore():
    """Explore GitHub projects by category/interest"""
    user_id = session.get('user_id')
    interest = request.args.get('interest', 'web_development')
    
    logger.debug(f"Explore page accessed by user {user_id} for interest: {interest}")
    
    try:
        # TODO: Implement get recommendations by interest
        # if recommendation_service:
        #     projects = recommendation_service.get_recommendations_by_interest(interest)
        # else:
        #     projects = []
        projects = []
        
        logger.info(f"Retrieved {len(projects)} projects for interest '{interest}' for user: {user_id}")
    except Exception as e:
        logger.error(f"Error getting projects by interest '{interest}': {str(e)}")
        projects = []
    
    return render_template('explore.html', 
                         current_interest=interest,
                         projects=projects)

@app.route('/bookmarks')
@login_required
def bookmarks():
    """User's bookmarked GitHub projects"""
    user_id = session.get('user_id')
    
    try:
        logger.info(f"Fetching bookmarks for user: {user_id}")
        
        bookmarks_result = supabase.table('user_bookmarks').select('''
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
        github_reference_id = data.get('github_reference_id')
        notes = data.get('notes', '')
        
        if not github_reference_id:
            logger.warning(f"Bookmark attempt without project ID by user {user_id}")
            return jsonify({'success': False, 'error': 'Project ID required'}), 400
        
        logger.info(f"Bookmark action for user {user_id}, project {github_reference_id}")
        
        existing = supabase.table('user_bookmarks').select('*')\
            .eq('user_id', user_id)\
            .eq('github_reference_id', github_reference_id)\
            .execute()
        
        if existing.data and len(existing.data) > 0:
            result = supabase.table('user_bookmarks').delete()\
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
            
            result = supabase.table('user_bookmarks').insert(bookmark_data).execute()
            
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
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'error': 'User not logged in'}), 401
            
        data = request.get_json()
        github_reference_id = data.get('github_reference_id')
        notes = data.get('notes', '')
        
        if not github_reference_id:
            return jsonify({'success': False, 'error': 'Project ID required'}), 400
            
        # Check if bookmark exists
        result = supabase.table('user_bookmarks').select('*').eq('user_id', user_id).eq('github_reference_id', github_reference_id).execute()
        
        if not result.data:
            logger.warning(f"Bookmark not found for user {user_id}, project {github_reference_id}")
            return jsonify({'success': False, 'error': 'Bookmark not found'}), 404
            
        # Update notes
        update_result = supabase.table('user_bookmarks').update({
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
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'error': 'User not logged in'}), 401
        
        # Check if bookmark exists
        result = supabase.table('user_bookmarks').select('*').eq('user_id', user_id).eq('github_reference_id', github_reference_id).execute()
        
        if not result.data:
            return jsonify({'success': False, 'error': 'Bookmark not found'}), 404
            
        # Remove bookmark completely
        delete_result = supabase.table('user_bookmarks').delete().eq('user_id', user_id).eq('github_reference_id', github_reference_id).execute()
        
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
        sort_field = request.args.get('sort', 'total_sessions')
        sort_order = request.args.get('order', 'desc')
        
        # Validate sort field to prevent SQL errors
        valid_sort_fields = [
            'email', 'full_name', 'total_sessions', 'total_minutes_on_platform',
            'github_views', 'github_clicks', 'live_project_views', 
            'collab_requests_sent', 'projects_created', 'projects_joined'
        ]
        if sort_field not in valid_sort_fields:
            sort_field = 'total_sessions'  # Default to total_sessions if invalid
        
        # Get users with stats from the view (using admin client to see all users)
        users_result = supabase_admin.table('user_engagement_summary')\
            .select('*')\
            .order(sort_field, desc=(sort_order == 'desc'))\
            .range(offset, offset + limit - 1)\
            .execute()
        
        # Enrich with created_at from users table
        if users_result.data:
            user_ids = [u['user_id'] for u in users_result.data]
            users_data = supabase_admin.table('users')\
                .select('id, created_at')\
                .in_('id', user_ids)\
                .execute()
            
            # Create a map of user_id -> created_at
            created_at_map = {u['id']: u['created_at'] for u in users_data.data} if users_data.data else {}
            
            # Add created_at to each user in the engagement summary
            for user in users_result.data:
                user['created_at'] = created_at_map.get(user['user_id'], None)
        
        # Get total count
        count_result = supabase_admin.table('user_engagement_summary')\
            .select('user_id', count='exact')\
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
        
        # Get user profile
        profile_result = supabase_admin.table('user_profiles')\
            .select('*')\
            .eq('user_id', user_id)\
            .execute()
        
        profile = profile_result.data[0] if profile_result.data else None
        
        # Get user engagement stats
        engagement_result = supabase_admin.table('user_engagement_summary')\
            .select('*')\
            .eq('user_id', user_id)\
            .execute()
        
        engagement = engagement_result.data[0] if engagement_result.data else {}
        
        # Get recent activity
        sessions_result = supabase_admin.table('user_sessions')\
            .select('*')\
            .eq('user_id', user_id)\
            .order('login_time', desc=True)\
            .limit(10)\
            .execute()
        
        return jsonify({
            'success': True,
            'data': {
                'user': user,
                'profile': profile,
                'engagement': engagement,
                'recent_sessions': sessions_result.data
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

# ==================== CONTEXT PROCESSORS ====================

@app.context_processor
def inject_user():
    """Inject user info into all templates"""
    return dict(
        user_id=session.get('user_id'),
        user_email=session.get('user_email'),
        user_name=session.get('user_name'),
        profile_completed=session.get('profile_completed', False),
        is_admin=session.get('user_email') in ADMIN_EMAILS
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
    app.run(debug=True, port=5000, host='0.0.0.0')