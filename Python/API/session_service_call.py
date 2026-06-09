from Daemons.session_service_daemon import (
    portal_session_create,
    portal_session_validate,
    portal_session_end,
    portal_session_status
)


def request_portal_session(user_id: int, ip: str | None = None, device: str | None = None):
    return portal_session_create(user_id=user_id, ip=ip, device=device)


def request_portal_validation(session_id: str):
    return portal_session_validate(session_id=session_id)


def request_portal_logout(session_id: str):
    return portal_session_end(session_id=session_id)


def request_portal_status(session_id: str):
    return portal_session_status(session_id=session_id)