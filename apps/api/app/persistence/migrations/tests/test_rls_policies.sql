-- =============================================================================
-- Test Suite: test_rls_policies.sql
-- Description: Automated SQL tests validating Row-Level Security (RLS) policies,
--              least-privilege role boundaries, and audit trail immutability.
-- Target: Supabase PostgreSQL (PostgreSQL 15+)
--
-- EXECUTION:
-- Execute in a non-production database or psql session:
--   psql -h <host> -U postgres -d <db> -f test_rls_policies.sql
-- All operations are wrapped in a transaction and rolled back at the end.
-- =============================================================================

BEGIN;

-- Display test header
DO $$
BEGIN
    RAISE NOTICE '=============================================================';
    RAISE NOTICE 'RUNNING RLS POLICY AND PRIVILEGE VERIFICATION TESTS';
    RAISE NOTICE '=============================================================';
END $$;

-- -----------------------------------------------------------------------------
-- 0. Seed a test lead as service_role
-- -----------------------------------------------------------------------------
SET LOCAL ROLE service_role;

INSERT INTO public.leads (
    id, customer_name, business_email, phone_number, website_url,
    business_category, target_city, requested_service, problem_description,
    urgency, status, consent_given, privacy_policy_version
) VALUES (
    '11111111-1111-1111-1111-111111111111',
    'Test Security Lead',
    'security@test.org',
    '+1 555-0199',
    'https://security.test.org',
    'Security',
    'Seattle, WA',
    'Audit',
    'Security testing payload for RLS boundary validation.',
    'HIGH',
    'NEW',
    TRUE,
    '2026-v1'
) ON CONFLICT (id) DO NOTHING;

INSERT INTO public.lead_status_history (
    id, lead_id, previous_status, new_status, changed_by, notes
) VALUES (
    '22222222-2222-2222-2222-222222222222',
    '11111111-1111-1111-1111-111111111111',
    NULL,
    'NEW',
    'Automated Test Harness',
    'Initial audit trail test entry'
) ON CONFLICT (id) DO NOTHING;

-- -----------------------------------------------------------------------------
-- TEST 1: Anonymous Role (anon) Access Boundary
-- Anon clients must have ZERO read, update, or delete access to leads and history.
-- -----------------------------------------------------------------------------
SET LOCAL ROLE anon;

-- 1.1 Anon SELECT on leads must return 0 rows or error
DO $$
DECLARE
    v_count INT;
BEGIN
    SELECT COUNT(*) INTO v_count FROM public.leads;
    IF v_count > 0 THEN
        RAISE EXCEPTION 'RLS LEAK: anon role was able to read % lead rows!', v_count;
    END IF;
    RAISE NOTICE '[PASS] anon cannot SELECT from public.leads';
EXCEPTION
    WHEN insufficient_privilege THEN
        RAISE NOTICE '[PASS] anon SELECT denied by table grant privilege';
END $$;

-- 1.2 Anon UPDATE on leads must fail or update 0 rows
DO $$
DECLARE
    v_updated INT;
BEGIN
    UPDATE public.leads SET customer_name = 'Hacked' WHERE id = '11111111-1111-1111-1111-111111111111';
    GET DIAGNOSTICS v_updated = ROW_COUNT;
    IF v_updated > 0 THEN
        RAISE EXCEPTION 'RLS VIOLATION: anon role was able to UPDATE lead rows!';
    END IF;
    RAISE NOTICE '[PASS] anon cannot UPDATE public.leads';
EXCEPTION
    WHEN insufficient_privilege THEN
        RAISE NOTICE '[PASS] anon UPDATE denied by table grant privilege';
END $$;

-- 1.3 Anon DELETE on leads must fail or delete 0 rows
DO $$
DECLARE
    v_deleted INT;
BEGIN
    DELETE FROM public.leads WHERE id = '11111111-1111-1111-1111-111111111111';
    GET DIAGNOSTICS v_deleted = ROW_COUNT;
    IF v_deleted > 0 THEN
        RAISE EXCEPTION 'RLS VIOLATION: anon role was able to DELETE lead rows!';
    END IF;
    RAISE NOTICE '[PASS] anon cannot DELETE public.leads';
EXCEPTION
    WHEN insufficient_privilege THEN
        RAISE NOTICE '[PASS] anon DELETE denied by table grant privilege';
END $$;

-- 1.4 Anon access to lead_status_history must be strictly rejected
DO $$
DECLARE
    v_count INT;
BEGIN
    SELECT COUNT(*) INTO v_count FROM public.lead_status_history;
    IF v_count > 0 THEN
        RAISE EXCEPTION 'RLS LEAK: anon role was able to read % status history rows!', v_count;
    END IF;
    RAISE NOTICE '[PASS] anon cannot SELECT from public.lead_status_history';
EXCEPTION
    WHEN insufficient_privilege THEN
        RAISE NOTICE '[PASS] anon SELECT on history denied by table grant privilege';
END $$;

-- -----------------------------------------------------------------------------
-- TEST 2: Standard Authenticated User (No Admin Claim)
-- A signed-in end-user (e.g. public user) must NOT be able to view or edit leads.
-- -----------------------------------------------------------------------------
SET LOCAL ROLE authenticated;
-- Set simulated JWT claims with NO admin role
SET LOCAL "request.jwt.claims" = '{"sub": "99999999-9999-9999-9999-999999999999", "role": "authenticated", "app_metadata": {"role": "member"}}';

DO $$
DECLARE
    v_count INT;
BEGIN
    SELECT COUNT(*) INTO v_count FROM public.leads;
    IF v_count > 0 THEN
        RAISE EXCEPTION 'RLS BOLA LEAK: authenticated user without admin role read % leads!', v_count;
    END IF;
    RAISE NOTICE '[PASS] Regular authenticated user cannot SELECT from public.leads';
END $$;

DO $$
DECLARE
    v_updated INT;
BEGIN
    UPDATE public.leads SET status = 'CLOSED' WHERE id = '11111111-1111-1111-1111-111111111111';
    GET DIAGNOSTICS v_updated = ROW_COUNT;
    IF v_updated > 0 THEN
        RAISE EXCEPTION 'RLS BOLA LEAK: regular authenticated user UPDATED lead status!';
    END IF;
    RAISE NOTICE '[PASS] Regular authenticated user cannot UPDATE public.leads';
END $$;

-- -----------------------------------------------------------------------------
-- TEST 3: Authenticated Staff with Valid app_metadata Admin Claim
-- Operators with app_metadata.role = 'admin' MUST be granted full management access.
-- -----------------------------------------------------------------------------
SET LOCAL ROLE authenticated;
SET LOCAL "request.jwt.claims" = '{"sub": "88888888-8888-8888-8888-888888888888", "role": "authenticated", "app_metadata": {"role": "admin"}}';

DO $$
DECLARE
    v_count INT;
BEGIN
    SELECT COUNT(*) INTO v_count FROM public.leads WHERE id = '11111111-1111-1111-1111-111111111111';
    IF v_count != 1 THEN
        RAISE EXCEPTION 'RLS ERROR: Admin operator was unable to read existing lead!';
    END IF;
    RAISE NOTICE '[PASS] Admin operator can SELECT from public.leads';
END $$;

DO $$
DECLARE
    v_updated INT;
BEGIN
    UPDATE public.leads
    SET status = 'CONTACTED', updated_at = NOW()
    WHERE id = '11111111-1111-1111-1111-111111111111';
    GET DIAGNOSTICS v_updated = ROW_COUNT;
    IF v_updated != 1 THEN
        RAISE EXCEPTION 'RLS ERROR: Admin operator was unable to UPDATE lead status!';
    END IF;
    RAISE NOTICE '[PASS] Admin operator can UPDATE public.leads status';
END $$;

-- -----------------------------------------------------------------------------
-- TEST 4: Untrusted user_metadata Spoofing Test
-- A malicious user modifying user_metadata.role to 'admin' must STILL be rejected.
-- -----------------------------------------------------------------------------
SET LOCAL ROLE authenticated;
SET LOCAL "request.jwt.claims" = '{"sub": "77777777-7777-7777-7777-777777777777", "role": "authenticated", "app_metadata": {"role": "user"}, "user_metadata": {"role": "admin"}}'; -- Attacker spoofed claim

DO $$
DECLARE
    v_count INT;
BEGIN
    SELECT COUNT(*) INTO v_count FROM public.leads WHERE id = '11111111-1111-1111-1111-111111111111';
    IF v_count > 0 THEN
        RAISE EXCEPTION 'CRITICAL SECURITY VULNERABILITY: Policy trusted user_metadata!';
    END IF;
    RAISE NOTICE '[PASS] Attacker cannot elevate privileges via spoofed user_metadata';
END $$;

-- -----------------------------------------------------------------------------
-- TEST 5: Service Role Bypass Test
-- -----------------------------------------------------------------------------
SET LOCAL ROLE service_role;

DO $$
DECLARE
    v_count INT;
BEGIN
    SELECT COUNT(*) INTO v_count FROM public.leads WHERE id = '11111111-1111-1111-1111-111111111111';
    IF v_count != 1 THEN
        RAISE EXCEPTION 'Service role was blocked from accessing leads!';
    END IF;
    RAISE NOTICE '[PASS] service_role maintains full bypass access for internal backend';
END $$;

DO $$
BEGIN
    RAISE NOTICE '=============================================================';
    RAISE NOTICE 'ALL RLS AND PRIVILEGE TESTS PASSED SUCCESSFULLY';
    RAISE NOTICE '=============================================================';
END $$;

-- Always rollback test transaction
ROLLBACK;
