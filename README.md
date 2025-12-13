# CoChain.ai - Complete Collaboration & Recommendation Platform

A comprehensive platform that combines AI-powered GitHub project recommendations with live student collaboration features. Students discover inspiring GitHub projects, create their own projects, find collaborators with matching skills, and receive intelligent recommendations powered by reinforcement learning.

### Developers
Benison: https://benisonjac.github.io/
Anthony: https://anthonyrajukondaveeti.github.io/
## 🌟 Key Features

### 🎯 GitHub Project Discovery
- **RL-Enhanced Recommendations**: Thompson Sampling algorithm with embeddings for personalized project suggestions
- **A/B Testing Framework**: Compare RL vs baseline recommendations with statistical significance testing
- **Semantic Search**: SentenceTransformer embeddings for intelligent project matching
- **Bookmarking & Notes**: Save favorite projects with personal annotations

### 🤝 Live Collaboration
- **Project Creation**: Students create and manage their own development projects
- **Smart Matching**: Algorithm matches projects with interested collaborators based on skills and interests
- **Join Requests**: Structured workflow for requesting to join and managing team members
- **Real-time Notifications**: Push notifications for join requests, acceptances, and project matches
- **User Portfolios**: Public profiles showing created and joined projects

### 🔐 Security & Performance
- **Rate Limiting**: Flask-Limiter protection on authentication and API endpoints
- **Session Management**: 24-hour session expiry with automatic timeout
- **Admin Access Control**: Environment-based admin email configuration
- **Pagination & Optimization**: Query limits and batch processing for performance
- **Row Level Security**: Supabase RLS policies for data protection

### 📊 Analytics & Admin Tools
- **Comprehensive Dashboard**: Track user engagement, recommendations, and collaboration metrics
- **A/B Test Management**: Start/stop tests, view results, and analyze performance
- **RL Performance Monitoring**: Track Thompson Sampling metrics and model training
- **User Management**: Admin panel for user oversight and analytics
- **Event Tracking**: Detailed logging of user interactions and system performance

## 🛠 Tech Stack

- **Backend**: Flask (Python 3.12+)
- **Database**: Supabase (PostgreSQL with pgvector extension + Row Level Security)
- **ML Models**: 
  - SentenceTransformer (all-MiniLM-L6-v2) for embeddings
  - Thompson Sampling for reinforcement learning
- **Security**: Flask-Limiter, session management, environment-based configuration
- **Frontend**: Jinja2 templates, vanilla JavaScript, responsive CSS
- **Analytics**: Custom event tracking and performance monitoring
- **Push Notifications**: Web Push API for real-time updates

## 📋 Prerequisites

- Python 3.12 or higher
- Supabase account and project with pgvector extension enabled
- GitHub account (for OAuth and data scraping)
- Hugging Face API key (for embeddings)

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/Benisonjac/CoChain.ai.git
cd CoChain.ai
```

### 2. Create Virtual Environment

```bash
python -m venv env

# Windows
env\Scripts\activate

# macOS/Linux
source env/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Environment Configuration

Create a `.env` file in the root directory (use `.env.example` as template):

```env
# Database Configuration
SUPABASE_URL=your-supabase-project-url
SUPABASE_KEY=your-supabase-anon-key
SUPABASE_SERVICE_KEY=your-supabase-service-role-key

# Security
SECRET_KEY=your-secret-key-here

# Admin Configuration (comma-separated emails)
ADMIN_EMAILS=admin@cochain.ai,your-email@example.com

# Optional: API Keys
GITHUB_TOKEN=your-github-token
HUGGINGFACE_API_KEY=your-huggingface-api-key
```

### 5. Database Setup

Run the following SQL files in your Supabase SQL Editor (in order):

1. **`database/platform_schema.sql`** - Core tables (users, projects, profiles)
2. **`database/add_rl_tables.sql`** - RL recommendation tables
3. **`database/ab_testing_schema.sql`** - A/B testing infrastructure
4. **`database/rl_prerequisites.sql`** - RL model setup
5. **`database/fix_rls_policies.sql`** - Row Level Security policies

### 6. Load Initial Data

```bash
# Load GitHub project data
python database/load_data.py
```

This will:
- Load GitHub projects from `data/github_scraped.csv`
- Generate embeddings using SentenceTransformer
- Initialize the database with sample data

### 7. Run the Application

```bash
python app.py
```

The application will be available at `http://localhost:5000`

**Default credentials**: Register a new account, then add your email to the `ADMIN_EMAILS` environment variable for admin access.

## 🧭 User Guide

### For Students

#### 1. **Registration & Profile Setup**
- Register with email and password
- Complete profile with education, skills, and interests
- Profile determines personalized recommendations

#### 2. **GitHub Project Discovery (Dashboard)**
- View personalized GitHub project recommendations
- Projects ranked by relevance to your profile
- Click to view details, bookmark favorites, add notes
- A/B testing automatically assigns you to Control or RL group

#### 3. **Live Collaboration Projects**
- Browse projects created by other students
- View project details, tech stack, and team requirements
- Send join requests with a personal message
- Track request status in notifications

#### 4. **Create Your Own Project**
- Post your project idea seeking collaborators
- Specify required skills, tech stack, complexity level
- Review and manage join requests
- Accept/reject collaborators for your team

#### 5. **Notifications**
- Receive join requests for your projects
- Get notified when your join requests are accepted/rejected
- See project match suggestions based on your interests

### For Admins

#### 1. **Admin Analytics Dashboard** (`/admin/analytics`)
- View platform-wide metrics (users, projects, engagement)
- Track GitHub recommendation performance
- Monitor collaboration project activity
- Export data for analysis

#### 2. **A/B Testing Management** (`/admin/ab-testing`)
- Start new A/B tests (Control vs RL recommendations)
- Monitor test progress and user assignments
- View statistical significance results
- Stop tests and declare winners

#### 3. **RL Performance** (`/admin/rl-performance`)
- Monitor Thompson Sampling algorithm metrics
- View exploration vs exploitation rates
- Trigger manual model training
- Track recommendation quality over time

#### 4. **User Management** (`/admin/users`)
- View all registered users
- Check profile completion rates
- Monitor user engagement metrics
- Manage admin access

## 📚 API Documentation

### Authentication Endpoints

#### Register
```http
POST /register
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "secure_password",
  "full_name": "John Doe"
}
```

**Rate Limit**: 5 requests per hour

#### Login
```http
POST /login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "secure_password"
}
```

**Rate Limit**: 10 requests per hour
**Session**: 24-hour expiry with automatic timeout

### Recommendation Endpoints

#### Get Recommendations (Dashboard)
```http
GET /dashboard
Headers: Cookie: session=<session_cookie>
```

Returns personalized recommendations based on:
- User profile (skills, interests, learning goals)
- A/B test assignment (RL or baseline)
- Historical interactions

#### Load More Recommendations
```http
POST /api/recommendations/load-more
Content-Type: application/json

{
  "offset": 12,
  "limit": 6
}
```

### Interaction Tracking

#### Track Recommendation Click
```http
POST /api/recommendation/click
Content-Type: application/json

{
  "github_id": "uuid",
  "rank_position": 1,
  "session_id": "session_uuid"
}
```

**Rate Limit**: 100 requests per hour

#### Bookmark Project
```http
POST /api/bookmark
Content-Type: application/json

{
  "github_reference_id": "uuid",
  "notes": "Interesting React patterns"
}
```

**Rate Limit**: 50 requests per hour

### Collaboration Endpoints

#### Get Live Projects
```http
GET /live-projects
```

Returns projects matching user's interests and skills.

#### Send Join Request
```http
POST /request-join/<project_id>
Content-Type: application/x-www-form-urlencoded

message=I'm interested in joining your project...
```

#### Respond to Join Request
```http
GET /respond-join-request/<request_id>/<action>
```

Actions: `accept` or `reject`

### Admin Endpoints (Require Admin Email)

#### Analytics Summary
```http
GET /api/admin/analytics/summary
```

Returns:
- Total users, projects, interactions
- Engagement metrics
- Recommendation performance

#### Start A/B Test
```http
POST /api/admin/ab-testing/start
Content-Type: application/json

{
  "test_name": "RL vs Baseline - Week 50",
  "description": "Testing new Thompson Sampling parameters",
  "control_variant": "baseline",
  "treatment_variant": "rl_thompson",
  "traffic_split": 50
}
```

#### Trigger RL Training
```http
POST /api/admin/rl/trigger-training
Content-Type: application/json

{
  "days": 7
}
```

## 🏗 Project Structure

```
CoChain.ai/
├── app.py                          # Main Flask application (4000+ lines)
├── config.py                       # Configuration constants
├── app_config.py                   # Legacy config (deprecated)
├── requirements.txt                # Python dependencies (73 packages)
├── .env                           # Environment variables (gitignored)
├── .env.example                   # Environment template
├── Procfile                       # Deployment configuration
├── runtime.txt                    # Python version for deployment
│
├── data/                          # Dataset files
│   ├── github_scraped.csv         # 2500+ GitHub projects
│   └── student_ideas_transformed.csv
│
├── database/                      # Database schemas and utilities
│   ├── connection.py              # Supabase client setup
│   ├── platform_schema.sql        # Core tables
│   ├── ab_testing_schema.sql      # A/B testing tables
│   ├── add_rl_tables.sql          # RL model tables
│   ├── rl_prerequisites.sql       # RL setup
│   ├── fix_rls_policies.sql       # Security policies
│   └── load_data.py              # Data loading utilities
│
├── services/                     # Business logic layer
│   ├── auth_service.py            # Authentication
│   ├── user_service.py            # User management
│   ├── collaboration_service.py   # Project collaboration
│   ├── rl_recommendation_engine.py # RL-powered recommendations
│   ├── enhanced_recommendation_engine.py # Base recommender
│   ├── ab_test_service.py         # A/B testing logic
│   ├── analytics_service.py       # Analytics tracking
│   ├── admin_analytics_service.py # Admin dashboards
│   ├── event_tracker.py           # Event logging
│   ├── performance_monitor.py     # Performance metrics
│   ├── logging_service.py         # Structured logging
│   ├── embeddings.py              # Embedding generation
│   └── background_tasks.py        # Scheduled jobs
│
├── api/                          # API blueprints
│   └── collaboration_routes.py    # Collaboration API endpoints
│
├── templates/                    # HTML templates (Jinja2)
│   ├── index.html                # Landing page
│   ├── register.html             # Registration
│   ├── login.html                # Login
│   ├── dashboard.html            # GitHub recommendations
│   ├── profile_setup.html        # Profile management
│   ├── live_projects.html        # Collaboration projects
│   ├── project_detail.html       # Project details
│   ├── my_projects.html          # User's projects
│   ├── create_project.html       # Project creation
│   ├── notifications.html        # User notifications
│   ├── admin_analytics.html      # Admin dashboard
│   └── ...
│
├── static/                       # Static assets
│   ├── css/
│   │   └── styles.css            # Main stylesheet
│   ├── js/
│   │   ├── main.js               # Core JavaScript
│   │   ├── event_tracking.js     # Analytics tracking
│   │   └── push-notifications.js # Push notification handler
│   └── manifest.json             # PWA manifest
│
├── logs/                         # Application logs (gitignored)
│   ├── app/                      # General logs
│   ├── analytics/                # Analytics logs
│   ├── errors/                   # Error logs
│   └── performance/              # Performance logs
│
└── docs/                         # Documentation
    ├── README.md                 # This file
    ├── AB_TESTING_EXPLAINED.md   # A/B testing guide (1500+ lines)
    ├── PROFILE_REDIRECT_FIX.md   # Technical fix documentation
    └── ...
```

## 🧠 How It Works

### Recommendation System Architecture

#### 1. **Dual Recommendation Engines**

**Baseline Recommender (Control Group)**:
- Uses SentenceTransformer embeddings (384 dimensions)
- Cosine similarity matching between user profile and projects
- Simple, interpretable, and fast
- No learning from user interactions

**RL Recommender (Treatment Group)**:
- Thompson Sampling algorithm for exploration vs exploitation
- Maintains Beta distributions for each project (α, β parameters)
- Learns from user interactions (clicks, bookmarks, time spent)
- Balances showing proven projects vs discovering new ones
- Combines similarity scores with RL scores for final ranking

#### 2. **A/B Testing Framework**

```
New User Registers
        ↓
Profile Completed
        ↓
A/B Test Assignment (50/50 split)
        ↓
    ┌───────┴───────┐
    ↓               ↓
Control Group   Treatment Group
(Baseline)      (RL Thompson)
    ↓               ↓
Similarity Only  RL + Similarity
    ↓               ↓
Track Metrics   Track Metrics
    ↓               ↓
    └───────┬───────┘
            ↓
Statistical Analysis
(Chi-square, T-test)
            ↓
Declare Winner
```

**Metrics Tracked**:
- Click-through rate (CTR)
- Bookmark rate
- Average time spent on projects
- Return visit rate
- User satisfaction scores

#### 3. **Thompson Sampling Algorithm**

For each project, maintain:
- **α (alpha)**: Successes (clicks, bookmarks, positive interactions)
- **β (beta)**: Failures (ignores, quick exits, negative interactions)

**Recommendation Process**:
1. Sample from Beta(α, β) for each project
2. Combine sampled score with similarity score
3. Rank projects by combined score
4. Update α and β based on user interactions

**Benefits**:
- Automatically balances exploration (new projects) vs exploitation (proven projects)
- Adapts to user behavior over time
- Handles cold start problem gracefully

#### 4. **Embedding Generation & Matching**

**User Profile Embedding**:
```python
profile_text = f"""
Education: {education_level} {field_of_study}
Skills: {", ".join(programming_languages)}
Interests: {", ".join(areas_of_interest)}
Bio: {bio}
Goals: {learning_goals}
"""
user_embedding = model.encode(profile_text)  # 384-dim vector
```

**Project Embedding**:
```python
project_text = f"""
Title: {title}
Description: {description}
Domain: {domain}
Skills: {", ".join(required_skills)}
Complexity: {complexity_level}
"""
project_embedding = model.encode(project_text)  # 384-dim vector
```

**Similarity Calculation**:
```python
similarity = cosine_similarity(user_embedding, project_embedding)
# Range: -1 to 1, typically 0.3 to 0.9 for relevant matches
```

#### 5. **Collaboration Matching Algorithm**

**Project-to-User Matching**:
1. Extract keywords from project's required skills and domain
2. Extract keywords from user's interests and programming languages
3. Find intersection of keywords (case-insensitive, normalized)
4. Match if intersection is non-empty
5. Send notification to matched users

**Smart Features**:
- Keyword normalization (e.g., "web_development" → "web", "development")
- Excludes project creator from matches
- Limits to 500 user profiles per batch for performance
- Batch processing (50 notifications at a time) with error handling

## 🔧 Configuration

### Rate Limiting

Configured via Flask-Limiter in `app.py`:

```python
# Global limits
default_limits = ["200 per day", "50 per hour"]

# Endpoint-specific limits
/register: 5 per hour
/login: 10 per hour
/api/recommendation/click: 100 per hour
/api/bookmark: 50 per hour
```

### Session Management

```python
SESSION_LIFETIME = 24 hours
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
```

Sessions expire after 24 hours of inactivity. Users are automatically logged out and redirected to login with a warning message.

### Admin Configuration

Set admin emails in `.env`:
```env
ADMIN_EMAILS=admin@cochain.ai,your-email@example.com,another-admin@example.com
```

Admins have access to:
- `/admin/analytics` - Platform analytics
- `/admin/users` - User management
- `/admin/ab-testing` - A/B test management
- `/admin/rl-performance` - RL model monitoring
- `/api/admin/*` - Admin API endpoints

### Complexity Levels

- **Beginner** (`1`): Simple projects, minimal dependencies, clear documentation
- **Intermediate** (`2`): Multiple features, moderate complexity, some prior experience needed
- **Advanced** (`3`): Complex architecture, advanced concepts, significant experience required

### Pagination & Limits

```python
# Analytics endpoints
MAX_LIMIT = 100  # Maximum records per query
MAX_DAYS = 90    # Maximum date range for queries

# RL metrics
RL_QUERY_LIMIT = 5000  # Project analysis limit

# Notification matching
MAX_PROFILES = 500     # User profiles per batch
NOTIFICATION_BATCH = 50  # Notifications per insert
```

## 🔐 Security Features

### Authentication & Authorization
- **Password Hashing**: Supabase Auth handles bcrypt hashing
- **Session Tokens**: Secure, HTTP-only cookies
- **JWT Tokens**: For API authentication (stored in session)
- **Admin Middleware**: Email-based admin verification
- **Login Protection**: Failed login tracking and account lockout

### Rate Limiting
- **Flask-Limiter**: Memory-based rate limiting
- **IP-based Tracking**: Limits per remote address
- **Endpoint Protection**: Different limits for different endpoints
- **Automatic 429 Responses**: Clear error messages when limit exceeded

### Database Security
- **Row Level Security (RLS)**: Supabase policies enforce data access
- **Admin Client**: Separate client with elevated privileges for admin operations
- **SQL Injection Prevention**: Parameterized queries via Supabase client
- **Environment Variables**: Sensitive credentials never hardcoded

### Session Security
- **24-hour Expiry**: Automatic timeout for inactive sessions
- **CSRF Protection**: SameSite cookie attribute
- **HTTPOnly Cookies**: Prevents XSS attacks
- **Timezone Handling**: UTC timestamps to prevent timezone exploits

## 📊 Analytics & Monitoring

### Event Tracking

All user interactions are logged:
- Page views
- Recommendation impressions
- Clicks on projects
- Bookmarks created
- Project views
- Collaboration requests
- Session start/end

**Storage**: Supabase tables with structured JSON
**Access**: Admin analytics dashboard and API endpoints

### Performance Monitoring

Tracked metrics:
- API response times (per endpoint)
- Database query duration
- Recommendation generation time
- Cache hit rates
- Error rates by endpoint

**Logging**: File-based logs in `logs/` directory
**Levels**: INFO, WARNING, ERROR, DEBUG
**Rotation**: Daily rotation with 30-day retention

### A/B Testing Analytics

**Statistical Tests**:
- **Chi-square test**: For categorical outcomes (CTR, bookmark rate)
- **T-test**: For continuous metrics (time spent, engagement score)
- **Confidence Level**: 95% (p-value < 0.05 for significance)

**Stopping Criteria**:
- Minimum 100 users per group
- Minimum 7 days of data collection
- Statistical significance achieved (p < 0.05)
- Or manual stop by admin

## 🚀 Deployment

### Local Development

```bash
# Activate virtual environment
env\Scripts\activate  # Windows
source env/bin/activate  # macOS/Linux

# Set Flask environment
export FLASK_ENV=development  # macOS/Linux
$env:FLASK_ENV="development"  # Windows PowerShell

# Run with debug mode
python app.py
```

Application runs on `http://localhost:5000` with auto-reload enabled.

### Production Deployment (Render/Heroku)

#### 1. **Prepare Files**

Ensure these files are present:
- `requirements.txt` - All dependencies
- `Procfile` - `web: gunicorn app:app`
- `runtime.txt` - Python version (e.g., `python-3.12.0`)
- `.env.example` - Template for environment variables

#### 2. **Environment Variables**

Set in hosting platform:
```env
SUPABASE_URL=your-production-url
SUPABASE_KEY=your-production-anon-key
SUPABASE_SERVICE_KEY=your-production-service-key
SECRET_KEY=generate-strong-random-key
ADMIN_EMAILS=admin@yourdomain.com
FLASK_ENV=production
DEBUG=False
```

#### 3. **Database Migration**

Run all SQL files in production Supabase in order (see Quick Start section).

#### 4. **Deploy**

**Render**:
```bash
# Connect GitHub repo to Render
# Set environment variables in dashboard
# Deploy automatically on push to main
```

**Heroku**:
```bash
heroku create your-app-name
heroku config:set SUPABASE_URL=...
heroku config:set SUPABASE_KEY=...
# ... set all environment variables
git push heroku main
```

#### 5. **Post-Deployment**

- Test authentication (register, login, logout)
- Verify recommendations load
- Check admin access
- Monitor logs for errors
- Set up uptime monitoring

### Production Checklist

- [ ] All environment variables configured
- [ ] Database migrations completed
- [ ] Admin emails configured
- [ ] Rate limiting enabled
- [ ] Session timeout configured (24 hours)
- [ ] Logs directory created with proper permissions
- [ ] Error monitoring configured (Sentry, etc.)
- [ ] Backup strategy for database
- [ ] SSL/HTTPS enabled
- [ ] Domain configured with proper DNS

## 🧪 Testing

### Manual Testing Checklist

**Authentication**:
- [ ] Register new user
- [ ] Login with correct credentials
- [ ] Login with incorrect credentials (should fail)
- [ ] Session expires after 24 hours
- [ ] Logout successfully

**Recommendations**:
- [ ] Dashboard loads recommendations
- [ ] Load more recommendations works
- [ ] Click tracking records properly
- [ ] Bookmark functionality works
- [ ] A/B test assigns users correctly

**Collaboration**:
- [ ] Create new project
- [ ] Browse live projects
- [ ] Send join request
- [ ] Receive notifications
- [ ] Accept/reject requests
- [ ] View user portfolios

**Admin**:
- [ ] Admin dashboard accessible
- [ ] Start A/B test
- [ ] View test results
- [ ] Trigger RL training
- [ ] User management works

**Rate Limiting**:
- [ ] Register endpoint limited (5/hour)
- [ ] Login endpoint limited (10/hour)
- [ ] 429 errors when limit exceeded

### Load Testing

```bash
# Using Apache Bench
ab -n 1000 -c 10 http://localhost:5000/

# Using wrk
wrk -t12 -c400 -d30s http://localhost:5000/dashboard
```

Target performance:
- Dashboard load: < 2 seconds
- Recommendation generation: < 1.5 seconds
- API endpoints: < 500ms
- Database queries: < 200ms

## 🤝 Contributing

We welcome contributions to CoChain.ai! Here's how you can help:

### Development Setup

1. Fork the repository on GitHub
2. Clone your fork locally
3. Create a feature branch: `git checkout -b feature/your-feature-name`
4. Set up development environment (see Quick Start)
5. Make your changes with proper testing
6. Commit with clear messages: `git commit -m 'feat: Add new feature'`
7. Push to your fork: `git push origin feature/your-feature-name`
8. Open a Pull Request with detailed description

### Contribution Guidelines

- **Code Style**: Follow PEP 8 for Python code
- **Documentation**: Update README.md and inline comments
- **Testing**: Add tests for new features
- **Commits**: Use conventional commit messages (feat:, fix:, docs:, etc.)
- **Security**: Never commit sensitive data (.env, credentials)

### Areas for Contribution

- 🐛 **Bug Fixes**: Check GitHub issues for reported bugs
- ✨ **Features**: Implement requested features from issues
- 📝 **Documentation**: Improve guides and API docs
- 🧪 **Testing**: Add unit tests and integration tests
- 🎨 **UI/UX**: Enhance frontend design and user experience
- 🚀 **Performance**: Optimize queries and algorithms
- 🔐 **Security**: Identify and fix security vulnerabilities

## 🐛 Troubleshooting

### Common Issues

#### "ModuleNotFoundError: No module named 'flask_limiter'"
```bash
# Ensure virtual environment is activated
env\Scripts\activate  # Windows
source env/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt
```

#### "Session expired" after short time
Check that `session_created_at` is being set correctly in login/register routes. Should use UTC timezone:
```python
from datetime import datetime, timezone
session['session_created_at'] = datetime.now(timezone.utc).isoformat()
```

#### "Admin access required" but email is in ADMIN_EMAILS
- Verify `.env` file has correct format: `ADMIN_EMAILS=email1@example.com,email2@example.com`
- No spaces after commas
- Restart Flask application after .env changes
- Check session has user_email set correctly

#### Recommendations not loading
- Verify Supabase connection in `.env`
- Check `github_references` table has data: `SELECT COUNT(*) FROM github_references;`
- Ensure embeddings are loaded: `SELECT COUNT(*) FROM embeddings WHERE embedding_vector IS NOT NULL;`
- Check application logs in `logs/app/` directory

#### Database connection errors
- Verify Supabase credentials in `.env`
- Check Supabase project is active (not paused)
- Ensure pgvector extension is enabled in Supabase
- Test connection: `python -c "from database.connection import supabase; print(supabase.table('users').select('count').execute())"`

#### Rate limiting too strict during development
Temporarily increase limits in `app.py`:
```python
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["2000 per day", "500 per hour"],  # Increased for dev
    storage_uri="memory://"
)
```

#### A/B test not assigning users
- Check `ab_tests` table has active test: `SELECT * FROM ab_tests WHERE status='active';`
- Verify test has available capacity: `traffic_split` should be 50 for 50/50 split
- Ensure user doesn't already have assignment in `ab_test_assignments` table

### Error Logs Location

```
logs/
├── app/           # General application logs
├── analytics/     # Analytics and tracking logs
├── errors/        # Error traces and stack dumps
└── performance/   # Performance metrics and slow queries
```

### Getting Help

1. **Check Documentation**: Review this README and specialized docs in `docs/`
2. **Search Issues**: Look for similar problems in GitHub issues
3. **Check Logs**: Review error logs for detailed stack traces
4. **Ask Questions**: Open a GitHub issue with:
   - Clear problem description
   - Steps to reproduce
   - Error messages and logs
   - Environment details (OS, Python version)

## 📖 Additional Documentation

- **[AB_TESTING_EXPLAINED.md](AB_TESTING_EXPLAINED.md)** - Comprehensive guide to A/B testing system (1500+ lines)
  - Statistical methods
  - Thompson Sampling algorithm
  - Admin workflow
  - How to interpret results

- **[PROFILE_REDIRECT_FIX.md](PROFILE_REDIRECT_FIX.md)** - Technical documentation for profile completion bug fix
  - Problem diagnosis
  - Solution implementation
  - Migration steps

## 🔮 Roadmap & Future Enhancements

### Short-term (Next 3 months)
- [ ] **Multi-language Support**: Extend beyond Python projects (Java, JavaScript, Go)
- [ ] **Advanced Filtering**: Filter recommendations by stars, recency, contributors
- [ ] **Project Search**: Full-text search for GitHub and collaboration projects
- [ ] **Email Notifications**: Send email alerts for join requests and matches
- [ ] **Mobile Responsiveness**: Optimize UI for mobile devices

### Medium-term (3-6 months)
- [ ] **GitHub Integration**: OAuth login and automatic skill detection from repos
- [ ] **Real-time Chat**: In-platform messaging for project collaborators
- [ ] **Project Templates**: Pre-filled templates for common project types
- [ ] **Skill Assessment**: Quiz-based skill verification
- [ ] **Recommendation Explanations**: "Why we recommended this project"

### Long-term (6-12 months)
- [ ] **Machine Learning Pipeline**: Automated model retraining based on feedback
- [ ] **Multi-modal Recommendations**: Consider code snippets, images, videos
- [ ] **Collaborative Filtering**: User-user similarity for recommendations
- [ ] **Project Success Metrics**: Track which collaborations succeed
- [ ] **API for External Apps**: Public API for third-party integrations

## 📄 License

This project is licensed under the MIT License. See the LICENSE file for details.

**MIT License Summary**:
- ✅ Commercial use allowed
- ✅ Modification allowed
- ✅ Distribution allowed
- ✅ Private use allowed
- ℹ️ License and copyright notice must be included

## 👥 Team & Contact

**Project**: CoChain.ai  
**Repository**: [github.com/Benisonjac/CoChain.ai](https://github.com/Benisonjac/CoChain.ai)  
**Maintainer**: Benison Jacob  

**Contact**:
- GitHub Issues: For bugs and feature requests
- Email: admin@cochain.ai (for security issues and partnerships)

## 🙏 Acknowledgments

- **SentenceTransformers**: For the excellent embedding models
- **Supabase**: For the robust backend infrastructure
- **Flask Community**: For the comprehensive web framework
- **Open Source Community**: For inspiration and contributions

## 📊 Project Stats

- **Total Lines of Code**: ~15,000+
- **Python Files**: 30+
- **Templates**: 20+ HTML files
- **Database Tables**: 25+ tables
- **API Endpoints**: 40+ routes
- **GitHub Projects**: 2,500+ in database
- **Active Development**: Since 2024

---

**Built with ❤️ by CoChain.ai team. Happy coding! 🚀**

*Last Updated: December 13, 2025*
