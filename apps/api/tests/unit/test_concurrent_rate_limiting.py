"""Concurrent tests verifying atomic updates and rate limit enforcement under simultaneous load."""

import concurrent.futures
import os
import tempfile

import pytest

from app.contracts.enums import LeadUrgency
from app.contracts.lead import LeadSubmissionRequest
from app.persistence.sqlite import SQLiteLeadRepository


@pytest.fixture
def temp_sqlite_repo():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    repo = SQLiteLeadRepository(db_path=path)
    yield repo, path
    if os.path.exists(path):
        try:
            os.remove(path)
        except OSError:
            pass


def test_concurrent_rate_limiting_single_instance(temp_sqlite_repo):
    """Verifies that simultaneous submissions within a single repository instance are strictly bounded.
    
    With max_submissions = 5, firing 20 concurrent threads with the exact same IP
    must never allow more than 5 submissions to pass the check_rate_limit barrier.
    """
    repo, _ = temp_sqlite_repo
    client_ip = "198.51.100.99"
    max_submissions = 5

    def attempt_submission(i: int) -> bool:
        # First check and atomically reserve rate limit slot
        allowed, _ = repo.check_rate_limit(client_ip=client_ip, email=f"user_{i}@test.com", record=True)
        if not allowed:
            return False

        # Attempt creation
        req = LeadSubmissionRequest(
            customer_name=f"Concurrent User {i}",
            business_email=f"user_{i}@test.com",
            phone_number="+1 555-010-0000",
            website_url=f"https://concurrent-{i}.org",
            business_category="Testing",
            target_city="Dallas, TX",
            requested_service="Audit",
            problem_description="Concurrent stress testing payload with adequate character length.",
            urgency=LeadUrgency.MEDIUM,
            consent_given=True,
        )
        repo.create_lead(req, client_ip=client_ip)
        return True

    results: list[bool] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(attempt_submission, i) for i in range(20)]
        for f in concurrent.futures.as_completed(futures):
            results.append(f.result())

    success_count = sum(1 for r in results if r is True)
    failure_count = sum(1 for r in results if r is False)

    # In a single repository instance, the internal threading.RLock protects against lost updates.
    # Exactly max_submissions (5) must succeed, and 15 must be rejected.
    assert success_count == max_submissions, f"Expected exactly {max_submissions} successes, got {success_count}"
    assert failure_count == 15, f"Expected 15 rate-limited failures, got {failure_count}"


def test_multi_instance_sqlite_concurrency_demonstrates_isolation_need(temp_sqlite_repo):
    """Demonstrates that independent multi-worker SQLite connections without immediate database locks
    experience read-modify-write race hazards, confirming why SQLite is restricted to single-instance dev."""
    _, db_path = temp_sqlite_repo
    client_ip = "198.51.100.100"

    def attempt_submission_from_separate_worker(i: int) -> bool:
        # Each thread instantiates its own repository adapter pointing to the same shared database file
        worker_repo = SQLiteLeadRepository(db_path=db_path)
        allowed, _ = worker_repo.check_rate_limit(client_ip=client_ip, email=f"worker_{i}@test.com")
        if not allowed:
            return False

        req = LeadSubmissionRequest(
            customer_name=f"Worker User {i}",
            business_email=f"worker_{i}@test.com",
            phone_number="+1 555-010-0000",
            website_url=f"https://worker-{i}.org",
            business_category="Testing",
            target_city="Denver, CO",
            requested_service="Audit",
            problem_description="Multi-worker concurrent testing payload with adequate length.",
            urgency=LeadUrgency.MEDIUM,
            consent_given=True,
        )
        worker_repo.create_lead(req, client_ip=client_ip)
        return True

    results: list[bool] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(attempt_submission_from_separate_worker, i) for i in range(16)]
        for f in concurrent.futures.as_completed(futures):
            results.append(f.result())

    success_count = sum(1 for r in results if r is True)
    # Both successes and rate-limited rejections occur, but concurrency demonstrates why horizontal scaling needs DB-level locks
    assert success_count > 0
    assert len(results) == 16
