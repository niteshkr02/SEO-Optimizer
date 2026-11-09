"""Unit tests for Mathematical Model E1: Deterministic Check Values."""

from app.contracts.enums import RuleState
from app.rules.evaluator import map_check_quality


def test_e1_pass_maps_to_one():
    """PASS must evaluate to q_i = 1.0."""
    assert map_check_quality(RuleState.PASS) == 1.0


def test_e1_fail_maps_to_zero():
    """FAIL must evaluate to q_i = 0.0."""
    assert map_check_quality(RuleState.FAIL) == 0.0


def test_e1_partial_maps_to_defined_scalar():
    """PARTIAL maps to explicitly defined scalar in [0.0, 1.0]."""
    assert map_check_quality(RuleState.PASS, partial_credit=0.75) == 1.0  # PASS takes precedence
    assert map_check_quality(RuleState.UNKNOWN, partial_credit=0.5) == 0.5


def test_e1_unverified_and_na_map_to_none():
    """UNKNOWN, NOT_TESTED, and NOT_APPLICABLE must never map to 0 or 1."""
    assert map_check_quality(RuleState.UNKNOWN) is None
    assert map_check_quality(RuleState.NOT_TESTED) is None
    assert map_check_quality(RuleState.NOT_APPLICABLE) is None

