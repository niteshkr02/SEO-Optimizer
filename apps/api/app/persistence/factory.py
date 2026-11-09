"""Factory for instantiating the configured lead persistence repository adapter."""

import logging

from app.core.config import settings
from app.persistence.in_memory import InMemoryLeadRepository
from app.persistence.interface import LeadRepositoryInterface
from app.persistence.sqlite import SQLiteLeadRepository
from app.persistence.supabase import SupabaseLeadRepository

logger = logging.getLogger(__name__)


def create_lead_repository(
    backend: str | None = None,
    db_path: str | None = None,
    supabase_url: str | None = None,
    supabase_key: str | None = None,
) -> LeadRepositoryInterface:
    """Creates a repository instance based on explicit parameters or app settings."""
    selected_backend = (backend or settings.PERSISTENCE_BACKEND).lower().strip()

    if selected_backend == "supabase":
        url = supabase_url or settings.SUPABASE_URL
        key = supabase_key or settings.SUPABASE_SERVICE_ROLE_KEY
        if url and key:
            logger.info("Initializing SupabaseLeadRepository adapter")
            return SupabaseLeadRepository(supabase_url=url, service_role_key=key)
        logger.warning(
            "Supabase credentials missing (SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY). "
            "Falling back to durable SQLite repository."
        )
        return SQLiteLeadRepository(db_path=db_path or settings.SQLITE_DB_PATH)

    if selected_backend == "in_memory":
        logger.info("Initializing InMemoryLeadRepository adapter (ephemeral)")
        return InMemoryLeadRepository()

    # Default to durable SQLite
    logger.info("Initializing SQLiteLeadRepository adapter at %s", db_path or settings.SQLITE_DB_PATH)
    return SQLiteLeadRepository(db_path=db_path or settings.SQLITE_DB_PATH)

