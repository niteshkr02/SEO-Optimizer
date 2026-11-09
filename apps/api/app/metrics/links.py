"""Mathematical Models E8 & E9: Internal Link Metrics."""

from pydantic import BaseModel, ConfigDict, Field

FORMULA_E8_ID = "E8"
FORMULA_E9_ID = "E9"
FORMULA_VERSION = "1.0.0"


class InternalLinkHealthResult(BaseModel):
    """Result of computing Mathematical Models E8 and E9."""

    model_config = ConfigDict(frozen=True)

    formula_e8_id: str = FORMULA_E8_ID
    formula_e9_id: str = FORMULA_E9_ID
    formula_version: str = FORMULA_VERSION
    total_internal_links_detected: int = Field(default=0, ge=0)
    verified_checked_links: int = Field(default=0, ge=0)
    verified_broken_links: int = Field(default=0, ge=0)
    inconclusive_links: int = Field(default=0, ge=0)
    blr_score: float | None = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="Broken Internal Link Ratio (BLR, 0-100), or None if 0 verified links.",
    )
    ilh_score: float | None = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="Internal Link Health (ILH = 100 - BLR, 0-100), or None if 0 verified links.",
    )


def calculate_internal_link_health(
    total_detected: int,
    verified_checked: int,
    verified_broken: int,
    inconclusive: int = 0,
) -> InternalLinkHealthResult:
    """Calculates BLR (Model E8) and ILH (Model E9).

    Formulations:
    BLR = 100 * (verified broken internal links) / (verified internal links checked)
    ILH = 100 - BLR

    Invariants:
    - Inconclusive/timed-out checks are excluded from both numerator and denominator.
    - If verified_checked == 0, both BLR and ILH return None (NULL).
    - BLR and ILH are clamped to [0.0, 100.0].
    """
    if verified_checked == 0:
        return InternalLinkHealthResult(
            total_internal_links_detected=total_detected,
            verified_checked_links=0,
            verified_broken_links=verified_broken,
            inconclusive_links=inconclusive,
            blr_score=None,
            ilh_score=None,
        )

    # Valid verified check
    raw_blr = (min(verified_broken, verified_checked) / verified_checked) * 100.0
    blr = max(0.0, min(100.0, round(raw_blr, 2)))
    ilh = max(0.0, min(100.0, round(100.0 - blr, 2)))

    return InternalLinkHealthResult(
        total_internal_links_detected=total_detected,
        verified_checked_links=verified_checked,
        verified_broken_links=verified_broken,
        inconclusive_links=inconclusive,
        blr_score=blr,
        ilh_score=ilh,
    )
