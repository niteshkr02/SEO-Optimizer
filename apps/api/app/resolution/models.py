"""Domain models for deterministic resolution planning and code patch proposals."""

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.contracts.enums import IssueSeverity, RuleCategory


class ResolutionActionType(str, Enum):
    """Classification of resolution execution mode."""

    AUTOMATED_CODE_PATCH = "AUTOMATED_CODE_PATCH"
    HUMAN_DECISION_REQUIRED = "HUMAN_DECISION_REQUIRED"


class CodePatchProposal(BaseModel):
    """Deterministic, reviewable code modification proposal."""

    model_config = ConfigDict(frozen=True)

    patchId: str = Field(..., description="Unique patch identifier.")
    findingId: str = Field(..., description="Associated audit rule ID.")
    affectedFile: str = Field(
        default="UNKNOWN (Requires Repository Access)",
        description="Target source code file path. Marked UNKNOWN for public scans.",
    )
    diffContent: str = Field(
        ..., description="Git unified diff representation of proposed code change."
    )
    beforeSnippet: str | None = Field(
        default=None, description="Verbatim original code or HTML snippet."
    )
    afterSnippet: str | None = Field(
        default=None, description="Proposed corrected code or HTML snippet."
    )
    patchHash: str = Field(
        ..., description="SHA-256 cryptographic hash of the diffContent."
    )
    requiresApproval: bool = Field(
        default=True,
        description="Strict safety requirement: explicit human authorization required.",
    )
    approvalStatus: str = Field(
        default="PENDING_REVIEW",
        description="PENDING_REVIEW | APPROVED | REJECTED",
    )


class ResolutionTask(BaseModel):
    """Actionable engineering resolution task with evidence-backed instructions."""

    taskId: str = Field(..., description="Unique resolution task identifier.")
    ruleId: str = Field(..., description="Target rule ID from audit findings.")
    category: RuleCategory = Field(..., description="Audit taxonomic category.")
    severity: IssueSeverity = Field(..., description="Impact severity rating.")
    actionType: ResolutionActionType = Field(
        ..., description="AUTOMATED_CODE_PATCH or HUMAN_DECISION_REQUIRED."
    )
    priorityScore: float = Field(
        ..., ge=0.0, description="RICE-inspired priority score (Model E21)."
    )
    triageScore: float = Field(
        ..., ge=0.0, le=100.0, description="Root-cause triage composite (Model E20)."
    )
    title: str = Field(..., description="Concise task title.")
    description: str = Field(..., description="Comprehensive problem statement.")
    targetSelector: str | None = Field(
        default=None, description="DOM selector or insertion path in rendered HTML."
    )
    targetFilePath: str = Field(
        default="UNKNOWN (Requires Repository Access)",
        description="Source code location. Explicitly UNKNOWN for public scans.",
    )
    proposedChange: str = Field(
        ...,
        description="Exact summary of what should be inserted, removed, or changed.",
    )
    procedure: list[str] = Field(
        default_factory=list, description="Ordered step-by-step resolution procedure."
    )
    expectedOutcome: str = Field(
        ..., description="Deterministic test criteria confirming fix."
    )
    risks: list[str] = Field(
        default_factory=list, description="Potential technical side effects or caveats."
    )
    rollbackInstructions: str = Field(
        ..., description="Exact operational procedure to revert proposed change."
    )
    codePatch: CodePatchProposal | None = Field(
        default=None, description="Unified diff patch proposal if unambiguous."
    )
    evidenceSnapshot: dict[str, Any] = Field(
        default_factory=dict, description="Verbatim evidence from original finding."
    )


class ResolutionPlanDTO(BaseModel):
    """Complete evidence-backed resolution plan covering all failing audit findings."""

    scanToken: str = Field(..., description="Unique scan identifier from audit report.")
    targetUrl: str = Field(..., description="Audited target landing URL.")
    totalIssues: int = Field(default=0, ge=0)
    automatedCount: int = Field(default=0, ge=0)
    humanDecisionCount: int = Field(default=0, ge=0)
    tasks: list[ResolutionTask] = Field(
        default_factory=list,
        description="List of resolution tasks sorted by priority (Model E21).",
    )
    createdAt: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Plan generation timestamp.",
    )
