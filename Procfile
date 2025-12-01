# Procfile for Heroku/Render deployment
# Specifies how to run the application in production

# Web process: Use gunicorn WSGI server
# Configuration:
#   - app:app = module:application (app.py contains Flask app named 'app')
#   - --workers 1 = Single worker process (RAM optimization for 512MB)
#   - --threads 4 = 4 threads per worker (handles concurrent requests)
#   - --timeout 120 = 2 minute timeout for slow API calls
#   - --bind 0.0.0.0:$PORT = Listen on all interfaces, use dynamic port
#   - --access-logfile - = Log requests to stdout
#   - --error-logfile - = Log errors to stdout
#   - --log-level info = Detailed logging

web: gunicorn app:app --workers 1 --threads 4 --timeout 120 --bind 0.0.0.0:$PORT --access-logfile - --error-logfile - --log-level info
