"""Health check and system telemetry endpoint."""

from typing import Any

from fastapi import APIRouter

from app.core.config import settings

router = APIRouter()


@router.get("/health", response_model=dict[str, Any])
async def health_check() -> dict[str, Any]:
    """Returns platform operational health and active component versions."""
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "ruleset_version": settings.RULESET_VERSION,
        "scoring_model_version": settings.SCORING_MODEL_VERSION,
        "ssrf_protection_enforced": settings.ENFORCE_SSRF_PROTECTION,
    }
