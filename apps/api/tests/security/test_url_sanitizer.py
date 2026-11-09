"""Security tests for URL parser, protocol limits, and input sanitization."""

import pytest

from app.core.errors import InvalidURLError, SSRFViolationError
from app.crawler.url_sanitizer import sanitize_and_validate_url


def test_valid_http_and_https_urls():
    """Verifies standard valid HTTP and HTTPS URLs are accepted."""
    _, canon1 = sanitize_and_validate_url("https://example.com/page")
    assert canon1 == "https://example.com/page"

    _, canon2 = sanitize_and_validate_url("http://example.com:80/path?query=1")
    assert canon2 == "http://example.com/path?query=1"


@pytest.mark.parametrize(
    "malicious_url,expected_exc",
    [
        ("ftp://example.com/file.txt", InvalidURLError),
        ("file:///etc/passwd", InvalidURLError),
        ("gopher://127.0.0.1:70", InvalidURLError),
        ("javascript:alert(1)", InvalidURLError),
        ("data:text/html,<h1>Pwn</h1>", InvalidURLError),
        ("https://admin:secret@example.com/", SSRFViolationError),
        ("https://example.com:8080/scan", SSRFViolationError),
        ("http://example.com:22/ssh", SSRFViolationError),
        ("http://example.com:5432/db", SSRFViolationError),
        ("http://localhost/", SSRFViolationError),
        ("http://127.0.0.1/", SSRFViolationError),
        ("http://169.254.169.254/latest/meta-data/", SSRFViolationError),
        ("http://[::1]/", SSRFViolationError),
        ("   ", InvalidURLError),
        ("", InvalidURLError),
    ],
)
def test_disallowed_schemes_ports_and_destinations(malicious_url: str, expected_exc: type):
    """Verifies non-standard schemes, forbidden ports, credentials, and localhost are rejected."""
    with pytest.raises(expected_exc):
        sanitize_and_validate_url(malicious_url)


def test_url_fragment_is_stripped():
    """Verifies that URL fragments are stripped from canonical scan URLs."""
    _, canonical = sanitize_and_validate_url("https://example.com/page#section-2")
    assert "#" not in canonical
    assert canonical == "https://example.com/page"

