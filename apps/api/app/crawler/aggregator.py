"""Deterministic site-wide metric and issue aggregation engine for multi-page crawls.

Adheres strictly to docs/MATHEMATICAL_MODEL_CATALOG.md:
- E1-E5 score preservation per page.
- Unweighted arithmetic mean across successfully audited page sets.
- Strict denominator zero safety (returns None / NULL on empty sets, never fabricated zeros).
- Deduplication of site-wide issues across pages to prevent diagnostic inflation.
"""

from app.contracts.crawl import (
    CrawlPageDTO,
    CrawlPageStatus,
    SiteAggregateReportDTO,
    SiteIssueSummaryDTO,
)
from app.contracts.enums import IssueSeverity, RuleCategory, RuleState
from app.contracts.finding import Finding
from app.contracts.scan import CategoryScoreDTO

SEVERITY_ORDER = {
    IssueSeverity.CRITICAL: 5,
    IssueSeverity.HIGH: 4,
    IssueSeverity.MEDIUM: 3,
    IssueSeverity.LOW: 2,
    IssueSeverity.INFO: 1,
}


def build_site_aggregate_report(
    job_id: str,
    seed_url: str,
    base_domain: str,
    pages: list[CrawlPageDTO],
    page_findings_map: dict[str, list[Finding]],
    page_category_scores_map: dict[str, dict[RuleCategory, CategoryScoreDTO]],
) -> SiteAggregateReportDTO:
    """Computes pure deterministic site-wide score averages and deduplicated issue summaries."""
    # Only analyze successfully crawled pages
    crawled_pages = [p for p in pages if p.status == CrawlPageStatus.CRAWLED]
    total_crawled = len(crawled_pages)

    if total_crawled == 0:
        return SiteAggregateReportDTO(
            jobId=job_id,
            seedUrl=seed_url,
            baseDomain=base_domain,
            overallScore=None,
            completenessScore=None,
            categoryScores={},
            totalPagesAnalyzed=0,
            totalIssuesIdentified=0,
            uniqueIssues=[],
            crawledPages=pages,
        )

    # 1. Site-wide Overall Health Score (unweighted mean of page overall scores)
    page_overall_scores = [p.overall_score for p in crawled_pages if p.overall_score is not None]
    site_overall_score: float | None = (
        round(sum(page_overall_scores) / len(page_overall_scores), 2)
        if page_overall_scores
        else None
    )

    # 2. Site-wide Completeness Score
    page_completeness_scores = [p.completeness_score for p in crawled_pages if p.completeness_score is not None]
    site_completeness_score: float | None = (
        round(sum(page_completeness_scores) / len(page_completeness_scores), 2)
        if page_completeness_scores
        else None
    )

    # 3. Site-wide Category Health Scores
    category_scores_accumulator: dict[RuleCategory, list[float]] = {}
    category_completeness_accumulator: dict[RuleCategory, list[float]] = {}
    category_applicable_checks: dict[RuleCategory, int] = {}
    category_evaluated_checks: dict[RuleCategory, int] = {}

    for page in crawled_pages:
        cat_map = page_category_scores_map.get(page.page_id, {})
        for cat, c_dto in cat_map.items():
            if c_dto.score is not None:
                category_scores_accumulator.setdefault(cat, []).append(c_dto.score)
            if c_dto.completeness is not None:
                category_completeness_accumulator.setdefault(cat, []).append(c_dto.completeness)
            app_val = getattr(c_dto, "applicableChecks", getattr(c_dto, "applicable_checks", 0))
            eval_val = getattr(c_dto, "evaluatedChecks", getattr(c_dto, "evaluated_checks", 0))
            category_applicable_checks[cat] = max(
                category_applicable_checks.get(cat, 0), app_val
            )
            category_evaluated_checks[cat] = max(
                category_evaluated_checks.get(cat, 0), eval_val
            )

    site_category_scores: dict[RuleCategory, CategoryScoreDTO] = {}
    for cat, scores in category_scores_accumulator.items():
        avg_score = round(sum(scores) / len(scores), 2) if scores else None
        comp_scores = category_completeness_accumulator.get(cat, [])
        avg_comp = round(sum(comp_scores) / len(comp_scores), 2) if comp_scores else None

        site_category_scores[cat] = CategoryScoreDTO(
            category=cat,
            score=avg_score,
            completeness=avg_comp,
            applicableChecks=category_applicable_checks.get(cat, 0),
            evaluatedChecks=category_evaluated_checks.get(cat, 0),
        )

    # 4. Issue Rollup & Deduplication
    # rule_id -> { "findings": [(page, finding)], "category", "severity", "title", "guidance" }
    rule_occurrences: dict[str, dict] = {}
    total_findings_count = 0

    for page in crawled_pages:
        findings = page_findings_map.get(page.page_id, [])
        for f in findings:
            if f.state == RuleState.FAIL:
                total_findings_count += 1
                entry = rule_occurrences.setdefault(
                    f.ruleId,
                    {
                        "rule_id": f.ruleId,
                        "category": f.category,
                        "severity": f.severity,
                        "title": f.title,
                        "guidance": f.remediationGuidance,
                        "pages": [],
                        "evidence_list": [],
                    },
                )
                if page.url not in entry["pages"]:
                    entry["pages"].append(page.url)
                    entry["evidence_list"].append(
                        {
                            "url": page.url,
                            "observedValue": f.evidence.observedValue if hasattr(f.evidence, "observedValue") else str(f.evidence),
                            "expectedValue": f.evidence.expectedValue if hasattr(f.evidence, "expectedValue") else "",
                        }
                    )

    # Build unique issues list
    unique_issues: list[SiteIssueSummaryDTO] = []
    for rule_id, data in rule_occurrences.items():
        failing_count = len(data["pages"])
        impact_pct = round((failing_count / total_crawled) * 100.0, 2)
        unique_issues.append(
            SiteIssueSummaryDTO(
                ruleId=rule_id,
                category=data["category"],
                severity=data["severity"],
                title=data["title"],
                failingPagesCount=failing_count,
                totalPagesAudited=total_crawled,
                impactPercentage=impact_pct,
                sampleUrls=data["pages"][:5],  # Top 5 sample pages
                sampleEvidence=data["evidence_list"][:5],
                remediationGuidance=data["guidance"],
            )
        )

    # Sort unique issues by severity (CRITICAL first) then by failing pages count descending
    unique_issues.sort(
        key=lambda item: (
            SEVERITY_ORDER.get(item.severity, 0),
            item.failing_pages_count,
        ),
        reverse=True,
    )

    return SiteAggregateReportDTO(
        jobId=job_id,
        seedUrl=seed_url,
        baseDomain=base_domain,
        overallScore=site_overall_score,
        completenessScore=site_completeness_score,
        categoryScores=site_category_scores,
        totalPagesAnalyzed=total_crawled,
        totalIssuesIdentified=total_findings_count,
        uniqueIssues=unique_issues,
        crawledPages=pages,
    )
