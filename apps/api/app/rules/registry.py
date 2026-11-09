"""Deterministic audit rules registry."""

from typing import Any

from app.contracts.finding import Finding
from app.crawler.client import CrawlResult
from app.parsers.html import ParsedDocument
from app.rules.assets import ImageAltCoverageRule, ImageDimensionsRule
from app.rules.base import BaseRule
from app.rules.crawlability import (
    HttpsEnforcedRule,
    HttpStatus200Rule,
    RedirectChainLengthRule,
    RobotsMetaIndexableRule,
    RobotsTxtPresentRule,
    SitemapReferencedRule,
    XRobotsTagIndexableRule,
)
from app.rules.indexability import (
    CanonicalFormatRule,
    CanonicalPresenceRule,
    MetaDescriptionLengthRule,
    MetaDescriptionPresenceRule,
    TitleLengthRule,
    TitlePresenceRule,
)
from app.rules.structure import H1PresenceRule, H1SingleRule, HeadingHierarchyRule
from app.rules.structured_data import JsonLdSchemaTypeRule, JsonLdValidSyntaxRule


class RuleRegistry:
    """Registry coordinating all active deterministic audit rules."""

    def __init__(self):
        self._rules: dict[str, BaseRule] = {}
        self._register_default_rules()

    def register(self, rule: BaseRule) -> None:
        """Registers a rule instance."""
        self._rules[rule.rule_id] = rule

    def get_rule(self, rule_id: str) -> BaseRule:
        """Retrieves a rule by its unique ID."""
        return self._rules[rule_id]

    def all_rules(self) -> list[BaseRule]:
        """Returns all registered rules in order."""
        return list(self._rules.values())

    def evaluate_all(
        self,
        crawl_result: CrawlResult,
        document: ParsedDocument,
        robots_result: Any = None,
        sitemap_result: Any = None,
    ) -> list[Finding]:
        """Evaluates all registered rules against the crawl result, document snapshot, and auxiliary data."""
        findings: list[Finding] = []
        for rule in self._rules.values():
            try:
                finding = rule.evaluate(
                    crawl_result=crawl_result,
                    document=document,
                    robots_result=robots_result,
                    sitemap_result=sitemap_result,
                )
            except TypeError:
                finding = rule.evaluate(crawl_result, document)
            findings.append(finding)
        return findings

    def _register_default_rules(self) -> None:
        """Registers the 20 Phase 1 deterministic audit rules."""
        # Crawlability & Network (7 rules)
        self.register(HttpStatus200Rule())
        self.register(RedirectChainLengthRule())
        self.register(HttpsEnforcedRule())
        self.register(RobotsMetaIndexableRule())
        self.register(XRobotsTagIndexableRule())
        self.register(RobotsTxtPresentRule())
        self.register(SitemapReferencedRule())

        # Indexability & Meta (6 rules)
        self.register(TitlePresenceRule())
        self.register(TitleLengthRule())
        self.register(MetaDescriptionPresenceRule())
        self.register(MetaDescriptionLengthRule())
        self.register(CanonicalPresenceRule())
        self.register(CanonicalFormatRule())

        # Document Structure (3 rules)
        self.register(H1PresenceRule())
        self.register(H1SingleRule())
        self.register(HeadingHierarchyRule())

        # Assets & Content (2 rules)
        self.register(ImageAltCoverageRule())
        self.register(ImageDimensionsRule())

        # Structured Data (2 rules)
        self.register(JsonLdValidSyntaxRule())
        self.register(JsonLdSchemaTypeRule())


default_registry = RuleRegistry()
