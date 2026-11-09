"""Unit tests for Mathematical Model E3: Overall SEO Health Score."""

from app.contracts.enums import RuleCategory
from app.scoring.overall import calculate_overall_health_score


def test_e3_all_categories_available_100():
    category_scores = {
        RuleCategory.INDEXABILITY: 100.0,
        RuleCategory.CRAWLABILITY: 100.0,
        RuleCategory.DOCUMENT: 100.0,
        RuleCategory.CONTENT: 100.0,
        RuleCategory.STRUCTURED: 100.0,
    }
    res = calculate_overall_health_score(category_scores)
    assert res.overall_score == 100.0
    assert res.available_categories_count == 5


def test_e3_all_categories_available_0():
    category_scores = {
        RuleCategory.INDEXABILITY: 0.0,
        RuleCategory.CRAWLABILITY: 0.0,
        RuleCategory.DOCUMENT: 0.0,
        RuleCategory.CONTENT: 0.0,
        RuleCategory.STRUCTURED: 0.0,
    }
    res = calculate_overall_health_score(category_scores)
    assert res.overall_score == 0.0


def test_e3_subset_categories_available_normalized_mean():
    # Only Indexability (w=0.35, score=80.0) and Crawlability (w=0.30, score=60.0) available
    # Normalized weights: w_I = 0.35/0.65, w_C = 0.30/0.65
    # Expected: (80 * 0.35 + 60 * 0.30) / 0.65 = (28 + 18) / 0.65 = 46 / 0.65 = 70.77
    category_scores = {
        RuleCategory.INDEXABILITY: 80.0,
        RuleCategory.CRAWLABILITY: 60.0,
        RuleCategory.DOCUMENT: None,
        RuleCategory.CONTENT: None,
        RuleCategory.STRUCTURED: None,
    }
    res = calculate_overall_health_score(category_scores)
    assert res.overall_score == 70.77
    assert res.available_categories_count == 2
    assert res.category_availability[RuleCategory.INDEXABILITY] is True
    assert res.category_availability[RuleCategory.DOCUMENT] is False


def test_e3_zero_categories_available_returns_none():
    category_scores = {
        RuleCategory.INDEXABILITY: None,
        RuleCategory.CRAWLABILITY: None,
        RuleCategory.DOCUMENT: None,
    }
    res = calculate_overall_health_score(category_scores)
    assert res.overall_score is None
    assert res.available_categories_count == 0

