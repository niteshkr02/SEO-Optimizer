"""Unit tests verifying PDF compilation with fpdf2 for Consultation Service Briefs."""

from datetime import UTC, datetime

from app.contracts.brief import (
    AuditScopeDTO,
    ClientDetailsDTO,
    CriticalIssueSummaryDTO,
    ServiceBriefDTO,
)
from app.contracts.enums import IssueSeverity, RuleCategory
from app.leads.pdf_export import generate_brief_pdf


def test_generate_brief_pdf_produces_valid_bytes():
    """Verifies that generate_brief_pdf produces non-empty valid PDF byte stream starting with %PDF."""
    brief = ServiceBriefDTO(
        brief_id="brief-test-12345",
        lead_id="lead-test-67890",
        generated_at=datetime.now(UTC),
        client_details=ClientDetailsDTO(
            customer_name="John Tech",
            business_email="john@techcorp.com",
            phone_number="+1 555-432-1098",
            website_url="https://techcorp.com",
            business_category="SaaS",
            target_city="Seattle, WA",
            requested_service="Speed & Vitals",
            urgency="HIGH",
            problem_description="Images lack alt text and dimensions causing layout shifts and accessibility failures.",
        ),
        audit_scope=AuditScopeDTO(
            has_audit_report=True,
            scan_token="scan-token-xyz",
            scan_timestamp=datetime.now(UTC),
            target_url="https://techcorp.com",
            status_code=200,
            overall_health_score=74.2,
            completeness_score=100.0,
            total_checks_evaluated=20,
            failing_checks_count=3,
            warning_checks_count=1,
            passed_checks_count=16,
        ),
        critical_issues=[
            CriticalIssueSummaryDTO(
                rule_id="http-status-200",
                category=RuleCategory.CRAWLABILITY,
                severity=IssueSeverity.CRITICAL,
                title="HTTP 200 Status",
                description="Final response status code was 500 instead of 200.",
                observed_value="500 Internal Server Error",
                expected_value="200 OK",
                raw_snippet="HTTP/1.1 500 Internal Server Error",
                target_element="HTTP Response Status Line",
                remediation_guidance="Resolve backend uncaught exceptions.",
            )
        ],
        proposed_solutions=[],
        implementation_priorities=[],
        verification_summary=None,
        unknown_and_unavailable_disclosures=[
            "Competitor SERP ranking positions unmeasured.",
            "Client git repository source files not accessed.",
        ],
        ranking_disclaimer="Google ranking and search engine placement are not guaranteed.",
    )

    pdf_bytes = generate_brief_pdf(brief)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 500
    # Valid PDF files start with %PDF
    assert pdf_bytes.startswith(b"%PDF")
