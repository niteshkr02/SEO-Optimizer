"""Deterministic resolution planning and code patch proposals package."""

from app.resolution.generator import (
    ResolutionGenerator,
    compute_patch_hash,
    create_unified_diff,
)
from app.resolution.models import (
    CodePatchProposal,
    ResolutionActionType,
    ResolutionPlanDTO,
    ResolutionTask,
)
from app.resolution.priority import (
    ResolutionPriorityResult,
    calculate_resolution_priority,
)
from app.resolution.triage import (
    TriageCompositeResult,
    calculate_root_cause_triage,
)

__all__ = [
    "CodePatchProposal",
    "ResolutionActionType",
    "ResolutionGenerator",
    "ResolutionPlanDTO",
    "ResolutionPriorityResult",
    "ResolutionTask",
    "TriageCompositeResult",
    "calculate_resolution_priority",
    "calculate_root_cause_triage",
    "compute_patch_hash",
    "create_unified_diff",
]
