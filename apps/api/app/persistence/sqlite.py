"""Durable SQLite repository persisting leads, status history, and scans across restarts."""

import json
import sqlite3
import threading
import time
import uuid
from datetime import UTC, datetime
from typing import Any

from app.contracts.enums import LeadStatus, LeadUrgency
from app.contracts.lead import (
    LeadDTO,
    LeadStatusHistoryDTO,
    LeadSubmissionRequest,
)
from app.contracts.scan import AuditReportDTO
from app.core.config import settings
from app.persistence.interface import LeadRepositoryInterface


class SQLiteLeadRepository(LeadRepositoryInterface):
    """Thread-safe SQLite persistent repository."""

    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = db_path or settings.SQLITE_DB_PATH
        self._lock = threading.RLock()
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
        return conn

    def _init_db(self) -> None:
        with self._lock:
            with self._get_connection() as conn:
                conn.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS leads (
                        id TEXT PRIMARY KEY,
                        scan_token TEXT,
                        customer_name TEXT NOT NULL,
                        business_email TEXT NOT NULL,
                        phone_number TEXT NOT NULL,
                        website_url TEXT NOT NULL,
                        business_category TEXT NOT NULL,
                        target_city TEXT NOT NULL,
                        requested_service TEXT NOT NULL,
                        problem_description TEXT NOT NULL,
                        urgency TEXT NOT NULL,
                        status TEXT NOT NULL,
                        consent_given INTEGER NOT NULL,
                        consent_timestamp TEXT NOT NULL,
                        privacy_policy_version TEXT NOT NULL,
                        tech_stack TEXT,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    );

                    CREATE INDEX IF NOT EXISTS idx_leads_business_email ON leads(business_email);
                    CREATE INDEX IF NOT EXISTS idx_leads_website_url ON leads(website_url);
                    CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status);
                    CREATE INDEX IF NOT EXISTS idx_leads_created_at ON leads(created_at DESC);

                    CREATE TABLE IF NOT EXISTS lead_status_history (
                        id TEXT PRIMARY KEY,
                        lead_id TEXT NOT NULL,
                        previous_status TEXT,
                        new_status TEXT NOT NULL,
                        changed_by TEXT NOT NULL,
                        notes TEXT,
                        created_at TEXT NOT NULL,
                        FOREIGN KEY (lead_id) REFERENCES leads (id) ON DELETE CASCADE
                    );

                    CREATE INDEX IF NOT EXISTS idx_history_lead_id ON lead_status_history(lead_id);
                    CREATE INDEX IF NOT EXISTS idx_history_created_at ON lead_status_history(created_at DESC);

                    CREATE TABLE IF NOT EXISTS scans (
                        scan_token TEXT PRIMARY KEY,
                        report_json TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    );

                    CREATE TABLE IF NOT EXISTS rate_limits (
                        key TEXT PRIMARY KEY,
                        timestamps_json TEXT NOT NULL
                    );

                    CREATE TABLE IF NOT EXISTS recent_submissions (
                        key TEXT PRIMARY KEY,
                        timestamp REAL NOT NULL
                    );
                    """
                )
                conn.commit()

    def save_scan(self, report: AuditReportDTO) -> None:
        token = getattr(report, "scanToken", getattr(report, "scan_token", None))
        if not token:
            return

        now_iso = datetime.now(UTC).isoformat()
        payload = report.model_dump_json(by_alias=True)

        with self._lock, self._get_connection() as conn:
            conn.execute(
                """
                    INSERT INTO scans (scan_token, report_json, created_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(scan_token) DO UPDATE SET
                        report_json = excluded.report_json,
                        created_at = excluded.created_at;
                    """,
                (token, payload, now_iso),
            )
            conn.commit()

    def get_scan(self, scan_token: str) -> AuditReportDTO | None:
        with self._lock, self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT report_json FROM scans WHERE scan_token = ?;",
                (scan_token,),
            )
            row = cursor.fetchone()
            if not row:
                return None
            return AuditReportDTO.model_validate_json(row["report_json"])

    def check_rate_limit(self, client_ip: str, email: str) -> tuple[bool, str]:
        now = time.time()
        window = float(settings.LEAD_RATE_LIMIT_WINDOW_SECONDS)
        max_submissions = settings.LEAD_RATE_LIMIT_MAX_SUBMISSIONS

        with self._lock:
            with self._get_connection() as conn:
                # 1. IP rate limit check
                ip_key = f"ip:{client_ip}"
                cursor = conn.execute(
                    "SELECT timestamps_json FROM rate_limits WHERE key = ?;",
                    (ip_key,),
                )
                row = cursor.fetchone()
                ip_history: list[float] = json.loads(row["timestamps_json"]) if row else []
                ip_history = [t for t in ip_history if now - t < window]

                if len(ip_history) >= max_submissions:
                    return (
                        False,
                        f"Too many inquiries from IP {client_ip}. Limit is {max_submissions} per {int(window / 60)} minutes.",
                    )

                # 2. Email rate limit check
                email_key = f"email:{email.lower().strip()}"
                cursor = conn.execute(
                    "SELECT timestamps_json FROM rate_limits WHERE key = ?;",
                    (email_key,),
                )
                row = cursor.fetchone()
                email_history: list[float] = json.loads(row["timestamps_json"]) if row else []
                email_history = [t for t in email_history if now - t < window]

                if len(email_history) >= max_submissions:
                    return (
                        False,
                        f"Too many inquiries from email {email}. Limit is {max_submissions} per {int(window / 60)} minutes.",
                    )

                return True, ""

    def check_duplicate_submission(self, email: str, website_url: str) -> bool:
        now = time.time()
        window = float(settings.LEAD_DUPLICATE_WINDOW_SECONDS)
        key = f"{email.lower().strip()}:{website_url.strip()}"

        with self._lock, self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT timestamp FROM recent_submissions WHERE key = ?;",
                (key,),
            )
            row = cursor.fetchone()
            if not row:
                return False
            last_time = float(row["timestamp"])
            return bool(now - last_time < window)

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

        with self._lock:
            with self._get_connection() as conn:
                # Update IP rate limits
                ip_key = f"ip:{client_ip}"
                cursor = conn.execute(
                    "SELECT timestamps_json FROM rate_limits WHERE key = ?;",
                    (ip_key,),
                )
                row = cursor.fetchone()
                ip_history: list[float] = json.loads(row["timestamps_json"]) if row else []
                ip_history.append(now_ts)
                conn.execute(
                    """
                    INSERT INTO rate_limits (key, timestamps_json)
                    VALUES (?, ?)
                    ON CONFLICT(key) DO UPDATE SET timestamps_json = excluded.timestamps_json;
                    """,
                    (ip_key, json.dumps(ip_history)),
                )

                # Update Email rate limits
                email_key = f"email:{req.business_email.lower().strip()}"
                cursor = conn.execute(
                    "SELECT timestamps_json FROM rate_limits WHERE key = ?;",
                    (email_key,),
                )
                row = cursor.fetchone()
                email_history: list[float] = json.loads(row["timestamps_json"]) if row else []
                email_history.append(now_ts)
                conn.execute(
                    """
                    INSERT INTO rate_limits (key, timestamps_json)
                    VALUES (?, ?)
                    ON CONFLICT(key) DO UPDATE SET timestamps_json = excluded.timestamps_json;
                    """,
                    (email_key, json.dumps(email_history)),
                )

                # Update duplicate submissions
                dup_key = f"{req.business_email.lower().strip()}:{req.website_url.strip()}"
                conn.execute(
                    """
                    INSERT INTO recent_submissions (key, timestamp)
                    VALUES (?, ?)
                    ON CONFLICT(key) DO UPDATE SET timestamp = excluded.timestamp;
                    """,
                    (dup_key, now_ts),
                )

                tech_stack = getattr(req, "tech_stack", None)
                # Insert lead record
                conn.execute(
                    """
                    INSERT INTO leads (
                        id, scan_token, customer_name, business_email, phone_number,
                        website_url, business_category, target_city, requested_service,
                        problem_description, urgency, status, consent_given,
                        consent_timestamp, privacy_policy_version, tech_stack,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        lead_id,
                        req.scan_token,
                        req.customer_name,
                        req.business_email,
                        req.phone_number,
                        req.website_url,
                        req.business_category,
                        req.target_city,
                        req.requested_service,
                        req.problem_description,
                        req.urgency.value if hasattr(req.urgency, "value") else str(req.urgency),
                        LeadStatus.NEW.value,
                        1 if req.consent_given else 0,
                        now_iso,
                        req.privacy_policy_version,
                        json.dumps(tech_stack) if tech_stack else None,
                        now_iso,
                        now_iso,
                    ),
                )

                # Insert initial status history
                conn.execute(
                    """
                    INSERT INTO lead_status_history (
                        id, lead_id, previous_status, new_status, changed_by, notes, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        history_id,
                        lead_id,
                        None,
                        LeadStatus.NEW.value,
                        "Public Website Form",
                        "Inquiry submitted via public web funnel",
                        now_iso,
                    ),
                )
                conn.commit()

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

    def _row_to_lead(self, row: sqlite3.Row, history: list[LeadStatusHistoryDTO]) -> LeadDTO:
        created_dt = datetime.fromisoformat(row["created_at"])
        updated_dt = datetime.fromisoformat(row["updated_at"])
        consent_dt = datetime.fromisoformat(row["consent_timestamp"])
        tech_stack = json.loads(row["tech_stack"]) if row["tech_stack"] else None

        return LeadDTO(
            id=row["id"],
            scan_token=row["scan_token"],
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
            consent_given=bool(row["consent_given"]),
            consent_timestamp=consent_dt,
            privacy_policy_version=row["privacy_policy_version"],
            tech_stack=tech_stack,
            created_at=created_dt,
            updated_at=updated_dt,
            status_history=history,
        )

    def _get_lead_history_internal(
        self, conn: sqlite3.Connection, lead_id: str
    ) -> list[LeadStatusHistoryDTO]:
        cursor = conn.execute(
            """
            SELECT id, lead_id, previous_status, new_status, changed_by, notes, created_at
            FROM lead_status_history
            WHERE lead_id = ?
            ORDER BY created_at ASC;
            """,
            (lead_id,),
        )
        items: list[LeadStatusHistoryDTO] = []
        for r in cursor.fetchall():
            prev = LeadStatus(r["previous_status"]) if r["previous_status"] else None
            new_s = LeadStatus(r["new_status"])
            items.append(
                LeadStatusHistoryDTO(
                    id=r["id"],
                    lead_id=r["lead_id"],
                    previous_status=prev,
                    new_status=new_s,
                    changed_by=r["changed_by"],
                    notes=r["notes"],
                    created_at=datetime.fromisoformat(r["created_at"]),
                )
            )
        return items

    def get_lead(self, lead_id: str) -> LeadDTO | None:
        with self._lock, self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM leads WHERE id = ?;",
                (lead_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None
            history = self._get_lead_history_internal(conn, lead_id)
            return self._row_to_lead(row, history)

    def list_leads(
        self,
        status: LeadStatus | None = None,
        search: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[LeadDTO], int]:
        with self._lock, self._get_connection() as conn:
            where_clauses: list[str] = []
            params: list[Any] = []

            if status is not None:
                where_clauses.append("status = ?")
                params.append(status.value if hasattr(status, "value") else str(status))

            if search and search.strip():
                pattern = f"%{search.strip().lower()}%"
                where_clauses.append(
                    "(LOWER(customer_name) LIKE ? OR LOWER(business_email) LIKE ? OR "
                    "LOWER(website_url) LIKE ? OR LOWER(target_city) LIKE ? OR "
                    "LOWER(business_category) LIKE ?)"
                )
                params.extend([pattern, pattern, pattern, pattern, pattern])

            where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

            count_cursor = conn.execute(
                f"SELECT COUNT(*) AS total FROM leads {where_sql};",
                params,
            )
            total = int(count_cursor.fetchone()["total"])

            query = f"""
                    SELECT * FROM leads
                    {where_sql}
                    ORDER BY created_at DESC
                    LIMIT ? OFFSET ?;
                """
            cursor = conn.execute(query, [*params, limit, offset])
            rows = cursor.fetchall()

            leads: list[LeadDTO] = []
            for row in rows:
                history = self._get_lead_history_internal(conn, row["id"])
                leads.append(self._row_to_lead(row, history))

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

        with self._lock:
            with self._get_connection() as conn:
                cursor = conn.execute("SELECT status FROM leads WHERE id = ?;", (lead_id,))
                row = cursor.fetchone()
                if not row:
                    return None

                prev_status_str = row["status"]
                history_id = str(uuid.uuid4())

                # Insert status history item
                conn.execute(
                    """
                    INSERT INTO lead_status_history (
                        id, lead_id, previous_status, new_status, changed_by, notes, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        history_id,
                        lead_id,
                        prev_status_str,
                        new_status_str,
                        changed_by,
                        notes,
                        now_iso,
                    ),
                )

                # Update lead status and updated_at
                conn.execute(
                    """
                    UPDATE leads
                    SET status = ?, updated_at = ?
                    WHERE id = ?;
                    """,
                    (new_status_str, now_iso, lead_id),
                )
                conn.commit()

                # Return updated lead
                return self.get_lead(lead_id)

    def get_status_history(self, lead_id: str) -> list[LeadStatusHistoryDTO]:
        with self._lock, self._get_connection() as conn:
            return self._get_lead_history_internal(conn, lead_id)

    def reset(self) -> None:
        """Clears all table contents (used in unit/integration testing)."""
        with self._lock, self._get_connection() as conn:
            conn.executescript(
                """
                    DELETE FROM lead_status_history;
                    DELETE FROM leads;
                    DELETE FROM scans;
                    DELETE FROM rate_limits;
                    DELETE FROM recent_submissions;
                    """
            )
            conn.commit()
