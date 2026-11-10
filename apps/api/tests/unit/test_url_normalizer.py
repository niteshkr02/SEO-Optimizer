"""Unit tests for URL normalization, deduplication, and crawl boundary enforcement."""

import pytest

from app.crawler.url_normalizer import (
    get_registrable_domain,
    is_same_domain,
    is_same_origin,
    is_url_within_boundary,
    normalize_url,
)


def test_normalize_url_basic_https():
    raw = "HTTPS://Example.COM:443/Path/To/Page"
    expected = "https://example.com/Path/To/Page"
    assert normalize_url(raw) == expected


def test_normalize_url_default_http_port():
    raw = "http://example.com:80/"
    expected = "http://example.com/"
    assert normalize_url(raw) == expected


def test_normalize_url_non_default_port():
    raw = "http://example.com:8080/app"
    expected = "http://example.com:8080/app"
    assert normalize_url(raw) == expected


def test_normalize_url_strips_fragments():
    raw = "https://example.com/docs#installation-section"
    expected = "https://example.com/docs"
    assert normalize_url(raw) == expected


def test_normalize_url_resolves_relative_to_base():
    base = "https://example.com/blog/article-1"
    raw = "../about-us"
    expected = "https://example.com/about-us"
    assert normalize_url(raw, base_url=base) == expected


def test_normalize_url_collapses_redundant_slashes():
    raw = "https://example.com//deep///nested////path"
    expected = "https://example.com/deep/nested/path"
    assert normalize_url(raw) == expected


def test_normalize_url_filters_tracking_parameters():
    raw = "https://example.com/product?utm_source=google&utm_medium=cpc&id=123&fbclid=xyz"
    expected = "https://example.com/product?id=123"
    assert normalize_url(raw) == expected


def test_normalize_url_sorts_query_parameters():
    raw1 = "https://example.com/search?z=99&a=1&m=50"
    raw2 = "https://example.com/search?m=50&z=99&a=1"
    expected = "https://example.com/search?a=1&m=50&z=99"
    assert normalize_url(raw1) == expected
    assert normalize_url(raw2) == expected
    assert normalize_url(raw1) == normalize_url(raw2)


def test_normalize_url_disallows_invalid_schemes():
    with pytest.raises(ValueError, match="Disallowed protocol"):
        normalize_url("javascript:void(0)")

    with pytest.raises(ValueError, match="Disallowed protocol"):
        normalize_url("mailto:support@example.com")

    with pytest.raises(ValueError, match="Disallowed protocol"):
        normalize_url("ftp://ftp.example.com/file")


def test_normalize_url_empty_raises():
    with pytest.raises(ValueError, match="non-empty"):
        normalize_url("")

    with pytest.raises(ValueError, match="whitespace"):
        normalize_url("   ")


def test_origin_and_domain_comparison():
    url1 = "https://example.com/page1"
    url2 = "https://example.com/page2?test=1"
    url3 = "https://sub.example.com/page3"
    url4 = "http://example.com/page1"
    url5 = "https://other.com/page1"

    # Same origin
    assert is_same_origin(url1, url2) is True
    assert is_same_origin(url1, url3) is False  # Different subdomain
    assert is_same_origin(url1, url4) is False  # Different scheme

    # Same domain
    assert is_same_domain(url1, url2) is True
    assert is_same_domain(url1, url3) is True   # Subdomain matches
    assert is_same_domain(url1, url5) is False  # Different root domain


def test_registrable_domain_parsing():
    assert get_registrable_domain("example.com") == "example.com"
    assert get_registrable_domain("blog.example.com") == "example.com"
    assert get_registrable_domain("deep.sub.example.com") == "example.com"
    assert get_registrable_domain("service.co.uk") == "service.co.uk"
    assert get_registrable_domain("api.service.co.uk") == "service.co.uk"


def test_crawl_boundary_enforcement():
    seed = "https://example.com/home"

    # Strict same-origin
    assert is_url_within_boundary("https://example.com/about", seed, "SAME_ORIGIN") is True
    assert is_url_within_boundary("https://sub.example.com/about", seed, "SAME_ORIGIN") is False
    assert is_url_within_boundary("http://example.com/about", seed, "SAME_ORIGIN") is False
    assert is_url_within_boundary("https://external.org/", seed, "SAME_ORIGIN") is False

    # Same-domain (subdomain permissive)
    assert is_url_within_boundary("https://sub.example.com/about", seed, "SAME_DOMAIN") is True
    assert is_url_within_boundary("https://blog.example.com/post", seed, "SAME_DOMAIN") is True
    assert is_url_within_boundary("https://different.com/about", seed, "SAME_DOMAIN") is False
