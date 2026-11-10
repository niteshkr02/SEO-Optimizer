-- =============================================================================
-- Migration: 003_multi_page_crawler.sql
-- Description: Multi-Page Asynchronous Website Crawler Persistence Schema:
--              1. crawl_jobs: Orchestration, progress, telemetry, and lifecycle state.
--              2. crawl_pages: Per-page crawl status, metrics, and deduplicated URLs.
--              3. crawl_page_findings: Page-level deterministic SEO rule findings.
--              4. crawl_site_aggregates: Site-wide scores and deduplicated issue rollups.
-- Database: Supabase PostgreSQL (PostgreSQL 15+)
-- Architectural Reference: docs/phase-2/WP_2_1_MULTI_PAGE_CRAWLER_DESIGN.md
-- Security Reference: docs/SECURITY_REQUIREMENTS.md (Section 5.1 & 6)
--
-- STRICT OPERATIONAL GUARD:
-- DO NOT EXECUTE ON PRODUCTION WITHOUT SIGNED CHANGE APPROVAL.
-- STAGING EXECUTION REQUIRES SEPARATE EXPLICIT APPROVAL AFTER REVIEW.
-- =============================================================================

-- 1. Crawl Jobs Table
CREATE TABLE IF NOT EXISTS public.crawl_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    seed_url TEXT NOT NULL,
    base_domain VARCHAR(255) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'QUEUED' 
        CHECK (status IN ('QUEUED', 'RUNNING', 'COMPLETED', 'PARTIAL', 'FAILED', 'CANCELLED')),
    max_pages INTEGER NOT NULL DEFAULT 25 CHECK (max_pages BETWEEN 1 AND 100),
    max_depth INTEGER NOT NULL DEFAULT 3 CHECK (max_depth BETWEEN 0 AND 5),
    pages_discovered INTEGER NOT NULL DEFAULT 1 CHECK (pages_discovered >= 0),
    pages_crawled INTEGER NOT NULL DEFAULT 0 CHECK (pages_crawled >= 0),
    pages_failed INTEGER NOT NULL DEFAULT 0 CHECK (pages_failed >= 0),
    pages_remaining INTEGER NOT NULL DEFAULT 1 CHECK (pages_remaining >= 0),
    current_depth INTEGER NOT NULL DEFAULT 0 CHECK (current_depth >= 0),
    config JSONB NOT NULL DEFAULT '{}'::jsonb,
    error_message TEXT NULL,
    started_at TIMESTAMPTZ NULL,
    completed_at TIMESTAMPTZ NULL,
    duration_seconds NUMERIC(10, 2) NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_crawl_jobs_status ON public.crawl_jobs(status);
CREATE INDEX IF NOT EXISTS idx_crawl_jobs_base_domain ON public.crawl_jobs(base_domain);
CREATE INDEX IF NOT EXISTS idx_crawl_jobs_created_at ON public.crawl_jobs(created_at DESC);

-- 2. Crawled Pages Table
CREATE TABLE IF NOT EXISTS public.crawl_pages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID NOT NULL REFERENCES public.crawl_jobs(id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    normalized_url TEXT NOT NULL,
    depth INTEGER NOT NULL DEFAULT 0 CHECK (depth >= 0),
    parent_url TEXT NULL,
    discovery_method VARCHAR(32) NOT NULL DEFAULT 'HTML_LINK'
        CHECK (discovery_method IN ('SEED', 'HTML_LINK', 'SITEMAP', 'CANONICAL')),
    status VARCHAR(32) NOT NULL DEFAULT 'PENDING'
        CHECK (status IN ('PENDING', 'FETCHING', 'CRAWLED', 'FAILED', 'DISALLOWED', 'SKIPPED')),
    http_status INTEGER NULL,
    response_time_ms INTEGER NULL,
    title TEXT NULL,
    canonical_url TEXT NULL,
    overall_score NUMERIC(5,2) NULL,
    completeness_score NUMERIC(5,2) NULL,
    error_reason TEXT NULL,
    crawled_at TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_crawl_pages_job_normalized_url UNIQUE (job_id, normalized_url)
);

CREATE INDEX IF NOT EXISTS idx_crawl_pages_job_status ON public.crawl_pages(job_id, status);
CREATE INDEX IF NOT EXISTS idx_crawl_pages_job_depth ON public.crawl_pages(job_id, depth);

-- 3. Page Findings Table
CREATE TABLE IF NOT EXISTS public.crawl_page_findings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID NOT NULL REFERENCES public.crawl_jobs(id) ON DELETE CASCADE,
    page_id UUID NOT NULL REFERENCES public.crawl_pages(id) ON DELETE CASCADE,
    rule_id VARCHAR(64) NOT NULL,
    category VARCHAR(32) NOT NULL,
    state VARCHAR(32) NOT NULL 
        CHECK (state IN ('PASS', 'FAIL', 'UNKNOWN', 'NOT_TESTED', 'NOT_APPLICABLE')),
    severity VARCHAR(32) NOT NULL 
        CHECK (severity IN ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO')),
    weight INTEGER NOT NULL DEFAULT 5,
    evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
    remediation_guidance TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_crawl_findings_page_id ON public.crawl_page_findings(page_id);
CREATE INDEX IF NOT EXISTS idx_crawl_findings_job_rule ON public.crawl_page_findings(job_id, rule_id);

-- 4. Site-Wide Aggregates Table
CREATE TABLE IF NOT EXISTS public.crawl_site_aggregates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id UUID NOT NULL UNIQUE REFERENCES public.crawl_jobs(id) ON DELETE CASCADE,
    seed_url TEXT NOT NULL,
    base_domain VARCHAR(255) NOT NULL,
    overall_score NUMERIC(5,2) NULL,
    completeness_score NUMERIC(5,2) NULL,
    category_scores JSONB NOT NULL DEFAULT '{}'::jsonb,
    unique_issues JSONB NOT NULL DEFAULT '[]'::jsonb,
    total_pages_analyzed INTEGER NOT NULL DEFAULT 0,
    total_issues_identified INTEGER NOT NULL DEFAULT 0,
    generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 5. Row Level Security (RLS) Configuration
ALTER TABLE public.crawl_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.crawl_pages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.crawl_page_findings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.crawl_site_aggregates ENABLE ROW LEVEL SECURITY;

-- 6. Role Permissions Boundary
-- Anonymous access is strictly revoked (Data API bypass protection)
REVOKE ALL ON public.crawl_jobs FROM anon;
REVOKE ALL ON public.crawl_pages FROM anon;
REVOKE ALL ON public.crawl_page_findings FROM anon;
REVOKE ALL ON public.crawl_site_aggregates FROM anon;

-- Backend service role has complete access
GRANT ALL ON public.crawl_jobs TO service_role;
GRANT ALL ON public.crawl_pages TO service_role;
GRANT ALL ON public.crawl_page_findings TO service_role;
GRANT ALL ON public.crawl_site_aggregates TO service_role;

-- Authenticated roles read-only access
GRANT SELECT ON public.crawl_jobs TO authenticated;
GRANT SELECT ON public.crawl_pages TO authenticated;
GRANT SELECT ON public.crawl_page_findings TO authenticated;
GRANT SELECT ON public.crawl_site_aggregates TO authenticated;

-- Service role policies
CREATE POLICY "service_role_all_crawl_jobs" ON public.crawl_jobs
    FOR ALL TO service_role USING (true) WITH CHECK (true);

CREATE POLICY "service_role_all_crawl_pages" ON public.crawl_pages
    FOR ALL TO service_role USING (true) WITH CHECK (true);

CREATE POLICY "service_role_all_crawl_findings" ON public.crawl_page_findings
    FOR ALL TO service_role USING (true) WITH CHECK (true);

CREATE POLICY "service_role_all_crawl_aggregates" ON public.crawl_site_aggregates
    FOR ALL TO service_role USING (true) WITH CHECK (true);

