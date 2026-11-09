"""Deterministic verification engine comparing baseline and post-change audits."""

import uuid

from app.contracts.enums import RuleCategory, RuleState
from app.contracts.scan import AuditReportDTO
from app.verification.models import (
    FindingComparisonDTO,
    ScoreDeltaDTO,
    VerificationReportDTO,
    VerificationTransition,
)
from app.verification.resolution import calculate_issue_resolution_rate


def calculate_score_delta(
    baseline_score: float | None,
    post_score: float | None,
) -> ScoreDeltaDTO:
    """Calculates difference (post - baseline) rounded to 2 decimal places."""
    if baseline_score is None or post_score is None:
        return ScoreDeltaDTO(
            baselineScore=baseline_score,
            postChangeScore=post_score,
            delta=None,
        )
    delta = round(post_score - baseline_score, 2)
    return ScoreDeltaDTO(
        baselineScore=baseline_score,
        postChangeScore=post_score,
        delta=delta,
    )


class VerificationEngine:
    """Zero-trust engine comparing baseline audit snapshots with post-deployment scans."""

    def compare_reports(
        self,
        baseline_report: AuditReportDTO,
        post_change_report: AuditReportDTO,
        attempted_rule_ids: list[str] | None = None,
    ) -> VerificationReportDTO:
        """Executes itemized rule comparison and computes Model E33 resolution metrics."""
        baseline_findings_map = {f.ruleId: f for f in baseline_report.findings}
        post_findings_map = {f.ruleId: f for f in post_change_report.findings}

        # If attempted_rule_ids is omitted, default to all baseline failing rules
        if attempted_rule_ids is None:
            attempted_set = {
                f.ruleId for f in baseline_report.findings if f.state == RuleState.FAIL
            }
        else:
            attempted_set = set(attempted_rule_ids)

        all_rule_ids = list(
            dict.fromkeys(
                list(baseline_findings_map.keys()) + list(post_findings_map.keys())
            )
        )

        comparisons: list[FindingComparisonDTO] = []
        resolved_count = 0
        unresolved_count = 0
        regressed_count = 0
        unknown_count = 0
        not_rechecked_count = 0

        for r_id in all_rule_ids:
            base_f = baseline_findings_map.get(r_id)
            post_f = post_findings_map.get(r_id)

            prev_state = base_f.state if base_f else RuleState.NOT_TESTED
            curr_state = post_f.state if post_f else RuleState.NOT_TESTED

            category = (
                post_f.category
                if post_f
                else base_f.category
                if base_f
                else RuleCategory.CRAWLABILITY
            )
            title = post_f.title if post_f else base_f.title if base_f else r_id

            was_attempted = r_id in attempted_set

            # Transition classification
            if curr_state == RuleState.UNKNOWN:
                transition = VerificationTransition.UNKNOWN
                unknown_count += 1
            elif curr_state == RuleState.NOT_TESTED or post_f is None:
                transition = VerificationTransition.NOT_RECHECKED
                not_rechecked_count += 1
            elif prev_state == RuleState.FAIL and curr_state == RuleState.PASS:
                transition = VerificationTransition.RESOLVED
                if was_attempted:
                    resolved_count += 1
            elif prev_state == RuleState.FAIL and curr_state == RuleState.FAIL:
                transition = VerificationTransition.UNRESOLVED
                if was_attempted:
                    unresolved_count += 1
            elif prev_state == RuleState.PASS and curr_state == RuleState.FAIL:
                transition = VerificationTransition.REGRESSED
                regressed_count += 1
            elif prev_state == RuleState.PASS and curr_state == RuleState.PASS:
                transition = VerificationTransition.PERSISTENT_PASS
            else:
                transition = VerificationTransition.NOT_RECHECKED
                not_rechecked_count += 1

            prev_evidence = (
                base_f.evidence.model_dump() if base_f and base_f.evidence else {}
            )
            curr_evidence = (
                post_f.evidence.model_dump() if post_f and post_f.evidence else {}
            )

            comparisons.append(
                FindingComparisonDTO(
                    ruleId=r_id,
                    category=category,
                    title=title,
                    previousState=prev_state,
                    currentState=curr_state,
                    transition=transition,
                    wasAttempted=was_attempted,
                    previousEvidence=prev_evidence,
                    currentEvidence=curr_evidence,
                )
            )

        # Compute Model E33: Issue Resolution Rate (IRR)
        attempted_count = len(attempted_set)
        irr_result = calculate_issue_resolution_rate(
            attempted_count=attempted_count,
            verified_resolved_count=resolved_count,
        )

        # Overall and completeness score deltas
        overall_delta = calculate_score_delta(
            baseline_report.overallScore, post_change_report.overallScore
        )
        completeness_delta = calculate_score_delta(
            baseline_report.completenessScore,
            post_change_report.completenessScore,
        )

        # Category score deltas
        category_deltas: dict[RuleCategory, ScoreDeltaDTO] = {}
        all_categories = {
            RuleCategory.CRAWLABILITY,
            RuleCategory.INDEXABILITY,
            RuleCategory.DOCUMENT,
            RuleCategory.CONTENT,
            RuleCategory.STRUCTURED,
        }
        for cat in all_categories:
            base_cat = baseline_report.categoryScores.get(cat)
            post_cat = post_change_report.categoryScores.get(cat)
            base_score = base_cat.score if base_cat else None
            post_score = post_cat.score if post_cat else None
            category_deltas[cat] = calculate_score_delta(base_score, post_score)

        verification_id = uuid.uuid4().hex[:16]

        return VerificationReportDTO(
            verificationId=verification_id,
            targetUrl=post_change_report.targetUrl,
            baselineScanToken=baseline_report.scanToken,
            postChangeScanToken=post_change_report.scanToken,
            totalAttempted=attempted_count,
            resolvedCount=resolved_count,
            unresolvedCount=unresolved_count,
            regressedCount=regressed_count,
            unknownCount=unknown_count,
            notRecheckedCount=not_rechecked_count,
            issueResolutionRate=irr_result.irr_score,
            overallScoreDelta=overall_delta,
            completenessDelta=completeness_delta,
            categoryDeltas=category_deltas,
            findingComparisons=comparisons,
            rulesetVersion=post_change_report.rulesetVersion,
            scoringModelVersion=post_change_report.scoringModelVersion,
        )

    def export_markdown_report(self, report: VerificationReportDTO) -> str:
        """Exports an audit verification report as GitHub-flavored Markdown."""
        lines: list[str] = []

        lines.append("# SEO Optimizer — Post-Deployment Verification Report")
        lines.append("")
        lines.append(f"**Verification ID:** `{report.verificationId}`  ")
        lines.append(f"**Target URL:** `{report.targetUrl}`  ")
        lines.append(f"**Baseline Scan:** `{report.baselineScanToken}`  ")
        lines.append(f"**Post-Change Scan:** `{report.postChangeScanToken}`  ")
        lines.append(f"**Verified At:** {report.verifiedAt.isoformat()}  ")
        lines.append("")

        lines.append("## 1. Resolution Metrics (Model E33)")
        lines.append("")
        irr_str = (
            f"{report.issueResolutionRate:.1f}%"
            if report.issueResolutionRate is not None
            else "N/A (0 issues attempted)"
        )
        lines.append("| Metric | Count / Value | Description |")
        lines.append("| :--- | :--- | :--- |")
        lines.append(
            f"| **Issue Resolution Rate (IRR)** | **{irr_str}** | Percentage"
            " of attempted issues successfully verified as `PASS` (Model E33) |"
        )
        lines.append(
            f"| **Total Issues Attempted** | {report.totalAttempted} | Baseline"
            " issues targeted for code resolution |"
        )
        lines.append(
            f"| **Verified Resolved** | {report.resolvedCount} | Issues that"
            " transitioned from `FAIL` to `PASS` |"
        )
        lines.append(
            f"| **Unresolved** | {report.unresolvedCount} | Attempted issues"
            " that still evaluate to `FAIL` |"
        )
        lines.append(
            f"| **Regressions** | {report.regressedCount} | Checks that"
            " previously passed but now fail |"
        )
        lines.append(
            f"| **Unknown / Inconclusive** | {report.unknownCount} | Checks"
            " that could not be evaluated definitively |"
        )
        lines.append("")

        lines.append("## 2. Score Deltas Overview")
        lines.append("")
        lines.append(
            r"| Dimension | Baseline Score | Post-Change Score | Delta ($\Delta$) |"
        )
        lines.append("| :--- | :--- | :--- | :--- |")

        def _fmt(val: float | None) -> str:
            return f"{val:.1f}" if val is not None else "N/A"

        def _fmt_delta(val: float | None) -> str:
            if val is None:
                return "N/A"
            prefix = "+" if val > 0 else ""
            return f"{prefix}{val:.1f}"

        lines.append(
            f"| **Overall SEO Health Score** |"
            f" {_fmt(report.overallScoreDelta.baselineScore)} |"
            f" {_fmt(report.overallScoreDelta.postChangeScore)} |"
            f" **{_fmt_delta(report.overallScoreDelta.delta)}** |"
        )
        lines.append(
            f"| **Report Completeness Index** |"
            f" {_fmt(report.completenessDelta.baselineScore)}% |"
            f" {_fmt(report.completenessDelta.postChangeScore)}% |"
            f" {_fmt_delta(report.completenessDelta.delta)}% |"
        )

        for cat, delta_dto in report.categoryDeltas.items():
            cat_name = cat.value if hasattr(cat, "value") else str(cat)
            lines.append(
                f"| Category: `{cat_name}` | {_fmt(delta_dto.baselineScore)} |"
                f" {_fmt(delta_dto.postChangeScore)} |"
                f" {_fmt_delta(delta_dto.delta)} |"
            )
        lines.append("")

        lines.append("## 3. Itemized Rule Transitions")
        lines.append("")
        lines.append(
            "| Rule ID | Category | Previous State | Current State |"
            " Transition | Attempted? |"
        )
        lines.append("| :--- | :--- | :--- | :--- | :--- | :--- |")
        for comp in report.findingComparisons:
            attempted_mark = "Yes" if comp.wasAttempted else "No"
            cat_str = (
                comp.category.value
                if hasattr(comp.category, "value")
                else str(comp.category)
            )
            prev_str = (
                comp.previousState.value
                if hasattr(comp.previousState, "value")
                else str(comp.previousState)
            )
            curr_str = (
                comp.currentState.value
                if hasattr(comp.currentState, "value")
                else str(comp.currentState)
            )
            trans_str = (
                comp.transition.value
                if hasattr(comp.transition, "value")
                else str(comp.transition)
            )
            lines.append(
                f"| `{comp.ruleId}` | {cat_str} | `{prev_str}` |"
                f" `{curr_str}` | **{trans_str}** |"
                f" {attempted_mark} |"
            )

        lines.append("")

        lines.append("---")
        lines.append(
            "*Generated deterministically by SEO Optimizer Verification Engine"
            " (Zero-Trust Model).* "
            "Never treat an untested check as resolved."
        )

        return "\n".join(lines)


default_verification_engine = VerificationEngine()
