"""Unit tests for Mathematical Model E33: Issue Resolution Rate (IRR)."""

from app.verification.resolution import (
    FORMULA_ID,
    FORMULA_VERSION,
    calculate_issue_resolution_rate,
)


def test_e33_model_metadata():
    """Verifies formula identifier and versioning invariants."""
    res = calculate_issue_resolution_rate(attempted_count=5, verified_resolved_count=5)
    assert res.formula_id == FORMULA_ID == "E33"
    assert res.formula_version == FORMULA_VERSION == "1.0.0"


def test_e33_zero_attempted_returns_none():
    """Integrity Guard: 0 attempted issues yields None (NULL) to prevent division by zero."""
    res = calculate_issue_resolution_rate(attempted_count=0, verified_resolved_count=0)
    assert res.irr_score is None
    assert res.total_attempted == 0
    assert res.verified_resolved == 0
    assert res.unresolved == 0


def test_e33_negative_attempted_returns_none():
    """Negative input yields None (NULL)."""
    res = calculate_issue_resolution_rate(attempted_count=-5, verified_resolved_count=0)
    assert res.irr_score is None


def test_e33_full_resolution_yields_100():
    """All attempted issues resolved = 100.0%."""
    res = calculate_issue_resolution_rate(attempted_count=8, verified_resolved_count=8)
    assert res.irr_score == 100.0
    assert res.unresolved == 0


def test_e33_zero_resolution_yields_0():
    """Zero attempted issues resolved = 0.0%."""
    res = calculate_issue_resolution_rate(attempted_count=10, verified_resolved_count=0)
    assert res.irr_score == 0.0
    assert res.unresolved == 10


def test_e33_partial_resolution():
    """Partial resolution calculation (3 of 4 = 75.0%)."""
    res = calculate_issue_resolution_rate(attempted_count=4, verified_resolved_count=3)
    assert res.irr_score == 75.0
    assert res.unresolved == 1


def test_e33_resolved_cannot_exceed_attempted():
    """Verified resolved count is capped at total attempted count."""
    res = calculate_issue_resolution_rate(attempted_count=5, verified_resolved_count=10)
    assert res.verified_resolved == 5
    assert res.irr_score == 100.0

