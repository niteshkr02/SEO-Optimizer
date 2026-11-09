"""Unit tests for Lead domain contracts, Pydantic validation, and sanitization."""

import pytest
from pydantic import ValidationError

from app.contracts.enums import LeadStatus, LeadUrgency
from app.contracts.lead import (
    LeadStatusUpdateRequest,
    LeadSubmissionRequest,
)


def test_valid_lead_submission_request():
    """Verifies that a well-formed lead inquiry instantiates cleanly."""
    req = LeadSubmissionRequest(
        customer_name="Jane Doe",
        business_email="jane@example.com",
        phone_number="+1 555-123-4567",
        website_url="https://example.com",
        business_category="E-Commerce",
        target_city="New York, NY",
        requested_service="Technical SEO Audit",
        problem_description="Observed 30% drop in organic traffic after site migration.",
        urgency=LeadUrgency.HIGH,
        consent_given=True,
        privacy_policy_version="2026-v1",
        scan_token="scan-token-1234",
    )
    assert req.customer_name == "Jane Doe"
    assert req.business_email == "jane@example.com"
    assert req.phone_number == "+1 555-123-4567"
    assert req.website_url == "https://example.com"
    assert req.urgency == LeadUrgency.HIGH
    assert req.consent_given is True


def test_consent_given_must_be_true():
    """Verifies that explicit consent cannot be false."""
    with pytest.raises(ValidationError) as exc:
        LeadSubmissionRequest(
            customer_name="Jane Doe",
            business_email="jane@example.com",
            phone_number="+1 555-123-4567",
            website_url="https://example.com",
            business_category="SaaS",
            target_city="Austin, TX",
            requested_service="Speed Optimization",
            problem_description="Core Web Vitals failing on mobile.",
            urgency=LeadUrgency.MEDIUM,
            consent_given=False,  # Violation
        )
    assert "Explicit contact and privacy consent must be accepted" in str(exc.value)


def test_honeypot_field_captured():
    """Verifies that honeypot field is captured for endpoint spam rejection."""
    req = LeadSubmissionRequest(
        customer_name="Bot Spammer",
        business_email="bot@spam.com",
        phone_number="+1 555-000-0000",
        website_url="https://spam.com",
        business_category="Spam",
        target_city="Nowhere",
        requested_service="Spam",
        problem_description="Buy cheap pills now buy cheap pills now.",
        consent_given=True,
        honeypot="I am a spam bot filling hidden inputs",
    )
    assert req.honeypot == "I am a spam bot filling hidden inputs"


def test_url_must_have_http_or_https_scheme():
    """Verifies that invalid URL formats are rejected."""
    with pytest.raises(ValidationError) as exc:
        LeadSubmissionRequest(
            customer_name="Jane Doe",
            business_email="jane@example.com",
            phone_number="+1 555-123-4567",
            website_url="ftp://ftp.example.com",  # Disallowed scheme
            business_category="SaaS",
            target_city="Austin, TX",
            requested_service="Speed Optimization",
            problem_description="Core Web Vitals failing on mobile.",
            consent_given=True,
        )
    assert "Website URL must start with http:// or https://" in str(exc.value)


def test_problem_description_minimum_length():
    """Verifies problem statement requires substantive technical context (min 10 chars)."""
    with pytest.raises(ValidationError) as exc:
        LeadSubmissionRequest(
            customer_name="Jane Doe",
            business_email="jane@example.com",
            phone_number="+1 555-123-4567",
            website_url="https://example.com",
            business_category="SaaS",
            target_city="Austin, TX",
            requested_service="Speed Optimization",
            problem_description="Help me",  # Too short
            consent_given=True,
        )
    assert "at least 10 characters" in str(exc.value)


def test_lead_status_update_request():
    """Verifies lead status transition request contract."""
    req = LeadStatusUpdateRequest(
        new_status=LeadStatus.SCOPED,
        changed_by="Lead Engineer",
        notes="Reviewed scan findings; scoping 15-day implementation proposal.",
    )
    assert req.new_status == LeadStatus.SCOPED
    assert req.changed_by == "Lead Engineer"
    assert req.notes is not None
