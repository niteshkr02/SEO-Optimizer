"""Unit tests for Consultation ServiceBriefGenerator and exports."""

from datetime import UTC, datetime

import pytest

from app.contracts.enums import (
    IssueSeverity,
    LeadStatus,
    LeadUrgency,
    ProvenanceCategory,
    RuleCategory,
    RuleState,
    ScanStatus,
)
from app.contracts.evidence import FindingEvidence
from app.contracts.finding import Finding
from app.contracts.lead import LeadDTO
from app.contracts.scan import AuditReportDTO, CategoryScoreDTO
from app.leads.brief_generator import DEFAULT_RANKING_DISCLAIMER, ServiceBriefGenerator


@pytest.fixture
def mock_lead():
    return LeadDTO(
        id="lead-test-123",
        scan_token="scan-token-abc",
        customer_name="Sarah Connor",
        business_email="sarah@skynet-defense.com",
        phone_number="+1 555-999-8888",
        website_url="https://skynet-defense.com",
        business_category="Cybersecurity",
        target_city="Los Angeles, CA",
        requested_service="Code Remediation",
        problem_description="Discovered critical security headers and indexing directives failing on public assets.",
        urgency=LeadUrgency.CRITICAL,
        status=LeadStatus.NEW,
        consent_given=True,
        consent_timestamp=datetime.now(UTC),
        privacy_policy_version="2026-v1",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        status_history=[],
    )


@pytest.fixture
def mock_audit_report():
    evidence_fail = FindingEvidence(
        observedValue="<meta name='robots' content='noindex'>",
        expectedValue="Indexable without noindex directive",
        provenance=ProvenanceCategory.DIRECT_OBSERVATION,
        targetElement="head > meta[name='robots']",
        rawSnippet="<meta name='robots' content='noindex'>",
        httpStatusCode=200,
        responseTimeMs=120,
        lineNumber=10,
    )
    evidence_pass = FindingEvidence(
        observedValue="https://skynet-defense.com",
        expectedValue="https://skynet-defense.com",
        provenance=ProvenanceCategory.DIRECT_OBSERVATION,
        targetElement="head > link[rel='canonical']",
        rawSnippet="<link rel='canonical' href='https://skynet-defense.com'>",
        httpStatusCode=200,
        responseTimeMs=120,
        lineNumber=12,
    )

    finding_fail = Finding(
        ruleId="robots-meta-indexable",
        category=RuleCategory.INDEXABILITY,
        state=RuleState.FAIL,
        severity=IssueSeverity.CRITICAL,
        weight=10,
        title="Meta Robots Indexable",
        description="Checks that meta robots tag does not block indexing.",
        evidence=evidence_fail,
        remediationGuidance="Remove noindex from meta robots tag.",
    )
    finding_pass = Finding(
        ruleId="canonical-presence",
        category=RuleCategory.INDEXABILITY,
        state=RuleState.PASS,
        severity=IssueSeverity.HIGH,
        weight=8,
        title="Canonical Tag Presence",
        description="Checks that link rel canonical is present.",
        evidence=evidence_pass,
        remediationGuidance="Canonical tag is present.",
    )

    return AuditReportDTO(
        scanToken="scan-token-abc",
        targetUrl="https://skynet-defense.com",
        finalUrl="https://skynet-defense.com",
        statusCode=200,
        status=ScanStatus.COMPLETED,
        overallScore=68.5,
        categoryScores={
            RuleCategory.INDEXABILITY: CategoryScoreDTO(
                category=RuleCategory.INDEXABILITY,
                score=50.0,
                completeness=100.0,
                applicableChecks=2,
                evaluatedChecks=2,
            )
        },
        completenessScore=100.0,
        categoryAvailability={RuleCategory.INDEXABILITY: True},
        findings=[finding_fail, finding_pass],
        robotsSummary=None,
        sitemapSummary=None,
        isSpaDetected=False,
    )


def test_generate_brief_with_audit_report(mock_lead, mock_audit_report):
    """Verifies service brief generation combining lead and audit report."""
    generator = ServiceBriefGenerator()
    brief = generator.generate_brief(lead=mock_lead, audit_report=mock_audit_report)

    assert brief.brief_id is not None
    assert brief.lead_id == mock_lead.id
    assert brief.client_details.customer_name == "Sarah Connor"
    assert brief.audit_scope.has_audit_report is True
    assert brief.audit_scope.overall_health_score == 68.5
    assert len(brief.critical_issues) == 1
    assert brief.critical_issues[0].rule_id == "robots-meta-indexable"
    assert brief.critical_issues[0].severity == IssueSeverity.CRITICAL
    assert len(brief.implementation_priorities) > 0
    assert DEFAULT_RANKING_DISCLAIMER in brief.ranking_disclaimer
    assert len(brief.unknown_and_unavailable_disclosures) >= 4


def test_generate_brief_without_audit_report(mock_lead):
    """Verifies that missing audit report gracefully produces unmeasured scope without crashing."""
    generator = ServiceBriefGenerator()
    brief = generator.generate_brief(lead=mock_lead, audit_report=None)

    assert brief.audit_scope.has_audit_report is False
    assert brief.audit_scope.overall_health_score is None
    assert len(brief.critical_issues) == 0
    assert len(brief.proposed_solutions) == 0
    assert brief.ranking_disclaimer is not None


def test_export_markdown_formatting(mock_lead, mock_audit_report):
    """Verifies Markdown export formats headers, evidence snippets, and disclaimers."""
    generator = ServiceBriefGenerator()
    brief = generator.generate_brief(lead=mock_lead, audit_report=mock_audit_report)
    md = generator.export_markdown(brief)

    assert "# Technical SEO Consultation Brief:" in md
    assert "Sarah Connor" in md
    assert "Overall Health Score (Model E3):" in md
    assert "robots-meta-indexable" in md
    assert "```html" in md
    assert "STATUTORY DISCLAIMER" in md or "Ranking Disclaimer:" in md
