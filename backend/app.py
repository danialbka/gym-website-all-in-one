from flask import Flask
from flask_cors import CORS
from routes.api import api_blueprint

app = Flask(__name__)
CORS(app)
app.register_blueprint(api_blueprint)

@app.route('/')
def home():
    return '''
    <html>
    <head>
        <title>GymRank API</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .endpoint { background: #f0f0f0; padding: 10px; margin: 10px 0; border-radius: 5px; }
        </style>
    </head>
    <body>
        <h1>🏋️ GymRank API</h1>
        <p>API is running successfully!</p>
        <h3>Available endpoints:</h3>
        <div class="endpoint">
            <strong>POST /api/register</strong><br>
            Register a new user with username and flag
        </div>
        <div class="endpoint">
            <strong>POST /api/submit_pr</strong><br>
            Submit a personal record (PR) for a lift
        </div>
        <div class="endpoint">
            <strong>GET /api/leaderboard</strong><br>
            Get the top 10 users ranked by ELO
        </div>
        <br>
        <a href="/api/leaderboard">View Leaderboard</a>
    </body>
    </html>
    '''

if __name__ == "__main__":
    app.run(debug=True)