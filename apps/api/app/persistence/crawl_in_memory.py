"""In-memory crawl repository adapter for unit tests and local isolation."""

import threading
from datetime import UTC, datetime

from app.contracts.crawl import (
    CrawlJobDTO,
    CrawlJobStatus,
    CrawlPageDetailDTO,
    CrawlPageDTO,
    CrawlPageStatus,
    SiteAggregateReportDTO,
)
from app.contracts.finding import Finding
from app.contracts.scan import CategoryScoreDTO
from app.persistence.crawl_interface import CrawlRepositoryInterface


class InMemoryCrawlRepository(CrawlRepositoryInterface):
    """Thread-safe in-memory crawl repository for unit and property testing."""

    def __init__(self):
        self._lock = threading.RLock()
        self._jobs: dict[str, CrawlJobDTO] = {}
        # job_id -> list of pages
        self._pages: dict[str, list[CrawlPageDTO]] = {}
        # (job_id, page_id) -> list of findings
        self._page_findings: dict[tuple[str, str], list[Finding]] = {}
        # (job_id, page_id) -> category scores
        self._page_cat_scores: dict[tuple[str, str], dict[str, CategoryScoreDTO]] = {}
        # job_id -> SiteAggregateReportDTO
        self._aggregates: dict[str, SiteAggregateReportDTO] = {}

    def create_job(self, job: CrawlJobDTO) -> CrawlJobDTO:
        with self._lock:
            self._jobs[job.job_id] = job
            self._pages[job.job_id] = []
            return job

    def get_job(self, job_id: str) -> CrawlJobDTO | None:
        with self._lock:
            return self._jobs.get(job_id)

    def update_job_progress(
        self,
        job_id: str,
        status: CrawlJobStatus | None = None,
        pages_discovered: int | None = None,
        pages_crawled: int | None = None,
        pages_failed: int | None = None,
        pages_remaining: int | None = None,
        current_depth: int | None = None,
        progress_percentage: float | None = None,
        error_message: str | None = None,
    ) -> CrawlJobDTO | None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return None

            job_dict = job.model_dump()
            if status is not None:
                job_dict["status"] = status
                if status == CrawlJobStatus.RUNNING and job.started_at is None:
                    job_dict["started_at"] = datetime.now(UTC)
                elif (
                    status in (CrawlJobStatus.COMPLETED, CrawlJobStatus.PARTIAL, CrawlJobStatus.FAILED, CrawlJobStatus.CANCELLED)
                    and job_dict.get("completed_at") is None
                ):
                    completed_time = datetime.now(UTC)
                    job_dict["completed_at"] = completed_time
                    if job.started_at:
                        job_dict["duration_seconds"] = max(0.0, (completed_time - job.started_at).total_seconds())

            if pages_discovered is not None:
                job_dict["pages_discovered"] = pages_discovered
            if pages_crawled is not None:
                job_dict["pages_crawled"] = pages_crawled
            if pages_failed is not None:
                job_dict["pages_failed"] = pages_failed
            if pages_remaining is not None:
                job_dict["pages_remaining"] = pages_remaining
            if current_depth is not None:
                job_dict["current_depth"] = current_depth
            if progress_percentage is not None:
                job_dict["progress_percentage"] = progress_percentage
            if error_message is not None:
                job_dict["error_message"] = error_message

            updated_job = CrawlJobDTO(**job_dict)
            self._jobs[job_id] = updated_job
            return updated_job

    def add_page(self, page: CrawlPageDTO) -> bool:
        with self._lock:
            pages = self._pages.setdefault(page.job_id, [])
            # Deduplication by normalized_url
            for existing in pages:
                if existing.normalized_url == page.normalized_url:
                    return False
            pages.append(page)
            return True

    def get_page(self, job_id: str, page_id: str) -> CrawlPageDTO | None:
        with self._lock:
            pages = self._pages.get(job_id, [])
            for p in pages:
                if p.page_id == page_id:
                    return p
            return None

    def get_page_by_url(self, job_id: str, normalized_url: str) -> CrawlPageDTO | None:
        with self._lock:
            pages = self._pages.get(job_id, [])
            for p in pages:
                if p.normalized_url == normalized_url:
                    return p
            return None

    def get_next_pending_pages(self, job_id: str, limit: int = 10) -> list[CrawlPageDTO]:
        with self._lock:
            pages = self._pages.get(job_id, [])
            pending = [p for p in pages if p.status == CrawlPageStatus.PENDING]
            # Order by depth ascending (BFS order)
            pending.sort(key=lambda p: (p.depth, p.page_id))
            return pending[:limit]

    def update_page_result(
        self,
        page: CrawlPageDTO,
        findings: list[Finding],
        category_scores: dict[str, CategoryScoreDTO] | None = None,
    ) -> CrawlPageDTO:
        with self._lock:
            pages = self._pages.setdefault(page.job_id, [])
            for idx, existing in enumerate(pages):
                if existing.page_id == page.page_id:
                    pages[idx] = page
                    break
            else:
                pages.append(page)

            self._page_findings[(page.job_id, page.page_id)] = findings
            if category_scores:
                self._page_cat_scores[(page.job_id, page.page_id)] = category_scores
            return page

    def list_pages(
        self,
        job_id: str,
        depth: int | None = None,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[CrawlPageDTO], int]:
        with self._lock:
            pages = self._pages.get(job_id, [])
            filtered = pages
            if depth is not None:
                filtered = [p for p in filtered if p.depth == depth]
            if status is not None:
                filtered = [p for p in filtered if p.status == status]

            total = len(filtered)
            paginated = filtered[offset : offset + limit]
            return paginated, total

    def get_page_detail(self, job_id: str, page_id: str) -> CrawlPageDetailDTO | None:
        with self._lock:
            page = self.get_page(job_id, page_id)
            if not page:
                return None
            findings = self._page_findings.get((job_id, page_id), [])
            cat_scores = self._page_cat_scores.get((job_id, page_id), {})
            return CrawlPageDetailDTO(page=page, findings=findings, category_scores=cat_scores)

    def save_site_aggregate(self, report: SiteAggregateReportDTO) -> SiteAggregateReportDTO:
        with self._lock:
            self._aggregates[report.job_id] = report
            return report

    def get_site_aggregate(self, job_id: str) -> SiteAggregateReportDTO | None:
        with self._lock:
            return self._aggregates.get(job_id)

    def reset(self) -> None:
        with self._lock:
            self._jobs.clear()
            self._pages.clear()
            self._page_findings.clear()
            self._page_cat_scores.clear()
            self._aggregates.clear()
