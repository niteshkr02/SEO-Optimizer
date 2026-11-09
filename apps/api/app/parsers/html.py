"""Deterministic HTML DOM and metadata parser using BeautifulSoup 4 and lxml."""

import re
import urllib.parse

from bs4 import BeautifulSoup
from pydantic import BaseModel, ConfigDict, Field

from app.parsers.jsonld import JsonLdReport, parse_jsonld


class ParsedHeading(BaseModel):
    """Structure representing an extracted heading element."""

    model_config = ConfigDict(frozen=True)

    level: int = Field(
        ..., ge=1, le=6, description="Heading level (1 for H1, 6 for H6)."
    )
    tag_name: str = Field(..., description="Tag name ('h1', 'h2', etc.).")
    text: str = Field(..., description="Trimmed text content of heading.")
    selector: str | None = Field(default=None, description="CSS selector path.")


class ParsedImage(BaseModel):
    """Structure representing an extracted image element."""

    model_config = ConfigDict(frozen=True)

    src: str | None = Field(default=None, description="Image source URL.")
    alt: str | None = Field(
        default=None, description="Raw alt attribute value (None if missing)."
    )
    has_alt_attr: bool = Field(..., description="True if alt attribute exists on tag.")
    is_decorative: bool = Field(
        ..., description="True if alt='' or role='presentation' or aria-hidden='true'."
    )
    width: str | None = Field(default=None, description="Width attribute if declared.")
    height: str | None = Field(
        default=None, description="Height attribute if declared."
    )
    raw_snippet: str = Field(..., description="Verbatim HTML tag string.")


class ParsedLink(BaseModel):
    """Structure representing an extracted anchor link."""

    model_config = ConfigDict(frozen=True)

    href: str = Field(..., description="Raw href value.")
    resolved_url: str | None = Field(default=None, description="Absolute resolved URL.")
    anchor_text: str = Field(default="", description="Visible text within link.")
    is_internal: bool = Field(
        ..., description="True if link targets the same origin domain."
    )


class ParsedDocument(BaseModel):
    """Comprehensive structured snapshot of a parsed HTML document."""

    model_config = ConfigDict(frozen=True)

    target_url: str
    title_text: str | None = None
    title_raw_snippet: str | None = None
    title_char_count: int = 0

    meta_description_text: str | None = None
    meta_description_raw_snippet: str | None = None
    meta_description_char_count: int = 0

    canonical_url: str | None = None
    canonical_raw_snippet: str | None = None

    robots_meta_directives: list[str] = Field(default_factory=list)
    x_robots_tag_directives: list[str] = Field(default_factory=list)

    headings: list[ParsedHeading] = Field(default_factory=list)
    images: list[ParsedImage] = Field(default_factory=list)
    links: list[ParsedLink] = Field(default_factory=list)
    jsonld_report: JsonLdReport

    is_spa_detected: bool = False
    dom_node_count: int = 0


def parse_html_document(
    html_content: str,
    target_url: str,
    headers: dict[str, str] | None = None,
) -> ParsedDocument:
    """Parses raw HTML and HTTP response headers into an immutable ParsedDocument model."""
    soup = BeautifulSoup(html_content, "lxml")
    parsed_base = urllib.parse.urlsplit(target_url)
    base_domain = parsed_base.netloc.lower()

    # Total DOM nodes
    all_tags = soup.find_all(True)
    dom_node_count = len(all_tags)

    # 1. Title tag
    title_text: str | None = None
    title_raw_snippet: str | None = None
    title_char_count = 0
    title_tag = soup.find("title")
    if title_tag:
        title_text = title_tag.get_text().strip()
        title_raw_snippet = str(title_tag)
        title_char_count = len(title_text)

    # 2. Meta description
    meta_desc_text: str | None = None
    meta_desc_raw_snippet: str | None = None
    meta_desc_char_count = 0
    desc_tag = soup.find(
        "meta", attrs={"name": re.compile(r"^description$", re.IGNORECASE)}
    )
    if desc_tag and desc_tag.get("content"):
        content_val = str(desc_tag.get("content", "")).strip()
        meta_desc_text = content_val
        meta_desc_raw_snippet = str(desc_tag)
        meta_desc_char_count = len(content_val)

    # 3. Canonical tag
    canonical_url: str | None = None
    canonical_raw_snippet: str | None = None
    canon_tag = soup.find(
        "link",
        attrs={
            "rel": lambda r: (
                r and "canonical" in r.lower() if isinstance(r, str) else False
            )
        },
    )
    if canon_tag and canon_tag.get("href"):
        canonical_url = str(canon_tag.get("href", "")).strip()
        canonical_raw_snippet = str(canon_tag)

    # 4. Meta robots directives
    robots_meta_directives: list[str] = []
    robots_tag = soup.find(
        "meta", attrs={"name": re.compile(r"^robots$", re.IGNORECASE)}
    )
    if robots_tag and robots_tag.get("content"):
        raw_directives = str(robots_tag.get("content", "")).lower().split(",")
        robots_meta_directives = [d.strip() for d in raw_directives if d.strip()]

    # 5. X-Robots-Tag from response headers
    x_robots_tag_directives: list[str] = []
    if headers:
        for k, v in headers.items():
            if k.lower() == "x-robots-tag":
                raw_directives = v.lower().split(",")
                x_robots_tag_directives.extend(
                    [d.strip() for d in raw_directives if d.strip()]
                )

    # 6. Headings hierarchy (H1 - H6)
    headings: list[ParsedHeading] = []
    heading_tags = soup.find_all(re.compile(r"^h[1-6]$", re.IGNORECASE))
    for h in heading_tags:
        lvl = int(h.name[1])
        txt = h.get_text().strip()
        headings.append(
            ParsedHeading(
                level=lvl,
                tag_name=h.name.lower(),
                text=txt,
                selector=f"{h.name.lower()}",
            )
        )

    # 7. Images
    images: list[ParsedImage] = []
    img_tags = soup.find_all("img")
    for img in img_tags:
        src = img.get("src")
        has_alt = "alt" in img.attrs
        alt_val = img.get("alt")

        role = img.get("role", "")
        aria_hidden = img.get("aria-hidden", "")
        is_decorative = (
            (has_alt and (alt_val == "" or alt_val is None))
            or role == "presentation"
            or aria_hidden == "true"
        )

        images.append(
            ParsedImage(
                src=str(src) if src else None,
                alt=str(alt_val) if alt_val is not None else None,
                has_alt_attr=has_alt,
                is_decorative=is_decorative,
                width=str(img.get("width")) if img.get("width") else None,
                height=str(img.get("height")) if img.get("height") else None,
                raw_snippet=str(img),
            )
        )

    # 8. Links
    links: list[ParsedLink] = []
    a_tags = soup.find_all("a", href=True)
    for a in a_tags:
        href = str(a.get("href", "")).strip()
        if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
            continue

        resolved = urllib.parse.urljoin(target_url, href)
        parsed_link = urllib.parse.urlsplit(resolved)
        is_internal = parsed_link.netloc.lower() == base_domain

        links.append(
            ParsedLink(
                href=href,
                resolved_url=resolved,
                anchor_text=a.get_text().strip(),
                is_internal=is_internal,
            )
        )

    # 9. JSON-LD Report (Model E14)
    jsonld_report = parse_jsonld(html_content, soup=soup)

    # 10. SPA Detection heuristic
    # If the body tag exists and has very few text nodes, but has common SPA anchor tags
    body = soup.find("body")
    body_text_len = len(body.get_text().strip()) if body else 0
    spa_indicators = soup.find_all(
        id=re.compile(r"^(root|__next|app|__nuxt)$", re.IGNORECASE)
    )
    is_spa_detected = (body_text_len < 60 and len(spa_indicators) > 0) or (
        dom_node_count < 10 and len(spa_indicators) > 0
    )

    return ParsedDocument(
        target_url=target_url,
        title_text=title_text,
        title_raw_snippet=title_raw_snippet,
        title_char_count=title_char_count,
        meta_description_text=meta_desc_text,
        meta_description_raw_snippet=meta_desc_raw_snippet,
        meta_description_char_count=meta_desc_char_count,
        canonical_url=canonical_url,
        canonical_raw_snippet=canonical_raw_snippet,
        robots_meta_directives=robots_meta_directives,
        x_robots_tag_directives=x_robots_tag_directives,
        headings=headings,
        images=images,
        links=links,
        jsonld_report=jsonld_report,
        is_spa_detected=is_spa_detected,
        dom_node_count=dom_node_count,
    )
