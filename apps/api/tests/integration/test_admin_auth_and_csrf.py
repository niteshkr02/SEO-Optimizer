"""Integration tests for Admin Session Authentication, CSRF Guards, and Origin Validation."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.main import app
from app.persistence.repository import lead_repository


@pytest.fixture(autouse=True)
def clean_repo():
    lead_repository.reset()
    yield
    lead_repository.reset()


@pytest.mark.asyncio
async def test_admin_login_success_and_cookie_set():
    """Verifies that valid credentials return an authenticated session and HttpOnly cookie."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/api/v1/auth/admin/login",
            json={"username": settings.ADMIN_USERNAME, "password": settings.ADMIN_PASSWORD},
            headers={"Origin": "http://localhost:3000"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["authenticated"] is True
    assert data["username"] == settings.ADMIN_USERNAME
    assert data["role"] == "admin"
    assert data["csrf_token"] is not None

    # Verify admin_session cookie was set
    assert "admin_session" in resp.cookies
    assert resp.cookies["admin_session"] is not None


@pytest.mark.asyncio
async def test_admin_login_invalid_credentials():
    """Verifies that invalid credentials yield 401 Unauthorized."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.post(
            "/api/v1/auth/admin/login",
            json={"username": "wrong_user", "password": "wrong_password"},
        )

    assert resp.status_code == 401
    assert resp.json()["detail"]["code"] == "INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_admin_session_check_endpoint():
    """Verifies /auth/admin/session detects active cookie session vs unauthenticated."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Without cookie
        resp_no_cookie = await client.get("/api/v1/auth/admin/session")
        assert resp_no_cookie.status_code == 200
        assert resp_no_cookie.json()["authenticated"] is False

        # Login to obtain cookie
        login_resp = await client.post(
            "/api/v1/auth/admin/login",
            json={"username": settings.ADMIN_USERNAME, "password": settings.ADMIN_PASSWORD},
        )
        assert login_resp.status_code == 200

        # Check session with cookie forwarded
        resp_with_cookie = await client.get(
            "/api/v1/auth/admin/session",
            cookies=login_resp.cookies,
        )
        assert resp_with_cookie.status_code == 200
        data = resp_with_cookie.json()
        assert data["authenticated"] is True
        assert data["csrf_token"] is not None


@pytest.mark.asyncio
async def test_admin_cookie_read_access_without_api_key():
    """Verifies that a valid session cookie grants read access to /leads without requiring an API key header."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Login
        login_resp = await client.post(
            "/api/v1/auth/admin/login",
            json={"username": settings.ADMIN_USERNAME, "password": settings.ADMIN_PASSWORD},
        )
        cookies = login_resp.cookies

        # GET /leads without any X-Admin-Api-Key or Authorization header
        resp = await client.get("/api/v1/leads", cookies=cookies)
        assert resp.status_code == 200
        assert "items" in resp.json()


@pytest.mark.asyncio
async def test_csrf_protection_on_cookie_authenticated_mutations():
    """Verifies that state-changing operations require a valid X-CSRF-Token when authenticated via cookie."""
    # First, submit a test lead
    lead_payload = {
        "customerName": "Isaac Kleiner",
        "businessEmail": "isaac@kleinerlabs.org",
        "phoneNumber": "+1 555-909-1234",
        "websiteUrl": "https://kleinerlabs.org",
        "businessCategory": "Physics",
        "targetCity": "Geneva",
        "requestedService": "Architecture",
        "problemDescription": "Teleportation documentation routing loop and broken canonicals.",
        "urgency": "HIGH",
        "consentGiven": True,
    }

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        create_resp = await client.post("/api/v1/leads", json=lead_payload)
        assert create_resp.status_code == 201
        lead_id = create_resp.json()["id"]

        # Login as admin
        login_resp = await client.post(
            "/api/v1/auth/admin/login",
            json={"username": settings.ADMIN_USERNAME, "password": settings.ADMIN_PASSWORD},
            headers={"Origin": "http://localhost:3000"},
        )
        cookies = login_resp.cookies
        csrf_token = login_resp.json()["csrf_token"]

        update_payload = {
            "newStatus": "CONTACTED",
            "changedBy": "Admin Operator",
            "notes": "Initiated technical outreach.",
        }

        # 1. Mutation with cookie but MISSING X-CSRF-Token -> Must return 403 Forbidden
        bad_resp = await client.patch(
            f"/api/v1/leads/{lead_id}/status",
            json=update_payload,
            cookies=cookies,
            headers={"Origin": "http://localhost:3000"},
        )
        assert bad_resp.status_code == 403
        assert bad_resp.json()["detail"]["code"] == "CSRF_VERIFICATION_FAILED"

        # 2. Mutation with cookie and INVALID X-CSRF-Token -> Must return 403 Forbidden
        bad_token_resp = await client.patch(
            f"/api/v1/leads/{lead_id}/status",
            json=update_payload,
            cookies=cookies,
            headers={"Origin": "http://localhost:3000", "X-CSRF-Token": "invalid-tampered-token"},
        )
        assert bad_token_resp.status_code == 403
        assert bad_token_resp.json()["detail"]["code"] == "CSRF_VERIFICATION_FAILED"

        # 3. Mutation with cookie and VALID X-CSRF-Token -> Must succeed (200 OK)
        good_resp = await client.patch(
            f"/api/v1/leads/{lead_id}/status",
            json=update_payload,
            cookies=cookies,
            headers={"Origin": "http://localhost:3000", "X-CSRF-Token": csrf_token},
        )
        assert good_resp.status_code == 200
        assert good_resp.json()["status"] == "CONTACTED"


@pytest.mark.asyncio
async def test_origin_validation_guards_against_evil_origins():
    """Verifies that mutations from unauthorized CORS origins are rejected with 403 Forbidden."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Login from an unauthorized origin
        evil_resp = await client.post(
            "/api/v1/auth/admin/login",
            json={"username": settings.ADMIN_USERNAME, "password": settings.ADMIN_PASSWORD},
            headers={"Origin": "https://malicious-attacker-site.com"},
        )
        assert evil_resp.status_code == 403
        assert evil_resp.json()["detail"]["code"] == "FORBIDDEN_ORIGIN"


@pytest.mark.asyncio
async def test_admin_logout_clears_session():
    """Verifies that /auth/admin/logout deletes the admin_session cookie."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Login
        login_resp = await client.post(
            "/api/v1/auth/admin/login",
            json={"username": settings.ADMIN_USERNAME, "password": settings.ADMIN_PASSWORD},
        )
        cookies = login_resp.cookies

        # Logout
        logout_resp = await client.post(
            "/api/v1/auth/admin/logout",
            cookies=cookies,
            headers={"Origin": "http://localhost:3000"},
        )
        assert logout_resp.status_code == 200
        assert logout_resp.json()["authenticated"] is False

        # Cookie deleted/expired
        deleted_cookie = logout_resp.cookies.get("admin_session")
        assert deleted_cookie is None or deleted_cookie == '""'
