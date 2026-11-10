-- =============================================================================
-- Migration Rollback: 002_rollback.sql
-- Description: Reverts Migration 002 (Atomic Rate Limiting and Anon Hardening)
--              Restores schema to 001_leads_and_status_history.sql state.
-- Database: Supabase PostgreSQL (PostgreSQL 15+)
--
-- STRICT OPERATIONAL GUARD:
-- DO NOT EXECUTE ON PRODUCTION WITHOUT SIGNED CHANGE APPROVAL.
-- =============================================================================

-- 1. Remove immutability trigger and function on lead_status_history
DROP TRIGGER IF EXISTS trg_prevent_lead_status_history_mutation ON public.lead_status_history;
DROP FUNCTION IF EXISTS public.prevent_lead_status_history_mutation();

-- 2. Revoke and drop check_and_record_rate_limit RPC
REVOKE EXECUTE ON FUNCTION public.check_and_record_rate_limit(text, numeric, numeric, integer, boolean) FROM service_role;
DROP FUNCTION IF EXISTS public.check_and_record_rate_limit(text, numeric, numeric, integer, boolean);

-- 3. Restore column-level INSERT grant to anon on public.leads
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

-- 4. Re-create anon_can_insert_leads policy
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

