"""Unit tests for deterministic resolution plan generation and code patch proposals."""

from app.contracts.enums import (
    IssueSeverity,
    ProvenanceCategory,
    RuleCategory,
    RuleState,
)
from app.contracts.evidence import FindingEvidence
from app.contracts.finding import Finding
from app.contracts.scan import AuditReportDTO
from app.resolution.generator import ResolutionGenerator
from app.resolution.models import ResolutionActionType


def create_sample_report_with_failures() -> AuditReportDTO:
    """Helper creating an AuditReportDTO with realistic failing findings."""
    findings = [
        Finding(
            ruleId="title-presence",
            category=RuleCategory.INDEXABILITY,
            title="Page Title Tag Presence",
            description="The page lacks a <title> tag.",
            state=RuleState.FAIL,
            severity=IssueSeverity.HIGH,
            weight=9,
            evidence=FindingEvidence(
                observedValue="No <title> found",
                expectedValue="Non-empty <title>",
                provenance=ProvenanceCategory.DIRECT_OBSERVATION,
                targetElement="head > title",
            ),
            remediationGuidance="Add a descriptive title tag.",
        ),
        Finding(
            ruleId="https-enforced",
            category=RuleCategory.CRAWLABILITY,
            title="HTTPS Encryption Enforced",
            description="Page is served over HTTP.",
            state=RuleState.FAIL,
            severity=IssueSeverity.HIGH,
            weight=7,
            evidence=FindingEvidence(
                observedValue="http://",
                expectedValue="https://",
                provenance=ProvenanceCategory.DIRECT_OBSERVATION,
            ),
            remediationGuidance="Install SSL and 301 redirect.",
        ),
        Finding(
            ruleId="robots-meta-indexable",
            category=RuleCategory.CRAWLABILITY,
            title="Robots Meta Tag Indexability",
            description="Contains noindex.",
            state=RuleState.FAIL,
            severity=IssueSeverity.CRITICAL,
            weight=9,
            evidence=FindingEvidence(
                observedValue="noindex, follow",
                expectedValue="index, follow",
                provenance=ProvenanceCategory.DIRECT_OBSERVATION,
                targetElement="head > meta[name='robots']",
            ),
            remediationGuidance="Remove noindex from meta robots.",
        ),
        Finding(
            ruleId="http-status-200",
            category=RuleCategory.CRAWLABILITY,
            title="HTTP Status 200 OK",
            description="Responded 200 OK.",
            state=RuleState.PASS,
            severity=IssueSeverity.CRITICAL,
            weight=10,
            evidence=FindingEvidence(
                observedValue="HTTP 200",
                expectedValue="HTTP 200",
                provenance=ProvenanceCategory.DIRECT_OBSERVATION,
            ),
            remediationGuidance="No action needed. Status is 200 OK.",
        ),

    ]

    return AuditReportDTO(
        scanToken="token-res-test-123",
        targetUrl="http://example.com/test",
        finalUrl="http://example.com/test",
        statusCode=200,
        overallScore=65.0,
        completenessScore=100.0,
        categoryScores={},
        categoryAvailability={},
        findings=findings,
    )


def test_resolution_generator_produces_prioritized_plan():
    """Verifies that failing findings are converted into actionable, prioritized tasks."""
    report = create_sample_report_with_failures()
    generator = ResolutionGenerator()

    plan = generator.generate_plan(report)

    assert plan.scanToken == "token-res-test-123"
    assert plan.targetUrl == "http://example.com/test"
    assert plan.totalIssues == 3  # 3 failing findings
    assert len(plan.tasks) == 3

    # Ensure tasks are sorted descending by priority score (Model E21)
    for i in range(len(plan.tasks) - 1):
        assert plan.tasks[i].priorityScore >= plan.tasks[i + 1].priorityScore


def test_resolution_action_type_classification():
    """Separates automated code patches from issues requiring human decisions."""
    report = create_sample_report_with_failures()
    generator = ResolutionGenerator()

    plan = generator.generate_plan(report)
    tasks_by_rule = {t.ruleId: t for t in plan.tasks}

    # title-presence and robots-meta-indexable can be patched automatically
    assert tasks_by_rule["title-presence"].actionType == ResolutionActionType.AUTOMATED_CODE_PATCH
    assert tasks_by_rule["robots-meta-indexable"].actionType == ResolutionActionType.AUTOMATED_CODE_PATCH

    # https-enforced requires web server SSL / DNS / hosting decision
    assert tasks_by_rule["https-enforced"].actionType == ResolutionActionType.HUMAN_DECISION_REQUIRED


def test_no_fake_source_file_paths_for_public_scans():
    """Strict Rule: Do not generate fake source-code file paths from public URL scan."""
    report = create_sample_report_with_failures()
    generator = ResolutionGenerator()

    plan = generator.generate_plan(report)
    for task in plan.tasks:
        assert task.targetFilePath == "UNKNOWN (Requires Repository Access)"
        if task.codePatch:
            assert task.codePatch.affectedFile == "UNKNOWN (Requires Repository Access)"


def test_code_patch_proposals_require_human_approval():
    """Strict Rule: Code patches must require explicit human approval and include diff."""
    report = create_sample_report_with_failures()
    generator = ResolutionGenerator()

    plan = generator.generate_plan(report)
    tasks_by_rule = {t.ruleId: t for t in plan.tasks}

    title_task = tasks_by_rule["title-presence"]
    assert title_task.codePatch is not None
    assert title_task.codePatch.requiresApproval is True
    assert title_task.codePatch.approvalStatus == "PENDING_REVIEW"
    assert "--- a/index.html" in title_task.codePatch.diffContent
    assert "+++ b/index.html" in title_task.codePatch.diffContent
    assert len(title_task.codePatch.patchHash) == 64  # SHA-256


def test_task_contains_procedure_and_rollback():
    """Verifies each task contains complete procedure, risks, and rollback instructions."""
    report = create_sample_report_with_failures()
    generator = ResolutionGenerator()

    plan = generator.generate_plan(report)
    for task in plan.tasks:
        assert len(task.procedure) > 0
        assert len(task.expectedOutcome) > 0
        assert len(task.rollbackInstructions) > 0
        assert task.triageScore >= 0.0
