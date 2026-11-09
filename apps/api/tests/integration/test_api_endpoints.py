"""Integration tests for FastAPI endpoints."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.contracts.enums import IssueSeverity, RuleState, ScanStatus
from app.crawler.client import CrawlResult
from app.crawler.redirects import RedirectEvaluation
from tests.fixtures.html_samples import VALID_PAGE_HTML


@pytest.mark.asyncio
async def test_health_check_endpoint(async_client: AsyncClient):
    """Verifies that the /api/v1/health endpoint responds with system telemetry."""
    response = await async_client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "SEO Optimizer API"
    assert data["ruleset_version"] == "1.0.0"
    assert data["scoring_model_version"] == "1.0.0"
    assert data["ssrf_protection_enforced"] is True


@pytest.mark.asyncio
async def test_scan_endpoint_blocks_ssrf_attacks(async_client: AsyncClient):
    """Verifies that submitting localhost or private CIDRs to /api/v1/scan is blocked immediately."""
    payload = {"url": "http://127.0.0.1:80/secret"}
    response = await async_client.post("/api/v1/scan", json=payload)
    assert response.status_code == 400
    data = response.json()
    assert "SSRF" in data["detail"]["code"] or "INVALID" in data["detail"]["code"]


@pytest.mark.asyncio
async def test_scan_endpoint_blocks_cloud_metadata(async_client: AsyncClient):
    """Verifies cloud metadata IP is rejected."""
    payload = {"url": "http://169.254.169.254/latest/meta-data/"}
    response = await async_client.post("/api/v1/scan", json=payload)
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_scan_endpoint_valid_crawl_produces_audit_report(
    async_client: AsyncClient,
):
    """Verifies end-to-end /api/v1/scan generates an AuditReportDTO with 20 findings and scores."""
    redirect_eval = RedirectEvaluation(
        total_hops=0,
        has_loop=False,
        initial_url="https://example.com/test",
        final_url="https://example.com/test",
        hops=[],
        rule_state=RuleState.PASS,
        severity=IssueSeverity.INFO,
        deduction_points=0,
        guidance="Direct URL",
    )
    mock_crawl = CrawlResult(
        requested_url="https://example.com/test",
        final_url="https://example.com/test",
        status_code=200,
        headers={"content-type": "text/html; charset=utf-8"},
        body=VALID_PAGE_HTML,
        body_byte_size=len(VALID_PAGE_HTML.encode("utf-8")),
        response_time_ms=95,
        redirect_evaluation=redirect_eval,
        content_type="text/html",
    )

    with patch(
        "app.api.v1.endpoints.scan.SafeHttpClient.fetch", new_callable=AsyncMock
    ) as mock_fetch:
        mock_fetch.return_value = mock_crawl

        response = await async_client.post(
            "/api/v1/scan", json={"url": "https://example.com/test"}
        )
        assert response.status_code == 200
        report = response.json()

        assert report["targetUrl"] == "https://example.com/test"
        assert report["statusCode"] == 200
        assert report["status"] == ScanStatus.COMPLETED
        assert report["overallScore"] is not None
        assert 0.0 <= report["overallScore"] <= 100.0
        assert report["completenessScore"] is not None
        assert len(report["findings"]) == 20
        assert "scanToken" in report
        assert len(report["categoryScores"]) == 5
        assert report["robotsSummary"] is not None
        assert report["sitemapSummary"] is not None
