from flask import Flask, send_from_directory, send_file
from flask_cors import CORS
from routes.api import api_blueprint
import os

app = Flask(__name__, static_folder='static', static_url_path='')
CORS(app)
app.register_blueprint(api_blueprint)

@app.route('/')
def home():
    return send_file('static/index.html')

@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

if __name__ == "__main__":
    app.run(debug=True)