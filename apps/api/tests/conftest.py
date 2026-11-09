"""Shared pytest fixtures and test configurations."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.contracts.enums import IssueSeverity, RuleState
from app.crawler.client import CrawlResult
from app.crawler.redirects import RedirectEvaluation
from app.main import app
from app.parsers.html import parse_html_document
from tests.fixtures.html_samples import VALID_PAGE_HTML


@pytest.fixture
def valid_crawl_result() -> CrawlResult:
    """Fixture providing a valid 200 OK crawl result for synthetic testing."""
    redirect_eval = RedirectEvaluation(
        total_hops=0,
        has_loop=False,
        initial_url="https://example.com/platform",
        final_url="https://example.com/platform",
        hops=[],
        rule_state=RuleState.PASS,
        severity=IssueSeverity.INFO,
        deduction_points=0,
        guidance="Direct URL.",
    )
    return CrawlResult(
        requested_url="https://example.com/platform",
        final_url="https://example.com/platform",
        status_code=200,
        headers={"content-type": "text/html; charset=utf-8"},
        body=VALID_PAGE_HTML,
        body_byte_size=len(VALID_PAGE_HTML.encode("utf-8")),
        response_time_ms=120,
        redirect_evaluation=redirect_eval,
        content_type="text/html; charset=utf-8",
    )


@pytest.fixture
def valid_parsed_document(valid_crawl_result: CrawlResult):
    """Fixture providing a parsed document model from valid_crawl_result."""
    return parse_html_document(
        html_content=valid_crawl_result.body,
        target_url=valid_crawl_result.final_url,
        headers=valid_crawl_result.headers,
    )


@pytest.fixture
async def async_client():
    """Async HTTP client for testing FastAPI endpoints without opening real network sockets."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client

