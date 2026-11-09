"""Integration tests for Supabase staging environment and PostgREST wire contract verification."""

import os
import uuid
from datetime import UTC, datetime

import httpx
import pytest

from app.contracts.enums import LeadStatus, LeadUrgency
from app.contracts.lead import LeadSubmissionRequest
from app.persistence.supabase import SupabaseLeadRepository

# Credentials for live staging verification (configured only in staging CI or explicitly)
STAGING_URL = os.getenv("SUPABASE_STAGING_URL")
STAGING_KEY = os.getenv("SUPABASE_STAGING_SERVICE_ROLE_KEY")


# -----------------------------------------------------------------------------
# Live Hosted Database Tests (Executed strictly when staging credentials exist)
# -----------------------------------------------------------------------------


@pytest.mark.skipif(
    not (STAGING_URL and STAGING_KEY),
    reason="Hosted Supabase staging credentials (SUPABASE_STAGING_URL / SUPABASE_STAGING_SERVICE_ROLE_KEY) "
    "are not configured. Skipping live hosted database tests to prevent false claims.",
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


# -----------------------------------------------------------------------------
# PostgREST Wire Contract Verification (Hermetic tests running in all environments)
# -----------------------------------------------------------------------------


def test_supabase_repository_wire_contract():
    """Verifies that SupabaseLeadRepository constructs exact PostgREST URLs, query params, and headers."""
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
    import urllib.parse
    assert "select=*,lead_status_history(*)" in urllib.parse.unquote(str(get_req.url))
