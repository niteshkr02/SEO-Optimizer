"""Unit tests for Mathematical Model E14: JSON-LD Syntax Validity Ratio (JVR)."""

from app.parsers.jsonld import parse_jsonld


def test_e14_valid_jsonld():
    html = """
    <html><head>
    <script type="application/ld+json">
    {"@context": "https://schema.org", "@type": "WebSite", "name": "Test"}
    </script>
    </head></html>
    """
    res = parse_jsonld(html)
    assert res.detected_blocks_count == 1
    assert res.valid_blocks_count == 1
    assert res.jvr_score == 100.0
    assert res.status == "SYNTAX_VALID"
    assert "WebSite" in res.detected_schema_types


def test_e14_invalid_jsonld():
    html = """
    <html><head>
    <script type="application/ld+json">
    { invalid: json without quotes }
    </script>
    </head></html>
    """
    res = parse_jsonld(html)
    assert res.detected_blocks_count == 1
    assert res.valid_blocks_count == 0
    assert res.jvr_score == 0.0
    assert res.status == "SYNTAX_INVALID"


def test_e14_no_jsonld_detected_returns_none():
    html = "<html><head><title>No JSONLD</title></head></html>"
    res = parse_jsonld(html)
    assert res.detected_blocks_count == 0
    assert res.jvr_score is None
    assert res.status == "NONE_DETECTED"

