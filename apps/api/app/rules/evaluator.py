"""Mathematical Model E1: Deterministic Check Values and Quality Mapping."""

from app.contracts.enums import RuleState


def map_check_quality(
    state: RuleState, partial_credit: float | None = None
) -> float | None:
    """Mathematical Model E1: Maps a 5-state audit rule outcome to quality scalar q_i in [0.0, 1.0].

    Formulation:
    - PASS: q_i = 1.0
    - FAIL: q_i = 0.0
    - PARTIAL: q_i = p_i (where p_i in [0.0, 1.0] is rule-defined)
    - UNKNOWN: q_i = None (excluded from score denominator, lowers completeness)
    - NOT_TESTED: q_i = None (excluded from score denominator, lowers completeness)
    - NOT_APPLICABLE: q_i = None (excluded from both score and completeness denominators)

    Invariants:
    - UNKNOWN, NOT_TESTED, and NOT_APPLICABLE must NEVER map to 0.0 or 1.0.
    """
    if state == RuleState.PASS:
        return 1.0

    if state == RuleState.FAIL:
        return 0.0

    if partial_credit is not None and 0.0 <= partial_credit <= 1.0:
        return partial_credit

    # UNKNOWN, NOT_TESTED, NOT_APPLICABLE
    return None
