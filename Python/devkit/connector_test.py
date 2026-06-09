import os
import mysql.connector

def get():
    connection = mysql.connector.connect(
        host = os.environ["DB_HOST"],
        user = os.environ["DB_API_USER"],
        password = os.environ["DB_API_PASSWORD"],
        database = os.environ["DB_API_NAME"]
    )
    return connection

def main():
    try:
        conn = get()
        cursor = conn.cursor()
        
        cursor.execute("SELECT DATABASE();")
        result = cursor.fetchone()
        
        print("Connected to database:", result[0])
        
        cursor.close()
        conn.close()
        
    except mysql.connector.Error as err:
        print("Database connection failed:")
        print(err)
        
if __name__ == "__main__":
    main()