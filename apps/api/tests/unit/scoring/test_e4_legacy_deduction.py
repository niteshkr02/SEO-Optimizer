"""Unit tests for Mathematical Model E4: Legacy Severity-Deduction Model."""

from app.contracts.enums import (
    IssueSeverity,
    ProvenanceCategory,
    RuleCategory,
    RuleState,
)
from app.contracts.evidence import FindingEvidence
from app.contracts.finding import Finding
from app.scoring.calibration import calculate_legacy_deduction_score


def create_failing_finding(severity: IssueSeverity) -> Finding:
    return Finding(
        ruleId=f"rule-{severity.value}",
        category=RuleCategory.CRAWLABILITY,
        title="Failing Rule",
        description="Fails",
        state=RuleState.FAIL,
        severity=severity,
        weight=5,
        evidence=FindingEvidence(
            observedValue="FAIL",
            expectedValue="PASS",
            provenance=ProvenanceCategory.DIRECT_OBSERVATION,
        ),
        remediationGuidance="Fix",
    )


def test_e4_zero_failures_returns_100():
    res = calculate_legacy_deduction_score([])
    assert res.deduction_score == 100.0
    assert res.total_deductions == 0
    assert res.failed_checks_count == 0


def test_e4_critical_and_high_deductions():
    # 1 CRITICAL (-25), 1 HIGH (-15) -> 100 - 40 = 60.0
    findings = [
        create_failing_finding(IssueSeverity.CRITICAL),
        create_failing_finding(IssueSeverity.HIGH),
    ]
    res = calculate_legacy_deduction_score(findings)
    assert res.deduction_score == 60.0
    assert res.total_deductions == 40
    assert res.failed_checks_count == 2


def test_e4_floored_at_zero():
    # 5 CRITICAL (-125) -> floor at 0.0
    findings = [create_failing_finding(IssueSeverity.CRITICAL) for _ in range(5)]
    res = calculate_legacy_deduction_score(findings)
    assert res.deduction_score == 0.0
    assert res.total_deductions == 125

