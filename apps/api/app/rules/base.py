"""Abstract base class for all deterministic SEO audit rules."""

from abc import ABC, abstractmethod
from typing import Any

from app.contracts.enums import IssueSeverity, RuleCategory
from app.contracts.finding import Finding
from app.crawler.client import CrawlResult
from app.parsers.html import ParsedDocument


class BaseRule(ABC):
    """Abstract base class for pure deterministic audit rules."""

    def __init__(
        self,
        rule_id: str,
        category: RuleCategory,
        title: str,
        description: str,
        severity: IssueSeverity,
        weight: int = 5,
    ):
        self.rule_id = rule_id
        self.category = category
        self.title = title
        self.description = description
        self.severity = severity
        self.weight = weight

    @abstractmethod
    def evaluate(
        self,
        crawl_result: CrawlResult,
        document: ParsedDocument,
        **kwargs: Any,
    ) -> Finding:
        """Evaluates the target crawl and document snapshot, returning an immutable Finding."""
