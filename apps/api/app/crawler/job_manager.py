"""Asynchronous job orchestration and lifecycle management for multi-page website crawls."""

import asyncio
import logging
import urllib.parse
import uuid

from app.contracts.crawl import (
    CrawlJobCreateRequest,
    CrawlJobDTO,
    CrawlJobStatus,
)
from app.crawler.client import SafeHttpClient
from app.crawler.multi_page_crawler import MultiPageCrawler
from app.crawler.url_normalizer import normalize_url
from app.persistence.crawl_factory import crawl_repository
from app.persistence.crawl_interface import CrawlRepositoryInterface

logger = logging.getLogger(__name__)


class CrawlJobManager:
    """Singleton service managing background crawl tasks and cancellation triggers."""

    def __init__(self, repo: CrawlRepositoryInterface | None = None):
        self.repo = repo or crawl_repository
        self._active_tasks: dict[str, asyncio.Task] = {}
        self._active_crawlers: dict[str, MultiPageCrawler] = {}

    def start_crawl_job(
        self,
        request: CrawlJobCreateRequest,
        client: SafeHttpClient | None = None,
    ) -> CrawlJobDTO:
        """Validates request, creates job record, and launches asynchronous crawl worker."""
        job_id = str(uuid.uuid4())
        normalized_seed = normalize_url(request.url)
        parsed = urllib.parse.urlsplit(normalized_seed)
        base_domain = parsed.hostname or "unknown"

        job = CrawlJobDTO(
            jobId=job_id,
            seedUrl=request.url,
            baseDomain=base_domain,
            status=CrawlJobStatus.QUEUED,
            progressPercentage=0.0,
            pagesDiscovered=1,
            pagesCrawled=0,
            pagesFailed=0,
            pagesRemaining=1,
            currentDepth=0,
            maxPages=request.max_pages,
            maxDepth=request.max_depth,
        )

        persisted_job = self.repo.create_job(job)

        crawler = MultiPageCrawler(
            job=persisted_job,
            repo=self.repo,
            client=client,
            max_concurrency=request.max_concurrency,
            request_delay_seconds=request.request_delay_seconds,
            boundary=request.boundary.value,
        )
        self._active_crawlers[job_id] = crawler

        # Dispatch background task
        task = asyncio.create_task(self._run_crawler_task(job_id, crawler))
        self._active_tasks[job_id] = task

        return persisted_job

    async def _run_crawler_task(self, job_id: str, crawler: MultiPageCrawler) -> None:
        """Worker wrapper running crawler lifecycle safely with exception containment."""
        try:
            await crawler.execute_crawl()
        except asyncio.CancelledError:
            logger.info("Crawl task %s was cancelled.", job_id)
            self.repo.update_job_progress(job_id, status=CrawlJobStatus.CANCELLED)
        except Exception as exc:
            logger.exception("Unexpected error in crawl job %s", job_id)
            self.repo.update_job_progress(
                job_id,
                status=CrawlJobStatus.FAILED,
                error_message=f"Fatal crawler execution error: {exc}",
            )
        finally:
            self._active_tasks.pop(job_id, None)
            self._active_crawlers.pop(job_id, None)

    def cancel_crawl_job(self, job_id: str) -> bool:
        """Requests graceful cancellation of a running crawl job. Returns True if job was active."""
        crawler = self._active_crawlers.get(job_id)
        if crawler:
            crawler.cancel()

        task = self._active_tasks.get(job_id)
        if task and not task.done():
            task.cancel()
            return True

        job = self.repo.get_job(job_id)
        if job and job.status in (CrawlJobStatus.QUEUED, CrawlJobStatus.RUNNING):
            self.repo.update_job_progress(job_id, status=CrawlJobStatus.CANCELLED)
            return True

        return False

    def get_job(self, job_id: str) -> CrawlJobDTO | None:
        """Retrieves current job status from repository."""
        return self.repo.get_job(job_id)


# Global crawl manager singleton
job_manager = CrawlJobManager()
