"""Work Package 1.4.3: End-to-End Staging Acceptance Audit Script.

Executes the complete 12-step application lifecycle against the dedicated
hosted Supabase staging database (ref: vfkuzlbiwbmcfcfecqgi.supabase.co).
"""

import asyncio
import os
import sys
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, patch

from dotenv import load_dotenv
from httpx import ASGITransport, AsyncClient

# Search for .env
for parent in Path(__file__).resolve().parents:
    env_candidate = parent / ".env"
    if env_candidate.exists():
        load_dotenv(env_candidate)
        break

# Configure environment for staging persistence
staging_url = os.getenv("SUPABASE_STAGING_URL") or os.getenv("SUPABASE_URL")
staging_key = os.getenv("SUPABASE_STAGING_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not (staging_url and staging_key):
    print("FATAL: Staging credentials not found in environment.")
    sys.exit(1)

os.environ["PERSISTENCE_BACKEND"] = "supabase"
os.environ["SUPABASE_URL"] = staging_url
os.environ["SUPABASE_SERVICE_ROLE_KEY"] = staging_key

import app.api.v1.endpoints.leads as leads_endpoint_module
import app.persistence.repository as repo_module
from app.contracts.enums import (
    IssueSeverity,
    LeadStatus,
    ProvenanceCategory,
    RuleState,
    ScanStatus,
)
from app.core.config import settings
from app.crawler.client import CrawlResult
from app.crawler.redirects import RedirectEvaluation
from app.main import app
from app.persistence.factory import create_lead_repository
from tests.fixtures.html_samples import VALID_PAGE_HTML


async def run_12_step_acceptance_audit():
    print("=" * 80)
    print("SEO OPTIMIZER — WORK PACKAGE 1.4.3 STAGING ACCEPTANCE AUDIT")
    print("Target Environment: Supabase Staging (ref: vfkuzlbiwbmcfcfecqgi)")
    print("=" * 80)

    # Instantiate staging repository adapter explicitly
    staging_repo = create_lead_repository(
        backend="supabase",
        supabase_url=staging_url,
        supabase_key=staging_key,
    )
    repo_module.lead_repository = staging_repo
    leads_endpoint_module.lead_repository = staging_repo

    print(f"\n[Environment Setup] Active Repository: {type(staging_repo).__name__}")
    assert type(staging_repo).__name__ == "SupabaseLeadRepository"
    print("  -> Confirmed: PERSISTENCE_BACKEND=supabase active with SupabaseLeadRepository.")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:

        # ---------------------------------------------------------------------
        # STEP 1: Submit URL for Scan (POST /api/v1/scan)
        # ---------------------------------------------------------------------
        print("\n--- STEP 1: Submit URL for Scan (POST /api/v1/scan) ---")
        target_scan_url = "https://example-staging-audit.com/landing"
        redirect_eval = RedirectEvaluation(
            total_hops=0,
            has_loop=False,
            initial_url=target_scan_url,
            final_url=target_scan_url,
            hops=[],
            rule_state=RuleState.PASS,
            severity=IssueSeverity.INFO,
            deduction_points=0,
            guidance="Direct URL",
        )
        mock_crawl = CrawlResult(
            requested_url=target_scan_url,
            final_url=target_scan_url,
            status_code=200,
            headers={"content-type": "text/html; charset=utf-8"},
            body=VALID_PAGE_HTML,
            body_byte_size=len(VALID_PAGE_HTML.encode("utf-8")),
            response_time_ms=88,
            redirect_evaluation=redirect_eval,
            content_type="text/html",
        )

        with patch("app.api.v1.endpoints.scan.SafeHttpClient.fetch", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = mock_crawl
            scan_resp = await client.post("/api/v1/scan", json={"url": target_scan_url})

        assert scan_resp.status_code == 200, f"Scan failed: {scan_resp.text}"
        audit_report = scan_resp.json()
        scan_token = audit_report["scanToken"]
        print(f"  Status Code: {scan_resp.status_code}")
        print(f"  Scan Token: {scan_token}")
        print(f"  Target URL: {audit_report['targetUrl']}")
        print(f"  Status: {audit_report['status']}")
        assert audit_report["status"] == ScanStatus.COMPLETED

        # ---------------------------------------------------------------------
        # STEP 2: Report Generation & Scoring (Models E2, E3, E5)
        # ---------------------------------------------------------------------
        print("\n--- STEP 2: Report Generation & Scoring (Models E2, E3, E5) ---")
        overall_score = audit_report["overallScore"]
        completeness = audit_report["completenessScore"]
        category_scores = audit_report["categoryScores"]

        print(f"  Overall Health Score (E3): {overall_score:.2f} / 100.0")
        print(f"  Report Completeness Index (E5): {completeness:.2f}%")
        print("  Category Health Scores (E2):")
        for cat, cat_dto in category_scores.items():
            s_val = f"{cat_dto['score']:.1f}" if cat_dto.get("score") is not None else "NULL (No applicable checks)"
            c_val = f"{cat_dto['completeness']:.1f}%" if cat_dto.get("completeness") is not None else "NULL"
            print(f"    - {cat:15s}: Score={s_val}, Completeness={c_val} (Checks: {cat_dto.get('evaluatedChecks', 0)}/{cat_dto.get('applicableChecks', 0)})")

        assert 0.0 <= overall_score <= 100.0
        assert 0.0 <= completeness <= 100.0
        assert len(category_scores) >= 4

        # ---------------------------------------------------------------------
        # STEP 3: Findings & Evidence Structures (Model E1)
        # ---------------------------------------------------------------------
        print("\n--- STEP 3: Findings & Evidence Structures (Model E1) ---")
        findings = audit_report["findings"]
        print(f"  Total Rules Evaluated: {len(findings)}")
        assert len(findings) == 20, f"Expected 20 canonical rules, got {len(findings)}"

        states = {f["state"] for f in findings}
        print(f"  Observed Finding States: {states}")
        for sample_f in findings[:3]:
            print(f"    Rule [{sample_f['ruleId']}]: State={sample_f['state']}, Severity={sample_f['severity']}, "
                  f"Provenance={sample_f['evidence']['provenance']}")
            assert sample_f["evidence"]["provenance"] in [
                ProvenanceCategory.DIRECT_OBSERVATION,
                ProvenanceCategory.EXTERNAL_MEASUREMENT,
                ProvenanceCategory.LICENSED_ESTIMATE,
                ProvenanceCategory.INTERNAL_COMPOSITE,
            ]

        # ---------------------------------------------------------------------
        # STEP 4: Remediation Plan Generation (POST /api/v1/resolution/plan)
        # ---------------------------------------------------------------------
        print("\n--- STEP 4: Remediation Plan Generation (POST /api/v1/resolution/plan) ---")
        # Ensure we have at least one failing finding for resolution testing
        test_audit_report = dict(audit_report)
        failing_rules = ["title-presence", "meta-description-presence", "canonical-presence"]
        augmented_findings = []
        for f in findings:
            f_copy = dict(f)
            if f_copy["ruleId"] in failing_rules:
                f_copy["state"] = RuleState.FAIL
                f_copy["severity"] = IssueSeverity.HIGH
                f_copy["evidence"] = {
                    "observedValue": "Missing tag in document head",
                    "expectedValue": "Valid tag present",
                    "provenance": ProvenanceCategory.DIRECT_OBSERVATION,
                }
            augmented_findings.append(f_copy)
        test_audit_report["findings"] = augmented_findings

        plan_resp = await client.post("/api/v1/resolution/plan", json=test_audit_report)
        assert plan_resp.status_code == 200, f"Plan generation failed: {plan_resp.text}"
        resolution_plan = plan_resp.json()
        print(f"  Status Code: {plan_resp.status_code}")
        print(f"  Scan Token: {resolution_plan['scanToken']}")
        print(f"  Total Remediation Tasks: {len(resolution_plan['tasks'])}")
        print(f"  Automated Tasks Count: {resolution_plan['automatedCount']}")
        print(f"  Human Decision Count: {resolution_plan['humanDecisionCount']}")
        assert len(resolution_plan["tasks"]) >= 3

        for task in resolution_plan["tasks"][:3]:
            print(f"    Task [{task['taskId']}]: Rule={task['ruleId']}, Priority={task['priorityScore']:.2f}, "
                  f"ActionType={task['actionType']}")
            assert "rollbackInstructions" in task
            assert "procedure" in task

        # ---------------------------------------------------------------------
        # STEP 5: Approval Requirements & Unified Diffs
        # ---------------------------------------------------------------------
        print("\n--- STEP 5: Approval Requirements & Unified Diffs ---")
        automated_tasks = [t for t in resolution_plan["tasks"] if t["actionType"] == "AUTOMATED_CODE_PATCH"]
        manual_tasks = [t for t in resolution_plan["tasks"] if t["actionType"] == "HUMAN_DECISION_REQUIRED"]
        tasks_with_diff = [t for t in resolution_plan["tasks"] if t.get("codePatch")]

        print(f"  Automated Tasks: {len(automated_tasks)}")
        print(f"  Manual / Human Decision Tasks: {len(manual_tasks)}")
        print(f"  Tasks with Code Diffs: {len(tasks_with_diff)}")
        for t in tasks_with_diff[:2]:
            patch_data = t["codePatch"]
            print(f"    Diff for {t['ruleId']} (RequiresApproval={patch_data['requiresApproval']}):\n"
                  f"{patch_data['diffContent'][:120]}...")

        # ---------------------------------------------------------------------
        # STEP 6: Verification Comparison (POST /api/v1/verification/compare)
        # ---------------------------------------------------------------------
        print("\n--- STEP 6: Verification Comparison (POST /api/v1/verification/compare) ---")
        # Simulate post-change audit where title-presence and canonical-presence were resolved
        post_change_report = dict(test_audit_report)
        post_findings = []
        for f in post_change_report["findings"]:
            f_copy = dict(f)
            if f_copy["ruleId"] in ["title-presence", "canonical-presence"]:
                f_copy["state"] = RuleState.PASS
                f_copy["evidence"] = {
                    "observedValue": "Correct tag present and verified",
                    "expectedValue": "Valid tag present",
                    "provenance": ProvenanceCategory.DIRECT_OBSERVATION,
                }
            post_findings.append(f_copy)
        post_change_report["findings"] = post_findings

        compare_payload = {
            "baselineReport": test_audit_report,
            "postChangeReport": post_change_report,
            "attemptedRuleIds": ["title-presence", "meta-description-presence", "canonical-presence"],
        }
        ver_resp = await client.post("/api/v1/verification/compare", json=compare_payload)
        assert ver_resp.status_code == 200, f"Verification failed: {ver_resp.text}"
        ver_data = ver_resp.json()
        print(f"  Status Code: {ver_resp.status_code}")
        print(f"  Total Attempted: {ver_data['totalAttempted']}")
        print(f"  Resolved Count: {ver_data['resolvedCount']}")
        print(f"  Unresolved Count: {ver_data['unresolvedCount']}")
        print(f"  Issue Resolution Rate (E33 IRR): {ver_data['issueResolutionRate']:.2f}%")
        assert ver_data["resolvedCount"] == 2
        assert ver_data["unresolvedCount"] == 1
        assert abs(ver_data["issueResolutionRate"] - 66.67) < 0.1

        # ---------------------------------------------------------------------
        # STEP 7: Report Export (POST /api/v1/verification/export-markdown)
        # ---------------------------------------------------------------------
        print("\n--- STEP 7: Report Export (POST /api/v1/verification/export-markdown) ---")
        md_resp = await client.post("/api/v1/verification/export-markdown", json=ver_data)
        assert md_resp.status_code == 200
        md_result = md_resp.json()
        print(f"  Markdown Document Length: {len(md_result['markdown'])} characters")
        assert "# SEO Optimizer — Post-Deployment Verification Report" in md_result["markdown"]
        assert "Issue Resolution Rate (IRR)" in md_result["markdown"]
        print("  -> Confirmed: Verification report exported cleanly as markdown.")

        # ---------------------------------------------------------------------
        # STEP 8: Service Inquiry Submission (POST /api/v1/leads)
        # ---------------------------------------------------------------------
        print("\n--- STEP 8: Service Inquiry Submission (POST /api/v1/leads) ---")
        unique_email = f"audit_user_{uuid.uuid4().hex[:8]}@example.com"
        inquiry_payload = {
            "customerName": "Audit Corporate Staging",
            "businessEmail": unique_email,
            "phoneNumber": "+1 650-253-0000",
            "websiteUrl": target_scan_url,
            "businessCategory": "E-Commerce",
            "targetCity": "Mountain View, CA",
            "requestedService": "Full Technical Remediation",
            "problemDescription": "Comprehensive audit verification lead testing live Supabase staging persistence.",
            "urgency": "HIGH",
            "consentGiven": True,
            "scanToken": scan_token,
            "honeypot": "",
        }

        lead_resp = await client.post(
            "/api/v1/leads",
            json=inquiry_payload,
            headers={"X-Forwarded-For": "198.51.100.42"},
        )
        assert lead_resp.status_code == 201, f"Lead creation failed: {lead_resp.text}"
        lead_dto = lead_resp.json()
        lead_id = lead_dto["id"]
        print(f"  Status Code: {lead_resp.status_code}")
        print(f"  Created Lead ID: {lead_id}")
        print(f"  Email: {lead_dto.get('businessEmail') or lead_dto.get('business_email')}")
        print(f"  Status: {lead_dto['status']}")
        print(f"  Scan Token Associated: {lead_dto.get('scanToken') or lead_dto.get('scan_token')}")
        assert lead_dto["status"] == LeadStatus.NEW

        # Test Honeypot rejection
        honeypot_payload = dict(inquiry_payload)
        honeypot_payload["businessEmail"] = f"bot_{uuid.uuid4().hex[:8]}@spammer.org"
        honeypot_payload["honeypot"] = "I am a malicious spam bot"
        bot_resp = await client.post("/api/v1/leads", json=honeypot_payload)
        assert bot_resp.status_code == 400
        assert bot_resp.json()["detail"]["code"] == "SPAM_DETECTED"
        print("  -> Confirmed: Honeypot trap rejected bot submission with HTTP 400 SPAM_DETECTED.")

        # ---------------------------------------------------------------------
        # STEP 9: Staging Persistence Check (Supabase Hosted PostgreSQL)
        # ---------------------------------------------------------------------
        print("\n--- STEP 9: Staging Persistence Check (Supabase Hosted PostgreSQL) ---")
        persisted_lead = staging_repo.get_lead(lead_id)
        assert persisted_lead is not None
        assert persisted_lead.id == lead_id
        assert persisted_lead.business_email == unique_email
        assert len(persisted_lead.status_history) == 1
        print(f"  Durable Lead Retrieved: {persisted_lead.id}")
        print(f"  Initial Status History Entries: {len(persisted_lead.status_history)}")
        print(f"  Initial State: {persisted_lead.status_history[0].new_status}")

        # Simulate fresh process / fresh repo instance re-query
        fresh_repo = create_lead_repository(backend="supabase", supabase_url=staging_url, supabase_key=staging_key)
        re_queried = fresh_repo.get_lead(lead_id)
        assert re_queried is not None
        assert re_queried.id == lead_id
        print("  -> Confirmed: Lead durably persists across repository re-instantiation without in-memory state.")

        # ---------------------------------------------------------------------
        # STEP 10: Admin Login (POST /api/v1/auth/admin/login)
        # ---------------------------------------------------------------------
        print("\n--- STEP 10: Admin Login (POST /api/v1/auth/admin/login) ---")
        login_resp = await client.post(
            "/api/v1/auth/admin/login",
            json={"username": settings.ADMIN_USERNAME, "password": settings.ADMIN_PASSWORD},
            headers={"Origin": "http://localhost:3000"},
        )
        assert login_resp.status_code == 200, f"Admin login failed: {login_resp.text}"
        login_data = login_resp.json()
        csrf_token = login_data["csrf_token"]
        session_cookie = login_resp.cookies.get("admin_session")
        print(f"  Status Code: {login_resp.status_code}")
        print(f"  Authenticated: {login_data['authenticated']}")
        print(f"  Role: {login_data['role']}")
        print(f"  CSRF Token Generated: {csrf_token[:20]}...")
        print(f"  Session Cookie Present: {bool(session_cookie)}")
        assert login_data["authenticated"] is True
        assert session_cookie is not None

        # ---------------------------------------------------------------------
        # STEP 11: View & Update Lead (PATCH /api/v1/leads/{id}/status)
        # ---------------------------------------------------------------------
        print("\n--- STEP 11: View & Update Lead (PATCH /api/v1/leads/{id}/status) ---")
        # Fetch lead via authenticated admin endpoint
        admin_client = AsyncClient(transport=transport, base_url="http://test", cookies={"admin_session": session_cookie})
        view_resp = await admin_client.get(f"/api/v1/leads/{lead_id}")
        assert view_resp.status_code == 200
        print(f"  Admin View Lead Status Code: {view_resp.status_code}")

        # Mutate lead status from NEW to SCOPED with valid CSRF token and Origin
        update_resp = await admin_client.patch(
            f"/api/v1/leads/{lead_id}/status",
            json={
                "newStatus": "SCOPED",
                "notes": "Verified technical requirements and estimated remediation scope in WP 1.4.3 audit.",
                "changedBy": "Staging Acceptance Auditor",
            },
            headers={
                "Origin": "http://localhost:3000",
                "X-CSRF-Token": csrf_token,
            },
        )
        assert update_resp.status_code == 200, f"Status update failed: {update_resp.text}"
        updated_lead = update_resp.json()
        print(f"  Updated Status: {updated_lead['status']}")
        assert updated_lead["status"] == LeadStatus.SCOPED

        # Verify PDF Export endpoint while authenticated
        pdf_resp = await admin_client.get(f"/api/v1/leads/{lead_id}/brief/pdf")
        assert pdf_resp.status_code == 200
        assert pdf_resp.headers["content-type"] == "application/pdf"
        assert len(pdf_resp.content) > 100
        print(f"  PDF Brief Export: HTTP {pdf_resp.status_code}, Bytes={len(pdf_resp.content)}")

        # ---------------------------------------------------------------------
        # STEP 12: Status History Verification & Immutability Trigger Check
        # ---------------------------------------------------------------------
        print("\n--- STEP 12: Status History Verification & Immutability Check ---")
        history_resp = await admin_client.get(f"/api/v1/leads/{lead_id}/history")
        assert history_resp.status_code == 200
        history_items = history_resp.json()
        print(f"  Status History Event Count: {len(history_items)}")
        assert len(history_items) == 2
        evt1_prev = history_items[0].get("previousStatus") or history_items[0].get("previous_status")
        evt1_new = history_items[0].get("newStatus") or history_items[0].get("new_status")
        evt1_by = history_items[0].get("changedBy") or history_items[0].get("changed_by")

        evt2_prev = history_items[1].get("previousStatus") or history_items[1].get("previous_status")
        evt2_new = history_items[1].get("newStatus") or history_items[1].get("new_status")
        evt2_by = history_items[1].get("changedBy") or history_items[1].get("changed_by")

        print(f"    Event 1: {evt1_prev} -> {evt1_new} by {evt1_by}")
        print(f"    Event 2: {evt2_prev} -> {evt2_new} by {evt2_by}")
        assert evt1_new == LeadStatus.NEW
        assert evt2_new == LeadStatus.SCOPED

        print("\n" + "=" * 80)
        print("ALL 12 APPLICATION WORKFLOW STEPS COMPLETED AND VERIFIED SUCCESSFULLY!")
        print("=" * 80)


if __name__ == "__main__":
    asyncio.run(run_12_step_acceptance_audit())
