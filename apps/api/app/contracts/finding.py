"""Immutable audit finding contract."""

from pydantic import BaseModel, ConfigDict, Field

from app.contracts.enums import IssueSeverity, RuleCategory, RuleState
from app.contracts.evidence import FindingEvidence


class Finding(BaseModel):
    """Immutable finding object representing a single evaluated audit rule."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    ruleId: str = Field(
        ..., description="Unique immutable rule key (e.g. 'canonical-presence')."
    )
    category: RuleCategory = Field(
        ..., description="Taxonomic category of the audit rule."
    )
    title: str = Field(..., description="Human-readable title of the rule.")
    description: str = Field(
        ..., description="Concise explanation of the standard evaluated."
    )
    state: RuleState = Field(
        ..., description="Deterministic 5-state evaluation outcome."
    )
    severity: IssueSeverity = Field(..., description="Impact severity rating.")
    weight: int = Field(
        default=5, ge=1, le=10, description="Rule weight in category scoring (w_i)."
    )
    evidence: FindingEvidence = Field(
        ..., description="Immutable verifiable proof object."
    )
    remediationGuidance: str = Field(
        ..., description="Deterministic actionable remediation instructions."
    )
