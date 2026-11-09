"""Immutable structured evidence data model."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.contracts.enums import ProvenanceCategory


class FindingEvidence(BaseModel):
    """Immutable structured evidence object attached to every evaluated finding."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    observedValue: str | None = Field(
        default=None,
        description="Exact observed value, attribute, text or header from crawl.",
    )
    expectedValue: str | None = Field(
        default=None,
        description="Standard compliance requirement or expected value.",
    )
    provenance: ProvenanceCategory = Field(
        default=ProvenanceCategory.DIRECT_OBSERVATION,
        description="Explicit provenance classification.",
    )
    targetElement: str | None = Field(
        default=None,
        description="CSS selector, XPath, or DOM container hierarchy.",
    )
    rawSnippet: str | None = Field(
        default=None,
        description="Exact verbatim HTML tag or response header snippet.",
    )
    httpStatusCode: int | None = Field(
        default=None,
        description="Relevant HTTP response status code.",
    )
    responseTimeMs: int | None = Field(
        default=None,
        description="Round-trip network timing in milliseconds.",
    )
    lineNumber: int | None = Field(
        default=None,
        description="Line number in raw HTML where element begins.",
    )
    contextData: dict[str, Any] | None = Field(
        default=None,
        description="Additional structured context (e.g. redirect history, parsed JSON-LD).",
    )
