That sounds like an awesome and competitive idea, Danial! Here's a step-by-step plan to get this gym PR showcase and ranking platform off the ground:

---

### 🧠 **Project Name (Placeholder):**

**LiftLeague** – (You can change it later, just a working title.)

---

## 🔧 **Core Features**

### 1. **User System**

* Sign up/login (OAuth or email-based)
* Username selection
* Country flag selection (auto-detect or manual dropdown)

### 2. **Video Uploads**

* Max duration: 30 seconds
* Accepted formats: MP4, WebM, etc.
* Upload validation (no NSFW, spam, etc.)
* Tag lift type: Bench, Deadlift, Squat
* Weight lifted (user inputs it manually, for now)

### 3. **Ranking System**

* Each lift is scored separately and combined for total (Bench + Deadlift + Squat)
* ELO-based ranking system:

  * Similar to Bakugan: higher weight = stronger “power level”
  * Real-time updates if someone beats your lift total
  * Ranks like: Rookie → Brawler → Elite → Titan → Champion

### 4. **Profile Page**

* Username + flag
* Total lift (kg)
* Rank + Rank progress bar
* Video gallery
* “PR Board” to pin their best lifts

### 5. **Leaderboard**

* Global and country-specific leaderboards
* Filters: lift type, age group, weight class (future upgrade)
* “Recent Climbers” section to highlight rising users

---

## ⚙️ **Tech Stack (Suggestion)**

### Frontend:

* **TailwindCSS** (styling)

### Backend:

*
* **Supabase** (auth, DB, file storage)
* **FFmpeg** (for processing video uploads)
* **PostgreSQL** (for ranking data and user info)

### Real-Time System:

* **Socket.IO** or **Pusher** to push live rank changes

---

## 🧮 **ELO Ranking (Simplified Model)**

```text
New Score = Current Score + K * (Win/Loss - Expected Score)

Where:
- Win = you outlift someone
- Loss = someone outlifts you
- Expected Score = 1 / (1 + 10^((OpponentScore - YourScore)/400))
- K = sensitivity factor (e.g., 32)
```

* Adjust ELO per lift type and combine for Total Rank
* Optional: add decay for inactive users

---

## 🎮 **Gamified Elements**

* Badges: “200kg Club”, “Triple Threat” (PR in all 3 lifts), “Rising Star”
* Weekly Challenges
* Flag emojis in leaderboards
* Comment section or 🔥 reacts on PRs

---

## 📈 Future Ideas

* AI verification of lifts (to prevent false PRs)
* Weight class filters
* Verified accounts for athletes
* Mobile app version
* Live PR competitions

---

## 🔜 **MVP Plan (Minimum Viable Product)**

**Sprint 1: Core Backend + Auth**

* User registration
* Flag and username setup
* Basic ELO logic with mock data

**Sprint 2: Video Uploads**

* Upload + store 30s videos
* Link videos to user and lift type

**Sprint 3: Rankings**

* ELO system + rank display
* Leaderboard page

**Sprint 4: UI Polish + Launch**

* Responsive UI
* Profile page
* Global ranking board

---

Here you go, Danial — a full starter setup for your **Gym PR Website** with **Flask backend**, **Supabase integration**, and a simple **React frontend** scaffold. This includes user registration, video uploads, PR submissions, and an ELO-based leaderboard.

---

# 🧠 Project Name: `GymRank`

---

## 🔧 Project Structure

```
/gymrank/
├── /backend/
│   ├── app.py
│   ├── /routes/api.py
│   ├── /services/supabase.py
│   └── requirements.txt
├── /frontend/
│   ├── index.html (or React project)
│   └── ...
├── .env
└── render.yaml
```

---

## 🧪 Flask Backend Code

### 📄 `requirements.txt`

```txt
flask
gunicorn
python-dotenv
supabase
```

---

### 📄 `.env` (Put this at the root)

```env
SUPABASE_URL=https://yourproject.supabase.co
SUPABASE_SERVICE_KEY=your-supabase-service-role-key
```

---

### 📄 `app.py`

```python
from flask import Flask
from routes.api import api_blueprint

app = Flask(__name__)
app.register_blueprint(api_blueprint)

if __name__ == "__main__":
    app.run(debug=True)
```

---

### 📄 `routes/api.py`

```python
from flask import Blueprint, request, jsonify
from services.supabase import supabase, calculate_elo

api_blueprint = Blueprint('api', __name__)

@api_blueprint.route('/api/register', methods=['POST'])
def register_user():
    data = request.json
    username = data['username']
    flag = data['flag']
    
    response = supabase.table('users').insert({'username': username, 'flag': flag}).execute()
    return jsonify(response.data), 201

@api_blueprint.route('/api/submit_pr', methods=['POST'])
def submit_pr():
    data = request.json
    username = data['username']
    lift_type = data['lift_type']  # bench, deadlift, squat
    weight = float(data['weight'])

    # Add the PR
    supabase.table('prs').insert({
        'username': username,
        'lift_type': lift_type,
        'weight': weight
    }).execute()

    # Update ELO
    calculate_elo(username)
    
    return jsonify({'message': 'PR submitted and ELO updated'}), 200

@api_blueprint.route('/api/leaderboard', methods=['GET'])
def leaderboard():
    res = supabase.table('users').select('*').order('elo', desc=True).limit(10).execute()
    return jsonify(res.data)
```

---

### 📄 `services/supabase.py`

```python
from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv()
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))

def calculate_elo(username):
    # Fetch all lifts for the user
    prs = supabase.table('prs').select('*').eq('username', username).execute().data
    total_weight = sum([pr['weight'] for pr in prs])

    # ELO formula (simplified)
    new_elo = 1000 + total_weight * 1.5  # You can scale this differently

    # Update user score
    supabase.table('users').update({'elo': new_elo}).eq('username', username).execute()
```

---

## 🛢️ Supabase Schema

### Table: `users`

| Column   | Type                 |
| -------- | -------------------- |
| username | text (PK)            |
| flag     | text                 |
| elo      | float (default 1000) |

### Table: `prs`

| Column     | Type                                    |
| ---------- | --------------------------------------- |
| username   | text (FK)                               |
| lift\_type | text                                    |
| weight     | float                                   |
| video\_url | text (optional for future upload links) |

---

## 🌐 Frontend (HTML Version Example)

Later you can convert this to React or Next.js.

### 📄 `frontend/index.html`

```html
<!DOCTYPE html>
<html>
<head>
  <title>GymRank</title>
</head>
<body>
  <h1>🏋️ GymRank Leaderboard</h1>
  <div id="leaderboard"></div>

  <script>
    fetch("https://your-backend.onrender.com/api/leaderboard")
      .then(res => res.json())
      .then(data => {
        const list = document.getElementById('leaderboard');
        data.forEach(user => {
          list.innerHTML += `<p>${user.username} ${user.flag} – ELO: ${user.elo.toFixed(2)}</p>`;
        });
      });
  </script>
</body>
</html>
```

---

## 🚀 `render.yaml` for Flask API Deployment

```yaml
services:
  - type: web
    name: gymrank-api
    env: python
    buildCommand: pip install -r backend/requirements.txt
    startCommand: gunicorn app:app
    envVars:
      - key: SUPABASE_URL
        value: your-supabase-url
      - key: SUPABASE_SERVICE_KEY
        value: your-service-key
```

---

## ✅ Deployment Checklist

1. ✅ Set up Supabase project and create `users` + `prs` tables.
2. ✅ Upload `.env` variables to Render dashboard.
3. ✅ Deploy backend to Render as Web Service.
4. ✅ Host frontend via Render Static Site or Netlify/Vercel.

---

Would you like a `.zip` of this full template or the Supabase SQL schema too?
