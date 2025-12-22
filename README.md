# CoChain.ai - Complete Collaboration & Recommendation Platform

A comprehensive platform that combines AI-powered GitHub project recommendations with live student collaboration features. Students discover inspiring GitHub projects, create their own projects, find collaborators with matching skills, and receive intelligent recommendations powered by reinforcement learning.

### Developers
Benison: https://benisonjac.github.io/
Anthony: https://anthonyrajukondaveeti.github.io/

## 📑 Table of Contents
- [Key Features](#-key-features)
- [Tech Stack](#-tech-stack)
- [Quick Start](#-quick-start)
- [User Guide](#-user-guide)
- [Project Structure](#-project-structure)
- [Configuration](#-configuration)
- [Security](#-security-features)
- [Deployment](#-deployment)
- [Additional Documentation](#-additional-documentation)
- [Troubleshooting](#-troubleshooting)

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
5. **`database/fix_rls_security_issues.sql`** - Row Level Security policies

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

1. **Registration & Profile Setup** - Complete your profile with skills and interests for personalized recommendations
2. **Discover Projects** - Browse AI-recommended GitHub projects on your dashboard
3. **Bookmark & Explore** - Save favorites, add notes, and explore project details
4. **Join Collaborations** - Browse live student projects and send join requests
5. **Create Projects** - Post your own project and recruit collaborators
6. **Manage Notifications** - Track join requests and acceptances in real-time

### For Admins

- **`/admin/analytics`** - Platform metrics, user engagement, and performance tracking
- **`/admin/ab-testing`** - Start/stop A/B tests and view statistical results
- **`/admin/rl-performance`** - Monitor RL algorithm metrics and trigger training
- **`/admin/users`** - User management and profile analytics

## 📚 API Endpoints

### Core Routes
- `POST /register` - User registration (rate: 5/hour)
- `POST /login` - Authentication (rate: 10/hour, 24hr session)
- `GET /dashboard` - Personalized recommendations
- `POST /api/recommendation/click` - Track interactions (rate: 100/hour)
- `POST /api/bookmark` - Bookmark projects (rate: 50/hour)
- `GET /live-projects` - Browse collaboration projects
- `POST /request-join/<project_id>` - Send join request

### Admin Routes (Admin email required)
- `GET /admin/analytics` - Platform dashboard
- `POST /api/admin/ab-testing/start` - Start A/B test
- `POST /api/admin/rl/trigger-training` - Trigger RL training
- `GET /api/admin/analytics/summary` - Metrics API

For detailed API documentation with request/response examples, see the source code in [app.py](app.py).

## 🏗 Project Structure

```
CoChain.ai/
├── app.py                          # Main Flask application (4000+ lines)
├── config.py                       # Configuration constants
├── app_config.py                   # Environment configuration
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
    ├── fix_rls_security_issues.sql # Security policies
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
├── AB_TESTING_EXPLAINED.md       # A/B testing guide (1500+ lines)
└── RL_TRAINING_REPORT.md         # RL training documentation
```

## 🧠 How It Works

### Recommendation System

**Baseline Recommender**: Uses SentenceTransformer embeddings (384-dim) with cosine similarity matching

**RL Recommender**: Thompson Sampling algorithm maintaining Beta distributions (α, β) for each project, learning from user interactions

**A/B Testing**: 50/50 split between Control (baseline) and Treatment (RL) groups, tracking CTR, bookmarks, and engagement

### Key Algorithms

- **Embeddings**: User profiles and projects encoded as 384-dim vectors for semantic matching
- **Thompson Sampling**: Balances exploration (new projects) vs exploitation (proven projects)
- **Collaboration Matching**: Keyword-based matching between project requirements and user skills

**For detailed technical documentation**:
- See [RL_TRAINING_REPORT.md](RL_TRAINING_REPORT.md) for RL implementation details
- See [AB_TESTING_EXPLAINED.md](AB_TESTING_EXPLAINED.md) for A/B testing methodology

## 🔧 Configuration

### Key Settings

**Rate Limiting**: Configured via Flask-Limiter
- Auth endpoints: 5-10 requests/hour
- API endpoints: 50-100 requests/hour
- Global: 200/day, 50/hour

**Session Management**: 24-hour expiry, HTTP-only cookies, SameSite='Lax'

**Admin Access**: Set `ADMIN_EMAILS` in `.env` (comma-separated)

**Performance Limits**:
- Analytics queries: Max 100 records, 90-day range
- RL queries: 5000 projects
- Notification batches: 50 per insert

**Project Complexity**: Beginner (1), Intermediate (2), Advanced (3)

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
env\Scripts\activate  # Windows
python app.py  # Runs on http://localhost:5000
```

### Production (Render/Heroku)

**Required Files**: `requirements.txt`, `Procfile` (web: gunicorn app:app), `runtime.txt`

**Environment Variables**: Set SUPABASE_URL, SUPABASE_KEY, SUPABASE_SERVICE_KEY, SECRET_KEY, ADMIN_EMAILS, FLASK_ENV=production

**Database**: Run SQL files in order (platform_schema.sql → add_rl_tables.sql → ab_testing_schema.sql → rl_prerequisites.sql → fix_rls_security_issues.sql)

**Deploy**: Connect GitHub repo, configure env vars, deploy

**Post-Deployment Checklist**:
- ✓ Test auth and recommendations
- ✓ Verify admin access
- ✓ Enable rate limiting & monitoring
- ✓ Configure SSL/HTTPS

## 🧪 Testing

Test core features: Authentication (register/login/logout), Recommendations (dashboard/bookmarks/A/B testing), Collaboration (create/join projects), Admin (analytics/A/B tests/RL training), and Rate limiting.

Target performance: Dashboard < 2s, Recommendations < 1.5s, API < 500ms, DB queries < 200ms

## 🤝 Contributing

Fork → Clone → Create branch → Make changes → Commit → Push → Open PR

**Guidelines**: Follow PEP 8, update docs, add tests, use conventional commits (feat:/fix:/docs:), never commit sensitive data

**Areas**: Bug fixes, features, documentation, testing, UI/UX, performance, security

## 🐛 Troubleshooting

### Common Issues

**ModuleNotFoundError**: Activate virtual environment and run `pip install -r requirements.txt`

**Session expires quickly**: Ensure `session_created_at` uses UTC timezone

**Admin access denied**: Check `.env` format (no spaces), restart app after changes

**Recommendations not loading**: Verify Supabase connection, check if `github_references` table has data

**Database errors**: Verify credentials, ensure Supabase project is active, test connection

**Rate limiting**: Temporarily increase limits in `app.py` for development

**A/B test not working**: Check `ab_tests` table for active tests

### Logs
Check `logs/` directory: `app/` (general), `analytics/` (tracking), `errors/` (stack traces), `performance/` (metrics)

### Getting Help
Review documentation, check GitHub issues, or open a new issue with error details and environment info

## 📖 Additional Documentation

- **[AB_TESTING_EXPLAINED.md](AB_TESTING_EXPLAINED.md)** - Comprehensive guide to A/B testing system (1500+ lines)
  - Statistical methods
  - Thompson Sampling algorithm
  - Admin workflow
  - How to interpret results

- **[RL_TRAINING_REPORT.md](RL_TRAINING_REPORT.md)** - Technical documentation for RL training system
  - Model architecture
  - Thompson Sampling implementation
  - Training process and metrics

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

*Last Updated: December 22, 2025*
