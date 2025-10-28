# app.py
"""
CoChain.ai - Complete Platform with GitHub Inspiration + Live Collaboration
============================================================================

User Flow:
1. Register → Fill Profile (with bio)
2. Dashboard → GitHub Projects (inspiration based on bio/interests)
3. Live Projects Tab → User Projects (seeking collaboration)
4. Admin Analytics → Track engagement on both systems (ADMIN ONLY)

Version: 3.0.0
"""

from flask import Flask, request, jsonify, render_template, session, redirect, url_for, flash
from functools import wraps
from datetime import datetime
import uuid
import os
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

# Create logger for this module
logger = logging.getLogger(__name__)

# Import our services
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
try:
    from services.personalized_recommendations import PersonalizedRecommendationService
    recommendation_service = PersonalizedRecommendationService()
    logger.info("✅ Recommendation service initialized successfully")
except Exception as e:
    logger.warning(f"⚠️ Failed to initialize recommendation service: {str(e)}")
    recommendation_service = None

# Admin emails (configure based on your needs)
ADMIN_EMAILS = ['admin@cochain.ai', 'analytics@cochain.ai']

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
        
        # Call auth service to register user
        result = user_service.register_user(
            email=email,
            password=data.get('password'),
            full_name=data.get('full_name')
        )
        
        if result.get('success'):
            logger.info(f"User registered successfully: {email}")
            
            # Auto-login user since no email confirmation required
            session['user_id'] = result['user_id']
            session['user_email'] = result['email']
            session['user_name'] = result['full_name']
            session['profile_completed'] = False
            
            # Store auth session
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
                
            # Show user-friendly error messages
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
    """User login"""
    if 'user_id' in session:
        logger.debug(f"Already logged in user {session.get('user_id')} attempted to access login")
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        data = request.json if request.is_json else request.form
        email = data.get('email', '').strip()
        password = data.get('password', '')
        
        # Validate input
        if not email or not password:
            error_msg = 'Email and password are required'
            logger.warning(f"Login attempt with missing credentials from {request.remote_addr}")
            
            if request.is_json:
                return jsonify({'success': False, 'error': error_msg}), 400
            flash(error_msg, 'error')
            return render_template('login.html')
        
        logger.info(f"🔐 Login attempt for email: {email} from IP: {request.remote_addr}")
        
        try:
            # Call auth service to login
            result = user_service.login_user(email=email, password=password)
            
            logger.info(f"🔍 Auth service result for {email}: success={result.get('success')}, error_type={result.get('error_type')}")
            
            if result.get('success'):
                user = result['user']
                session['user_id'] = user['id']
                session['user_email'] = user['email']
                session['user_name'] = user['full_name']
                session['profile_completed'] = user.get('profile_completed', False)
                
                # Store auth session
                if 'session' in result and result['session']:
                    session['auth_token'] = result['session'].access_token
                    session['refresh_token'] = result['session'].refresh_token
                    logger.info(f"✅ Auth session stored for {email}")
                else:
                    logger.warning(f"⚠️ No auth session available for {email}")
                
                # Create session tracking
                session['session_id'] = str(uuid.uuid4())
                
                logger.info(f"✅ LOGIN SUCCESS: User {email} (ID: {user['id']}) logged in successfully")
                
                if request.is_json:
                    return jsonify({
                        'success': True,
                        'message': 'Login successful!',
                        'user': user,
                        'redirect': url_for('profile_setup') if not user.get('profile_completed') else url_for('dashboard')
                    })
                
                if not user.get('profile_completed'):
                    flash('Welcome! Please complete your profile.', 'info')
                    return redirect(url_for('profile_setup'))
                
                flash('Login successful! Welcome back!', 'success')
                next_page = request.args.get('next')
                return redirect(next_page if next_page else url_for('dashboard'))
            else:
                error_message = result.get('error', 'Login failed')
                error_type = result.get('error_type', 'general')
                
                logger.error(f"❌ LOGIN FAILED for {email}: {error_message} (type: {error_type})")
                
                if request.is_json:
                    return jsonify({
                        'success': False,
                        'error': error_message,
                        'error_type': error_type
                    }), 401
                
                # Provide specific feedback for different error types
                if 'Invalid login credentials' in error_message:
                    flash('❌ Invalid email or password. Please check your credentials and try again.', 'error')
                elif 'User not found' in error_message:
                    flash('❌ No account found with this email. Please register first.', 'error')
                else:
                    flash(f'❌ Login failed: {error_message}', 'error')
                    
        except Exception as e:
            logger.error(f"💥 CRITICAL LOGIN ERROR for {email}: {str(e)}", exc_info=True)
            
            if request.is_json:
                return jsonify({
                    'success': False,
                    'error': 'An unexpected error occurred. Please try again.'
                }), 500
            
            flash('💥 An unexpected error occurred. Please try again.', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """User logout"""
    user_email = session.get('user_email')
    logger.info(f"User logout: {user_email}")
    
    # Call user service to logout from Supabase Auth
    user_service.logout_user()
    
    session.clear()
    flash('You have been logged out successfully', 'success')
    return redirect(url_for('index'))

# ==================== PROFILE MANAGEMENT ====================

@app.route('/profile/setup', methods=['GET', 'POST'])
@login_required
def profile_setup():
    """
    Profile setup/edit page
    Fields: education, field of study, bio (career aspirations),
            skill level, interests, languages, frameworks, learning goals
    """
    user_id = session.get('user_id')
    
    if request.method == 'POST':
        data = request.json if request.is_json else request.form
        
        logger.info(f"Profile setup attempt for user: {user_id}")
        
        profile_data = {
            'education_level': data.get('education_level'),
            'current_year': data.get('current_year'),
            'field_of_study': data.get('field_of_study'),
            'bio': data.get('bio'),  # Career aspirations
            'overall_skill_level': data.get('overall_skill_level', 'intermediate'),
            'areas_of_interest': data.getlist('areas_of_interest') if hasattr(data, 'getlist') else data.get('areas_of_interest', []),
            'programming_languages': data.getlist('programming_languages') if hasattr(data, 'getlist') else data.get('programming_languages', []),
            'frameworks_known': data.getlist('frameworks_known') if hasattr(data, 'getlist') else data.get('frameworks_known', []),
            'learning_goals': data.get('learning_goals'),
            'profile_completed': True
        }
        
        # Save to user_profiles table
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
    
    # GET request - show form
    # Define interest areas for the template
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
        # Get user profile data
        user_profile = user_service.get_user_profile(user_id)
        
        if user_profile.get('success'):
            user_data = user_profile['profile']
            
            # Mock stats for now (you can implement these later)
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
    """
    Main dashboard showing GitHub projects (inspiration)
    Personalized based on user's bio, interests, and skills
    """
    user_id = session.get('user_id')
    
    logger.debug(f"Dashboard accessed by user: {user_id}")
    
    # Check if profile is completed
    if not session.get('profile_completed'):
        logger.info(f"User {user_id} redirected to profile setup - incomplete profile")
        flash('Please complete your profile first', 'warning')
        return redirect(url_for('profile_setup'))
    
    # Get GitHub recommendations based on user profile
    try:
        logger.debug(f"Fetching recommendations for user: {user_id}")
        
        # Get user profile with complete data
        profile_result = user_service.get_user_profile(user_id)
        if profile_result.get('success'):
            user_profile = profile_result['profile']
            logger.debug(f"User profile retrieved successfully for: {user_id}")
            logger.debug(f"User interests: {user_profile.get('areas_of_interest', [])}")
        else:
            # Fallback to basic profile
            logger.warning(f"Could not retrieve user profile for {user_id}, using fallback")
            user_profile = {
                'areas_of_interest': ['web_development', 'machine_learning'],
                'programming_languages': ['Python', 'JavaScript'],
                'overall_skill_level': 'intermediate'
            }
        
        # Get initial 12 recommendations
        if recommendation_service:
            recommendations_result = recommendation_service.get_recommendations_for_user(user_id, num_recommendations=12)
            
            if isinstance(recommendations_result, dict):
                if recommendations_result.get('success'):
                    recommendations = recommendations_result.get('recommendations', [])
                    cache_status = "from cache" if recommendations_result.get('cached') else "freshly generated"
                    logger.info(f"Retrieved {len(recommendations)} recommendations {cache_status} for user: {user_id}")
                else:
                    logger.warning(f"Recommendation service returned error: {recommendations_result.get('error')}")
                    recommendations = []
            else:
                # Fallback if service returns a list directly
                recommendations = recommendations_result if recommendations_result else []
                logger.info(f"Retrieved {len(recommendations)} recommendations for user: {user_id}")
        else:
            logger.warning("Recommendation service not available")
            recommendations = []
        
    except Exception as e:
        logger.error(f"Error getting recommendations for user {user_id}: {str(e)}")
        recommendations = []
    
    return render_template('dashboard.html', 
                         page_title='GitHub Inspiration',
                         recommendations=recommendations,
                         user_interests=user_profile.get('areas_of_interest', []))

@app.route('/live-projects')
@login_required
def live_projects():
    """
    Live Projects page - User-created projects seeking collaboration
    """
    user_id = session.get('user_id')
    
    logger.debug(f"Live projects accessed by user: {user_id}")
    
    try:
        # Get user projects open for collaboration
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
    
    # TODO: Get project details
    # project = project_service.get_project(project_id)
    # creator_profile = profile_service.get_profile(project.creator_id)
    # team_members = project_service.get_team_members(project_id)
    
    # Track project view
    # TODO: Insert into project_views table
    
    return render_template('project_detail.html')

@app.route('/my-projects')
@login_required
def my_projects():
    """User's own projects"""
    user_id = session.get('user_id')
    
    # TODO: Get user's created projects
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
            # Create project
            result = project_service.create_project(project_data)
            
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
    
    # TODO: Get requests
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
        # Get GitHub projects by interest
        projects = recommendation_service.get_recommendations_by_interest(interest)
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
        
        # Get user bookmarks with GitHub project details
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
                    # Flatten the structure for easier template access
                    project = bookmark['github_references']
                    bookmark_info = {
                        'bookmark_id': bookmark['id'],
                        'notes': bookmark.get('notes', ''),
                        'is_favorite': bookmark.get('is_favorite', False),
                        'created_at': bookmark['created_at'],
                        # Project details
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
        
        # Get user info for navbar
        user_service = UserService()
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
    
    # TODO: Generate recommendations
    # recommendations = github_recommender.get_recommendations(user_id, data)
    
    return jsonify({'success': True, 'recommendations': []})

@app.route('/api/projects/send-request', methods=['POST'])
@login_required
def api_send_collaboration_request():
    """Send collaboration request"""
    user_id = session.get('user_id')
    data = request.json
    
    request_data = {
        'requester_id': user_id,
        'project_id': data.get('project_id'),
        'requested_role': data.get('role'),
        'cover_message': data.get('cover_message'),
        'why_interested': data.get('why_interested'),
        'relevant_experience': data.get('relevant_experience')
    }
    
    # TODO: Send request
    # result = collab_service.send_request(request_data)
    
    # Track in collaboration_analytics
    # TODO: Insert into collaboration_analytics table
    
    return jsonify({'success': True})

@app.route('/api/projects/respond-request', methods=['POST'])
@login_required
def api_respond_to_request():
    """Accept/reject collaboration request"""
    user_id = session.get('user_id')
    data = request.json
    
    # TODO: Respond to request
    # result = collab_service.respond_to_request(
    #     request_id=data.get('request_id'),
    #     response=data.get('response'),  # 'accepted' or 'rejected'
    #     message=data.get('message')
    # )
    
    # Update collaboration_analytics
    
    return jsonify({'success': True})

@app.route('/api/bookmark', methods=['POST'])
@login_required
def api_add_bookmark():
    """Bookmark a GitHub project"""
    user_id = session.get('user_id')
    data = request.json
    
    try:
        github_reference_id = data.get('github_reference_id')
        notes = data.get('notes', '')
        
        if not github_reference_id:
            return jsonify({'success': False, 'error': 'GitHub reference ID is required'}), 400
        
        logger.info(f"Adding bookmark for user {user_id}, project {github_reference_id}")
        
        # Check if bookmark already exists
        existing = supabase.table('user_bookmarks').select('*').eq('user_id', user_id).eq('github_reference_id', github_reference_id).execute()
        
        if existing.data and len(existing.data) > 0:
            # Toggle bookmark - remove it
            result = supabase.table('user_bookmarks').delete().eq('user_id', user_id).eq('github_reference_id', github_reference_id).execute()
            logger.info(f"Removed bookmark for user {user_id}, project {github_reference_id}")
            return jsonify({'success': True, 'action': 'removed'})
        else:
            # Add new bookmark
            bookmark_data = {
                'user_id': user_id,
                'github_reference_id': github_reference_id,
                'notes': notes
            }
            
            result = supabase.table('user_bookmarks').insert(bookmark_data).execute()
            
            if result.data:
                logger.info(f"Added bookmark for user {user_id}, project {github_reference_id}")
                return jsonify({'success': True, 'action': 'added'})
            else:
                logger.error(f"Failed to add bookmark for user {user_id}, project {github_reference_id}")
                return jsonify({'success': False, 'error': 'Failed to add bookmark'}), 500
                
    except Exception as e:
        logger.error(f"Error managing bookmark for user {user_id}: {str(e)}")
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
        filter_interest = data.get('filter')  # Interest filter from frontend
        
        logger.info(f"Loading more recommendations for user {user_id}, current count: {current_count}, filter: {filter_interest}")
        
        # Maximum 15 total recommendations
        if current_count >= 15:
            return jsonify({
                'success': True,
                'recommendations': [],
                'has_more': False,
                'message': 'Maximum recommendations reached'
            })
        
        # Calculate how many more to load (max 3, but don't exceed 15 total)
        remaining = 15 - current_count
        num_to_load = min(3, remaining)
        
        # Get recommendations with offset
        if recommendation_service:
            # Get more recommendations than needed to account for filtering
            recommendations_result = recommendation_service.get_recommendations_for_user(
                user_id, 
                num_recommendations=30,  # Get more to filter from
                offset=0  # Always start from 0 and handle filtering in memory
            )
            
            if isinstance(recommendations_result, dict) and recommendations_result.get('success'):
                all_recommendations = recommendations_result.get('recommendations', [])
                
                # Apply filter if specified
                if filter_interest and filter_interest != 'all':
                    filtered_recommendations = []
                    filter_text = filter_interest.replace('_', ' ').lower()
                    
                    for rec in all_recommendations:
                        # Check if recommendation matches filter
                        match_found = False
                        
                        # Check in technologies
                        if rec.get('technologies'):
                            tech_text = rec['technologies'].lower()
                            if filter_text in tech_text:
                                match_found = True
                        
                        # Check in domain
                        if rec.get('domain'):
                            domain_text = rec['domain'].lower()
                            if filter_text in domain_text:
                                match_found = True
                        
                        # Check in title and description
                        title_text = (rec.get('title') or '').lower()
                        desc_text = (rec.get('description') or '').lower()
                        if filter_text in title_text or filter_text in desc_text:
                            match_found = True
                        
                        if match_found:
                            filtered_recommendations.append(rec)
                    
                    all_recommendations = filtered_recommendations
                
                # Get the next batch
                new_recommendations = all_recommendations[current_count:current_count + num_to_load]
            else:
                new_recommendations = []
        else:
            new_recommendations = []
        
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

@app.route('/api/project/view', methods=['POST'])
@login_required
def api_track_project_view():
    """Track user viewing a live project"""
    user_id = session.get('user_id')
    data = request.json
    
    # TODO: Insert into project_views table
    # track_service.track_project_view(
    #     project_id=data.get('project_id'),
    #     viewer_id=user_id,
    #     session_id=session.get('session_id')
    # )
    
    return jsonify({'success': True})

# ==================== ADMIN ROUTES (ANALYTICS) ====================

@app.route('/admin/analytics')
@admin_required
def admin_analytics():
    """Admin analytics dashboard"""
    days = request.args.get('days', 30, type=int)
    
    # TODO: Get analytics data
    # github_analytics = analytics_service.get_github_analytics(days)
    # collab_analytics = analytics_service.get_collaboration_analytics(days)
    # user_engagement = analytics_service.get_user_engagement(days)
    
    return render_template('admin/analytics.html')

@app.route('/admin/users')
@admin_required
def admin_users():
    """Admin user management"""
    # TODO: Get all users with stats
    return render_template('admin/users.html')

@app.route('/admin/projects')
@admin_required
def admin_projects():
    """Admin project management"""
    # TODO: Get all user projects
    return render_template('admin/projects.html')

@app.route('/api/admin/analytics/github', methods=['GET'])
@admin_required
def api_admin_github_analytics():
    """API: Get GitHub recommendation analytics"""
    days = request.args.get('days', 30, type=int)
    
    # TODO: Query analytics
    # data = {
    #     'ctr': analytics_service.get_github_ctr(days),
    #     'position_bias': analytics_service.get_position_bias(days),
    #     'popular_projects': analytics_service.get_popular_github_projects(days)
    # }
    
    return jsonify({'success': True})

@app.route('/api/admin/analytics/collaboration', methods=['GET'])
@admin_required
def api_admin_collaboration_analytics():
    """API: Get collaboration analytics"""
    days = request.args.get('days', 30, type=int)
    
    # TODO: Query collaboration_analytics view
    # data = {
    #     'conversion_rate': ...,
    #     'successful_matches': ...,
    #     'acceptance_rate': ...
    # }
    
    return jsonify({'success': True})

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
    print("\n🔧 Admin Routes:")
    print("   /admin/analytics → Platform analytics")
    print("   /admin/users → User management")
    print("   /admin/projects → Project management")
    print("\n📊 API Endpoints:")
    print("   POST /api/github/recommend")
    print("   POST /api/projects/send-request")
    print("   POST /api/projects/respond-request")
    print("   POST /api/bookmark")
    print("   GET  /api/admin/analytics/*")
    print("="*60 + "\n")
    
    app.run(debug=True, port=5000, host='0.0.0.0')