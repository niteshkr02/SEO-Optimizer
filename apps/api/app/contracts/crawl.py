"""Pydantic v2 contracts for multi-page asynchronous crawling and aggregate site audits."""

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel

from app.contracts.enums import IssueSeverity, RuleCategory
from app.contracts.finding import Finding
from app.contracts.scan import CategoryScoreDTO


class CrawlJobStatus(str, Enum):
    """Lifecycle states of a multi-page crawl job."""

    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class CrawlPageStatus(str, Enum):
    """Status of an individual discovered URL within a crawl job."""

    PENDING = "PENDING"
    FETCHING = "FETCHING"
    CRAWLED = "CRAWLED"
    FAILED = "FAILED"
    DISALLOWED = "DISALLOWED"
    SKIPPED = "SKIPPED"


class DiscoveryMethod(str, Enum):
    """Channel through which a candidate URL was discovered."""

    SEED = "SEED"
    HTML_LINK = "HTML_LINK"
    SITEMAP = "SITEMAP"
    CANONICAL = "CANONICAL"


class CrawlBoundary(str, Enum):
    """Boundary rule restricting crawl scope."""

    SAME_ORIGIN = "SAME_ORIGIN"
    SAME_DOMAIN = "SAME_DOMAIN"


# -----------------------------------------------------------------------------
# Request & Response Contracts
# -----------------------------------------------------------------------------


class CrawlJobCreateRequest(BaseModel):
    """Request payload to initiate an asynchronous multi-page crawl."""

    model_config = ConfigDict(
        frozen=True,
        alias_generator=to_camel,
        populate_by_name=True,
    )

    url: str = Field(..., description="Starting seed website URL.")
    max_pages: int = Field(
        default=25,
        ge=1,
        le=100,
        description="Maximum number of pages to crawl (1 to 100).",
    )
    max_depth: int = Field(
        default=3,
        ge=0,
        le=5,
        description="Maximum crawl link depth from seed (0 to 5, seed=0).",
    )
    boundary: CrawlBoundary = Field(
        default=CrawlBoundary.SAME_ORIGIN,
        description="SAME_ORIGIN | SAME_DOMAIN",
    )
    request_delay_seconds: float = Field(
        default=0.25,
        ge=0.1,
        le=2.0,
        description="Politeness interval between requests to same host.",
    )
    max_concurrency: int = Field(
        default=2,
        ge=1,
        le=5,
        description="Simultaneous connections allowed per host.",
    )

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        clean = v.strip()
        if not clean.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return clean


class CrawlJobDTO(BaseModel):
    """Telemetry and status entity representing an asynchronous crawl job."""

    model_config = ConfigDict(
        frozen=True,
        alias_generator=to_camel,
        populate_by_name=True,
    )

    job_id: str = Field(..., description="Unique crawl job identifier.")
    seed_url: str = Field(..., description="Original seed URL requested.")
    base_domain: str = Field(..., description="Normalized root hostname.")
    status: CrawlJobStatus = Field(default=CrawlJobStatus.QUEUED)
    progress_percentage: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="Calculated crawl completion percentage.",
    )
    pages_discovered: int = Field(default=1, ge=0)
    pages_crawled: int = Field(default=0, ge=0)
    pages_failed: int = Field(default=0, ge=0)
    pages_remaining: int = Field(default=1, ge=0)
    current_depth: int = Field(default=0, ge=0)
    max_pages: int = Field(default=25, ge=1)
    max_depth: int = Field(default=3, ge=0)
    started_at: datetime | None = Field(default=None)
    completed_at: datetime | None = Field(default=None)
    duration_seconds: float | None = Field(default=None)
    error_message: str | None = Field(default=None)


class CrawlPageDTO(BaseModel):
    """Summary of an individual crawled page in a website crawl."""

    model_config = ConfigDict(
        frozen=True,
        alias_generator=to_camel,
        populate_by_name=True,
    )

    page_id: str = Field(..., description="Unique page record identifier.")
    job_id: str = Field(..., description="Associated crawl job identifier.")
    url: str = Field(..., description="Requested page URL.")
    normalized_url: str = Field(..., description="Canonicalized deduplicated URL.")
    depth: int = Field(default=0, ge=0, description="Link distance from seed URL.")
    parent_url: str | None = Field(default=None, description="Discovered from page.")
    discovery_method: DiscoveryMethod = Field(default=DiscoveryMethod.HTML_LINK)
    status: CrawlPageStatus = Field(default=CrawlPageStatus.PENDING)
    http_status: int | None = Field(default=None, description="HTTP status code.")
    response_time_ms: int | None = Field(default=None, description="Roundtrip latency.")
    title: str | None = Field(default=None, description="Extracted HTML title.")
    canonical_url: str | None = Field(default=None, description="Declared canonical.")
    overall_score: float | None = Field(default=None, ge=0.0, le=100.0)
    completeness_score: float | None = Field(default=None, ge=0.0, le=100.0)
    error_reason: str | None = Field(default=None)
    crawled_at: datetime | None = Field(default=None)


class CrawlPageDetailDTO(BaseModel):
    """Detailed audit diagnostic results for an individual crawled page."""

    model_config = ConfigDict(
        frozen=True,
        alias_generator=to_camel,
        populate_by_name=True,
    )

    page: CrawlPageDTO
    findings: list[Finding] = Field(default_factory=list, description="20 canonical SEO findings.")
    category_scores: dict[RuleCategory, CategoryScoreDTO] = Field(
        default_factory=dict, description="Category-level scores for this page."
    )


class SiteIssueSummaryDTO(BaseModel):
    """Aggregated issue occurrence across multiple crawled pages."""

    model_config = ConfigDict(
        frozen=True,
        alias_generator=to_camel,
        populate_by_name=True,
    )

    rule_id: str = Field(..., description="Audit rule identifier.")
    category: RuleCategory = Field(..., description="Taxonomic category.")
    severity: IssueSeverity = Field(..., description="Impact severity rating.")
    title: str = Field(..., description="Rule title.")
    failing_pages_count: int = Field(default=0, ge=0, description="Count of pages failing this check.")
    total_pages_audited: int = Field(default=0, ge=0, description="Total pages evaluated.")
    impact_percentage: float = Field(default=0.0, ge=0.0, le=100.0)
    sample_urls: list[str] = Field(default_factory=list, description="Sample URLs affected.")
    sample_evidence: list[dict[str, Any]] = Field(
        default_factory=list, description="Verbatim evidence snapshots."
    )
    remediation_guidance: str = Field(..., description="Standard remediation instructions.")


class SiteAggregateReportDTO(BaseModel):
    """Comprehensive site-wide aggregated SEO health report."""

    model_config = ConfigDict(
        frozen=True,
        alias_generator=to_camel,
        populate_by_name=True,
    )

    job_id: str = Field(..., description="Crawl job identifier.")
    seed_url: str = Field(..., description="Seed website URL.")
    base_domain: str = Field(..., description="Target domain.")
    overall_score: float | None = Field(default=None, ge=0.0, le=100.0)
    completeness_score: float | None = Field(default=None, ge=0.0, le=100.0)
    category_scores: dict[RuleCategory, CategoryScoreDTO] = Field(default_factory=dict)
    total_pages_analyzed: int = Field(default=0, ge=0)
    total_issues_identified: int = Field(default=0, ge=0)
    unique_issues: list[SiteIssueSummaryDTO] = Field(default_factory=list)
    crawled_pages: list[CrawlPageDTO] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

