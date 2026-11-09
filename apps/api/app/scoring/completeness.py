"""Mathematical Model E5: Report Completeness Index."""

from pydantic import BaseModel, ConfigDict, Field

from app.contracts.enums import RuleState
from app.contracts.finding import Finding

FORMULA_ID = "E5"
FORMULA_VERSION = "1.0.0"


class CompletenessResult(BaseModel):
    """Result of computing Mathematical Model E5."""

    model_config = ConfigDict(frozen=True)

    formula_id: str = FORMULA_ID
    formula_version: str = FORMULA_VERSION
    completeness_score: float | None = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="Completeness percentage (0-100), or None if no applicable checks.",
    )
    evaluated_weight: float = Field(default=0.0, ge=0.0)
    applicable_weight: float = Field(default=0.0, ge=0.0)
    unverified_checks_count: int = Field(default=0, ge=0)


def calculate_report_completeness(findings: list[Finding]) -> CompletenessResult:
    """Calculates the Report Completeness Index according to Model E5.

    Formulation:
    C = 100 * (sum w_i [check i evaluated]) / (sum w_i [check i applicable])
    where evaluated is PASS or FAIL or PARTIAL.
    UNKNOWN and NOT_TESTED are unverified.
    NOT_APPLICABLE is excluded from both numerator and denominator.

    Invariants:
    - If no applicable checks apply (denominator 0), C is None (NULL).
    - If all applicable checks evaluated to PASS or FAIL, C is 100.0.
    """
    evaluated_weight = 0.0
    applicable_weight = 0.0
    unverified_count = 0

    for finding in findings:
        if finding.state == RuleState.NOT_APPLICABLE:
            continue

        w = float(finding.weight)
        applicable_weight += w

        if finding.state in {RuleState.PASS, RuleState.FAIL}:
            evaluated_weight += w
        else:
            # UNKNOWN or NOT_TESTED
            unverified_count += 1

    if applicable_weight == 0.0:
        return CompletenessResult(
            completeness_score=None,
            evaluated_weight=0.0,
            applicable_weight=0.0,
            unverified_checks_count=0,
        )

    raw_c = (evaluated_weight / applicable_weight) * 100.0
    clamped_c = max(0.0, min(100.0, round(raw_c, 2)))

    return CompletenessResult(
        completeness_score=clamped_c,
        evaluated_weight=evaluated_weight,
        applicable_weight=applicable_weight,
        unverified_checks_count=unverified_count,
    )
