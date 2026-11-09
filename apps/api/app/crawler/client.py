"""Safe HTTP client with manual redirect interception and streaming byte limits."""

import time
import urllib.parse

import httpx
from pydantic import BaseModel, ConfigDict, Field

from app.core.config import settings
from app.core.errors import (
    CrawlerTimeoutError,
    MaxRedirectsExceededError,
    RedirectLoopError,
    ResourceSizeLimitExceededError,
    SSRFViolationError,
)
from app.crawler.redirects import (
    RedirectEvaluation,
    RedirectHop,
    evaluate_redirect_chain,
)
from app.crawler.transport import create_ssrf_safe_transport
from app.crawler.url_sanitizer import sanitize_and_validate_url


class CrawlResult(BaseModel):
    """Immutable outcome of crawling a target URL."""

    model_config = ConfigDict(frozen=True)

    requested_url: str = Field(..., description="Original URL requested.")
    final_url: str = Field(..., description="Final landing URL.")
    status_code: int = Field(..., description="Final HTTP status code.")
    headers: dict[str, str] = Field(
        default_factory=dict, description="Normalized response headers."
    )
    body: str = Field(default="", description="Decoded HTML/text response body.")
    body_byte_size: int = Field(
        default=0, ge=0, description="Size of response payload in bytes."
    )
    response_time_ms: int = Field(
        default=0, ge=0, description="Round-trip network time in milliseconds."
    )
    redirect_evaluation: RedirectEvaluation = Field(
        ..., description="Model E11 evaluation."
    )
    content_type: str = Field(
        default="", description="Content-Type response header value."
    )


class SafeHttpClient:
    """Zero-trust HTTP client executing scans with strict SSRF defense and bounds."""

    def __init__(self, verify_ssl: bool = True, timeout: float | None = None):
        self.verify_ssl = verify_ssl
        self.timeout = timeout or settings.SCAN_TIMEOUT_SECONDS
        self.transport = create_ssrf_safe_transport(verify_ssl=verify_ssl)

    async def fetch(self, target_url: str) -> CrawlResult:
        """Fetches a target URL while manually following and validating all redirect hops."""
        start_time = time.perf_counter()

        _, current_url = sanitize_and_validate_url(target_url)
        initial_url = current_url
        hops: list[RedirectHop] = []
        seen_urls: set[str] = {current_url}

        async with httpx.AsyncClient(
            transport=self.transport,
            follow_redirects=False,  # Explicitly manual redirect control
            headers={"User-Agent": settings.CRAWLER_USER_AGENT},
            timeout=httpx.Timeout(
                connect=settings.CONNECT_TIMEOUT_SECONDS,
                read=settings.READ_TIMEOUT_SECONDS,
                write=settings.CONNECT_TIMEOUT_SECONDS,
                pool=settings.CONNECT_TIMEOUT_SECONDS,
            ),
        ) as client:
            while True:
                hop_start = time.perf_counter()
                try:
                    req = client.build_request("GET", current_url)
                    response = await client.send(req, stream=True)
                except httpx.TimeoutException as exc:
                    raise CrawlerTimeoutError(
                        f"Request to '{current_url}' timed out."
                    ) from exc
                except httpx.RequestError as exc:
                    raise SSRFViolationError(
                        f"Network transport error connecting to '{current_url}': {exc}"
                    ) from exc

                hop_elapsed_ms = int((time.perf_counter() - hop_start) * 1000)
                status_code = response.status_code

                # Check for 3xx redirect status
                if 300 <= status_code < 400 and "location" in response.headers:
                    raw_location = response.headers["location"]
                    next_url = urllib.parse.urljoin(current_url, raw_location)

                    # Validate the redirect target with zero-trust checks
                    _, sanitized_next = sanitize_and_validate_url(next_url)

                    # Loop detection
                    if sanitized_next in seen_urls:
                        hop = RedirectHop(
                            hop_index=len(hops),
                            status_code=status_code,
                            request_url=current_url,
                            target_url=sanitized_next,
                            latency_ms=hop_elapsed_ms,
                        )
                        hops.append(hop)
                        await response.aclose()
                        redirect_eval = evaluate_redirect_chain(
                            hops=hops,
                            initial_url=initial_url,
                            final_url=sanitized_next,
                            has_loop=True,
                        )
                        raise RedirectLoopError(
                            f"Redirect loop detected: '{sanitized_next}' already visited in chain.",
                            details={"redirect_evaluation": redirect_eval.model_dump()},
                        )

                    hop = RedirectHop(
                        hop_index=len(hops),
                        status_code=status_code,
                        request_url=current_url,
                        target_url=sanitized_next,
                        latency_ms=hop_elapsed_ms,
                    )
                    hops.append(hop)
                    seen_urls.add(sanitized_next)
                    await response.aclose()

                    # Maximum redirect hops check
                    if len(hops) > settings.MAX_REDIRECTS:
                        redirect_eval = evaluate_redirect_chain(
                            hops=hops,
                            initial_url=initial_url,
                            final_url=sanitized_next,
                            has_loop=False,
                        )
                        raise MaxRedirectsExceededError(
                            f"Redirect chain exceeded max limit of {settings.MAX_REDIRECTS} hops.",
                            details={"redirect_evaluation": redirect_eval.model_dump()},
                        )

                    current_url = sanitized_next
                    continue

                # Final landing response: read with streaming byte limit
                try:
                    content_bytes = bytearray()
                    async for chunk in response.aiter_bytes():
                        content_bytes.extend(chunk)
                        if len(content_bytes) > settings.MAX_RESPONSE_BYTES:
                            await response.aclose()
                            raise ResourceSizeLimitExceededError(
                                f"Response body exceeded maximum limit of {settings.MAX_RESPONSE_BYTES} bytes."
                            )
                finally:
                    await response.aclose()

                total_elapsed_ms = int((time.perf_counter() - start_time) * 1000)

                # Decode text body
                content_type = response.headers.get("content-type", "").lower()
                charset = "utf-8"
                if "charset=" in content_type:
                    charset = content_type.split("charset=")[-1].split(";")[0].strip()

                try:
                    decoded_body = content_bytes.decode(charset, errors="replace")
                except (LookupError, UnicodeDecodeError):
                    decoded_body = content_bytes.decode("utf-8", errors="replace")

                redirect_eval = evaluate_redirect_chain(
                    hops=hops,
                    initial_url=initial_url,
                    final_url=current_url,
                    has_loop=False,
                )

                # Normalize headers to lowercase keys
                normalized_headers = {k.lower(): v for k, v in response.headers.items()}

                return CrawlResult(
                    requested_url=target_url,
                    final_url=current_url,
                    status_code=status_code,
                    headers=normalized_headers,
                    body=decoded_body,
                    body_byte_size=len(content_bytes),
                    response_time_ms=total_elapsed_ms,
                    redirect_evaluation=redirect_eval,
                    content_type=content_type,
                )
