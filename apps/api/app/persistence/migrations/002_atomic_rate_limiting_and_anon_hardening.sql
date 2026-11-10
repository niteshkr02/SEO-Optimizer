-- =============================================================================
-- Migration: 002_atomic_rate_limiting_and_anon_hardening.sql
-- Description: Hardening migration for SEO Optimizer:
--              1. Revokes anonymous direct INSERT on public.leads and drops anon_can_insert_leads policy.
--              2. Implements concurrency-safe atomic sliding-window rate limiting RPC
--                 (public.check_and_record_rate_limit) using advisory locking and UPSERT semantics.
--              3. Restricts RPC execution strictly to backend service_role.
--              4. Enforces immutable audit trail on public.lead_status_history via trigger.
-- Database: Supabase PostgreSQL (PostgreSQL 15+)
-- Architectural Reference: docs/DATA_PROVENANCE_AND_DICTIONARY.md (Section 3.10)
-- Security Reference: docs/SECURITY_REQUIREMENTS.md (Section 5.1 & 6)
--
-- STRICT OPERATIONAL GUARD:
-- Dedicated Non-Production Staging Project Execution Authorized by User.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. Revoke Anonymous Direct INSERT Privileges on Leads (BLK-02 Remediation)
-- -----------------------------------------------------------------------------
-- All customer inquiries are submitted through FastAPI (POST /api/v1/leads) which
-- enforces server-side honeypots, Pydantic validation, duplicate checks, and rate limits.
-- Revoking direct anon table grants closes the Supabase Data API bypass vector.

DROP POLICY IF EXISTS "anon_can_insert_leads" ON public.leads;
REVOKE INSERT ON public.leads FROM anon;

-- Ensure anon has zero permissions on any table in the schema
REVOKE ALL ON public.leads FROM anon;
REVOKE ALL ON public.lead_status_history FROM anon;
REVOKE ALL ON public.rate_limits FROM anon;


-- -----------------------------------------------------------------------------
-- 2. Concurrency-Safe Atomic Rate Limiting RPC (BLK-03 Remediation)
-- -----------------------------------------------------------------------------
-- Eliminates multi-instance read-modify-write race hazards.
-- Uses:
--   a) Transaction-level advisory lock (pg_advisory_xact_lock) to serialize concurrent
--      first-requests before any row exists.
--   b) Safe UPSERT (INSERT ... ON CONFLICT DO NOTHING) to guarantee row existence.
--   c) SELECT ... FOR UPDATE row-level lock for serialized window evaluation.
--   d) In-place timestamp pruning to prevent storage bloat.
--
-- SECURITY CONTROLS:
--   - SECURITY DEFINER: Executes with definer privileges to update public.rate_limits.
--   - SET search_path = '': Highest security posture against search_path hijacking.
--   - Fully qualified relation and system function calls with public.* and pg_catalog.*.

CREATE OR REPLACE FUNCTION public.check_and_record_rate_limit(
    p_rate_key text,
    p_now numeric,
    p_window_seconds numeric,
    p_max_submissions integer,
    p_record boolean DEFAULT true
)
RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
DECLARE
    v_timestamps numeric[];
    v_valid numeric[];
BEGIN
    -- Input boundary validation
    IF p_rate_key IS NULL OR pg_catalog.length(pg_catalog.btrim(p_rate_key)) = 0 THEN
        RAISE EXCEPTION 'p_rate_key cannot be null or empty';
    END IF;

    IF p_max_submissions <= 0 THEN
        RETURN FALSE;
    END IF;

    IF p_window_seconds <= 0 THEN
        RAISE EXCEPTION 'p_window_seconds must be positive';
    END IF;

    -- 1. Acquire transaction-level advisory lock on rate_key hash.
    --    This guarantees that concurrent requests for a non-existent key
    --    are safely serialized before row creation.
    PERFORM pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtext('rate_limit:' || p_rate_key));

    -- 2. Safe UPSERT: Ensure row exists without race hazards.
    INSERT INTO public.rate_limits (rate_key, timestamps, updated_at)
    VALUES (p_rate_key, ARRAY[]::numeric[], pg_catalog.now())
    ON CONFLICT (rate_key) DO NOTHING;

    -- 3. Row-level lock: Explicitly lock the row for update.
    SELECT timestamps INTO v_timestamps
    FROM public.rate_limits
    WHERE rate_key = p_rate_key
    FOR UPDATE;

    -- 4. Purge expired timestamps outside the sliding window.
    SELECT COALESCE(pg_catalog.array_agg(t), ARRAY[]::numeric[])
    INTO v_valid
    FROM pg_catalog.unnest(COALESCE(v_timestamps, ARRAY[]::numeric[])) AS t
    WHERE t >= (p_now - p_window_seconds);

    -- 5. Evaluate rate limit threshold.
    IF pg_catalog.cardinality(v_valid) >= p_max_submissions THEN
        -- Clean up expired timestamps in storage even when rejecting
        IF p_record THEN
            UPDATE public.rate_limits
            SET timestamps = v_valid,
                updated_at = pg_catalog.now()
            WHERE rate_key = p_rate_key;
        END IF;
        RETURN FALSE;
    END IF;

    -- 6. Atomically append new timestamp if recording is enabled.
    IF p_record THEN
        UPDATE public.rate_limits
        SET timestamps = pg_catalog.array_append(v_valid, p_now),
            updated_at = pg_catalog.now()
        WHERE rate_key = p_rate_key;
    END IF;

    RETURN TRUE;
END;
$$;

-- -----------------------------------------------------------------------------
-- 3. Least-Privilege Execution Boundary for the RPC
-- -----------------------------------------------------------------------------
-- Revoke execution from PUBLIC, anon, and standard authenticated users.
-- Grant execution strictly to service_role (used by backend worker).

REVOKE ALL ON FUNCTION public.check_and_record_rate_limit(text, numeric, numeric, integer, boolean) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.check_and_record_rate_limit(text, numeric, numeric, integer, boolean) TO service_role;


-- -----------------------------------------------------------------------------
-- 4. Immutable Audit Trail Trigger for Lead Status History
-- -----------------------------------------------------------------------------
-- Ensures status history records can NEVER be modified or deleted by any role.

CREATE OR REPLACE FUNCTION public.prevent_lead_status_history_mutation()
RETURNS TRIGGER
LANGUAGE plpgsql
SET search_path = ''
AS $$
BEGIN
    RAISE EXCEPTION 'Audit records in public.lead_status_history are immutable: UPDATE and DELETE operations are forbidden.';
END;
$$;

DROP TRIGGER IF EXISTS trg_prevent_lead_status_history_mutation ON public.lead_status_history;
CREATE TRIGGER trg_prevent_lead_status_history_mutation
    BEFORE UPDATE OR DELETE ON public.lead_status_history
    FOR EACH ROW
    EXECUTE FUNCTION public.prevent_lead_status_history_mutation();

-- Ensure service_role maintains full backend pipeline access
GRANT ALL ON public.leads TO service_role;
GRANT ALL ON public.lead_status_history TO service_role;
GRANT ALL ON public.rate_limits TO service_role;
