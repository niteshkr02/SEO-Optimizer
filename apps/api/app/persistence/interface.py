"""Repository interface protocol for leads, scans, and audit trail persistence."""

from typing import Protocol, runtime_checkable

from app.contracts.enums import LeadStatus
from app.contracts.lead import (
    LeadDTO,
    LeadStatusHistoryDTO,
    LeadSubmissionRequest,
)
from app.contracts.scan import AuditReportDTO


@runtime_checkable
class LeadRepositoryInterface(Protocol):
    """Protocol defining persistence operations for leads, status history, and scans."""

    def save_scan(self, report: AuditReportDTO) -> None:
        """Stores an audit report indexed by scan token."""
        ...

    def get_scan(self, scan_token: str) -> AuditReportDTO | None:
        """Retrieves an audit report by scan token."""
        ...

    def check_rate_limit(self, client_ip: str, email: str) -> tuple[bool, str]:
        """Checks sliding-window rate limit for a client IP and business email."""
        ...

    def check_duplicate_submission(self, email: str, website_url: str) -> bool:
        """Flags rapid duplicate submissions for identical email and target URL."""
        ...

    def create_lead(
        self,
        req: LeadSubmissionRequest,
        client_ip: str = "127.0.0.1",
    ) -> LeadDTO:
        """Persists a new validated lead and initializes status history."""
        ...

    def get_lead(self, lead_id: str) -> LeadDTO | None:
        """Retrieves a single lead by ID, including complete status history."""
        ...

    def list_leads(
        self,
        status: LeadStatus | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[LeadDTO], int]:
        """Returns filtered, paginated leads alongside the total match count."""
        ...

    def update_lead_status(
        self,
        lead_id: str,
        new_status: LeadStatus,
        changed_by: str,
        notes: str | None = None,
    ) -> LeadDTO | None:
        """Updates lead status and appends an immutable audit history item."""
        ...

    def get_status_history(self, lead_id: str) -> list[LeadStatusHistoryDTO]:
        """Retrieves the complete status change audit trail for a lead."""
        ...

    def reset(self) -> None:
        """Clears or resets state for test isolation."""
        ...

