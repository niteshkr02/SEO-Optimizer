"""Unit tests verifying deterministic rule execution across the rules registry."""

from app.contracts.enums import RuleState
from app.crawler.client import CrawlResult
from app.crawler.redirects import RedirectEvaluation
from app.crawler.robots import RobotsTxtResult
from app.crawler.sitemap import SitemapDiscoveryResult
from app.parsers.html import parse_html_document
from app.rules.registry import default_registry
from tests.fixtures.html_samples import NOINDEX_PAGE_HTML


def test_default_registry_evaluates_all_20_rules(
    valid_crawl_result: CrawlResult, valid_parsed_document
):
    """Verifies all 20 default rules execute and produce structured findings."""
    findings = default_registry.evaluate_all(valid_crawl_result, valid_parsed_document)
    assert len(findings) == 20

    # Ensure every finding has evidence with observed and expected values
    for f in findings:
        assert f.evidence is not None
        assert f.evidence.provenance is not None
        assert f.remediationGuidance is not None
        assert f.state in {
            RuleState.PASS,
            RuleState.FAIL,
            RuleState.NOT_APPLICABLE,
            RuleState.UNKNOWN,
            RuleState.NOT_TESTED,
        }


def test_valid_page_evaluates_to_predominantly_pass(
    valid_crawl_result: CrawlResult, valid_parsed_document
):
    """Verifies that our compliant synthetic HTML passes core checks."""
    robots_res = RobotsTxtResult(
        is_present=True,
        status_code=200,
        sitemap_urls=["https://example.com/sitemap.xml"],
        is_target_allowed=True,
        raw_content="User-agent: *\nAllow: /",
    )
    sitemap_res = SitemapDiscoveryResult(
        is_sitemap_found=True,
        sitemap_url="https://example.com/sitemap.xml",
        discovered_sitemaps=["https://example.com/sitemap.xml"],
        sitemap_source="ROBOTS_TXT",
        total_urls_sampled=10,
        sampled_urls=["https://example.com/"],
    )

    findings = default_registry.evaluate_all(
        valid_crawl_result,
        valid_parsed_document,
        robots_result=robots_res,
        sitemap_result=sitemap_res,
    )
    findings_map = {f.ruleId: f.state for f in findings}

    assert findings_map["http-status-200"] == RuleState.PASS
    assert findings_map["title-presence"] == RuleState.PASS
    assert findings_map["meta-description-presence"] == RuleState.PASS
    assert findings_map["canonical-presence"] == RuleState.PASS
    assert findings_map["h1-presence"] == RuleState.PASS
    assert findings_map["h1-single"] == RuleState.PASS
    assert findings_map["robots-meta-indexable"] == RuleState.PASS
    assert findings_map["jsonld-valid-syntax"] == RuleState.PASS
    assert findings_map["robots-txt-present"] == RuleState.PASS
    assert findings_map["sitemap-referenced"] == RuleState.PASS


def test_noindex_page_triggers_critical_fail():
    """Verifies that a page with meta noindex triggers a critical FAIL finding."""
    redirect_eval = RedirectEvaluation(
        total_hops=0,
        has_loop=False,
        initial_url="https://example.com/staging",
        final_url="https://example.com/staging",
        hops=[],
        rule_state=RuleState.PASS,
        severity="INFO",  # type: ignore[arg-type]
        deduction_points=0,
        guidance="OK",
    )
    crawl_result = CrawlResult(
        requested_url="https://example.com/staging",
        final_url="https://example.com/staging",
        status_code=200,
        headers={},
        body=NOINDEX_PAGE_HTML,
        body_byte_size=len(NOINDEX_PAGE_HTML),
        response_time_ms=100,
        redirect_evaluation=redirect_eval,
        content_type="text/html",
    )
    doc = parse_html_document(NOINDEX_PAGE_HTML, "https://example.com/staging")

    findings = default_registry.evaluate_all(crawl_result, doc)
    findings_map = {f.ruleId: f for f in findings}

    noindex_finding = findings_map["robots-meta-indexable"]
    assert noindex_finding.state == RuleState.FAIL
    assert noindex_finding.severity == "CRITICAL"
    assert "noindex" in noindex_finding.evidence.observedValue
