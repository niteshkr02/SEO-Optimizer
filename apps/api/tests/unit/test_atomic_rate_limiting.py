"""Unit and concurrency tests for atomic rate limiting, first-row creation, and anonymous access."""

import concurrent.futures
import threading
import time
import uuid

import httpx
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.persistence.in_memory import InMemoryLeadRepository
from app.persistence.sqlite import SQLiteLeadRepository
from app.persistence.supabase import SupabaseLeadRepository

# -----------------------------------------------------------------------------
# 1. First-Row Creation and Concurrency Race Hazard Tests
# -----------------------------------------------------------------------------


def test_first_row_creation_concurrency_race():
    """Verifies that 20 simultaneous threads racing for a brand-new rate key safely initialize the row.
    
    In a thread-safe / atomic implementation:
    - Exactly LEAD_RATE_LIMIT_MAX_SUBMISSIONS (5) succeed.
    - The remaining 15 are rejected.
    - Zero duplicate-key or unhandled race exceptions occur.
    """
    repo = InMemoryLeadRepository()
    test_key_ip = f"198.51.100.{uuid.uuid4().hex[:6]}"
    test_email = f"first_row_{uuid.uuid4().hex[:6]}@example.com"

    results: list[tuple[bool, str]] = []
    lock = threading.Lock()

    def worker(_: int) -> None:
        allowed, msg = repo.check_rate_limit(test_key_ip, test_email, record=True)
        with lock:
            results.append((allowed, msg))

    # Fire 20 concurrent threads at the exact same millisecond
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(worker, i) for i in range(20)]
        concurrent.futures.wait(futures)

    allowed_count = sum(1 for allowed, _ in results if allowed)
    rejected_count = sum(1 for allowed, _ in results if not allowed)

    assert len(results) == 20
    assert allowed_count == settings.LEAD_RATE_LIMIT_MAX_SUBMISSIONS  # 5 allowed
    assert rejected_count == 20 - settings.LEAD_RATE_LIMIT_MAX_SUBMISSIONS  # 15 rejected


def test_sqlite_first_row_creation_concurrency():
    """Verifies SQLite repository safely handles first-row creation under concurrency."""
    repo = SQLiteLeadRepository(db_path=f"test_concurrency_{uuid.uuid4().hex[:8]}.db")
    test_key_ip = f"203.0.113.{uuid.uuid4().hex[:6]}"
    test_email = f"sqlite_concurrency_{uuid.uuid4().hex[:6]}@example.com"

    results: list[tuple[bool, str]] = []
    lock = threading.Lock()

    def worker(_: int) -> None:
        allowed, msg = repo.check_rate_limit(test_key_ip, test_email, record=True)
        with lock:
            results.append((allowed, msg))

    with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
        futures = [executor.submit(worker, i) for i in range(15)]
        concurrent.futures.wait(futures)

    allowed_count = sum(1 for allowed, _ in results if allowed)
    rejected_count = sum(1 for allowed, _ in results if not allowed)

    assert allowed_count == settings.LEAD_RATE_LIMIT_MAX_SUBMISSIONS
    assert rejected_count == 15 - settings.LEAD_RATE_LIMIT_MAX_SUBMISSIONS


# -----------------------------------------------------------------------------
# 2. Rate-Limit Boundary and Window Expiration Tests
# -----------------------------------------------------------------------------


def test_rate_limit_exact_boundary():
    """Verifies that submissions 1-5 pass and the 6th is rejected with a descriptive message."""
    repo = InMemoryLeadRepository()
    ip = "192.0.2.55"
    email = "boundary_test@example.com"

    for i in range(5):
        allowed, msg = repo.check_rate_limit(ip, email, record=True)
        assert allowed is True, f"Submission {i + 1} should be allowed"
        assert msg == ""

    # 6th submission must be rejected
    allowed, msg = repo.check_rate_limit(ip, email, record=True)
    assert allowed is False
    assert "Too many inquiries from IP" in msg
    assert f"Limit is {settings.LEAD_RATE_LIMIT_MAX_SUBMISSIONS}" in msg


def test_inspection_mode_does_not_increment():
    """Verifies that record=False inspects rate limits without incrementing the counter."""
    repo = InMemoryLeadRepository()
    ip = "192.0.2.66"
    email = "inspection_mode@example.com"

    # Calling check_rate_limit 10 times with record=False should never decrement quota
    for _ in range(10):
        allowed, msg = repo.check_rate_limit(ip, email, record=False)
        assert allowed is True
        assert msg == ""

    # Quota is still 5 full submissions
    for _ in range(5):
        allowed, _ = repo.check_rate_limit(ip, email, record=True)
        assert allowed is True

    # 6th recorded submission is blocked
    allowed, _ = repo.check_rate_limit(ip, email, record=True)
    assert allowed is False


def test_sliding_window_expiration_boundary():
    """Verifies that expired timestamps are pruned and quota is restored after window elapses."""
    repo = InMemoryLeadRepository()
    ip = "192.0.2.77"
    email = "window_expiry@example.com"

    now = time.time()
    # Inject 5 timestamps from 15 minutes ago (window is 10 minutes = 600s)
    stale_ts = now - 900.0  # 15 minutes ago
    repo._rate_limits[f"ip:{ip}"] = [stale_ts] * 5

    # A new submission arrives now. Stale timestamps should be pruned and request allowed.
    allowed, msg = repo.check_rate_limit(ip, email, record=True)
    assert allowed is True
    assert msg == ""


# -----------------------------------------------------------------------------
# 3. PostgREST Wire Contract and RPC Fallback Tests
# -----------------------------------------------------------------------------


def test_supabase_rpc_wire_contract_check_and_record():
    """Verifies that SupabaseLeadRepository formats the check_and_record_rate_limit RPC call correctly."""
    fake_url = "https://mock-staging.supabase.co"
    fake_key = "mock-service-role-key-test"

    dispatched_requests: list[httpx.Request] = []

    def mock_transport(request: httpx.Request) -> httpx.Response:
        dispatched_requests.append(request)

        # Mock /rpc/check_and_record_rate_limit
        if "/rpc/check_and_record_rate_limit" in str(request.url):
            return httpx.Response(200, json=True)

        return httpx.Response(404, json={"message": "Not found"})

    repo = SupabaseLeadRepository(supabase_url=fake_url, service_role_key=fake_key)
    repo._client = lambda: httpx.Client(
        base_url=f"{fake_url}/rest/v1",
        headers=repo._headers,
        transport=httpx.MockTransport(mock_transport),
    )

    allowed, msg = repo.check_rate_limit("198.51.100.12", "rpc_test@example.com", record=True)
    assert allowed is True
    assert msg == ""

    # Verify dispatched requests
    rpc_calls = [r for r in dispatched_requests if "/rpc/check_and_record_rate_limit" in str(r.url)]
    assert len(rpc_calls) >= 2  # Once for IP, once for Email

    ip_call = rpc_calls[0]
    assert ip_call.method == "POST"
    assert ip_call.headers["apikey"] == fake_key
    assert ip_call.headers["Authorization"] == f"Bearer {fake_key}"
    import json

    body = json.loads(ip_call.content.decode("utf-8"))
    assert body["p_rate_key"] == "ip:198.51.100.12"
    assert body["p_max_submissions"] == settings.LEAD_RATE_LIMIT_MAX_SUBMISSIONS
    assert body["p_record"] is True
    assert "p_now" in body
    assert "p_window_seconds" in body


def test_supabase_rpc_graceful_fallback_when_rpc_missing():
    """Verifies that if the RPC returns 404 (migration 002 not yet applied), the repository falls back safely."""
    fake_url = "https://mock-staging.supabase.co"
    fake_key = "mock-service-role-key-test"

    dispatched_requests: list[httpx.Request] = []

    def mock_transport(request: httpx.Request) -> httpx.Response:
        dispatched_requests.append(request)

        # RPC returns 404 (function does not exist yet)
        if "/rpc/check_and_record_rate_limit" in str(request.url):
            return httpx.Response(404, json={"code": "PGRST202", "message": "Could not find the function"})

        # Fallback table query succeeds
        if "/rate_limits" in str(request.url):
            return httpx.Response(200, json=[])

        return httpx.Response(404, json={"message": "Not found"})

    repo = SupabaseLeadRepository(supabase_url=fake_url, service_role_key=fake_key)
    repo._client = lambda: httpx.Client(
        base_url=f"{fake_url}/rest/v1",
        headers=repo._headers,
        transport=httpx.MockTransport(mock_transport),
    )

    allowed, msg = repo.check_rate_limit("198.51.100.13", "fallback_test@example.com", record=False)
    assert allowed is True
    assert msg == ""

    # Verify fallback GET /rate_limits was called
    table_calls = [r for r in dispatched_requests if "/rate_limits" in str(r.url) and r.method == "GET"]
    assert len(table_calls) == 1


# -----------------------------------------------------------------------------
# 4. Anonymous Access and Security Mediation Tests
# -----------------------------------------------------------------------------


def test_fastapi_mediates_anonymous_inquiries():
    """Verifies that anonymous users must submit through FastAPI POST /api/v1/leads, which enforces protections."""
    client = TestClient(app)

    # 1. Valid anonymous submission succeeds through FastAPI
    valid_payload = {
        "customerName": "Verified Client",
        "businessEmail": f"anon_client_{uuid.uuid4().hex[:6]}@example.com",
        "phoneNumber": "+1 555-432-1098",
        "websiteUrl": "https://client-corp.io",
        "businessCategory": "E-Commerce",
        "targetCity": "Austin, TX",
        "requestedService": "Audit",
        "problemDescription": "Testing anonymous client submission through FastAPI endpoint boundary.",
        "urgency": "MEDIUM",
        "consentGiven": True,
        "privacyPolicyVersion": "2026-v1",
    }
    resp = client.post("/api/v1/leads", json=valid_payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["customerName"] == "Verified Client"
    assert data["status"] == "NEW"

    # 2. Bot submission with honeypot filled is rejected
    bot_payload = dict(valid_payload)
    bot_payload["honeypot"] = "I am a spam bot attempting to bypass security"
    resp_bot = client.post("/api/v1/leads", json=bot_payload)
    assert resp_bot.status_code == 400
    assert resp_bot.json()["detail"]["code"] == "SPAM_DETECTED"

    # 3. Duplicate submission within 60s window is rejected
    resp_dup = client.post("/api/v1/leads", json=valid_payload)
    assert resp_dup.status_code == 409
    assert resp_dup.json()["detail"]["code"] == "DUPLICATE_SUBMISSION"
