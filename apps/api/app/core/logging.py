"""Logging configuration for SEO Optimizer API."""

import logging
import sys


def setup_logging() -> None:
    """Configures structured console logging for the application."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


logger = logging.getLogger("seo_optimizer")
