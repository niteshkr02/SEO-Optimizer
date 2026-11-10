"""API v1 router composition."""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    crawl,
    health,
    leads,
    resolution,
    scan,
    verification,
)

api_router = APIRouter()
api_router.include_router(health.router, tags=["Health"])
api_router.include_router(auth.router, tags=["Authentication"])
api_router.include_router(scan.router, tags=["Scan"])
api_router.include_router(crawl.router, tags=["Crawl"])
api_router.include_router(resolution.router, tags=["Resolution"])
api_router.include_router(verification.router, tags=["Verification"])
api_router.include_router(leads.router, tags=["Leads"])

