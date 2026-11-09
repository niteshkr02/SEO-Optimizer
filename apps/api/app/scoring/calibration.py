"""Mathematical Model E4: Legacy Severity-Deduction Model (Calibration Only)."""

from pydantic import BaseModel, ConfigDict, Field

from app.contracts.enums import IssueSeverity, RuleState
from app.contracts.finding import Finding

FORMULA_ID = "E4"
FORMULA_VERSION = "1.0.0"

# Initial candidate deduction values from PRD
SEVERITY_DEDUCTIONS = {
    IssueSeverity.CRITICAL: 25,
    IssueSeverity.HIGH: 15,
    IssueSeverity.MEDIUM: 8,
    IssueSeverity.LOW: 3,
    IssueSeverity.INFO: 0,
}


class LegacyDeductionResult(BaseModel):
    """Result of computing Mathematical Model E4."""

    model_config = ConfigDict(frozen=True)

    formula_id: str = FORMULA_ID
    formula_version: str = FORMULA_VERSION
    deduction_score: float = Field(
        ..., ge=0.0, le=100.0, description="Deduction score (0-100)."
    )
    total_deductions: int = Field(default=0, ge=0)
    failed_checks_count: int = Field(default=0, ge=0)


def calculate_legacy_deduction_score(findings: list[Finding]) -> LegacyDeductionResult:
    """Calculates the Legacy Severity-Deduction Model according to Model E4.

    Formulation:
    S_d = max(0, 100 - sum(d(s_i))) for all findings with state == FAIL.

    Invariants:
    - Floored at 0.0 (never negative).
    - Kept strictly for calibration/comparison; never combined with E2/E3.
    """
    total_deductions = 0
    failed_checks = 0

    for finding in findings:
        if finding.state == RuleState.FAIL:
            failed_checks += 1
            deduction = SEVERITY_DEDUCTIONS.get(finding.severity, 0)
            total_deductions += deduction

    score = max(0.0, float(100 - total_deductions))

    return LegacyDeductionResult(
        deduction_score=score,
        total_deductions=total_deductions,
        failed_checks_count=failed_checks,
    )
