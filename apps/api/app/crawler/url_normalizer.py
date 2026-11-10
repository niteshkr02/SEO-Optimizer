"""Deterministic URL normalization, deduplication, and crawl boundary validation.

Adheres to RFC 3986 and zero-trust egress requirements:
- Scheme & hostname lowercasing and default port stripping.
- Relative URL resolution against parent pages.
- Query parameter filtering (strips analytics/tracking params, sorts functional params).
- Fragment removal.
- Same-origin and same-domain crawl boundary validation.
"""

import re
import urllib.parse

from app.core.config import settings

# Non-semantic analytics/tracking query parameters that should be stripped for deduplication
STRIP_QUERY_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "gclid",
    "fbclid",
    "mc_eid",
    "mc_cid",
    "_hsenc",
    "_hsmi",
    "msclkid",
}


def normalize_url(raw_url: str, base_url: str | None = None) -> str:
    """Safely normalizes, cleans, and canonicalizes a URL string for crawling and deduplication.

    Args:
        raw_url: The URL string to normalize (relative or absolute).
        base_url: Optional parent page URL to resolve relative URLs against.

    Returns:
        Canonicalized absolute URL string.

    Raises:
        ValueError: If raw_url is empty, malformed, or cannot be resolved to an absolute HTTP/HTTPS URL.
    """
    if not raw_url or not isinstance(raw_url, str):
        raise ValueError("URL must be a non-empty string.")

    cleaned = raw_url.strip()
    if not cleaned:
        raise ValueError("URL cannot be whitespace only.")

    # Disallow non-HTTP schemes early
    lower_raw = cleaned.lower()
    if lower_raw.startswith(("javascript:", "mailto:", "tel:", "data:", "ftp:", "file:")):
        raise ValueError(f"Disallowed protocol in URL: {cleaned}")

    # Resolve relative URL if base_url is provided
    if base_url:
        try:
            resolved = urllib.parse.urljoin(base_url, cleaned)
        except Exception as exc:
            raise ValueError(f"Failed to resolve relative URL '{cleaned}' against base '{base_url}': {exc}") from exc
    else:
        resolved = cleaned

    try:
        parsed = urllib.parse.urlsplit(resolved)
    except Exception as exc:
        raise ValueError(f"Malformed URL string: {resolved}") from exc

    scheme = parsed.scheme.lower()
    if scheme not in settings.ALLOWED_SCHEMES:
        raise ValueError(f"Disallowed scheme '{scheme}'. Only {settings.ALLOWED_SCHEMES} are permitted.")

    hostname = parsed.hostname
    if not hostname:
        raise ValueError("URL must contain a valid hostname.")
    hostname = hostname.lower().rstrip(".")

    # Port normalization: strip default ports 80/443
    port = parsed.port
    if (scheme == "http" and port == 80) or (scheme == "https" and port == 443):
        netloc = hostname
    elif port is not None:
        netloc = f"{hostname}:{port}"
    else:
        netloc = hostname

    # Path normalization
    path = parsed.path or "/"
    # Collapse redundant consecutive slashes (e.g., //path///to -> /path/to)
    path = re.sub(r"/{2,}", "/", path)

    # Query parameter normalization:
    # 1. Strip tracking parameters
    # 2. Sort remaining parameters deterministically by key and value
    query = ""
    if parsed.query:
        query_pairs = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
        filtered_pairs = [
            (k, v) for k, v in query_pairs if k.lower() not in STRIP_QUERY_PARAMS
        ]
        if filtered_pairs:
            # Sort deterministically
            filtered_pairs.sort(key=lambda item: (item[0], item[1]))
            query = urllib.parse.urlencode(filtered_pairs)

    # Fragment is strictly discarded per RFC 3986 § 3.5 (fragments are client-side only)
    return urllib.parse.urlunsplit((scheme, netloc, path, query, ""))


def get_origin(url: str) -> str:
    """Returns the canonical origin (scheme://hostname[:port]) of a URL."""
    parsed = urllib.parse.urlsplit(url)
    scheme = parsed.scheme.lower()
    hostname = (parsed.hostname or "").lower()
    port = parsed.port

    if (scheme == "http" and port == 80) or (scheme == "https" and port == 443) or port is None:
        return f"{scheme}://{hostname}"
    return f"{scheme}://{hostname}:{port}"


def is_same_origin(url_a: str, url_b: str) -> bool:
    """Checks whether two URLs share the identical scheme, host, and port."""
    try:
        return get_origin(url_a) == get_origin(url_b)
    except (ValueError, TypeError, AttributeError):
        return False


def get_registrable_domain(hostname: str) -> str:
    """Extracts the base registrable domain from a hostname (e.g. 'sub.example.com' -> 'example.com').

    Implements safe public suffix heuristics for standard domains (.com, .org, .co.uk, etc.).
    """
    clean_host = hostname.lower().rstrip(".")
    parts = clean_host.split(".")
    if len(parts) <= 2:
        return clean_host

    # Common two-part TLD suffixes
    two_part_tlds = {"co.uk", "org.uk", "gov.uk", "com.au", "net.au", "co.nz", "co.jp", "com.br", "co.in"}
    if len(parts) >= 3 and f"{parts[-2]}.{parts[-1]}" in two_part_tlds:
        return ".".join(parts[-3:])

    return ".".join(parts[-2:])


def is_same_domain(url_a: str, url_b: str) -> bool:
    """Checks whether two URLs belong to the same root domain or its subdomains."""
    try:
        host_a = urllib.parse.urlsplit(url_a).hostname or ""
        host_b = urllib.parse.urlsplit(url_b).hostname or ""
        return get_registrable_domain(host_a) == get_registrable_domain(host_b)
    except (ValueError, TypeError, AttributeError):
        return False


def is_url_within_boundary(candidate_url: str, seed_url: str, boundary: str = "SAME_ORIGIN") -> bool:
    """Determines if a candidate URL is permitted within the configured crawl boundary."""
    if boundary == "SAME_DOMAIN":
        return is_same_domain(candidate_url, seed_url)
    # Default to strict same-origin
    return is_same_origin(candidate_url, seed_url)
