"""Mathematical Model E2: Category Weighted SEO Health Score."""

from pydantic import BaseModel, ConfigDict, Field

from app.contracts.enums import RuleCategory, RuleState
from app.contracts.finding import Finding
from app.rules.evaluator import map_check_quality

FORMULA_ID = "E2"
FORMULA_VERSION = "1.0.0"


class CategoryScoreResult(BaseModel):
    """Result of computing Mathematical Model E2 for a specific category."""

    model_config = ConfigDict(frozen=True)

    formula_id: str = FORMULA_ID
    formula_version: str = FORMULA_VERSION
    category: RuleCategory
    score: float | None = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="Category score (0-100), or None if no applicable checks evaluated.",
    )
    total_checks: int = Field(default=0, ge=0)
    applicable_checks: int = Field(default=0, ge=0)
    evaluated_checks: int = Field(default=0, ge=0)
    weight_sum_evaluated: float = Field(default=0.0, ge=0.0)
    weighted_quality_sum: float = Field(default=0.0, ge=0.0)


def calculate_category_score(
    category: RuleCategory,
    findings: list[Finding],
) -> CategoryScoreResult:
    """Calculates Category Weighted SEO Health Score according to Model E2.

    Mathematical Formulation:
    S_c = 100 * (sum(w_i * q_i)) / (sum(w_i))
    over all applicable evaluated checks (q_i != None).

    Invariants:
    - UNKNOWN, NOT_TESTED, and NOT_APPLICABLE are excluded from the score denominator.
    - If sum(w_i) == 0 (no applicable checks evaluated), S_c is None (NULL), never 0.0.
    - Score is strictly clamped to [0.0, 100.0].
    """
    category_findings = [f for f in findings if f.category == category]
    total_checks = len(category_findings)

    applicable_checks = 0
    evaluated_checks = 0
    weight_sum_evaluated = 0.0
    weighted_quality_sum = 0.0

    for finding in category_findings:
        if finding.state == RuleState.NOT_APPLICABLE:
            continue

        applicable_checks += 1
        q_i = map_check_quality(finding.state)

        if q_i is not None:
            evaluated_checks += 1
            weight_sum_evaluated += float(finding.weight)
            weighted_quality_sum += float(finding.weight) * q_i

    if weight_sum_evaluated == 0.0:
        return CategoryScoreResult(
            category=category,
            score=None,
            total_checks=total_checks,
            applicable_checks=applicable_checks,
            evaluated_checks=evaluated_checks,
            weight_sum_evaluated=0.0,
            weighted_quality_sum=0.0,
        )

    raw_score = (weighted_quality_sum / weight_sum_evaluated) * 100.0
    clamped_score = max(0.0, min(100.0, round(raw_score, 2)))

    return CategoryScoreResult(
        category=category,
        score=clamped_score,
        total_checks=total_checks,
        applicable_checks=applicable_checks,
        evaluated_checks=evaluated_checks,
        weight_sum_evaluated=weight_sum_evaluated,
        weighted_quality_sum=weighted_quality_sum,
    )
