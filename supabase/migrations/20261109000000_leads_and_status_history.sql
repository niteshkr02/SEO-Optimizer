-- =============================================================================
-- Migration: 001_leads_and_status_history.sql
-- Description: Hardened Schema, Least-Privilege Grants, and Row-Level Security (RLS)
--              for service inquiries, immutable audit trails, and distributed rate limiting.
-- Database: Supabase PostgreSQL (PostgreSQL 15+)
-- Architectural Reference: docs/DATA_PROVENANCE_AND_DICTIONARY.md (Section 3.10)
-- Security Reference: docs/SECURITY_REQUIREMENTS.md (Section 5.1 & 6)
--
-- STRICT OPERATIONAL GUARD:
-- DO NOT EXECUTE ON PRODUCTION WITHOUT SIGNED CHANGE APPROVAL.
-- =============================================================================

-- 1. Enable required cryptographic extensions
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- 2. Leads Table
CREATE TABLE IF NOT EXISTS public.leads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scan_token VARCHAR(64) NULL,
    customer_name VARCHAR(150) NOT NULL,
    business_email VARCHAR(255) NOT NULL,
    phone_number VARCHAR(30) NOT NULL,
    website_url TEXT NOT NULL,
    business_category VARCHAR(100) NOT NULL,
    target_city VARCHAR(100) NOT NULL,
    requested_service VARCHAR(100) NOT NULL,
    problem_description TEXT NOT NULL,
    urgency VARCHAR(20) NOT NULL DEFAULT 'MEDIUM' CHECK (urgency IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    status VARCHAR(32) NOT NULL DEFAULT 'NEW' CHECK (status IN ('NEW', 'CONTACTED', 'SCOPED', 'CONTRACTED', 'CLOSED')),
    consent_given BOOLEAN NOT NULL DEFAULT TRUE CHECK (consent_given = TRUE),
    consent_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    privacy_policy_version VARCHAR(32) NOT NULL DEFAULT '2026-v1',
    tech_stack JSONB NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexing for fast search, duplicate checks, and status filtering
CREATE INDEX IF NOT EXISTS idx_leads_business_email ON public.leads(business_email);
CREATE INDEX IF NOT EXISTS idx_leads_website_url ON public.leads(website_url);
CREATE INDEX IF NOT EXISTS idx_leads_status ON public.leads(status);
CREATE INDEX IF NOT EXISTS idx_leads_created_at ON public.leads(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_leads_scan_token ON public.leads(scan_token);

-- 3. Lead Status History (Immutable Audit Trail)
CREATE TABLE IF NOT EXISTS public.lead_status_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lead_id UUID NOT NULL REFERENCES public.leads(id) ON DELETE CASCADE,
    previous_status VARCHAR(32) NULL,
    new_status VARCHAR(32) NOT NULL CHECK (new_status IN ('NEW', 'CONTACTED', 'SCOPED', 'CONTRACTED', 'CLOSED')),
    changed_by VARCHAR(100) NOT NULL,
    notes TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_lead_status_history_lead_id ON public.lead_status_history(lead_id);
CREATE INDEX IF NOT EXISTS idx_lead_status_history_created_at ON public.lead_status_history(created_at DESC);

-- 4. Distributed Rate Limits Table
-- Enables atomic sliding-window rate limiting across horizontally-scaled backend nodes
CREATE TABLE IF NOT EXISTS public.rate_limits (
    rate_key VARCHAR(255) PRIMARY KEY,
    timestamps NUMERIC[] NOT NULL DEFAULT ARRAY[]::NUMERIC[],
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 5. Automatic updated_at Trigger for leads
CREATE OR REPLACE FUNCTION public.update_leads_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
SET search_path = ''
AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_update_leads_updated_at ON public.leads;
CREATE TRIGGER trg_update_leads_updated_at
    BEFORE UPDATE ON public.leads
    FOR EACH ROW
    EXECUTE FUNCTION public.update_leads_updated_at();

-- 6. Least-Privilege Grants Boundary
-- Revoke all default table permissions from public roles
REVOKE ALL ON public.leads FROM anon, authenticated, public;
REVOKE ALL ON public.lead_status_history FROM anon, authenticated, public;
REVOKE ALL ON public.rate_limits FROM anon, authenticated, public;

-- Anon role: Restrict exclusively to column-level INSERT on customer submission fields
GRANT INSERT (
    customer_name,
    business_email,
    phone_number,
    website_url,
    business_category,
    target_city,
    requested_service,
    problem_description,
    urgency,
    consent_given,
    privacy_policy_version,
    scan_token
) ON public.leads TO anon;

-- Authenticated role: Can access leads/history ONLY if JWT claim has admin/engineer role (enforced by RLS)
GRANT SELECT, INSERT, UPDATE ON public.leads TO authenticated;
GRANT SELECT, INSERT ON public.lead_status_history TO authenticated;

-- Service role: Full backend pipeline bypass
GRANT ALL ON public.leads TO service_role;
GRANT ALL ON public.lead_status_history TO service_role;
GRANT ALL ON public.rate_limits TO service_role;

-- 7. Row-Level Security (RLS) Configuration
ALTER TABLE public.leads ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.lead_status_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.rate_limits ENABLE ROW LEVEL SECURITY;

-- 7.1 Public / Anonymous Access Boundary
-- Anon clients may INSERT new service inquiries matching validation criteria, but CANNOT read, update, or delete records.
DROP POLICY IF EXISTS "anon_can_insert_leads" ON public.leads;
CREATE POLICY "anon_can_insert_leads"
    ON public.leads
    FOR INSERT
    TO anon
    WITH CHECK (
        consent_given = TRUE
        AND length(customer_name) >= 2
        AND length(business_email) >= 5
        AND length(problem_description) >= 10
    );

-- Anon has NO access to lead_status_history or rate_limits (default deny)

-- 7.2 Authenticated Administrative Access Boundary
-- Standard authenticated users (e.g. public accounts) are strictly DENIED access.
-- ONLY users with app_metadata.role in ('admin', 'engineer') or service_role can access.
DROP POLICY IF EXISTS "staff_admin_only_leads" ON public.leads;
CREATE POLICY "staff_admin_only_leads"
    ON public.leads
    FOR ALL
    TO authenticated
    USING (
        ((select auth.jwt()) -> 'app_metadata' ->> 'role') IN ('admin', 'engineer')
        OR ((select auth.jwt()) ->> 'role') = 'service_role'
    )
    WITH CHECK (
        ((select auth.jwt()) -> 'app_metadata' ->> 'role') IN ('admin', 'engineer')
        OR ((select auth.jwt()) ->> 'role') = 'service_role'
    );

DROP POLICY IF EXISTS "staff_admin_only_history" ON public.lead_status_history;
CREATE POLICY "staff_admin_only_history"
    ON public.lead_status_history
    FOR ALL
    TO authenticated
    USING (
        ((select auth.jwt()) -> 'app_metadata' ->> 'role') IN ('admin', 'engineer')
        OR ((select auth.jwt()) ->> 'role') = 'service_role'
    )
    WITH CHECK (
        ((select auth.jwt()) -> 'app_metadata' ->> 'role') IN ('admin', 'engineer')
        OR ((select auth.jwt()) ->> 'role') = 'service_role'
    );

-- 7.3 Service Role (Backend internal worker bypass)
DROP POLICY IF EXISTS "service_role_full_access_leads" ON public.leads;
CREATE POLICY "service_role_full_access_leads"
    ON public.leads
    FOR ALL
    TO service_role
    USING (TRUE)
    WITH CHECK (TRUE);

DROP POLICY IF EXISTS "service_role_full_access_history" ON public.lead_status_history;
CREATE POLICY "service_role_full_access_history"
    ON public.lead_status_history
    FOR ALL
    TO service_role
    USING (TRUE)
    WITH CHECK (TRUE);

DROP POLICY IF EXISTS "service_role_full_access_rate_limits" ON public.rate_limits;
CREATE POLICY "service_role_full_access_rate_limits"
    ON public.rate_limits
    FOR ALL
    TO service_role
    USING (TRUE)
    WITH CHECK (TRUE);

-- =============================================================================
-- VERIFICATION QUERIES (Run to verify RLS and grants posture)
-- =============================================================================
/*
-- 1. Check table RLS status:
SELECT relname, relrowsecurity, relforcerowsecurity 
FROM pg_class 
WHERE relname IN ('leads', 'lead_status_history', 'rate_limits');

-- 2. Inspect active policies:
SELECT schemaname, tablename, policyname, roles, cmd, qual, with_check 
FROM pg_policies 
WHERE tablename IN ('leads', 'lead_status_history', 'rate_limits');

-- 3. Verify column-level permissions for anon:
SELECT table_name, column_name, privilege_type 
FROM information_schema.column_privileges 
WHERE grantee = 'anon' AND table_name = 'leads';
*/

-- =============================================================================
-- ROLLBACK / DOWN MIGRATION (Execute only if rolling back this migration)
-- =============================================================================
/*
DROP POLICY IF EXISTS "service_role_full_access_rate_limits" ON public.rate_limits;
DROP POLICY IF EXISTS "service_role_full_access_history" ON public.lead_status_history;
DROP POLICY IF EXISTS "service_role_full_access_leads" ON public.leads;
DROP POLICY IF EXISTS "staff_admin_only_history" ON public.lead_status_history;
DROP POLICY IF EXISTS "staff_admin_only_leads" ON public.leads;
DROP POLICY IF EXISTS "anon_can_insert_leads" ON public.leads;

DROP TRIGGER IF EXISTS trg_update_leads_updated_at ON public.leads;
DROP FUNCTION IF EXISTS public.update_leads_updated_at();

DROP TABLE IF EXISTS public.rate_limits;
DROP TABLE IF EXISTS public.lead_status_history;
DROP TABLE IF EXISTS public.leads;
*/
