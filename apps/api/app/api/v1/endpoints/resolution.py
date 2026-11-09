"""Resolution planning endpoints."""

from fastapi import APIRouter, status

from app.contracts.scan import AuditReportDTO
from app.resolution.generator import ResolutionGenerator
from app.resolution.models import ResolutionPlanDTO

router = APIRouter()
generator = ResolutionGenerator()


@router.post(
    "/resolution/plan",
    response_model=ResolutionPlanDTO,
    status_code=status.HTTP_200_OK,
    summary="Generate evidence-backed deterministic resolution plan",
)
async def generate_resolution_plan(report: AuditReportDTO) -> ResolutionPlanDTO:
    """Generates an evidence-backed resolution plan and reviewable code patches from audit findings."""
    return generator.generate_plan(report)

