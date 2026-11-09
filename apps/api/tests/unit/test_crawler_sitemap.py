"""Unit tests for XML sitemap parsing, XXE defense, and limits."""

from app.crawler.sitemap import (
    MAX_SITEMAP_BYTES,
    extract_header_sitemaps,
    parse_sitemap_xml,
)


def test_parse_valid_sitemap_xml():
    xml = b"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://example.com/</loc>
    <lastmod>2026-01-01</lastmod>
  </url>
  <url>
    <loc>https://example.com/about</loc>
  </url>
</urlset>"""
    is_index, child_sitemaps, url_locs = parse_sitemap_xml(xml, "https://example.com")
    assert is_index is False
    assert len(child_sitemaps) == 0
    assert url_locs == ["https://example.com/", "https://example.com/about"]


def test_parse_sitemap_index_xml():
    xml = b"""<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <sitemap>
    <loc>https://example.com/sitemap-posts.xml</loc>
  </sitemap>
  <sitemap>
    <loc>https://example.com/sitemap-pages.xml</loc>
  </sitemap>
</sitemapindex>"""
    is_index, child_sitemaps, url_locs = parse_sitemap_xml(xml, "https://example.com")
    assert is_index is True
    assert child_sitemaps == [
        "https://example.com/sitemap-posts.xml",
        "https://example.com/sitemap-pages.xml",
    ]
    assert len(url_locs) == 0


def test_xxe_payload_is_rejected():
    xxe_xml = b"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE test [
  <!ENTITY xxe SYSTEM "file:///etc/passwd">
]>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>&xxe;</loc>
  </url>
</urlset>"""
    is_index, child_sitemaps, url_locs = parse_sitemap_xml(xxe_xml, "https://example.com")
    # Entity declaration triggers instant rejection
    assert is_index is False
    assert child_sitemaps == []
    assert url_locs == []


def test_oversized_sitemap_is_rejected():
    oversized = b"<urlset>" + (b"<url><loc>https://example.com/</loc></url>" * 150000)
    assert len(oversized) > MAX_SITEMAP_BYTES
    is_index, _child_sitemaps, url_locs = parse_sitemap_xml(oversized, "https://example.com")
    assert is_index is False
    assert url_locs == []


def test_extract_header_sitemaps():
    headers = {
        "link": '<https://example.com/sitemap.xml>; rel="sitemap", <https://example.com/style.css>; rel="stylesheet"',
    }
    extracted = extract_header_sitemaps(headers)
    assert extracted == ["https://example.com/sitemap.xml"]

