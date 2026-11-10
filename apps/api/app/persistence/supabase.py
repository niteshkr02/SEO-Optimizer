"""Supabase PostgreSQL repository adapter using PostgREST endpoints and server-only credentials."""

import logging
import re
import time
import uuid
from datetime import UTC, datetime
from typing import Any

import httpx

from app.contracts.enums import LeadStatus, LeadUrgency
from app.contracts.lead import (
    LeadDTO,
    LeadStatusHistoryDTO,
    LeadSubmissionRequest,
)
from app.contracts.scan import AuditReportDTO
from app.core.config import settings
from app.persistence.interface import LeadRepositoryInterface

logger = logging.getLogger(__name__)


class SupabaseLeadRepository(LeadRepositoryInterface):
    """Server-side repository communicating with Supabase PostgreSQL via PostgREST.
    
    Security Guarantee:
    Requires server-side SUPABASE_SERVICE_ROLE_KEY. Never expose this key or adapter
    to browser clients.
    """

    def __init__(
        self,
        supabase_url: str | None = None,
        service_role_key: str | None = None,
        timeout: float = 10.0,
    ) -> None:
        self.supabase_url = (supabase_url or settings.SUPABASE_URL or "").rstrip("/")
        self.service_role_key = service_role_key or settings.SUPABASE_SERVICE_ROLE_KEY or ""
        self.timeout = timeout

        if not self.supabase_url or not self.service_role_key:
            raise ValueError(
                "SupabaseLeadRepository requires SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY to be configured."
            )

        self._headers = {
            "apikey": self.service_role_key,
            "Authorization": f"Bearer {self.service_role_key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }
        # In-memory auxiliary cache for scans if scans table is not provisioned
        self._scans_cache: dict[str, AuditReportDTO] = {}

    def _client(self) -> httpx.Client:
        return httpx.Client(
            base_url=f"{self.supabase_url}/rest/v1",
            headers=self._headers,
            timeout=self.timeout,
        )

    def save_scan(self, report: AuditReportDTO) -> None:
        token = getattr(report, "scanToken", getattr(report, "scan_token", None))
        if token:
            self._scans_cache[token] = report

    def get_scan(self, scan_token: str) -> AuditReportDTO | None:
        return self._scans_cache.get(scan_token)

    def check_rate_limit(
        self,
        client_ip: str,
        email: str,
        record: bool = False,
    ) -> tuple[bool, str]:
        now = time.time()
        window = float(settings.LEAD_RATE_LIMIT_WINDOW_SECONDS)
        max_submissions = settings.LEAD_RATE_LIMIT_MAX_SUBMISSIONS

        ip_key = f"ip:{client_ip}"
        email_key = f"email:{email.lower().strip()}"

        with self._client() as client:
            # 1. Attempt atomic RPC check_and_record_rate_limit
            try:
                ip_resp = client.post(
                    "/rpc/check_and_record_rate_limit",
                    json={
                        "p_rate_key": ip_key,
                        "p_now": now,
                        "p_window_seconds": window,
                        "p_max_submissions": max_submissions,
                        "p_record": record,
                    },
                )
                if ip_resp.status_code == 200:
                    if not ip_resp.json():
                        return (
                            False,
                            f"Too many inquiries from IP {client_ip}. Limit is {max_submissions} per {int(window / 60)} minutes.",
                        )

                    email_resp = client.post(
                        "/rpc/check_and_record_rate_limit",
                        json={
                            "p_rate_key": email_key,
                            "p_now": now,
                            "p_window_seconds": window,
                            "p_max_submissions": max_submissions,
                            "p_record": record,
                        },
                    )
                    if email_resp.status_code == 200:
                        if not email_resp.json():
                            return (
                                False,
                                f"Too many inquiries from email {email}. Limit is {max_submissions} per {int(window / 60)} minutes.",
                            )
                        return True, ""
            except httpx.HTTPError as exc:
                logger.warning(
                    "Error calling check_and_record_rate_limit RPC: %s; falling back to table query",
                    exc,
                )

            # Fallback to query rate limits table if RPC is not provisioned or failed
            resp = client.get(
                "/rate_limits",
                params={"rate_key": f"in.(ip:{client_ip},email:{email.lower().strip()})"},
            )
            if resp.status_code == 200:
                rows = resp.json()
                for row in rows:
                    key = row.get("rate_key", "")
                    ts_list = [
                        float(t)
                        for t in row.get("timestamps", [])
                        if now - float(t) < window
                    ]
                    if len(ts_list) >= max_submissions:
                        if key.startswith("ip:"):
                            return (
                                False,
                                f"Too many inquiries from IP {client_ip}. Limit is {max_submissions} per {int(window / 60)} minutes.",
                            )
                        return (
                            False,
                            f"Too many inquiries from email {email}. Limit is {max_submissions} per {int(window / 60)} minutes.",
                        )

        return True, ""

    def check_duplicate_submission(self, email: str, website_url: str) -> bool:
        now = datetime.now(UTC)
        window = float(settings.LEAD_DUPLICATE_WINDOW_SECONDS)

        with self._client() as client:
            resp = client.get(
                "/leads",
                params={
                    "business_email": f"eq.{email.lower().strip()}",
                    "website_url": f"eq.{website_url.strip()}",
                    "order": "created_at.desc",
                    "limit": "1",
                },
            )
            if resp.status_code == 200:
                rows = resp.json()
                if rows:
                    last_created = datetime.fromisoformat(rows[0]["created_at"])
                    diff = (now - last_created).total_seconds()
                    if diff < window:
                        return True
        return False

    def create_lead(
        self,
        req: LeadSubmissionRequest,
        client_ip: str = "127.0.0.1",
    ) -> LeadDTO:
        now_dt = datetime.now(UTC)
        now_iso = now_dt.isoformat()
        now_ts = time.time()

        lead_id = str(uuid.uuid4())
        history_id = str(uuid.uuid4())

        initial_history = LeadStatusHistoryDTO(
            id=history_id,
            lead_id=lead_id,
            previous_status=None,
            new_status=LeadStatus.NEW,
            changed_by="Public Website Form",
            notes="Inquiry submitted via public web funnel",
            created_at=now_dt,
        )

        with self._client() as client:
            # 1. Update distributed rate limits atomically via RPC
            ip_key = f"ip:{client_ip}"
            email_key = f"email:{req.business_email.lower().strip()}"
            for k in [ip_key, email_key]:
                recorded = False
                try:
                    rpc_resp = client.post(
                        "/rpc/check_and_record_rate_limit",
                        json={
                            "p_rate_key": k,
                            "p_now": now_ts,
                            "p_window_seconds": float(settings.LEAD_RATE_LIMIT_WINDOW_SECONDS),
                            "p_max_submissions": settings.LEAD_RATE_LIMIT_MAX_SUBMISSIONS,
                            "p_record": True,
                        },
                    )
                    if rpc_resp.status_code == 200:
                        recorded = True
                except httpx.HTTPError as exc:
                    logger.warning("Atomic RPC call in create_lead failed for key %s: %s", k, exc)

                if not recorded:
                    # Fallback to merge-duplicates if RPC not yet provisioned
                    r = client.get("/rate_limits", params={"rate_key": f"eq.{k}"})
                    existing = r.json() if r.status_code == 200 and r.json() else []
                    current_ts = existing[0].get("timestamps", []) if existing else []
                    current_ts.append(now_ts)
                    client.post(
                        "/rate_limits",
                        headers={"Prefer": "resolution=merge-duplicates"},
                        json={"rate_key": k, "timestamps": current_ts, "updated_at": now_iso},
                    )

            # 2. Insert Lead
            lead_payload = {
                "id": lead_id,
                "scan_token": req.scan_token,
                "customer_name": req.customer_name,
                "business_email": req.business_email,
                "phone_number": req.phone_number,
                "website_url": req.website_url,
                "business_category": req.business_category,
                "target_city": req.target_city,
                "requested_service": req.requested_service,
                "problem_description": req.problem_description,
                "urgency": req.urgency.value if hasattr(req.urgency, "value") else str(req.urgency),
                "status": LeadStatus.NEW.value,
                "consent_given": req.consent_given,
                "consent_timestamp": now_iso,
                "privacy_policy_version": req.privacy_policy_version,
                "tech_stack": getattr(req, "tech_stack", None),
                "created_at": now_iso,
                "updated_at": now_iso,
            }
            lead_resp = client.post("/leads", json=lead_payload)
            lead_resp.raise_for_status()

            # 3. Insert Initial History
            history_payload = {
                "id": history_id,
                "lead_id": lead_id,
                "previous_status": None,
                "new_status": LeadStatus.NEW.value,
                "changed_by": "Public Website Form",
                "notes": "Inquiry submitted via public web funnel",
                "created_at": now_iso,
            }
            client.post("/lead_status_history", json=history_payload)

        return LeadDTO(
            id=lead_id,
            scan_token=req.scan_token,
            customer_name=req.customer_name,
            business_email=req.business_email,
            phone_number=req.phone_number,
            website_url=req.website_url,
            business_category=req.business_category,
            target_city=req.target_city,
            requested_service=req.requested_service,
            problem_description=req.problem_description,
            urgency=req.urgency,
            status=LeadStatus.NEW,
            consent_given=req.consent_given,
            consent_timestamp=now_dt,
            privacy_policy_version=req.privacy_policy_version,
            tech_stack=getattr(req, "tech_stack", None),
            created_at=now_dt,
            updated_at=now_dt,
            status_history=[initial_history],
        )

    def _parse_lead_dict(self, row: dict[str, Any]) -> LeadDTO:
        history_raw = row.get("lead_status_history") or []
        history = [
            LeadStatusHistoryDTO(
                id=h["id"],
                lead_id=h["lead_id"],
                previous_status=LeadStatus(h["previous_status"]) if h.get("previous_status") else None,
                new_status=LeadStatus(h["new_status"]),
                changed_by=h["changed_by"],
                notes=h.get("notes"),
                created_at=datetime.fromisoformat(h["created_at"]),
            )
            for h in history_raw
        ]
        history.sort(key=lambda x: x.created_at)

        return LeadDTO(
            id=row["id"],
            scan_token=row.get("scan_token"),
            customer_name=row["customer_name"],
            business_email=row["business_email"],
            phone_number=row["phone_number"],
            website_url=row["website_url"],
            business_category=row["business_category"],
            target_city=row["target_city"],
            requested_service=row["requested_service"],
            problem_description=row["problem_description"],
            urgency=LeadUrgency(row["urgency"]),
            status=LeadStatus(row["status"]),
            consent_given=row["consent_given"],
            consent_timestamp=datetime.fromisoformat(row["consent_timestamp"]),
            privacy_policy_version=row["privacy_policy_version"],
            tech_stack=row.get("tech_stack"),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            status_history=history,
        )

    def get_lead(self, lead_id: str) -> LeadDTO | None:
        with self._client() as client:
            resp = client.get(
                "/leads",
                params={"id": f"eq.{lead_id}", "select": "*,lead_status_history(*)"},
            )
            if resp.status_code == 200:
                rows = resp.json()
                if rows:
                    return self._parse_lead_dict(rows[0])
        return None

    def list_leads(
        self,
        status: LeadStatus | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[LeadDTO], int]:
        params: dict[str, str] = {
            "select": "*,lead_status_history(*)",
            "order": "created_at.desc",
            "limit": str(limit),
            "offset": str(offset),
        }

        if status is not None:
            params["status"] = f"eq.{status.value if hasattr(status, 'value') else str(status)}"

        if search and search.strip():
            # Sanitize search term to prevent PostgREST grammar breakdown on commas and parentheses
            clean_q = re.sub(r'[,()"]', " ", search).strip()
            if clean_q:
                params["or"] = (
                    f"(customer_name.ilike.*{clean_q}*,business_email.ilike.*{clean_q}*,"
                    f"website_url.ilike.*{clean_q}*,target_city.ilike.*{clean_q}*,business_category.ilike.*{clean_q}*)"
                )

        headers = dict(self._headers)
        headers["Prefer"] = "count=exact"

        with httpx.Client(
            base_url=f"{self.supabase_url}/rest/v1",
            headers=headers,
            timeout=self.timeout,
        ) as client:
            resp = client.get("/leads", params=params)
            resp.raise_for_status()

            rows = resp.json()
            # PostgREST returns total count in Content-Range header: "0-9/42"
            content_range = resp.headers.get("Content-Range", "")
            total = len(rows)
            if "/" in content_range:
                try:
                    total = int(content_range.split("/")[1])
                except ValueError:
                    pass

            leads = [self._parse_lead_dict(r) for r in rows]
            return leads, total

    def update_lead_status(
        self,
        lead_id: str,
        new_status: LeadStatus,
        changed_by: str,
        notes: str | None = None,
    ) -> LeadDTO | None:
        now_dt = datetime.now(UTC)
        now_iso = now_dt.isoformat()
        new_status_str = new_status.value if hasattr(new_status, "value") else str(new_status)

        current = self.get_lead(lead_id)
        if not current:
            return None

        prev_status_str = current.status.value if hasattr(current.status, "value") else str(current.status)

        with self._client() as client:
            # Insert status history record
            history_payload = {
                "id": str(uuid.uuid4()),
                "lead_id": lead_id,
                "previous_status": prev_status_str,
                "new_status": new_status_str,
                "changed_by": changed_by,
                "notes": notes,
                "created_at": now_iso,
            }
            client.post("/lead_status_history", json=history_payload)

            # Update lead record
            client.patch(
                "/leads",
                params={"id": f"eq.{lead_id}"},
                json={"status": new_status_str, "updated_at": now_iso},
            )

        return self.get_lead(lead_id)

    def get_status_history(self, lead_id: str) -> list[LeadStatusHistoryDTO]:
        with self._client() as client:
            resp = client.get(
                "/lead_status_history",
                params={"lead_id": f"eq.{lead_id}", "order": "created_at.asc"},
            )
            if resp.status_code == 200:
                rows = resp.json()
                return [
                    LeadStatusHistoryDTO(
                        id=h["id"],
                        lead_id=h["lead_id"],
                        previous_status=LeadStatus(h["previous_status"]) if h.get("previous_status") else None,
                        new_status=LeadStatus(h["new_status"]),
                        changed_by=h["changed_by"],
                        notes=h.get("notes"),
                        created_at=datetime.fromisoformat(h["created_at"]),
                    )
                    for h in rows
                ]
        return []

    def reset(self) -> None:
        """Cleans test rows in test database."""
        self._scans_cache.clear()
        with self._client() as client:
            client.delete("/lead_status_history", params={"id": "not.is.null"})
            client.delete("/leads", params={"id": "not.is.null"})
            client.delete("/rate_limits", params={"rate_key": "not.is.null"})
