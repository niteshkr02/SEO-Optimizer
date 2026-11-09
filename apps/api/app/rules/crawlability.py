"""Crawlability and network transport deterministic audit rules."""

from typing import Any

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


class HttpStatus200Rule(BaseRule):
    """Verifies that the final landing URL responds with HTTP status 200 OK."""

    def __init__(self):
        super().__init__(
            rule_id="http-status-200",
            category=RuleCategory.CRAWLABILITY,
            title="HTTP Status 200 OK",
            description="The requested page must respond with an HTTP 200 OK status code.",
            severity=IssueSeverity.CRITICAL,
            weight=10,
        )

    def evaluate(
        self,
        crawl_result: CrawlResult,
        document: ParsedDocument,
        **kwargs: Any,
    ) -> Finding:
        status = crawl_result.status_code
        state = RuleState.PASS if status == 200 else RuleState.FAIL
        evidence = FindingEvidence(
            observedValue=f"HTTP {status}",
            expectedValue="HTTP 200",
            provenance=ProvenanceCategory.DIRECT_OBSERVATION,
            httpStatusCode=status,
            responseTimeMs=crawl_result.response_time_ms,
        )
        guidance = (
            "Ensure the server returns an HTTP 200 OK status for canonical pages. "
            "Resolve any 4xx client errors or 5xx server errors."
        )
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


class RedirectChainLengthRule(BaseRule):
    """Audits the length and health of the HTTP redirect chain (Model E11)."""

    def __init__(self):
        super().__init__(
            rule_id="redirect-chain-length",
            category=RuleCategory.CRAWLABILITY,
            title="Redirect Chain Length",
            description="The page should not exceed 1 redirect hop before reaching the final URL.",
            severity=IssueSeverity.HIGH,
            weight=8,
        )

    def evaluate(
        self,
        crawl_result: CrawlResult,
        document: ParsedDocument,
        **kwargs: Any,
    ) -> Finding:
        redirect_eval = crawl_result.redirect_evaluation
        total_hops = redirect_eval.total_hops

        evidence = FindingEvidence(
            observedValue=f"{total_hops} redirect hops",
            expectedValue="<= 1 redirect hop",
            provenance=ProvenanceCategory.DIRECT_OBSERVATION,
            contextData={"hops": [h.model_dump() for h in redirect_eval.hops]},
        )

        return Finding(
            ruleId=self.rule_id,
            category=self.category,
            title=self.title,
            description=self.description,
            state=redirect_eval.rule_state,
            severity=redirect_eval.severity,
            weight=self.weight,
            evidence=evidence,
            remediationGuidance=redirect_eval.guidance,
        )


class HttpsEnforcedRule(BaseRule):
    """Ensures that the target URL is served over HTTPS."""

    def __init__(self):
        super().__init__(
            rule_id="https-enforced",
            category=RuleCategory.CRAWLABILITY,
            title="HTTPS Encryption Enforced",
            description="The website must serve content securely over HTTPS.",
            severity=IssueSeverity.HIGH,
            weight=7,
        )

    def evaluate(
        self,
        crawl_result: CrawlResult,
        document: ParsedDocument,
        **kwargs: Any,
    ) -> Finding:
        is_https = crawl_result.final_url.lower().startswith("https://")
        state = RuleState.PASS if is_https else RuleState.FAIL
        observed = "https://" if is_https else "http://"

        evidence = FindingEvidence(
            observedValue=observed,
            expectedValue="https://",
            provenance=ProvenanceCategory.DIRECT_OBSERVATION,
        )
        guidance = "Install an SSL/TLS certificate and configure HTTP to HTTPS 301 redirection."

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


class RobotsMetaIndexableRule(BaseRule):
    """Checks that the <meta name='robots'> tag does not contain 'noindex'."""

    def __init__(self):
        super().__init__(
            rule_id="robots-meta-indexable",
            category=RuleCategory.CRAWLABILITY,
            title="Robots Meta Tag Indexability",
            description="The page must not have a 'noindex' directive in the robots meta tag.",
            severity=IssueSeverity.CRITICAL,
            weight=9,
        )

    def evaluate(
        self,
        crawl_result: CrawlResult,
        document: ParsedDocument,
        **kwargs: Any,
    ) -> Finding:
        directives = document.robots_meta_directives
        has_noindex = "noindex" in directives

        if has_noindex:
            state = RuleState.FAIL
            observed = f"contains noindex ({', '.join(directives)})"
            guidance = "Remove the 'noindex' directive from <meta name='robots'> if this page is intended to rank."
        else:
            state = RuleState.PASS
            observed = (
                f"indexable ({', '.join(directives)})"
                if directives
                else "no restrictive directives"
            )
            guidance = "No action needed. Page is indexable by meta robots directives."

        evidence = FindingEvidence(
            observedValue=observed,
            expectedValue="Indexable (noindex absent)",
            provenance=ProvenanceCategory.DIRECT_OBSERVATION,
            targetElement="head > meta[name='robots']",
        )

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


class XRobotsTagIndexableRule(BaseRule):
    """Checks that the X-Robots-Tag HTTP response header does not block indexation."""

    def __init__(self):
        super().__init__(
            rule_id="x-robots-tag-indexable",
            category=RuleCategory.CRAWLABILITY,
            title="X-Robots-Tag Header Indexability",
            description="The HTTP headers must not contain an X-Robots-Tag with 'noindex'.",
            severity=IssueSeverity.CRITICAL,
            weight=9,
        )

    def evaluate(
        self,
        crawl_result: CrawlResult,
        document: ParsedDocument,
        **kwargs: Any,
    ) -> Finding:
        directives = document.x_robots_tag_directives
        has_noindex = "noindex" in directives

        if has_noindex:
            state = RuleState.FAIL
            observed = f"contains noindex ({', '.join(directives)})"
            guidance = (
                "Remove the 'noindex' directive from the X-Robots-Tag response header."
            )
        else:
            state = RuleState.PASS
            observed = (
                f"indexable ({', '.join(directives)})"
                if directives
                else "header not present"
            )
            guidance = "No action needed. The X-Robots-Tag header does not block search engines."

        evidence = FindingEvidence(
            observedValue=observed,
            expectedValue="Indexable (X-Robots-Tag noindex absent)",
            provenance=ProvenanceCategory.DIRECT_OBSERVATION,
        )

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


class RobotsTxtPresentRule(BaseRule):
    """Checks existence and accessibility of /robots.txt at the origin root."""

    def __init__(self):
        super().__init__(
            rule_id="robots-txt-present",
            category=RuleCategory.CRAWLABILITY,
            title="Robots.txt Presence & Accessibility",
            description="The website should have an accessible /robots.txt file at its origin root.",
            severity=IssueSeverity.MEDIUM,
            weight=6,
        )

    def evaluate(
        self,
        crawl_result: CrawlResult,
        document: ParsedDocument,
        robots_result: Any = None,
        **kwargs: Any,
    ) -> Finding:
        if robots_result is None:
            return Finding(
                ruleId=self.rule_id,
                category=self.category,
                title=self.title,
                description=self.description,
                state=RuleState.UNKNOWN,
                severity=self.severity,
                weight=self.weight,
                evidence=FindingEvidence(
                    observedValue="Robots.txt evaluation was not performed",
                    expectedValue="HTTP 200 on /robots.txt",
                    provenance=ProvenanceCategory.DIRECT_OBSERVATION,
                ),
                remediationGuidance="Verify that /robots.txt is accessible to search engine crawlers.",
            )

        if robots_result.is_present:
            state = RuleState.PASS
            observed = f"HTTP {robots_result.status_code} OK (/robots.txt accessible)"
            guidance = "No action needed. /robots.txt is present and accessible."
        elif robots_result.status_code == 404:
            state = RuleState.FAIL
            observed = f"HTTP {robots_result.status_code} Not Found"
            guidance = "Create a /robots.txt file at the origin root to guide search engine crawlers."
        elif robots_result.error_reason:
            state = RuleState.UNKNOWN
            observed = f"Error: {robots_result.error_reason}"
            guidance = (
                "Resolve network or server issues preventing access to /robots.txt."
            )
        else:
            state = RuleState.FAIL
            observed = f"HTTP {robots_result.status_code}"
            guidance = "Ensure /robots.txt returns an HTTP 200 OK status."

        evidence = FindingEvidence(
            observedValue=observed,
            expectedValue="HTTP 200 on /robots.txt",
            provenance=ProvenanceCategory.DIRECT_OBSERVATION,
            rawSnippet=robots_result.raw_content[:500]
            if robots_result.raw_content
            else None,
            httpStatusCode=robots_result.status_code
            if robots_result.status_code > 0
            else None,
        )

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


class SitemapReferencedRule(BaseRule):
    """Verifies that an XML sitemap is declared in robots.txt, HTTP headers, or root fallback (Model E12)."""

    def __init__(self):
        super().__init__(
            rule_id="sitemap-referenced",
            category=RuleCategory.CRAWLABILITY,
            title="XML Sitemap Referenced & Discovered",
            description="The website should declare an XML sitemap in robots.txt or provide one at /sitemap.xml.",
            severity=IssueSeverity.LOW,
            weight=4,
        )

    def evaluate(
        self,
        crawl_result: CrawlResult,
        document: ParsedDocument,
        sitemap_result: Any = None,
        **kwargs: Any,
    ) -> Finding:
        if sitemap_result is None:
            return Finding(
                ruleId=self.rule_id,
                category=self.category,
                title=self.title,
                description=self.description,
                state=RuleState.UNKNOWN,
                severity=self.severity,
                weight=self.weight,
                evidence=FindingEvidence(
                    observedValue="Sitemap discovery was not performed",
                    expectedValue="XML sitemap declared or accessible",
                    provenance=ProvenanceCategory.DIRECT_OBSERVATION,
                ),
                remediationGuidance="Add a 'Sitemap: ...' directive to robots.txt pointing to your XML sitemap.",
            )

        if sitemap_result.is_sitemap_found:
            state = RuleState.PASS
            observed = (
                f"Sitemap discovered via {sitemap_result.sitemap_source}: "
                f"{sitemap_result.sitemap_url} ({sitemap_result.total_urls_sampled} URLs sampled)"
            )
            guidance = "No action needed. XML sitemap is referenced and discoverable."
        elif (
            sitemap_result.error_reason
            and "timeout" in sitemap_result.error_reason.lower()
        ):
            state = RuleState.UNKNOWN
            observed = f"Error: {sitemap_result.error_reason}"
            guidance = "Ensure sitemap URL does not time out when accessed by search engine crawlers."
        else:
            state = RuleState.FAIL
            observed = "No XML sitemap found in robots.txt directives, Link headers, or /sitemap.xml"
            guidance = "Add a 'Sitemap: https://yourdomain.com/sitemap.xml' directive to robots.txt."

        context = {
            "sitemap_url": sitemap_result.sitemap_url,
            "sitemap_source": sitemap_result.sitemap_source,
            "total_urls_sampled": sitemap_result.total_urls_sampled,
        }
        if (
            sitemap_result.health_result
            and sitemap_result.health_result.sh_score is not None
        ):
            context["sh_score"] = sitemap_result.health_result.sh_score

        evidence = FindingEvidence(
            observedValue=observed,
            expectedValue="XML sitemap declared in robots.txt or accessible at /sitemap.xml",
            provenance=ProvenanceCategory.DIRECT_OBSERVATION,
            contextData=context,
        )

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
