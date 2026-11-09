"""Security dependencies, session authentication, CSRF guards, and origin validation."""

import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Any
from urllib.parse import urlparse

from fastapi import Header, HTTPException, Request, status

from app.core.config import settings

# -----------------------------------------------------------------------------
# HMAC Session Token Utilities
# -----------------------------------------------------------------------------


def _b64encode_str(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _b64decode_str(s: str) -> bytes:
    padding = "=" * ((4 - len(s) % 4) % 4)
    return base64.urlsafe_b64decode(s + padding)


def create_session_token(username: str, role: str = "admin") -> str:
    """Generates a tamper-proof HMAC-SHA256 signed session token."""
    now = int(time.time())
    payload = {
        "sub": username,
        "role": role,
        "iat": now,
        "exp": now + settings.ADMIN_SESSION_TTL_SECONDS,
    }
    payload_json = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    payload_b64 = _b64encode_str(payload_json)

    sig = hmac.new(
        settings.ADMIN_SESSION_SECRET.encode("utf-8"),
        payload_b64.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    sig_b64 = _b64encode_str(sig)

    return f"{payload_b64}.{sig_b64}"


def verify_session_token(token: str) -> dict[str, Any] | None:
    """Validates signature and expiration of an admin session token."""
    try:
        parts = token.split(".")
        if len(parts) != 2:
            return None

        payload_b64, sig_b64 = parts
        expected_sig = hmac.new(
            settings.ADMIN_SESSION_SECRET.encode("utf-8"),
            payload_b64.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        provided_sig = _b64decode_str(sig_b64)

        if not secrets.compare_digest(expected_sig, provided_sig):
            return None

        payload = json.loads(_b64decode_str(payload_b64).decode("utf-8"))
        exp = int(payload.get("exp", 0))
        if time.time() > exp:
            return None

        return payload
    except (ValueError, KeyError, json.JSONDecodeError):
        return None


# -----------------------------------------------------------------------------
# CSRF Token Utilities
# -----------------------------------------------------------------------------


def generate_csrf_token(session_sub: str) -> str:
    """Generates an HMAC CSRF token bound to the current session subject."""
    salt = secrets.token_hex(8)
    ts = str(int(time.time()))
    msg = f"{session_sub}:{salt}:{ts}".encode()
    sig = hmac.new(
        settings.CSRF_SECRET.encode("utf-8"),
        msg,
        hashlib.sha256,
    ).hexdigest()
    return f"{salt}:{ts}:{sig}"


def verify_csrf_token(csrf_token: str, session_sub: str) -> bool:
    """Validates the CSRF token signature and age (< 24 hours)."""
    try:
        parts = csrf_token.split(":")
        if len(parts) != 3:
            return False

        salt, ts_str, provided_sig = parts
        ts = int(ts_str)
        # 24-hour validity window
        if abs(time.time() - ts) > 86400:
            return False

        msg = f"{session_sub}:{salt}:{ts_str}".encode()
        expected_sig = hmac.new(
            settings.CSRF_SECRET.encode("utf-8"),
            msg,
            hashlib.sha256,
        ).hexdigest()

        return secrets.compare_digest(expected_sig, provided_sig)
    except (ValueError, KeyError):
        return False


# -----------------------------------------------------------------------------
# Origin / Referer Validation
# -----------------------------------------------------------------------------


def verify_request_origin(request: Request) -> None:
    """Verifies that state-changing requests originate from an allowed CORS origin."""
    origin = request.headers.get("origin")
    if not origin:
        referer = request.headers.get("referer")
        if referer:
            parsed = urlparse(referer)
            origin = f"{parsed.scheme}://{parsed.netloc}"

    if origin:
        # Check against allowed CORS origins
        allowed = set(settings.CORS_ORIGINS)
        # Normalize trailing slashes
        clean_origin = origin.rstrip("/")
        normalized_allowed = {o.rstrip("/") for o in allowed}
        if clean_origin not in normalized_allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "FORBIDDEN_ORIGIN",
                    "message": f"Cross-origin request from '{origin}' is forbidden.",
                },
            )


# -----------------------------------------------------------------------------
# Unified Server-Side Authorization Dependency
# -----------------------------------------------------------------------------


def verify_admin_authorization(
    request: Request,
    x_admin_api_key: str | None = Header(None, alias="X-Admin-Api-Key"),
    authorization: str | None = Header(None, alias="Authorization"),
    x_csrf_token: str | None = Header(None, alias="X-CSRF-Token"),
) -> dict[str, Any]:
    """Authenticates admin access via session cookie (browser) or API key (automation).
    
    Security guarantees:
    1. Browser sessions authenticate via HttpOnly cookie with CSRF verification for mutations.
    2. Automated callers use server-to-server API key without exposing secrets to frontend.
    3. State-changing requests validate Origin / Referer against CORS whitelist.
    """
    # 1. State-changing request origin validation
    if request.method in ("POST", "PATCH", "PUT", "DELETE"):
        verify_request_origin(request)

    # 2. Check HttpOnly Session Cookie (preferred for UI)
    session_cookie = request.cookies.get("admin_session")
    if session_cookie:
        payload = verify_session_token(session_cookie)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "code": "SESSION_EXPIRED",
                    "message": "Administrative session has expired or is invalid. Please log in again.",
                },
            )

        # Enforce CSRF protection for cookie-authenticated mutations
        if request.method in (
            "POST",
            "PATCH",
            "PUT",
            "DELETE",
        ) and (not x_csrf_token or not verify_csrf_token(x_csrf_token, payload.get("sub", ""))):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "CSRF_VERIFICATION_FAILED",
                    "message": "Valid X-CSRF-Token header is required for administrative state changes.",
                },
            )

        return {"sub": payload.get("sub", "admin"), "role": payload.get("role", "admin"), "auth_type": "cookie"}

    # 3. Check Headless API Key / Bearer Token (server-to-server automation)
    provided_key: str | None = None
    if x_admin_api_key:
        provided_key = x_admin_api_key.strip()
    elif authorization:
        parts = authorization.strip().split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            provided_key = parts[1]

    if provided_key:
        if secrets.compare_digest(provided_key, settings.ADMIN_API_KEY):
            return {"sub": "api_key", "role": "admin", "auth_type": "api_key"}
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "UNAUTHORIZED",
                "message": "Access denied. Invalid administrative API key.",
            },
        )

    # 4. Deny access if neither credential is valid
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={
            "code": "UNAUTHORIZED",
            "message": "Access denied. Valid administrative authorization credentials are required.",
        },
    )


# Backward compatibility alias
verify_admin_key = verify_admin_authorization
