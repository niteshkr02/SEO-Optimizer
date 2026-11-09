"""Unit tests for Mathematical Models E8 (BLR) and E9 (ILH)."""

from app.metrics.links import calculate_internal_link_health


def test_e8_e9_zero_broken_links_is_100_health():
    res = calculate_internal_link_health(
        total_detected=10,
        verified_checked=10,
        verified_broken=0,
    )
    assert res.blr_score == 0.0
    assert res.ilh_score == 100.0


def test_e8_e9_broken_links_ratio():
    # 2 broken out of 10 checked -> BLR = 20.0%, ILH = 80.0%
    res = calculate_internal_link_health(
        total_detected=12,
        verified_checked=10,
        verified_broken=2,
        inconclusive=2,
    )
    assert res.blr_score == 20.0
    assert res.ilh_score == 80.0
    assert res.inconclusive_links == 2


def test_e8_e9_zero_checked_links_returns_none():
    res = calculate_internal_link_health(
        total_detected=0,
        verified_checked=0,
        verified_broken=0,
    )
    assert res.blr_score is None
    assert res.ilh_score is None

