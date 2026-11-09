"""Mathematical Model E10: Image Alt Attribute Coverage (IAC)."""

from pydantic import BaseModel, ConfigDict, Field

FORMULA_ID = "E10"
FORMULA_VERSION = "1.0.0"


class ImageAltCoverageResult(BaseModel):
    """Result of computing Mathematical Model E10."""

    model_config = ConfigDict(frozen=True)

    formula_id: str = FORMULA_ID
    formula_version: str = FORMULA_VERSION
    total_images_found: int = Field(default=0, ge=0)
    decorative_images_count: int = Field(default=0, ge=0)
    eligible_meaningful_images: int = Field(default=0, ge=0)
    images_with_non_empty_alt: int = Field(default=0, ge=0)
    images_missing_alt: int = Field(default=0, ge=0)
    iac_score: float | None = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="Image Alt Coverage percentage (0-100), or None if 0 eligible images.",
    )


def calculate_image_alt_coverage(
    total_images: int,
    decorative_count: int,
    with_non_empty_alt: int,
) -> ImageAltCoverageResult:
    """Calculates Image Alt Attribute Coverage according to Model E10.

    Formulation:
    IAC = 100 * (eligible meaningful images with non-empty alt) / (eligible meaningful images analysed)

    Invariants:
    - Decorative images (alt="", role="presentation") are NOT counted as failures; they are excluded from the denominator.
    - If eligible_meaningful_images == 0, IAC is None (NULL).
    - Score is strictly clamped to [0.0, 100.0].
    """
    eligible_count = max(0, total_images - decorative_count)
    valid_with_alt = min(with_non_empty_alt, eligible_count)
    missing_alt = eligible_count - valid_with_alt

    if eligible_count == 0:
        return ImageAltCoverageResult(
            total_images_found=total_images,
            decorative_images_count=decorative_count,
            eligible_meaningful_images=0,
            images_with_non_empty_alt=0,
            images_missing_alt=0,
            iac_score=None,
        )

    raw_iac = (valid_with_alt / eligible_count) * 100.0
    iac = max(0.0, min(100.0, round(raw_iac, 2)))

    return ImageAltCoverageResult(
        total_images_found=total_images,
        decorative_images_count=decorative_count,
        eligible_meaningful_images=eligible_count,
        images_with_non_empty_alt=valid_with_alt,
        images_missing_alt=missing_alt,
        iac_score=iac,
    )
