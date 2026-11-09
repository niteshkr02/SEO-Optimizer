"""Unit tests verifying repository factory production startup safety and fallback policies."""

import pytest

from app.core.config import settings
from app.persistence.factory import create_lead_repository
from app.persistence.in_memory import InMemoryLeadRepository
from app.persistence.sqlite import SQLiteLeadRepository


def test_factory_returns_in_memory_when_configured():
    repo = create_lead_repository(backend="in_memory")
    assert isinstance(repo, InMemoryLeadRepository)


def test_factory_returns_sqlite_by_default(tmp_path):
    db_file = str(tmp_path / "test.db")
    repo = create_lead_repository(backend="sqlite", db_path=db_file)
    assert isinstance(repo, SQLiteLeadRepository)


def test_factory_fails_in_production_if_supabase_credentials_missing(monkeypatch):
    """In production environment, missing Supabase credentials MUST raise RuntimeError, not silently fall back."""
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(settings, "SUPABASE_URL", None)
    monkeypatch.setattr(settings, "SUPABASE_SERVICE_ROLE_KEY", None)

    with pytest.raises(RuntimeError) as exc_info:
        create_lead_repository(backend="supabase")

    assert "Production startup failure" in str(exc_info.value)
    assert "Refusing silent fallback to local SQLite" in str(exc_info.value)


def test_factory_falls_back_in_development_if_supabase_credentials_missing(monkeypatch, tmp_path):
    """In development/test environment, missing Supabase credentials falls back to SQLite with warning."""
    monkeypatch.setattr(settings, "ENVIRONMENT", "development")
    monkeypatch.setattr(settings, "SUPABASE_URL", None)
    monkeypatch.setattr(settings, "SUPABASE_SERVICE_ROLE_KEY", None)
    db_file = str(tmp_path / "dev_fallback.db")

    repo = create_lead_repository(backend="supabase", db_path=db_file)
    assert isinstance(repo, SQLiteLeadRepository)
