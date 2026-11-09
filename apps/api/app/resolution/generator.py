"""Deterministic resolution plan and code patch proposal generator."""

import difflib
import hashlib
import uuid
from typing import Any

from app.contracts.enums import (
    ProvenanceCategory,
    RuleState,
)
from app.contracts.finding import Finding
from app.contracts.scan import AuditReportDTO
from app.resolution.models import (
    CodePatchProposal,
    ResolutionActionType,
    ResolutionPlanDTO,
    ResolutionTask,
)
from app.resolution.priority import calculate_resolution_priority
from app.resolution.triage import calculate_root_cause_triage

# Standard site-wide rules affecting entire domain / origin
SITE_WIDE_RULES = {
    "http-status-200",
    "redirect-chain-length",
    "https-enforced",
    "robots-txt-present",
    "sitemap-referenced",
    "x-robots-tag-indexable",
}


def create_unified_diff(
    before_snippet: str,
    after_snippet: str,
    file_path: str = "index.html",
) -> str:
    """Generates a standard Git unified diff string between before and after snippets."""
    before_lines = before_snippet.splitlines(keepends=True)
    after_lines = after_snippet.splitlines(keepends=True)

    diff = difflib.unified_diff(
        before_lines,
        after_lines,
        fromfile=f"a/{file_path}",
        tofile=f"b/{file_path}",
        lineterm="",
    )
    return "".join(diff)


def compute_patch_hash(diff_content: str) -> str:
    """Computes SHA-256 hash of unified diff content."""
    return hashlib.sha256(diff_content.encode("utf-8")).hexdigest()


class ResolutionGenerator:
    """Generates deterministic, evidence-backed resolution plans from audit findings."""

    def generate_plan(self, report: AuditReportDTO) -> ResolutionPlanDTO:
        """Analyzes all findings in an audit report and builds a prioritized resolution plan."""
        tasks: list[ResolutionTask] = []
        automated_count = 0
        human_decision_count = 0

        # Target failing findings and actionable unknown findings
        actionable_findings = [
            f for f in report.findings if f.state in {RuleState.FAIL, RuleState.UNKNOWN}
        ]

        for finding in actionable_findings:
            task = self._build_task_for_finding(finding, report)
            if task:
                tasks.append(task)
                if task.actionType == ResolutionActionType.AUTOMATED_CODE_PATCH:
                    automated_count += 1
                else:
                    human_decision_count += 1

        # Sort tasks descending by RICE-inspired priority score (Model E21)
        tasks.sort(key=lambda t: t.priorityScore, reverse=True)

        return ResolutionPlanDTO(
            scanToken=report.scanToken,
            targetUrl=report.targetUrl,
            totalIssues=len(tasks),
            automatedCount=automated_count,
            humanDecisionCount=human_decision_count,
            tasks=tasks,
        )

    def _build_task_for_finding(
        self,
        finding: Finding,
        report: AuditReportDTO,
    ) -> ResolutionTask | None:
        """Builds a deterministic ResolutionTask for a specific finding."""
        rule_id = finding.ruleId
        target_selector = (
            finding.evidence.targetElement
            if finding.evidence and finding.evidence.targetElement
            else self._infer_default_selector(rule_id)
        )

        # 1. Determine reach, impact, confidence, and effort for Model E21
        is_site_wide = rule_id in SITE_WIDE_RULES
        reach = 10.0 if is_site_wide else self._estimate_reach(rule_id)
        confidence = (
            1.0
            if (
                finding.evidence
                and finding.evidence.provenance == ProvenanceCategory.DIRECT_OBSERVATION
            )
            else 0.8
        )
        effort = self._estimate_effort(rule_id)

        priority_res = calculate_resolution_priority(
            reach=reach,
            impact=finding.severity,
            confidence=confidence,
            effort=effort,
        )

        # 2. Compute Root-Cause Triage Composite for Model E20
        evidence_strength = (
            100.0
            if (
                finding.evidence
                and (
                    finding.evidence.httpStatusCode is not None
                    or finding.evidence.rawSnippet is not None
                )
            )
            else 85.0
            if target_selector
            else 60.0
        )
        scope = 100.0 if is_site_wide else 50.0

        triage_res = calculate_root_cause_triage(
            evidence_strength=evidence_strength,
            reproducibility=100.0,
            persistence=100.0,
            scope=scope,
        )

        # 3. Build Rule-Specific Resolution Content & Code Patch
        builder_method = getattr(self, f"_resolve_{rule_id.replace('-', '_')}", None)
        if builder_method:
            content, action_type, code_patch = builder_method(
                finding, report, target_selector
            )
        else:
            content, action_type, code_patch = self._default_fallback_resolution(
                finding, target_selector
            )

        task_id = uuid.uuid4().hex[:16]

        return ResolutionTask(
            taskId=task_id,
            ruleId=finding.ruleId,
            category=finding.category,
            severity=finding.severity,
            actionType=action_type,
            priorityScore=priority_res.priority_score,
            triageScore=triage_res.rc_score,
            title=content["title"],
            description=content["description"],
            targetSelector=target_selector,
            targetFilePath="UNKNOWN (Requires Repository Access)",
            proposedChange=content["proposedChange"],
            procedure=content["procedure"],
            expectedOutcome=content["expectedOutcome"],
            risks=content["risks"],
            rollbackInstructions=content["rollbackInstructions"],
            codePatch=code_patch,
            evidenceSnapshot=finding.evidence.model_dump() if finding.evidence else {},
        )

    def _infer_default_selector(self, rule_id: str) -> str | None:
        """Infers standard DOM selector or location from rule ID."""
        mapping = {
            "title-presence": "head > title",
            "title-length": "head > title",
            "meta-description-presence": "head > meta[name='description']",
            "meta-description-length": "head > meta[name='description']",
            "canonical-presence": "head > link[rel='canonical']",
            "canonical-format": "head > link[rel='canonical']",
            "h1-presence": "body h1",
            "h1-single": "body h1",
            "heading-hierarchy": "body h1, h2, h3, h4, h5, h6",
            "robots-meta-indexable": "head > meta[name='robots']",
            "x-robots-tag-indexable": "HTTP Header: X-Robots-Tag",
            "image-alt-coverage": "body img:not([alt])",
            "image-dimensions": "body img:not([width]):not([height])",
            "jsonld-valid-syntax": "head > script[type='application/ld+json']",
            "jsonld-schema-type": "head > script[type='application/ld+json']",
            "robots-txt-present": "Origin root: /robots.txt",
            "sitemap-referenced": "Origin root: /robots.txt or /sitemap.xml",
            "http-status-200": "Web server routing / HTTP response",
            "redirect-chain-length": "Web server redirect configuration",
            "https-enforced": "Web server TLS / SSL configuration",
        }
        return mapping.get(rule_id)

    def _estimate_reach(self, rule_id: str) -> float:
        """Estimates reach factor on scale [1.0, 10.0]."""
        if rule_id in {"robots-meta-indexable", "x-robots-tag-indexable"}:
            return 8.0
        if rule_id in {
            "title-presence",
            "title-length",
            "canonical-presence",
            "canonical-format",
            "h1-presence",
        }:
            return 6.0
        if rule_id in {"meta-description-presence", "image-alt-coverage"}:
            return 5.0
        return 3.0

    def _estimate_effort(self, rule_id: str) -> float:
        """Estimates engineering effort in hours [1.0, 10.0]."""
        if rule_id in {
            "title-presence",
            "title-length",
            "meta-description-presence",
            "meta-description-length",
            "canonical-presence",
            "canonical-format",
            "robots-meta-indexable",
        }:
            return 1.0
        if rule_id in {
            "h1-presence",
            "h1-single",
            "heading-hierarchy",
            "image-alt-coverage",
            "image-dimensions",
            "robots-txt-present",
            "sitemap-referenced",
        }:
            return 2.0
        return 3.0

    # -------------------------------------------------------------------------
    # Rule-specific resolution content & patch generators
    # -------------------------------------------------------------------------

    def _resolve_title_presence(
        self, finding: Finding, report: AuditReportDTO, selector: str | None
    ) -> tuple[dict[str, Any], ResolutionActionType, CodePatchProposal | None]:
        before = "<head>\n</head>"
        after = "<head>\n  <title>Descriptive Canonical Page Title</title>\n</head>"
        diff = create_unified_diff(before, after)
        patch = CodePatchProposal(
            patchId=uuid.uuid4().hex[:12],
            findingId=finding.ruleId,
            diffContent=diff,
            beforeSnippet=before,
            afterSnippet=after,
            patchHash=compute_patch_hash(diff),
        )
        content = {
            "title": "Add Missing <title> Tag to Document Head",
            "description": "The page lacks a <title> element, severely degrading organic search snippet presentation.",
            "proposedChange": "Insert a descriptive, non-empty <title> tag inside the <head> element.",
            "procedure": [
                "Locate the HTML <head> template for this view.",
                "Insert `<title>Descriptive Canonical Title</title>` before meta tags.",
                "Ensure title length is between 30 and 60 characters.",
                "Deploy and verify via re-scan.",
            ],
            "expectedOutcome": "Audit rule `title-presence` evaluates to PASS with HTTP 200.",
            "risks": ["Browser tab title and SERP snippet will change to new text."],
            "rollbackInstructions": "Remove the inserted <title> element or revert the template commit.",
        }
        return content, ResolutionActionType.AUTOMATED_CODE_PATCH, patch

    def _resolve_title_length(
        self, finding: Finding, report: AuditReportDTO, selector: str | None
    ) -> tuple[dict[str, Any], ResolutionActionType, CodePatchProposal | None]:
        current_title = (
            finding.evidence.observedValue
            if finding.evidence and finding.evidence.observedValue
            else "Current Short Title"
        )
        before = f"<title>{current_title}</title>"
        after = "<title>Optimized Descriptive Page Title (30 to 60 Chars)</title>"
        diff = create_unified_diff(before, after)
        patch = CodePatchProposal(
            patchId=uuid.uuid4().hex[:12],
            findingId=finding.ruleId,
            diffContent=diff,
            beforeSnippet=before,
            afterSnippet=after,
            patchHash=compute_patch_hash(diff),
        )
        content = {
            "title": "Optimize Page Title Length to 30-60 Characters",
            "description": f"The page title ({current_title}) is outside the optimal 30-60 character boundary.",
            "proposedChange": "Edit <title> tag text to fit between 30 and 60 characters.",
            "procedure": [
                "Open template containing the <title> tag.",
                "Draft a descriptive title containing primary keyword, between 30 and 60 characters.",
                "Update the <title> content.",
            ],
            "expectedOutcome": "Audit rule `title-length` evaluates to PASS.",
            "risks": ["Search engines may take several days to update snippet text."],
            "rollbackInstructions": f"Revert <title> tag text back to: '{current_title}'.",
        }
        return content, ResolutionActionType.AUTOMATED_CODE_PATCH, patch

    def _resolve_meta_description_presence(
        self, finding: Finding, report: AuditReportDTO, selector: str | None
    ) -> tuple[dict[str, Any], ResolutionActionType, CodePatchProposal | None]:
        before = "<head>\n</head>"
        after = (
            '<head>\n  <meta name="description" content="Accurate, compelling summary'
            " of the webpage content designed for organic search snippets"
            ' (120-160 characters).">\n</head>'
        )
        diff = create_unified_diff(before, after)
        patch = CodePatchProposal(
            patchId=uuid.uuid4().hex[:12],
            findingId=finding.ruleId,
            diffContent=diff,
            beforeSnippet=before,
            afterSnippet=after,
            patchHash=compute_patch_hash(diff),
        )
        content = {
            "title": "Add Missing Meta Description",
            "description": "The page lacks a meta description tag, leading to auto-generated SERP snippets.",
            "proposedChange": 'Insert `<meta name="description" content="...">` inside <head>.',
            "procedure": [
                "Draft a compelling 120-160 character summary of the page.",
                'Add `<meta name="description" content="...">` inside <head>.',
                "Verify snippet text is not duplicated across pages.",
            ],
            "expectedOutcome": "Audit rule `meta-description-presence` evaluates to PASS.",
            "risks": ["None. Purely additive metadata tag."],
            "rollbackInstructions": "Delete the inserted <meta name='description'> tag.",
        }
        return content, ResolutionActionType.AUTOMATED_CODE_PATCH, patch

    def _resolve_meta_description_length(
        self, finding: Finding, report: AuditReportDTO, selector: str | None
    ) -> tuple[dict[str, Any], ResolutionActionType, CodePatchProposal | None]:
        content = {
            "title": "Adjust Meta Description Length to 120-160 Characters",
            "description": "Meta description is too short or too long, risking snippet truncation in search results.",
            "proposedChange": "Revise meta description content attribute to be 120-160 characters long.",
            "procedure": [
                "Review the current meta description text in the document <head>.",
                "Edit description text to provide a complete value proposition between 120 and 160 characters.",
            ],
            "expectedOutcome": "Audit rule `meta-description-length` evaluates to PASS.",
            "risks": ["None."],
            "rollbackInstructions": "Restore original meta description string in template.",
        }
        return content, ResolutionActionType.AUTOMATED_CODE_PATCH, None

    def _resolve_canonical_presence(
        self, finding: Finding, report: AuditReportDTO, selector: str | None
    ) -> tuple[dict[str, Any], ResolutionActionType, CodePatchProposal | None]:
        canonical_url = report.finalUrl
        before = "<head>\n</head>"
        after = f'<head>\n  <link rel="canonical" href="{canonical_url}">\n</head>'
        diff = create_unified_diff(before, after)
        patch = CodePatchProposal(
            patchId=uuid.uuid4().hex[:12],
            findingId=finding.ruleId,
            diffContent=diff,
            beforeSnippet=before,
            afterSnippet=after,
            patchHash=compute_patch_hash(diff),
        )
        content = {
            "title": "Add Missing Canonical Link Tag",
            "description": "The page lacks a rel='canonical' link tag, exposing it to duplicate content ambiguity.",
            "proposedChange": f'Insert `<link rel="canonical" href="{canonical_url}">` inside <head>.',
            "procedure": [
                "Locate header template.",
                f'Insert `<link rel="canonical" href="{canonical_url}">`.',
                "Ensure URL protocol is HTTPS and matches authoritative landing URL.",
            ],
            "expectedOutcome": "Audit rule `canonical-presence` evaluates to PASS.",
            "risks": [
                "Ensure canonical points to this exact authoritative URL, not an unintended landing page."
            ],
            "rollbackInstructions": "Remove the inserted <link rel='canonical'> element.",
        }
        return content, ResolutionActionType.AUTOMATED_CODE_PATCH, patch

    def _resolve_canonical_format(
        self, finding: Finding, report: AuditReportDTO, selector: str | None
    ) -> tuple[dict[str, Any], ResolutionActionType, CodePatchProposal | None]:
        content = {
            "title": "Format Canonical URL as Absolute HTTPS Address",
            "description": "The canonical link is either relative, invalid, or mismatches the site origin host.",
            "proposedChange": f"Update the canonical href attribute to the absolute HTTPS URL: '{report.finalUrl}'.",
            "procedure": [
                "Locate the <link rel='canonical'> element in <head>.",
                f"Replace relative or invalid href with absolute URL: '{report.finalUrl}'.",
            ],
            "expectedOutcome": "Audit rule `canonical-format` evaluates to PASS.",
            "risks": ["Cross-domain canonicalization will de-index current URL."],
            "rollbackInstructions": "Revert href attribute to previous state.",
        }
        return content, ResolutionActionType.AUTOMATED_CODE_PATCH, None

    def _resolve_h1_presence(
        self, finding: Finding, report: AuditReportDTO, selector: str | None
    ) -> tuple[dict[str, Any], ResolutionActionType, CodePatchProposal | None]:
        before = "<main>\n</main>"
        after = "<main>\n  <h1>Authoritative Primary Page Heading</h1>\n</main>"
        diff = create_unified_diff(before, after)
        patch = CodePatchProposal(
            patchId=uuid.uuid4().hex[:12],
            findingId=finding.ruleId,
            diffContent=diff,
            beforeSnippet=before,
            afterSnippet=after,
            patchHash=compute_patch_hash(diff),
        )
        content = {
            "title": "Add Primary <h1> Heading",
            "description": "The document structure lacks a top-level <h1> element defining the primary page topic.",
            "proposedChange": "Insert exactly one <h1> element inside the primary content container.",
            "procedure": [
                "Identify the main article/page container (<main> or primary <section>).",
                "Add an <h1> heading matching the page's core topic.",
            ],
            "expectedOutcome": "Audit rule `h1-presence` evaluates to PASS.",
            "risks": ["Visual typography adjustment may be required."],
            "rollbackInstructions": "Remove inserted <h1> element.",
        }
        return content, ResolutionActionType.AUTOMATED_CODE_PATCH, patch

    def _resolve_h1_single(
        self, finding: Finding, report: AuditReportDTO, selector: str | None
    ) -> tuple[dict[str, Any], ResolutionActionType, CodePatchProposal | None]:
        content = {
            "title": "Demote Multiple <h1> Tags to <h2>",
            "description": "The page contains multiple <h1> headings, creating document outline ambiguity.",
            "proposedChange": "Retain only the primary <h1> tag and demote secondary <h1> tags to <h2>.",
            "procedure": [
                "Inspect the page headings and identify the primary page title <h1>.",
                "Change all other <h1> tags in secondary sections into <h2> tags.",
            ],
            "expectedOutcome": "Audit rule `h1-single` evaluates to PASS (count of <h1> == 1).",
            "risks": ["CSS styles applied to <h1> may need updating on demoted <h2>s."],
            "rollbackInstructions": "Restore secondary headings to <h1> tags.",
        }
        return content, ResolutionActionType.AUTOMATED_CODE_PATCH, None

    def _resolve_heading_hierarchy(
        self, finding: Finding, report: AuditReportDTO, selector: str | None
    ) -> tuple[dict[str, Any], ResolutionActionType, CodePatchProposal | None]:
        content = {
            "title": "Fix Skipped Heading Hierarchy Levels",
            "description": "Heading levels skip descending order (e.g. H2 followed directly by H4).",
            "proposedChange": "Adjust heading hierarchy to be strictly sequential (H1 -> H2 -> H3 -> H4).",
            "procedure": [
                "Locate the skipped heading identified in evidence.",
                "Adjust heading level to the immediate sub-level (e.g. change H4 to H3 if preceding heading is H2).",
            ],
            "expectedOutcome": "Audit rule `heading-hierarchy` evaluates to PASS.",
            "risks": ["None."],
            "rollbackInstructions": "Revert changed heading tag level.",
        }
        return content, ResolutionActionType.AUTOMATED_CODE_PATCH, None

    def _resolve_robots_meta_indexable(
        self, finding: Finding, report: AuditReportDTO, selector: str | None
    ) -> tuple[dict[str, Any], ResolutionActionType, CodePatchProposal | None]:
        before = '<meta name="robots" content="noindex, follow">'
        after = '<meta name="robots" content="index, follow">'
        diff = create_unified_diff(before, after)
        patch = CodePatchProposal(
            patchId=uuid.uuid4().hex[:12],
            findingId=finding.ruleId,
            diffContent=diff,
            beforeSnippet=before,
            afterSnippet=after,
            patchHash=compute_patch_hash(diff),
        )
        content = {
            "title": "Remove 'noindex' from Meta Robots Tag",
            "description": "CRITICAL: The page explicitly instructs search engines not to index it via <meta name='robots'>.",
            "proposedChange": "Remove 'noindex' or replace with 'index, follow' in the meta robots tag.",
            "procedure": [
                "Locate `<meta name='robots'>` in `<head>`.",
                "Remove 'noindex' directive.",
                "If the page should rank, replace with `<meta name='robots' content='index, follow'>`.",
            ],
            "expectedOutcome": "Audit rule `robots-meta-indexable` evaluates to PASS.",
            "risks": [
                "Search engines will index this page. Verify this page is intended for public indexing."
            ],
            "rollbackInstructions": "Re-insert 'noindex' if page is intended to be private or staging.",
        }
        return content, ResolutionActionType.AUTOMATED_CODE_PATCH, patch

    def _resolve_x_robots_tag_indexable(
        self, finding: Finding, report: AuditReportDTO, selector: str | None
    ) -> tuple[dict[str, Any], ResolutionActionType, CodePatchProposal | None]:
        content = {
            "title": "Remove 'noindex' from X-Robots-Tag HTTP Header",
            "description": "CRITICAL: The web server emits an HTTP header 'X-Robots-Tag: noindex' blocking indexing.",
            "proposedChange": "Configure web server or reverse proxy to remove 'noindex' from X-Robots-Tag response header.",
            "procedure": [
                "Inspect server configuration (Nginx, Apache, Cloudflare, Vercel headers, or application middleware).",
                "Remove the directive adding 'X-Robots-Tag: noindex' for production canonical routes.",
                "Reload or redeploy web server.",
            ],
            "expectedOutcome": "HTTP response header X-Robots-Tag does not contain 'noindex'.",
            "risks": [
                "Verify with devops team that the page is not in a staging environment."
            ],
            "rollbackInstructions": "Re-enable header directive in web server config.",
        }
        return content, ResolutionActionType.HUMAN_DECISION_REQUIRED, None

    def _resolve_image_alt_coverage(
        self, finding: Finding, report: AuditReportDTO, selector: str | None
    ) -> tuple[dict[str, Any], ResolutionActionType, CodePatchProposal | None]:
        content = {
            "title": "Add Descriptive Alt Attributes to Meaningful Images",
            "description": "One or more meaningful <img> elements lack non-empty 'alt' attributes (Model E10).",
            "proposedChange": "Add descriptive 'alt' attribute summarizing image content to all non-decorative <img> tags.",
            "procedure": [
                "Inspect images flagged in audit evidence.",
                "For content images: add `alt='Descriptive text'`. For decorative icons: add `alt='' aria-hidden='true'`.",
            ],
            "expectedOutcome": "Audit rule `image-alt-coverage` evaluates to PASS.",
            "risks": ["None."],
            "rollbackInstructions": "Remove or revert added alt attributes.",
        }
        return content, ResolutionActionType.AUTOMATED_CODE_PATCH, None

    def _resolve_image_dimensions(
        self, finding: Finding, report: AuditReportDTO, selector: str | None
    ) -> tuple[dict[str, Any], ResolutionActionType, CodePatchProposal | None]:
        content = {
            "title": "Declare Explicit Width and Height on <img> Tags",
            "description": "Images lack explicit width and height attributes, increasing Cumulative Layout Shift (CLS).",
            "proposedChange": "Add width='...' and height='...' attributes or CSS aspect-ratio to prevent layout shift.",
            "procedure": [
                "Determine intrinsic dimensions of images flagged in audit evidence.",
                "Add `width='{w}' height='{h}'` attributes directly to <img> tags.",
            ],
            "expectedOutcome": "Audit rule `image-dimensions` evaluates to PASS.",
            "risks": [
                "Ensure CSS `height: auto` is applied to prevent image distortion."
            ],
            "rollbackInstructions": "Remove added width and height attributes.",
        }
        return content, ResolutionActionType.AUTOMATED_CODE_PATCH, None

    def _resolve_jsonld_valid_syntax(
        self, finding: Finding, report: AuditReportDTO, selector: str | None
    ) -> tuple[dict[str, Any], ResolutionActionType, CodePatchProposal | None]:
        content = {
            "title": "Correct JSON-LD Syntax Errors in Schema Scripts",
            "description": "One or more <script type='application/ld+json'> tags contain invalid JSON syntax (Model E14).",
            "proposedChange": "Fix JSON syntax (trailing commas, unescaped characters, missing quotes) in JSON-LD scripts.",
            "procedure": [
                "Locate the invalid JSON-LD block in <head> or <body>.",
                "Validate the JSON payload against RFC 8259 using a JSON validator.",
                "Update script content with valid JSON.",
            ],
            "expectedOutcome": "Audit rule `jsonld-valid-syntax` evaluates to PASS.",
            "risks": ["None."],
            "rollbackInstructions": "Restore original script payload.",
        }
        return content, ResolutionActionType.AUTOMATED_CODE_PATCH, None

    def _resolve_jsonld_schema_type(
        self, finding: Finding, report: AuditReportDTO, selector: str | None
    ) -> tuple[dict[str, Any], ResolutionActionType, CodePatchProposal | None]:
        content = {
            "title": "Declare Recognized Schema.org @type in JSON-LD",
            "description": "JSON-LD schema lacks a recognized Schema.org @type (e.g. Organization, WebSite, Article).",
            "proposedChange": "Specify a canonical Schema.org '@type' suitable for your entity.",
            "procedure": [
                "Choose the appropriate Schema.org entity type (Organization, WebSite, Product, Article, etc.).",
                'Set `"@type": "Organization"` (or selected type) in the root JSON-LD object.',
            ],
            "expectedOutcome": "Audit rule `jsonld-schema-type` evaluates to PASS.",
            "risks": [
                "Ensure required properties for the chosen Schema type are provided."
            ],
            "rollbackInstructions": "Revert the @type field change.",
        }
        return content, ResolutionActionType.HUMAN_DECISION_REQUIRED, None

    def _resolve_robots_txt_present(
        self, finding: Finding, report: AuditReportDTO, selector: str | None
    ) -> tuple[dict[str, Any], ResolutionActionType, CodePatchProposal | None]:
        content = {
            "title": "Create and Publish /robots.txt at Origin Root",
            "description": "No accessible /robots.txt file was found at the website's origin root (responded 404 or unavailable).",
            "proposedChange": "Deploy a standard /robots.txt file at the domain root with crawl guidelines and sitemap directive.",
            "procedure": [
                "Create a text file named `robots.txt` in the website public web root.",
                "Add standard rules:\nUser-agent: *\nAllow: /\nSitemap: https://yourdomain.com/sitemap.xml",
                "Deploy and confirm https://yourdomain.com/robots.txt returns HTTP 200.",
            ],
            "expectedOutcome": "Audit rule `robots-txt-present` evaluates to PASS.",
            "risks": [
                "Ensure disallow directives do not accidentally block search engines from public pages."
            ],
            "rollbackInstructions": "Delete or replace /robots.txt on server.",
        }
        return content, ResolutionActionType.HUMAN_DECISION_REQUIRED, None

    def _resolve_sitemap_referenced(
        self, finding: Finding, report: AuditReportDTO, selector: str | None
    ) -> tuple[dict[str, Any], ResolutionActionType, CodePatchProposal | None]:
        content = {
            "title": "Reference XML Sitemap in /robots.txt or Root Location",
            "description": "No XML sitemap was found referenced in robots.txt, HTTP Link headers, or at /sitemap.xml (Model E12).",
            "proposedChange": "Add 'Sitemap: https://yourdomain.com/sitemap.xml' directive to robots.txt.",
            "procedure": [
                "Generate a valid XML sitemap of all canonical indexable pages.",
                "Publish the sitemap at `https://yourdomain.com/sitemap.xml`.",
                "Add `Sitemap: https://yourdomain.com/sitemap.xml` to `robots.txt`.",
            ],
            "expectedOutcome": "Audit rule `sitemap-referenced` evaluates to PASS.",
            "risks": [
                "Ensure non-canonical, 404, or noindex pages are excluded from sitemap."
            ],
            "rollbackInstructions": "Remove the Sitemap directive from robots.txt.",
        }
        return content, ResolutionActionType.HUMAN_DECISION_REQUIRED, None

    def _resolve_http_status_200(
        self, finding: Finding, report: AuditReportDTO, selector: str | None
    ) -> tuple[dict[str, Any], ResolutionActionType, CodePatchProposal | None]:
        content = {
            "title": f"Resolve Non-200 HTTP Response (Status {report.statusCode})",
            "description": f"CRITICAL: The requested landing page returned HTTP {report.statusCode} instead of HTTP 200 OK.",
            "proposedChange": "Fix server route, application exception, or client-side URL to return HTTP 200 OK.",
            "procedure": [
                "Check web server error logs for application crashes or missing routes.",
                "If page was moved, configure a 301 permanent redirect to the new authoritative URL.",
                "If page is active, ensure backend returns HTTP 200 status code.",
            ],
            "expectedOutcome": "The landing URL responds with HTTP status 200 OK.",
            "risks": [
                "Application changes may require server restart or code deployment."
            ],
            "rollbackInstructions": "Revert server configuration or route changes.",
        }
        return content, ResolutionActionType.HUMAN_DECISION_REQUIRED, None

    def _resolve_redirect_chain_length(
        self, finding: Finding, report: AuditReportDTO, selector: str | None
    ) -> tuple[dict[str, Any], ResolutionActionType, CodePatchProposal | None]:
        content = {
            "title": "Consolidate Multi-Hop Redirect Chain (Model E11)",
            "description": "The URL traverses multiple redirect hops before reaching the landing destination.",
            "proposedChange": "Update redirect rules and internal links to point directly to the final landing URL in 1 hop.",
            "procedure": [
                "Inspect the redirect chain hops in audit evidence.",
                "Update server redirect mapping (e.g. Nginx, Cloudflare) so the initial URL redirects directly to final URL.",
                "Update internal site links to target the final destination directly.",
            ],
            "expectedOutcome": "Redirect chain length <= 1 hop.",
            "risks": [
                "Ensure other incoming traffic to intermediary URLs is preserved."
            ],
            "rollbackInstructions": "Restore previous redirect rules in server config.",
        }
        return content, ResolutionActionType.HUMAN_DECISION_REQUIRED, None

    def _resolve_https_enforced(
        self, finding: Finding, report: AuditReportDTO, selector: str | None
    ) -> tuple[dict[str, Any], ResolutionActionType, CodePatchProposal | None]:
        content = {
            "title": "Enforce HTTPS Protocol and TLS Encryption",
            "description": "Content is being served over unencrypted HTTP protocol.",
            "proposedChange": "Install valid SSL/TLS certificate and configure HTTP 301 redirect to HTTPS.",
            "procedure": [
                "Install a valid SSL/TLS certificate on the web server or CDN.",
                "Configure 301 permanent redirect from `http://` to `https://` for all incoming requests.",
                "Ensure HSTS (HTTP Strict Transport Security) header is configured.",
            ],
            "expectedOutcome": "All incoming HTTP requests redirect to HTTPS and landing URL scheme is 'https:'.",
            "risks": ["Mixed content warnings if internal assets reference HTTP."],
            "rollbackInstructions": "Disable HTTPS redirect rule if certificate issue occurs.",
        }
        return content, ResolutionActionType.HUMAN_DECISION_REQUIRED, None

    def _default_fallback_resolution(
        self, finding: Finding, selector: str | None
    ) -> tuple[dict[str, Any], ResolutionActionType, CodePatchProposal | None]:
        content = {
            "title": f"Resolve Issue: {finding.title}",
            "description": finding.description,
            "proposedChange": finding.remediationGuidance
            or "Apply recommended correction.",
            "procedure": [
                "Review evidence snapshot attached to this finding.",
                "Apply corrective adjustments to page template or server config.",
                "Re-scan to verify resolution.",
            ],
            "expectedOutcome": f"Audit rule `{finding.ruleId}` evaluates to PASS.",
            "risks": ["Review changes in staging before deploying."],
            "rollbackInstructions": "Revert the applied change if unexpected behavior occurs.",
        }
        return content, ResolutionActionType.HUMAN_DECISION_REQUIRED, None
