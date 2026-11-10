"""Integration tests for multi-page crawl API endpoints."""

import asyncio
from unittest.mock import patch

import pytest
from httpx import AsyncClient

from app.contracts.crawl import (
    CrawlJobDTO,
    CrawlJobStatus,
    CrawlPageDTO,
    CrawlPageStatus,
)
from app.contracts.enums import IssueSeverity, RuleState
from app.crawler.client import CrawlResult
from app.crawler.redirects import RedirectEvaluation
from app.crawler.robots import RobotsTxtResult
from app.persistence.crawl_factory import crawl_repository


@pytest.fixture(autouse=True)
def clean_crawl_repo():
    crawl_repository.reset()
    yield
    crawl_repository.reset()


def _make_mock_html(title: str, links: list[str]) -> str:
    links_html = "".join(f'<a href="{url}">Link</a>' for url in links)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <title>{title}</title>
    <meta name="description" content="Meta description for {title} that is long enough to satisfy standard SEO criteria.">
    <link rel="canonical" href="https://example.com{links[0] if links else '/'}">
</head>
<body>
    <h1>{title}</h1>
    <p>Content for {title}.</p>
    {links_html}
</body>
</html>"""


@pytest.mark.asyncio
async def test_crawl_endpoint_blocks_ssrf(async_client: AsyncClient):
    """Verifies that POST /api/v1/crawl rejects loopback and cloud metadata seeds."""
    # Loopback
    resp = await async_client.post("/api/v1/crawl", json={"url": "http://127.0.0.1/admin"})
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "SSRF_VIOLATION"

    # Cloud metadata
    resp = await async_client.post(
        "/api/v1/crawl", json={"url": "http://169.254.169.254/latest/meta-data"}
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_crawl_endpoint_accepts_valid_url(async_client: AsyncClient):
    """Verifies that POST /api/v1/crawl queues a job and returns 202 Accepted."""
    # Prevent background task from actually running in this test
    with patch("app.crawler.job_manager.MultiPageCrawler.execute_crawl", return_value=None):
        resp = await async_client.post(
            "/api/v1/crawl",
            json={
                "url": "https://example.com/",
                "maxPages": 5,
                "maxDepth": 2,
            },
        )
        assert resp.status_code == 202
        data = resp.json()
        assert "jobId" in data
        assert data["seedUrl"] == "https://example.com/"
        assert data["baseDomain"] == "example.com"
        assert data["maxPages"] == 5
        assert data["maxDepth"] == 2
        assert data["status"] in ["QUEUED", "RUNNING"]


@pytest.mark.asyncio
async def test_crawl_status_and_not_found(async_client: AsyncClient):
    """Verifies GET /api/v1/crawl/{job_id} retrieves progress or 404."""
    # Non-existent
    resp = await async_client.get("/api/v1/crawl/non-existent-job-id")
    assert resp.status_code == 404
    assert resp.json()["detail"]["code"] == "JOB_NOT_FOUND"

    # Seed job directly in repo
    job = CrawlJobDTO(
        jobId="test-job-status-1",
        seedUrl="https://example.com/",
        baseDomain="example.com",
        status=CrawlJobStatus.RUNNING,
        progressPercentage=45.0,
        pagesDiscovered=10,
        pagesCrawled=4,
        pagesRemaining=6,
    )
    crawl_repository.create_job(job)

    resp = await async_client.get("/api/v1/crawl/test-job-status-1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["jobId"] == "test-job-status-1"
    assert data["status"] == "RUNNING"
    assert data["progressPercentage"] == 45.0
    assert data["pagesCrawled"] == 4


@pytest.mark.asyncio
async def test_crawl_pages_list_and_detail(async_client: AsyncClient):
    """Verifies listing discovered pages and inspecting page details."""
    job_id = "test-job-pages-1"
    job = CrawlJobDTO(
        jobId=job_id,
        seedUrl="https://example.com/",
        baseDomain="example.com",
        status=CrawlJobStatus.RUNNING,
    )
    crawl_repository.create_job(job)

    p1 = CrawlPageDTO(
        pageId="p1",
        jobId=job_id,
        url="https://example.com/",
        normalizedUrl="https://example.com/",
        depth=0,
        status=CrawlPageStatus.CRAWLED,
        httpStatus=200,
        title="Home",
    )
    p2 = CrawlPageDTO(
        pageId="p2",
        jobId=job_id,
        url="https://example.com/about",
        normalizedUrl="https://example.com/about",
        depth=1,
        status=CrawlPageStatus.PENDING,
    )
    crawl_repository.add_page(p1)
    crawl_repository.add_page(p2)

    # List all
    resp = await async_client.get(f"/api/v1/crawl/{job_id}/pages")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert len(data["pages"]) == 2

    # Filter by depth
    resp = await async_client.get(f"/api/v1/crawl/{job_id}/pages?depth=1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["pages"][0]["pageId"] == "p2"

    # Page detail
    resp = await async_client.get(f"/api/v1/crawl/{job_id}/pages/p1")
    assert resp.status_code == 200
    detail = resp.json()
    assert detail["page"]["pageId"] == "p1"
    assert "findings" in detail


@pytest.mark.asyncio
async def test_crawl_cancel_endpoint(async_client: AsyncClient):
    """Verifies POST /api/v1/crawl/{job_id}/cancel endpoint."""
    job_id = "test-job-cancel-1"
    job = CrawlJobDTO(
        jobId=job_id,
        seedUrl="https://example.com/",
        baseDomain="example.com",
        status=CrawlJobStatus.RUNNING,
    )
    crawl_repository.create_job(job)

    resp = await async_client.post(f"/api/v1/crawl/{job_id}/cancel")
    assert resp.status_code == 200
    data = resp.json()
    assert data["jobId"] == job_id
    assert "cancelled" in data


@pytest.mark.asyncio
async def test_crawl_e2e_execution_and_report_endpoint(async_client: AsyncClient):
    """Runs a simulated multi-page crawl and verifies report endpoint returns aggregated metrics."""
    site_pages = {
        "https://test-site.org/": _make_mock_html("Root", ["/blog", "/contact"]),
        "https://test-site.org/blog": _make_mock_html("Blog", []),
        "https://test-site.org/contact": _make_mock_html("Contact", []),
    }

    async def mock_fetch(url: str) -> CrawlResult:
        html = site_pages.get(url, _make_mock_html("Default", []))
        return CrawlResult(
            requested_url=url,
            final_url=url,
            status_code=200,
            headers={"content-type": "text/html; charset=utf-8"},
            body=html,
            body_byte_size=len(html.encode("utf-8")),
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
            content_type="text/html",
        )

    with patch("app.crawler.multi_page_crawler.SafeHttpClient.fetch", side_effect=mock_fetch), patch(
        "app.crawler.multi_page_crawler.fetch_and_evaluate_robots_txt",
        return_value=RobotsTxtResult(is_present=False, status_code=404),
    ), patch(
        "app.crawler.multi_page_crawler.discover_and_evaluate_sitemaps",
        return_value=None,
    ):
        # 1. Start crawl
        resp = await async_client.post(
            "/api/v1/crawl",
            json={
                "url": "https://test-site.org/",
                "maxPages": 3,
                "maxDepth": 1,
            },
        )
        assert resp.status_code == 202
        job_id = resp.json()["jobId"]

        # Wait for the background crawl task to complete
        for _ in range(50):
            await asyncio.sleep(0.05)
            status_resp = await async_client.get(f"/api/v1/crawl/{job_id}")
            if status_resp.status_code == 200:
                status_data = status_resp.json()
                if status_data["status"] in ["COMPLETED", "PARTIAL", "FAILED"]:
                    break

        # Verify completed
        assert status_data["status"] in ["COMPLETED", "PARTIAL"]
        assert status_data["pagesCrawled"] >= 2

        # 2. Get Site Aggregate Report
        report_resp = await async_client.get(f"/api/v1/crawl/{job_id}/report")
        assert report_resp.status_code == 200
        report = report_resp.json()
        assert report["jobId"] == job_id
        assert report["seedUrl"] == "https://test-site.org/"
        assert report["totalPagesAnalyzed"] >= 2
        assert "overallScore" in report
        assert "categoryScores" in report
        assert "uniqueIssues" in report
