"""Abstract repository interface for multi-page crawl jobs, pages, and aggregated reports."""

from abc import ABC, abstractmethod

from app.contracts.crawl import (
    CrawlJobDTO,
    CrawlJobStatus,
    CrawlPageDetailDTO,
    CrawlPageDTO,
    SiteAggregateReportDTO,
)
from app.contracts.finding import Finding
from app.contracts.scan import CategoryScoreDTO


class CrawlRepositoryInterface(ABC):
    """Interface defining durable storage operations for multi-page website crawls."""

    @abstractmethod
    def create_job(self, job: CrawlJobDTO) -> CrawlJobDTO:
        """Persists a newly created crawl job."""

    @abstractmethod
    def get_job(self, job_id: str) -> CrawlJobDTO | None:
        """Retrieves a crawl job by its ID."""

    @abstractmethod
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
        """Updates progress counters and lifecycle state for a crawl job."""

    @abstractmethod
    def add_page(self, page: CrawlPageDTO) -> bool:
        """Adds a discovered page to the job. Returns False if already exists."""

    @abstractmethod
    def get_page(self, job_id: str, page_id: str) -> CrawlPageDTO | None:
        """Retrieves a page by its ID."""

    @abstractmethod
    def get_page_by_url(self, job_id: str, normalized_url: str) -> CrawlPageDTO | None:
        """Retrieves a page record by its normalized URL within a job."""

    @abstractmethod
    def get_next_pending_pages(self, job_id: str, limit: int = 10) -> list[CrawlPageDTO]:
        """Fetches the next batch of pending pages ordered by depth (BFS)."""

    @abstractmethod
    def update_page_result(
        self,
        page: CrawlPageDTO,
        findings: list[Finding],
        category_scores: dict[str, CategoryScoreDTO] | None = None,
    ) -> CrawlPageDTO:
        """Updates a crawled page's outcome and stores its 20 SEO findings."""

    @abstractmethod
    def list_pages(
        self,
        job_id: str,
        depth: int | None = None,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[CrawlPageDTO], int]:
        """Returns paginated pages for a job matching optional filters."""

    @abstractmethod
    def get_page_detail(self, job_id: str, page_id: str) -> CrawlPageDetailDTO | None:
        """Retrieves complete page details including its 20 findings."""

    @abstractmethod
    def save_site_aggregate(self, report: SiteAggregateReportDTO) -> SiteAggregateReportDTO:
        """Stores the site-wide aggregated report for a crawl job."""

    @abstractmethod
    def get_site_aggregate(self, job_id: str) -> SiteAggregateReportDTO | None:
        """Retrieves the site-wide aggregated report for a crawl job."""

    @abstractmethod
    def reset(self) -> None:
        """Clears all stored crawl jobs (for testing hygiene only)."""
