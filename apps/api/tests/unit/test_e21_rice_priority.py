"""Unit tests for Mathematical Model E21: Resolution Priority (RICE-inspired)."""

from app.contracts.enums import IssueSeverity
from app.resolution.priority import (
    FORMULA_ID,
    FORMULA_VERSION,
    calculate_resolution_priority,
)


def test_e21_model_metadata():
    """Verifies formula identifier and versioning invariants."""
    res = calculate_resolution_priority(reach=5.0, impact=3.0)
    assert res.formula_id == FORMULA_ID == "E21"
    assert res.formula_version == FORMULA_VERSION == "1.0.0"


def test_e21_standard_calculation():
    """Formula: (R * I * C) / E.

    R=10.0, I=CRITICAL (5.0), C=1.0, E=2.0 -> (10 * 5 * 1.0) / 2.0 = 25.0
    """
    res = calculate_resolution_priority(
        reach=10.0,
        impact=IssueSeverity.CRITICAL,
        confidence=1.0,
        effort=2.0,
    )
    assert res.priority_score == 25.0


def test_e21_severity_enum_mapping():
    """Verifies mapping of IssueSeverity to numeric impact values."""
    res_crit = calculate_resolution_priority(reach=1.0, impact=IssueSeverity.CRITICAL, effort=1.0)
    res_high = calculate_resolution_priority(reach=1.0, impact=IssueSeverity.HIGH, effort=1.0)
    res_med = calculate_resolution_priority(reach=1.0, impact=IssueSeverity.MEDIUM, effort=1.0)
    res_low = calculate_resolution_priority(reach=1.0, impact=IssueSeverity.LOW, effort=1.0)
    res_info = calculate_resolution_priority(reach=1.0, impact=IssueSeverity.INFO, effort=1.0)

    assert res_crit.impact == 5.0
    assert res_high.impact == 4.0
    assert res_med.impact == 3.0
    assert res_low.impact == 2.0
    assert res_info.impact == 1.0


def test_e21_zero_denominator_guard():
    """Effort <= 0.0 must be floored to 1.0 to prevent division by zero."""
    res_zero = calculate_resolution_priority(reach=5.0, impact=3.0, effort=0.0)
    assert res_zero.effort == 1.0
    assert res_zero.priority_score == 15.0

    res_negative = calculate_resolution_priority(reach=5.0, impact=3.0, effort=-10.0)
    assert res_negative.effort == 1.0
    assert res_negative.priority_score == 15.0


def test_e21_reach_and_confidence_clamping():
    """Reach is clamped to [1.0, 10.0], confidence to [0.1, 1.0]."""
    res_clamped = calculate_resolution_priority(
        reach=50.0,  # Clamped to 10.0
        impact=10.0,  # Clamped to 5.0
        confidence=2.0,  # Clamped to 1.0
        effort=1.0,
    )
    assert res_clamped.reach == 10.0
    assert res_clamped.impact == 5.0
    assert res_clamped.confidence == 1.0
    assert res_clamped.priority_score == 50.0

