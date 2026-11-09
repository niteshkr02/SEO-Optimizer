"""Strict URL parsing, validation, and sanitization."""

import urllib.parse

from app.core.config import settings
from app.core.errors import InvalidURLError, SSRFViolationError
from app.crawler.cidr import is_ip_allowed


def sanitize_and_validate_url(raw_url: str) -> tuple[urllib.parse.ParseResult, str]:
    """Validates and normalizes an input URL according to zero-trust egress rules.

    Returns:
        Tuple of (parsed_url, canonical_url_string).

    Raises:
        InvalidURLError: If the URL is syntactically invalid or uses disallowed protocols.
        SSRFViolationError: If the URL targets localhost, credentials, or illegal IP ranges.
    """
    if not raw_url or not isinstance(raw_url, str):
        raise InvalidURLError("Target URL must be a non-empty string.")

    cleaned_url = raw_url.strip()

    try:
        parsed = urllib.parse.urlsplit(cleaned_url)
    except Exception as exc:
        raise InvalidURLError(f"Malformed URL string: {cleaned_url}") from exc

    # Protocol validation
    scheme = parsed.scheme.lower()
    if scheme not in settings.ALLOWED_SCHEMES:
        raise InvalidURLError(
            f"Disallowed URL scheme '{scheme}'. Only {settings.ALLOWED_SCHEMES} are permitted."
        )

    # Hostname validation
    hostname = parsed.hostname
    if not hostname:
        raise InvalidURLError("URL must contain a valid hostname.")

    # Rejection of user credentials (user:pass@host)
    if parsed.username or parsed.password:
        raise SSRFViolationError("URLs containing user credentials are not permitted.")

    # Port validation
    port = parsed.port
    if port is None:
        port = 443 if scheme == "https" else 80

    if port not in settings.ALLOWED_EGRESS_PORTS:
        raise SSRFViolationError(
            f"Port {port} is not in permitted egress ports {settings.ALLOWED_EGRESS_PORTS}."
        )

    # Disallow known localhost aliases directly
    lower_host = hostname.lower()
    if lower_host in {
        "localhost",
        "localhost.localdomain",
        "ip6-localhost",
        "ip6-loopback",
    }:
        raise SSRFViolationError(
            f"Target host '{hostname}' is a forbidden localhost alias."
        )

    # If the host is already an IP address, validate it immediately
    try:
        import ipaddress

        ip_obj = ipaddress.ip_address(lower_host)
        if not is_ip_allowed(ip_obj):
            raise SSRFViolationError(
                f"Target host IP '{lower_host}' is in a forbidden CIDR range."
            )
    except ValueError:
        # Not an IP literal, it is a hostname
        pass

    # Canonicalize URL without fragment
    canonical_url = urllib.parse.urlunsplit(
        (
            scheme,
            f"{hostname}:{port}"
            if (scheme == "http" and port != 80) or (scheme == "https" and port != 443)
            else hostname,
            parsed.path or "/",
            parsed.query,
            "",  # Strip fragment
        )
    )

    return parsed, canonical_url
