import os

from Regions.region_connector import get
from API.server_service_call import request_service_validation


def files_access(session_id: str) -> dict:
    validation = request_service_validation(
        session_id=session_id,
        required_service="FILES"
    )

    if not validation.get("success"):
        return validation

    conn = None
    cursor = None

    try:
        conn = get()
        cursor = conn.cursor(dictionary=True)

        query = """
            SELECT
                storage_region.user_id,
                storage_region.volume,
                storage_region.region_root,
                storage_region.filepath,
                storage_region.user_path
            FROM storage_region
            JOIN portal_sessions
                ON storage_region.user_id = portal_sessions.user_id
            WHERE portal_sessions.session_id = %s
            AND portal_sessions.state = 'ACTIVE'
            AND storage_region.enabled = TRUE
        """

        cursor.execute(query, (session_id,))
        region = cursor.fetchone()

        if region is None:
            return {"success": False, "error": "NO_STORAGE_REGION"}

        return {
            "success": True,
            "region": "FILES",
            "user_path": region["user_path"]
        }

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def resolve_files_path(session_id: str, relative_path: str = "") -> dict:
    access = files_access(session_id)

    if not access.get("success"):
        return access

    base_path = os.path.abspath(access["user_path"])

    requested_path = os.path.abspath(
        os.path.join(base_path, relative_path)
    )

    if not requested_path.startswith(base_path):
        return {"success": False, "error": "INVALID_PATH"}

    return {
        "success": True,
        "base_path": base_path,
        "requested_path": requested_path
    }


def list_files(session_id: str) -> dict:
    path_result = resolve_files_path(session_id, "")

    if not path_result.get("success"):
        return path_result

    requested_path = path_result["requested_path"]

    if not os.path.exists(requested_path):
        return {"success": False, "error": "PATH_NOT_FOUND"}

    if not os.path.isdir(requested_path):
        return {"success": False, "error": "NOT_A_DIRECTORY"}

    entries = []

    for item in os.listdir(requested_path):
        item_path = os.path.join(requested_path, item)

        if os.path.isfile(item_path):
            entries.append({
                "name": item,
                "type": "file",
                "size": os.path.getsize(item_path)
            })

    return {
        "success": True,
        "region": "FILES",
        "path": "",
        "entries": entries
    }


def get_file_path(session_id: str, filename: str) -> dict:
    safe_filename = os.path.basename(filename)

    if safe_filename != filename:
        return {"success": False, "error": "INVALID_FILENAME"}

    path_result = resolve_files_path(session_id, safe_filename)

    if not path_result.get("success"):
        return path_result

    requested_path = path_result["requested_path"]

    if not os.path.exists(requested_path):
        return {"success": False, "error": "FILE_NOT_FOUND"}

    if not os.path.isfile(requested_path):
        return {"success": False, "error": "NOT_A_FILE"}

    return {
        "success": True,
        "file_path": requested_path,
        "filename": safe_filename
    }


def save_uploaded_file(session_id: str, filename: str, file_data) -> dict:
    safe_filename = os.path.basename(filename)

    if safe_filename != filename:
        return {"success": False, "error": "INVALID_FILENAME"}

    folder_result = resolve_files_path(session_id, "")

    if not folder_result.get("success"):
        return folder_result

    target_folder = folder_result["requested_path"]

    if not os.path.exists(target_folder):
        return {"success": False, "error": "TARGET_FOLDER_NOT_FOUND"}

    if not os.path.isdir(target_folder):
        return {"success": False, "error": "TARGET_NOT_A_DIRECTORY"}

    target_file = os.path.abspath(
        os.path.join(target_folder, safe_filename)
    )

    base_path = folder_result["base_path"]

    if not target_file.startswith(base_path):
        return {"success": False, "error": "INVALID_PATH"}

    with open(target_file, "wb") as output_file:
        output_file.write(file_data)

    return {
        "success": True,
        "result": "UPLOAD_SUCCESS",
        "filename": safe_filename,
        "path": os.path.relpath(target_file, base_path)
    }


def delete_file(session_id: str, filename: str) -> dict:
    safe_filename = os.path.basename(filename)

    if safe_filename != filename:
        return {"success": False, "error": "INVALID_FILENAME"}

    path_result = resolve_files_path(session_id, safe_filename)

    if not path_result.get("success"):
        return path_result

    target_file = path_result["requested_path"]

    if not os.path.exists(target_file):
        return {"success": False, "error": "FILE_NOT_FOUND"}

    if not os.path.isfile(target_file):
        return {"success": False, "error": "NOT_A_FILE"}

    os.remove(target_file)

    return {
        "success": True,
        "result": "FILE_DELETED",
        "filename": safe_filename
    }