"""Verification engine, before/after comparisons, and resolution metrics package."""

from app.verification.engine import (
    VerificationEngine,
    calculate_score_delta,
    default_verification_engine,
)
from app.verification.models import (
    FindingComparisonDTO,
    ScoreDeltaDTO,
    VerificationReportDTO,
    VerificationTransition,
)
from app.verification.resolution import (
    IssueResolutionRateResult,
    calculate_issue_resolution_rate,
)

__all__ = [
    "FindingComparisonDTO",
    "IssueResolutionRateResult",
    "ScoreDeltaDTO",
    "VerificationEngine",
    "VerificationReportDTO",
    "VerificationTransition",
    "calculate_issue_resolution_rate",
    "calculate_score_delta",
    "default_verification_engine",
]
