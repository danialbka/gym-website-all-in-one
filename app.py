from flask import Flask, send_from_directory, send_file
from flask_cors import CORS
from flask_mail import Mail
from flask_jwt_extended import JWTManager
from routes.api import api_blueprint
import os
from dotenv import load_dotenv

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
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = os.getenv('JWT_ACCESS_TOKEN_EXPIRES', 86400)  # 24 hours

# Initialize extensions
mail = Mail(app)
jwt = JWTManager(app)

CORS(app)
app.register_blueprint(api_blueprint)

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