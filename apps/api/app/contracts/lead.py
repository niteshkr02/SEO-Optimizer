"""Pydantic v2 contracts for service inquiries and lead management."""

import re
from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from pydantic.alias_generators import to_camel

from app.contracts.enums import LeadStatus, LeadUrgency


class LeadSubmissionRequest(BaseModel):
    """Client-submitted SEO service inquiry payload."""

    model_config = ConfigDict(
        frozen=True,
        alias_generator=to_camel,
        populate_by_name=True,
    )

    customer_name: str = Field(
        ...,
        min_length=2,
        max_length=150,
        description="Full name of client contact",
    )
    business_email: EmailStr = Field(
        ...,
        max_length=255,
        description="Business or corporate email address",
    )
    phone_number: str = Field(
        ...,
        min_length=7,
        max_length=30,
        description="Contact phone number including country code (e.g. +1 555-0199)",
    )
    website_url: str = Field(
        ...,
        min_length=4,
        max_length=1000,
        description="Audited website URL (must start with http:// or https://)",
    )
    business_category: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Industry vertical or category (e.g. E-Commerce, SaaS, Local)",
    )
    target_city: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Target geographic market / city",
    )
    requested_service: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Type of SEO consulting or engineering service requested",
    )
    problem_description: str = Field(
        ...,
        min_length=10,
        max_length=2000,
        description="Detailed description of SEO issues or objectives",
    )
    urgency: LeadUrgency = Field(
        default=LeadUrgency.MEDIUM,
        description="Client operational urgency",
    )
    consent_given: bool = Field(
        ...,
        description="Explicit consent for technical contact and data processing",
    )
    privacy_policy_version: str = Field(
        default="2026-v1",
        max_length=32,
        description="Version of privacy policy acknowledged",
    )
    scan_token: str | None = Field(
        default=None,
        max_length=64,
        description="Associated single-page audit scan token",
    )
    honeypot: str | None = Field(
        default=None,
        max_length=100,
        description="Anti-spam honeypot field. Must remain empty.",
    )

    @field_validator("customer_name")
    @classmethod
    def validate_customer_name(cls, v: str) -> str:
        clean = v.strip()
        if len(clean) < 2:
            raise ValueError("Customer name must be at least 2 non-whitespace characters.")
        return clean

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        clean = v.strip()
        # Basic international telephone sanity check (+ optional digits, spaces, hyphens, parens)
        if not re.match(r"^\+?[\d\s\-().]{7,30}$", clean):
            raise ValueError(
                "Phone number must contain a valid international or regional format with country code (e.g. +1 555-123-4567)."
            )
        return clean

    @field_validator("website_url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        clean = v.strip()
        if not clean.startswith(("http://", "https://")):
            raise ValueError("Website URL must start with http:// or https://")
        return clean

    @field_validator("consent_given")
    @classmethod
    def validate_consent(cls, v: bool) -> bool:
        if not v:
            raise ValueError("Explicit contact and privacy consent must be accepted.")
        return v

    @field_validator("honeypot")
    @classmethod
    def validate_honeypot(cls, v: str | None) -> str | None:
        return v


class LeadStatusHistoryDTO(BaseModel):
    """Audit trail record of lead status transition."""

    model_config = ConfigDict(
        frozen=True,
        alias_generator=to_camel,
        populate_by_name=True,
    )

    id: str = Field(..., description="Unique status change ID")
    lead_id: str = Field(..., description="Associated lead ID")
    previous_status: LeadStatus | None = Field(
        default=None, description="Prior lifecycle status"
    )
    new_status: LeadStatus = Field(..., description="New lifecycle status")
    changed_by: str = Field(..., description="Identifier of engineer or system making change")
    notes: str | None = Field(default=None, description="Optional transition notes")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Transition timestamp",
    )


class LeadDTO(BaseModel):
    """Canonical persisted service lead entity."""

    model_config = ConfigDict(
        frozen=True,
        alias_generator=to_camel,
        populate_by_name=True,
    )

    id: str = Field(..., description="Unique lead identifier")
    scan_token: str | None = Field(
        default=None, description="Linked audit scan token if available"
    )
    customer_name: str = Field(..., description="Client contact name")
    business_email: str = Field(..., description="Business email address")
    phone_number: str = Field(..., description="Phone number with country code")
    website_url: str = Field(..., description="Target website URL")
    business_category: str = Field(..., description="Business industry category")
    target_city: str = Field(..., description="Target city / location")
    requested_service: str = Field(..., description="Requested SEO service")
    problem_description: str = Field(..., description="Client problem statement")
    urgency: LeadUrgency = Field(..., description="Client urgency")
    status: LeadStatus = Field(default=LeadStatus.NEW, description="Current workflow status")
    consent_given: bool = Field(default=True, description="Explicit consent status")
    consent_timestamp: datetime = Field(..., description="Timestamp when consent was recorded")
    privacy_policy_version: str = Field(..., description="Privacy policy version")
    created_at: datetime = Field(..., description="Lead creation timestamp")
    updated_at: datetime = Field(..., description="Lead last updated timestamp")
    status_history: list[LeadStatusHistoryDTO] = Field(
        default_factory=list, description="Historical audit trail of status changes"
    )


class LeadStatusUpdateRequest(BaseModel):
    """Payload to transition lead workflow status."""

    model_config = ConfigDict(
        frozen=True,
        alias_generator=to_camel,
        populate_by_name=True,
    )

    new_status: LeadStatus = Field(
        ...,
        description="Target status: NEW | CONTACTED | SCOPED | CONTRACTED | CLOSED",
    )
    changed_by: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Admin operator or engineer performing the update",
    )
    notes: str | None = Field(
        default=None,
        max_length=1000,
        description="Operational context or qualification notes",
    )


class LeadListResponse(BaseModel):
    """Paginated list of leads for admin management."""

    model_config = ConfigDict(
        frozen=True,
        alias_generator=to_camel,
        populate_by_name=True,
    )

    items: list[LeadDTO] = Field(..., description="List of matching leads")
    total: int = Field(..., description="Total matching leads count")
    limit: int = Field(..., description="Pagination page size limit")
    offset: int = Field(..., description="Pagination offset")
