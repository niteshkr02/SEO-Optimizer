"""Core configuration, error handling, and utilities."""

from app.core.config import settings
from app.core.errors import (
    AppError,
    CrawlerTimeoutError,
    InvalidURLError,
    MaxRedirectsExceededError,
    RedirectLoopError,
    ResourceSizeLimitExceededError,
    SSRFViolationError,
)

__all__ = [
    "AppError",
    "CrawlerTimeoutError",
    "InvalidURLError",
    "MaxRedirectsExceededError",
    "RedirectLoopError",
    "ResourceSizeLimitExceededError",
    "SSRFViolationError",
    "settings",
]
