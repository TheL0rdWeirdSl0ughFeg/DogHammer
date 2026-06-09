import secrets
from datetime import datetime, timezone, timedelta

from Daemons.daemon_connector import get

SERVICE_TOKEN_BYTES = 32

REGION_SERVICES = {"GAMES", "FILES", "FORUM"}
PRIVILEGE_SERVICES = {"ADMIN", "BACKEND"}


def service_token_gen() -> str:
    return secrets.token_hex(SERVICE_TOKEN_BYTES)


def grant_service(session_id: str, service_type: str, service_name: str, user_role: str) -> dict:
    conn = get()
    cursor = conn.cursor(dictionary=True)

    timestamp = datetime.now(timezone.utc)

    session_query = """
        SELECT user_id, session_id, state
        FROM portal_sessions
        WHERE session_id = %s
    """
    cursor.execute(session_query, (session_id,))
    session = cursor.fetchone()

    if session is None:
        cursor.close()
        conn.close()
        return {"success": False, "error": "NOT_AUTHENTICATED"}

    if session["state"] != "ACTIVE":
        cursor.close()
        conn.close()
        return {"success": False, "error": "ACCESS_DENIED"}

    existing_query = """
        SELECT session_id
        FROM service
        WHERE session_id = %s
    """
    cursor.execute(existing_query, (session_id,))
    existing_service = cursor.fetchone()

    if existing_service is not None:
        cursor.close()
        conn.close()
        return {"success": False, "error": "ERROR_SERVICE_ALREADY_ACTIVE"}

    if service_type == "REGION":
        if service_name not in REGION_SERVICES:
            cursor.close()
            conn.close()
            return {"success": False, "error": "INVALID_SERVICE"}

    elif service_type == "PRIVILEGE":
        if service_name not in PRIVILEGE_SERVICES:
            cursor.close()
            conn.close()
            return {"success": False, "error": "INVALID_SERVICE"}

        if service_name == "ADMIN" and user_role not in ("ADMIN", "SUPERADMIN"):
            cursor.close()
            conn.close()
            return {"success": False, "error": "ACCESS_DENIED"}
        
        if service_name == "BACKEND" and user_role != "SUPERADMIN":
            cursor.close()
            conn.close()
            return {"success": False, "error": "ACCESS_DENIED"}

    else:
        cursor.close()
        conn.close()
        return {"success": False, "error": "INVALID_SERVICE_TYPE"}

    token = service_token_gen()

    if service_type == "PRIVILEGE":
        expires_at = timestamp + timedelta(minutes=30)
    else:
        expires_at = timestamp + timedelta(hours=24)

    service_insert = """
        INSERT INTO service (
            token,
            session_id,
            service_type,
            service_name,
            issued_at,
            expires_at
        )
        VALUES (%s, %s, %s, %s, %s, %s)
    """
    cursor.execute(service_insert, (token, session_id, service_type, service_name, timestamp, expires_at))

    log_insert = """
        INSERT INTO activity_log (
            timestamp,
            user_id,
            session_id,
            event_type,
            service_type,
            service_name
        )
        VALUES (%s, %s, %s, 'SERVICE_ENTER', %s, %s)
    """
    cursor.execute(log_insert, (timestamp, session["user_id"], session_id, service_type, service_name))

    conn.commit()
    cursor.close()
    conn.close()

    return {
        "success": True,
        "token": token,
        "service_type": service_type,
        "service_name": service_name,
        "expires_at": expires_at.isoformat()
    }
    
def clear_service(session_id: str) -> dict:
    conn = get()
    cursor = conn.cursor(dictionary=True)

    timestamp = datetime.now(timezone.utc)

    lookup = """
        SELECT
            service.session_id,
            service.service_type,
            service.service_name,
            portal_sessions.user_id
        FROM service
        JOIN portal_sessions ON service.session_id = portal_sessions.session_id
        WHERE service.session_id = %s
    """

    cursor.execute(lookup, (session_id,))
    service = cursor.fetchone()

    if service is None:
        cursor.close()
        conn.close()
        return {
            "success": False,
            "error": "NO_ACTIVE_SERVICE"
        }

    log_update = """
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
        log_update,
        (
            timestamp,
            service["user_id"],
            session_id,
            service["service_type"],
            service["service_name"]
        )
    )

    delete = """
        DELETE FROM service
        WHERE session_id = %s
    """

    cursor.execute(delete, (session_id,))

    conn.commit()
    cursor.close()
    conn.close()

    return {
        "success": True,
        "service_type": service["service_type"],
        "service_name": service["service_name"]
    }
    
def validate_service(session_id: str, required_service: str) -> dict:
    conn = get()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT
            service.service_type,
            service.service_name,
            service.expires_at,
            portal_sessions.state
        FROM service
        JOIN portal_sessions ON service.session_id = portal_sessions.session_id
        WHERE service.session_id = %s
    """

    cursor.execute(query, (session_id,))
    service = cursor.fetchone()

    cursor.close()
    conn.close()

    if service is None:
        return {"success": False, "error": "ACCESS_DENIED"}

    if service["state"] != "ACTIVE":
        return {"success": False, "error": "ACCESS_DENIED"}
    
    if service["expires_at"] <= datetime.now(timezone.utc).replace(tzinfo=None):
        return {"success": False, "error": "SERVICE_EXPIRED"}

    if service["service_name"] != required_service:
        return {"success": False, "error": "ACCESS_DENIED"}

    return {
        "success": True,
        "service_type": service["service_type"],
        "service_name": service["service_name"]
    }

def service_status(session_id: str):
    conn = None
    cursor = None

    try:
        conn = get()
        cursor = conn.cursor(dictionary=True)

        query = """
            SELECT
                service_type,
                service_name,
                issued_at,
                expires_at
            FROM service
            WHERE session_id = %s
        """

        cursor.execute(query, (session_id,))
        service = cursor.fetchone()

        if service is None:
            return {
                "success": False,
                "error": "NO_ACTIVE_SERVICE"
            }

        return {
            "success": True,
            "service_type": service["service_type"],
            "service_name": service["service_name"],
            "issued_at": service["issued_at"],
            "expires_at": service["expires_at"]
        }

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()