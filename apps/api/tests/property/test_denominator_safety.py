"""Property-based tests verifying denominator safety and zero division prevention."""

from hypothesis import given
from hypothesis import strategies as st

from app.metrics.assets import calculate_image_alt_coverage
from app.metrics.links import calculate_internal_link_health
from app.metrics.sitemap import calculate_sitemap_health


def test_zero_denominator_links():
    """BLR and ILH must return None when verified_checked == 0, never ZeroDivisionError."""
    res = calculate_internal_link_health(total_detected=0, verified_checked=0, verified_broken=0)
    assert res.blr_score is None
    assert res.ilh_score is None


def test_zero_denominator_assets():
    """IAC must return None when eligible images == 0, never ZeroDivisionError."""
    res = calculate_image_alt_coverage(total_images=5, decorative_count=5, with_non_empty_alt=0)
    assert res.iac_score is None


def test_zero_denominator_sitemap():
    """SH must return None when sampled_count == 0, never ZeroDivisionError."""
    res = calculate_sitemap_health(sampled_count=0, passing_count=0)
    assert res.sh_score is None


@given(
    st.integers(min_value=0, max_value=1000),
    st.integers(min_value=0, max_value=1000),
)
def test_image_alt_coverage_never_crashes(total, decorative):
    """Property: IAC calculation never raises ZeroDivisionError regardless of inputs."""
    res = calculate_image_alt_coverage(
        total_images=total,
        decorative_count=decorative,
        with_non_empty_alt=total,
    )
    if res.iac_score is not None:
        assert 0.0 <= res.iac_score <= 100.0


@given(
    st.integers(min_value=0, max_value=1000),
    st.integers(min_value=0, max_value=1000),
    st.integers(min_value=0, max_value=1000),
)
def test_link_health_never_crashes(detected, checked, broken):
    """Property: Link health calculation never raises ZeroDivisionError regardless of inputs."""
    res = calculate_internal_link_health(
        total_detected=detected,
        verified_checked=checked,
        verified_broken=broken,
    )
    if res.blr_score is not None:
        assert 0.0 <= res.blr_score <= 100.0
        assert 0.0 <= res.ilh_score <= 100.0

