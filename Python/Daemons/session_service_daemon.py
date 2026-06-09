import secrets
import mysql.connector
from datetime import datetime, timezone

from Daemons.daemon_connector import get

SESSION_BYTES = 32


def utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def session_id_gen() -> str:
    return secrets.token_hex(SESSION_BYTES)


def portal_session_create(user_id: int, ip: str | None = None, device: str | None = None) -> str | dict:
    conn = None
    cursor = None

    try:
        conn = get()
        cursor = conn.cursor()

        timestamp = utc_now()
        session_id = None

        registry_query = """
            INSERT INTO session_registry (
                session_id,
                user_id,
                created_at
            )
            VALUES (%s, %s, %s)
        """

        for _ in range(5):
            candidate_session_id = session_id_gen()

            try:
                cursor.execute(registry_query, (candidate_session_id, user_id, timestamp))
                session_id = candidate_session_id
                break

            except mysql.connector.IntegrityError:
                continue

        if session_id is None:
            conn.rollback()
            return {"success": False, "error": "SESSION_ID_GENERATION_FAILED"}

        portal_query = """
            INSERT INTO portal_sessions (
                user_id,
                session_id,
                created_at,
                last_seen,
                state,
                login_gen
            )
            VALUES (%s, %s, %s, %s, 'ACTIVE', 1)
            ON DUPLICATE KEY UPDATE
                session_id = VALUES(session_id),
                created_at = VALUES(created_at),
                last_seen = VALUES(last_seen),
                state = 'ACTIVE',
                login_gen = login_gen + 1
        """
        cursor.execute(portal_query, (user_id, session_id, timestamp, timestamp))

        meta_data = []

        if ip is not None:
            meta_data.append(f"ip={ip}")

        if device is not None:
            meta_data.append(f"device={device}")

        metadata = "; ".join(meta_data) if meta_data else None

        log_query = """
            INSERT INTO activity_log (
                timestamp,
                user_id,
                session_id,
                event_type,
                metadata
            )
            VALUES (%s, %s, %s, 'LOGIN_SUCCESS', %s)
        """

        cursor.execute(log_query, (timestamp, user_id, session_id, metadata))

        conn.commit()

        return session_id

    except mysql.connector.Error as err:
        if conn:
            conn.rollback()
        return {"success": False, "error": "DATABASE_ERROR", "detail": str(err)}

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def portal_session_validate(session_id: str):
    conn = None
    cursor = None

    try:
        conn = get()
        cursor = conn.cursor(dictionary=True)

        query = """
            SELECT
                portal_sessions.user_id,
                portal_sessions.session_id,
                portal_sessions.state,
                portal_sessions.last_seen,
                users.username,
                users.role,
                users.enabled
            FROM portal_sessions
            JOIN users ON portal_sessions.user_id = users.id
            WHERE portal_sessions.session_id = %s
        """

        cursor.execute(query, (session_id,))
        session = cursor.fetchone()

        if session is None:
            return None

        if session["state"] != "ACTIVE":
            return None

        if not session["enabled"]:
            return None

        update_query = """
            UPDATE portal_sessions
            SET last_seen = %s
            WHERE session_id = %s
        """

        timestamp = utc_now()
        cursor.execute(update_query, (timestamp, session_id))
        conn.commit()

        return {
            "user_id": session["user_id"],
            "session_id": session["session_id"],
            "username": session["username"],
            "role": session["role"]
        }

    except mysql.connector.Error:
        if conn:
            conn.rollback()
        return None

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def portal_session_end(session_id: str) -> bool:
    conn = None
    cursor = None

    try:
        conn = get()
        cursor = conn.cursor(dictionary=True)

        lookup_query = """
            SELECT user_id, session_id
            FROM portal_sessions
            WHERE session_id = %s
        """

        cursor.execute(lookup_query, (session_id,))
        session = cursor.fetchone()

        if session is None:
            return False

        user_id = session["user_id"]
        timestamp = utc_now()

        delete_service_query = """
            DELETE FROM service
            WHERE session_id = %s
        """

        cursor.execute(delete_service_query, (session_id,))

        log_query = """
            INSERT INTO activity_log (
                timestamp,
                user_id,
                session_id,
                event_type
            )
            VALUES (%s, %s, %s, 'LOGOUT')
        """

        cursor.execute(log_query, (timestamp, user_id, session_id))

        portal_query = """
            UPDATE portal_sessions
            SET
                session_id = NULL,
                last_seen = %s,
                state = 'LOGGED_OUT'
            WHERE user_id = %s
        """

        cursor.execute(portal_query, (timestamp, user_id))

        conn.commit()

        return True

    except mysql.connector.Error:
        if conn:
            conn.rollback()
        return False

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def portal_session_status(session_id: str):
    conn = None
    cursor = None

    try:
        conn = get()
        cursor = conn.cursor(dictionary=True)

        query = """
            SELECT
                portal_sessions.user_id,
                portal_sessions.session_id,
                portal_sessions.created_at,
                portal_sessions.last_seen,
                portal_sessions.state,
                users.username,
                users.role
            FROM portal_sessions
            JOIN users
                ON portal_sessions.user_id = users.id
            WHERE portal_sessions.session_id = %s
        """

        cursor.execute(query, (session_id,))
        session = cursor.fetchone()

        if session is None:
            return {
                "success": False,
                "error": "NOT_AUTHENTICATED"
            }

        return {
            "success": True,
            "user_id": session["user_id"],
            "username": session["username"],
            "role": session["role"],
            "created_at": session["created_at"],
            "last_seen": session["last_seen"],
            "state": session["state"]
        }

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()