"""Global repository instance and backward-compatible persistence exports."""

from app.persistence.factory import create_lead_repository
from app.persistence.in_memory import InMemoryLeadRepository
from app.persistence.interface import LeadRepositoryInterface
from app.persistence.sqlite import SQLiteLeadRepository
from app.persistence.supabase import SupabaseLeadRepository

# Backward compatibility alias
LeadRepository = InMemoryLeadRepository

# Singleton repository configured by settings
lead_repository: LeadRepositoryInterface = create_lead_repository()

__all__ = [
    "InMemoryLeadRepository",
    "LeadRepository",
    "LeadRepositoryInterface",
    "SQLiteLeadRepository",
    "SupabaseLeadRepository",
    "create_lead_repository",
    "lead_repository",
]
