import time
import mysql.connector
from datetime import datetime, timezone

from Daemons.daemon_connector import get

CHECK_INTERVAL_SECONDS = 30


def utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def expire_service():
    conn = None
    cursor = None

    try:
        conn = get()
        cursor = conn.cursor(dictionary=True)

        timestamp = utc_now()

        lookup = """
            SELECT
                service.session_id,
                service.service_type,
                service.service_name,
                portal_sessions.user_id
            FROM service
            JOIN portal_sessions
                ON service.session_id = portal_sessions.session_id
            WHERE service.expires_at <= %s
        """

        cursor.execute(lookup, (timestamp,))
        expired_services = cursor.fetchall()

        for service in expired_services:
            log_query = """
                INSERT INTO activity_log (
                    timestamp,
                    user_id,
                    session_id,
                    event_type,
                    service_type,
                    service_name
                )
                VALUES (%s, %s, %s, 'SERVICE_EXIT', %s, %s)
            """

            cursor.execute(
                log_query,
                (
                    timestamp,
                    service["user_id"],
                    service["session_id"],
                    service["service_type"],
                    service["service_name"]
                )
            )

            delete = """
                DELETE FROM service
                WHERE session_id = %s
            """

            cursor.execute(delete, (service["session_id"],))

            update_portal = """
                UPDATE portal_sessions
                SET last_seen = %s
                WHERE session_id = %s
            """

            cursor.execute(update_portal, (timestamp, service["session_id"]))

        conn.commit()

    except mysql.connector.Error as err:
        if conn:
            conn.rollback()
        print("expire_service database error:", err)

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def expire_portal():
    conn = None
    cursor = None

    try:
        conn = get()
        cursor = conn.cursor(dictionary=True)

        timestamp = utc_now()

        lookup = """
            SELECT
                portal_sessions.user_id,
                portal_sessions.session_id
            FROM portal_sessions
            LEFT JOIN service
                ON portal_sessions.session_id = service.session_id
            WHERE portal_sessions.state = 'ACTIVE'
            AND portal_sessions.session_id IS NOT NULL
            AND service.session_id IS NULL
            AND portal_sessions.last_seen <= DATE_SUB(%s, INTERVAL 30 MINUTE)
        """

        cursor.execute(lookup, (timestamp,))
        expired_sessions = cursor.fetchall()

        for session in expired_sessions:
            log_query = """
                INSERT INTO activity_log (
                    timestamp,
                    user_id,
                    session_id,
                    event_type
                )
                VALUES (%s, %s, %s, 'SESSION_EXPIRED')
            """

            cursor.execute(
                log_query,
                (
                    timestamp,
                    session["user_id"],
                    session["session_id"]
                )
            )

            update = """
                UPDATE portal_sessions
                SET
                    session_id = NULL,
                    last_seen = %s,
                    state = 'EXPIRED'
                WHERE user_id = %s
            """

            cursor.execute(update, (timestamp, session["user_id"]))

        conn.commit()

    except mysql.connector.Error as err:
        if conn:
            conn.rollback()
        print("expire_portal database error:", err)

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def cleanup():
    while True:
        expire_service()
        expire_portal()
        time.sleep(CHECK_INTERVAL_SECONDS)


if __name__ == "__main__":
    cleanup()