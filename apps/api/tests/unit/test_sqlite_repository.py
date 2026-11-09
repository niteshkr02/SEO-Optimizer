"""Unit tests verifying SQLiteLeadRepository durability across restarts and process boundaries."""

import os
import tempfile

import pytest

from app.contracts.enums import LeadStatus, LeadUrgency
from app.contracts.lead import LeadSubmissionRequest
from app.persistence.sqlite import SQLiteLeadRepository


@pytest.fixture
def temp_sqlite_repo():
    """Provides a temporary SQLite repository file that is cleaned up after test execution."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    repo = SQLiteLeadRepository(db_path=path)
    yield repo, path
    if os.path.exists(path):
        try:
            os.remove(path)
        except OSError:
            pass


def test_sqlite_persistence_across_restarts(temp_sqlite_repo):
    """Verifies that leads and status history persist across distinct repository instances."""
    repo1, db_path = temp_sqlite_repo

    req = LeadSubmissionRequest(
        customer_name="Gordon Freeman",
        business_email="gordon@blackmesa.org",
        phone_number="+1 555-019-2834",
        website_url="https://blackmesa.org",
        business_category="Research",
        target_city="Albuquerque, NM",
        requested_service="Technical SEO Audit",
        problem_description="Anomalous materials page missing canonical tags and open graph data.",
        urgency=LeadUrgency.HIGH,
        consent_given=True,
        privacy_policy_version="2026-v1",
    )

    created = repo1.create_lead(req, client_ip="192.168.1.50")
    assert created.id is not None
    assert created.status == LeadStatus.NEW
    assert len(created.status_history) == 1

    # Simulate process shutdown / restart by creating an independent repository instance
    repo2 = SQLiteLeadRepository(db_path=db_path)

    # Verify retrieval from new instance
    retrieved = repo2.get_lead(created.id)
    assert retrieved is not None
    assert retrieved.id == created.id
    assert retrieved.customer_name == "Gordon Freeman"
    assert retrieved.business_email == "gordon@blackmesa.org"
    assert retrieved.status == LeadStatus.NEW
    assert len(retrieved.status_history) == 1
    assert retrieved.status_history[0].new_status == LeadStatus.NEW

    # Update status in instance 2
    updated = repo2.update_lead_status(
        lead_id=created.id,
        new_status=LeadStatus.SCOPED,
        changed_by="Analyst Barney Calhoun",
        notes="Scoped 5 technical issues in DOM hierarchy.",
    )
    assert updated is not None
    assert updated.status == LeadStatus.SCOPED
    assert len(updated.status_history) == 2

    # Simulate another restart and verify in instance 3
    repo3 = SQLiteLeadRepository(db_path=db_path)
    retrieved_after_restart = repo3.get_lead(created.id)
    assert retrieved_after_restart is not None
    assert retrieved_after_restart.status == LeadStatus.SCOPED
    assert len(retrieved_after_restart.status_history) == 2
    assert retrieved_after_restart.status_history[1].new_status == LeadStatus.SCOPED
    assert retrieved_after_restart.status_history[1].changed_by == "Analyst Barney Calhoun"


def test_sqlite_duplicate_detection_persists(temp_sqlite_repo):
    """Verifies that duplicate submission tracking survives instance recreation."""
    repo1, db_path = temp_sqlite_repo

    req = LeadSubmissionRequest(
        customer_name="Alyx Vance",
        business_email="alyx@city17.org",
        phone_number="+1 555-888-9999",
        website_url="https://city17.org",
        business_category="Civilian",
        target_city="City 17",
        requested_service="Consultation",
        problem_description="Robots directives and heading structure corrupted.",
        urgency=LeadUrgency.CRITICAL,
        consent_given=True,
    )

    repo1.create_lead(req)

    # Spawn new instance
    repo2 = SQLiteLeadRepository(db_path=db_path)

    # Duplicate check should immediately flag identical email & target URL
    is_dup = repo2.check_duplicate_submission("alyx@city17.org", "https://city17.org")
    assert is_dup is True

    # Different URL should not be flagged
    is_not_dup = repo2.check_duplicate_submission("alyx@city17.org", "https://other.org")
    assert is_not_dup is False


def test_sqlite_rate_limiting_persists(temp_sqlite_repo):
    """Verifies that sliding window rate limit counts persist across repository restarts."""
    repo1, db_path = temp_sqlite_repo
    client_ip = "203.0.113.42"
    email = "test@limit.com"

    for i in range(5):
        req = LeadSubmissionRequest(
            customer_name=f"Lead User {i}",
            business_email=f"unique{i}@limit.com",
            phone_number="+1 555-000-1111",
            website_url=f"https://limit-site-{i}.com",
            business_category="Testing",
            target_city="Test City",
            requested_service="SEO",
            problem_description="Test problem description with enough characters.",
            urgency=LeadUrgency.LOW,
            consent_given=True,
        )
        repo1.create_lead(req, client_ip=client_ip)

    # Instance 2 checks IP limit
    repo2 = SQLiteLeadRepository(db_path=db_path)
    allowed, msg = repo2.check_rate_limit(client_ip=client_ip, email="another@limit.com")
    assert allowed is False
    assert "Too many inquiries from IP 203.0.113.42" in msg


def test_sqlite_search_and_pagination(temp_sqlite_repo):
    """Verifies SQLite repository filtering, search, and pagination."""
    repo, _ = temp_sqlite_repo

    for i in range(12):
        city = "Seattle, WA" if i % 2 == 0 else "Austin, TX"
        req = LeadSubmissionRequest(
            customer_name=f"Client Alpha {i}",
            business_email=f"alpha{i}@client.com",
            phone_number=f"+1 555-123-00{i:02d}",
            website_url=f"https://alpha-{i}.com",
            business_category="E-Commerce",
            target_city=city,
            requested_service="Technical Audit",
            problem_description="E-commerce category filter causing duplicate content issues.",
            urgency=LeadUrgency.MEDIUM,
            consent_given=True,
        )
        repo.create_lead(req)

    # Search by city
    leads, total = repo.list_leads(search="Austin", limit=10, offset=0)
    assert total == 6
    assert len(leads) == 6
    assert all("Austin" in lead.target_city for lead in leads)

    # Pagination
    page1, total_all = repo.list_leads(limit=5, offset=0)
    assert total_all == 12
    assert len(page1) == 5

    page2, _ = repo.list_leads(limit=5, offset=5)
    assert len(page2) == 5
    assert page1[0].id != page2[0].id
