"""HTML and structured data parser package."""

from app.parsers.html import (
    ParsedDocument,
    ParsedHeading,
    ParsedImage,
    ParsedLink,
    parse_html_document,
)
from app.parsers.jsonld import JsonLdReport, ParsedJsonLdBlock, parse_jsonld

__all__ = [
    "JsonLdReport",
    "ParsedDocument",
    "ParsedHeading",
    "ParsedImage",
    "ParsedJsonLdBlock",
    "ParsedLink",
    "parse_html_document",
    "parse_jsonld",
]
