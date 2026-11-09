"""Scan request and response transfer models."""

from datetime import UTC, datetime

from pydantic import BaseModel, Field, HttpUrl

from app.contracts.enums import RuleCategory, ScanStatus
from app.contracts.finding import Finding


class ScanRequest(BaseModel):
    """Public scan request payload."""

    url: HttpUrl = Field(
        ..., description="Target webpage URL to audit (HTTP or HTTPS)."
    )


class CategoryScoreDTO(BaseModel):
    """Detailed score summary for an audit category."""

    category: RuleCategory = Field(..., description="Category identifier.")
    score: float | None = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="Category score (0-100), or None if no applicable checks evaluated.",
    )
    completeness: float | None = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="Percentage of applicable checks that yielded definitive PASS/FAIL.",
    )
    applicableChecks: int = Field(
        default=0, ge=0, description="Total applicable checks in category."
    )
    evaluatedChecks: int = Field(
        default=0, ge=0, description="Total checks definitively evaluated."
    )


class RobotsTxtSummaryDTO(BaseModel):
    """Summary of robots.txt discovery and path permission evaluation."""

    isPresent: bool = Field(
        ..., description="True if /robots.txt exists with status 200."
    )
    statusCode: int = Field(..., description="HTTP status code from /robots.txt fetch.")
    sitemapUrls: list[str] = Field(
        default_factory=list, description="Sitemap URLs declared in robots.txt."
    )
    isTargetAllowed: bool | None = Field(
        default=None,
        description="True if target path is permitted by robots.txt rules, False if blocked, None if absent.",
    )
    errorReason: str | None = Field(
        default=None, description="Error reason if fetch failed."
    )


class SitemapSummaryDTO(BaseModel):
    """Summary of XML sitemap discovery and Model E12 evaluation."""

    isSitemapFound: bool = Field(
        ..., description="True if a valid XML sitemap was discovered."
    )
    sitemapUrl: str | None = Field(
        default=None, description="Primary sitemap URL evaluated."
    )
    sitemapSource: str = Field(
        default="NONE",
        description="Discovery source: ROBOTS_TXT | HTTP_HEADER | FALLBACK_ROOT | NONE",
    )
    totalUrlsSampled: int = Field(
        default=0, ge=0, description="Count of URLs sampled from sitemap."
    )
    healthScore: float | None = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="Model E12 sitemap URL health percentage (0-100), or None if unavailable.",
    )
    errorReason: str | None = Field(
        default=None, description="Error reason if discovery or parsing failed."
    )


class AuditReportDTO(BaseModel):
    """Comprehensive evidence-backed SEO audit report response."""

    scanToken: str = Field(..., description="Cryptographic unique scan identifier.")
    targetUrl: str = Field(..., description="Initial requested URL.")
    finalUrl: str = Field(..., description="Final landing URL following redirects.")
    statusCode: int = Field(..., description="Final HTTP status code.")
    status: ScanStatus = Field(
        default=ScanStatus.COMPLETED, description="Scan operational status."
    )
    overallScore: float | None = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="Overall SEO Health Score (0-100), or None if unavailable.",
    )
    categoryScores: dict[RuleCategory, CategoryScoreDTO] = Field(
        default_factory=dict,
        description="Dictionary of category scores.",
    )
    completenessScore: float | None = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="Overall report completeness index (0-100).",
    )
    categoryAvailability: dict[RuleCategory, bool] = Field(
        default_factory=dict,
        description="Explicit map of category availability.",
    )
    findings: list[Finding] = Field(
        default_factory=list,
        description="List of all evaluated findings with evidence.",
    )
    robotsSummary: RobotsTxtSummaryDTO | None = Field(
        default=None,
        description="Summary of robots.txt discovery and path evaluation.",
    )
    sitemapSummary: SitemapSummaryDTO | None = Field(
        default=None,
        description="Summary of XML sitemap discovery and Model E12 evaluation.",
    )
    isSpaDetected: bool = Field(
        default=False,
        description="True if static analysis detected Single-Page Application behavior.",
    )
    rulesetVersion: str = Field(default="1.0.0", description="Ruleset version applied.")
    scoringModelVersion: str = Field(
        default="1.0.0", description="Scoring model version applied."
    )
    createdAt: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Scan execution timestamp.",
    )
