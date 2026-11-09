"""Property-based invariant tests for Models E20, E21, and E33 using Hypothesis."""

from hypothesis import given
from hypothesis import strategies as st

from app.resolution.priority import calculate_resolution_priority
from app.resolution.triage import calculate_root_cause_triage
from app.verification.resolution import calculate_issue_resolution_rate


@given(
    evidence=st.floats(allow_nan=False, allow_infinity=False),
    reproducibility=st.floats(allow_nan=False, allow_infinity=False),
    persistence=st.floats(allow_nan=False, allow_infinity=False),
    scope=st.floats(allow_nan=False, allow_infinity=False),
)
def test_e20_triage_score_always_bounded_in_0_to_100(
    evidence: float,
    reproducibility: float,
    persistence: float,
    scope: float,
):
    """Model E20 invariant: RC is strictly in [0.0, 100.0] for any floating point inputs."""
    res = calculate_root_cause_triage(
        evidence_strength=evidence,
        reproducibility=reproducibility,
        persistence=persistence,
        scope=scope,
    )
    assert 0.0 <= res.rc_score <= 100.0


@given(
    reach=st.floats(allow_nan=False, allow_infinity=False),
    impact=st.floats(allow_nan=False, allow_infinity=False),
    confidence=st.floats(allow_nan=False, allow_infinity=False),
    effort=st.floats(allow_nan=False, allow_infinity=False),
)
def test_e21_priority_score_always_non_negative_and_never_divides_by_zero(
    reach: float,
    impact: float,
    confidence: float,
    effort: float,
):
    """Model E21 invariant: P_priority is always non-negative and effort floor prevents ZeroDivisionError."""
    res = calculate_resolution_priority(
        reach=reach,
        impact=impact,
        confidence=confidence,
        effort=effort,
    )
    assert res.priority_score >= 0.0
    assert res.effort >= 1.0


@given(
    attempted=st.integers(min_value=-1000, max_value=10000),
    resolved=st.integers(min_value=-1000, max_value=10000),
)
def test_e33_irr_always_bounded_or_none(attempted: int, resolved: int):
    """Model E33 invariant: IRR is either None (when attempted <= 0) or bounded in [0.0, 100.0]."""
    res = calculate_issue_resolution_rate(
        attempted_count=attempted,
        verified_resolved_count=resolved,
    )
    if attempted <= 0:
        assert res.irr_score is None
    else:
        assert res.irr_score is not None
        assert 0.0 <= res.irr_score <= 100.0
