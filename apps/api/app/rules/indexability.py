"""Indexability and document metadata deterministic audit rules."""

import urllib.parse

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


class TitlePresenceRule(BaseRule):
    """Validates the presence of a non-empty <title> tag."""

    def __init__(self):
        super().__init__(
            rule_id="title-presence",
            category=RuleCategory.INDEXABILITY,
            title="Page Title Tag Presence",
            description="Every page must declare a non-empty <title> tag within the <head>.",
            severity=IssueSeverity.HIGH,
            weight=8,
        )

    def evaluate(self, crawl_result: CrawlResult, document: ParsedDocument) -> Finding:
        title = document.title_text
        has_title = title is not None and len(title.strip()) > 0

        state = RuleState.PASS if has_title else RuleState.FAIL
        observed = title if has_title else "Missing or empty"

        evidence = FindingEvidence(
            observedValue=observed,
            expectedValue="Non-empty <title> tag",
            provenance=ProvenanceCategory.DIRECT_OBSERVATION,
            targetElement="head > title",
            rawSnippet=document.title_raw_snippet,
        )
        guidance = "Add a unique, descriptive <title> tag inside the <head> element."

        return Finding(
            ruleId=self.rule_id,
            category=self.category,
            title=self.title,
            description=self.description,
            state=state,
            severity=self.severity,
            weight=self.weight,
            evidence=evidence,
            remediationGuidance=guidance,
        )


class TitleLengthRule(BaseRule):
    """Verifies that the page title length is optimal (30-60 characters)."""

    def __init__(self):
        super().__init__(
            rule_id="title-length",
            category=RuleCategory.INDEXABILITY,
            title="Page Title Length Optimization",
            description="The page title should ideally be between 30 and 60 characters to avoid SERP truncation.",
            severity=IssueSeverity.MEDIUM,
            weight=5,
        )

    def evaluate(self, crawl_result: CrawlResult, document: ParsedDocument) -> Finding:
        length = document.title_char_count

        if length == 0:
            return Finding(
                ruleId=self.rule_id,
                category=self.category,
                title=self.title,
                description=self.description,
                state=RuleState.FAIL,
                severity=self.severity,
                weight=self.weight,
                evidence=FindingEvidence(
                    observedValue="0 characters",
                    expectedValue="30-60 characters",
                    provenance=ProvenanceCategory.DIRECT_OBSERVATION,
                    targetElement="head > title",
                ),
                remediationGuidance="Add a title tag between 30 and 60 characters.",
            )

        is_optimal = 30 <= length <= 60
        state = RuleState.PASS if is_optimal else RuleState.FAIL

        if length < 30:
            guidance = f"The title is {length} characters (too short). Expand to at least 30 characters."
        elif length > 60:
            guidance = f"The title is {length} characters (too long). Shorten to 60 characters to prevent truncation."
        else:
            guidance = "Title length is optimal."

        return Finding(
            ruleId=self.rule_id,
            category=self.category,
            title=self.title,
            description=self.description,
            state=state,
            severity=self.severity,
            weight=self.weight,
            evidence=FindingEvidence(
                observedValue=f"{length} characters ({document.title_text})",
                expectedValue="30-60 characters",
                provenance=ProvenanceCategory.DIRECT_OBSERVATION,
                targetElement="head > title",
                rawSnippet=document.title_raw_snippet,
            ),
            remediationGuidance=guidance,
        )


class MetaDescriptionPresenceRule(BaseRule):
    """Validates the presence of a non-empty meta description tag."""

    def __init__(self):
        super().__init__(
            rule_id="meta-description-presence",
            category=RuleCategory.INDEXABILITY,
            title="Meta Description Presence",
            description="The page should include a descriptive meta description tag.",
            severity=IssueSeverity.HIGH,
            weight=7,
        )

    def evaluate(self, crawl_result: CrawlResult, document: ParsedDocument) -> Finding:
        desc = document.meta_description_text
        has_desc = desc is not None and len(desc.strip()) > 0

        state = RuleState.PASS if has_desc else RuleState.FAIL
        observed = desc if has_desc else "Missing or empty"

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
                expectedValue="Non-empty meta description",
                provenance=ProvenanceCategory.DIRECT_OBSERVATION,
                targetElement="head > meta[name='description']",
                rawSnippet=document.meta_description_raw_snippet,
            ),
            remediationGuidance="Add a compelling, unique <meta name='description'> summarizing the page.",
        )


class MetaDescriptionLengthRule(BaseRule):
    """Checks that the meta description length is optimal (120-160 characters)."""

    def __init__(self):
        super().__init__(
            rule_id="meta-description-length",
            category=RuleCategory.INDEXABILITY,
            title="Meta Description Length Optimization",
            description="The meta description should be between 120 and 160 characters.",
            severity=IssueSeverity.LOW,
            weight=4,
        )

    def evaluate(self, crawl_result: CrawlResult, document: ParsedDocument) -> Finding:
        length = document.meta_description_char_count

        if length == 0:
            return Finding(
                ruleId=self.rule_id,
                category=self.category,
                title=self.title,
                description=self.description,
                state=RuleState.NOT_APPLICABLE,
                severity=self.severity,
                weight=self.weight,
                evidence=FindingEvidence(
                    observedValue="0 characters",
                    expectedValue="120-160 characters",
                    provenance=ProvenanceCategory.DIRECT_OBSERVATION,
                ),
                remediationGuidance="Add a meta description first.",
            )

        is_optimal = 120 <= length <= 160
        state = RuleState.PASS if is_optimal else RuleState.FAIL
        guidance = (
            "Meta description length is optimal."
            if is_optimal
            else f"Length is {length} characters. Adjust to 120-160 characters."
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
                observedValue=f"{length} characters",
                expectedValue="120-160 characters",
                provenance=ProvenanceCategory.DIRECT_OBSERVATION,
                rawSnippet=document.meta_description_raw_snippet,
            ),
            remediationGuidance=guidance,
        )


class CanonicalPresenceRule(BaseRule):
    """Verifies that a canonical link tag is declared."""

    def __init__(self):
        super().__init__(
            rule_id="canonical-presence",
            category=RuleCategory.INDEXABILITY,
            title="Canonical Tag Declared",
            description="The page should declare a canonical URL via <link rel='canonical'>.",
            severity=IssueSeverity.HIGH,
            weight=8,
        )

    def evaluate(self, crawl_result: CrawlResult, document: ParsedDocument) -> Finding:
        canonical = document.canonical_url
        has_canon = canonical is not None and len(canonical.strip()) > 0

        state = RuleState.PASS if has_canon else RuleState.FAIL
        observed = canonical if has_canon else "Missing"

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
                expectedValue="Canonical link tag present",
                provenance=ProvenanceCategory.DIRECT_OBSERVATION,
                targetElement="head > link[rel='canonical']",
                rawSnippet=document.canonical_raw_snippet,
            ),
            remediationGuidance="Add a <link rel='canonical' href='...'> pointing to the preferred version of this URL.",
        )


class CanonicalFormatRule(BaseRule):
    """Verifies that the canonical URL is an absolute URL matching the host protocol."""

    def __init__(self):
        super().__init__(
            rule_id="canonical-format",
            category=RuleCategory.INDEXABILITY,
            title="Canonical URL Absolute Format",
            description="The canonical URL must be an absolute URL including protocol and host.",
            severity=IssueSeverity.HIGH,
            weight=7,
        )

    def evaluate(self, crawl_result: CrawlResult, document: ParsedDocument) -> Finding:
        canonical = document.canonical_url

        if not canonical:
            return Finding(
                ruleId=self.rule_id,
                category=self.category,
                title=self.title,
                description=self.description,
                state=RuleState.NOT_APPLICABLE,
                severity=self.severity,
                weight=self.weight,
                evidence=FindingEvidence(
                    observedValue="No canonical tag",
                    expectedValue="Absolute canonical URL",
                    provenance=ProvenanceCategory.DIRECT_OBSERVATION,
                ),
                remediationGuidance="Add a canonical tag first.",
            )

        parsed = urllib.parse.urlsplit(canonical)
        is_absolute = bool(parsed.scheme and parsed.netloc)

        state = RuleState.PASS if is_absolute else RuleState.FAIL
        guidance = (
            "Canonical format is valid."
            if is_absolute
            else "Canonical is a relative path. Change to a full absolute URL."
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
                observedValue=canonical,
                expectedValue="Absolute URL with scheme and host",
                provenance=ProvenanceCategory.DIRECT_OBSERVATION,
                rawSnippet=document.canonical_raw_snippet,
            ),
            remediationGuidance=guidance,
        )
