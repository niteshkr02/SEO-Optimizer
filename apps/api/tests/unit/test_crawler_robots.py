"""Unit tests for robots.txt parsing and path evaluation."""

from app.crawler.robots import parse_robots_txt


def test_parse_robots_txt_extracts_sitemaps():
    content = """
User-agent: *
Disallow: /admin/
Disallow: /private/
Allow: /private/public-page

Sitemap: https://example.com/sitemap.xml
Sitemap: https://example.com/sitemap2.xml
"""
    sitemaps, is_allowed = parse_robots_txt(content, "/about")
    assert sitemaps == [
        "https://example.com/sitemap.xml",
        "https://example.com/sitemap2.xml",
    ]
    assert is_allowed is True


def test_parse_robots_txt_disallows_path():
    content = """
User-agent: *
Disallow: /admin/
"""
    _, is_allowed = parse_robots_txt(content, "/admin/dashboard")
    assert is_allowed is False


def test_parse_robots_txt_allow_precedence():
    content = """
User-agent: *
Disallow: /section/
Allow: /section/open/
"""
    _, is_blocked = parse_robots_txt(content, "/section/closed")
    assert is_blocked is False

    _, is_allowed = parse_robots_txt(content, "/section/open/resource")
    assert is_allowed is True


def test_parse_robots_txt_empty_or_no_rules():
    content = """
# Empty file
"""
    sitemaps, is_allowed = parse_robots_txt(content, "/any-page")
    assert sitemaps == []
    assert is_allowed is True

