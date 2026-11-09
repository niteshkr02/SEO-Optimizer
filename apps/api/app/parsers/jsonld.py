"""Mathematical Model E14: JSON-LD Syntax Validity Ratio (JVR) and Schema.org parser."""

import json
from typing import Any

from bs4 import BeautifulSoup
from pydantic import BaseModel, ConfigDict, Field


class ParsedJsonLdBlock(BaseModel):
    """Result of parsing an individual JSON-LD script element."""

    model_config = ConfigDict(frozen=True)

    raw_text: str = Field(..., description="Raw text content of script tag.")
    is_valid_syntax: bool = Field(
        ..., description="True if text parsed cleanly as RFC 8259 JSON."
    )
    parsed_json: Any | None = Field(
        default=None, description="Decoded Python object if valid."
    )
    syntax_error: str | None = Field(
        default=None, description="Syntax error message if invalid."
    )
    schema_types: list[str] = Field(
        default_factory=list, description="Extracted @type values if present."
    )


class JsonLdReport(BaseModel):
    """Mathematical Model E14 evaluation summary."""

    model_config = ConfigDict(frozen=True)

    formula_id: str = "E14"
    formula_version: str = "1.0.0"
    detected_blocks_count: int = Field(
        default=0, ge=0, description="Total JSON-LD script tags detected."
    )
    valid_blocks_count: int = Field(
        default=0, ge=0, description="Count of blocks passing JSON syntax."
    )
    jvr_score: float | None = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="JSON-LD Validity Ratio (0-100), or None if 0 blocks detected.",
    )
    status: str = Field(
        ..., description="NONE_DETECTED | SYNTAX_VALID | SYNTAX_INVALID"
    )
    blocks: list[ParsedJsonLdBlock] = Field(
        default_factory=list, description="List of parsed block results."
    )
    detected_schema_types: list[str] = Field(
        default_factory=list, description="Deduplicated @type values found."
    )


def extract_schema_types(data: Any) -> list[str]:
    """Recursively traverses a JSON-LD structure to extract all '@type' strings."""
    types: list[str] = []
    if isinstance(data, dict):
        if "@type" in data:
            t = data["@type"]
            if isinstance(t, str):
                types.append(t)
            elif isinstance(t, list):
                types.extend([item for item in t if isinstance(item, str)])
        for value in data.values():
            types.extend(extract_schema_types(value))
    elif isinstance(data, list):
        for item in data:
            types.extend(extract_schema_types(item))
    return types


def parse_jsonld(html_content: str, soup: BeautifulSoup | None = None) -> JsonLdReport:
    """Parses all JSON-LD blocks in an HTML document and calculates Model E14 (JVR).

    Formulation:
    JVR = 100 * (valid JSON-LD blocks) / (detected JSON-LD blocks)
    If detected == 0, JVR is None (NULL), status is 'NONE_DETECTED'.
    """
    if soup is None:
        soup = BeautifulSoup(html_content, "lxml")

    script_tags = soup.find_all("script", attrs={"type": "application/ld+json"})
    detected_count = len(script_tags)

    if detected_count == 0:
        return JsonLdReport(
            detected_blocks_count=0,
            valid_blocks_count=0,
            jvr_score=None,
            status="NONE_DETECTED",
            blocks=[],
            detected_schema_types=[],
        )

    valid_count = 0
    parsed_blocks: list[ParsedJsonLdBlock] = []
    all_types: set[str] = set()

    for tag in script_tags:
        raw_text = tag.string or tag.get_text() or ""
        trimmed_text = raw_text.strip()

        try:
            parsed = json.loads(trimmed_text)
            types = extract_schema_types(parsed)
            all_types.update(types)
            valid_count += 1
            parsed_blocks.append(
                ParsedJsonLdBlock(
                    raw_text=raw_text,
                    is_valid_syntax=True,
                    parsed_json=parsed,
                    schema_types=types,
                )
            )
        except (json.JSONDecodeError, ValueError) as exc:
            parsed_blocks.append(
                ParsedJsonLdBlock(
                    raw_text=raw_text,
                    is_valid_syntax=False,
                    parsed_json=None,
                    syntax_error=str(exc),
                    schema_types=[],
                )
            )

    jvr = (valid_count / detected_count) * 100.0
    status = "SYNTAX_VALID" if valid_count == detected_count else "SYNTAX_INVALID"

    return JsonLdReport(
        detected_blocks_count=detected_count,
        valid_blocks_count=valid_count,
        jvr_score=round(jvr, 2),
        status=status,
        blocks=parsed_blocks,
        detected_schema_types=sorted(all_types),
    )
