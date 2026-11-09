"""Technical metrics package."""

from app.metrics.assets import ImageAltCoverageResult, calculate_image_alt_coverage
from app.metrics.links import InternalLinkHealthResult, calculate_internal_link_health
from app.metrics.sitemap import SitemapHealthResult, calculate_sitemap_health

__all__ = [
    "ImageAltCoverageResult",
    "InternalLinkHealthResult",
    "SitemapHealthResult",
    "calculate_image_alt_coverage",
    "calculate_internal_link_health",
    "calculate_sitemap_health",
]
