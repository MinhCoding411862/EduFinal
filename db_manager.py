import mysql.connector
from mysql.connector import Error
from datetime import datetime, timedelta
import random

def setup_database():
    conn = None
    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password=""
        )
        cursor = conn.cursor()

        cursor.execute("CREATE DATABASE IF NOT EXISTS exercise_tracker")
        cursor.execute("USE exercise_tracker")

        # Create user_score table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_score (
                id INT AUTO_INCREMENT PRIMARY KEY,
                total_points INT NOT NULL,
                score_date DATE NOT NULL
            )
        """)

        # Create exercise table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS exercise (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_score_id INT,
                exercise_type ENUM('squat', 'bicep_curl', 'push_up') NOT NULL,
                points INT NOT NULL,
                FOREIGN KEY (user_score_id) REFERENCES user_score(id)
            )
        """)

        # Populate tables with sample data
        cursor.execute("SELECT COUNT(*) FROM user_score")
        if cursor.fetchone()[0] == 0:
            for i in range(30):
                date = (datetime.now() - timedelta(days=29-i)).date()
                
                # Insert into user_score table
                cursor.execute(
                    "INSERT INTO user_score (total_points, score_date) VALUES (%s, %s)",
                    (0, date)
                )
                user_score_id = cursor.lastrowid

                # Insert exercises
                total_points = 0
                for exercise_type in ['squat', 'bicep_curl', 'push_up']:
                    points = random.randint(1, 10) * 10  # Ensure points are multiples of 10
                    total_points += points
                    cursor.execute(
                        "INSERT INTO exercise (user_score_id, exercise_type, points) VALUES (%s, %s, %s)",
                        (user_score_id, exercise_type, points)
                    )

                # Update total points in user_score table
                cursor.execute(
                    "UPDATE user_score SET total_points = %s WHERE id = %s",
                    (total_points, user_score_id)
                )

        conn.commit()
        print("Database setup completed successfully.")
    except Error as e:
        print(f"Error setting up database: {e}")
    finally:
        if conn and conn.is_connected():
            conn.close()

def get_score_data():
    conn = None
    try:
        setup_database()

        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="exercise_tracker"
        )
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT 
                us.score_date,
                us.total_points,
                MAX(CASE WHEN e.exercise_type = 'squat' THEN e.points ELSE 0 END) as squat_points,
                MAX(CASE WHEN e.exercise_type = 'bicep_curl' THEN e.points ELSE 0 END) as bicep_curl_points,
                MAX(CASE WHEN e.exercise_type = 'push_up' THEN e.points ELSE 0 END) as push_up_points
            FROM user_score us
            LEFT JOIN exercise e ON us.id = e.user_score_id
            GROUP BY us.id, us.score_date, us.total_points
            ORDER BY us.score_date
        """)
        data = cursor.fetchall()

        cursor.execute("SELECT SUM(total_points) AS grand_total FROM user_score")
        grand_total = cursor.fetchone()['grand_total']

        return data, grand_total
    except Error as e:
        print(f"Error fetching data from database: {e}")
        return [], 0
    finally:
        if conn and conn.is_connected():
            conn.close()

if __name__ == "__main__":
    setup_database()
    data, grand_total = get_score_data()
    print("Sample data:")
    for row in data[:5]:  # Print first 5 rows
        print(row)
    print(f"Grand total points: {grand_total}")