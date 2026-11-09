"""Unit tests for Mathematical Model E2: Category Weighted SEO Health Score."""

from app.contracts.enums import (
    IssueSeverity,
    ProvenanceCategory,
    RuleCategory,
    RuleState,
)
from app.contracts.evidence import FindingEvidence
from app.contracts.finding import Finding
from app.scoring.category import calculate_category_score


def create_mock_finding(
    rule_id: str,
    category: RuleCategory,
    state: RuleState,
    weight: int = 5,
) -> Finding:
    return Finding(
        ruleId=rule_id,
        category=category,
        title=f"Rule {rule_id}",
        description="Description",
        state=state,
        severity=IssueSeverity.HIGH,
        weight=weight,
        evidence=FindingEvidence(
            observedValue=state.value,
            expectedValue="PASS",
            provenance=ProvenanceCategory.DIRECT_OBSERVATION,
        ),
        remediationGuidance="None",
    )


def test_e2_all_pass_returns_100():
    findings = [
        create_mock_finding("r1", RuleCategory.CRAWLABILITY, RuleState.PASS, weight=10),
        create_mock_finding("r2", RuleCategory.CRAWLABILITY, RuleState.PASS, weight=5),
    ]
    res = calculate_category_score(RuleCategory.CRAWLABILITY, findings)
    assert res.score == 100.0
    assert res.applicable_checks == 2
    assert res.evaluated_checks == 2


def test_e2_all_fail_returns_0():
    findings = [
        create_mock_finding("r1", RuleCategory.CRAWLABILITY, RuleState.FAIL, weight=8),
        create_mock_finding("r2", RuleCategory.CRAWLABILITY, RuleState.FAIL, weight=2),
    ]
    res = calculate_category_score(RuleCategory.CRAWLABILITY, findings)
    assert res.score == 0.0


def test_e2_weighted_calculation():
    # r1 weight 10 PASS (10 * 1 = 10)
    # r2 weight 5 FAIL (5 * 0 = 0)
    # total weight = 15. Score = 100 * (10 / 15) = 66.67
    findings = [
        create_mock_finding("r1", RuleCategory.INDEXABILITY, RuleState.PASS, weight=10),
        create_mock_finding("r2", RuleCategory.INDEXABILITY, RuleState.FAIL, weight=5),
    ]
    res = calculate_category_score(RuleCategory.INDEXABILITY, findings)
    assert res.score == 66.67


def test_e2_excludes_unknown_not_tested_not_applicable_from_denominator():
    # r1 PASS w=10
    # r2 UNKNOWN w=10 (excluded)
    # r3 NOT_APPLICABLE w=10 (excluded)
    # Denominator should be 10, not 30! Score = 100.0
    findings = [
        create_mock_finding("r1", RuleCategory.DOCUMENT, RuleState.PASS, weight=10),
        create_mock_finding("r2", RuleCategory.DOCUMENT, RuleState.UNKNOWN, weight=10),
        create_mock_finding("r3", RuleCategory.DOCUMENT, RuleState.NOT_APPLICABLE, weight=10),
    ]
    res = calculate_category_score(RuleCategory.DOCUMENT, findings)
    assert res.score == 100.0
    assert res.applicable_checks == 2  # r1 and r2
    assert res.evaluated_checks == 1   # r1


def test_e2_zero_denominator_returns_none():
    """When all checks are UNKNOWN or NOT_APPLICABLE, score must be None (NULL), never 0.0."""
    findings = [
        create_mock_finding("r1", RuleCategory.CONTENT, RuleState.UNKNOWN, weight=5),
        create_mock_finding("r2", RuleCategory.CONTENT, RuleState.NOT_APPLICABLE, weight=5),
    ]
    res = calculate_category_score(RuleCategory.CONTENT, findings)
    assert res.score is None

