"""Integration tests for resolution planning and verification endpoints."""

import pytest
from httpx import AsyncClient

from app.contracts.enums import (
    IssueSeverity,
    ProvenanceCategory,
    RuleCategory,
    RuleState,
)
from app.contracts.evidence import FindingEvidence
from app.contracts.finding import Finding
from app.contracts.scan import AuditReportDTO


def make_audit_report(token: str, fail_rules: list[str]) -> dict:
    findings = [
        Finding(
            ruleId=r_id,
            category=RuleCategory.INDEXABILITY,
            title=f"Rule {r_id}",
            description="Audit rule",
            state=RuleState.FAIL,
            severity=IssueSeverity.HIGH,
            weight=8,
            evidence=FindingEvidence(
                observedValue="Failed check",
                expectedValue="PASS",
                provenance=ProvenanceCategory.DIRECT_OBSERVATION,
            ),
            remediationGuidance=f"Remediation guidance for {r_id}",
        ).model_dump()

        for r_id in fail_rules
    ]

    report = AuditReportDTO(
        scanToken=token,
        targetUrl="https://example.com/test",
        finalUrl="https://example.com/test",
        statusCode=200,
        overallScore=70.0,
        completenessScore=100.0,
        categoryScores={},
        categoryAvailability={},
        findings=[],  # Will populate below
    ).model_dump(mode="json")

    report["findings"] = [f.model_dump(mode="json") if hasattr(f, "model_dump") else f for f in findings]
    return report


@pytest.mark.asyncio
async def test_api_resolution_plan_endpoint(async_client: AsyncClient):
    """Verifies POST /api/v1/resolution/plan accepts AuditReportDTO and returns ResolutionPlanDTO."""
    report_dict = make_audit_report("token-res-api", ["title-presence", "canonical-presence"])

    response = await async_client.post("/api/v1/resolution/plan", json=report_dict)
    assert response.status_code == 200
    plan = response.json()

    assert plan["scanToken"] == "token-res-api"
    assert plan["totalIssues"] == 2
    assert len(plan["tasks"]) == 2
    rule_ids = {t["ruleId"] for t in plan["tasks"]}
    assert "title-presence" in rule_ids
    assert "canonical-presence" in rule_ids
    for task in plan["tasks"]:
        assert task["targetFilePath"] == "UNKNOWN (Requires Repository Access)"
        assert task["priorityScore"] > 0.0


@pytest.mark.asyncio
async def test_api_verification_compare_endpoint(async_client: AsyncClient):
    """Verifies POST /api/v1/verification/compare calculates transitions and Model E33 IRR."""
    baseline = make_audit_report("token-base", ["title-presence", "h1-presence"])
    # In post-change, title-presence is fixed, but h1-presence is still failing
    post = make_audit_report("token-post", ["h1-presence"])
    # Add title-presence as PASS in post
    pass_finding = Finding(
        ruleId="title-presence",
        category=RuleCategory.INDEXABILITY,
        title="Rule title-presence",
        description="Audit rule",
        state=RuleState.PASS,
        severity=IssueSeverity.HIGH,
        weight=8,
        evidence=FindingEvidence(
            observedValue="Passing title",
            expectedValue="PASS",
            provenance=ProvenanceCategory.DIRECT_OBSERVATION,
        ),
        remediationGuidance="No action needed. Title is present.",
    ).model_dump(mode="json")

    post["findings"].append(pass_finding)

    payload = {
        "baselineReport": baseline,
        "postChangeReport": post,
        "attemptedRuleIds": ["title-presence", "h1-presence"],
    }

    response = await async_client.post("/api/v1/verification/compare", json=payload)
    assert response.status_code == 200
    ver_report = response.json()

    assert ver_report["totalAttempted"] == 2
    assert ver_report["resolvedCount"] == 1
    assert ver_report["unresolvedCount"] == 1
    assert ver_report["issueResolutionRate"] == 50.0

    # Test markdown export endpoint
    md_response = await async_client.post(
        "/api/v1/verification/export-markdown", json=ver_report
    )
    assert md_response.status_code == 200
    md_data = md_response.json()
    assert "# SEO Optimizer — Post-Deployment Verification Report" in md_data["markdown"]
    assert "Issue Resolution Rate (IRR)" in md_data["markdown"]
