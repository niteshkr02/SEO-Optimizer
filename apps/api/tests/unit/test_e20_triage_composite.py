"""Unit tests for Mathematical Model E20: Root-Cause Triage Composite (RC)."""

from app.resolution.triage import (
    FORMULA_ID,
    FORMULA_VERSION,
    calculate_root_cause_triage,
)


def test_e20_model_metadata():
    """Verifies formula identifier and versioning invariants."""
    res = calculate_root_cause_triage(evidence_strength=100.0)
    assert res.formula_id == FORMULA_ID == "E20"
    assert res.formula_version == FORMULA_VERSION == "1.0.0"


def test_e20_maximum_inputs():
    """All maximum inputs (100) yield a score of 100.0."""
    res = calculate_root_cause_triage(
        evidence_strength=100.0,
        reproducibility=100.0,
        persistence=100.0,
        scope=100.0,
    )
    assert res.rc_score == 100.0


def test_e20_minimum_inputs():
    """All zero inputs yield a score of 0.0."""
    res = calculate_root_cause_triage(
        evidence_strength=0.0,
        reproducibility=0.0,
        persistence=0.0,
        scope=0.0,
    )
    assert res.rc_score == 0.0


def test_e20_weighted_calculation():
    """Formulation: 0.40*E + 0.25*P + 0.20*H + 0.15*S."""
    # 0.40*80 + 0.25*100 + 0.20*100 + 0.15*50 = 32 + 25 + 20 + 7.5 = 84.5
    res = calculate_root_cause_triage(
        evidence_strength=80.0,
        reproducibility=100.0,
        persistence=100.0,
        scope=50.0,
    )
    assert res.rc_score == 84.5


def test_e20_input_clamping():
    """Out-of-bounds inputs (<0 or >100) are strictly clamped."""
    res_high = calculate_root_cause_triage(
        evidence_strength=250.0,
        reproducibility=150.0,
        persistence=200.0,
        scope=300.0,
    )
    assert res_high.rc_score == 100.0

    res_low = calculate_root_cause_triage(
        evidence_strength=-50.0,
        reproducibility=-10.0,
        persistence=-5.0,
        scope=-100.0,
    )
    assert res_low.rc_score == 0.0

