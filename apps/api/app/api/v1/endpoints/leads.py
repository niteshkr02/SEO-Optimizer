"""Versioned FastAPI endpoints for lead capture, consultation management, and exports."""


from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Request,
    Response,
    status,
)

from app.contracts.brief import ServiceBriefDTO
from app.contracts.enums import LeadStatus
from app.contracts.lead import (
    LeadDTO,
    LeadListResponse,
    LeadStatusHistoryDTO,
    LeadStatusUpdateRequest,
    LeadSubmissionRequest,
)
from app.core.security import verify_admin_key
from app.leads.brief_generator import ServiceBriefGenerator
from app.persistence.repository import lead_repository

router = APIRouter()
brief_generator = ServiceBriefGenerator()


def get_client_ip(request: Request) -> str:
    """Extracts client IP address safely, checking X-Forwarded-For if available."""
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "127.0.0.1"


# -----------------------------------------------------------------------------
# Public Lead Capture
# -----------------------------------------------------------------------------


@router.post(
    "/leads",
    response_model=LeadDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Submit technical SEO service inquiry",
    description="Public endpoint to capture client service inquiries, enforcing rate limiting and honeypot spam protection.",
)
async def submit_lead(
    request: Request,
    lead_in: LeadSubmissionRequest,
) -> LeadDTO:
    """Captures and securely persists a client service inquiry."""
    # 1. Honeypot check (anti-bot protection)
    if lead_in.honeypot is not None and lead_in.honeypot.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "SPAM_DETECTED", "message": "Automated submission rejected."},
        )

    client_ip = get_client_ip(request)

    # 2. Duplicate submission protection
    if lead_repository.check_duplicate_submission(
        lead_in.business_email, lead_in.website_url
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "DUPLICATE_SUBMISSION",
                "message": (
                    "A consultation inquiry for this email and website was submitted recently. "
                    "Our engineering team is already reviewing it."
                ),
            },
        )

    # 3. Rate limiting (sliding window per IP & email)
    allowed, rate_msg = lead_repository.check_rate_limit(
        client_ip, lead_in.business_email
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"code": "RATE_LIMIT_EXCEEDED", "message": rate_msg},
        )

    # 4. Create and persist lead record
    created_lead = lead_repository.create_lead(lead_in, client_ip=client_ip)
    return created_lead


# -----------------------------------------------------------------------------
# Admin Lead Management (Protected by Server-Side Authorization)
# -----------------------------------------------------------------------------


@router.get(
    "/leads",
    response_model=LeadListResponse,
    dependencies=[Depends(verify_admin_key)],
    summary="List all captured leads (Admin)",
    description="Returns filtered and paginated leads. Requires administrative authorization.",
)
async def list_leads(
    status_filter: Annotated[LeadStatus | None, Query(alias="status", description="Filter by status")] = None,
    search: Annotated[str | None, Query(description="Search by name, email, URL, or city")] = None,
    limit: Annotated[int, Query(ge=1, le=200, description="Page size limit")] = 50,
    offset: Annotated[int, Query(ge=0, description="Page offset")] = 0,
) -> LeadListResponse:
    """Lists leads with search and status filtering for admin operators."""
    items, total = lead_repository.list_leads(
        status=status_filter,
        search=search,
        limit=limit,
        offset=offset,
    )
    return LeadListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/leads/{lead_id}",
    response_model=LeadDTO,
    dependencies=[Depends(verify_admin_key)],
    summary="Get lead details (Admin)",
)
async def get_lead(lead_id: str) -> LeadDTO:
    """Retrieves full details and status history for a single lead."""
    lead = lead_repository.get_lead(lead_id)
    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "LEAD_NOT_FOUND", "message": f"Lead {lead_id} was not found."},
        )
    return lead


@router.patch(
    "/leads/{lead_id}/status",
    response_model=LeadDTO,
    dependencies=[Depends(verify_admin_key)],
    summary="Update lead workflow status (Admin)",
)
async def update_lead_status(
    lead_id: str,
    update_req: LeadStatusUpdateRequest,
) -> LeadDTO:
    """Updates lead workflow status and appends to the immutable audit trail."""
    updated = lead_repository.update_lead_status(
        lead_id=lead_id,
        new_status=update_req.new_status,
        changed_by=update_req.changed_by,
        notes=update_req.notes,
    )
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "LEAD_NOT_FOUND", "message": f"Lead {lead_id} was not found."},
        )
    return updated


@router.get(
    "/leads/{lead_id}/history",
    response_model=list[LeadStatusHistoryDTO],
    dependencies=[Depends(verify_admin_key)],
    summary="Get lead status audit history (Admin)",
)
async def get_lead_history(lead_id: str) -> list[LeadStatusHistoryDTO]:
    """Returns the immutable status change audit trail for a lead."""
    lead = lead_repository.get_lead(lead_id)
    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "LEAD_NOT_FOUND", "message": f"Lead {lead_id} was not found."},
        )
    return lead_repository.get_status_history(lead_id)


# -----------------------------------------------------------------------------
# Consultation Brief Generation & Exports (Admin)
# -----------------------------------------------------------------------------


@router.get(
    "/leads/{lead_id}/brief",
    response_model=ServiceBriefDTO,
    dependencies=[Depends(verify_admin_key)],
    summary="Generate Consultation Service Brief (JSON)",
)
async def get_service_brief(lead_id: str) -> ServiceBriefDTO:
    """Generates an evidence-backed consultation brief combining lead, audit, and resolution plan."""
    lead = lead_repository.get_lead(lead_id)
    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "LEAD_NOT_FOUND", "message": f"Lead {lead_id} was not found."},
        )
    return brief_generator.generate_brief(lead=lead)


@router.get(
    "/leads/{lead_id}/brief/markdown",
    dependencies=[Depends(verify_admin_key)],
    summary="Export Consultation Brief as Markdown",
)
async def export_brief_markdown(lead_id: str) -> Response:
    """Generates and returns the Consultation Service Brief formatted as Markdown."""
    lead = lead_repository.get_lead(lead_id)
    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "LEAD_NOT_FOUND", "message": f"Lead {lead_id} was not found."},
        )
    brief = brief_generator.generate_brief(lead=lead)
    markdown_content = brief_generator.export_markdown(brief)
    return Response(
        content=markdown_content,
        media_type="text/markdown",
        headers={"Content-Disposition": f'inline; filename="consultation-brief-{lead_id[:8]}.md"'},
    )


@router.get(
    "/leads/{lead_id}/brief/pdf",
    dependencies=[Depends(verify_admin_key)],
    summary="Export Consultation Brief as PDF",
)
async def export_brief_pdf(lead_id: str) -> Response:
    """Compiles and streams the Consultation Service Brief as a downloadable PDF document."""
    lead = lead_repository.get_lead(lead_id)
    if not lead:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "LEAD_NOT_FOUND", "message": f"Lead {lead_id} was not found."},
        )
    brief = brief_generator.generate_brief(lead=lead)
    pdf_bytes = brief_generator.export_pdf(brief)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="consultation-brief-{lead_id[:8]}.pdf"'},
    )
