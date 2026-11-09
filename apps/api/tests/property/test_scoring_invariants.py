"""Property-based tests verifying mathematical scoring invariants using Hypothesis."""

from hypothesis import given
from hypothesis import strategies as st

from app.contracts.enums import (
    IssueSeverity,
    ProvenanceCategory,
    RuleCategory,
    RuleState,
)
from app.contracts.evidence import FindingEvidence
from app.contracts.finding import Finding
from app.scoring.category import calculate_category_score
from app.scoring.completeness import calculate_report_completeness
from app.scoring.overall import calculate_overall_health_score

rule_states = st.sampled_from([
    RuleState.PASS,
    RuleState.FAIL,
    RuleState.UNKNOWN,
    RuleState.NOT_TESTED,
    RuleState.NOT_APPLICABLE,
])

categories = st.sampled_from([
    RuleCategory.CRAWLABILITY,
    RuleCategory.INDEXABILITY,
    RuleCategory.DOCUMENT,
    RuleCategory.CONTENT,
    RuleCategory.STRUCTURED,
])


def finding_strategy(cat: RuleCategory):
    return st.builds(
        Finding,
        ruleId=st.text(min_size=1, max_size=20),
        category=st.just(cat),
        title=st.text(min_size=1, max_size=30),
        description=st.text(min_size=1, max_size=50),
        state=rule_states,
        severity=st.sampled_from(list(IssueSeverity)),
        weight=st.integers(min_value=1, max_value=10),
        evidence=st.just(
            FindingEvidence(
                observedValue="val",
                expectedValue="exp",
                provenance=ProvenanceCategory.DIRECT_OBSERVATION,
            )
        ),
        remediationGuidance=st.text(min_size=1, max_size=30),
    )


@given(st.lists(finding_strategy(RuleCategory.CRAWLABILITY), min_size=0, max_size=50))
def test_category_score_is_always_bounded_or_none(findings):
    """Property: Category score Sc must strictly be in [0.0, 100.0] or None."""
    res = calculate_category_score(RuleCategory.CRAWLABILITY, findings)
    if res.score is not None:
        assert 0.0 <= res.score <= 100.0
    else:
        assert res.weight_sum_evaluated == 0.0


@given(
    st.dictionaries(
        keys=categories,
        values=st.one_of(st.none(), st.floats(min_value=0.0, max_value=100.0, allow_nan=False)),
        max_size=5,
    )
)
def test_overall_score_is_always_bounded_or_none(category_scores):
    """Property: Overall score S must strictly be in [0.0, 100.0] or None."""
    res = calculate_overall_health_score(category_scores)
    if res.overall_score is not None:
        assert 0.0 <= res.overall_score <= 100.0
    else:
        # None only if 0 available categories
        assert res.available_categories_count == 0


@given(st.lists(finding_strategy(RuleCategory.INDEXABILITY), min_size=0, max_size=50))
def test_completeness_is_always_bounded_or_none(findings):
    """Property: Completeness C must strictly be in [0.0, 100.0] or None."""
    res = calculate_report_completeness(findings)
    if res.completeness_score is not None:
        assert 0.0 <= res.completeness_score <= 100.0
    else:
        assert res.applicable_weight == 0.0


@given(st.lists(st.integers(min_value=1, max_value=10), min_size=1, max_size=20))
def test_completeness_100_when_all_pass_or_fail(weights):
    """Property: If all applicable checks are PASS or FAIL, completeness is strictly 100.0%."""
    findings = [
        Finding(
            ruleId=f"r_{i}",
            category=RuleCategory.INDEXABILITY,
            title="T",
            description="D",
            state=RuleState.PASS if i % 2 == 0 else RuleState.FAIL,
            severity=IssueSeverity.HIGH,
            weight=w,
            evidence=FindingEvidence(
                observedValue="obs",
                expectedValue="exp",
                provenance=ProvenanceCategory.DIRECT_OBSERVATION,
            ),
            remediationGuidance="G",
        )
        for i, w in enumerate(weights)
    ]
    res = calculate_report_completeness(findings)
    assert res.completeness_score == 100.0

