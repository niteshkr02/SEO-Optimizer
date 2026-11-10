"""Unit tests for MultiPageCrawler engine, frontier scheduling, and boundary controls."""

from unittest.mock import patch

import pytest

from app.contracts.crawl import (
    CrawlJobDTO,
    CrawlJobStatus,
    CrawlPageStatus,
)
from app.contracts.enums import IssueSeverity, RuleState
from app.crawler.client import CrawlResult, SafeHttpClient
from app.crawler.multi_page_crawler import MultiPageCrawler
from app.crawler.redirects import RedirectEvaluation
from app.crawler.robots import RobotsTxtResult
from app.persistence.crawl_in_memory import InMemoryCrawlRepository


def make_html(title: str, links: list[str] | None = None, canonical: str | None = None) -> str:
    """Helper creating basic HTML with specific title, links, and canonical."""
    links_html = "".join(f'<a href="{l}">Link to {l}</a>' for l in (links or []))
    canonical_html = f'<link rel="canonical" href="{canonical}">' if canonical else ""
    return f"""<!DOCTYPE html>
<html>
<head>
    <title>{title}</title>
    <meta name="description" content="Meta description for {title}">
    {canonical_html}
</head>
<body>
    <h1>{title}</h1>
    {links_html}
</body>
</html>"""


@pytest.fixture
def mock_repo():
    return InMemoryCrawlRepository()


@pytest.fixture
def base_job():
    return CrawlJobDTO(
        jobId="job-test-1",
        seedUrl="https://example.com/",
        baseDomain="example.com",
        status=CrawlJobStatus.QUEUED,
        maxPages=10,
        maxDepth=2,
    )


@pytest.mark.asyncio
async def test_multi_page_crawler_discovers_and_crawls_internal_links(mock_repo, base_job):
    """Verifies that the crawler discovers internal HTML links and evaluates findings across pages."""
    mock_repo.create_job(base_job)

    # Simulated site tree:
    # / -> links to /about and /services
    # /about -> links to /team
    # /services -> no links
    site_pages = {
        "https://example.com/": make_html("Home Page", ["/about", "/services"]),
        "https://example.com/about": make_html("About Us", ["/team"]),
        "https://example.com/services": make_html("Our Services", []),
        "https://example.com/team": make_html("Our Team", []),
    }

    mock_client = SafeHttpClient()

    async def mock_fetch(url: str) -> CrawlResult:
        html = site_pages.get(url, make_html("Default Page"))
        return CrawlResult(
            requested_url=url,
            final_url=url,
            status_code=200,
            headers={"content-type": "text/html; charset=utf-8"},
            body=html,
            body_byte_size=len(html.encode("utf-8")),
            response_time_ms=50,
            redirect_evaluation=RedirectEvaluation(
                total_hops=0,
                has_loop=False,
                initial_url=url,
                final_url=url,
                hops=[],
                rule_state=RuleState.PASS,
                severity=IssueSeverity.INFO,
                deduction_points=0,
                guidance="",
            ),
            content_type="text/html",
        )

    with patch.object(mock_client, "fetch", side_effect=mock_fetch), patch(
        "app.crawler.multi_page_crawler.fetch_and_evaluate_robots_txt",
        return_value=RobotsTxtResult(is_present=False, status_code=404),
    ), patch(
        "app.crawler.multi_page_crawler.discover_and_evaluate_sitemaps",
        return_value=None,
    ):
        crawler = MultiPageCrawler(
            job=base_job,
            repo=mock_repo,
            client=mock_client,
            max_concurrency=2,
            request_delay_seconds=0.01,
        )

        completed_job = await crawler.execute_crawl()

        assert completed_job.status == CrawlJobStatus.COMPLETED
        assert completed_job.pages_crawled == 4
        assert completed_job.pages_failed == 0
        assert completed_job.current_depth == 2

        # Check pages in repo
        pages, total = mock_repo.list_pages(base_job.job_id)
        assert total == 4
        urls = {p.url for p in pages}
        assert "https://example.com/" in urls
        assert "https://example.com/about" in urls
        assert "https://example.com/services" in urls
        assert "https://example.com/team" in urls

        # Check depth tracking
        home_page = next(p for p in pages if p.url == "https://example.com/")
        about_page = next(p for p in pages if p.url == "https://example.com/about")
        team_page = next(p for p in pages if p.url == "https://example.com/team")
        assert home_page.depth == 0
        assert about_page.depth == 1
        assert team_page.depth == 2

        # Verify site aggregate report was generated
        report = mock_repo.get_site_aggregate(base_job.job_id)
        assert report is not None
        assert report.total_pages_analyzed == 4
        assert report.overall_score is not None
        assert report.overall_score > 0.0


@pytest.mark.asyncio
async def test_multi_page_crawler_respects_robots_txt_disallow(mock_repo):
    """Verifies that paths disallowed in robots.txt are not crawled and marked DISALLOWED."""
    job = CrawlJobDTO(
        jobId="job-robots-1",
        seedUrl="https://example.com/",
        baseDomain="example.com",
        status=CrawlJobStatus.QUEUED,
        maxPages=10,
        maxDepth=2,
    )
    mock_repo.create_job(job)

    robots_content = """User-agent: *
Disallow: /admin/
Disallow: /private
"""
    site_pages = {
        "https://example.com/": make_html("Home", ["/public-page", "/admin/dashboard", "/private/secret"]),
        "https://example.com/public-page": make_html("Public Page"),
    }

    mock_client = SafeHttpClient()

    async def mock_fetch(url: str) -> CrawlResult:
        if "/admin/" in url or "/private" in url:
            pytest.fail(f"Crawler attempted to fetch disallowed URL: {url}")
        html = site_pages.get(url, make_html("Page"))
        return CrawlResult(
            requested_url=url,
            final_url=url,
            status_code=200,
            headers={"content-type": "text/html"},
            body=html,
            body_byte_size=len(html),
            response_time_ms=30,
            redirect_evaluation=RedirectEvaluation(
                total_hops=0,
                has_loop=False,
                initial_url=url,
                final_url=url,
                hops=[],
                rule_state=RuleState.PASS,
                severity=IssueSeverity.INFO,
                deduction_points=0,
                guidance="",
            ),
        )

    with patch.object(mock_client, "fetch", side_effect=mock_fetch), patch(
        "app.crawler.multi_page_crawler.fetch_and_evaluate_robots_txt",
        return_value=RobotsTxtResult(is_present=True, status_code=200, raw_content=robots_content),
    ), patch(
        "app.crawler.multi_page_crawler.discover_and_evaluate_sitemaps",
        return_value=None,
    ):
        crawler = MultiPageCrawler(job=job, repo=mock_repo, client=mock_client, request_delay_seconds=0.01)
        completed_job = await crawler.execute_crawl()

        assert completed_job.status == CrawlJobStatus.COMPLETED
        assert completed_job.pages_crawled == 2  # / and /public-page

        # Disallowed pages must be recorded with status DISALLOWED
        disallowed, count = mock_repo.list_pages(job.job_id, status=CrawlPageStatus.DISALLOWED.value)
        assert count == 2
        disallowed_urls = {p.url for p in disallowed}
        assert "https://example.com/admin/dashboard" in disallowed_urls
        assert "https://example.com/private/secret" in disallowed_urls


@pytest.mark.asyncio
async def test_multi_page_crawler_respects_max_pages_ceiling(mock_repo):
    """Verifies that crawling stops when max_pages is reached, resulting in PARTIAL status."""
    job = CrawlJobDTO(
        jobId="job-max-pages",
        seedUrl="https://example.com/",
        baseDomain="example.com",
        status=CrawlJobStatus.QUEUED,
        maxPages=2,  # Hard ceiling of 2 pages
        maxDepth=3,
    )
    mock_repo.create_job(job)

    # Home page has 5 links
    site_pages = {
        "https://example.com/": make_html("Home", [f"/p{i}" for i in range(1, 6)]),
    }
    for i in range(1, 6):
        site_pages[f"https://example.com/p{i}"] = make_html(f"Page {i}")

    mock_client = SafeHttpClient()

    async def mock_fetch(url: str) -> CrawlResult:
        html = site_pages.get(url, make_html("Page"))
        return CrawlResult(
            requested_url=url,
            final_url=url,
            status_code=200,
            headers={"content-type": "text/html"},
            body=html,
            body_byte_size=len(html),
            response_time_ms=20,
            redirect_evaluation=RedirectEvaluation(
                total_hops=0,
                has_loop=False,
                initial_url=url,
                final_url=url,
                hops=[],
                rule_state=RuleState.PASS,
                severity=IssueSeverity.INFO,
                deduction_points=0,
                guidance="",
            ),
        )

    with patch.object(mock_client, "fetch", side_effect=mock_fetch), patch(
        "app.crawler.multi_page_crawler.fetch_and_evaluate_robots_txt",
        return_value=RobotsTxtResult(is_present=False, status_code=404),
    ), patch(
        "app.crawler.multi_page_crawler.discover_and_evaluate_sitemaps",
        return_value=None,
    ):
        crawler = MultiPageCrawler(job=job, repo=mock_repo, client=mock_client, request_delay_seconds=0.01)
        completed_job = await crawler.execute_crawl()

        # Reached ceiling of 2 with more pending -> PARTIAL
        assert completed_job.status == CrawlJobStatus.PARTIAL
        assert completed_job.pages_crawled == 2
        assert completed_job.pages_discovered > 2


@pytest.mark.asyncio
async def test_multi_page_crawler_respects_max_depth(mock_repo):
    """Verifies that discovered links deeper than max_depth are not queued."""
    job = CrawlJobDTO(
        jobId="job-max-depth",
        seedUrl="https://example.com/",
        baseDomain="example.com",
        status=CrawlJobStatus.QUEUED,
        maxPages=20,
        maxDepth=1,  # Max depth 1: home (0) -> /p1 (1) -> /p2 should NOT be queued
    )
    mock_repo.create_job(job)

    site_pages = {
        "https://example.com/": make_html("Home (Depth 0)", ["/p1"]),
        "https://example.com/p1": make_html("Page 1 (Depth 1)", ["/p2"]),
        "https://example.com/p2": make_html("Page 2 (Depth 2)", []),
    }

    mock_client = SafeHttpClient()

    async def mock_fetch(url: str) -> CrawlResult:
        html = site_pages.get(url, make_html("Page"))
        return CrawlResult(
            requested_url=url,
            final_url=url,
            status_code=200,
            headers={"content-type": "text/html"},
            body=html,
            body_byte_size=len(html),
            response_time_ms=20,
            redirect_evaluation=RedirectEvaluation(
                total_hops=0,
                has_loop=False,
                initial_url=url,
                final_url=url,
                hops=[],
                rule_state=RuleState.PASS,
                severity=IssueSeverity.INFO,
                deduction_points=0,
                guidance="",
            ),
        )

    with patch.object(mock_client, "fetch", side_effect=mock_fetch), patch(
        "app.crawler.multi_page_crawler.fetch_and_evaluate_robots_txt",
        return_value=RobotsTxtResult(is_present=False, status_code=404),
    ), patch(
        "app.crawler.multi_page_crawler.discover_and_evaluate_sitemaps",
        return_value=None,
    ):
        crawler = MultiPageCrawler(job=job, repo=mock_repo, client=mock_client, request_delay_seconds=0.01)
        completed_job = await crawler.execute_crawl()

        assert completed_job.status == CrawlJobStatus.COMPLETED
        assert completed_job.pages_crawled == 2
        assert completed_job.current_depth == 1

        pages, total = mock_repo.list_pages(job.job_id)
        assert total == 2
        urls = {p.url for p in pages}
        assert "https://example.com/p2" not in urls


@pytest.mark.asyncio
async def test_multi_page_crawler_excludes_external_domains(mock_repo, base_job):
    """Verifies that external links (e.g. to twitter, github) are never crawled."""
    mock_repo.create_job(base_job)

    site_pages = {
        "https://example.com/": make_html(
            "Home",
            ["/local-page", "https://twitter.com/seo", "https://other-site.org/info"],
        ),
        "https://example.com/local-page": make_html("Local Page"),
    }

    mock_client = SafeHttpClient()

    async def mock_fetch(url: str) -> CrawlResult:
        if "twitter.com" in url or "other-site.org" in url:
            pytest.fail(f"Crawler attempted to fetch external domain: {url}")
        html = site_pages.get(url, make_html("Page"))
        return CrawlResult(
            requested_url=url,
            final_url=url,
            status_code=200,
            headers={"content-type": "text/html"},
            body=html,
            body_byte_size=len(html),
            response_time_ms=20,
            redirect_evaluation=RedirectEvaluation(
                total_hops=0,
                has_loop=False,
                initial_url=url,
                final_url=url,
                hops=[],
                rule_state=RuleState.PASS,
                severity=IssueSeverity.INFO,
                deduction_points=0,
                guidance="",
            ),
        )

    with patch.object(mock_client, "fetch", side_effect=mock_fetch), patch(
        "app.crawler.multi_page_crawler.fetch_and_evaluate_robots_txt",
        return_value=RobotsTxtResult(is_present=False, status_code=404),
    ), patch(
        "app.crawler.multi_page_crawler.discover_and_evaluate_sitemaps",
        return_value=None,
    ):
        crawler = MultiPageCrawler(
            job=base_job,
            repo=mock_repo,
            client=mock_client,
            request_delay_seconds=0.01,
            boundary="SAME_ORIGIN",
        )
        completed_job = await crawler.execute_crawl()

        assert completed_job.status == CrawlJobStatus.COMPLETED
        assert completed_job.pages_crawled == 2
        pages, total = mock_repo.list_pages(base_job.job_id)
        assert total == 2
        urls = {p.url for p in pages}
        assert "https://example.com/local-page" in urls
