"""Asset and media optimization deterministic audit rules."""

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


class ImageAltCoverageRule(BaseRule):
    """Audits image elements for non-empty alt attributes (Model E10)."""

    def __init__(self):
        super().__init__(
            rule_id="image-alt-coverage",
            category=RuleCategory.CONTENT,
            title="Image Alt Attribute Coverage",
            description="All eligible non-decorative images must declare a meaningful non-empty alt attribute.",
            severity=IssueSeverity.HIGH,
            weight=7,
        )

    def evaluate(self, crawl_result: CrawlResult, document: ParsedDocument) -> Finding:
        images = document.images

        # Eligible non-decorative images
        eligible_images = [img for img in images if not img.is_decorative]
        total_eligible = len(eligible_images)

        if total_eligible == 0:
            return Finding(
                ruleId=self.rule_id,
                category=self.category,
                title=self.title,
                description=self.description,
                state=RuleState.NOT_APPLICABLE,
                severity=self.severity,
                weight=self.weight,
                evidence=FindingEvidence(
                    observedValue=f"{len(images)} images (0 eligible non-decorative)",
                    expectedValue="N/A",
                    provenance=ProvenanceCategory.DIRECT_OBSERVATION,
                ),
                remediationGuidance="No non-decorative images found on the page.",
            )

        with_alt = [
            img for img in eligible_images if img.alt and len(img.alt.strip()) > 0
        ]
        missing_alt = [
            img for img in eligible_images if not img.alt or len(img.alt.strip()) == 0
        ]

        iac_percentage = (len(with_alt) / total_eligible) * 100.0
        is_pass = len(missing_alt) == 0

        state = RuleState.PASS if is_pass else RuleState.FAIL
        observed = f"{len(with_alt)}/{total_eligible} images ({iac_percentage:.1f}%) have alt text"
        guidance = (
            "All meaningful images have descriptive alt attributes."
            if is_pass
            else f"Add descriptive alt attributes to {len(missing_alt)} images."
        )

        snippet = missing_alt[0].raw_snippet if missing_alt else None

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
                expectedValue="100% of eligible images with non-empty alt",
                provenance=ProvenanceCategory.DIRECT_OBSERVATION,
                targetElement="img",
                rawSnippet=snippet,
                contextData={
                    "total_images": len(images),
                    "eligible_images": total_eligible,
                    "with_alt_count": len(with_alt),
                    "missing_alt_count": len(missing_alt),
                },
            ),
            remediationGuidance=guidance,
        )


class ImageDimensionsRule(BaseRule):
    """Checks that images declare explicit width and height attributes to mitigate CLS."""

    def __init__(self):
        super().__init__(
            rule_id="image-dimensions",
            category=RuleCategory.CONTENT,
            title="Image Explicit Dimensions",
            description="Images should specify width and height attributes to prevent layout shift during loading.",
            severity=IssueSeverity.LOW,
            weight=4,
        )

    def evaluate(self, crawl_result: CrawlResult, document: ParsedDocument) -> Finding:
        images = document.images
        if not images:
            return Finding(
                ruleId=self.rule_id,
                category=self.category,
                title=self.title,
                description=self.description,
                state=RuleState.NOT_APPLICABLE,
                severity=self.severity,
                weight=self.weight,
                evidence=FindingEvidence(
                    observedValue="0 images",
                    expectedValue="N/A",
                    provenance=ProvenanceCategory.DIRECT_OBSERVATION,
                ),
                remediationGuidance="No images on page.",
            )

        with_dims = [img for img in images if img.width and img.height]
        missing_dims = [img for img in images if not (img.width and img.height)]

        is_pass = len(missing_dims) == 0
        state = RuleState.PASS if is_pass else RuleState.FAIL
        observed = f"{len(with_dims)}/{len(images)} images have explicit dimensions"
        guidance = (
            "Images have explicit dimensions."
            if is_pass
            else f"Add width and height attributes to {len(missing_dims)} image(s) to avoid layout shifts."
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
                expectedValue="All images declare width & height",
                provenance=ProvenanceCategory.DIRECT_OBSERVATION,
                targetElement="img",
                rawSnippet=missing_dims[0].raw_snippet if missing_dims else None,
            ),
            remediationGuidance=guidance,
        )
