from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
from services.supabase import get_db_connection, calculate_elo
import os
import uuid
import ffmpeg
import bcrypt
from datetime import datetime

api_blueprint = Blueprint('api', __name__)

@api_blueprint.route('/api/register', methods=['POST'])
def register_user():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    email = data.get('email')
    display_name = data.get('display_name', username)
    flag = data.get('flag')
    
    # Validate required fields
    if not all([username, password, flag]):
        return jsonify({'error': 'Username, password, and flag are required'}), 400
    
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
                INSERT INTO users (username, password_hash, email, display_name, flag) 
                VALUES (%s, %s, %s, %s, %s) RETURNING username, email, display_name, flag, elo, created_at
            """, (username, password_hash, email, display_name, flag))
            
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
                SELECT username, password_hash, email, display_name, flag, elo, is_active, created_at 
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
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM users ORDER BY elo DESC LIMIT 10")
            users = cur.fetchall()
            return jsonify([dict(user) for user in users])
    finally:
        conn.close()

def validate_video_duration(file_path):
    try:
        probe = ffmpeg.probe(file_path)
        duration = float(probe['streams'][0]['duration'])
        return duration <= 30.0
    except:
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
    
    # Validate video duration
    if not validate_video_duration(file_path):
        os.remove(file_path)
        return jsonify({'error': 'Video must be 30 seconds or less'}), 400
    
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
                SELECT p.*, u.flag, u.elo 
                FROM prs p 
                JOIN users u ON p.username = u.username 
                WHERE p.video_url IS NOT NULL 
                ORDER BY p.created_at DESC
            """)
            videos = cur.fetchall()
            return jsonify([dict(video) for video in videos])
    finally:
        conn.close()

@api_blueprint.route('/uploads/<filename>')
def uploaded_file(filename):
    from flask import send_from_directory
    upload_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads')
    return send_from_directory(upload_dir, filename)