from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.responses import FileResponse
from pydantic import BaseModel

from API.user_auth import authenticate_user
from API.session_service_call import (
    request_portal_session,
    request_portal_validation,
    request_portal_logout,
    request_portal_status
)
from API.server_service_call import (
    request_service_scope,
    request_clear_service,
    request_service_validation,
    request_service_status
)
from API.admin_call import (
    call_peek_sessions,
    call_peek_services,
    call_peek_users,
    call_peek_logs,
    call_kill_service,
    call_kill_user,
    hammer_down,
    give_greenlight,
    promotion,
    demotion,
    request_scrutiny
)
from Daemons.admin_daemon import (
    escalate_admin,
    escalate_superadmin
)
from Regions.region_gateway import (
    files_access,
    list_files,
    get_file_path,
    save_uploaded_file,
    delete_file
)

app = FastAPI()


class LoginRequest(BaseModel):
    username: str
    password: str


class ServiceRequest(BaseModel):
    session_id: str
    service_type: str
    service_name: str


class ClearServiceRequest(BaseModel):
    session_id: str


class ValidateServiceRequest(BaseModel):
    session_id: str
    required_service: str


class ActiveSessionRequest(BaseModel):
    session_id: str


class ActiveServiceRequest(BaseModel):
    session_id: str


class LogoutRequest(BaseModel):
    session_id: str


class AdminRequest(BaseModel):
    session_id: str


class AdminLogRequest(BaseModel):
    session_id: str
    limit: int = 40


class AdminScrutinyRequest(BaseModel):
    session_id: str
    limit: int = 100


class AdminTargetSessionRequest(BaseModel):
    session_id: str
    target_session_id: str


class AdminTargetUserRequest(BaseModel):
    session_id: str
    target_user_id: int


class RegionFilesRequest(BaseModel):
    session_id: str


class RegionFileRequest(BaseModel):
    session_id: str
    filename: str


class AdminEscalationRequest(BaseModel):
    session_id: str
    admin_password: str


class SuperadminEscalationRequest(BaseModel):
    session_id: str
    superadmin_password: str


@app.get("/")
def root():
    return {"status": "API is running"}


@app.post("/login")
def login(login_data: LoginRequest, request: Request):
    user = authenticate_user(login_data.username, login_data.password)

    if user is None:
        return {"success": False, "error": "LOGIN_FAILURE"}

    ip = request.client.host if request.client else None
    device = request.headers.get("user-agent")

    session_result = request_portal_session(
        user_id=user["id"],
        ip=ip,
        device=device
    )

    if isinstance(session_result, dict):
        return session_result

    return {
        "success": True,
        "portal_session_id": session_result,
        "role": user["role"]
    }


@app.post("/request_service")
def request_service(service_data: ServiceRequest):
    session = request_portal_validation(service_data.session_id)

    if session is None:
        return {"success": False, "error": "NOT_AUTHENTICATED"}

    return request_service_scope(
        session_id=service_data.session_id,
        service_type=service_data.service_type,
        service_name=service_data.service_name,
        user_role=session["role"]
    )


@app.post("/clear_service")
def clear_service(service_data: ClearServiceRequest):
    session = request_portal_validation(service_data.session_id)

    if session is None:
        return {"success": False, "error": "NOT_AUTHENTICATED"}

    return request_clear_service(service_data.session_id)


@app.post("/validate_service")
def validate_service(validate_data: ValidateServiceRequest):
    session = request_portal_validation(validate_data.session_id)

    if session is None:
        return {"success": False, "error": "NOT_AUTHENTICATED"}

    return request_service_validation(
        session_id=validate_data.session_id,
        required_service=validate_data.required_service
    )


@app.post("/active_session")
def active_session(session_data: ActiveSessionRequest):
    return request_portal_status(session_data.session_id)


@app.post("/active_service")
def active_service(service_data: ActiveServiceRequest):
    session = request_portal_validation(service_data.session_id)

    if session is None:
        return {"success": False, "error": "NOT_AUTHENTICATED"}

    return request_service_status(service_data.session_id)


@app.post("/admin/peek_sessions")
def admin_peek_sessions(admin_data: AdminRequest):
    return call_peek_sessions(admin_data.session_id)


@app.post("/admin/peek_services")
def admin_peek_services(admin_data: AdminRequest):
    return call_peek_services(admin_data.session_id)


@app.post("/admin/peek_users")
def admin_peek_users(admin_data: AdminRequest):
    return call_peek_users(admin_data.session_id)


@app.post("/admin/peek_logs")
def admin_peek_logs(admin_data: AdminLogRequest):
    return call_peek_logs(
        admin_session_id=admin_data.session_id,
        limit=admin_data.limit
    )


@app.post("/admin/kill_service")
def admin_kill_service(admin_data: AdminTargetSessionRequest):
    return call_kill_service(
        admin_session_id=admin_data.session_id,
        target_session_id=admin_data.target_session_id
    )


@app.post("/admin/kill_user")
def admin_kill_user(admin_data: AdminTargetSessionRequest):
    return call_kill_user(
        admin_session_id=admin_data.session_id,
        target_session_id=admin_data.target_session_id
    )


@app.post("/admin/hammer")
def admin_hammer(admin_data: AdminTargetUserRequest):
    return hammer_down(
        admin_session_id=admin_data.session_id,
        target_user_id=admin_data.target_user_id
    )


@app.post("/admin/greenlight")
def admin_greenlight(admin_data: AdminTargetUserRequest):
    return give_greenlight(
        admin_session_id=admin_data.session_id,
        target_user_id=admin_data.target_user_id
    )


@app.post("/admin/promote")
def admin_promote(admin_data: AdminTargetUserRequest):
    return promotion(
        admin_session_id=admin_data.session_id,
        target_user_id=admin_data.target_user_id
    )


@app.post("/admin/demote")
def admin_demote(admin_data: AdminTargetUserRequest):
    return demotion(
        admin_session_id=admin_data.session_id,
        target_user_id=admin_data.target_user_id
    )


@app.post("/admin/scrutiny")
def admin_scrutiny(admin_data: AdminScrutinyRequest):
    return request_scrutiny(
        admin_session_id=admin_data.session_id,
        limit=admin_data.limit
    )


@app.post("/logout")
def logout(logout_data: LogoutRequest):
    session = request_portal_validation(logout_data.session_id)

    if session is None:
        return {"success": False, "error": "NOT_AUTHENTICATED"}

    result = request_portal_logout(logout_data.session_id)

    if not result:
        return {"success": False, "error": "LOGOUT_FAILED"}

    return {"success": True, "result": "LOGOUT_SUCCESS"}


@app.post("/region/files")
def region_files(region_data: RegionFilesRequest):
    session = request_portal_validation(region_data.session_id)

    if session is None:
        return {"success": False, "error": "NOT_AUTHENTICATED"}

    return files_access(region_data.session_id)


@app.post("/region/files/list")
def region_files_list(region_data: RegionFilesRequest):
    session = request_portal_validation(region_data.session_id)

    if session is None:
        return {"success": False, "error": "NOT_AUTHENTICATED"}

    return list_files(region_data.session_id)


@app.post("/region/files/download")
def region_files_download(region_data: RegionFileRequest):
    session = request_portal_validation(region_data.session_id)

    if session is None:
        return {"success": False, "error": "NOT_AUTHENTICATED"}

    result = get_file_path(
        session_id=region_data.session_id,
        filename=region_data.filename
    )

    if not result.get("success"):
        return result

    return FileResponse(
        path=result["file_path"],
        filename=result["filename"],
        media_type="application/octet-stream"
    )


@app.post("/region/files/upload")
async def region_files_upload(
    session_id: str = Form(...),
    file: UploadFile = File(...)
):
    session = request_portal_validation(session_id)

    if session is None:
        return {"success": False, "error": "NOT_AUTHENTICATED"}

    file_data = await file.read()

    return save_uploaded_file(
        session_id=session_id,
        filename=file.filename,
        file_data=file_data
    )


@app.post("/region/files/delete")
def region_files_delete(region_data: RegionFileRequest):
    session = request_portal_validation(region_data.session_id)

    if session is None:
        return {"success": False, "error": "NOT_AUTHENTICATED"}

    return delete_file(
        session_id=region_data.session_id,
        filename=region_data.filename
    )


@app.post("/privilege/admin")
def privilege_admin(privilege_data: AdminEscalationRequest):
    session = request_portal_validation(privilege_data.session_id)

    if session is None:
        return {"success": False, "error": "NOT_AUTHENTICATED"}

    return escalate_admin(
        session_id=privilege_data.session_id,
        admin_password=privilege_data.admin_password
    )


@app.post("/privilege/superadmin")
def privilege_superadmin(privilege_data: SuperadminEscalationRequest):
    session = request_portal_validation(privilege_data.session_id)

    if session is None:
        return {"success": False, "error": "NOT_AUTHENTICATED"}

    return escalate_superadmin(
        session_id=privilege_data.session_id,
        superadmin_password=privilege_data.superadmin_password
    )