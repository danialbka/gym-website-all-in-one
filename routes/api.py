from flask import Blueprint, request, jsonify, current_app, render_template
from werkzeug.utils import secure_filename
from services.supabase import get_db_connection, calculate_elo
from flask_mail import Message
import os
import uuid
import bcrypt
from datetime import datetime
import secrets
import hashlib

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
    if not all([username, password, email, flag, gender]):
        return jsonify({'error': 'Username, password, email, flag, and gender are required'}), 400
    
    # Hash password
    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Check if user already exists
            cur.execute("SELECT username FROM users WHERE username = %s", (username,))
            if cur.fetchone():
                return jsonify({'error': 'Username already exists'}), 400
            
            # Check if email already exists
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
                SELECT username, password_hash, email, display_name, flag, team, weight, gender, elo, is_active, created_at 
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


@api_blueprint.route('/api/leaderboard', methods=['GET'])
def leaderboard():
    gender_filter = request.args.get('gender')  # Optional filter for gender
    country_filter = request.args.get('country')  # Optional filter for country (flag)
    
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Get users with weight and gender for DOTS calculation
            query = """
                SELECT username, display_name, email, flag, team, weight, gender, elo, created_at 
                FROM users 
                WHERE weight IS NOT NULL AND weight > 0 AND gender IS NOT NULL
            """
            params = []
            
            if gender_filter in ['male', 'female']:
                query += " AND gender = %s"
                params.append(gender_filter)
            
            if country_filter:
                query += " AND flag = %s"
                params.append(country_filter)
            
            cur.execute(query, tuple(params))
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

@api_blueprint.route('/api/submit_pr', methods=['POST'])
def submit_pr():
    username = request.form.get('username')
    lift_type = request.form.get('lift_type')
    weight = request.form.get('weight')
    instagram_url = request.form.get('instagram_url')
    
    if not all([username, lift_type, weight, instagram_url]):
        return jsonify({'error': 'Missing required fields'}), 400
    
    # Validate Instagram URL
    if 'instagram.com' not in instagram_url:
        return jsonify({'error': 'Invalid Instagram URL'}), 400
    
    # Save to database
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO prs (username, lift_type, weight, video_url) 
                VALUES (%s, %s, %s, %s) RETURNING id
            """, (username, lift_type, float(weight), instagram_url))
            
            pr_id = cur.fetchone()['id']
            conn.commit()
            
            # Update ELO
            calculate_elo(username)
            
            return jsonify({
                'message': 'PR submitted successfully',
                'pr_id': pr_id,
                'instagram_url': instagram_url
            }), 201
    except Exception as e:
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

@api_blueprint.route('/api/user/<username>', methods=['GET'])
def get_user_profile(username):
    """Get detailed user profile including PRs and videos"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Get user basic info
            cur.execute("""
                SELECT username, display_name, email, flag, team, weight, gender, elo, created_at 
                FROM users WHERE username = %s AND is_active = TRUE
            """, (username,))
            user = cur.fetchone()
            
            if not user:
                return jsonify({'error': 'User not found'}), 404
            
            user_dict = dict(user)
            
            # Get user's PRs (get the record with max weight for each lift type)
            cur.execute("""
                SELECT DISTINCT ON (lift_type) lift_type, weight as max_weight, video_url, created_at
                FROM prs 
                WHERE username = %s 
                ORDER BY lift_type, weight DESC, created_at DESC
            """, (username,))
            prs = cur.fetchall()
            
            # Get all user's PR history
            cur.execute("""
                SELECT id, lift_type, weight, video_url, created_at
                FROM prs 
                WHERE username = %s 
                ORDER BY created_at DESC
                LIMIT 20
            """, (username,))
            history = cur.fetchall()
            
            # Get user's videos
            cur.execute("""
                SELECT id, lift_type, weight, video_url, created_at
                FROM prs 
                WHERE username = %s AND video_url IS NOT NULL AND video_url != ''
                ORDER BY created_at DESC
                LIMIT 10
            """, (username,))
            videos = cur.fetchall()
            
            # Calculate DOTS score if user has all required data
            dots_score = None
            total_lifted = 0
            current_prs = {'bench': 0, 'squat': 0, 'deadlift': 0}
            
            for pr in prs:
                weight = pr['max_weight']
                lift_type = pr['lift_type']
                current_prs[lift_type] = weight
                total_lifted += weight
                print(f"Processing PR: {lift_type} = {weight}kg, running total = {total_lifted}kg")
            
            if user_dict['weight'] and user_dict['gender'] and all(current_prs.values()):
                dots_score = calculate_dots_score(
                    total_lifted, 
                    user_dict['weight'], 
                    user_dict['gender']
                )
            
            return jsonify({
                'user': user_dict,
                'prs': [dict(pr) for pr in prs],
                'history': [dict(record) for record in history],
                'videos': [dict(video) for video in videos],
                'dots_score': dots_score,
                'total_lifted': total_lifted,
                'current_prs': current_prs
            })
            
    except Exception as e:
        return jsonify({'error': f'Failed to get user profile: {str(e)}'}), 500
    finally:
        conn.close()

@api_blueprint.route('/api/user/<username>/progress', methods=['GET'])
def get_user_progress(username):
    """Get user's progress data for charts"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Check if user exists
            cur.execute("SELECT username FROM users WHERE username = %s AND is_active = TRUE", (username,))
            if not cur.fetchone():
                return jsonify({'error': 'User not found'}), 404
            
            # Get progress data for each lift type
            progress_data = {}
            
            for lift_type in ['bench', 'squat', 'deadlift']:
                cur.execute("""
                    SELECT weight, created_at
                    FROM prs 
                    WHERE username = %s AND lift_type = %s
                    ORDER BY created_at ASC
                """, (username, lift_type))
                
                records = cur.fetchall()
                progress_data[lift_type] = [
                    {
                        'weight': record['weight'],
                        'date': record['created_at'].isoformat() if record['created_at'] else None
                    }
                    for record in records
                ]
            
            return jsonify(progress_data)
            
    except Exception as e:
        return jsonify({'error': f'Failed to get user progress: {str(e)}'}), 500
    finally:
        conn.close()

@api_blueprint.route('/api/forgot-password', methods=['POST'])
def forgot_password():
    """Handle forgot password requests"""
    try:
        data = request.get_json()
        identifier = data.get('identifier', '').strip()
        
        if not identifier:
            return jsonify({'error': 'Username or email is required'}), 400
        
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                # Check if user exists by username or email
                cur.execute("""
                    SELECT email, username FROM users 
                    WHERE (username = %s OR email = %s) AND is_active = TRUE
                """, (identifier, identifier))
                user = cur.fetchone()
                
                if not user or not user['email']:
                    # Don't reveal if user exists or not for security
                    return jsonify({'message': 'If your username or email exists, you will receive reset instructions.'}), 200
                
                # Generate reset token
                reset_token = secrets.token_urlsafe(32)
                token_hash = hashlib.sha256(reset_token.encode()).hexdigest()
                
                # Ensure password_reset_tokens table exists
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS password_reset_tokens (
                        id SERIAL PRIMARY KEY,
                        username VARCHAR(255) UNIQUE NOT NULL,
                        token_hash VARCHAR(255) NOT NULL,
                        expires_at TIMESTAMP NOT NULL,
                        created_at TIMESTAMP DEFAULT NOW()
                    )
                """)
                
                # Store reset token (expires in 1 hour) - use the username from database
                username = user['username']
                cur.execute("""
                    INSERT INTO password_reset_tokens (username, token_hash, expires_at, created_at)
                    VALUES (%s, %s, NOW() + INTERVAL '1 hour', NOW())
                    ON CONFLICT (username) 
                    DO UPDATE SET 
                        token_hash = EXCLUDED.token_hash,
                        expires_at = EXCLUDED.expires_at,
                        created_at = EXCLUDED.created_at
                """, (username, token_hash))
                
                conn.commit()
                
                # Send email with reset link
                try:
                    from app import mail
                    
                    # Validate email exists
                    email = user.get('email')
                    if not email:
                        print(f"No email address found for user: {username}")
                        return jsonify({'message': 'If your username or email exists, you will receive reset instructions.'}), 200
                    
                    # Determine the base URL (use environment variable or default)
                    base_url = os.getenv('BASE_URL', 'http://localhost:5000')
                    reset_url = f"{base_url}/reset-password.html?token={reset_token}"
                    
                    # Create email message
                    msg = Message(
                        subject="Reset Your GymRank Password",
                        recipients=[email],
                        html=render_template('password_reset_email.html', 
                                           username=username, 
                                           reset_url=reset_url)
                    )
                    
                    # Send the email
                    mail.send(msg)
                    print(f"Password reset email sent to {email} for user: {username}")
                    
                except Exception as email_error:
                    print(f"Failed to send email: {email_error}")
                    print(f"User data: {user}")
                    # Still return success to not reveal if user exists
                
                return jsonify({'message': 'If your username or email exists, you will receive reset instructions.'}), 200
                
        except Exception as e:
            conn.rollback()
            print(f"Forgot password error: {str(e)}")
            return jsonify({'error': 'Failed to process password reset request'}), 500
        finally:
            conn.close()
            
    except Exception as e:
        return jsonify({'error': 'Invalid request'}), 400

@api_blueprint.route('/api/reset-password', methods=['POST'])
def reset_password():
    """Handle password reset with token"""
    try:
        data = request.get_json()
        token = data.get('token', '').strip()
        new_password = data.get('password', '').strip()
        
        if not token or not new_password:
            return jsonify({'error': 'Token and new password are required'}), 400
        
        if len(new_password) < 6:
            return jsonify({'error': 'Password must be at least 6 characters long'}), 400
        
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                # Check if token is valid and not expired
                cur.execute("""
                    SELECT username FROM password_reset_tokens 
                    WHERE token_hash = %s AND expires_at > NOW()
                """, (token_hash,))
                
                result = cur.fetchone()
                if not result:
                    return jsonify({'error': 'Invalid or expired reset token'}), 400
                
                username = result['username']
                
                # Hash new password
                password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                
                # Update password
                cur.execute("UPDATE users SET password_hash = %s WHERE username = %s", (password_hash, username))
                
                # Delete used reset token
                cur.execute("DELETE FROM password_reset_tokens WHERE username = %s", (username,))
                
                conn.commit()
                
                return jsonify({'message': 'Password reset successful'}), 200
                
        except Exception as e:
            conn.rollback()
            print(f"Password reset error: {str(e)}")
            return jsonify({'error': 'Failed to reset password'}), 500
        finally:
            conn.close()
            
    except Exception as e:
        return jsonify({'error': 'Invalid request'}), 400