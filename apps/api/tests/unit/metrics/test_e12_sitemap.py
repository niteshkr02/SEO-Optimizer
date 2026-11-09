"""Unit tests for Mathematical Model E12: Sitemap URL Health (SH)."""

from app.metrics.sitemap import calculate_sitemap_health


def test_e12_all_passing_sitemap():
    res = calculate_sitemap_health(
        sampled_count=50,
        passing_count=50,
        syntax_valid=50,
        status_200=50,
        canonical_aligned=50,
        indexable=50,
    )
    assert res.sh_score == 100.0
    assert res.passing_all_dimensions_urls == 50


def test_e12_partial_passing_sitemap():
    # 40 passing out of 50 sampled -> SH = 80.0%
    res = calculate_sitemap_health(
        sampled_count=50,
        passing_count=40,
        syntax_valid=50,
        status_200=45,
        canonical_aligned=42,
        indexable=40,
    )
    assert res.sh_score == 80.0
    assert res.status_200_count == 45


def test_e12_zero_sampled_sitemap_returns_none():
    res = calculate_sitemap_health(
        sampled_count=0,
        passing_count=0,
    )
    assert res.sh_score is None

