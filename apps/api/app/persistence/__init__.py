"""Persistence layer exports."""

from app.persistence.factory import create_lead_repository
from app.persistence.in_memory import InMemoryLeadRepository
from app.persistence.interface import LeadRepositoryInterface
from app.persistence.repository import LeadRepository, lead_repository
from app.persistence.sqlite import SQLiteLeadRepository
from app.persistence.supabase import SupabaseLeadRepository

__all__ = [
    "InMemoryLeadRepository",
    "LeadRepository",
    "LeadRepositoryInterface",
    "SQLiteLeadRepository",
    "SupabaseLeadRepository",
    "create_lead_repository",
    "lead_repository",
]
