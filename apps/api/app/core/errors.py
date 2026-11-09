"""Custom domain exceptions and error definitions."""

from typing import Any


class AppError(Exception):
    """Base application error."""

    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}


class InvalidURLError(AppError):
    """Raised when an invalid or malformed URL is provided."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message, code="INVALID_URL", details=details)


class SSRFViolationError(AppError):
    """Raised when a URL attempts to access forbidden IP or network destination."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message, code="SSRF_VIOLATION", details=details)


class MaxRedirectsExceededError(AppError):
    """Raised when crawler exceeds the maximum permitted redirect hops."""

    def __init__(
        self,
        message: str = "Maximum redirects exceeded (limit: 5)",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message, code="MAX_REDIRECTS_EXCEEDED", details=details)


class RedirectLoopError(AppError):
    """Raised when an infinite redirect loop is detected."""

    def __init__(
        self,
        message: str = "Redirect loop detected in HTTP chain",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message, code="REDIRECT_LOOP_DETECTED", details=details)


class CrawlerTimeoutError(AppError):
    """Raised when crawling exceeds configured socket or read timeouts."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message, code="CRAWLER_TIMEOUT", details=details)


class ResourceSizeLimitExceededError(AppError):
    """Raised when response body exceeds maximum byte size threshold."""

    def __init__(
        self,
        message: str = "Response payload exceeds maximum allowed size (10 MB)",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message, code="RESOURCE_SIZE_LIMIT_EXCEEDED", details=details)
