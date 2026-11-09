"""Mathematical Model E3: Overall SEO Health Score."""

from pydantic import BaseModel, ConfigDict, Field

from app.contracts.enums import RuleCategory
from app.core.config import settings

FORMULA_ID = "E3"
FORMULA_VERSION = "1.0.0"

# Canonical category mapping for overall score weighting
# Indexability (35%), Crawlability/Technical (30%), Performance (20%), On-Page (15%)
DEFAULT_CATEGORY_WEIGHTS: dict[RuleCategory, float] = {
    RuleCategory.INDEXABILITY: settings.WEIGHT_INDEXABILITY,
    RuleCategory.CRAWLABILITY: settings.WEIGHT_TECHNICAL,
    RuleCategory.DOCUMENT: settings.WEIGHT_ON_PAGE * 0.40,
    RuleCategory.CONTENT: settings.WEIGHT_ON_PAGE * 0.35,
    RuleCategory.STRUCTURED: settings.WEIGHT_ON_PAGE * 0.25,
}


class OverallScoreResult(BaseModel):
    """Result of computing Mathematical Model E3."""

    model_config = ConfigDict(frozen=True)

    formula_id: str = FORMULA_ID
    formula_version: str = FORMULA_VERSION
    overall_score: float | None = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="Overall SEO Health Score (0-100), or None if unavailable.",
    )
    available_categories_count: int = Field(default=0, ge=0)
    total_categories_count: int = Field(default=len(DEFAULT_CATEGORY_WEIGHTS), ge=0)
    category_availability: dict[RuleCategory, bool] = Field(default_factory=dict)
    normalized_weights_used: dict[RuleCategory, float] = Field(default_factory=dict)


def calculate_overall_health_score(
    category_scores: dict[RuleCategory, float | None],
    weights: dict[RuleCategory, float] | None = None,
) -> OverallScoreResult:
    """Calculates the Overall SEO Health Score according to Model E3.

    Formulation:
    When all categories available: S = sum(alpha_c * S_c)
    When subset available: S = sum(alpha_c * S_c) / sum(alpha_c) for available categories c.
    If no categories available: S = None (NULL).

    Invariants:
    - Never returns 0.0 when categories are missing or unmeasured.
    - Score is strictly clamped to [0.0, 100.0].
    """
    cat_weights = weights or DEFAULT_CATEGORY_WEIGHTS

    available_categories: dict[RuleCategory, float] = {}
    availability_map: dict[RuleCategory, bool] = {}

    for cat in DEFAULT_CATEGORY_WEIGHTS:
        score_val = category_scores.get(cat)
        if score_val is not None:
            available_categories[cat] = score_val
            availability_map[cat] = True
        else:
            availability_map[cat] = False

    if not available_categories:
        return OverallScoreResult(
            overall_score=None,
            available_categories_count=0,
            category_availability=availability_map,
            normalized_weights_used={},
        )

    # Sum of weights for available categories
    sum_weights = sum(cat_weights.get(cat, 0.1) for cat in available_categories)

    if sum_weights <= 0.0:
        return OverallScoreResult(
            overall_score=None,
            available_categories_count=len(available_categories),
            category_availability=availability_map,
            normalized_weights_used={},
        )

    weighted_score_sum = 0.0
    normalized_weights: dict[RuleCategory, float] = {}

    for cat, score in available_categories.items():
        w = cat_weights.get(cat, 0.1)
        normalized_w = w / sum_weights
        normalized_weights[cat] = round(normalized_w, 4)
        weighted_score_sum += score * normalized_w

    clamped_score = max(0.0, min(100.0, round(weighted_score_sum, 2)))

    return OverallScoreResult(
        overall_score=clamped_score,
        available_categories_count=len(available_categories),
        category_availability=availability_map,
        normalized_weights_used=normalized_weights,
    )
