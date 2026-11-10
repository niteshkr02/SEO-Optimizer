"""Versioned FastAPI endpoints for multi-page website crawling and site-wide reporting."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from app.contracts.crawl import (
    CrawlJobCreateRequest,
    CrawlJobDTO,
    CrawlPageDetailDTO,
    SiteAggregateReportDTO,
)
from app.core.errors import AppError, SSRFViolationError
from app.crawler.job_manager import job_manager
from app.crawler.url_sanitizer import sanitize_and_validate_url
from app.persistence.crawl_factory import crawl_repository

router = APIRouter()


@router.post(
    "/crawl",
    response_model=CrawlJobDTO,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Initiate asynchronous multi-page website crawl",
    description="Validates seed URL with SSRF checks, queues a multi-page crawl job, and returns its status tracker.",
)
async def start_crawl(request: CrawlJobCreateRequest) -> CrawlJobDTO:
    """Starts a multi-page crawl job in the background."""
    # Pre-validate seed URL with zero-trust SSRF protections
    try:
        sanitize_and_validate_url(request.url)
    except SSRFViolationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "SSRF_VIOLATION", "message": str(exc)},
        ) from exc
    except AppError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": exc.code, "message": exc.message},
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_URL", "message": f"Invalid seed URL: {exc}"},
        ) from exc

    return job_manager.start_crawl_job(request)


@router.get(
    "/crawl/{job_id}",
    response_model=CrawlJobDTO,
    summary="Get crawl job status and progress",
    description="Retrieves real-time progress percentage, discovered/crawled counters, and execution status.",
)
async def get_crawl_status(job_id: str) -> CrawlJobDTO:
    """Retrieves current crawl progress and counters."""
    job = crawl_repository.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "JOB_NOT_FOUND", "message": f"Crawl job '{job_id}' does not exist."},
        )
    return job


@router.get(
    "/crawl/{job_id}/pages",
    summary="List discovered and crawled pages",
    description="Returns a paginated list of pages for a crawl job with optional depth and status filtering.",
)
async def list_crawl_pages(
    job_id: str,
    depth: Annotated[int | None, Query(description="Filter by crawl depth (0 to 5)")] = None,
    status_filter: Annotated[str | None, Query(alias="status", description="Filter by status (PENDING, CRAWLED, etc.)")] = None,
    limit: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 50,
    offset: Annotated[int, Query(ge=0, description="Pagination offset")] = 0,
) -> dict:
    """Lists pages discovered or crawled within a crawl job."""
    job = crawl_repository.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "JOB_NOT_FOUND", "message": f"Crawl job '{job_id}' does not exist."},
        )

    pages, total = crawl_repository.list_pages(
        job_id=job_id,
        depth=depth,
        status=status_filter,
        limit=limit,
        offset=offset,
    )
    return {
        "jobId": job_id,
        "total": total,
        "limit": limit,
        "offset": offset,
        "pages": [p.model_dump(by_alias=True) for p in pages],
    }


@router.get(
    "/crawl/{job_id}/pages/{page_id}",
    response_model=CrawlPageDetailDTO,
    summary="Get individual page diagnostic results",
    description="Retrieves full page details including all 20 canonical SEO rule findings and category scores.",
)
async def get_page_details(job_id: str, page_id: str) -> CrawlPageDetailDTO:
    """Retrieves full SEO findings for a single crawled page."""
    detail = crawl_repository.get_page_detail(job_id, page_id)
    if not detail:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PAGE_NOT_FOUND", "message": f"Page '{page_id}' was not found in job '{job_id}'."},
        )
    return detail


@router.get(
    "/crawl/{job_id}/report",
    response_model=SiteAggregateReportDTO,
    summary="Get site-wide aggregated crawl report",
    description="Returns site-wide health scores, completeness, and deduplicated unique issues across all pages.",
)
async def get_site_report(job_id: str) -> SiteAggregateReportDTO:
    """Retrieves site-wide aggregated report for a crawl job."""
    report = crawl_repository.get_site_aggregate(job_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "REPORT_NOT_READY",
                "message": f"Aggregated report for crawl job '{job_id}' is not yet available or job has not completed.",
            },
        )
    return report


@router.post(
    "/crawl/{job_id}/cancel",
    summary="Cancel active crawl job",
    description="Requests graceful cancellation of a running crawl job.",
)
async def cancel_crawl(job_id: str) -> dict:
    """Cancels an active or queued crawl job."""
    job = crawl_repository.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "JOB_NOT_FOUND", "message": f"Crawl job '{job_id}' does not exist."},
        )

    cancelled = job_manager.cancel_crawl_job(job_id)
    return {
        "jobId": job_id,
        "cancelled": cancelled,
        "message": "Crawl cancellation requested.",
    }
