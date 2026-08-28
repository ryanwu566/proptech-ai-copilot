-- verify_rls_deny_by_default.sql
--
-- Operator verification for Stage -1 Supabase Security Hotfix (migration 012).
-- Run this in the Supabase SQL Editor (or psql) AGAINST proptech-valuation-db
-- (ref flyhsjcynreuofbcdxod) AFTER applying migration 012. It is READ-ONLY:
-- it performs only SELECTs and role-scoped probe SELECTs. It does NOT write.
--
-- Expected results after remediation:
--   Query 1 (RLS disabled tables in public)      -> 0 rows
--   Query 2 (anon/authenticated table grants)    -> 0 rows
--   Query 3 (anon/authenticated on public schema)-> 0 rows (no USAGE)
--   Query 4 (guard functions mutable search_path)-> 0 rows
--   Query 5 (anon SELECT probe on sensitive tbls)-> permission denied / 0 rows
--
-- ---------------------------------------------------------------------------
-- Query 1: Any base table in public WITHOUT row level security enabled.
--          Must return zero rows. This is the direct rls_disabled_in_public
--          check.
-- ---------------------------------------------------------------------------
select n.nspname as schema, c.relname as table, c.relrowsecurity as rls_enabled
from pg_class c
join pg_namespace n on n.oid = c.relnamespace
where n.nspname = 'public'
  and c.relkind = 'r'
  and c.relrowsecurity = false
order by c.relname;

-- ---------------------------------------------------------------------------
-- Query 2: Any table/sequence privilege still granted to anon / authenticated
--          in the public schema. Must return zero rows.
-- ---------------------------------------------------------------------------
select grantee, table_schema, table_name, privilege_type
from information_schema.role_table_grants
where table_schema = 'public'
  and grantee in ('anon', 'authenticated')
order by table_name, grantee, privilege_type;

-- ---------------------------------------------------------------------------
-- Query 3: Whether anon / authenticated still hold USAGE on schema public.
--          Must return 'f' (false) for both, i.e. usage revoked.
-- ---------------------------------------------------------------------------
select rolname,
       has_schema_privilege(rolname, 'public', 'USAGE') as has_usage
from pg_roles
where rolname in ('anon', 'authenticated')
order by rolname;

-- ---------------------------------------------------------------------------
-- Query 4: PLVR guard functions that still have a mutable (unset) search_path.
--          Must return zero rows (proconfig should contain search_path=...).
-- ---------------------------------------------------------------------------
select p.proname, p.proconfig
from pg_proc p
join pg_namespace n on n.oid = p.pronamespace
where n.nspname = 'public'
  and p.proname like 'plvr_guard_%'
  and (p.proconfig is null
       or not exists (
            select 1 from unnest(p.proconfig) cfg where cfg like 'search_path=%'
       ))
order by p.proname;

-- ---------------------------------------------------------------------------
-- Query 5: Anonymous / authenticated Data API attack probe.
--          Simulates the PostgREST role. Each SELECT must fail with
--          "permission denied" OR return 0 rows (RLS deny-all). Run each
--          block separately; reset role after.
--
--          NOTE: SET ROLE requires that your admin login can assume the role.
--          In Supabase SQL Editor these roles exist. If SET ROLE is not
--          permitted, use the REST API probes in the remediation doc instead.
-- ---------------------------------------------------------------------------
-- Anonymous:
set role anon;
select 'pilot_contacts'       as probe, count(*) from public.pilot_contacts;
select 'pilot_profiles'       as probe, count(*) from public.pilot_profiles;
select 'pilot_feedback'       as probe, count(*) from public.pilot_feedback;
select 'professional_reviews' as probe, count(*) from public.professional_reviews;
select 'tax_analysis_history' as probe, count(*) from public.tax_analysis_history;
select 'schema_migration_ledger' as probe, count(*) from public.schema_migration_ledger;
reset role;

-- Authenticated:
set role authenticated;
select 'pilot_contacts'       as probe, count(*) from public.pilot_contacts;
select 'pilot_profiles'       as probe, count(*) from public.pilot_profiles;
select 'pilot_feedback'       as probe, count(*) from public.pilot_feedback;
select 'professional_reviews' as probe, count(*) from public.professional_reviews;
select 'tax_analysis_history' as probe, count(*) from public.tax_analysis_history;
select 'schema_migration_ledger' as probe, count(*) from public.schema_migration_ledger;
reset role;
