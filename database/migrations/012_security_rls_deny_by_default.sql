-- 012_security_rls_deny_by_default.sql
--
-- Stage -1 Emergency Supabase Security Hotfix.
--
-- Purpose
-- -------
-- Close the Supabase Security Advisor `rls_disabled_in_public` findings and
-- establish a deny-by-default posture for the `public` schema of the
-- proptech-valuation-db project (ref flyhsjcynreuofbcdxod).
--
-- Context / access model
-- ----------------------
-- The application runtime connects to Postgres DIRECTLY via psycopg using a
-- privileged connection role (DATABASE_URL / VALUATION_DATABASE_URL /
-- PILOT_EVIDENCE_DATABASE_URL). It NEVER uses the Supabase Data API (PostgREST)
-- `anon` / `authenticated` roles, the anon key, the service_role key, or a
-- browser Supabase client (verified: no @supabase/supabase-js, no anon key, no
-- NEXT_PUBLIC_SUPABASE anywhere in the repository). The frontend talks only to
-- the FastAPI backend.
--
-- Consequence: enabling RLS and revoking `anon`/`authenticated` privileges does
-- NOT affect backend functionality, because the owning/privileged connection
-- role BYPASSES RLS (we ENABLE, and deliberately do NOT FORCE, row level
-- security). It only closes the auto-exposed PostgREST Data API surface that the
-- application does not use but Supabase enables by default.
--
-- Design principles (deny by default)
-- -----------------------------------
--   * ENABLE (not FORCE) ROW LEVEL SECURITY on every base table in `public`.
--   * Add NO permissive policy. RLS enabled + no policy = deny all for every
--     non-owner role. We deliberately do NOT create `USING (true)` policies.
--   * REVOKE all privileges from `anon`, `authenticated`, and `PUBLIC` on every
--     table, sequence, and function in `public`.
--   * Harden the existing SECURITY INVOKER guard functions with a fixed
--     search_path (they already fully-qualify their object references).
--   * Set ALTER DEFAULT PRIVILEGES so future tables/sequences/functions in
--     `public` are not automatically exposed to `anon` / `authenticated`.
--     This protects the upcoming VNext tables (properties, cases, evidence,
--     documents, contacts, CRM) from inheriting unsafe public access.
--
-- Safety
-- ------
-- This migration is ADDITIVE and IDEMPOTENT. It performs NO destructive
-- operation: it does not DROP tables, DELETE rows, rewrite PLVR facts, alter
-- valuation formulas, or change application product behaviour. It is safe to
-- re-run. All statements guard for object/role existence.
--
-- Role existence is guarded because a plain (non-Supabase) Postgres instance
-- used for CI / disposable validation may not have the `anon` /
-- `authenticated` / `service_role` roles. On such instances the REVOKE/ALTER
-- DEFAULT PRIVILEGES for those roles are simply skipped; RLS is still enabled.

-- ---------------------------------------------------------------------------
-- 1. Enable Row Level Security on every base table in the public schema.
--    Deny-by-default: no policy is added, so non-owner roles get zero rows and
--    cannot write. The privileged backend role (table owner) bypasses RLS.
-- ---------------------------------------------------------------------------
do $$
declare
    target regclass;
begin
    for target in
        select c.oid::regclass
        from pg_class c
        join pg_namespace n on n.oid = c.relnamespace
        where n.nspname = 'public'
          and c.relkind = 'r'            -- ordinary tables only (not views/matviews)
          and not c.relrowsecurity        -- skip tables that already have RLS enabled
    loop
        execute format('alter table %s enable row level security', target);
    end loop;
end
$$;

-- ---------------------------------------------------------------------------
-- 2. Revoke every privilege on public tables/sequences from the Data API roles
--    and from PUBLIC. Guarded for role existence so CI/plain Postgres is fine.
-- ---------------------------------------------------------------------------
do $$
begin
    -- PUBLIC pseudo-role always exists.
    execute 'revoke all on all tables in schema public from public';
    execute 'revoke all on all sequences in schema public from public';
    execute 'revoke all on all functions in schema public from public';

    if exists (select 1 from pg_roles where rolname = 'anon') then
        execute 'revoke all on all tables in schema public from anon';
        execute 'revoke all on all sequences in schema public from anon';
        execute 'revoke all on all functions in schema public from anon';
        execute 'revoke usage on schema public from anon';
    end if;

    if exists (select 1 from pg_roles where rolname = 'authenticated') then
        execute 'revoke all on all tables in schema public from authenticated';
        execute 'revoke all on all sequences in schema public from authenticated';
        execute 'revoke all on all functions in schema public from authenticated';
        execute 'revoke usage on schema public from authenticated';
    end if;
end
$$;

-- ---------------------------------------------------------------------------
-- 3. Harden the existing PLVR guard functions.
--    They are already declared SECURITY INVOKER and already fully-qualify all
--    referenced objects (public.plvr_dataset_generations, ...), so pinning
--    search_path is safe and resolves the Advisor "mutable search_path"
--    (function_search_path_mutable) warnings. EXECUTE is revoked from the Data
--    API roles as well. Guarded so it is a no-op if a function is absent.
-- ---------------------------------------------------------------------------
do $$
declare
    guard_fn text;
    fn_regproc text;
begin
    foreach guard_fn in array array[
        'public.plvr_guard_frozen_generation_manifest()',
        'public.plvr_guard_generation_transaction()',
        'public.plvr_guard_generation_derived_row()',
        'public.plvr_guard_active_generation()'
    ]
    loop
        -- to_regprocedure returns NULL when the function does not exist.
        if to_regprocedure(guard_fn) is not null then
            execute format('alter function %s set search_path = pg_catalog, public', guard_fn);
            execute format('revoke all on function %s from public', guard_fn);
            if exists (select 1 from pg_roles where rolname = 'anon') then
                execute format('revoke all on function %s from anon', guard_fn);
            end if;
            if exists (select 1 from pg_roles where rolname = 'authenticated') then
                execute format('revoke all on function %s from authenticated', guard_fn);
            end if;
        end if;
    end loop;
end
$$;

-- ---------------------------------------------------------------------------
-- 4. Default privilege hardening.
--    Ensure that future objects created in `public` by the migration/owner role
--    are NOT automatically granted to anon / authenticated. This is what stops
--    the next new table (including VNext properties/cases/evidence/documents/
--    contacts/CRM) from silently re-opening the Data API surface.
--
--    ALTER DEFAULT PRIVILEGES only affects objects created AFTER this runs and
--    only for objects created by the specified role. We apply it FOR the role
--    that executes this migration (current_user), which is the owner role the
--    migration runner uses.
-- ---------------------------------------------------------------------------
do $$
declare
    owner_role text := current_user;
begin
    if exists (select 1 from pg_roles where rolname = 'anon') then
        execute format(
            'alter default privileges for role %I in schema public revoke all on tables from anon',
            owner_role);
        execute format(
            'alter default privileges for role %I in schema public revoke all on sequences from anon',
            owner_role);
        execute format(
            'alter default privileges for role %I in schema public revoke all on functions from anon',
            owner_role);
    end if;

    if exists (select 1 from pg_roles where rolname = 'authenticated') then
        execute format(
            'alter default privileges for role %I in schema public revoke all on tables from authenticated',
            owner_role);
        execute format(
            'alter default privileges for role %I in schema public revoke all on sequences from authenticated',
            owner_role);
        execute format(
            'alter default privileges for role %I in schema public revoke all on functions from authenticated',
            owner_role);
    end if;

    -- Also close default grants to PUBLIC for functions (Postgres grants
    -- EXECUTE to PUBLIC by default on new functions).
    execute format(
        'alter default privileges for role %I in schema public revoke all on functions from public',
        owner_role);
    execute format(
        'alter default privileges for role %I in schema public revoke all on tables from public',
        owner_role);
end
$$;

-- ---------------------------------------------------------------------------
-- 5. Documentation marker comment on the ledger table (non-functional).
-- ---------------------------------------------------------------------------
comment on table public.schema_migration_ledger is
    'Operational migration ledger. RLS enabled (deny-by-default) by migration 012; contains no secrets or business records.';
