"""Unit tests for Mathematical Model E5: Report Completeness Index."""

from app.contracts.enums import (
    IssueSeverity,
    ProvenanceCategory,
    RuleCategory,
    RuleState,
)
from app.contracts.evidence import FindingEvidence
from app.contracts.finding import Finding
from app.scoring.completeness import calculate_report_completeness


def create_finding(state: RuleState, weight: int = 5) -> Finding:
    return Finding(
        ruleId=f"rule-{state.value}",
        category=RuleCategory.INDEXABILITY,
        title="Rule",
        description="Rule",
        state=state,
        severity=IssueSeverity.MEDIUM,
        weight=weight,
        evidence=FindingEvidence(
            observedValue=state.value,
            expectedValue="PASS",
            provenance=ProvenanceCategory.DIRECT_OBSERVATION,
        ),
        remediationGuidance="None",
    )


def test_e5_all_evaluated_returns_100():
    findings = [
        create_finding(RuleState.PASS, weight=5),
        create_finding(RuleState.FAIL, weight=5),
    ]
    res = calculate_report_completeness(findings)
    assert res.completeness_score == 100.0
    assert res.unverified_checks_count == 0


def test_e5_partial_completeness_with_unknown():
    # 1 PASS (w=10), 1 UNKNOWN (w=10) -> evaluated=10, applicable=20 -> C = 50.0%
    findings = [
        create_finding(RuleState.PASS, weight=10),
        create_finding(RuleState.UNKNOWN, weight=10),
    ]
    res = calculate_report_completeness(findings)
    assert res.completeness_score == 50.0
    assert res.unverified_checks_count == 1


def test_e5_excludes_not_applicable_from_denominator():
    # 1 PASS (w=10), 1 NOT_APPLICABLE (w=10, excluded) -> C = 100.0%
    findings = [
        create_finding(RuleState.PASS, weight=10),
        create_finding(RuleState.NOT_APPLICABLE, weight=10),
    ]
    res = calculate_report_completeness(findings)
    assert res.completeness_score == 100.0
    assert res.applicable_weight == 10.0


def test_e5_zero_applicable_checks_returns_none():
    findings = [
        create_finding(RuleState.NOT_APPLICABLE, weight=10),
    ]
    res = calculate_report_completeness(findings)
    assert res.completeness_score is None

