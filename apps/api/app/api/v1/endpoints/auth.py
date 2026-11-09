"""Authentication and session management endpoints for administrative operators."""

import secrets

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

    # Check username matching
    valid_user = secrets.compare_digest(creds.username.strip(), settings.ADMIN_USERNAME)

    # Check password against ADMIN_PASSWORD or ADMIN_API_KEY
    valid_pass = (
        secrets.compare_digest(creds.password, settings.ADMIN_PASSWORD)
        or secrets.compare_digest(creds.password, settings.ADMIN_API_KEY)
    )

    if not (valid_user and valid_pass):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "INVALID_CREDENTIALS",
                "message": "Invalid administrator username or password.",
            },
        )

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
