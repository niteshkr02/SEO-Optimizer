"""Consultation service brief generator combining audit, resolution, and verification."""

import uuid
from datetime import UTC, datetime

from app.contracts.brief import (
    AuditScopeDTO,
    ClientDetailsDTO,
    CriticalIssueSummaryDTO,
    ServiceBriefDTO,
)
from app.contracts.enums import IssueSeverity, RuleState
from app.contracts.lead import LeadDTO
from app.contracts.scan import AuditReportDTO
from app.leads.pdf_export import generate_brief_pdf
from app.persistence.repository import lead_repository
from app.resolution.generator import ResolutionGenerator
from app.resolution.models import ResolutionPlanDTO
from app.verification.models import VerificationReportDTO

DEFAULT_RANKING_DISCLAIMER = (
    "Google ranking and search engine placement are not guaranteed. Deterministic "
    "code resolutions and technical optimizations eliminate standards-compliance "
    "defects, crawling impediments, and indexation blockers; however, final SERP "
    "positions depend on proprietary external search algorithms, domain history, "
    "and competitor actions."
)

STANDARD_DISCLOSURES = [
    "Competitor SERP intelligence and keyword ranking positions are unmeasured in this single-page diagnostic.",
    "Historical organic search performance and Google Search Console click-through curves are unavailable without authorized OAuth access.",
    "Client source code repository file paths and branch configurations are unmeasured during this public scan.",
    "Field Core Web Vitals (CrUX 75th percentile) are unavailable without aggregate 28-day user telemetry.",
]


class ServiceBriefGenerator:
    """Combines lead inquiry, audit report, and resolution plan into an advisory brief."""

    def __init__(self) -> None:
        self.resolution_generator = ResolutionGenerator()

    def generate_brief(
        self,
        lead: LeadDTO,
        audit_report: AuditReportDTO | None = None,
        resolution_plan: ResolutionPlanDTO | None = None,
        verification_report: VerificationReportDTO | None = None,
    ) -> ServiceBriefDTO:
        """Constructs a deterministic, evidence-backed consultation service brief."""
        now = datetime.now(UTC)
        brief_id = str(uuid.uuid4())

        # If audit report not explicitly provided, attempt to look up via scan_token
        if audit_report is None and lead.scan_token:
            audit_report = lead_repository.get_scan(lead.scan_token)

        # 1. Client details
        client_details = ClientDetailsDTO(
            customer_name=lead.customer_name,
            business_email=lead.business_email,
            phone_number=lead.phone_number,
            website_url=lead.website_url,
            business_category=lead.business_category,
            target_city=lead.target_city,
            requested_service=lead.requested_service,
            urgency=lead.urgency.value if hasattr(lead.urgency, "value") else str(lead.urgency),
            problem_description=lead.problem_description,
        )

        # 2. Audit Scope
        if audit_report is not None:
            failing_count = sum(1 for f in audit_report.findings if f.state == RuleState.FAIL)
            warning_count = sum(
                1
                for f in audit_report.findings
                if f.state == RuleState.FAIL and f.severity in (IssueSeverity.LOW, IssueSeverity.INFO)
            )
            passed_count = sum(1 for f in audit_report.findings if f.state == RuleState.PASS)
            evaluated_count = sum(
                1
                for f in audit_report.findings
                if f.state in (RuleState.PASS, RuleState.FAIL)
            )

            audit_scope = AuditScopeDTO(
                has_audit_report=True,
                scan_token=audit_report.scanToken,
                scan_timestamp=audit_report.createdAt,
                target_url=audit_report.targetUrl,
                status_code=audit_report.statusCode,
                overall_health_score=audit_report.overallScore,
                completeness_score=audit_report.completenessScore,
                total_checks_evaluated=evaluated_count,
                failing_checks_count=failing_count,
                warning_checks_count=warning_count,
                passed_checks_count=passed_count,
            )

            # 3. Critical & High Issues
            critical_issues = [
                CriticalIssueSummaryDTO(
                    rule_id=f.ruleId,
                    category=f.category,
                    severity=f.severity,
                    title=f.title,
                    description=f.description,
                    observed_value=f.evidence.observedValue,
                    expected_value=f.evidence.expectedValue,
                    raw_snippet=f.evidence.rawSnippet,
                    target_element=f.evidence.targetElement,
                    remediation_guidance=f.remediationGuidance,
                )
                for f in audit_report.findings
                if f.state == RuleState.FAIL
                and f.severity in (IssueSeverity.CRITICAL, IssueSeverity.HIGH)
            ]

            # 4. Proposed solutions & priorities
            if resolution_plan is None:
                resolution_plan = self.resolution_generator.generate_plan(audit_report)

            proposed_solutions = list(resolution_plan.tasks)
            implementation_priorities = sorted(
                resolution_plan.tasks,
                key=lambda t: t.priorityScore,
                reverse=True,
            )
        else:
            audit_scope = AuditScopeDTO(
                has_audit_report=False,
                scan_token=None,
                scan_timestamp=None,
                target_url=lead.website_url,
                status_code=None,
                overall_health_score=None,
                completeness_score=None,
                total_checks_evaluated=0,
                failing_checks_count=0,
                warning_checks_count=0,
                passed_checks_count=0,
            )
            critical_issues = []
            proposed_solutions = []
            implementation_priorities = []

        verification_summary = (
            verification_report.finding_comparisons if verification_report else None
        )

        return ServiceBriefDTO(
            brief_id=brief_id,
            lead_id=lead.id,
            generated_at=now,
            client_details=client_details,
            audit_scope=audit_scope,
            critical_issues=critical_issues,
            proposed_solutions=proposed_solutions,
            implementation_priorities=implementation_priorities,
            verification_summary=verification_summary,
            unknown_and_unavailable_disclosures=STANDARD_DISCLOSURES,
            ranking_disclaimer=DEFAULT_RANKING_DISCLAIMER,
        )

    def export_markdown(self, brief: ServiceBriefDTO) -> str:
        """Renders the consultation brief as GitHub-flavored Markdown."""
        lines = [
            f"# Technical SEO Consultation Brief: {brief.client_details.website_url}",
            "",
            f"**Brief ID:** `{brief.brief_id}`  ",
            f"**Generated:** {brief.generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}  ",
            f"**Client Contact:** {brief.client_details.customer_name} ({brief.client_details.business_email})  ",
            f"**Urgency:** {brief.client_details.urgency}  ",
            "",
            "---",
            "",
            "## 1. Executive Summary & Audit Scope",
            "",
        ]

        if brief.audit_scope.has_audit_report:
            score_str = (
                f"{brief.audit_scope.overall_health_score:.1f}/100"
                if brief.audit_scope.overall_health_score is not None
                else "Unmeasured"
            )
            comp_str = (
                f"{brief.audit_scope.completeness_score:.1f}%"
                if brief.audit_scope.completeness_score is not None
                else "N/A"
            )
            lines.extend(
                [
                    f"- **Target URL:** {brief.audit_scope.target_url}",
                    f"- **HTTP Status:** `{brief.audit_scope.status_code}`",
                    f"- **Overall Health Score (Model E3):** **{score_str}**",
                    f"- **Report Completeness (Model E5):** **{comp_str}**",
                    f"- **Critical/High Impediments:** **{len(brief.critical_issues)}**",
                    f"- **Total Checks Evaluated:** {brief.audit_scope.total_checks_evaluated}",
                ]
            )
        else:
            lines.append(
                "> [!NOTE]\n> No single-page audit report was linked to this inquiry. Scope is based on client submission."
            )

        lines.extend(
            [
                "",
                "### Client Problem Statement",
                f"> {brief.client_details.problem_description}",
                "",
                "---",
                "",
                "## 2. Verified Critical Findings & Technical Evidence",
                "",
            ]
        )

        if not brief.critical_issues:
            lines.append("*No CRITICAL or HIGH severity issues identified in this audit.*")
        else:
            for idx, issue in enumerate(brief.critical_issues, 1):
                lines.extend(
                    [
                        f"### {idx}. [{issue.severity}] {issue.title} (`{issue.rule_id}`)",
                        f"- **Category:** `{issue.category}`",
                        f"- **Observed Value:** `{issue.observed_value or 'N/A'}`",
                        f"- **Expected Value:** `{issue.expected_value or 'N/A'}`",
                    ]
                )
                if issue.raw_snippet:
                    lines.extend(
                        [
                            "- **Observed Snippet:**",
                            "```html",
                            issue.raw_snippet[:500],
                            "```",
                        ]
                    )
                lines.extend(
                    [
                        f"- **Recommended Correction:** {issue.remediation_guidance}",
                        "",
                    ]
                )

        lines.extend(
            [
                "---",
                "",
                "## 3. Prioritized Engineering Action Plan (Model E21)",
                "",
            ]
        )

        if not brief.implementation_priorities:
            lines.append("*No action items generated.*")
        else:
            for idx, task in enumerate(brief.implementation_priorities, 1):
                lines.extend(
                    [
                        f"#### Task {idx}: {task.title}",
                        f"- **RICE Priority Score (E21):** `{task.priorityScore:.1f}`",
                        f"- **Root-Cause Triage (E20):** `{task.triageScore:.1f}`",
                        f"- **Action Type:** `{task.actionType.value if hasattr(task.actionType, 'value') else task.actionType}`",
                        f"- **Proposed Change:** {task.proposedChange}",
                        f"- **Expected Outcome:** {task.expectedOutcome}",
                        f"- **Rollback:** {task.rollbackInstructions}",
                        "",
                    ]
                )

        lines.extend(
            [
                "---",
                "",
                "## 4. Unknown & Unavailable Data Disclosures",
                "",
            ]
        )
        for disc in brief.unknown_and_unavailable_disclosures:
            lines.append(f"- {disc}")

        lines.extend(
            [
                "",
                "---",
                "",
                "## 5. Statutory Ranking Non-Guarantee",
                "",
                f"> [!IMPORTANT]\n> **Ranking Disclaimer:** {brief.ranking_disclaimer}",
                "",
            ]
        )

        return "\n".join(lines)

    def export_pdf(self, brief: ServiceBriefDTO) -> bytes:
        """Exports the consultation brief as binary PDF stream."""
        return generate_brief_pdf(brief)
