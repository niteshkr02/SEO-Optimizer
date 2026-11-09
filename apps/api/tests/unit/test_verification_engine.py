"""Unit tests for deterministic before/after verification engine and Model E33."""

from app.contracts.enums import (
    IssueSeverity,
    ProvenanceCategory,
    RuleCategory,
    RuleState,
)
from app.contracts.evidence import FindingEvidence
from app.contracts.finding import Finding
from app.contracts.scan import AuditReportDTO, CategoryScoreDTO
from app.verification.engine import VerificationEngine
from app.verification.models import VerificationTransition


def build_finding(rule_id: str, state: RuleState, category: RuleCategory = RuleCategory.CRAWLABILITY) -> Finding:
    return Finding(
        ruleId=rule_id,
        category=category,
        title=f"Rule {rule_id}",
        description="Test finding description",
        state=state,
        severity=IssueSeverity.HIGH,
        weight=8,
        evidence=FindingEvidence(
            observedValue=f"State: {state}",
            expectedValue="PASS",
            provenance=ProvenanceCategory.DIRECT_OBSERVATION,
        ),
        remediationGuidance=f"Remediation steps for {rule_id}",
    )



def test_verification_engine_correctly_classifies_transitions():
    """Verifies RESOLVED, UNRESOLVED, REGRESSED, and PERSISTENT_PASS transitions."""
    # Baseline findings:
    # - rule-1: FAIL
    # - rule-2: FAIL
    # - rule-3: PASS
    # - rule-4: PASS
    baseline_findings = [
        build_finding("rule-1", RuleState.FAIL),
        build_finding("rule-2", RuleState.FAIL),
        build_finding("rule-3", RuleState.PASS),
        build_finding("rule-4", RuleState.PASS),
    ]
    baseline_report = AuditReportDTO(
        scanToken="token-baseline",
        targetUrl="https://example.com",
        finalUrl="https://example.com",
        statusCode=200,
        overallScore=50.0,
        completenessScore=100.0,
        categoryScores={},
        categoryAvailability={},
        findings=baseline_findings,
    )

    # Post-change findings:
    # - rule-1: PASS (Resolved!)
    # - rule-2: FAIL (Unresolved)
    # - rule-3: FAIL (Regressed!)
    # - rule-4: PASS (Persistent Pass)
    post_findings = [
        build_finding("rule-1", RuleState.PASS),
        build_finding("rule-2", RuleState.FAIL),
        build_finding("rule-3", RuleState.FAIL),
        build_finding("rule-4", RuleState.PASS),
    ]
    post_report = AuditReportDTO(
        scanToken="token-post",
        targetUrl="https://example.com",
        finalUrl="https://example.com",
        statusCode=200,
        overallScore=60.0,
        completenessScore=100.0,
        categoryScores={},
        categoryAvailability={},
        findings=post_findings,
    )

    engine = VerificationEngine()
    ver_report = engine.compare_reports(baseline_report, post_report)

    transitions = {comp.ruleId: comp.transition for comp in ver_report.findingComparisons}

    assert transitions["rule-1"] == VerificationTransition.RESOLVED
    assert transitions["rule-2"] == VerificationTransition.UNRESOLVED
    assert transitions["rule-3"] == VerificationTransition.REGRESSED
    assert transitions["rule-4"] == VerificationTransition.PERSISTENT_PASS

    # Model E33: 2 attempted (rule-1, rule-2), 1 resolved -> IRR = 50.0%
    assert ver_report.totalAttempted == 2
    assert ver_report.resolvedCount == 1
    assert ver_report.unresolvedCount == 1
    assert ver_report.regressedCount == 1
    assert ver_report.issueResolutionRate == 50.0


def test_untested_findings_never_treated_as_resolved():
    """Strict Rule: If a post-change finding is UNKNOWN or NOT_TESTED, it must never be marked RESOLVED."""
    baseline_findings = [
        build_finding("rule-timeout", RuleState.FAIL),
    ]
    baseline_report = AuditReportDTO(
        scanToken="token-base-untested",
        targetUrl="https://example.com",
        finalUrl="https://example.com",
        statusCode=200,
        overallScore=40.0,
        completenessScore=100.0,
        categoryScores={},
        categoryAvailability={},
        findings=baseline_findings,
    )

    post_findings = [
        build_finding("rule-timeout", RuleState.UNKNOWN),
    ]
    post_report = AuditReportDTO(
        scanToken="token-post-untested",
        targetUrl="https://example.com",
        finalUrl="https://example.com",
        statusCode=200,
        overallScore=40.0,
        completenessScore=80.0,
        categoryScores={},
        categoryAvailability={},
        findings=post_findings,
    )

    engine = VerificationEngine()
    ver_report = engine.compare_reports(baseline_report, post_report)

    assert ver_report.resolvedCount == 0
    assert ver_report.issueResolutionRate == 0.0
    comp = ver_report.findingComparisons[0]
    assert comp.transition == VerificationTransition.UNKNOWN


def test_score_deltas_calculation():
    """Verifies that overall score, completeness, and category deltas are correctly calculated."""
    cat_base = {
        RuleCategory.INDEXABILITY: CategoryScoreDTO(category=RuleCategory.INDEXABILITY, score=70.0),
    }
    cat_post = {
        RuleCategory.INDEXABILITY: CategoryScoreDTO(category=RuleCategory.INDEXABILITY, score=90.0),
    }

    baseline_report = AuditReportDTO(
        scanToken="token-base-delta",
        targetUrl="https://example.com",
        finalUrl="https://example.com",
        statusCode=200,
        overallScore=65.0,
        completenessScore=90.0,
        categoryScores=cat_base,
        categoryAvailability={RuleCategory.INDEXABILITY: True},
        findings=[],
    )

    post_report = AuditReportDTO(
        scanToken="token-post-delta",
        targetUrl="https://example.com",
        finalUrl="https://example.com",
        statusCode=200,
        overallScore=85.0,
        completenessScore=100.0,
        categoryScores=cat_post,
        categoryAvailability={RuleCategory.INDEXABILITY: True},
        findings=[],
    )

    engine = VerificationEngine()
    ver_report = engine.compare_reports(baseline_report, post_report)

    assert ver_report.overallScoreDelta.baselineScore == 65.0
    assert ver_report.overallScoreDelta.postChangeScore == 85.0
    assert ver_report.overallScoreDelta.delta == 20.0

    assert ver_report.completenessDelta.delta == 10.0
    assert ver_report.categoryDeltas[RuleCategory.INDEXABILITY].delta == 20.0


def test_export_markdown_report_formatting():
    """Verifies that export_markdown_report generates a valid GitHub Flavored Markdown document."""
    baseline_report = AuditReportDTO(
        scanToken="token-md-base",
        targetUrl="https://example.com",
        finalUrl="https://example.com",
        statusCode=200,
        overallScore=60.0,
        completenessScore=100.0,
        categoryScores={},
        categoryAvailability={},
        findings=[build_finding("title-presence", RuleState.FAIL)],
    )

    post_report = AuditReportDTO(
        scanToken="token-md-post",
        targetUrl="https://example.com",
        finalUrl="https://example.com",
        statusCode=200,
        overallScore=90.0,
        completenessScore=100.0,
        categoryScores={},
        categoryAvailability={},
        findings=[build_finding("title-presence", RuleState.PASS)],
    )

    engine = VerificationEngine()
    ver_report = engine.compare_reports(baseline_report, post_report)
    md_content = engine.export_markdown_report(ver_report)

    assert "# SEO Optimizer — Post-Deployment Verification Report" in md_content
    assert "Issue Resolution Rate (IRR)" in md_content
    assert "100.0%" in md_content
    assert "`title-presence`" in md_content
    assert "**RESOLVED**" in md_content
