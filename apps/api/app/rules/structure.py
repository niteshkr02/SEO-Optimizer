"""Document structure and heading hierarchy deterministic audit rules."""

from app.contracts.enums import (
    IssueSeverity,
    ProvenanceCategory,
    RuleCategory,
    RuleState,
)
from app.contracts.evidence import FindingEvidence
from app.contracts.finding import Finding
from app.crawler.client import CrawlResult
from app.parsers.html import ParsedDocument
from app.rules.base import BaseRule


class H1PresenceRule(BaseRule):
    """Verifies that the page contains at least one <h1> heading."""

    def __init__(self):
        super().__init__(
            rule_id="h1-presence",
            category=RuleCategory.DOCUMENT,
            title="H1 Heading Presence",
            description="The page must have at least one main <h1> heading.",
            severity=IssueSeverity.HIGH,
            weight=8,
        )

    def evaluate(self, crawl_result: CrawlResult, document: ParsedDocument) -> Finding:
        h1_tags = [h for h in document.headings if h.level == 1]
        has_h1 = len(h1_tags) >= 1

        state = RuleState.PASS if has_h1 else RuleState.FAIL
        observed = f"{len(h1_tags)} H1 tag(s)" if has_h1 else "0 H1 tags"
        guidance = (
            "H1 heading is present."
            if has_h1
            else "Add an <h1> heading describing the page topic."
        )

        return Finding(
            ruleId=self.rule_id,
            category=self.category,
            title=self.title,
            description=self.description,
            state=state,
            severity=self.severity,
            weight=self.weight,
            evidence=FindingEvidence(
                observedValue=observed,
                expectedValue=">= 1 H1 heading",
                provenance=ProvenanceCategory.DIRECT_OBSERVATION,
                targetElement="h1",
            ),
            remediationGuidance=guidance,
        )


class H1SingleRule(BaseRule):
    """Verifies that the page has exactly one <h1> heading (no multiple H1s)."""

    def __init__(self):
        super().__init__(
            rule_id="h1-single",
            category=RuleCategory.DOCUMENT,
            title="Single H1 Heading",
            description="The page should declare exactly one <h1> heading to establish clear document topic hierarchy.",
            severity=IssueSeverity.MEDIUM,
            weight=5,
        )

    def evaluate(self, crawl_result: CrawlResult, document: ParsedDocument) -> Finding:
        h1_count = len([h for h in document.headings if h.level == 1])

        if h1_count == 1:
            state = RuleState.PASS
            guidance = "Exactly one H1 heading found."
        elif h1_count == 0:
            state = RuleState.FAIL
            guidance = "Page is missing an H1 heading."
        else:
            state = RuleState.FAIL
            guidance = f"Multiple H1 headings detected ({h1_count}). Demote secondary headings to <h2>."

        return Finding(
            ruleId=self.rule_id,
            category=self.category,
            title=self.title,
            description=self.description,
            state=state,
            severity=self.severity,
            weight=self.weight,
            evidence=FindingEvidence(
                observedValue=f"{h1_count} H1 tags",
                expectedValue="Exactly 1 H1 tag",
                provenance=ProvenanceCategory.DIRECT_OBSERVATION,
                targetElement="h1",
            ),
            remediationGuidance=guidance,
        )


class HeadingHierarchyRule(BaseRule):
    """Checks that heading levels are not skipped (e.g. H2 directly to H4)."""

    def __init__(self):
        super().__init__(
            rule_id="heading-hierarchy",
            category=RuleCategory.DOCUMENT,
            title="Logical Heading Hierarchy",
            description="Heading levels should not be skipped (e.g., jumping from H2 directly to H4).",
            severity=IssueSeverity.LOW,
            weight=4,
        )

    def evaluate(self, crawl_result: CrawlResult, document: ParsedDocument) -> Finding:
        headings = document.headings

        if len(headings) <= 1:
            return Finding(
                ruleId=self.rule_id,
                category=self.category,
                title=self.title,
                description=self.description,
                state=RuleState.NOT_APPLICABLE,
                severity=self.severity,
                weight=self.weight,
                evidence=FindingEvidence(
                    observedValue=f"{len(headings)} heading(s)",
                    expectedValue="Structured heading tree",
                    provenance=ProvenanceCategory.DIRECT_OBSERVATION,
                ),
                remediationGuidance="Add structured sub-headings to organize content.",
            )

        skipped_transitions: list[str] = []
        prev_level = headings[0].level

        for h in headings[1:]:
            # If heading level jumps by more than 1 (e.g. H1 to H3, or H2 to H4)
            if h.level > prev_level + 1:
                skipped_transitions.append(
                    f"H{prev_level} -> H{h.level} ('{h.text[:30]}')"
                )
            prev_level = h.level

        is_valid = len(skipped_transitions) == 0
        state = RuleState.PASS if is_valid else RuleState.FAIL
        observed = (
            "No skipped levels"
            if is_valid
            else f"Skipped: {', '.join(skipped_transitions[:3])}"
        )
        guidance = (
            "Heading levels follow a logical hierarchy."
            if is_valid
            else "Fix skipped heading levels to ensure an accessible document outline."
        )

        return Finding(
            ruleId=self.rule_id,
            category=self.category,
            title=self.title,
            description=self.description,
            state=state,
            severity=self.severity,
            weight=self.weight,
            evidence=FindingEvidence(
                observedValue=observed,
                expectedValue="Sequential heading hierarchy",
                provenance=ProvenanceCategory.DIRECT_OBSERVATION,
            ),
            remediationGuidance=guidance,
        )
