"""Factory for instantiating the crawl persistence repository adapter."""

import logging

from app.core.config import settings
from app.persistence.crawl_in_memory import InMemoryCrawlRepository
from app.persistence.crawl_interface import CrawlRepositoryInterface
from app.persistence.crawl_sqlite import SQLiteCrawlRepository

logger = logging.getLogger(__name__)


def create_crawl_repository(
    backend: str | None = None,
    db_path: str | None = None,
) -> CrawlRepositoryInterface:
    """Creates a crawl repository instance based on explicit parameters or app settings."""
    selected_backend = (backend or settings.PERSISTENCE_BACKEND).lower().strip()

    if selected_backend == "in_memory":
        logger.info("Initializing InMemoryCrawlRepository adapter")
        return InMemoryCrawlRepository()

    # In local/staging, use SQLiteCrawlRepository by default for crawler data
    target_db = db_path or settings.SQLITE_DB_PATH
    logger.info("Initializing SQLiteCrawlRepository adapter at %s", target_db)
    return SQLiteCrawlRepository(db_path=target_db)


# Global singleton instance
crawl_repository: CrawlRepositoryInterface = create_crawl_repository()

