"""Crawler, transport, and SSRF guard package."""

from app.crawler.cidr import is_ip_allowed, validate_ip_address
from app.crawler.client import CrawlResult, SafeHttpClient
from app.crawler.dns_resolver import resolve_and_validate_hostname
from app.crawler.redirects import (
    RedirectEvaluation,
    RedirectHop,
    evaluate_redirect_chain,
)
from app.crawler.robots import RobotsTxtResult, fetch_and_evaluate_robots_txt
from app.crawler.sitemap import (
    SitemapDiscoveryResult,
    discover_and_evaluate_sitemaps,
    parse_sitemap_xml,
)
from app.crawler.transport import (
    SSRFSafeAsyncHTTPTransport,
    SSRFSafeNetworkBackend,
    create_ssrf_safe_transport,
)
from app.crawler.url_sanitizer import sanitize_and_validate_url

__all__ = [
    "CrawlResult",
    "RedirectEvaluation",
    "RedirectHop",
    "RobotsTxtResult",
    "SSRFSafeAsyncHTTPTransport",
    "SSRFSafeNetworkBackend",
    "SafeHttpClient",
    "SitemapDiscoveryResult",
    "create_ssrf_safe_transport",
    "discover_and_evaluate_sitemaps",
    "evaluate_redirect_chain",
    "fetch_and_evaluate_robots_txt",
    "is_ip_allowed",
    "parse_sitemap_xml",
    "resolve_and_validate_hostname",
    "sanitize_and_validate_url",
    "validate_ip_address",
]
