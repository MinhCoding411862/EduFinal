import mysql.connector
from mysql.connector import Error

def create_connection():
    try:
        connection = mysql.connector.connect(
            host='127.0.0.1',  # Your MySQL host
            user='root',       # Your MySQL username
            password='',  # Your MySQL password
            database='hackkathon2024'  # Your MySQL database name
        )
        if connection.is_connected():
            return connection
    except Error as e:
        print(f"Error: {e}")
        return None
    
def update_survey_data(survey_data):
            # Insert survey data into the database
        connection = create_connection()
        if connection:
            cursor = connection.cursor()
            insert_query = """
            INSERT INTO user_information (weight, height, gender, activity, goal, intensity)
            VALUES (%s, %s, %s, %s, %s, %s)
            """
            values = (survey_data['weight'], survey_data['height'], survey_data['gender'], survey_data['activity'], survey_data['goal'], survey_data['intensity'])
            try:
                cursor.execute(insert_query, values)
                connection.commit()
                print("Survey data inserted successfully.")
            except Error as e:
                print(f"Error: {e}")
                connection.rollback()
            finally:
                cursor.close()
                connection.close()