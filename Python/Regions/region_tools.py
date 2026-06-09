import mysql.connector
import os
from Regions.region_tools_connector import get


def get_users() -> dict:
    conn = None
    cursor = None

    try:
        conn = get()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                id,
                username,
                firstname,
                role,
                enabled
            FROM users
            ORDER BY username ASC
            """
        )

        users = cursor.fetchall()

        return {
            "success": True,
            "users": [
                {
                    "user_id": user["id"],
                    "username": user["username"],
                    "firstname": user["firstname"],
                    "role": user["role"],
                    "enabled": bool(user["enabled"])
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


def create_storage_assignment(
    username: str,
    volume: str,
    region_root: str,
    filepath: str
) -> dict:
    conn = None
    cursor = None

    try:
        conn = get()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT id, username
            FROM users
            WHERE username = %s
            """,
            (username,)
        )

        user = cursor.fetchone()

        if user is None:
            return {"success": False, "error": "USER_NOT_FOUND"}

        cursor.execute(
            """
            INSERT INTO storage_region (
                user_id,
                volume,
                region_root,
                filepath,
                enabled
            )
            VALUES (%s, %s, %s, %s, TRUE)
            ON DUPLICATE KEY UPDATE
                volume = VALUES(volume),
                region_root = VALUES(region_root),
                filepath = VALUES(filepath),
                enabled = TRUE
            """,
            (
                user["id"],
                volume,
                region_root,
                filepath
            )
        )

        conn.commit()

        cursor.execute(
            """
            SELECT
                storage_id,
                user_id,
                volume,
                region_root,
                filepath,
                user_path,
                enabled
            FROM storage_region
            WHERE user_id = %s
            """,
            (user["id"],)
        )

        assignment = cursor.fetchone()

        return {
            "success": True,
            "result": "STORAGE_ASSIGNMENT_CREATED",
            "assignment": assignment
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


def view_storage_assignments() -> dict:
    conn = None
    cursor = None

    try:
        conn = get()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                storage_region.storage_id,
                storage_region.user_id,
                users.username,
                storage_region.volume,
                storage_region.region_root,
                storage_region.filepath,
                storage_region.user_path,
                storage_region.enabled,
                storage_region.created_at,
                storage_region.updated_at
            FROM storage_region
            JOIN users
                ON storage_region.user_id = users.id
            ORDER BY users.username ASC
            """
        )

        rows = cursor.fetchall()

        return {
            "success": True,
            "assignments": [
                {
                    "storage_id": row["storage_id"],
                    "user_id": row["user_id"],
                    "username": row["username"],
                    "volume": row["volume"],
                    "region_root": row["region_root"],
                    "filepath": row["filepath"],
                    "user_path": row["user_path"],
                    "enabled": bool(row["enabled"]),
                    "created_at": str(row["created_at"]),
                    "updated_at": str(row["updated_at"])
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


def set_storage_enabled(username: str, enabled: bool) -> dict:
    conn = None
    cursor = None

    try:
        conn = get()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT id, username
            FROM users
            WHERE username = %s
            """,
            (username,)
        )

        user = cursor.fetchone()

        if user is None:
            return {"success": False, "error": "USER_NOT_FOUND"}

        cursor.execute(
            """
            UPDATE storage_region
            SET enabled = %s
            WHERE user_id = %s
            """,
            (enabled, user["id"])
        )

        if cursor.rowcount == 0:
            conn.rollback()
            return {"success": False, "error": "STORAGE_ASSIGNMENT_NOT_FOUND"}

        conn.commit()

        return {
            "success": True,
            "result": "STORAGE_ENABLED_UPDATED",
            "username": username,
            "enabled": enabled
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


def update_storage_assignment(
    username: str,
    volume: str,
    region_root: str,
    filepath: str
) -> dict:
    conn = None
    cursor = None

    try:
        conn = get()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT id, username
            FROM users
            WHERE username = %s
            """,
            (username,)
        )

        user = cursor.fetchone()

        if user is None:
            return {"success": False, "error": "USER_NOT_FOUND"}

        cursor.execute(
            """
            UPDATE storage_region
            SET
                volume = %s,
                region_root = %s,
                filepath = %s
            WHERE user_id = %s
            """,
            (
                volume,
                region_root,
                filepath,
                user["id"]
            )
        )

        if cursor.rowcount == 0:
            conn.rollback()
            return {"success": False, "error": "STORAGE_ASSIGNMENT_NOT_FOUND"}

        conn.commit()

        cursor.execute(
            """
            SELECT
                storage_id,
                user_id,
                volume,
                region_root,
                filepath,
                user_path,
                enabled
            FROM storage_region
            WHERE user_id = %s
            """,
            (user["id"],)
        )

        assignment = cursor.fetchone()

        return {
            "success": True,
            "result": "STORAGE_ASSIGNMENT_UPDATED",
            "assignment": assignment
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


def create_user_storage_directory(username: str) -> dict:
    conn = None
    cursor = None

    try:
        conn = get()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                storage_region.user_path
            FROM storage_region
            JOIN users
                ON storage_region.user_id = users.id
            WHERE users.username = %s
            """,
            (username,)
        )

        storage = cursor.fetchone()

        if storage is None:
            return {"success": False, "error": "STORAGE_ASSIGNMENT_NOT_FOUND"}

        os.makedirs(storage["user_path"], exist_ok=True)

        return {
            "success": True,
            "result": "DIRECTORY_READY",
            "user_path": storage["user_path"]
        }

    except OSError as err:
        return {"success": False, "error": "DIRECTORY_ERROR", "detail": str(err)}

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def list_user_storage_directory(username: str) -> dict:
    conn = None
    cursor = None

    try:
        conn = get()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                storage_region.user_path
            FROM storage_region
            JOIN users
                ON storage_region.user_id = users.id
            WHERE users.username = %s
            """
            ,
            (username,)
        )

        storage = cursor.fetchone()

        if storage is None:
            return {"success": False, "error": "STORAGE_ASSIGNMENT_NOT_FOUND"}

        user_path = storage["user_path"]

        if not os.path.exists(user_path):
            return {"success": False, "error": "DIRECTORY_NOT_FOUND"}

        if not os.path.isdir(user_path):
            return {"success": False, "error": "NOT_A_DIRECTORY"}

        entries = []

        for entry in os.listdir(user_path):
            entry_path = os.path.join(user_path, entry)

            entries.append({
                "name": entry,
                "type": "folder" if os.path.isdir(entry_path) else "file",
                "size": os.path.getsize(entry_path) if os.path.isfile(entry_path) else None
            })

        return {
            "success": True,
            "user_path": user_path,
            "entries": entries
        }

    except OSError as err:
        return {"success": False, "error": "DIRECTORY_ERROR", "detail": str(err)}

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()