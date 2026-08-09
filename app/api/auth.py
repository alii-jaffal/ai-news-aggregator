import base64
import hashlib
import hmac
import json

from fastapi import HTTPException, Request, Response, status

from app.settings import settings

DASHBOARD_SESSION_COOKIE = "ai_news_dashboard_session"
DASHBOARD_SESSION_MAX_AGE = 60 * 60 * 8


def get_dashboard_allowed_origins() -> list[str]:
    return [
        origin.strip()
        for origin in settings.DASHBOARD_ALLOWED_ORIGINS.split(",")
        if origin.strip()
    ]


def get_dashboard_allowed_origin_regex() -> str | None:
    regex = settings.DASHBOARD_ALLOWED_ORIGIN_REGEX.strip()
    return regex or None


def build_dashboard_session_payload() -> dict[str, str]:
    return {"username": settings.DASHBOARD_ADMIN_USERNAME}


def authenticate_dashboard_admin(username: str, password: str) -> bool:
    return hmac.compare_digest(username, settings.DASHBOARD_ADMIN_USERNAME) and hmac.compare_digest(
        password,
        settings.DASHBOARD_ADMIN_PASSWORD,
    )


def _sign_dashboard_session(data: str) -> str:
    return hmac.new(
        settings.DASHBOARD_SESSION_SECRET.encode("utf-8"),
        data.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _encode_dashboard_session(payload: dict[str, str]) -> str:
    raw_payload = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    encoded_payload = base64.urlsafe_b64encode(raw_payload).decode("utf-8")
    signature = _sign_dashboard_session(encoded_payload)
    return f"{encoded_payload}.{signature}"


def _decode_dashboard_session(cookie_value: str) -> dict[str, str] | None:
    try:
        encoded_payload, signature = cookie_value.rsplit(".", 1)
    except ValueError:
        return None

    expected_signature = _sign_dashboard_session(encoded_payload)
    if not hmac.compare_digest(signature, expected_signature):
        return None

    try:
        raw_payload = base64.urlsafe_b64decode(encoded_payload.encode("utf-8"))
        payload = json.loads(raw_payload.decode("utf-8"))
    except (ValueError, json.JSONDecodeError):
        return None

    if not isinstance(payload, dict):
        return None

    username = payload.get("username")
    if not isinstance(username, str) or not username:
        return None

    return {"username": username}


def set_dashboard_session(response: Response, payload: dict[str, str]) -> None:
    response.set_cookie(
        key=DASHBOARD_SESSION_COOKIE,
        value=_encode_dashboard_session(payload),
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=DASHBOARD_SESSION_MAX_AGE,
    )


def clear_dashboard_session(response: Response) -> None:
    response.delete_cookie(DASHBOARD_SESSION_COOKIE)


def get_dashboard_session(request: Request) -> dict[str, str] | None:
    cookie_value = request.cookies.get(DASHBOARD_SESSION_COOKIE)
    if not cookie_value:
        return None
    return _decode_dashboard_session(cookie_value)


def require_dashboard_admin(request: Request) -> dict[str, str]:
    session = get_dashboard_session(request)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Dashboard authentication required",
        )
    return session
