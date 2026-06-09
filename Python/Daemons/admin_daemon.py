import mysql.connector
from datetime import datetime, timezone

from Daemons.daemon_connector import get
from API.pass_secure import verify_pass
from Daemons.privilege_connector import get as privilege_get
from Daemons.server_service_daemon import grant_service


def utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def admin_metadata(admin: dict) -> str:
    return f"admin_user_id={admin['user_id']}; admin_username={admin['username']}"

def _get_admin(cursor, admin_session_id: str):
    query = """
        SELECT
            portal_sessions.user_id,
            users.username,
            users.role,
            portal_sessions.state
        FROM portal_sessions
        JOIN users
            ON portal_sessions.user_id = users.id
        WHERE portal_sessions.session_id = %s
    """

    cursor.execute(query, (admin_session_id,))
    admin = cursor.fetchone()

    if admin is None:
        return None, {"success": False, "error": "ADMIN_NOT_AUTHENTICATED"}

    if admin["state"] != "ACTIVE":
        return None, {"success": False, "error": "ADMIN_NOT_ACTIVE"}

    if admin["role"] not in ("ADMIN", "SUPERADMIN"):
        return None, {"success": False, "error": "ACCESS_DENIED"}

    return admin, None

def _get_actor(cursor, session_id: str):
    query = """
        SELECT
            portal_sessions.user_id,
            users.username,
            users.role,
            portal_sessions.state,
            service.service_type,
            service.service_name
        FROM portal_sessions
        JOIN users
            ON portal_sessions.user_id = users.id
        LEFT JOIN service
            ON portal_sessions.session_id = service.session_id
        WHERE portal_sessions.session_id = %s
    """

    cursor.execute(query, (session_id,))
    actor = cursor.fetchone()

    if actor is None:
        return None, {"success": False, "error": "NOT_AUTHENTICATED"}

    if actor["state"] != "ACTIVE":
        return None, {"success": False, "error": "SESSION_NOT_ACTIVE"}

    return actor, None

def escalate_admin(session_id: str, admin_password: str) -> dict:
    conn = None
    cursor = None

    try:
        conn = privilege_get()
        cursor = conn.cursor(dictionary=True)

        timestamp = utc_now()

        query = """
            SELECT
                portal_sessions.user_id,
                portal_sessions.session_id,
                portal_sessions.state,
                users.role,
                admin_credentials.admin_password_hash
            FROM portal_sessions
            JOIN users
                ON portal_sessions.user_id = users.id
            JOIN admin_credentials
                ON users.id = admin_credentials.user_id
            WHERE portal_sessions.session_id = %s
        """

        cursor.execute(query, (session_id,))
        admin = cursor.fetchone()

        if admin is None:
            return {"success": False, "error": "NOT_AUTHENTICATED"}

        if admin["state"] != "ACTIVE":
            return {"success": False, "error": "ACCESS_DENIED"}

        active_service_query = """
            SELECT session_id
            FROM service
            WHERE session_id = %s
        """

        cursor.execute(active_service_query, (session_id,))
        active_service = cursor.fetchone()

        if active_service is not None:
            return {"success": False, "error": "SERVICE_ALREADY_ACTIVE"}

        if admin["role"] not in ("ADMIN", "SUPERADMIN"):
            return {"success": False, "error": "ACCESS_DENIED"}

        if admin["admin_password_hash"] is None:
            return {"success": False, "error": "ADMIN_CREDENTIAL_NOT_SET"}

        if not verify_pass(admin_password, admin["admin_password_hash"]):
            return {"success": False, "error": "ACCESS_DENIED"}

        result = grant_service(
            session_id=session_id,
            service_type="PRIVILEGE",
            service_name="ADMIN",
            user_role=admin["role"]
        )

        if not result.get("success"):
            return result

        cursor.execute(
            """
            INSERT INTO activity_log (
                timestamp,
                user_id,
                session_id,
                event_type,
                service_type,
                service_name,
                metadata
            )
            VALUES (%s, %s, %s, 'ADMIN_ESCALATION', 'PRIVILEGE', 'ADMIN', %s)
            """,
            (
                timestamp,
                admin["user_id"],
                session_id,
                "admin privilege granted"
            )
        )

        conn.commit()

        return result

    except mysql.connector.Error as err:
        if conn:
            conn.rollback()
        return {"success": False, "error": "DATABASE_ERROR", "detail": str(err)}

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def escalate_superadmin(session_id: str, superadmin_password: str) -> dict:
    conn = None
    cursor = None

    try:
        conn = privilege_get()
        cursor = conn.cursor(dictionary=True)

        query = """
            SELECT
                portal_sessions.user_id,
                portal_sessions.session_id,
                portal_sessions.state,
                users.role,
                service.service_type,
                service.service_name,
                superadmin_credentials.superadmin_password_hash
            FROM portal_sessions
            JOIN users
                ON portal_sessions.user_id = users.id
            JOIN superadmin_credentials
                ON users.id = superadmin_credentials.user_id
            LEFT JOIN service
                ON portal_sessions.session_id = service.session_id
            WHERE portal_sessions.session_id = %s
        """

        cursor.execute(query, (session_id,))
        superadmin = cursor.fetchone()

        if superadmin is None:
            return {"success": False, "error": "NOT_AUTHENTICATED"}

        if superadmin["state"] != "ACTIVE":
            return {"success": False, "error": "ACCESS_DENIED"}

        if superadmin["role"] != "SUPERADMIN":
            return {"success": False, "error": "ACCESS_DENIED"}

        if (
            superadmin["service_type"] != "PRIVILEGE"
            or superadmin["service_name"] != "ADMIN"
        ):
            return {"success": False, "error": "ADMIN_PRIVILEGE_REQUIRED"}

        if superadmin["superadmin_password_hash"] is None:
            return {"success": False, "error": "SUPERADMIN_CREDENTIAL_NOT_SET"}

        if not verify_pass(
            superadmin_password,
            superadmin["superadmin_password_hash"]
        ):
            return {"success": False, "error": "ACCESS_DENIED"}

        clear_admin_service = """
            DELETE FROM service
            WHERE session_id = %s
            AND service_type = 'PRIVILEGE'
            AND service_name = 'ADMIN'
        """

        cursor.execute(clear_admin_service, (session_id,))
        conn.commit()

        return grant_service(
            session_id=session_id,
            service_type="PRIVILEGE",
            service_name="BACKEND",
            user_role=superadmin["role"]
        )

    except mysql.connector.Error as err:
        if conn:
            conn.rollback()
        return {"success": False, "error": "DATABASE_ERROR", "detail": str(err)}

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def has_admin_privilege(actor: dict) -> bool:
    return (
        actor["role"] in ("ADMIN", "SUPERADMIN")
        and actor["service_type"] == "PRIVILEGE"
        and actor["service_name"] == "ADMIN"
    )


def has_backend_privilege(actor: dict) -> bool:
    return (
        actor["role"] == "SUPERADMIN"
        and actor["service_type"] == "PRIVILEGE"
        and actor["service_name"] == "BACKEND"
    )


def peek_sessions(admin_session_id: str) -> dict:
    conn = None
    cursor = None

    try:
        conn = get()
        cursor = conn.cursor(dictionary=True)

        admin, error = _get_admin(cursor, admin_session_id)

        if error is not None:
            return error

        query = """
            SELECT
                portal_sessions.user_id,
                users.username,
                users.role,
                portal_sessions.session_id,
                portal_sessions.created_at,
                portal_sessions.last_seen,
                portal_sessions.state
            FROM portal_sessions
            JOIN users
                ON portal_sessions.user_id = users.id
            WHERE portal_sessions.state = 'ACTIVE'
            AND portal_sessions.session_id IS NOT NULL
            AND (
                %s = 'SUPERADMIN'
                OR users.role != 'SUPERADMIN'
            )
            ORDER BY portal_sessions.last_seen DESC
        """

        cursor.execute(query, (admin["role"],))
        sessions = cursor.fetchall()

        return {
            "success": True,
            "sessions": [
                {
                    "user_id": session["user_id"],
                    "username": session["username"],
                    "role": session["role"],
                    "session_id": session["session_id"],
                    "created_at": str(session["created_at"]),
                    "last_seen": str(session["last_seen"]),
                    "state": session["state"]
                }
                for session in sessions
            ]
        }

    except mysql.connector.Error as err:
        return {"success": False, "error": "DATABASE_ERROR", "detail": str(err)}

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def peek_services(admin_session_id: str) -> dict:
    conn = None
    cursor = None

    try:
        conn = get()
        cursor = conn.cursor(dictionary=True)

        admin, error = _get_admin(cursor, admin_session_id)

        if error is not None:
            return error

        query = """
            SELECT
                portal_sessions.user_id,
                users.username,
                users.role,
                service.session_id,
                service.service_type,
                service.service_name,
                service.issued_at,
                service.expires_at
            FROM service
            JOIN portal_sessions
                ON service.session_id = portal_sessions.session_id
            JOIN users
                ON portal_sessions.user_id = users.id
            WHERE portal_sessions.state = 'ACTIVE'
            AND (
                %s = 'SUPERADMIN'
                OR users.role != 'SUPERADMIN'
            )
            ORDER BY service.expires_at ASC
        """

        cursor.execute(query, (admin["role"],))
        services = cursor.fetchall()

        return {
            "success": True,
            "services": [
                {
                    "user_id": service["user_id"],
                    "username": service["username"],
                    "role": service["role"],
                    "session_id": service["session_id"],
                    "service_type": service["service_type"],
                    "service_name": service["service_name"],
                    "issued_at": str(service["issued_at"]),
                    "expires_at": str(service["expires_at"])
                }
                for service in services
            ]
        }

    except mysql.connector.Error as err:
        return {"success": False, "error": "DATABASE_ERROR", "detail": str(err)}

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def peek_users(admin_session_id: str) -> dict:
    conn = None
    cursor = None

    try:
        conn = get()
        cursor = conn.cursor(dictionary=True)

        admin, error = _get_admin(cursor, admin_session_id)

        if error is not None:
            return error

        query = """
            SELECT
                portal_sessions.user_id,
                users.username,
                users.role,
                portal_sessions.session_id,
                portal_sessions.created_at,
                portal_sessions.last_seen,
                portal_sessions.state,
                service.service_type,
                service.service_name,
                service.issued_at,
                service.expires_at
            FROM portal_sessions
            JOIN users
                ON portal_sessions.user_id = users.id
            LEFT JOIN service
                ON portal_sessions.session_id = service.session_id
            WHERE portal_sessions.state = 'ACTIVE'
            AND portal_sessions.session_id IS NOT NULL
            AND (
                %s = 'SUPERADMIN'
                OR users.role != 'SUPERADMIN'
            )
            ORDER BY portal_sessions.last_seen DESC
        """

        cursor.execute(query, (admin["role"],))
        users = cursor.fetchall()

        return {
            "success": True,
            "users": [
                {
                    "user_id": user["user_id"],
                    "username": user["username"],
                    "role": user["role"],
                    "session_id": user["session_id"],
                    "created_at": str(user["created_at"]),
                    "last_seen": str(user["last_seen"]),
                    "state": user["state"],
                    "service_type": user["service_type"],
                    "service_name": user["service_name"],
                    "issued_at": str(user["issued_at"]) if user["issued_at"] else None,
                    "expires_at": str(user["expires_at"]) if user["expires_at"] else None
                }
                for user in users
            ]
        }

    except mysql.connector.Error as err:
        return {"success": False, "error": "DATABASE_ERROR", "detail": str(err)}

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def peek_logs(admin_session_id: str, limit: int = 40) -> dict:
    conn = None
    cursor = None

    try:
        conn = get()
        cursor = conn.cursor(dictionary=True)

        admin, error = _get_admin(cursor, admin_session_id)

        if error is not None:
            return error

        query = """
            SELECT
                activity_log.event_id,
                activity_log.timestamp,
                activity_log.user_id,
                users.username,
                activity_log.session_id,
                activity_log.event_type,
                activity_log.service_type,
                activity_log.service_name,
                activity_log.metadata
            FROM activity_log
            JOIN users
                ON activity_log.user_id = users.id
            WHERE (
                %s = 'SUPERADMIN'
                OR users.role != 'SUPERADMIN'
            )
            ORDER BY activity_log.timestamp DESC
            LIMIT %s
        """

        cursor.execute(query, (admin["role"], limit))
        logs = cursor.fetchall()

        return {
            "success": True,
            "logs": [
                {
                    "event_id": log["event_id"],
                    "timestamp": str(log["timestamp"]),
                    "user_id": log["user_id"],
                    "username": log["username"],
                    "session_id": log["session_id"],
                    "event_type": log["event_type"],
                    "service_type": log["service_type"],
                    "service_name": log["service_name"],
                    "metadata": log["metadata"]
                }
                for log in logs
            ]
        }

    except mysql.connector.Error as err:
        return {"success": False, "error": "DATABASE_ERROR", "detail": str(err)}

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def scrutiny(admin_session_id: str, limit: int = 100) -> dict:
    conn = None
    cursor = None

    try:
        conn = get()
        cursor = conn.cursor(dictionary=True)

        admin, error = _get_admin(cursor, admin_session_id)

        if error is not None:
            return error

        query = """
            SELECT
                activity_log.event_id,
                activity_log.timestamp,
                activity_log.user_id,
                users.username,
                activity_log.session_id,
                activity_log.event_type,
                activity_log.service_type,
                activity_log.service_name,
                activity_log.metadata
            FROM activity_log
            JOIN users
                ON activity_log.user_id = users.id
            WHERE (
                %s = 'SUPERADMIN'
                OR users.role != 'SUPERADMIN'
            )
            ORDER BY activity_log.timestamp DESC
            LIMIT %s
        """

        cursor.execute(query, (admin["role"], limit))
        rows = cursor.fetchall()

        return {
            "success": True,
            "events": [
                {
                    "event_id": row["event_id"],
                    "timestamp": str(row["timestamp"]),
                    "user_id": row["user_id"],
                    "username": row["username"],
                    "session_id": row["session_id"],
                    "event_type": row["event_type"],
                    "service_type": row["service_type"],
                    "service_name": row["service_name"],
                    "metadata": row["metadata"]
                }
                for row in rows
            ]
        }

    except mysql.connector.Error as err:
        return {"success": False, "error": "DATABASE_ERROR", "detail": str(err)}

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def kill_service(admin_session_id: str, target_session_id: str) -> dict:
    conn = None
    cursor = None

    try:
        conn = get()
        cursor = conn.cursor(dictionary=True)
        timestamp = utc_now()

        actor, error = _get_actor(cursor, admin_session_id)

        if error is not None:
            return error

        if not has_admin_privilege(actor):
            return {"success": False, "error": "ACCESS_DENIED"}

        metadata = admin_metadata(actor)

        target_query = """
            SELECT
                portal_sessions.user_id,
                users.username,
                users.role,
                service.session_id,
                service.service_type,
                service.service_name
            FROM service
            JOIN portal_sessions
                ON service.session_id = portal_sessions.session_id
            JOIN users
                ON portal_sessions.user_id = users.id
            WHERE service.session_id = %s
        """

        cursor.execute(target_query, (target_session_id,))
        target = cursor.fetchone()

        if target is None:
            return {"success": False, "error": "NO_ACTIVE_SERVICE"}

        if target["role"] == "SUPERADMIN":
            return {"success": False, "error": "ACCESS_DENIED"}

        cursor.execute(
            """
            INSERT INTO activity_log (
                timestamp,
                user_id,
                session_id,
                event_type,
                service_type,
                service_name,
                metadata
            )
            VALUES (%s, %s, %s, 'SERVICE_EXIT', %s, %s, %s)
            """,
            (
                timestamp,
                target["user_id"],
                target_session_id,
                target["service_type"],
                target["service_name"],
                metadata
            )
        )

        cursor.execute(
            """
            INSERT INTO activity_log (
                timestamp,
                user_id,
                session_id,
                event_type,
                service_type,
                service_name,
                metadata
            )
            VALUES (%s, %s, %s, 'KILL_SERVICE', 'PRIVILEGE', 'ADMIN', %s)
            """,
            (
                timestamp,
                actor["user_id"],
                admin_session_id,
                metadata
            )
        )

        cursor.execute(
            """
            DELETE FROM service
            WHERE session_id = %s
            """,
            (target_session_id,)
        )

        cursor.execute(
            """
            UPDATE portal_sessions
            SET last_seen = %s
            WHERE session_id = %s
            """,
            (timestamp, target_session_id)
        )

        conn.commit()

        return {
            "success": True,
            "result": "KILL_SERVICE_SUCCESS",
            "target_session_id": target_session_id,
            "service_type": target["service_type"],
            "service_name": target["service_name"]
        }

    except mysql.connector.Error as err:
        if conn:
            conn.rollback()
        return {"success": False, "error": "DATABASE_ERROR", "detail": str(err)}

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def kill_user(admin_session_id: str, target_session_id: str) -> dict:
    conn = None
    cursor = None

    try:
        conn = get()
        cursor = conn.cursor(dictionary=True)
        timestamp = utc_now()

        actor, error = _get_actor(cursor, admin_session_id)

        if error is not None:
            return error

        if not has_admin_privilege(actor):
            return {"success": False, "error": "ACCESS_DENIED"}

        metadata = admin_metadata(actor)

        target_query = """
            SELECT
                portal_sessions.user_id,
                users.username,
                users.role,
                portal_sessions.session_id,
                portal_sessions.state
            FROM portal_sessions
            JOIN users
                ON portal_sessions.user_id = users.id
            WHERE portal_sessions.session_id = %s
        """

        cursor.execute(target_query, (target_session_id,))
        target = cursor.fetchone()

        if target is None:
            return {"success": False, "error": "TARGET_NOT_AUTHENTICATED"}

        if target["state"] != "ACTIVE":
            return {"success": False, "error": "TARGET_NOT_ACTIVE"}

        if target["role"] == "SUPERADMIN":
            return {"success": False, "error": "ACCESS_DENIED"}

        service_query = """
            SELECT service_type, service_name
            FROM service
            WHERE session_id = %s
        """

        cursor.execute(service_query, (target_session_id,))
        active_service = cursor.fetchone()

        if active_service is not None:
            cursor.execute(
                """
                INSERT INTO activity_log (
                    timestamp,
                    user_id,
                    session_id,
                    event_type,
                    service_type,
                    service_name,
                    metadata
                )
                VALUES (%s, %s, %s, 'SERVICE_EXIT', %s, %s, %s)
                """,
                (
                    timestamp,
                    target["user_id"],
                    target_session_id,
                    active_service["service_type"],
                    active_service["service_name"],
                    metadata
                )
            )

            cursor.execute(
                """
                DELETE FROM service
                WHERE session_id = %s
                """,
                (target_session_id,)
            )

        cursor.execute(
            """
            INSERT INTO activity_log (
                timestamp,
                user_id,
                session_id,
                event_type,
                metadata
            )
            VALUES (%s, %s, %s, 'KILL_USER', %s)
            """,
            (
                timestamp,
                actor["user_id"],
                admin_session_id,
                metadata
            )
        )

        cursor.execute(
            """
            INSERT INTO activity_log (
                timestamp,
                user_id,
                session_id,
                event_type,
                metadata
            )
            VALUES (%s, %s, %s, 'FORCED_LOGOUT', %s)
            """,
            (
                timestamp,
                target["user_id"],
                target_session_id,
                metadata
            )
        )

        cursor.execute(
            """
            UPDATE portal_sessions
            SET
                session_id = NULL,
                last_seen = %s,
                state = 'LOGGED_OUT'
            WHERE user_id = %s
            """,
            (
                timestamp,
                target["user_id"]
            )
        )

        conn.commit()

        return {
            "success": True,
            "result": "KILL_USER_SUCCESS",
            "target_user_id": target["user_id"],
            "target_username": target["username"]
        }

    except mysql.connector.Error as err:
        if conn:
            conn.rollback()
        return {"success": False, "error": "DATABASE_ERROR", "detail": str(err)}

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def hammer(admin_session_id: str, target_user_id: int) -> dict:
    conn = None
    cursor = None

    try:
        conn = get()
        cursor = conn.cursor(dictionary=True)
        timestamp = utc_now()

        actor, error = _get_actor(cursor, admin_session_id)

        if error is not None:
            return error

        metadata = admin_metadata(actor)

        target_query = """
            SELECT id, username, role, enabled
            FROM users
            WHERE id = %s
        """

        cursor.execute(target_query, (target_user_id,))
        target = cursor.fetchone()

        if target is None:
            return {"success": False, "error": "TARGET_USER_NOT_FOUND"}

        if target["role"] == "SUPERADMIN":
            return {"success": False, "error": "ACCESS_DENIED"}

        if target["role"] == "USER":
            if not has_admin_privilege(actor):
                return {"success": False, "error": "ACCESS_DENIED"}

        elif target["role"] == "ADMIN":
            if not has_backend_privilege(actor):
                return {"success": False, "error": "ACCESS_DENIED"}

        else:
            return {"success": False, "error": "INVALID_TARGET_ROLE"}

        cursor.execute(
            """
            UPDATE users
            SET enabled = FALSE
            WHERE id = %s
            """,
            (target_user_id,)
        )

        cursor.execute(
            """
            INSERT INTO activity_log (
                timestamp,
                user_id,
                session_id,
                event_type,
                metadata
            )
            VALUES (%s, %s, %s, 'HAMMER', %s)
            """,
            (
                timestamp,
                actor["user_id"],
                admin_session_id,
                metadata
            )
        )

        session_query = """
            SELECT session_id
            FROM portal_sessions
            WHERE user_id = %s
            AND session_id IS NOT NULL
        """

        cursor.execute(session_query, (target_user_id,))
        target_session = cursor.fetchone()

        if target_session is not None:
            target_session_id = target_session["session_id"]

            service_query = """
                SELECT service_type, service_name
                FROM service
                WHERE session_id = %s
            """

            cursor.execute(service_query, (target_session_id,))
            active_service = cursor.fetchone()

            if active_service is not None:
                cursor.execute(
                    """
                    INSERT INTO activity_log (
                        timestamp,
                        user_id,
                        session_id,
                        event_type,
                        service_type,
                        service_name,
                        metadata
                    )
                    VALUES (%s, %s, %s, 'SERVICE_EXIT', %s, %s, %s)
                    """,
                    (
                        timestamp,
                        target["id"],
                        target_session_id,
                        active_service["service_type"],
                        active_service["service_name"],
                        metadata
                    )
                )

                cursor.execute(
                    """
                    DELETE FROM service
                    WHERE session_id = %s
                    """,
                    (target_session_id,)
                )

            cursor.execute(
                """
                INSERT INTO activity_log (
                    timestamp,
                    user_id,
                    session_id,
                    event_type,
                    metadata
                )
                VALUES (%s, %s, %s, 'FORCED_LOGOUT', %s)
                """,
                (
                    timestamp,
                    target["id"],
                    target_session_id,
                    metadata
                )
            )

            cursor.execute(
                """
                UPDATE portal_sessions
                SET
                    session_id = NULL,
                    last_seen = %s,
                    state = 'LOGGED_OUT'
                WHERE user_id = %s
                """,
                (
                    timestamp,
                    target["id"]
                )
            )

        conn.commit()

        return {
            "success": True,
            "result": "HAMMER_SUCCESS",
            "target_user_id": target["id"],
            "target_username": target["username"]
        }

    except mysql.connector.Error as err:
        if conn:
            conn.rollback()
        return {"success": False, "error": "DATABASE_ERROR", "detail": str(err)}

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def greenlight(admin_session_id: str, target_user_id: int) -> dict:
    conn = None
    cursor = None

    try:
        conn = get()
        cursor = conn.cursor(dictionary=True)
        timestamp = utc_now()

        actor, error = _get_actor(cursor, admin_session_id)

        if error is not None:
            return error

        metadata = admin_metadata(actor)

        target_query = """
            SELECT id, username, role, enabled
            FROM users
            WHERE id = %s
        """

        cursor.execute(target_query, (target_user_id,))
        target = cursor.fetchone()

        if target is None:
            return {"success": False, "error": "TARGET_USER_NOT_FOUND"}

        if target["role"] == "USER" and not has_admin_privilege(actor):
            return {"success": False, "error": "ACCESS_DENIED"}

        if target["role"] in ("ADMIN", "SUPERADMIN") and not has_backend_privilege(actor):
            return {"success": False, "error": "ACCESS_DENIED"}

        cursor.execute(
            """
            UPDATE users
            SET enabled = TRUE
            WHERE id = %s
            """,
            (target_user_id,)
        )

        cursor.execute(
            """
            INSERT INTO activity_log (
                timestamp,
                user_id,
                session_id,
                event_type,
                metadata
            )
            VALUES (%s, %s, %s, 'GREENLIGHT', %s)
            """,
            (
                timestamp,
                actor["user_id"],
                admin_session_id,
                metadata
            )
        )

        conn.commit()

        return {
            "success": True,
            "result": "GREENLIGHT_SUCCESS",
            "target_user_id": target["id"],
            "target_username": target["username"]
        }

    except mysql.connector.Error as err:
        if conn:
            conn.rollback()
        return {"success": False, "error": "DATABASE_ERROR", "detail": str(err)}

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def promote(admin_session_id: str, target_user_id: int) -> dict:
    conn = None
    cursor = None

    try:
        conn = get()
        cursor = conn.cursor(dictionary=True)
        timestamp = utc_now()

        actor, error = _get_actor(cursor, admin_session_id)

        if error is not None:
            return error

        if not has_backend_privilege(actor):
            return {"success": False, "error": "ACCESS_DENIED"}

        metadata = admin_metadata(actor)

        cursor.execute(
            """
            SELECT id, username, role
            FROM users
            WHERE id = %s
            """,
            (target_user_id,)
        )

        target = cursor.fetchone()

        if target is None:
            return {"success": False, "error": "TARGET_USER_NOT_FOUND"}

        if target["role"] != "USER":
            return {"success": False, "error": "INVALID_TARGET_ROLE"}

        cursor.execute(
            """
            UPDATE users
            SET role = 'ADMIN'
            WHERE id = %s
            """,
            (target_user_id,)
        )

        cursor.execute(
            """
            INSERT INTO activity_log (
                timestamp,
                user_id,
                session_id,
                event_type,
                metadata
            )
            VALUES (%s, %s, %s, 'PROMOTE', %s)
            """,
            (
                timestamp,
                actor["user_id"],
                admin_session_id,
                metadata
            )
        )

        conn.commit()

        return {
            "success": True,
            "result": "PROMOTE_SUCCESS",
            "target_user_id": target["id"],
            "target_username": target["username"]
        }

    except mysql.connector.Error as err:
        if conn:
            conn.rollback()
        return {"success": False, "error": "DATABASE_ERROR", "detail": str(err)}

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def demote(admin_session_id: str, target_user_id: int) -> dict:
    conn = None
    cursor = None

    try:
        conn = get()
        cursor = conn.cursor(dictionary=True)
        timestamp = utc_now()

        actor, error = _get_actor(cursor, admin_session_id)

        if error is not None:
            return error

        if not has_backend_privilege(actor):
            return {"success": False, "error": "ACCESS_DENIED"}

        metadata = admin_metadata(actor)

        cursor.execute(
            """
            SELECT id, username, role
            FROM users
            WHERE id = %s
            """,
            (target_user_id,)
        )

        target = cursor.fetchone()

        if target is None:
            return {"success": False, "error": "TARGET_USER_NOT_FOUND"}

        if target["role"] != "ADMIN":
            return {"success": False, "error": "INVALID_TARGET_ROLE"}

        cursor.execute(
            """
            UPDATE users
            SET role = 'USER'
            WHERE id = %s
            """,
            (target_user_id,)
        )

        cursor.execute(
            """
            INSERT INTO activity_log (
                timestamp,
                user_id,
                session_id,
                event_type,
                metadata
            )
            VALUES (%s, %s, %s, 'DEMOTE', %s)
            """,
            (
                timestamp,
                actor["user_id"],
                admin_session_id,
                metadata
            )
        )

        conn.commit()

        return {
            "success": True,
            "result": "DEMOTE_SUCCESS",
            "target_user_id": target["id"],
            "target_username": target["username"]
        }

    except mysql.connector.Error as err:
        if conn:
            conn.rollback()
        return {"success": False, "error": "DATABASE_ERROR", "detail": str(err)}

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()