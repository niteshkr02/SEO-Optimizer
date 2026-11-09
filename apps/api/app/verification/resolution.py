"""Mathematical Model E33: Issue Resolution Rate (IRR)."""

from pydantic import BaseModel, ConfigDict, Field

FORMULA_ID = "E33"
FORMULA_VERSION = "1.0.0"


class IssueResolutionRateResult(BaseModel):
    """Result of computing Mathematical Model E33."""

    model_config = ConfigDict(frozen=True)

    formula_id: str = FORMULA_ID
    formula_version: str = FORMULA_VERSION
    total_attempted: int = Field(default=0, ge=0)
    verified_resolved: int = Field(default=0, ge=0)
    unresolved: int = Field(default=0, ge=0)
    irr_score: float | None = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="Issue Resolution Rate percentage on [0.0, 100.0], or None if 0 attempted.",
    )


def calculate_issue_resolution_rate(
    attempted_count: int,
    verified_resolved_count: int,
) -> IssueResolutionRateResult:
    """Calculates Issue Resolution Rate (IRR) according to Model E33.

    Formulation:
    IRR = 100 * (|F_verified_resolved|) / (|F_attempted|)

    Where:
    - F_attempted: Set of audit issues for which a code patch or remediation was attempted.
    - F_verified_resolved: Subset of attempted issues where post-deployment re-scan evaluates to PASS.

    Integrity Guard:
    - If attempted_count == 0, IRR is None (NULL) to prevent division by zero.
    - verified_resolved_count cannot exceed attempted_count.
    - Strictly clamped to [0.0, 100.0].
    """
    if attempted_count <= 0:
        return IssueResolutionRateResult(
            total_attempted=0,
            verified_resolved=0,
            unresolved=0,
            irr_score=None,
        )

    resolved = min(max(0, verified_resolved_count), attempted_count)
    unresolved = attempted_count - resolved

    raw_irr = (resolved / attempted_count) * 100.0
    irr = max(0.0, min(100.0, round(raw_irr, 2)))

    return IssueResolutionRateResult(
        total_attempted=attempted_count,
        verified_resolved=resolved,
        unresolved=unresolved,
        irr_score=irr,
    )

