from flask import Flask, send_from_directory, send_file, request
from flask_cors import CORS
from flask_mail import Mail
from flask_jwt_extended import JWTManager
from routes.api import api_blueprint
import os
from dotenv import load_dotenv
from datetime import timedelta

load_dotenv()

app = Flask(__name__, static_folder='static', static_url_path='')

# Configure Flask-Mail
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True').lower() == 'true'
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER')

# Configure JWT
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'your-secret-key-change-in-production')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(seconds=int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES', 86400)))  # 24 hours

# Initialize extensions
mail = Mail(app)
jwt = JWTManager(app)

CORS(app)
app.register_blueprint(api_blueprint)

# Add cache headers for static assets (McMaster-Carr style caching)
@app.after_request
def add_cache_headers(response):
    # Static assets get long cache times
    if request.endpoint == 'serve_static':
        # Critical files get no cache to avoid styling issues
        if 'critical-css.js' in request.path or request.path.endswith('index.html'):
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
        elif any(request.path.endswith(ext) for ext in ['.css', '.js', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', '.woff', '.woff2', '.ttf']):
            # 1 year cache for static assets
            response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
            response.headers['Expires'] = 'Thu, 31 Dec 2025 23:59:59 GMT'
        elif request.path.endswith('.html'):
            # 5 minutes cache for HTML pages
            response.headers['Cache-Control'] = 'public, max-age=300'
    
    # API responses get shorter cache times
    elif request.endpoint and 'api' in request.endpoint:
        if 'leaderboard' in request.path:
            response.headers['Cache-Control'] = 'public, max-age=300'  # 5 minutes
        elif 'videos' in request.path:
            response.headers['Cache-Control'] = 'public, max-age=60'   # 1 minute
        else:
            response.headers['Cache-Control'] = 'no-cache'
    
    # Add security headers
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    
    return response

# Initialize database indexes on startup
def initialize_database():
    try:
        from routes.api import create_performance_indexes
        create_performance_indexes()
    except Exception as e:
        print(f"Warning: Could not create database indexes on startup: {e}")

# Call initialization
with app.app_context():
    initialize_database()

@app.route('/')
def home():
    return send_file('static/index.html')

@app.route('/health')
def health_check():
    return {'status': 'healthy', 'version': '1.0.0'}, 200

@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

if __name__ == "__main__":
    app.run(debug=True)