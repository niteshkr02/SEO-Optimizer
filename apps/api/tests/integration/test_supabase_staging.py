"""Integration tests for Supabase staging environment and PostgREST wire contract verification."""

import os
import urllib.parse
import uuid
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest
from dotenv import load_dotenv

from app.contracts.enums import LeadStatus, LeadUrgency
from app.contracts.lead import LeadSubmissionRequest
from app.persistence.supabase import SupabaseLeadRepository

# Search up parents for .env file safely without printing secrets
for parent in Path(__file__).resolve().parents:
    env_candidate = parent / ".env"
    if env_candidate.exists():
        load_dotenv(env_candidate)

STAGING_URL = os.getenv("SUPABASE_STAGING_URL")
STAGING_KEY = os.getenv("SUPABASE_STAGING_SERVICE_ROLE_KEY")
ALLOW_LIVE_MUTATIONS = os.getenv("ALLOW_STAGING_LIVE_MUTATIONS", "0") == "1"


# -----------------------------------------------------------------------------
# Read-Only Staging Connectivity Checks
# -----------------------------------------------------------------------------


@pytest.mark.skipif(
    not (STAGING_URL and STAGING_KEY),
    reason="Hosted Supabase staging credentials (SUPABASE_STAGING_URL / SUPABASE_STAGING_SERVICE_ROLE_KEY) "
    "are not configured. Skipping live staging connectivity test.",
)
def test_supabase_staging_connectivity():
    """Performs a non-destructive read-only connectivity check against the dedicated staging project.
    
    Verifies that the staging PostgREST OpenAPI spec is reachable with the service-role key,
    without executing any migrations or mutating any database records.
    """
    headers = {
        "apikey": STAGING_KEY,
        "Authorization": f"Bearer {STAGING_KEY}",
    }
    with httpx.Client(
        base_url=f"{STAGING_URL.rstrip('/')}/rest/v1",
        headers=headers,
        timeout=10.0,
    ) as client:
        resp = client.get("/")
        assert resp.status_code == 200, f"Expected 200 from PostgREST root, got {resp.status_code}"
        spec = resp.json()
        assert "paths" in spec
        # Verify PostgREST exposes endpoints
        assert isinstance(spec["paths"], dict)


# -----------------------------------------------------------------------------
# Live Hosted Database Mutation Tests (Strictly Gated)
# -----------------------------------------------------------------------------


@pytest.mark.skipif(
    not (STAGING_URL and STAGING_KEY and ALLOW_LIVE_MUTATIONS),
    reason="Live database mutation tests require ALLOW_STAGING_LIVE_MUTATIONS=1 and valid staging credentials. "
    "Skipped to enforce the strict rule: Migration execution and data modification require separate explicit approval.",
)
def test_supabase_live_staging_end_to_end():
    """Validates real PostgREST CRUD, foreign key cascade, and audit trails on hosted staging."""
    repo = SupabaseLeadRepository(supabase_url=STAGING_URL, service_role_key=STAGING_KEY)

    req = LeadSubmissionRequest(
        customer_name="Staging Verification User",
        business_email=f"staging_{uuid.uuid4().hex[:8]}@example.com",
        phone_number="+1 555-010-9999",
        website_url="https://staging.example.com",
        business_category="SaaS",
        target_city="San Francisco, CA",
        requested_service="Full Remediation",
        problem_description="Staging integration test payload verifying live Supabase PostgREST.",
        urgency=LeadUrgency.HIGH,
        consent_given=True,
    )

    # 1. Create
    created = repo.create_lead(req, client_ip="198.51.100.1")
    assert created.id is not None
    assert created.status == LeadStatus.NEW

    # 2. Read
    fetched = repo.get_lead(created.id)
    assert fetched is not None
    assert fetched.id == created.id
    assert len(fetched.status_history) >= 1

    # 3. Status Transition
    updated = repo.update_lead_status(
        lead_id=created.id,
        new_status=LeadStatus.SCOPED,
        changed_by="Staging CI Operator",
        notes="Scoped in live staging verification test.",
    )
    assert updated is not None
    assert updated.status == LeadStatus.SCOPED
    assert len(updated.status_history) == 2

    # 4. List and Filter
    leads, total = repo.list_leads(status=LeadStatus.SCOPED, limit=10)
    assert total >= 1
    assert any(l.id == created.id for l in leads)


@pytest.mark.skipif(
    not (STAGING_URL and STAGING_KEY and ALLOW_LIVE_MUTATIONS),
    reason="Live database mutation tests require ALLOW_STAGING_LIVE_MUTATIONS=1 and valid staging credentials.",
)
def test_supabase_live_staging_anonymous_insert_revocation():
    """Verifies that direct anonymous INSERT to /leads and execution of the rate-limit RPC are strictly denied."""
    pub_key = os.getenv("SUPABASE_PUBLISHABLE_KEY") or os.getenv("SUPABASE_ANON_KEY")
    if not pub_key:
        pytest.skip("SUPABASE_PUBLISHABLE_KEY not configured for anonymous boundary test.")

    anon_headers = {
        "apikey": pub_key,
        "Authorization": f"Bearer {pub_key}",
        "Content-Type": "application/json",
    }

    with httpx.Client(base_url=f"{STAGING_URL.rstrip('/')}/rest/v1", headers=anon_headers, timeout=10.0) as client:
        # 1. Verify anonymous direct INSERT on /leads is rejected (401/403/permission denied)
        payload = {
            "customer_name": "Direct Anon Attack",
            "business_email": "attacker@darkweb.io",
            "phone_number": "+1 555-666-7777",
            "website_url": "https://malicious.example.com",
            "business_category": "Spam",
            "target_city": "Unknown",
            "requested_service": "Audit",
            "problem_description": "Attempting direct Data API injection to bypass FastAPI server.",
            "urgency": "HIGH",
            "consent_given": True,
        }
        resp = client.post("/leads", json=payload)
        # Expect 401 Unauthorized, 403 Forbidden, or error message mentioning permission denied / RLS
        assert resp.status_code in (401, 403, 404) or "permission denied" in resp.text.lower() or "policy" in resp.text.lower()

        # 2. Verify anonymous invocation of check_and_record_rate_limit RPC is rejected
        rpc_payload = {
            "p_rate_key": "anon:test",
            "p_now": 1700000000.0,
            "p_window_seconds": 600.0,
            "p_max_submissions": 5,
            "p_record": True,
        }
        rpc_resp = client.post("/rpc/check_and_record_rate_limit", json=rpc_payload)
        assert rpc_resp.status_code in (401, 403, 404) or "permission denied" in rpc_resp.text.lower()


@pytest.mark.skipif(
    not (STAGING_URL and STAGING_KEY and ALLOW_LIVE_MUTATIONS),
    reason="Live database mutation tests require ALLOW_STAGING_LIVE_MUTATIONS=1 and valid staging credentials.",
)
def test_supabase_live_staging_atomic_rpc_rate_limiting():
    """Verifies atomic RPC execution and sliding-window rate limit enforcement on live staging database."""
    repo = SupabaseLeadRepository(supabase_url=STAGING_URL, service_role_key=STAGING_KEY)
    test_ip = f"198.51.100.{uuid.uuid4().hex[:6]}"
    test_email = f"rpc_live_{uuid.uuid4().hex[:6]}@example.com"

    # Submissions 1 through 5 (allowed by default limit of 5)
    for i in range(5):
        allowed, msg = repo.check_rate_limit(test_ip, test_email, record=True)
        assert allowed is True, f"Submission {i + 1} should be allowed on live staging, got msg: {msg}"
        assert msg == ""

    # 6th submission must be rejected by the live atomic RPC
    allowed, msg = repo.check_rate_limit(test_ip, test_email, record=True)
    assert allowed is False
    assert "Too many inquiries from IP" in msg

    # Clean up test rate limit keys from staging
    with repo._client() as client:
        client.delete("/rate_limits", params={"rate_key": f"eq.ip:{test_ip}"})
        client.delete("/rate_limits", params={"rate_key": f"eq.email:{test_email.lower().strip()}"})


# -----------------------------------------------------------------------------
# PostgREST Wire Contract Verification (Hermetic tests running in all environments)
# -----------------------------------------------------------------------------


def test_supabase_repository_wire_contract():
    """Verifies that SupabaseLeadRepository constructs exact PostgREST URLs, query params, headers, and RPC payloads."""
    fake_url = "https://fake-project.supabase.co"
    fake_key = "fake-service-role-key-never-leaked"

    dispatched_requests: list[httpx.Request] = []

    def mock_transport_handler(request: httpx.Request) -> httpx.Response:
        dispatched_requests.append(request)

        # Mock GET /leads
        if request.url.path == "/rest/v1/leads" and request.method == "GET":
            if "id=eq." in str(request.url):
                return httpx.Response(
                    200,
                    json=[
                        {
                            "id": "test-lead-uuid",
                            "scan_token": "token-xyz",
                            "customer_name": "Dr. Judith Mossman",
                            "business_email": "mossman@blackmesa.org",
                            "phone_number": "+1 555-123-4567",
                            "website_url": "https://blackmesa.org",
                            "business_category": "Physics",
                            "target_city": "Geneva",
                            "requested_service": "Audit",
                            "problem_description": "PostgREST wire contract test description.",
                            "urgency": "MEDIUM",
                            "status": "NEW",
                            "consent_given": True,
                            "consent_timestamp": datetime.now(UTC).isoformat(),
                            "privacy_policy_version": "2026-v1",
                            "tech_stack": None,
                            "created_at": datetime.now(UTC).isoformat(),
                            "updated_at": datetime.now(UTC).isoformat(),
                            "lead_status_history": [
                                {
                                    "id": "hist-uuid-1",
                                    "lead_id": "test-lead-uuid",
                                    "previous_status": None,
                                    "new_status": "NEW",
                                    "changed_by": "Public Form",
                                    "notes": "Initial inquiry",
                                    "created_at": datetime.now(UTC).isoformat(),
                                }
                            ],
                        }
                    ],
                )
            return httpx.Response(
                200,
                headers={"Content-Range": "0-0/1"},
                json=[],
            )

        # Mock POST /leads
        if request.url.path == "/rest/v1/leads" and request.method == "POST":
            return httpx.Response(201, json=[])

        # Mock POST /lead_status_history
        if request.url.path == "/rest/v1/lead_status_history" and request.method == "POST":
            return httpx.Response(201, json=[])

        # Mock POST /rpc/check_and_record_rate_limit
        if request.url.path == "/rest/v1/rpc/check_and_record_rate_limit":
            return httpx.Response(200, json=True)

        # Mock GET /rate_limits
        if request.url.path == "/rest/v1/rate_limits":
            return httpx.Response(200, json=[])

        # Mock POST /rate_limits
        if request.url.path == "/rest/v1/rate_limits" and request.method == "POST":
            return httpx.Response(200, json=[])

        return httpx.Response(404, json={"message": "Not found"})

    repo = SupabaseLeadRepository(supabase_url=fake_url, service_role_key=fake_key)

    # Monkeypatch client factory to use custom mock transport
    repo._client = lambda: httpx.Client(
        base_url=f"{fake_url}/rest/v1",
        headers=repo._headers,
        transport=httpx.MockTransport(mock_transport_handler),
    )

    # 1. Test get_lead requests foreign key relationship embedding
    lead = repo.get_lead("test-lead-uuid")
    assert lead is not None
    assert lead.id == "test-lead-uuid"
    assert len(lead.status_history) == 1

    get_req = next(r for r in dispatched_requests if r.method == "GET" and "/leads" in str(r.url))
    assert get_req.headers["apikey"] == fake_key
    assert get_req.headers["Authorization"] == f"Bearer {fake_key}"
    assert "select=*,lead_status_history(*)" in urllib.parse.unquote(str(get_req.url))

    # 2. Test check_rate_limit invokes atomic RPC
    dispatched_requests.clear()
    allowed, msg = repo.check_rate_limit("198.51.100.22", "wire_test@example.com", record=True)
    assert allowed is True
    assert msg == ""

    rpc_requests = [r for r in dispatched_requests if "/rpc/check_and_record_rate_limit" in str(r.url)]
    assert len(rpc_requests) >= 2
    assert rpc_requests[0].method == "POST"
    assert rpc_requests[0].headers["apikey"] == fake_key
    assert rpc_requests[0].headers["Authorization"] == f"Bearer {fake_key}"
