"""Structured data and Schema.org deterministic audit rules."""

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


class JsonLdValidSyntaxRule(BaseRule):
    """Validates that all JSON-LD script blocks are valid RFC 8259 JSON (Model E14)."""

    def __init__(self):
        super().__init__(
            rule_id="jsonld-valid-syntax",
            category=RuleCategory.STRUCTURED,
            title="JSON-LD Syntax Validity",
            description="All <script type='application/ld+json'> blocks must parse as valid RFC 8259 JSON.",
            severity=IssueSeverity.HIGH,
            weight=8,
        )

    def evaluate(self, crawl_result: CrawlResult, document: ParsedDocument) -> Finding:
        report = document.jsonld_report

        if report.detected_blocks_count == 0:
            return Finding(
                ruleId=self.rule_id,
                category=self.category,
                title=self.title,
                description=self.description,
                state=RuleState.NOT_APPLICABLE,
                severity=self.severity,
                weight=self.weight,
                evidence=FindingEvidence(
                    observedValue="0 JSON-LD blocks detected",
                    expectedValue="N/A",
                    provenance=ProvenanceCategory.DIRECT_OBSERVATION,
                ),
                remediationGuidance="Consider adding JSON-LD structured data to enrich search results.",
            )

        is_valid = report.status == "SYNTAX_VALID"
        state = RuleState.PASS if is_valid else RuleState.FAIL
        observed = f"{report.valid_blocks_count}/{report.detected_blocks_count} blocks valid (JVR: {report.jvr_score}%)"
        guidance = (
            "All JSON-LD blocks parse cleanly."
            if is_valid
            else "Fix JSON syntax errors in your application/ld+json scripts."
        )

        invalid_blocks = [b for b in report.blocks if not b.is_valid_syntax]
        snippet = invalid_blocks[0].raw_text if invalid_blocks else None

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
                expectedValue="100% valid JSON syntax",
                provenance=ProvenanceCategory.DIRECT_OBSERVATION,
                targetElement="script[type='application/ld+json']",
                rawSnippet=snippet,
                contextData={
                    "detected_count": report.detected_blocks_count,
                    "valid_count": report.valid_blocks_count,
                    "jvr_score": report.jvr_score,
                },
            ),
            remediationGuidance=guidance,
        )


class JsonLdSchemaTypeRule(BaseRule):
    """Verifies that detected JSON-LD blocks declare recognized Schema.org types."""

    def __init__(self):
        super().__init__(
            rule_id="jsonld-schema-type",
            category=RuleCategory.STRUCTURED,
            title="Recognized Schema.org Types",
            description="Structured data should declare recognized Schema.org entity types.",
            severity=IssueSeverity.MEDIUM,
            weight=5,
        )

    def evaluate(self, crawl_result: CrawlResult, document: ParsedDocument) -> Finding:
        report = document.jsonld_report

        if report.detected_blocks_count == 0:
            return Finding(
                ruleId=self.rule_id,
                category=self.category,
                title=self.title,
                description=self.description,
                state=RuleState.NOT_APPLICABLE,
                severity=self.severity,
                weight=self.weight,
                evidence=FindingEvidence(
                    observedValue="No structured data",
                    expectedValue="N/A",
                    provenance=ProvenanceCategory.DIRECT_OBSERVATION,
                ),
                remediationGuidance="Add Schema.org structured data.",
            )

        types = report.detected_schema_types
        has_types = len(types) > 0

        state = RuleState.PASS if has_types else RuleState.FAIL
        observed = f"Types: {', '.join(types)}" if has_types else "No @type declared"
        guidance = (
            "Recognized Schema.org types declared."
            if has_types
            else "Declare an '@type' in your JSON-LD block (e.g., Organization, Article, WebSite)."
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
                expectedValue="At least 1 valid Schema.org @type",
                provenance=ProvenanceCategory.DIRECT_OBSERVATION,
                targetElement="script[type='application/ld+json']",
            ),
            remediationGuidance=guidance,
        )
