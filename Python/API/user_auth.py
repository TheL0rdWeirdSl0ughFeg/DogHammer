import mysql.connector

from API.api_connector import get
from API.pass_secure import verify_pass


def authenticate_user(username: str, password: str):
    conn = None
    cursor = None

    try:
        conn = get()
        cursor = conn.cursor(dictionary=True)

        query = """
            SELECT id, username, password_hash, role, enabled
            FROM users
            WHERE username = %s
        """

        cursor.execute(query, (username,))
        user = cursor.fetchone()

        if user is None:
            return None

        if not user["enabled"]:
            return None

        if not verify_pass(password, user["password_hash"]):
            return None

        return {
            "id": user["id"],
            "username": user["username"],
            "role": user["role"]
        }

    except mysql.connector.Error:
        return None

    except ValueError:
        return None

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()