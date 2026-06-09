from Daemons.server_service_daemon import (
    grant_service,
    clear_service,
    validate_service,
    service_status
)


def request_service_scope(
    session_id: str,
    service_type: str,
    service_name: str,
    user_role: str
):
    return grant_service(
        session_id=session_id,
        service_type=service_type,
        service_name=service_name,
        user_role=user_role
    )


def request_clear_service(session_id: str):
    return clear_service(session_id=session_id)


def request_service_validation(session_id: str, required_service: str):
    return validate_service(
        session_id=session_id,
        required_service=required_service
    )


def request_service_status(session_id: str):
    return service_status(session_id=session_id)