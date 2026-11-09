"""Post-deployment audit verification endpoints."""

from fastapi import APIRouter, Response, status
from pydantic import BaseModel, Field

from app.contracts.scan import AuditReportDTO
from app.verification.engine import default_verification_engine
from app.verification.models import VerificationReportDTO

router = APIRouter()


class VerificationCompareRequest(BaseModel):
    """Payload for comparing baseline and post-change audits."""

    baselineReport: AuditReportDTO = Field(
        ..., description="Baseline audit report snapshot."
    )
    postChangeReport: AuditReportDTO = Field(
        ..., description="Post-remediation audit report snapshot."
    )
    attemptedRuleIds: list[str] | None = Field(
        default=None,
        description="Optional list of specific rule IDs attempted for remediation.",
    )


class MarkdownExportResponse(BaseModel):
    """Container for exported Markdown verification report."""

    markdown: str = Field(..., description="Markdown report text.")


@router.post(
    "/verification/compare",
    response_model=VerificationReportDTO,
    status_code=status.HTTP_200_OK,
    summary="Compare baseline and post-change audit reports",
)
async def compare_audit_reports(
    request: VerificationCompareRequest,
) -> VerificationReportDTO:
    """Executes deterministic before-and-after audit verification (Model E33)."""
    return default_verification_engine.compare_reports(
        baseline_report=request.baselineReport,
        post_change_report=request.postChangeReport,
        attempted_rule_ids=request.attemptedRuleIds,
    )


@router.post(
    "/verification/export-markdown",
    response_model=MarkdownExportResponse,
    status_code=status.HTTP_200_OK,
    summary="Export verification report as Markdown document",
)
async def export_verification_markdown(
    report: VerificationReportDTO,
) -> MarkdownExportResponse:
    """Renders a verification report into a GitHub-flavored Markdown document."""
    md_text = default_verification_engine.export_markdown_report(report)
    return MarkdownExportResponse(markdown=md_text)


@router.post(
    "/verification/export-markdown/raw",
    response_class=Response,
    status_code=status.HTTP_200_OK,
    summary="Export verification report as raw text/markdown stream",
)
async def export_verification_markdown_raw(
    report: VerificationReportDTO,
) -> Response:
    """Returns raw text/markdown file stream."""
    md_text = default_verification_engine.export_markdown_report(report)
    return Response(content=md_text, media_type="text/markdown")

