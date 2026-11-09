"""Thread-safe in-memory repository for unit tests and local ephemeral execution."""

import threading
import time
import uuid
from datetime import UTC, datetime

from app.contracts.enums import LeadStatus
from app.contracts.lead import (
    LeadDTO,
    LeadStatusHistoryDTO,
    LeadSubmissionRequest,
)
from app.contracts.scan import AuditReportDTO
from app.core.config import settings
from app.persistence.interface import LeadRepositoryInterface


class InMemoryLeadRepository(LeadRepositoryInterface):
    """In-memory thread-safe repository matching the lead storage lifecycle."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._scans: dict[str, AuditReportDTO] = {}
        self._leads: dict[str, LeadDTO] = {}
        self._status_history: dict[str, list[LeadStatusHistoryDTO]] = {}
        self._rate_limits: dict[str, list[float]] = {}
        self._recent_submissions: dict[str, float] = {}

    def save_scan(self, report: AuditReportDTO) -> None:
        token = getattr(report, "scanToken", getattr(report, "scan_token", None))
        if token:
            with self._lock:
                self._scans[token] = report

    def get_scan(self, scan_token: str) -> AuditReportDTO | None:
        with self._lock:
            return self._scans.get(scan_token)

    def check_rate_limit(self, client_ip: str, email: str) -> tuple[bool, str]:
        now = time.time()
        window = float(settings.LEAD_RATE_LIMIT_WINDOW_SECONDS)
        max_submissions = settings.LEAD_RATE_LIMIT_MAX_SUBMISSIONS

        with self._lock:
            ip_key = f"ip:{client_ip}"
            ip_history = [t for t in self._rate_limits.get(ip_key, []) if now - t < window]
            if len(ip_history) >= max_submissions:
                return False, f"Too many inquiries from IP {client_ip}. Limit is {max_submissions} per {int(window / 60)} minutes."
            self._rate_limits[ip_key] = ip_history

            email_key = f"email:{email.lower().strip()}"
            email_history = [t for t in self._rate_limits.get(email_key, []) if now - t < window]
            if len(email_history) >= max_submissions:
                return False, f"Too many inquiries from email {email}. Limit is {max_submissions} per {int(window / 60)} minutes."
            self._rate_limits[email_key] = email_history

            return True, ""

    def check_duplicate_submission(self, email: str, website_url: str) -> bool:
        now = time.time()
        window = float(settings.LEAD_DUPLICATE_WINDOW_SECONDS)
        key = f"{email.lower().strip()}:{website_url.strip()}"

        with self._lock:
            last_time = self._recent_submissions.get(key)
            return bool(last_time and (now - last_time < window))

    def create_lead(
        self,
        req: LeadSubmissionRequest,
        client_ip: str = "127.0.0.1",
    ) -> LeadDTO:
        now_dt = datetime.now(UTC)
        now_ts = time.time()

        with self._lock:
            ip_key = f"ip:{client_ip}"
            email_key = f"email:{req.business_email.lower().strip()}"
            self._rate_limits.setdefault(ip_key, []).append(now_ts)
            self._rate_limits.setdefault(email_key, []).append(now_ts)

            dup_key = f"{req.business_email.lower().strip()}:{req.website_url.strip()}"
            self._recent_submissions[dup_key] = now_ts

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

            lead = LeadDTO(
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
                created_at=now_dt,
                updated_at=now_dt,
                status_history=[initial_history],
            )

            self._leads[lead_id] = lead
            self._status_history[lead_id] = [initial_history]
            return lead

    def get_lead(self, lead_id: str) -> LeadDTO | None:
        with self._lock:
            lead = self._leads.get(lead_id)
            if not lead:
                return None
            history = self._status_history.get(lead_id, [])
            return lead.model_copy(update={"status_history": history})

    def list_leads(
        self,
        status: LeadStatus | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[LeadDTO], int]:
        with self._lock:
            all_leads = list(self._leads.values())

            if status is not None:
                all_leads = [lead for lead in all_leads if lead.status == status]

            if search and search.strip():
                q = search.lower().strip()
                all_leads = [
                    lead
                    for lead in all_leads
                    if (
                        q in lead.customer_name.lower()
                        or q in lead.business_email.lower()
                        or q in lead.website_url.lower()
                        or q in lead.target_city.lower()
                        or q in lead.business_category.lower()
                    )
                ]

            all_leads.sort(key=lambda x: x.created_at, reverse=True)

            total = len(all_leads)
            paginated = all_leads[offset : offset + limit]

            result = [
                lead.model_copy(
                    update={"status_history": self._status_history.get(lead.id, [])}
                )
                for lead in paginated
            ]
            return result, total

    def update_lead_status(
        self,
        lead_id: str,
        new_status: LeadStatus,
        changed_by: str,
        notes: str | None = None,
    ) -> LeadDTO | None:
        now_dt = datetime.now(UTC)

        with self._lock:
            lead = self._leads.get(lead_id)
            if not lead:
                return None

            prev_status = lead.status
            history_item = LeadStatusHistoryDTO(
                id=str(uuid.uuid4()),
                lead_id=lead_id,
                previous_status=prev_status,
                new_status=new_status,
                changed_by=changed_by,
                notes=notes,
                created_at=now_dt,
            )

            updated_history = self._status_history.setdefault(lead_id, [])
            updated_history.append(history_item)

            updated_lead = lead.model_copy(
                update={
                    "status": new_status,
                    "updated_at": now_dt,
                    "status_history": updated_history,
                }
            )
            self._leads[lead_id] = updated_lead
            return updated_lead

    def get_status_history(self, lead_id: str) -> list[LeadStatusHistoryDTO]:
        with self._lock:
            return list(self._status_history.get(lead_id, []))

    def reset(self) -> None:
        with self._lock:
            self._scans.clear()
            self._leads.clear()
            self._status_history.clear()
            self._rate_limits.clear()
            self._recent_submissions.clear()

