"""Pydantic v2 contracts for Consultation Service Briefs."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from app.contracts.enums import IssueSeverity, RuleCategory
from app.resolution.models import ResolutionTask
from app.verification.models import FindingComparisonDTO


class ClientDetailsDTO(BaseModel):
    """Customer and organizational details from inquiry."""

    model_config = ConfigDict(frozen=True, alias_generator=to_camel, populate_by_name=True)

    customer_name: str
    business_email: str
    phone_number: str
    website_url: str
    business_category: str
    target_city: str
    requested_service: str
    urgency: str
    problem_description: str


class AuditScopeDTO(BaseModel):
    """Scope and telemetry coverage of the associated audit."""

    model_config = ConfigDict(frozen=True, alias_generator=to_camel, populate_by_name=True)

    has_audit_report: bool
    scan_token: str | None = None
    scan_timestamp: datetime | None = None
    target_url: str
    status_code: int | None = None
    overall_health_score: float | None = None
    completeness_score: float | None = None
    total_checks_evaluated: int = 0
    failing_checks_count: int = 0
    warning_checks_count: int = 0
    passed_checks_count: int = 0


class CriticalIssueSummaryDTO(BaseModel):
    """Summarized critical or high-severity finding with verbatim evidence."""

    model_config = ConfigDict(frozen=True, alias_generator=to_camel, populate_by_name=True)

    rule_id: str
    category: RuleCategory
    severity: IssueSeverity
    title: str
    description: str
    observed_value: str | None = None
    expected_value: str | None = None
    raw_snippet: str | None = None
    target_element: str | None = None
    remediation_guidance: str


class ServiceBriefDTO(BaseModel):
    """Complete evidence-backed consultation brief for SEO engineers and clients."""

    model_config = ConfigDict(frozen=True, alias_generator=to_camel, populate_by_name=True)

    brief_id: str = Field(..., description="Unique service brief identifier")
    lead_id: str = Field(..., description="Linked lead inquiry identifier")
    generated_at: datetime = Field(..., description="Brief generation timestamp")

    client_details: ClientDetailsDTO
    audit_scope: AuditScopeDTO

    critical_issues: list[CriticalIssueSummaryDTO] = Field(
        default_factory=list,
        description="Verified CRITICAL and HIGH severity findings",
    )
    proposed_solutions: list[ResolutionTask] = Field(
        default_factory=list,
        description="Actionable engineering resolution tasks with procedures and risks",
    )
    implementation_priorities: list[ResolutionTask] = Field(
        default_factory=list,
        description="Tasks sorted by Model E21 RICE Priority",
    )
    verification_summary: list[FindingComparisonDTO] | None = Field(
        default=None,
        description="Before/after verification comparisons if re-scan is available",
    )
    unknown_and_unavailable_disclosures: list[str] = Field(
        default_factory=list,
        description="Explicit disclosures of data points not measured or unavailable",
    )
    ranking_disclaimer: str = Field(
        default=(
            "Google ranking and search engine placement are not guaranteed. Deterministic "
            "code resolutions and technical optimizations eliminate standards-compliance "
            "defects, crawling impediments, and indexation blockers; however, final SERP "
            "positions depend on proprietary external search algorithms, domain history, "
            "and competitor actions."
        ),
        description="Statutory legal and technical disclaimer regarding search engine rankings",
    )
