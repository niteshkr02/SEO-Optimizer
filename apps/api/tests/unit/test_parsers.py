"""Unit tests for HTML DOM and structured data parsers."""

from app.parsers.html import parse_html_document
from tests.fixtures.html_samples import (
    DECORATIVE_IMAGES_HTML,
    MISSING_TAGS_HTML,
    MULTIPLE_H1_HTML,
    NOINDEX_PAGE_HTML,
    SPA_CONTAINER_HTML,
    VALID_PAGE_HTML,
)


def test_parse_valid_document():
    """Verifies parsing of a fully compliant HTML fixture."""
    doc = parse_html_document(
        html_content=VALID_PAGE_HTML,
        target_url="https://example.com/platform",
        headers={"x-robots-tag": "index, follow"},
    )

    assert doc.title_text == "Enterprise SEO Platform — Deterministic Audits & Remediation"
    assert doc.title_char_count > 0
    assert doc.canonical_url == "https://example.com/platform"
    assert "noindex" not in doc.robots_meta_directives
    assert "noindex" not in doc.x_robots_tag_directives
    assert len(doc.headings) == 3  # H1, H2, H3
    assert doc.headings[0].level == 1
    assert doc.headings[0].text == "Deterministic SEO Diagnosis Platform"
    assert len(doc.images) == 2
    assert doc.images[0].alt == "SEO dashboard screenshot"
    assert doc.images[1].is_decorative is True
    assert doc.jsonld_report.status == "SYNTAX_VALID"
    assert "SoftwareApplication" in doc.jsonld_report.detected_schema_types
    assert doc.is_spa_detected is False


def test_parse_noindex_document():
    """Verifies extraction of noindex directives from meta tag."""
    doc = parse_html_document(
        html_content=NOINDEX_PAGE_HTML,
        target_url="https://example.com/staging",
    )
    assert "noindex" in doc.robots_meta_directives
    assert "nofollow" in doc.robots_meta_directives


def test_parse_missing_tags_document():
    """Verifies graceful handling of document missing title, headings, and canonical."""
    doc = parse_html_document(
        html_content=MISSING_TAGS_HTML,
        target_url="https://example.com/empty",
    )
    assert doc.title_text is None
    assert doc.meta_description_text is None
    assert doc.canonical_url is None
    assert len(doc.headings) == 0
    assert len(doc.images) == 1
    assert doc.images[0].has_alt_attr is False
    assert doc.jsonld_report.status == "SYNTAX_INVALID"


def test_parse_multiple_h1_document():
    """Verifies heading tree extraction on multi-H1 page."""
    doc = parse_html_document(
        html_content=MULTIPLE_H1_HTML,
        target_url="https://example.com/multi-h1",
    )
    h1_count = len([h for h in doc.headings if h.level == 1])
    assert h1_count == 3


def test_parse_decorative_images():
    """Verifies decorative image identification."""
    doc = parse_html_document(
        html_content=DECORATIVE_IMAGES_HTML,
        target_url="https://example.com/images",
    )
    assert len(doc.images) == 4
    # img1 has alt="Informative visual graph" -> meaningful
    assert doc.images[0].is_decorative is False
    # img2 has alt="" role="presentation" -> decorative
    assert doc.images[1].is_decorative is True
    # img3 has aria-hidden="true" -> decorative
    assert doc.images[2].is_decorative is True
    # img4 has alt="   " -> whitespace only, not decorative but missing meaningful text
    assert doc.images[3].is_decorative is False


def test_parse_spa_detection():
    """Verifies static detection of SPA containers."""
    doc = parse_html_document(
        html_content=SPA_CONTAINER_HTML,
        target_url="https://example.com/spa",
    )
    assert doc.is_spa_detected is True

