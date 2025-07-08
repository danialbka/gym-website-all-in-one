from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
from services.supabase import get_db_connection, calculate_elo
import os
import uuid
import bcrypt
from datetime import datetime

# DOTS Formula Constants
DOTS_MEN = {
    'a': 47.46178854,
    'b': 8.472061379,
    'c': 0.07369410346,
    'd': -0.001395833811,
    'e': 0.000007076659730
}

DOTS_WOMEN = {
    'a': -125.4255398,
    'b': 13.71219419,
    'c': -0.03307250631,
    'd': 0.0003872554572,
    'e': -0.00000113708316
}

def calculate_dots_score(total_lifted, bodyweight, gender):
    """
    Calculate DOTS score based on total lifted weight, bodyweight, and gender
    
    Args:
        total_lifted (float): Total weight lifted (bench + squat + deadlift) in kg
        bodyweight (float): User's bodyweight in kg
        gender (str): 'male' or 'female'
    
    Returns:
        float: DOTS score
    """
    if not bodyweight or bodyweight <= 0:
        return 0
    
    constants = DOTS_MEN if gender == 'male' else DOTS_WOMEN
    
    # DOTS formula: 500 * total_lifted / (a + b*W + c*W^2 + d*W^3 + e*W^4)
    denominator = (constants['a'] + 
                  constants['b'] * bodyweight + 
                  constants['c'] * (bodyweight ** 2) + 
                  constants['d'] * (bodyweight ** 3) + 
                  constants['e'] * (bodyweight ** 4))
    
    dots_score = 500 * total_lifted / denominator
    return round(dots_score, 2)

def get_user_total_lifts(username):
    """
    Get the best lift for each type (bench, squat, deadlift) for a user
    
    Returns:
        dict: {'bench': weight, 'squat': weight, 'deadlift': weight, 'total': total}
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT lift_type, MAX(weight) as max_weight
                FROM prs 
                WHERE username = %s
                GROUP BY lift_type
            """, (username,))
            
            lifts = cur.fetchall()
            lift_data = {'bench': 0, 'squat': 0, 'deadlift': 0}
            
            for lift in lifts:
                lift_data[lift['lift_type']] = float(lift['max_weight'])
            
            lift_data['total'] = lift_data['bench'] + lift_data['squat'] + lift_data['deadlift']
            return lift_data
    finally:
        conn.close()

api_blueprint = Blueprint('api', __name__)

@api_blueprint.route('/api/register', methods=['POST'])
def register_user():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    email = data.get('email')
    display_name = data.get('display_name', username)
    flag = data.get('flag')
    team = data.get('team', 'Independent')
    gender = data.get('gender')
    
    # Validate required fields
    if not all([username, password, flag, gender]):
        return jsonify({'error': 'Username, password, flag, and gender are required'}), 400
    
    # Hash password
    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Check if user already exists
            cur.execute("SELECT username FROM users WHERE username = %s", (username,))
            if cur.fetchone():
                return jsonify({'error': 'Username already exists'}), 400
            
            # Check if email already exists (if provided)
            if email:
                cur.execute("SELECT email FROM users WHERE email = %s", (email,))
                if cur.fetchone():
                    return jsonify({'error': 'Email already exists'}), 400
            
            cur.execute("""
                INSERT INTO users (username, password_hash, email, display_name, flag, team, gender) 
                VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING username, email, display_name, flag, team, gender, elo, created_at
            """, (username, password_hash, email, display_name, flag, team, gender))
            
            user = cur.fetchone()
            conn.commit()
            return jsonify(dict(user)), 201
    except Exception as e:
        return jsonify({'error': 'Registration failed'}), 500
    finally:
        conn.close()

@api_blueprint.route('/api/login', methods=['POST'])
def login_user():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    if not all([username, password]):
        return jsonify({'error': 'Username and password are required'}), 400
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT username, password_hash, email, display_name, flag, team, elo, is_active, created_at 
                FROM users WHERE username = %s AND is_active = TRUE
            """, (username,))
            user = cur.fetchone()
            
            if not user:
                return jsonify({'error': 'Invalid username or password'}), 401
            
            # Verify password
            if not bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
                return jsonify({'error': 'Invalid username or password'}), 401
            
            # Update last login
            cur.execute("UPDATE users SET last_login = %s WHERE username = %s", 
                       (datetime.now(), username))
            conn.commit()
            
            # Return user data without password hash
            user_data = dict(user)
            del user_data['password_hash']
            return jsonify(user_data), 200
            
    except Exception as e:
        return jsonify({'error': 'Login failed'}), 500
    finally:
        conn.close()

@api_blueprint.route('/api/submit_pr', methods=['POST'])
def submit_pr():
    data = request.json
    username = data['username']
    lift_type = data['lift_type']  # bench, deadlift, squat
    weight = float(data['weight'])

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Add the PR
            cur.execute("INSERT INTO prs (username, lift_type, weight) VALUES (%s, %s, %s)",
                       (username, lift_type, weight))
            conn.commit()

            # Update ELO
            calculate_elo(username)
            
            return jsonify({'message': 'PR submitted and ELO updated'}), 200
    finally:
        conn.close()

@api_blueprint.route('/api/leaderboard', methods=['GET'])
def leaderboard():
    gender_filter = request.args.get('gender')  # Optional filter for gender
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Get users with weight and gender for DOTS calculation
            query = """
                SELECT username, display_name, email, flag, team, weight, gender, elo, created_at 
                FROM users 
                WHERE weight IS NOT NULL AND weight > 0 AND gender IS NOT NULL
            """
            params = ()
            
            if gender_filter in ['male', 'female']:
                query += " AND gender = %s"
                params = (gender_filter,)
            
            cur.execute(query, params)
            users = cur.fetchall()
            
            # Calculate DOTS scores for each user
            leaderboard_data = []
            for user in users:
                user_dict = dict(user)
                lift_data = get_user_total_lifts(user['username'])
                
                if lift_data['total'] > 0:  # Only include users with actual lifts
                    dots_score = calculate_dots_score(
                        lift_data['total'], 
                        user['weight'], 
                        user['gender']
                    )
                    
                    user_dict['dots_score'] = dots_score
                    user_dict['total_lifted'] = lift_data['total']
                    user_dict['bench'] = lift_data['bench']
                    user_dict['squat'] = lift_data['squat']
                    user_dict['deadlift'] = lift_data['deadlift']
                    
                    leaderboard_data.append(user_dict)
            
            # Sort by DOTS score (descending) and limit to top 50
            leaderboard_data.sort(key=lambda x: x['dots_score'], reverse=True)
            return jsonify(leaderboard_data[:50])
            
    finally:
        conn.close()

def validate_video_file(file_path):
    try:
        # Check file size (rough estimate: 30 seconds of video should be under 50MB)
        file_size = os.path.getsize(file_path)
        max_size = 50 * 1024 * 1024  # 50MB
        
        if file_size > max_size:
            print(f"File too large: {file_size} bytes (max: {max_size})")
            return False
            
        print(f"Video file size: {file_size} bytes - OK")
        return True
    except Exception as e:
        print(f"Error validating video file: {e}")
        return False

@api_blueprint.route('/api/upload_video', methods=['POST'])
def upload_video():
    if 'video' not in request.files:
        return jsonify({'error': 'No video file provided'}), 400
    
    video_file = request.files['video']
    username = request.form.get('username')
    lift_type = request.form.get('lift_type')
    weight = request.form.get('weight')
    
    if not all([username, lift_type, weight]):
        return jsonify({'error': 'Missing required fields'}), 400
    
    if video_file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    # Validate file extension
    allowed_extensions = {'.mp4', '.webm', '.mov', '.avi'}
    file_ext = os.path.splitext(video_file.filename)[1].lower()
    if file_ext not in allowed_extensions:
        return jsonify({'error': 'Invalid file format. Use MP4, WebM, MOV, or AVI'}), 400
    
    # Generate unique filename
    filename = f"{uuid.uuid4()}{file_ext}"
    upload_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads')
    file_path = os.path.join(upload_dir, filename)
    
    # Save file temporarily to check duration
    video_file.save(file_path)
    
    # Validate video file
    if not validate_video_file(file_path):
        os.remove(file_path)
        return jsonify({'error': 'Video file too large (max 50MB)'}), 400
    
    # Save to database
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            video_url = f"/uploads/{filename}"
            cur.execute("""
                INSERT INTO prs (username, lift_type, weight, video_url) 
                VALUES (%s, %s, %s, %s) RETURNING id
            """, (username, lift_type, float(weight), video_url))
            
            pr_id = cur.fetchone()['id']
            conn.commit()
            
            # Update ELO
            calculate_elo(username)
            
            return jsonify({
                'message': 'Video uploaded successfully',
                'pr_id': pr_id,
                'video_url': video_url
            }), 201
    except Exception as e:
        os.remove(file_path)  # Clean up file on database error
        return jsonify({'error': 'Database error'}), 500
    finally:
        conn.close()

@api_blueprint.route('/api/videos', methods=['GET'])
def get_videos():
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT p.*, u.flag, u.team, u.elo 
                FROM prs p 
                JOIN users u ON p.username = u.username 
                WHERE p.video_url IS NOT NULL AND p.video_url != '' 
                ORDER BY p.created_at DESC
            """)
            videos = cur.fetchall()
            return jsonify([dict(video) for video in videos])
    finally:
        conn.close()

@api_blueprint.route('/uploads/<filename>')
def uploaded_file(filename):
    from flask import send_from_directory, abort
    import os
    
    upload_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads')
    file_path = os.path.join(upload_dir, filename)
    
    # Check if file exists
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        abort(404)
    
    print(f"Serving video file: {file_path}")
    
    # Set appropriate headers for video files
    response = send_from_directory(upload_dir, filename)
    response.headers['Content-Type'] = 'video/mp4'
    response.headers['Accept-Ranges'] = 'bytes'
    return response

@api_blueprint.route('/api/team_leaderboard', methods=['GET'])
def team_leaderboard():
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    team,
                    COUNT(DISTINCT username) as member_count,
                    AVG(elo) as avg_elo,
                    MAX(elo) as top_elo,
                    SUM(elo) as total_elo
                FROM users 
                WHERE team IS NOT NULL AND team != '' 
                GROUP BY team 
                ORDER BY avg_elo DESC
            """)
            teams = cur.fetchall()
            return jsonify([dict(team) for team in teams])
    finally:
        conn.close()

@api_blueprint.route('/api/team_members/<team_name>', methods=['GET'])
def team_members(team_name):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT username, display_name, flag, elo, team
                FROM users 
                WHERE team = %s 
                ORDER BY elo DESC
            """, (team_name,))
            members = cur.fetchall()
            return jsonify([dict(member) for member in members])
    finally:
        conn.close()

@api_blueprint.route('/api/profile/update', methods=['PUT'])
def update_profile():
    data = request.json
    username = data.get('username')
    new_username = data.get('new_username')
    team = data.get('team')
    weight = data.get('weight')
    gender = data.get('gender')
    
    if not all([username, new_username, team, gender]):
        return jsonify({'error': 'Username, new username, team, and gender are required'}), 400
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Check if new username already exists (if changing username)
            if username != new_username:
                cur.execute("SELECT username FROM users WHERE username = %s", (new_username,))
                if cur.fetchone():
                    return jsonify({'error': 'Username already exists'}), 400
            
            # Update the profile
            cur.execute("""
                UPDATE users 
                SET username = %s, team = %s, weight = %s, gender = %s 
                WHERE username = %s
                RETURNING username, display_name, email, flag, team, weight, gender, elo, created_at
            """, (new_username, team, weight, gender, username))
            
            user = cur.fetchone()
            if not user:
                return jsonify({'error': 'User not found'}), 404
            
            # Update all PRs to use new username if username changed
            if username != new_username:
                cur.execute("UPDATE prs SET username = %s WHERE username = %s", (new_username, username))
            
            conn.commit()
            
            # Recalculate ELO for the user
            calculate_elo(new_username)
            
            return jsonify(dict(user)), 200
    except Exception as e:
        return jsonify({'error': 'Profile update failed'}), 500
    finally:
        conn.close()

@api_blueprint.route('/api/user/<username>/posts', methods=['GET'])
def get_user_posts(username):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT p.*, u.flag, u.team, u.elo 
                FROM prs p 
                JOIN users u ON p.username = u.username 
                WHERE p.username = %s 
                ORDER BY p.created_at DESC
            """, (username,))
            posts = cur.fetchall()
            return jsonify([dict(post) for post in posts])
    finally:
        conn.close()

@api_blueprint.route('/api/posts/<int:post_id>', methods=['DELETE'])
def delete_post(post_id):
    data = request.json
    username = data.get('username')
    
    if not username:
        return jsonify({'error': 'Username is required'}), 400
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Check if post exists and belongs to user
            cur.execute("""
                SELECT id, video_url FROM prs 
                WHERE id = %s AND username = %s
            """, (post_id, username))
            post = cur.fetchone()
            
            if not post:
                return jsonify({'error': 'Post not found or not authorized'}), 404
            
            # Delete the video file if it exists
            if post['video_url']:
                video_path = os.path.join(
                    os.path.dirname(os.path.dirname(__file__)), 
                    'uploads', 
                    os.path.basename(post['video_url'])
                )
                if os.path.exists(video_path):
                    os.remove(video_path)
            
            # Delete the post
            cur.execute("DELETE FROM prs WHERE id = %s", (post_id,))
            conn.commit()
            
            # Recalculate ELO
            calculate_elo(username)
            
            return jsonify({'message': 'Post deleted successfully'}), 200
    except Exception as e:
        return jsonify({'error': 'Failed to delete post'}), 500
    finally:
        conn.close()

@api_blueprint.route('/api/posts/<int:post_id>', methods=['PUT'])
def edit_post(post_id):
    data = request.json
    username = data.get('username')
    lift_type = data.get('lift_type')
    weight = data.get('weight')
    
    if not all([username, lift_type, weight]):
        return jsonify({'error': 'Username, lift type and weight are required'}), 400
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Check if post exists and belongs to user
            cur.execute("SELECT id FROM prs WHERE id = %s AND username = %s", (post_id, username))
            if not cur.fetchone():
                return jsonify({'error': 'Post not found or not authorized'}), 404
            
            # Update the post
            cur.execute("""
                UPDATE prs 
                SET lift_type = %s, weight = %s 
                WHERE id = %s
                RETURNING id, username, lift_type, weight, video_url, created_at
            """, (lift_type, float(weight), post_id))
            
            post = cur.fetchone()
            conn.commit()
            
            # Recalculate ELO
            calculate_elo(username)
            
            return jsonify(dict(post)), 200
    except Exception as e:
        return jsonify({'error': 'Failed to update post'}), 500
    finally:
        conn.close()