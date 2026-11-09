"""Unit tests for LeadRepository, sliding-window rate limiting, and status transitions."""

import pytest

from app.contracts.enums import LeadStatus, LeadUrgency
from app.contracts.lead import LeadSubmissionRequest
from app.persistence.repository import LeadRepository


@pytest.fixture
def repo():
    """Provides a fresh isolated repository instance."""
    repository = LeadRepository()
    repository.reset()
    return repository


def test_create_and_get_lead(repo: LeadRepository):
    """Verifies persisting a lead initializes status NEW and creates an audit history entry."""
    req = LeadSubmissionRequest(
        customer_name="Alex Smith",
        business_email="alex@techcorp.io",
        phone_number="+44 20 7946 0912",
        website_url="https://techcorp.io",
        business_category="B2B SaaS",
        target_city="London, UK",
        requested_service="Code Remediation",
        problem_description="H1 tags and canonical URLs misconfigured across landing pages.",
        urgency=LeadUrgency.CRITICAL,
        consent_given=True,
    )

    lead = repo.create_lead(req, client_ip="198.51.100.1")
    assert lead.id is not None
    assert lead.status == LeadStatus.NEW
    assert lead.urgency == LeadUrgency.CRITICAL
    assert len(lead.status_history) == 1
    assert lead.status_history[0].new_status == LeadStatus.NEW

    fetched = repo.get_lead(lead.id)
    assert fetched is not None
    assert fetched.id == lead.id
    assert fetched.customer_name == "Alex Smith"


def test_status_update_appends_history(repo: LeadRepository):
    """Verifies updating status appends an immutable audit entry and updates updated_at."""
    req = LeadSubmissionRequest(
        customer_name="Alex Smith",
        business_email="alex@techcorp.io",
        phone_number="+44 20 7946 0912",
        website_url="https://techcorp.io",
        business_category="B2B SaaS",
        target_city="London, UK",
        requested_service="Code Remediation",
        problem_description="H1 tags and canonical URLs misconfigured across landing pages.",
        urgency=LeadUrgency.MEDIUM,
        consent_given=True,
    )
    lead = repo.create_lead(req)

    updated = repo.update_lead_status(
        lead_id=lead.id,
        new_status=LeadStatus.CONTACTED,
        changed_by="Consultant Sarah",
        notes="Introductory technical scoping call completed.",
    )
    assert updated is not None
    assert updated.status == LeadStatus.CONTACTED
    assert len(updated.status_history) == 2
    assert updated.status_history[1].previous_status == LeadStatus.NEW
    assert updated.status_history[1].new_status == LeadStatus.CONTACTED
    assert updated.status_history[1].changed_by == "Consultant Sarah"


def test_rate_limiting_per_ip(repo: LeadRepository):
    """Verifies that exceeding max submissions from an IP triggers rate limiting."""
    ip = "203.0.113.42"
    email = "lead{}@example.com"

    # Submit up to the limit (5)
    for i in range(5):
        req = LeadSubmissionRequest(
            customer_name=f"User {i}",
            business_email=email.format(i),
            phone_number="+1 555-123-4567",
            website_url=f"https://site{i}.com",
            business_category="Retail",
            target_city="Miami, FL",
            requested_service="Audit",
            problem_description="Detailed problem statement for testing rate limits.",
            consent_given=True,
        )
        allowed, _ = repo.check_rate_limit(ip, req.business_email)
        assert allowed is True
        repo.create_lead(req, client_ip=ip)

    # 6th submission from same IP should be blocked
    allowed, msg = repo.check_rate_limit(ip, "another@example.com")
    assert allowed is False
    assert "Too many inquiries from IP" in msg


def test_duplicate_submission_detection(repo: LeadRepository):
    """Verifies that rapid duplicate submissions for identical email and target URL are flagged."""
    req = LeadSubmissionRequest(
        customer_name="John Doe",
        business_email="john@example.com",
        phone_number="+1 555-123-4567",
        website_url="https://example.com",
        business_category="Retail",
        target_city="Miami, FL",
        requested_service="Audit",
        problem_description="Detailed problem statement for testing duplicate submissions.",
        consent_given=True,
    )
    repo.create_lead(req)

    # Immediate second submission should be detected as duplicate
    is_dup = repo.check_duplicate_submission(req.business_email, req.website_url)
    assert is_dup is True

    # Submission for different domain by same email should not be a duplicate
    is_diff_domain = repo.check_duplicate_submission(req.business_email, "https://otherdomain.com")
    assert is_diff_domain is False


def test_list_leads_filter_and_search(repo: LeadRepository):
    """Verifies filtering by status and text search."""
    req1 = LeadSubmissionRequest(
        customer_name="Alice Alpha",
        business_email="alice@alpha.com",
        phone_number="+1 555-111-2222",
        website_url="https://alpha.com",
        business_category="FinTech",
        target_city="Boston, MA",
        requested_service="Audit",
        problem_description="Detailed problem statement for alpha fintech site.",
        consent_given=True,
    )
    req2 = LeadSubmissionRequest(
        customer_name="Bob Beta",
        business_email="bob@beta.org",
        phone_number="+1 555-333-4444",
        website_url="https://beta.org",
        business_category="Healthcare",
        target_city="Chicago, IL",
        requested_service="Migration Review",
        problem_description="Detailed problem statement for beta healthcare site.",
        consent_given=True,
    )
    lead1 = repo.create_lead(req1)
    lead2 = repo.create_lead(req2)
    repo.update_lead_status(lead2.id, LeadStatus.SCOPED, "Engineer")

    # Filter by status
    new_leads, total_new = repo.list_leads(status=LeadStatus.NEW)
    assert total_new == 1
    assert new_leads[0].id == lead1.id

    scoped_leads, total_scoped = repo.list_leads(status=LeadStatus.SCOPED)
    assert total_scoped == 1
    assert scoped_leads[0].id == lead2.id

    # Search by keyword
    search_res, total_search = repo.list_leads(search="fintech")
    assert total_search == 1
    assert search_res[0].customer_name == "Alice Alpha"

