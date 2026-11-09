"""Mathematical Model E12: Sitemap URL Health (SH)."""

from pydantic import BaseModel, ConfigDict, Field

FORMULA_ID = "E12"
FORMULA_VERSION = "1.0.0"


class SitemapHealthResult(BaseModel):
    """Result of computing Mathematical Model E12."""

    model_config = ConfigDict(frozen=True)

    formula_id: str = FORMULA_ID
    formula_version: str = FORMULA_VERSION
    total_sampled_urls: int = Field(default=0, ge=0)
    passing_all_dimensions_urls: int = Field(default=0, ge=0)
    syntax_valid_count: int = Field(default=0, ge=0)
    status_200_count: int = Field(default=0, ge=0)
    canonical_aligned_count: int = Field(default=0, ge=0)
    indexable_directives_count: int = Field(default=0, ge=0)
    sh_score: float | None = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="Sitemap URL Health percentage (0-100), or None if 0 sampled URLs.",
    )


def calculate_sitemap_health(
    sampled_count: int,
    passing_count: int,
    syntax_valid: int = 0,
    status_200: int = 0,
    canonical_aligned: int = 0,
    indexable: int = 0,
) -> SitemapHealthResult:
    """Calculates Sitemap URL Health according to Model E12.

    Formulation:
    SH = 100 * (sampled sitemap URLs passing defined validation) / (sampled sitemap URLs evaluated)

    Invariants:
    - If sampled_count == 0 (e.g. sitemap not present or empty), SH is None (NULL).
    - Dimensions are disclosed separately.
    - Score is strictly clamped to [0.0, 100.0].
    """
    if sampled_count == 0:
        return SitemapHealthResult(
            total_sampled_urls=0,
            passing_all_dimensions_urls=0,
            syntax_valid_count=0,
            status_200_count=0,
            canonical_aligned_count=0,
            indexable_directives_count=0,
            sh_score=None,
        )

    valid_passing = min(passing_count, sampled_count)
    raw_sh = (valid_passing / sampled_count) * 100.0
    sh = max(0.0, min(100.0, round(raw_sh, 2)))

    return SitemapHealthResult(
        total_sampled_urls=sampled_count,
        passing_all_dimensions_urls=valid_passing,
        syntax_valid_count=syntax_valid,
        status_200_count=status_200,
        canonical_aligned_count=canonical_aligned,
        indexable_directives_count=indexable,
        sh_score=sh,
    )
