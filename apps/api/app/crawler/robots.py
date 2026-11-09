"""Safe robots.txt fetching, parsing, and rule evaluation."""

import re
import urllib.parse

from pydantic import BaseModel, ConfigDict, Field

from app.core.errors import AppError
from app.crawler.client import SafeHttpClient


class RobotsTxtResult(BaseModel):
    """Immutable outcome of discovering and evaluating a site's robots.txt."""

    model_config = ConfigDict(frozen=True)

    is_present: bool = Field(
        default=False, description="True if /robots.txt responded with HTTP 200."
    )
    status_code: int = Field(
        default=404, description="HTTP status code from /robots.txt fetch."
    )
    sitemap_urls: list[str] = Field(
        default_factory=list, description="Sitemap URLs declared in robots.txt."
    )
    is_target_allowed: bool | None = Field(
        default=None,
        description="True if target URL path is permitted by User-agent rules, False if blocked, None if unknown.",
    )
    raw_content: str | None = Field(
        default=None, description="Raw text snippet of robots.txt."
    )
    error_reason: str | None = Field(
        default=None, description="Error reason if fetch failed."
    )


def parse_robots_txt(content: str, target_path: str) -> tuple[list[str], bool]:
    """Parses robots.txt content to extract sitemap URLs and evaluate path permissions.

    Returns:
        Tuple of (sitemap_urls_list, is_path_allowed).
    """
    sitemap_urls: list[str] = []
    lines = content.splitlines()

    # Normalize target path
    normalized_path = target_path if target_path.startswith("/") else f"/{target_path}"

    is_in_wildcard_agent = False
    disallows: list[str] = []
    allows: list[str] = []

    for raw_line in lines:
        # Strip comments
        line = raw_line.split("#")[0].strip()
        if not line:
            continue

        # Check Sitemap directive
        sitemap_match = re.match(r"^sitemap:\s*(.+)$", line, re.IGNORECASE)
        if sitemap_match:
            sitemap_url = sitemap_match.group(1).strip()
            if sitemap_url and sitemap_url not in sitemap_urls:
                sitemap_urls.append(sitemap_url)
            continue

        # Check User-agent
        ua_match = re.match(r"^user-agent:\s*(.+)$", line, re.IGNORECASE)
        if ua_match:
            agent = ua_match.group(1).strip().lower()
            is_in_wildcard_agent = agent in ("*", "seooptimizerbot")
            continue

        if is_in_wildcard_agent:
            # Check Disallow
            disallow_match = re.match(r"^disallow:\s*(.*)$", line, re.IGNORECASE)
            if disallow_match:
                path = disallow_match.group(1).strip()
                if path:
                    disallows.append(path)
                continue

            # Check Allow
            allow_match = re.match(r"^allow:\s*(.*)$", line, re.IGNORECASE)
            if allow_match:
                path = allow_match.group(1).strip()
                if path:
                    allows.append(path)
                continue

    # Evaluate target path against allows and disallows
    # Most specific (longest matching) rule takes precedence
    longest_allow = max(
        [len(p) for p in allows if normalized_path.startswith(p)], default=-1
    )
    longest_disallow = max(
        [len(p) for p in disallows if normalized_path.startswith(p)], default=-1
    )

    if longest_disallow > longest_allow:
        is_allowed = False
    else:
        is_allowed = True

    return sitemap_urls, is_allowed


async def fetch_and_evaluate_robots_txt(
    client: SafeHttpClient,
    target_url: str,
) -> RobotsTxtResult:
    """Discovers, fetches, and evaluates /robots.txt from the target URL's origin root."""
    parsed = urllib.parse.urlsplit(target_url)
    origin_root = f"{parsed.scheme}://{parsed.netloc}"
    robots_url = urllib.parse.urljoin(origin_root, "/robots.txt")
    target_path = parsed.path or "/"

    try:
        crawl = await client.fetch(robots_url)
    except AppError as exc:
        return RobotsTxtResult(
            is_present=False,
            status_code=0,
            sitemap_urls=[],
            is_target_allowed=None,
            raw_content=None,
            error_reason=f"Failed to fetch robots.txt: {exc.message}",
        )
    except Exception as exc:  # noqa: BLE001
        return RobotsTxtResult(
            is_present=False,
            status_code=0,
            sitemap_urls=[],
            is_target_allowed=None,
            raw_content=None,
            error_reason=f"Unexpected error fetching robots.txt: {exc}",
        )

    if crawl.status_code == 200:
        sitemaps, is_allowed = parse_robots_txt(crawl.body, target_path)
        return RobotsTxtResult(
            is_present=True,
            status_code=200,
            sitemap_urls=sitemaps,
            is_target_allowed=is_allowed,
            raw_content=crawl.body[:2000],  # Bound stored snippet
            error_reason=None,
        )

    # 404 or other HTTP status
    return RobotsTxtResult(
        is_present=False,
        status_code=crawl.status_code,
        sitemap_urls=[],
        is_target_allowed=True,  # Absence of robots.txt defaults to permitted
        raw_content=None,
        error_reason=f"HTTP {crawl.status_code} returned for /robots.txt",
    )
