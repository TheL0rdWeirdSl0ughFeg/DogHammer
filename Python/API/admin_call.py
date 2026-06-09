from Daemons.admin_daemon import (
    peek_sessions,
    peek_services,
    peek_users,
    peek_logs,
    kill_service,
    kill_user,
    hammer,
    greenlight,
    promote,
    demote,
    scrutiny
)


def call_peek_sessions(admin_session_id: str) -> dict:
    return peek_sessions(admin_session_id=admin_session_id)


def call_peek_services(admin_session_id: str) -> dict:
    return peek_services(admin_session_id=admin_session_id)


def call_peek_users(admin_session_id: str) -> dict:
    return peek_users(admin_session_id=admin_session_id)


def call_peek_logs(admin_session_id: str, limit: int = 40) -> dict:
    return peek_logs(admin_session_id=admin_session_id, limit=limit)


def call_kill_service(admin_session_id: str, target_session_id: str) -> dict:
    return kill_service(
        admin_session_id=admin_session_id,
        target_session_id=target_session_id
    )


def call_kill_user(admin_session_id: str, target_session_id: str) -> dict:
    return kill_user(
        admin_session_id=admin_session_id,
        target_session_id=target_session_id
    )


def hammer_down(admin_session_id: str, target_user_id: int) -> dict:
    return hammer(
        admin_session_id=admin_session_id,
        target_user_id=target_user_id
    )


def give_greenlight(admin_session_id: str, target_user_id: int) -> dict:
    return greenlight(
        admin_session_id=admin_session_id,
        target_user_id=target_user_id
    )


def promotion(admin_session_id: str, target_user_id: int) -> dict:
    return promote(
        admin_session_id=admin_session_id,
        target_user_id=target_user_id
    )


def demotion(admin_session_id: str, target_user_id: int) -> dict:
    return demote(
        admin_session_id=admin_session_id,
        target_user_id=target_user_id
    )


def request_scrutiny(admin_session_id: str, limit: int = 100) -> dict:
    return scrutiny(admin_session_id=admin_session_id, limit=limit)