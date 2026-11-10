"""SQLite crawl repository adapter for local development and offline durability."""

import json
import sqlite3
import threading
from datetime import UTC, datetime
from pathlib import Path

from app.contracts.crawl import (
    CrawlJobDTO,
    CrawlJobStatus,
    CrawlPageDetailDTO,
    CrawlPageDTO,
    CrawlPageStatus,
    DiscoveryMethod,
    SiteAggregateReportDTO,
)
from app.contracts.enums import RuleCategory
from app.contracts.finding import Finding
from app.contracts.scan import CategoryScoreDTO
from app.persistence.crawl_interface import CrawlRepositoryInterface


class SQLiteCrawlRepository(CrawlRepositoryInterface):
    """Thread-safe SQLite persistent repository for multi-page website crawls."""

    def __init__(self, db_path: str = "seo_optimizer.db"):
        self.db_path = str(Path(db_path).resolve())
        self._lock = threading.RLock()
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def _init_db(self) -> None:
        with self._lock, self._get_connection() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS crawl_jobs (
                    job_id TEXT PRIMARY KEY,
                    seed_url TEXT NOT NULL,
                    base_domain TEXT NOT NULL,
                    status TEXT NOT NULL,
                    progress_percentage REAL NOT NULL DEFAULT 0.0,
                    pages_discovered INTEGER NOT NULL DEFAULT 1,
                    pages_crawled INTEGER NOT NULL DEFAULT 0,
                    pages_failed INTEGER NOT NULL DEFAULT 0,
                    pages_remaining INTEGER NOT NULL DEFAULT 1,
                    current_depth INTEGER NOT NULL DEFAULT 0,
                    max_pages INTEGER NOT NULL DEFAULT 25,
                    max_depth INTEGER NOT NULL DEFAULT 3,
                    started_at TEXT,
                    completed_at TEXT,
                    duration_seconds REAL,
                    error_message TEXT,
                    created_at TEXT NOT NULL DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS crawl_pages (
                    page_id TEXT PRIMARY KEY,
                    job_id TEXT NOT NULL REFERENCES crawl_jobs(job_id) ON DELETE CASCADE,
                    url TEXT NOT NULL,
                    normalized_url TEXT NOT NULL,
                    depth INTEGER NOT NULL DEFAULT 0,
                    parent_url TEXT,
                    discovery_method TEXT NOT NULL DEFAULT 'HTML_LINK',
                    status TEXT NOT NULL DEFAULT 'PENDING',
                    http_status INTEGER,
                    response_time_ms INTEGER,
                    title TEXT,
                    canonical_url TEXT,
                    overall_score REAL,
                    completeness_score REAL,
                    error_reason TEXT,
                    crawled_at TEXT,
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    UNIQUE(job_id, normalized_url)
                );

                CREATE TABLE IF NOT EXISTS crawl_page_findings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT NOT NULL REFERENCES crawl_jobs(job_id) ON DELETE CASCADE,
                    page_id TEXT NOT NULL REFERENCES crawl_pages(page_id) ON DELETE CASCADE,
                    rule_id TEXT NOT NULL,
                    category TEXT NOT NULL,
                    state TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    weight INTEGER NOT NULL,
                    evidence_json TEXT NOT NULL,
                    remediation_guidance TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT (datetime('now'))
                );

                CREATE TABLE IF NOT EXISTS crawl_page_category_scores (
                    job_id TEXT NOT NULL REFERENCES crawl_jobs(job_id) ON DELETE CASCADE,
                    page_id TEXT NOT NULL REFERENCES crawl_pages(page_id) ON DELETE CASCADE,
                    category TEXT NOT NULL,
                    score_json TEXT NOT NULL,
                    PRIMARY KEY(page_id, category)
                );

                CREATE TABLE IF NOT EXISTS crawl_site_aggregates (
                    job_id TEXT PRIMARY KEY REFERENCES crawl_jobs(job_id) ON DELETE CASCADE,
                    seed_url TEXT NOT NULL,
                    base_domain TEXT NOT NULL,
                    overall_score REAL,
                    completeness_score REAL,
                    category_scores_json TEXT NOT NULL,
                    total_pages_analyzed INTEGER NOT NULL,
                    total_issues_identified INTEGER NOT NULL,
                    unique_issues_json TEXT NOT NULL,
                    generated_at TEXT NOT NULL DEFAULT (datetime('now'))
                );

                CREATE INDEX IF NOT EXISTS idx_crawl_pages_job_status ON crawl_pages(job_id, status);
                CREATE INDEX IF NOT EXISTS idx_crawl_pages_depth ON crawl_pages(job_id, depth);
                CREATE INDEX IF NOT EXISTS idx_crawl_findings_page ON crawl_page_findings(job_id, page_id);
                """
            )

    def create_job(self, job: CrawlJobDTO) -> CrawlJobDTO:
        with self._lock, self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO crawl_jobs (
                    job_id, seed_url, base_domain, status, progress_percentage,
                    pages_discovered, pages_crawled, pages_failed, pages_remaining,
                    current_depth, max_pages, max_depth, started_at, completed_at,
                    duration_seconds, error_message
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job.job_id,
                    job.seed_url,
                    job.base_domain,
                    job.status.value,
                    job.progress_percentage,
                    job.pages_discovered,
                    job.pages_crawled,
                    job.pages_failed,
                    job.pages_remaining,
                    job.current_depth,
                    job.max_pages,
                    job.max_depth,
                    job.started_at.isoformat() if job.started_at else None,
                    job.completed_at.isoformat() if job.completed_at else None,
                    job.duration_seconds,
                    job.error_message,
                ),
            )
            return job

    def get_job(self, job_id: str) -> CrawlJobDTO | None:
        with self._lock, self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM crawl_jobs WHERE job_id = ?", (job_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_job(row)

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
        with self._lock, self._get_connection() as conn:
            existing = self.get_job(job_id)
            if not existing:
                return None

            started_at = existing.started_at
            completed_at = existing.completed_at
            duration_seconds = existing.duration_seconds

            if status == CrawlJobStatus.RUNNING and started_at is None:
                started_at = datetime.now(UTC)
            elif (
                status in (CrawlJobStatus.COMPLETED, CrawlJobStatus.PARTIAL, CrawlJobStatus.FAILED, CrawlJobStatus.CANCELLED)
                and completed_at is None
            ):
                completed_at = datetime.now(UTC)
                if started_at:
                    duration_seconds = max(0.0, (completed_at - started_at).total_seconds())

            conn.execute(
                """
                UPDATE crawl_jobs SET
                    status = COALESCE(?, status),
                    pages_discovered = COALESCE(?, pages_discovered),
                    pages_crawled = COALESCE(?, pages_crawled),
                    pages_failed = COALESCE(?, pages_failed),
                    pages_remaining = COALESCE(?, pages_remaining),
                    current_depth = COALESCE(?, current_depth),
                    progress_percentage = COALESCE(?, progress_percentage),
                    error_message = COALESCE(?, error_message),
                    started_at = COALESCE(?, started_at),
                    completed_at = COALESCE(?, completed_at),
                    duration_seconds = COALESCE(?, duration_seconds)
                WHERE job_id = ?
                """,
                (
                    status.value if status else None,
                    pages_discovered,
                    pages_crawled,
                    pages_failed,
                    pages_remaining,
                    current_depth,
                    progress_percentage,
                    error_message,
                    started_at.isoformat() if started_at else None,
                    completed_at.isoformat() if completed_at else None,
                    duration_seconds,
                    job_id,
                ),
            )
            return self.get_job(job_id)

    def add_page(self, page: CrawlPageDTO) -> bool:
        with self._lock, self._get_connection() as conn:
            try:
                conn.execute(
                    """
                    INSERT INTO crawl_pages (
                        page_id, job_id, url, normalized_url, depth, parent_url,
                        discovery_method, status, http_status, response_time_ms,
                        title, canonical_url, overall_score, completeness_score,
                        error_reason, crawled_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        page.page_id,
                        page.job_id,
                        page.url,
                        page.normalized_url,
                        page.depth,
                        page.parent_url,
                        page.discovery_method.value,
                        page.status.value,
                        page.http_status,
                        page.response_time_ms,
                        page.title,
                        page.canonical_url,
                        page.overall_score,
                        page.completeness_score,
                        page.error_reason,
                        page.crawled_at.isoformat() if page.crawled_at else None,
                    ),
                )
                return True
            except sqlite3.IntegrityError:
                # Already exists (duplicate normalized_url for this job)
                return False

    def get_page(self, job_id: str, page_id: str) -> CrawlPageDTO | None:
        with self._lock, self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM crawl_pages WHERE job_id = ? AND page_id = ?",
                (job_id, page_id),
            )
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_page(row)

    def get_page_by_url(self, job_id: str, normalized_url: str) -> CrawlPageDTO | None:
        with self._lock, self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM crawl_pages WHERE job_id = ? AND normalized_url = ?",
                (job_id, normalized_url),
            )
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_page(row)

    def get_next_pending_pages(self, job_id: str, limit: int = 10) -> list[CrawlPageDTO]:
        with self._lock, self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT * FROM crawl_pages 
                WHERE job_id = ? AND status = 'PENDING'
                ORDER BY depth ASC, rowid ASC
                LIMIT ?
                """,
                (job_id, limit),
            )
            return [self._row_to_page(r) for r in cursor.fetchall()]

    def update_page_result(
        self,
        page: CrawlPageDTO,
        findings: list[Finding],
        category_scores: dict[str, CategoryScoreDTO] | None = None,
    ) -> CrawlPageDTO:
        with self._lock, self._get_connection() as conn:
            conn.execute(
                """
                UPDATE crawl_pages SET
                    status = ?,
                    http_status = ?,
                    response_time_ms = ?,
                    title = ?,
                    canonical_url = ?,
                    overall_score = ?,
                    completeness_score = ?,
                    error_reason = ?,
                    crawled_at = ?
                WHERE job_id = ? AND page_id = ?
                """,
                (
                    page.status.value,
                    page.http_status,
                    page.response_time_ms,
                    page.title,
                    page.canonical_url,
                    page.overall_score,
                    page.completeness_score,
                    page.error_reason,
                    page.crawled_at.isoformat() if page.crawled_at else None,
                    page.job_id,
                    page.page_id,
                ),
            )

            # Insert findings
            conn.execute(
                "DELETE FROM crawl_page_findings WHERE job_id = ? AND page_id = ?",
                (page.job_id, page.page_id),
            )
            for f in findings:
                conn.execute(
                    """
                    INSERT INTO crawl_page_findings (
                        job_id, page_id, rule_id, category, state, severity, weight,
                        evidence_json, remediation_guidance
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        page.job_id,
                        page.page_id,
                        getattr(f, "ruleId", getattr(f, "rule_id", "")),
                        f.category.value if hasattr(f.category, "value") else str(f.category),
                        f.state.value if hasattr(f.state, "value") else str(f.state),
                        f.severity.value if hasattr(f.severity, "value") else str(f.severity),
                        f.weight,
                        f.evidence.model_dump_json() if hasattr(f.evidence, "model_dump_json") else json.dumps(f.evidence),
                        getattr(f, "remediationGuidance", getattr(f, "remediation_guidance", "")),
                    ),
                )

            # Insert category scores
            if category_scores:
                conn.execute(
                    "DELETE FROM crawl_page_category_scores WHERE job_id = ? AND page_id = ?",
                    (page.job_id, page.page_id),
                )
                for cat, c_dto in category_scores.items():
                    conn.execute(
                        """
                        INSERT INTO crawl_page_category_scores (job_id, page_id, category, score_json)
                        VALUES (?, ?, ?, ?)
                        """,
                        (
                            page.job_id,
                            page.page_id,
                            cat.value if hasattr(cat, "value") else str(cat),
                            c_dto.model_dump_json() if hasattr(c_dto, "model_dump_json") else json.dumps(c_dto),
                        ),
                    )
            return page

    def list_pages(
        self,
        job_id: str,
        depth: int | None = None,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[CrawlPageDTO], int]:
        with self._lock, self._get_connection() as conn:
            query = "SELECT * FROM crawl_pages WHERE job_id = ?"
            params: list[object] = [job_id]

            if depth is not None:
                query += " AND depth = ?"
                params.append(depth)
            if status is not None:
                query += " AND status = ?"
                params.append(status)

            # Count total matching
            count_query = query.replace("SELECT *", "SELECT COUNT(*)")
            cursor = conn.execute(count_query, params)
            total = cursor.fetchone()[0]

            query += " ORDER BY depth ASC, rowid ASC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            cursor = conn.execute(query, params)
            pages = [self._row_to_page(r) for r in cursor.fetchall()]
            return pages, total

    def get_page_detail(self, job_id: str, page_id: str) -> CrawlPageDetailDTO | None:
        with self._lock, self._get_connection() as conn:
            page = self.get_page(job_id, page_id)
            if not page:
                return None

            # Load findings
            f_cursor = conn.execute(
                "SELECT * FROM crawl_page_findings WHERE job_id = ? AND page_id = ? ORDER BY id ASC",
                (job_id, page_id),
            )
            findings: list[Finding] = []
            for r in f_cursor.fetchall():
                ev_data = json.loads(r["evidence_json"])
                findings.append(
                    Finding(
                        ruleId=r["rule_id"],
                        category=r["category"],
                        title=r["rule_id"],
                        description="",
                        state=r["state"],
                        severity=r["severity"],
                        weight=r["weight"],
                        evidence=ev_data,
                        remediationGuidance=r["remediation_guidance"],
                    )
                )

            # Load category scores
            cat_cursor = conn.execute(
                "SELECT * FROM crawl_page_category_scores WHERE job_id = ? AND page_id = ?",
                (job_id, page_id),
            )
            cat_scores: dict[RuleCategory, CategoryScoreDTO] = {}
            for r in cat_cursor.fetchall():
                c_data = json.loads(r["score_json"])
                cat_enum = RuleCategory(r["category"]) if r["category"] in RuleCategory._value2member_map_ else r["category"]
                cat_scores[cat_enum] = CategoryScoreDTO(**c_data)

            return CrawlPageDetailDTO(page=page, findings=findings, category_scores=cat_scores)

    def save_site_aggregate(self, report: SiteAggregateReportDTO) -> SiteAggregateReportDTO:
        with self._lock, self._get_connection() as conn:
            cat_json = json.dumps({(k.value if hasattr(k, "value") else str(k)): v.model_dump() for k, v in report.category_scores.items()})
            issues_json = json.dumps([i.model_dump() for i in report.unique_issues])

            conn.execute(
                """
                INSERT OR REPLACE INTO crawl_site_aggregates (
                    job_id, seed_url, base_domain, overall_score, completeness_score,
                    category_scores_json, total_pages_analyzed, total_issues_identified,
                    unique_issues_json, generated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    report.job_id,
                    report.seed_url,
                    report.base_domain,
                    report.overall_score,
                    report.completeness_score,
                    cat_json,
                    report.total_pages_analyzed,
                    report.total_issues_identified,
                    issues_json,
                    report.generated_at.isoformat(),
                ),
            )
            return report

    def get_site_aggregate(self, job_id: str) -> SiteAggregateReportDTO | None:
        with self._lock, self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM crawl_site_aggregates WHERE job_id = ?", (job_id,))
            row = cursor.fetchone()
            if not row:
                return None

            cat_dict = json.loads(row["category_scores_json"])
            cat_scores = {
                (RuleCategory(k) if k in RuleCategory._value2member_map_ else k): CategoryScoreDTO(**v)
                for k, v in cat_dict.items()
            }
            issues_list = json.loads(row["unique_issues_json"])

            # Fetch list of crawled pages
            pages, _ = self.list_pages(job_id, status=CrawlPageStatus.CRAWLED.value, limit=100)

            return SiteAggregateReportDTO(
                jobId=row["job_id"],
                seedUrl=row["seed_url"],
                baseDomain=row["base_domain"],
                overallScore=row["overall_score"],
                completenessScore=row["completeness_score"],
                categoryScores=cat_scores,
                totalPagesAnalyzed=row["total_pages_analyzed"],
                totalIssuesIdentified=row["total_issues_identified"],
                uniqueIssues=issues_list,
                crawledPages=pages,
                generatedAt=datetime.fromisoformat(row["generated_at"]),
            )

    def reset(self) -> None:
        with self._lock, self._get_connection() as conn:
            conn.executescript(
                """
                DELETE FROM crawl_page_findings;
                DELETE FROM crawl_page_category_scores;
                DELETE FROM crawl_site_aggregates;
                DELETE FROM crawl_pages;
                DELETE FROM crawl_jobs;
                """
            )

    @staticmethod
    def _row_to_job(row: sqlite3.Row) -> CrawlJobDTO:
        return CrawlJobDTO(
            jobId=row["job_id"],
            seedUrl=row["seed_url"],
            baseDomain=row["base_domain"],
            status=CrawlJobStatus(row["status"]),
            progressPercentage=row["progress_percentage"],
            pagesDiscovered=row["pages_discovered"],
            pagesCrawled=row["pages_crawled"],
            pagesFailed=row["pages_failed"],
            pagesRemaining=row["pages_remaining"],
            currentDepth=row["current_depth"],
            maxPages=row["max_pages"],
            maxDepth=row["max_depth"],
            startedAt=datetime.fromisoformat(row["started_at"]) if row["started_at"] else None,
            completedAt=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
            durationSeconds=row["duration_seconds"],
            errorMessage=row["error_message"],
        )

    @staticmethod
    def _row_to_page(row: sqlite3.Row) -> CrawlPageDTO:
        return CrawlPageDTO(
            pageId=row["page_id"],
            jobId=row["job_id"],
            url=row["url"],
            normalizedUrl=row["normalized_url"],
            depth=row["depth"],
            parentUrl=row["parent_url"],
            discoveryMethod=DiscoveryMethod(row["discovery_method"]),
            status=CrawlPageStatus(row["status"]),
            httpStatus=row["http_status"],
            responseTimeMs=row["response_time_ms"],
            title=row["title"],
            canonicalUrl=row["canonical_url"],
            overallScore=row["overall_score"],
            completenessScore=row["completeness_score"],
            errorReason=row["error_reason"],
            crawledAt=datetime.fromisoformat(row["crawled_at"]) if row["crawled_at"] else None,
        )
