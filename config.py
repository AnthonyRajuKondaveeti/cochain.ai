"""
Configuration constants for CoChain.ai application
"""
import os

# Session Configuration
SESSION_LIFETIME_HOURS = int(os.getenv('SESSION_LIFETIME_HOURS', '24'))
SESSION_COOKIE_SECURE = os.getenv('FLASK_ENV') == 'production'
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'

# Rate Limiting
RATE_LIMIT_REGISTER = "5 per hour"
RATE_LIMIT_LOGIN = "10 per hour"
RATE_LIMIT_API_CLICK = "100 per hour"
RATE_LIMIT_API_BOOKMARK = "50 per hour"
RATE_LIMIT_DEFAULT = ["200 per day", "50 per hour"]

# Pagination
MAX_ITEMS_PER_PAGE = 100
DEFAULT_PAGE_SIZE = 50

# Notification Matching
MAX_PROFILES_TO_CHECK = 500
NOTIFICATION_BATCH_SIZE = 50

# Recommendation System
MAX_RECOMMENDATIONS_PER_REQUEST = 15
RECOMMENDATION_CACHE_TTL = 3600  # seconds

# Database Query Limits
MAX_QUERY_DAYS = 90
MAX_INTERACTION_QUERY_LIMIT = 5000

# Admin Configuration
ADMIN_EMAILS = os.getenv('ADMIN_EMAILS', '').split(',')
ADMIN_EMAILS = [email.strip() for email in ADMIN_EMAILS if email.strip()]

# Security
SECRET_KEY = os.getenv('SECRET_KEY')
if not SECRET_KEY and os.getenv('FLASK_ENV') == 'production':
    raise ValueError("SECRET_KEY environment variable is required in production")

# Logging
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

# Feature Flags
USE_RL_RECOMMENDATIONS = True
ENABLE_AUTO_TRAINING = False
