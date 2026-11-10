"""Asynchronous multi-page website crawler with polite concurrency and SSRF safety.

Orchestrates:
- Robots.txt (RFC 9309) path checking with 5 distinct outcome states.
- XML Sitemap link discovery and seed ingestion.
- BFS crawl frontier ordering (seed=0, direct links=1, etc.).
- SSRF zero-trust revalidation for every discovered link.
- Continuous 20-rule SEO evaluation per page.
- Controlled rate limiting (minimum request intervals and max concurrency per host).
- Graceful cancellation and partial completion handling.
"""

import asyncio
import logging
import urllib.parse
import uuid
from datetime import UTC, datetime

from app.contracts.crawl import (
    CrawlJobDTO,
    CrawlJobStatus,
    CrawlPageDTO,
    CrawlPageStatus,
    DiscoveryMethod,
)
from app.contracts.enums import RuleCategory
from app.contracts.finding import Finding
from app.contracts.scan import CategoryScoreDTO
from app.crawler.aggregator import build_site_aggregate_report
from app.crawler.client import SafeHttpClient
from app.crawler.robots import (
    RobotsTxtResult,
    fetch_and_evaluate_robots_txt,
    parse_robots_txt,
)
from app.crawler.sitemap import discover_and_evaluate_sitemaps
from app.crawler.url_normalizer import (
    is_url_within_boundary,
    normalize_url,
)
from app.parsers.html import parse_html_document
from app.rules.registry import default_registry
from app.scoring.category import calculate_category_score
from app.scoring.completeness import calculate_report_completeness
from app.scoring.overall import calculate_overall_health_score

logger = logging.getLogger(__name__)


class MultiPageCrawler:
    """Asynchronous multi-page website crawler instance bound to a single CrawlJob."""

    def __init__(
        self,
        job: CrawlJobDTO,
        repo,
        client: SafeHttpClient | None = None,
        max_concurrency: int = 2,
        request_delay_seconds: float = 0.25,
        boundary: str = "SAME_ORIGIN",
    ):
        self.job = job
        self.repo = repo
        self.client = client or SafeHttpClient(verify_ssl=True)
        self.max_concurrency = max_concurrency
        self.request_delay_seconds = request_delay_seconds
        self.boundary = boundary
        self._cancel_requested = False
        self._robots_result: RobotsTxtResult | None = None
        self._robots_content: str | None = None

    def cancel(self) -> None:
        """Requests graceful cancellation of the active crawl job."""
        self._cancel_requested = True

    async def execute_crawl(self) -> CrawlJobDTO:
        """Runs the complete multi-page crawl lifecycle to completion or safe boundary."""
        job_id = self.job.job_id
        seed_url = self.job.seed_url
        logger.info("Starting multi-page crawl job %s for seed %s", job_id, seed_url)

        # 1. Update job to RUNNING
        self.job = self.repo.update_job_progress(
            job_id,
            status=CrawlJobStatus.RUNNING,
            pages_discovered=1,
            pages_crawled=0,
            pages_failed=0,
            pages_remaining=1,
            progress_percentage=0.0,
        )

        try:
            # 2. Normalize seed URL
            normalized_seed = normalize_url(seed_url)
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to normalize seed URL %s: %s", seed_url, exc)
            return self.repo.update_job_progress(
                job_id,
                status=CrawlJobStatus.FAILED,
                error_message=f"Invalid seed URL: {exc}",
            )

        # 3. Add seed page to frontier if not already present
        seed_page = CrawlPageDTO(
            pageId=uuid.uuid4().hex[:16],
            jobId=job_id,
            url=seed_url,
            normalizedUrl=normalized_seed,
            depth=0,
            parentUrl=None,
            discoveryMethod=DiscoveryMethod.SEED,
            status=CrawlPageStatus.PENDING,
        )
        self.repo.add_page(seed_page)

        # 4. Fetch and evaluate /robots.txt from origin root
        try:
            self._robots_result = await fetch_and_evaluate_robots_txt(self.client, normalized_seed)
            self._robots_content = self._robots_result.raw_content
        except Exception as exc:  # noqa: BLE001
            logger.warning("Robots.txt discovery failed for %s: %s", normalized_seed, exc)
            self._robots_result = RobotsTxtResult(
                is_present=False,
                status_code=500,
                error_reason=f"Failed to fetch robots.txt: {exc}",
            )

        # 5. Discover XML Sitemaps and ingest initial candidate links
        try:
            sitemap_result = await discover_and_evaluate_sitemaps(self.client, self._robots_result)
            if sitemap_result and sitemap_result.sampled_urls:
                sitemap_added = 0
                for s_url in sitemap_result.sampled_urls:
                    if sitemap_added >= self.job.max_pages:
                        break
                    try:
                        norm_s_url = normalize_url(s_url, base_url=normalized_seed)
                        if is_url_within_boundary(norm_s_url, normalized_seed, self.boundary):
                            page_dto = CrawlPageDTO(
                                pageId=uuid.uuid4().hex[:16],
                                jobId=job_id,
                                url=s_url,
                                normalizedUrl=norm_s_url,
                                depth=1,
                                parentUrl=sitemap_result.sitemap_url,
                                discoveryMethod=DiscoveryMethod.SITEMAP,
                                status=CrawlPageStatus.PENDING,
                            )
                            if self.repo.add_page(page_dto):
                                sitemap_added += 1
                    except Exception:  # noqa: S112, BLE001
                        continue
        except Exception as exc:  # noqa: BLE001
            logger.warning("Sitemap discovery failed for %s: %s", normalized_seed, exc)
            sitemap_result = None

        # 6. Main Crawl Loop (Polite Concurrency with Semaphore)
        semaphore = asyncio.Semaphore(self.max_concurrency)
        pages_crawled_count = 0
        pages_failed_count = 0
        max_depth_reached = 0

        while not self._cancel_requested:
            # Check if page quota reached
            remaining_quota = self.job.max_pages - pages_crawled_count
            if remaining_quota <= 0:
                logger.info("Crawl job %s reached max_pages limit (%d)", job_id, self.job.max_pages)
                break

            # Fetch next batch of pending pages ordered by depth (BFS), bounded by remaining quota
            batch_limit = min(self.max_concurrency, remaining_quota)
            pending_batch = self.repo.get_next_pending_pages(job_id, limit=batch_limit)
            if not pending_batch:
                # Queue exhausted
                break

            # Process pending batch
            tasks = [
                self._process_single_page(page, semaphore, normalized_seed, sitemap_result)
                for page in pending_batch
            ]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            for res in batch_results:
                if isinstance(res, tuple):
                    status, depth = res
                    if status == CrawlPageStatus.CRAWLED:
                        pages_crawled_count += 1
                        max_depth_reached = max(max_depth_reached, depth)
                    elif status == CrawlPageStatus.FAILED:
                        pages_failed_count += 1
                elif isinstance(res, Exception):
                    pages_failed_count += 1

            # Update progress counters
            all_pages, total_discovered = self.repo.list_pages(job_id, limit=500)
            pending_count = sum(1 for p in all_pages if p.status == CrawlPageStatus.PENDING)
            target_ceiling = min(total_discovered, self.job.max_pages)
            progress = round((pages_crawled_count / max(1, target_ceiling)) * 100.0, 1)

            self.repo.update_job_progress(
                job_id,
                pages_discovered=total_discovered,
                pages_crawled=pages_crawled_count,
                pages_failed=pages_failed_count,
                pages_remaining=pending_count,
                current_depth=max_depth_reached,
                progress_percentage=min(100.0, progress),
            )

        # 7. Finalize Lifecycle State
        final_pages, total_discovered = self.repo.list_pages(job_id, limit=500)
        pending_count = sum(1 for p in final_pages if p.status == CrawlPageStatus.PENDING)

        if self._cancel_requested:
            final_status = CrawlJobStatus.CANCELLED
        elif pending_count > 0 and pages_crawled_count >= self.job.max_pages:
            final_status = CrawlJobStatus.PARTIAL
        elif pages_crawled_count == 0 and pages_failed_count > 0:
            final_status = CrawlJobStatus.FAILED
        else:
            final_status = CrawlJobStatus.COMPLETED

        # 8. Compute and Store Site-Wide Aggregates
        crawled_pages = [p for p in final_pages if p.status == CrawlPageStatus.CRAWLED]
        page_findings_map: dict[str, list[Finding]] = {}
        page_cat_map: dict[str, dict[RuleCategory, CategoryScoreDTO]] = {}

        for p in crawled_pages:
            detail = self.repo.get_page_detail(job_id, p.page_id)
            if detail:
                page_findings_map[p.page_id] = detail.findings
                page_cat_map[p.page_id] = detail.category_scores

        site_report = build_site_aggregate_report(
            job_id=job_id,
            seed_url=seed_url,
            base_domain=self.job.base_domain,
            pages=final_pages,
            page_findings_map=page_findings_map,
            page_category_scores_map=page_cat_map,
        )
        self.repo.save_site_aggregate(site_report)

        # 9. Update final job status
        return self.repo.update_job_progress(
            job_id,
            status=final_status,
            pages_discovered=total_discovered,
            pages_crawled=pages_crawled_count,
            pages_failed=pages_failed_count,
            pages_remaining=pending_count,
            current_depth=max_depth_reached,
            progress_percentage=100.0 if final_status == CrawlJobStatus.COMPLETED else min(100.0, progress),
        )

    async def _process_single_page(
        self,
        page: CrawlPageDTO,
        semaphore: asyncio.Semaphore,
        seed_url: str,
        sitemap_result,
    ) -> tuple[CrawlPageStatus, int]:
        """Fetches, parses, checks robots.txt, and evaluates all 20 SEO rules on a single page."""
        async with semaphore:
            if self._cancel_requested:
                return CrawlPageStatus.SKIPPED, page.depth

            disc_method = getattr(page, "discovery_method", getattr(page, "discoveryMethod", DiscoveryMethod.HTML_LINK))

            try:
                # Check robots.txt path permission
                target_path = urllib.parse.urlsplit(page.url).path or "/"
                if self._robots_content:
                    _, is_allowed = parse_robots_txt(self._robots_content, target_path)
                    if not is_allowed:
                        disallowed_page = CrawlPageDTO(
                            pageId=page.page_id,
                            jobId=page.job_id,
                            url=page.url,
                            normalizedUrl=page.normalized_url,
                            depth=page.depth,
                            parentUrl=page.parent_url,
                            discoveryMethod=disc_method,
                            status=CrawlPageStatus.DISALLOWED,
                            errorReason="Blocked by robots.txt Disallow directive",
                        )
                        self.repo.update_page_result(disallowed_page, findings=[])
                        return CrawlPageStatus.DISALLOWED, page.depth

                # Politeness delay
                if self.request_delay_seconds > 0:
                    await asyncio.sleep(self.request_delay_seconds)

                # Mark FETCHING
                fetching_page = CrawlPageDTO(
                    pageId=page.page_id,
                    jobId=page.job_id,
                    url=page.url,
                    normalizedUrl=page.normalized_url,
                    depth=page.depth,
                    parentUrl=page.parent_url,
                    discoveryMethod=disc_method,
                    status=CrawlPageStatus.FETCHING,
                )
                self.repo.update_page_result(fetching_page, findings=[])

                # Network fetch via SafeHttpClient (enforcing SSRF protection & streaming byte caps)
                try:
                    crawl_result = await self.client.fetch(page.url)
                except Exception as exc:  # noqa: BLE001
                    failed_page = CrawlPageDTO(
                        pageId=page.page_id,
                        jobId=page.job_id,
                        url=page.url,
                        normalizedUrl=page.normalized_url,
                        depth=page.depth,
                        parentUrl=page.parent_url,
                        discoveryMethod=disc_method,
                        status=CrawlPageStatus.FAILED,
                        errorReason=f"Network fetch failed: {exc}",
                    )
                    self.repo.update_page_result(failed_page, findings=[])
                    return CrawlPageStatus.FAILED, page.depth

                # Parse HTML document
                doc = parse_html_document(
                    html_content=crawl_result.body,
                    target_url=crawl_result.final_url,
                    headers=crawl_result.headers,
                )

                # Evaluate 20 canonical SEO rules
                findings = default_registry.evaluate_all(
                    crawl_result=crawl_result,
                    document=doc,
                    robots_result=self._robots_result,
                    sitemap_result=sitemap_result,
                )

                # Compute category scores and overall health score
                cat_scores: dict[RuleCategory, CategoryScoreDTO] = {}
                cat_scores_map: dict[RuleCategory, float] = {}
                for category in [
                    RuleCategory.CRAWLABILITY,
                    RuleCategory.INDEXABILITY,
                    RuleCategory.DOCUMENT,
                    RuleCategory.CONTENT,
                    RuleCategory.STRUCTURED,
                ]:
                    res = calculate_category_score(category, findings)
                    cat_scores[category] = CategoryScoreDTO(
                        category=category,
                        score=res.score,
                        completeness=None,
                        applicableChecks=res.applicable_checks,
                        evaluatedChecks=res.evaluated_checks,
                    )
                    if res.score is not None:
                        cat_scores_map[category] = res.score

                overall_res = calculate_overall_health_score(cat_scores_map)
                completeness_res = calculate_report_completeness(findings)
                overall_score = overall_res.overall_score if overall_res else None
                completeness = completeness_res.completeness_score if completeness_res else None

                # Mark CRAWLED and store findings
                crawled_page = CrawlPageDTO(
                    pageId=page.page_id,
                    jobId=page.job_id,
                    url=page.url,
                    normalizedUrl=page.normalized_url,
                    depth=page.depth,
                    parentUrl=page.parent_url,
                    discoveryMethod=disc_method,
                    status=CrawlPageStatus.CRAWLED,
                    httpStatus=crawl_result.status_code,
                    responseTimeMs=crawl_result.response_time_ms,
                    title=doc.title_text,
                    canonicalUrl=doc.canonical_url,
                    overallScore=overall_score,
                    completenessScore=completeness,
                    crawledAt=datetime.now(UTC),
                )
                self.repo.update_page_result(crawled_page, findings=findings, category_scores=cat_scores)

                # Discover new internal links if below max_depth
                if page.depth < self.job.max_depth:
                    self._discover_and_queue_links(doc, page, seed_url)

                return CrawlPageStatus.CRAWLED, page.depth

            except Exception as unhandled_exc:
                logger.exception("Unexpected error processing page %s", page.url)
                error_page = CrawlPageDTO(
                    pageId=page.page_id,
                    jobId=page.job_id,
                    url=page.url,
                    normalizedUrl=page.normalized_url,
                    depth=page.depth,
                    parentUrl=page.parent_url,
                    discoveryMethod=disc_method,
                    status=CrawlPageStatus.FAILED,
                    errorReason=f"Processing error: {unhandled_exc}",
                )
                self.repo.update_page_result(error_page, findings=[])
                return CrawlPageStatus.FAILED, page.depth

    def _discover_and_queue_links(self, doc, current_page: CrawlPageDTO, seed_url: str) -> None:
        """Extracts internal links and canonical declarations from parsed document and adds to frontier."""
        next_depth = current_page.depth + 1

        # 1. HTML Links
        for link in doc.links:
            if not link.resolved_url or not link.is_internal:
                continue

            try:
                norm_link = normalize_url(link.resolved_url, base_url=current_page.url)
            except Exception:  # noqa: S112, BLE001
                continue

            if is_url_within_boundary(norm_link, seed_url, self.boundary):
                candidate_page = CrawlPageDTO(
                    pageId=uuid.uuid4().hex[:16],
                    jobId=current_page.job_id,
                    url=link.resolved_url,
                    normalizedUrl=norm_link,
                    depth=next_depth,
                    parentUrl=current_page.url,
                    discoveryMethod=DiscoveryMethod.HTML_LINK,
                    status=CrawlPageStatus.PENDING,
                )
                self.repo.add_page(candidate_page)

        # 2. Canonical URL if declared and internal
        if doc.canonical_url:
            try:
                norm_canonical = normalize_url(doc.canonical_url, base_url=current_page.url)
                if (
                    norm_canonical != current_page.normalized_url
                    and is_url_within_boundary(norm_canonical, seed_url, self.boundary)
                ):
                    candidate_canonical = CrawlPageDTO(
                        pageId=uuid.uuid4().hex[:16],
                        jobId=current_page.job_id,
                        url=doc.canonical_url,
                        normalizedUrl=norm_canonical,
                        depth=next_depth,
                        parentUrl=current_page.url,
                        discoveryMethod=DiscoveryMethod.CANONICAL,
                        status=CrawlPageStatus.PENDING,
                    )
                    self.repo.add_page(candidate_canonical)
            except Exception:  # noqa: S110, BLE001
                pass
