"""Authentication and session management endpoints for administrative operators."""

import secrets
import threading
import time

from fastapi import APIRouter, HTTPException, Request, Response, status
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.security import (
    create_session_token,
    generate_csrf_token,
    verify_request_origin,
    verify_session_token,
)

router = APIRouter(prefix="/auth")

# In-memory sliding window for login brute-force defense
_login_failures_lock = threading.RLock()
_login_failures: dict[str, list[float]] = {}
LOGIN_MAX_FAILURES = 5
LOGIN_WINDOW_SECONDS = 900.0  # 15 minutes lockout window


def _get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "127.0.0.1"


def check_login_rate_limit(client_ip: str) -> tuple[bool, str]:
    now = time.time()
    with _login_failures_lock:
        history = [t for t in _login_failures.get(client_ip, []) if now - t < LOGIN_WINDOW_SECONDS]
        _login_failures[client_ip] = history
        if len(history) >= LOGIN_MAX_FAILURES:
            remaining = int((LOGIN_WINDOW_SECONDS - (now - history[0])) / 60) + 1
            return False, f"Too many failed login attempts from IP {client_ip}. Please wait {remaining} minutes before retrying."
        return True, ""


def record_login_failure(client_ip: str) -> None:
    now = time.time()
    with _login_failures_lock:
        _login_failures.setdefault(client_ip, []).append(now)


def reset_login_failures(client_ip: str) -> None:
    with _login_failures_lock:
        _login_failures.pop(client_ip, None)


class AdminLoginRequest(BaseModel):
    """Admin login credentials payload."""

    username: str = Field(..., min_length=1, max_length=100, description="Administrator username")
    password: str = Field(..., min_length=1, max_length=255, description="Administrator password")


class AdminSessionResponse(BaseModel):
    """Admin session status and CSRF token response."""

    authenticated: bool
    username: str | None = None
    role: str | None = None
    csrf_token: str | None = None


@router.post(
    "/admin/login",
    response_model=AdminSessionResponse,
    status_code=status.HTTP_200_OK,
    summary="Administrator login",
    description="Authenticates admin credentials, sets an HttpOnly session cookie, and returns a CSRF token.",
)
async def admin_login(
    request: Request,
    response: Response,
    creds: AdminLoginRequest,
) -> AdminSessionResponse:
    """Authenticates admin operator and creates a secure HttpOnly session."""
    verify_request_origin(request)

    client_ip = _get_client_ip(request)

    # 1. Check brute force rate limit
    allowed, rate_msg = check_login_rate_limit(client_ip)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": "LOGIN_RATE_LIMIT_EXCEEDED",
                "message": rate_msg,
            },
        )

    # 2. Check credentials
    valid_user = secrets.compare_digest(creds.username.strip(), settings.ADMIN_USERNAME)
    valid_pass = (
        secrets.compare_digest(creds.password, settings.ADMIN_PASSWORD)
        or secrets.compare_digest(creds.password, settings.ADMIN_API_KEY)
    )

    if not (valid_user and valid_pass):
        record_login_failure(client_ip)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "INVALID_CREDENTIALS",
                "message": "Invalid administrator username or password.",
            },
        )

    # 3. Successful login - clear failed attempts for this IP
    reset_login_failures(client_ip)

    # Generate session token and bound CSRF token
    session_token = create_session_token(username=creds.username.strip(), role="admin")
    csrf_token = generate_csrf_token(session_sub=creds.username.strip())

    # Set secure HttpOnly cookie
    response.set_cookie(
        key="admin_session",
        value=session_token,
        httponly=True,
        samesite="lax",
        secure=settings.COOKIE_SECURE,
        max_age=settings.ADMIN_SESSION_TTL_SECONDS,
        path="/",
    )

    return AdminSessionResponse(
        authenticated=True,
        username=creds.username.strip(),
        role="admin",
        csrf_token=csrf_token,
    )


@router.post(
    "/admin/logout",
    response_model=AdminSessionResponse,
    status_code=status.HTTP_200_OK,
    summary="Administrator logout",
    description="Clears the HttpOnly admin session cookie.",
)
async def admin_logout(
    request: Request,
    response: Response,
) -> AdminSessionResponse:
    """Terminates active admin session and invalidates cookie."""
    verify_request_origin(request)
    response.delete_cookie(key="admin_session", path="/")
    return AdminSessionResponse(authenticated=False)


@router.get(
    "/admin/session",
    response_model=AdminSessionResponse,
    status_code=status.HTTP_200_OK,
    summary="Check administrator session",
    description="Checks whether the caller has an active, valid administrative session.",
)
async def admin_session(request: Request) -> AdminSessionResponse:
    """Verifies cookie session validity and returns CSRF token if active."""
    session_cookie = request.cookies.get("admin_session")
    if not session_cookie:
        return AdminSessionResponse(authenticated=False)

    payload = verify_session_token(session_cookie)
    if not payload:
        return AdminSessionResponse(authenticated=False)

    username = payload.get("sub", "admin")
    csrf_token = generate_csrf_token(session_sub=username)

    return AdminSessionResponse(
        authenticated=True,
        username=username,
        role=payload.get("role", "admin"),
        csrf_token=csrf_token,
    )
