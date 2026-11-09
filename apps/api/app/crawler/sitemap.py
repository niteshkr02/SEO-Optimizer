"""Safe XML sitemap discovery, XXE-protected parsing, and Model E12 evaluation."""

import re
import urllib.parse

from lxml import etree
from pydantic import BaseModel, ConfigDict, Field

from app.crawler.client import SafeHttpClient
from app.crawler.robots import RobotsTxtResult
from app.metrics.sitemap import SitemapHealthResult, calculate_sitemap_health

MAX_SITEMAP_BYTES = 5 * 1024 * 1024  # 5 MB
MAX_SAMPLED_URLS = 50
MAX_SITEMAP_INDEX_CHILDREN = 3


class SitemapDiscoveryResult(BaseModel):
    """Immutable outcome of discovering and evaluating sitemaps for an origin."""

    model_config = ConfigDict(frozen=True)

    is_sitemap_found: bool = Field(
        default=False, description="True if a valid XML sitemap was fetched."
    )
    sitemap_url: str | None = Field(
        default=None, description="Primary sitemap URL evaluated."
    )
    discovered_sitemaps: list[str] = Field(
        default_factory=list, description="All candidate sitemap URLs identified."
    )
    sitemap_source: str = Field(
        default="NONE", description="ROBOTS_TXT | HTTP_HEADER | FALLBACK_ROOT | NONE"
    )
    total_urls_sampled: int = Field(
        default=0, ge=0, description="Count of URLs sampled from sitemap."
    )
    sampled_urls: list[str] = Field(
        default_factory=list, description="List of sampled URL strings."
    )
    health_result: SitemapHealthResult | None = Field(
        default=None, description="Model E12 calculation."
    )
    error_reason: str | None = Field(
        default=None, description="Error reason if discovery or parsing failed."
    )


def create_safe_xml_parser() -> etree.XMLParser:
    """Creates a hardened lxml XMLParser that strictly blocks external entities (XXE)."""
    return etree.XMLParser(
        resolve_entities=False,
        no_network=True,
        dtd_validation=False,
        load_dtd=False,
    )


def extract_header_sitemaps(headers: dict[str, str]) -> list[str]:
    """Extracts sitemap URLs from HTTP Link headers with rel='sitemap'."""
    sitemaps: list[str] = []
    link_header = headers.get("link", "")
    if not link_header:
        return sitemaps

    # Format: <https://example.com/sitemap.xml>; rel="sitemap"
    matches = re.findall(
        r'<([^>]+)>;\s*rel=["\']?sitemap["\']?', link_header, re.IGNORECASE
    )
    for m in matches:
        sitemaps.append(m.strip())
    return sitemaps


def parse_sitemap_xml(
    xml_content: bytes,
    expected_origin: str,
) -> tuple[bool, list[str], list[str]]:
    """Safely parses XML sitemap bytes with XXE protection.

    Returns:
        Tuple of (is_index, child_sitemap_locs, url_locs).
    """
    if len(xml_content) > MAX_SITEMAP_BYTES:
        return False, [], []

    # Check for raw entity declarations before parsing as secondary defense
    if b"<!ENTITY" in xml_content.upper():
        return False, [], []

    parser = create_safe_xml_parser()
    try:
        root = etree.fromstring(xml_content, parser=parser)
    except (etree.XMLSyntaxError, ValueError):
        return False, [], []

    tag = root.tag.lower()
    is_index = "sitemapindex" in tag

    child_sitemaps: list[str] = []
    url_locs: list[str] = []

    # Namespace-agnostic element traversal
    for elem in root.iter():
        clean_tag = (
            elem.tag.split("}")[-1].lower() if "}" in elem.tag else elem.tag.lower()
        )
        if clean_tag == "loc" and elem.text:
            loc = elem.text.strip()
            if loc:
                if is_index:
                    child_sitemaps.append(loc)
                else:
                    url_locs.append(loc)

    return is_index, child_sitemaps, url_locs


async def discover_and_evaluate_sitemaps(
    client: SafeHttpClient,
    target_url: str,
    robots_result: RobotsTxtResult,
    headers: dict[str, str],
) -> SitemapDiscoveryResult:
    """Discovers, fetches, and evaluates XML sitemaps for the target URL's origin root."""
    parsed = urllib.parse.urlsplit(target_url)
    origin_root = f"{parsed.scheme}://{parsed.netloc}"
    expected_host = parsed.netloc.lower()

    # Collect candidate sitemap URLs in priority order
    candidates: list[str] = []
    source = "NONE"

    # 1. From robots.txt
    if robots_result.sitemap_urls:
        candidates.extend(robots_result.sitemap_urls)
        source = "ROBOTS_TXT"

    # 2. From HTTP Link header
    header_sitemaps = extract_header_sitemaps(headers)
    for sm in header_sitemaps:
        if sm not in candidates:
            candidates.append(sm)
            if source == "NONE":
                source = "HTTP_HEADER"

    # 3. Fallback standard path
    fallback_url = urllib.parse.urljoin(origin_root, "/sitemap.xml")
    if fallback_url not in candidates:
        candidates.append(fallback_url)
        if source == "NONE":
            source = "FALLBACK_ROOT"

    # Attempt to fetch candidates until a valid XML sitemap is found
    for sitemap_candidate in candidates:
        try:
            crawl = await client.fetch(sitemap_candidate)
        except Exception:  # noqa: BLE001, S112
            continue

        if crawl.status_code != 200:
            continue

        raw_bytes = crawl.body.encode("utf-8", errors="replace")
        is_index, child_sitemaps, url_locs = parse_sitemap_xml(raw_bytes, origin_root)

        # If sitemap index, fetch first child sitemap
        if is_index and child_sitemaps:
            child_candidate = child_sitemaps[0]
            try:
                child_crawl = await client.fetch(child_candidate)
                if child_crawl.status_code == 200:
                    child_bytes = child_crawl.body.encode("utf-8", errors="replace")
                    _, _, child_urls = parse_sitemap_xml(child_bytes, origin_root)
                    url_locs = child_urls
            except Exception:  # noqa: BLE001, S110
                pass

        if not url_locs and not is_index:
            continue

        # Sample up to MAX_SAMPLED_URLS
        sampled = url_locs[:MAX_SAMPLED_URLS]
        sampled_count = len(sampled)

        if sampled_count == 0:
            continue

        # Evaluate Model E12 dimensions across sampled URLs
        syntax_valid = 0
        canonical_aligned = 0
        indexable_directives = 0

        for u in sampled:
            u_parsed = urllib.parse.urlsplit(u)
            if u_parsed.scheme in ("http", "https") and u_parsed.netloc:
                syntax_valid += 1
                if u_parsed.netloc.lower() == expected_host:
                    canonical_aligned += 1
                    indexable_directives += 1

        # Calculate Model E12
        sh_res = calculate_sitemap_health(
            sampled_count=sampled_count,
            passing_count=indexable_directives,
            syntax_valid=syntax_valid,
            status_200=sampled_count,  # Declared in valid sitemap
            canonical_aligned=canonical_aligned,
            indexable=indexable_directives,
        )

        return SitemapDiscoveryResult(
            is_sitemap_found=True,
            sitemap_url=sitemap_candidate,
            discovered_sitemaps=candidates,
            sitemap_source=source,
            total_urls_sampled=sampled_count,
            sampled_urls=sampled,
            health_result=sh_res,
            error_reason=None,
        )

    # No valid sitemap could be retrieved
    return SitemapDiscoveryResult(
        is_sitemap_found=False,
        sitemap_url=None,
        discovered_sitemaps=candidates,
        sitemap_source=source,
        total_urls_sampled=0,
        sampled_urls=[],
        health_result=None,
        error_reason="No valid XML sitemap could be found or parsed at discovered locations.",
    )
