"""Domain transfer models for audit verification and before/after comparisons."""

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.contracts.enums import RuleCategory, RuleState


class VerificationTransition(str, Enum):
    """Lifecycle transition state of a finding between baseline and post-change."""

    RESOLVED = "RESOLVED"
    UNRESOLVED = "UNRESOLVED"
    REGRESSED = "REGRESSED"
    PERSISTENT_PASS = "PERSISTENT_PASS"
    UNKNOWN = "UNKNOWN"
    NOT_RECHECKED = "NOT_RECHECKED"


class ScoreDeltaDTO(BaseModel):
    """Measurable change in score between baseline and post-change audits."""

    model_config = ConfigDict(frozen=True)

    baselineScore: float | None = Field(default=None)
    postChangeScore: float | None = Field(default=None)
    delta: float | None = Field(
        default=None,
        description="postChangeScore - baselineScore, or None if either is unavailable.",
    )


class FindingComparisonDTO(BaseModel):
    """Detailed transition comparison for a specific audit rule."""

    model_config = ConfigDict(frozen=True)

    ruleId: str = Field(..., description="Unique rule identifier.")
    category: RuleCategory = Field(..., description="Audit taxonomic category.")
    title: str = Field(..., description="Rule title.")
    previousState: RuleState = Field(..., description="State in baseline audit.")
    currentState: RuleState = Field(..., description="State in post-change audit.")
    transition: VerificationTransition = Field(
        ...,
        description="RESOLVED | UNRESOLVED | REGRESSED | PERSISTENT_PASS | UNKNOWN | NOT_RECHECKED",
    )
    wasAttempted: bool = Field(
        default=False,
        description="True if remediation was attempted for this rule.",
    )
    previousEvidence: dict[str, Any] = Field(
        default_factory=dict, description="Evidence from baseline audit."
    )
    currentEvidence: dict[str, Any] = Field(
        default_factory=dict, description="Evidence from post-change audit."
    )


class VerificationReportDTO(BaseModel):
    """Comprehensive post-deployment verification report comparing baseline and post-change audits."""

    verificationId: str = Field(
        ..., description="Unique verification report identifier."
    )
    targetUrl: str = Field(..., description="Audited target URL.")
    baselineScanToken: str = Field(..., description="Scan token of baseline audit.")
    postChangeScanToken: str = Field(
        ..., description="Scan token of post-change audit."
    )
    verifiedAt: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Verification execution timestamp.",
    )
    totalAttempted: int = Field(
        default=0, ge=0, description="Count of attempted fix issues."
    )
    resolvedCount: int = Field(
        default=0, ge=0, description="Count of verified resolved issues."
    )
    unresolvedCount: int = Field(
        default=0, ge=0, description="Count of persistent unresolved issues."
    )
    regressedCount: int = Field(
        default=0, ge=0, description="Count of newly failing (regressed) issues."
    )
    unknownCount: int = Field(
        default=0, ge=0, description="Count of checks that returned UNKNOWN."
    )
    notRecheckedCount: int = Field(
        default=0, ge=0, description="Count of checks not re-tested."
    )
    issueResolutionRate: float | None = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="Model E33 Issue Resolution Rate percentage (0-100), or None if 0 attempted.",
    )
    overallScoreDelta: ScoreDeltaDTO = Field(
        ..., description="Delta of overall SEO Health Score."
    )
    completenessDelta: ScoreDeltaDTO = Field(
        ..., description="Delta of report completeness index."
    )
    categoryDeltas: dict[RuleCategory, ScoreDeltaDTO] = Field(
        default_factory=dict,
        description="Per-category score deltas.",
    )
    findingComparisons: list[FindingComparisonDTO] = Field(
        default_factory=list,
        description="Itemized comparison of all audited rules.",
    )
    rulesetVersion: str = Field(default="1.0.0", description="Ruleset version applied.")
    scoringModelVersion: str = Field(
        default="1.0.0", description="Scoring model version applied."
    )
