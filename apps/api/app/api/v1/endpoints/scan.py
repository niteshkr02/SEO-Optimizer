"""Public URL scan endpoint executing deterministic technical audit."""

import uuid

from fastapi import APIRouter, HTTPException, status

from app.contracts.enums import RuleCategory, ScanStatus
from app.contracts.scan import (
    AuditReportDTO,
    CategoryScoreDTO,
    RobotsTxtSummaryDTO,
    ScanRequest,
    SitemapSummaryDTO,
)
from app.core.config import settings
from app.core.errors import AppError, CrawlerTimeoutError, SSRFViolationError
from app.crawler.client import SafeHttpClient
from app.crawler.robots import fetch_and_evaluate_robots_txt
from app.crawler.sitemap import discover_and_evaluate_sitemaps
from app.parsers.html import parse_html_document
from app.rules.registry import default_registry
from app.scoring.category import calculate_category_score
from app.scoring.completeness import calculate_report_completeness
from app.scoring.overall import calculate_overall_health_score

router = APIRouter()


@router.post(
    "/scan",
    response_model=AuditReportDTO,
    status_code=status.HTTP_200_OK,
    summary="Execute public single-page deterministic SEO scan",
)
async def scan_url(request: ScanRequest) -> AuditReportDTO:
    """Executes a zero-trust single URL audit with deterministic evidence and scoring."""
    target_url = str(request.url)
    client = SafeHttpClient(verify_ssl=True)

    try:
        crawl_result = await client.fetch(target_url)
    except SSRFViolationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "SSRF_VIOLATION", "message": exc.message},
        ) from exc
    except CrawlerTimeoutError as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail={"code": "CRAWLER_TIMEOUT", "message": exc.message},
        ) from exc
    except AppError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": exc.code, "message": exc.message},
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "INTERNAL_CRAWL_ERROR", "message": str(exc)},
        ) from exc

    # Parse HTML and extract metadata
    parsed_doc = parse_html_document(
        html_content=crawl_result.body,
        target_url=crawl_result.final_url,
        headers=crawl_result.headers,
    )

    # Auxiliary crawl: robots.txt discovery and path evaluation
    robots_result = await fetch_and_evaluate_robots_txt(
        client=client,
        target_url=crawl_result.final_url,
    )

    # Auxiliary crawl: sitemap discovery and evaluation (Model E12)
    sitemap_result = await discover_and_evaluate_sitemaps(
        client=client,
        target_url=crawl_result.final_url,
        robots_result=robots_result,
        headers=crawl_result.headers,
    )

    # Deterministic rule evaluation (all 20 Phase 1 rules)
    findings = default_registry.evaluate_all(
        crawl_result=crawl_result,
        document=parsed_doc,
        robots_result=robots_result,
        sitemap_result=sitemap_result,
    )

    # Category Scoring (Model E2)
    category_scores: dict[RuleCategory, CategoryScoreDTO] = {}
    category_scores_map: dict[RuleCategory, float] = {}

    for cat in [
        RuleCategory.CRAWLABILITY,
        RuleCategory.INDEXABILITY,
        RuleCategory.DOCUMENT,
        RuleCategory.CONTENT,
        RuleCategory.STRUCTURED,
    ]:
        res = calculate_category_score(cat, findings)
        category_scores[cat] = CategoryScoreDTO(
            category=cat,
            score=res.score,
            completeness=None,
            applicableChecks=res.applicable_checks,
            evaluatedChecks=res.evaluated_checks,
        )
        if res.score is not None:
            category_scores_map[cat] = res.score

    # Overall Health Score (Model E3)
    overall_res = calculate_overall_health_score(category_scores_map)

    # Report Completeness (Model E5)
    completeness_res = calculate_report_completeness(findings)

    # Generate cryptographic scan token
    scan_token = uuid.uuid4().hex[:24]

    # Structure auxiliary summaries
    robots_summary = RobotsTxtSummaryDTO(
        isPresent=robots_result.is_present,
        statusCode=robots_result.status_code,
        sitemapUrls=robots_result.sitemap_urls,
        isTargetAllowed=robots_result.is_target_allowed,
        errorReason=robots_result.error_reason,
    )

    sitemap_summary = SitemapSummaryDTO(
        isSitemapFound=sitemap_result.is_sitemap_found,
        sitemapUrl=sitemap_result.sitemap_url,
        sitemapSource=sitemap_result.sitemap_source,
        totalUrlsSampled=sitemap_result.total_urls_sampled,
        healthScore=(
            sitemap_result.health_result.sh_score
            if sitemap_result.health_result
            else None
        ),
        errorReason=sitemap_result.error_reason,
    )

    report = AuditReportDTO(
        scanToken=scan_token,
        targetUrl=target_url,
        finalUrl=crawl_result.final_url,
        statusCode=crawl_result.status_code,
        status=ScanStatus.COMPLETED,
        overallScore=overall_res.overall_score,
        categoryScores=category_scores,
        completenessScore=completeness_res.completeness_score,
        categoryAvailability=overall_res.category_availability,
        findings=findings,
        robotsSummary=robots_summary,
        sitemapSummary=sitemap_summary,
        isSpaDetected=parsed_doc.is_spa_detected,
        rulesetVersion=settings.RULESET_VERSION,
        scoringModelVersion=settings.SCORING_MODEL_VERSION,
    )
    from app.persistence.repository import lead_repository

    lead_repository.save_scan(report)
    return report


@router.get(
    "/scan/{token}",
    response_model=AuditReportDTO,
    summary="Retrieve a previously executed scan report by token",
)
async def get_scan_by_token(token: str) -> AuditReportDTO:
    """Returns stored audit report for the given scan token."""
    from app.persistence.repository import lead_repository

    report = lead_repository.get_scan(token)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "SCAN_NOT_FOUND", "message": f"Scan report with token {token} was not found."},
        )
    return report

