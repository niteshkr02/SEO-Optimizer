-- =============================================================================
-- Rollback Script: 003_rollback.sql
-- Description: Safely drops multi-page crawler tables in reverse dependency order.
-- =============================================================================

DROP TABLE IF EXISTS public.crawl_site_aggregates CASCADE;
DROP TABLE IF EXISTS public.crawl_page_findings CASCADE;
DROP TABLE IF EXISTS public.crawl_pages CASCADE;
DROP TABLE IF EXISTS public.crawl_jobs CASCADE;

