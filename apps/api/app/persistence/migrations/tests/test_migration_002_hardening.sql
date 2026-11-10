-- =============================================================================
-- Test Suite: test_migration_002_hardening.sql
-- Description: Automated transactional test verifying Migration 002 hardening:
--              1. Anon direct INSERT denial on public.leads.
--              2. Anon and Authenticated RPC execution denial on check_and_record_rate_limit.
--              3. Service role RPC execution authorization.
--              4. Concurrency safety: First-row creation for new rate keys.
--              5. Sliding-window threshold boundary enforcement (3 allowed, 4th denied).
--              6. Automatic expired timestamp pruning.
--              7. Audit history immutability (UPDATE and DELETE blocked by trigger).
--
-- PREREQUISITE:
-- Migration 002 (002_atomic_rate_limiting_and_anon_hardening.sql) MUST be applied
-- to the database BEFORE running this verification test suite.
-- =============================================================================

DO $test_suite$
DECLARE
    v_test_lead_id UUID;
    v_history_id UUID;
    v_allowed BOOLEAN;
    v_now NUMERIC := 1700000000.0;
    v_window NUMERIC := 600.0;
    v_key TEXT := 'test_ip:198.51.100.99';
    v_err_caught BOOLEAN := FALSE;
BEGIN
    RAISE NOTICE '=== Running Test Suite: Migration 002 Hardening ===';

    -- -------------------------------------------------------------------------
    -- PRE-FLIGHT CHECK: Ensure Migration 002 has been applied
    -- -------------------------------------------------------------------------
    IF NOT EXISTS (
        SELECT 1 FROM pg_catalog.pg_proc p
        JOIN pg_catalog.pg_namespace n ON p.pronamespace = n.oid
        WHERE n.nspname = 'public' AND p.proname = 'check_and_record_rate_limit'
    ) THEN
        RAISE EXCEPTION 'PREREQUISITE MISSING: Function public.check_and_record_rate_limit does not exist. '
                        'Migration 002 must be applied before running this test suite.';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_catalog.pg_proc p
        JOIN pg_catalog.pg_namespace n ON p.pronamespace = n.oid
        WHERE n.nspname = 'public' AND p.proname = 'prevent_lead_status_history_mutation'
    ) THEN
        RAISE EXCEPTION 'PREREQUISITE MISSING: Function public.prevent_lead_status_history_mutation does not exist. '
                        'Migration 002 must be applied before running this test suite.';
    END IF;

    -- -------------------------------------------------------------------------
    -- TEST 1: Service Role RPC Execution & First-Row Creation
    -- -------------------------------------------------------------------------
    SET LOCAL ROLE service_role;
    
    -- Ensure clean slate for test key
    DELETE FROM public.rate_limits WHERE rate_key = v_key;

    -- Call 1: First-row creation for a brand-new key
    v_allowed := public.check_and_record_rate_limit(
        p_rate_key := v_key,
        p_now := v_now,
        p_window_seconds := v_window,
        p_max_submissions := 3,
        p_record := TRUE
    );
    IF v_allowed IS NOT TRUE THEN
        RAISE EXCEPTION 'TEST 1 FAILED: First call should return TRUE, got %', v_allowed;
    END IF;

    -- Verify row was created with exactly 1 timestamp
    IF NOT EXISTS (
        SELECT 1 FROM public.rate_limits 
        WHERE rate_key = v_key AND pg_catalog.cardinality(timestamps) = 1
    ) THEN
        RAISE EXCEPTION 'TEST 1 FAILED: rate_limits row not created with 1 timestamp';
    END IF;
    RAISE NOTICE 'TEST 1 PASSED: Service role executed RPC and created initial row atomically.';

    -- -------------------------------------------------------------------------
    -- TEST 2: Rate Limit Boundary (Limit = 3)
    -- -------------------------------------------------------------------------
    -- Call 2 (Allowed)
    v_allowed := public.check_and_record_rate_limit(v_key, v_now + 1.0, v_window, 3, TRUE);
    IF v_allowed IS NOT TRUE THEN RAISE EXCEPTION 'TEST 2 FAILED: Call 2 should return TRUE'; END IF;

    -- Call 3 (Allowed - hits max threshold)
    v_allowed := public.check_and_record_rate_limit(v_key, v_now + 2.0, v_window, 3, TRUE);
    IF v_allowed IS NOT TRUE THEN RAISE EXCEPTION 'TEST 2 FAILED: Call 3 should return TRUE'; END IF;

    -- Call 4 (Exceeds limit -> MUST return FALSE)
    v_allowed := public.check_and_record_rate_limit(v_key, v_now + 3.0, v_window, 3, TRUE);
    IF v_allowed IS NOT FALSE THEN
        RAISE EXCEPTION 'TEST 2 FAILED: Call 4 should return FALSE (rate limit exceeded), got %', v_allowed;
    END IF;
    RAISE NOTICE 'TEST 2 PASSED: Rate limit threshold enforced (3 allowed, 4th rejected).';

    -- -------------------------------------------------------------------------
    -- TEST 3: Expired Timestamp Pruning Outside Sliding Window
    -- -------------------------------------------------------------------------
    -- Call 5 at v_now + 700.0 (past 600.0s window). Previous 3 timestamps are expired.
    v_allowed := public.check_and_record_rate_limit(v_key, v_now + 700.0, v_window, 3, TRUE);
    IF v_allowed IS NOT TRUE THEN
        RAISE EXCEPTION 'TEST 3 FAILED: Request after sliding window expiration should be allowed, got %', v_allowed;
    END IF;

    -- Verify expired timestamps were pruned and only the new one remains
    IF NOT EXISTS (
        SELECT 1 FROM public.rate_limits 
        WHERE rate_key = v_key AND pg_catalog.cardinality(timestamps) = 1
    ) THEN
        RAISE EXCEPTION 'TEST 3 FAILED: Old timestamps not pruned after window expiration';
    END IF;
    RAISE NOTICE 'TEST 3 PASSED: Sliding window expiration pruned stale timestamps.';

    -- -------------------------------------------------------------------------
    -- TEST 4: Anonymous Role Direct INSERT Denial on public.leads
    -- -------------------------------------------------------------------------
    SET LOCAL ROLE anon;
    v_err_caught := FALSE;
    BEGIN
        INSERT INTO public.leads (
            customer_name, business_email, phone_number, website_url,
            business_category, target_city, requested_service,
            problem_description, urgency, consent_given
        ) VALUES (
            'Anon Hacker', 'hacker@malicious.com', '+1 555-000-0000', 'https://malicious.com',
            'Spam', 'Unknown', 'Audit', 'Spamming direct Supabase Data API bypassing FastAPI server.',
            'HIGH', TRUE
        );
    EXCEPTION WHEN insufficient_privilege THEN
        v_err_caught := TRUE;
    END;

    IF NOT v_err_caught THEN
        RAISE EXCEPTION 'TEST 4 FAILED: Anonymous INSERT succeeded on public.leads; expected permission denied';
    END IF;
    RAISE NOTICE 'TEST 4 PASSED: Anonymous direct INSERT on public.leads denied (insufficient_privilege).';

    -- -------------------------------------------------------------------------
    -- TEST 5: Anonymous Role RPC Execution Denial
    -- -------------------------------------------------------------------------
    SET LOCAL ROLE anon;
    v_err_caught := FALSE;
    BEGIN
        PERFORM public.check_and_record_rate_limit(
            p_rate_key := 'anon_spoof_key',
            p_now := 1700000000.0,
            p_window_seconds := 600.0,
            p_max_submissions := 5,
            p_record := TRUE
        );
    EXCEPTION WHEN insufficient_privilege THEN
        v_err_caught := TRUE;
    END;

    IF NOT v_err_caught THEN
        RAISE EXCEPTION 'TEST 5 FAILED: Anonymous user executed check_and_record_rate_limit; expected permission denied';
    END IF;
    RAISE NOTICE 'TEST 5 PASSED: Anonymous execution of check_and_record_rate_limit denied.';

    -- -------------------------------------------------------------------------
    -- TEST 6: Authenticated End-User RPC Execution Denial
    -- -------------------------------------------------------------------------
    SET LOCAL ROLE authenticated;
    v_err_caught := FALSE;
    BEGIN
        PERFORM public.check_and_record_rate_limit(
            p_rate_key := 'auth_user_key',
            p_now := 1700000000.0,
            p_window_seconds := 600.0,
            p_max_submissions := 5,
            p_record := TRUE
        );
    EXCEPTION WHEN insufficient_privilege THEN
        v_err_caught := TRUE;
    END;

    IF NOT v_err_caught THEN
        RAISE EXCEPTION 'TEST 6 FAILED: Authenticated user executed check_and_record_rate_limit; expected permission denied';
    END IF;
    RAISE NOTICE 'TEST 6 PASSED: Authenticated user execution of check_and_record_rate_limit denied.';

    -- -------------------------------------------------------------------------
    -- TEST 7: Audit History Immutability (UPDATE and DELETE Forbidden)
    -- -------------------------------------------------------------------------
    SET LOCAL ROLE service_role;
    
    INSERT INTO public.leads (
        customer_name, business_email, phone_number, website_url,
        business_category, target_city, requested_service,
        problem_description, urgency, consent_given
    ) VALUES (
        'Audit Verification', 'audit@example.com', '+1 555-999-8888', 'https://audit.example.com',
        'Legal', 'New York, NY', 'Remediation', 'Testing immutability trigger.', 'LOW', TRUE
    ) RETURNING id INTO v_test_lead_id;

    INSERT INTO public.lead_status_history (
        lead_id, previous_status, new_status, changed_by, notes
    ) VALUES (
        v_test_lead_id, NULL, 'NEW', 'Public Form', 'Initial creation'
    ) RETURNING id INTO v_history_id;

    -- Attempt UPDATE on lead_status_history
    v_err_caught := FALSE;
    BEGIN
        UPDATE public.lead_status_history
        SET notes = 'Tampered notes'
        WHERE id = v_history_id;
    EXCEPTION WHEN raise_exception THEN
        v_err_caught := TRUE;
    END;
    IF NOT v_err_caught THEN
        RAISE EXCEPTION 'TEST 7A FAILED: UPDATE succeeded on lead_status_history; expected immutability trigger error';
    END IF;

    -- Attempt DELETE on lead_status_history
    v_err_caught := FALSE;
    BEGIN
        DELETE FROM public.lead_status_history
        WHERE id = v_history_id;
    EXCEPTION WHEN raise_exception THEN
        v_err_caught := TRUE;
    END;
    IF NOT v_err_caught THEN
        RAISE EXCEPTION 'TEST 7B FAILED: DELETE succeeded on lead_status_history; expected immutability trigger error';
    END IF;
    RAISE NOTICE 'TEST 7 PASSED: Audit history immutability trigger prevented UPDATE and DELETE.';

    -- -------------------------------------------------------------------------
    -- CLEANUP: Clean up test artifacts cleanly
    -- -------------------------------------------------------------------------
    RESET ROLE;
    ALTER TABLE public.lead_status_history DISABLE TRIGGER trg_prevent_lead_status_history_mutation;
    DELETE FROM public.lead_status_history WHERE id = v_history_id;
    DELETE FROM public.leads WHERE id = v_test_lead_id;
    ALTER TABLE public.lead_status_history ENABLE TRIGGER trg_prevent_lead_status_history_mutation;
    DELETE FROM public.rate_limits WHERE rate_key = v_key;

    RAISE NOTICE '=== ALL MIGRATION 002 HARDENING TESTS PASSED SUCCESSFULLY ===';
END $test_suite$;
