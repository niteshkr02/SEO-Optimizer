"""Mathematical Model E20: Root-Cause Triage Composite (RC)."""

from pydantic import BaseModel, ConfigDict, Field

FORMULA_ID = "E20"
FORMULA_VERSION = "1.0.0"


class TriageCompositeResult(BaseModel):
    """Result of computing Mathematical Model E20."""

    model_config = ConfigDict(frozen=True)

    formula_id: str = FORMULA_ID
    formula_version: str = FORMULA_VERSION
    evidence_strength: float = Field(default=0.0, ge=0.0, le=100.0)
    reproducibility: float = Field(default=0.0, ge=0.0, le=100.0)
    persistence: float = Field(default=0.0, ge=0.0, le=100.0)
    scope: float = Field(default=0.0, ge=0.0, le=100.0)
    rc_score: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="Root-Cause Triage Composite score on [0.0, 100.0].",
    )


def calculate_root_cause_triage(
    evidence_strength: float,
    reproducibility: float = 100.0,
    persistence: float = 100.0,
    scope: float = 50.0,
) -> TriageCompositeResult:
    """Calculates the Root-Cause Triage Composite (RC) according to Model E20.

    Formulation:
    RC = 0.40 * E + 0.25 * P + 0.20 * H + 0.15 * S

    Where all inputs are bounded in [0.0, 100.0]:
    - E: Direct evidence strength (e.g. 100 for raw HTTP headers, 80 for DOM selector, 40 for heuristic).
    - P: Reproducibility across multiple test fetches.
    - H: Historical consistency / persistence.
    - S: Affected page scope / blast radius (share of site pages affected).

    Critical Semantic Guard:
    RC is a triage prioritization composite, NOT a causal probability.
    Direct deterministic findings are already confirmed facts.

    Invariants:
    - Inputs outside [0.0, 100.0] are strictly clamped.
    - Output is strictly clamped to [0.0, 100.0].
    """
    e = max(0.0, min(100.0, float(evidence_strength)))
    p = max(0.0, min(100.0, float(reproducibility)))
    h = max(0.0, min(100.0, float(persistence)))
    s = max(0.0, min(100.0, float(scope)))

    raw_rc = (0.40 * e) + (0.25 * p) + (0.20 * h) + (0.15 * s)
    rc = max(0.0, min(100.0, round(raw_rc, 2)))

    return TriageCompositeResult(
        evidence_strength=e,
        reproducibility=p,
        persistence=h,
        scope=s,
        rc_score=rc,
    )

