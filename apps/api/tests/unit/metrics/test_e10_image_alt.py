"""Unit tests for Mathematical Model E10: Image Alt Attribute Coverage (IAC)."""

from app.metrics.assets import calculate_image_alt_coverage


def test_e10_all_meaningful_images_with_alt_returns_100():
    res = calculate_image_alt_coverage(
        total_images=5,
        decorative_count=2,
        with_non_empty_alt=3,
    )
    # 5 total - 2 decorative = 3 eligible. 3 with alt -> 100.0%
    assert res.iac_score == 100.0
    assert res.eligible_meaningful_images == 3
    assert res.images_missing_alt == 0


def test_e10_missing_alt_calculates_percentage():
    # 10 total - 2 decorative = 8 eligible. 6 with alt -> 6/8 = 75.0%
    res = calculate_image_alt_coverage(
        total_images=10,
        decorative_count=2,
        with_non_empty_alt=6,
    )
    assert res.iac_score == 75.0
    assert res.images_missing_alt == 2


def test_e10_zero_eligible_images_returns_none():
    # 3 total, all 3 decorative -> 0 eligible -> None
    res = calculate_image_alt_coverage(
        total_images=3,
        decorative_count=3,
        with_non_empty_alt=0,
    )
    assert res.iac_score is None
    assert res.eligible_meaningful_images == 0

