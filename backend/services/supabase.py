import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv

load_dotenv()

def get_db_connection():
    return psycopg2.connect(
        os.getenv("DATABASE_URL"),
        cursor_factory=RealDictCursor
    )

def calculate_elo(username):
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Fetch all lifts for the user
            cur.execute("SELECT * FROM prs WHERE username = %s", (username,))
            prs = cur.fetchall()
            total_weight = sum([pr['weight'] for pr in prs])

            # ELO formula (simplified)
            new_elo = 1000 + total_weight * 1.5  # You can scale this differently

            # Update user score
            cur.execute("UPDATE users SET elo = %s WHERE username = %s", (new_elo, username))
            conn.commit()
    finally:
        conn.close()