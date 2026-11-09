"""Mathematical Model E21: Resolution Priority (RICE-inspired)."""

from pydantic import BaseModel, ConfigDict, Field

from app.contracts.enums import IssueSeverity

FORMULA_ID = "E21"
FORMULA_VERSION = "1.0.0"

SEVERITY_IMPACT_MAP: dict[IssueSeverity, float] = {
    IssueSeverity.CRITICAL: 5.0,
    IssueSeverity.HIGH: 4.0,
    IssueSeverity.MEDIUM: 3.0,
    IssueSeverity.LOW: 2.0,
    IssueSeverity.INFO: 1.0,
}


class ResolutionPriorityResult(BaseModel):
    """Result of computing Mathematical Model E21."""

    model_config = ConfigDict(frozen=True)

    formula_id: str = FORMULA_ID
    formula_version: str = FORMULA_VERSION
    reach: float = Field(default=1.0, ge=1.0, le=10.0)
    impact: float = Field(default=1.0, ge=1.0, le=5.0)
    confidence: float = Field(default=1.0, ge=0.1, le=1.0)
    effort: float = Field(default=1.0, ge=1.0)
    priority_score: float = Field(
        default=0.0,
        ge=0.0,
        description="RICE-inspired priority score: (R * I * C) / E.",
    )


def calculate_resolution_priority(
    reach: float,
    impact: float | IssueSeverity,
    confidence: float = 1.0,
    effort: float = 1.0,
) -> ResolutionPriorityResult:
    """Calculates Resolution Priority according to Model E21.

    Formulation:
    P_priority = (R * I * C) / E

    Where:
    - R: Reach (scale 1.0 to 10.0, e.g. site-wide impact vs single-page).
    - I: Impact (scale 1.0 to 5.0, directly mapped from IssueSeverity or custom numeric).
    - C: Evidence confidence factor (0.5 for indirect/heuristic, 0.8 for high, 1.0 for direct proof).
    - E: Estimated engineering effort (hours or points, strictly floored at 1.0 to prevent division by zero).

    Null and Denominator Guard:
    - Effort E is constrained to E >= 1.0. If effort <= 0.0 or None, it is floored at 1.0.
    """
    r = max(1.0, min(10.0, float(reach)))

    if isinstance(impact, IssueSeverity):
        i = SEVERITY_IMPACT_MAP.get(impact, 3.0)
    else:
        i = max(1.0, min(5.0, float(impact)))

    c = max(0.1, min(1.0, float(confidence)))
    e = max(1.0, float(effort))  # Floor at 1.0 to prevent division by zero

    raw_priority = (r * i * c) / e
    priority = max(0.0, round(raw_priority, 2))

    return ResolutionPriorityResult(
        reach=r,
        impact=i,
        confidence=c,
        effort=e,
        priority_score=priority,
    )

