"""Integration tests for Lead Capture, Admin Management, and Consultation Brief endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.main import app
from app.persistence.repository import lead_repository


@pytest.fixture(autouse=True)
def clean_repository():
    """Ensures a clean repository state before every test."""
    lead_repository.reset()
    yield
    lead_repository.reset()


@pytest.mark.asyncio
async def test_public_lead_submission_success():
    """Verifies that a valid client service inquiry is accepted and returns 201 Created."""
    payload = {
        "customerName": "Elena Vance",
        "businessEmail": "elena@blackmesa.org",
        "phoneNumber": "+1 555-432-8765",
        "websiteUrl": "https://blackmesa.org",
        "businessCategory": "Scientific Research",
        "targetCity": "Albuquerque, NM",
        "requestedService": "Technical SEO Audit & Code Remediation",
        "problemDescription": "Robots.txt directives and JSON-LD schema syntax failing after CMS update.",
        "urgency": "HIGH",
        "consentGiven": True,
        "privacyPolicyVersion": "2026-v1",
    }

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/api/v1/leads", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["customerName"] == "Elena Vance"
    assert data["businessEmail"] == "elena@blackmesa.org"
    assert data["status"] == "NEW"
    assert data["id"] is not None
    assert len(data["statusHistory"]) == 1


@pytest.mark.asyncio
async def test_honeypot_spam_is_rejected():
    """Verifies that populating the honeypot field is rejected with 400 Bad Request."""
    payload = {
        "customerName": "Bot Spammer",
        "businessEmail": "spambot@spammer.com",
        "phoneNumber": "+1 555-000-0000",
        "websiteUrl": "https://spam.com",
        "businessCategory": "Spam",
        "targetCity": "None",
        "requestedService": "Spam",
        "problemDescription": "Automated spam payload filling all fields.",
        "urgency": "LOW",
        "consentGiven": True,
        "honeypot": "Automated bot input",
    }

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/api/v1/leads", json=payload)

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "SPAM_DETECTED"


@pytest.mark.asyncio
async def test_duplicate_submission_is_rejected():
    """Verifies that rapid duplicate submissions for identical email and target URL are rejected."""
    payload = {
        "customerName": "Marcus Brody",
        "businessEmail": "marcus@museum.edu",
        "phoneNumber": "+1 555-321-4567",
        "websiteUrl": "https://museum.edu",
        "businessCategory": "Education",
        "targetCity": "New York, NY",
        "requestedService": "Audit",
        "problemDescription": "Initial submission about duplicate content issues.",
        "urgency": "MEDIUM",
        "consentGiven": True,
    }

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        res1 = await client.post("/api/v1/leads", json=payload)
        assert res1.status_code == 201

        # Duplicate immediate submission
        res2 = await client.post("/api/v1/leads", json=payload)
        assert res2.status_code == 409
        assert res2.json()["detail"]["code"] == "DUPLICATE_SUBMISSION"


@pytest.mark.asyncio
async def test_admin_authorization_guard():
    """Verifies that admin lead endpoints strictly enforce server-side authentication."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # 1. Missing authorization header
        res_missing = await client.get("/api/v1/leads")
        assert res_missing.status_code == 401
        assert res_missing.json()["detail"]["code"] == "UNAUTHORIZED"

        # 2. Invalid API key
        res_invalid = await client.get(
            "/api/v1/leads", headers={"X-Admin-Api-Key": "wrong-secret-key"}
        )
        assert res_invalid.status_code == 401

        # 3. Valid API key
        res_valid = await client.get(
            "/api/v1/leads",
            headers={"X-Admin-Api-Key": settings.ADMIN_API_KEY},
        )
        assert res_valid.status_code == 200
        assert "items" in res_valid.json()


@pytest.mark.asyncio
async def test_admin_status_update_and_audit_history():
    """Verifies admin status transition from NEW to SCOPED and immutable history logging."""
    # First, submit a lead
    payload = {
        "customerName": "Gordon Freeman",
        "businessEmail": "gordon@blackmesa.gov",
        "phoneNumber": "+1 555-111-2222",
        "websiteUrl": "https://blackmesa.gov",
        "businessCategory": "Government",
        "targetCity": "Black Mesa, NM",
        "requestedService": "Full Code Remediation",
        "problemDescription": "Anomalous materials section has multiple broken canonical tags.",
        "urgency": "CRITICAL",
        "consentGiven": True,
    }

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        create_res = await client.post("/api/v1/leads", json=payload)
        assert create_res.status_code == 201
        lead_id = create_res.json()["id"]

        # Admin updates status to SCOPED
        update_payload = {
            "newStatus": "SCOPED",
            "changedBy": "Senior Consultant",
            "notes": "Reviewed audit evidence with client; 15-day scope agreed.",
        }
        update_res = await client.patch(
            f"/api/v1/leads/{lead_id}/status",
            json=update_payload,
            headers={"X-Admin-Api-Key": settings.ADMIN_API_KEY},
        )
        assert update_res.status_code == 200
        updated_data = update_res.json()
        assert updated_data["status"] == "SCOPED"
        assert len(updated_data["statusHistory"]) == 2

        # Check history endpoint
        hist_res = await client.get(
            f"/api/v1/leads/{lead_id}/history",
            headers={"X-Admin-Api-Key": settings.ADMIN_API_KEY},
        )
        assert hist_res.status_code == 200
        history_items = hist_res.json()
        assert len(history_items) == 2
        assert history_items[1]["newStatus"] == "SCOPED"


@pytest.mark.asyncio
async def test_consultation_brief_exports_json_markdown_pdf():
    """Verifies consultation brief export endpoints in JSON, Markdown, and PDF formats."""
    # Submit lead
    payload = {
        "customerName": "Dr. Eli Vance",
        "businessEmail": "eli@resistance.org",
        "phoneNumber": "+1 555-777-6666",
        "websiteUrl": "https://resistance.org",
        "businessCategory": "Non-Profit",
        "targetCity": "City 17",
        "requestedService": "Technical SEO Audit",
        "problemDescription": "Need comprehensive consultation brief for leadership review.",
        "urgency": "HIGH",
        "consentGiven": True,
    }

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        create_res = await client.post("/api/v1/leads", json=payload)
        lead_id = create_res.json()["id"]

        headers = {"X-Admin-Api-Key": settings.ADMIN_API_KEY}

        # 1. JSON Brief
        json_res = await client.get(f"/api/v1/leads/{lead_id}/brief", headers=headers)
        assert json_res.status_code == 200
        brief_data = json_res.json()
        assert brief_data["leadId"] == lead_id
        assert brief_data["clientDetails"]["customerName"] == "Dr. Eli Vance"
        assert "Google ranking and search engine placement are not guaranteed" in brief_data["rankingDisclaimer"]

        # 2. Markdown Brief
        md_res = await client.get(f"/api/v1/leads/{lead_id}/brief/markdown", headers=headers)
        assert md_res.status_code == 200
        assert md_res.headers["content-type"].startswith("text/markdown")
        assert "# Technical SEO Consultation Brief:" in md_res.text
        assert "Dr. Eli Vance" in md_res.text

        # 3. PDF Brief
        pdf_res = await client.get(f"/api/v1/leads/{lead_id}/brief/pdf", headers=headers)
        assert pdf_res.status_code == 200
        assert pdf_res.headers["content-type"] == "application/pdf"
        assert pdf_res.content.startswith(b"%PDF")

