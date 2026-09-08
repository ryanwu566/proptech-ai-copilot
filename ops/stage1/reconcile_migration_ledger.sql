-- NOT A MIGRATION
-- NOT AUTHORIZED FOR PRODUCTION EXECUTION
-- REQUIRES SEPARATE LIVE MUTATION APPROVAL
--
-- Stage 1 custom-ledger reconciliation review artifact.
-- This file is intentionally outside database/migrations and is not registered.
-- Run it only after a separately authorized live mutation window, current
-- backup/PITR verification, peer review, and operator audit capture.
--
-- Durable writes are limited to five checksum changes and four inserts in
-- public.schema_migration_ledger. Historical migration SQL is never replayed.

begin transaction isolation level serializable;

lock table public.schema_migration_ledger in exclusive mode;

-- Capture this result in the operator record before any write.
select migration_id, schema_version, applied_at, release_version, checksum
from public.schema_migration_ledger
order by migration_id;

do $stage1_ledger_reconciliation$
declare
    baseline_recorded_at timestamptz := transaction_timestamp();
    changed_rows bigint;
    observed_count bigint;
    observed_hash text;
    business_counts_before bigint[];
    history_before jsonb;
begin
    -- Require the exact six-row forensic state, including provenance fields.
    if exists (
        with expected(
            migration_id, schema_version, applied_at, release_version, checksum
        ) as (
            values
              ('001_add_dedupe_key_to_real_price_transactions', 'schema-001',
               '2026-08-14 03:43:49.208983+00'::timestamptz,
               'phase2f-approval-a-ledger-baseline',
               '557eef5065a66083aadb1c189ed68dc1271cfdfff48547abcf7f54be9fee0bcd'),
              ('002_add_market_direct_query_indexes', 'schema-002',
               '2026-08-14 03:43:49.208983+00'::timestamptz,
               'phase2f-approval-a-ledger-baseline',
               'ca201d932388090018e5543f89d69d43d812c6596e995d354b30b50f52e1203f'),
              ('002_expand_valuation_import_runs', 'schema-002',
               '2026-08-14 03:43:49.208983+00'::timestamptz,
               'phase2f-approval-a-ledger-baseline',
               'da83474b55277316a7e8a35c490eb2a31595781bc2331f2d1aba69caea2c8caa'),
              ('003_add_market_region_coverage', 'schema-003',
               '2026-08-14 03:43:49.208983+00'::timestamptz,
               'phase2f-approval-a-ledger-baseline',
               '34171ca38e64509c29ae2075874388cf9736ae3df7752c6ae105118d3ee90ce5'),
              ('007_add_schema_migration_ledger', 'schema-007',
               '2026-08-14 03:43:49.208983+00'::timestamptz,
               'phase2f-approval-a-ledger-baseline',
               'f4a8ef650ab6bbce8bd1909345785411f350eb6aabe23d0d377fb674ef5934f5'),
              ('010_add_plvr_generation_schema', 'schema-010',
               '2026-08-14 03:43:49.208983+00'::timestamptz,
               'phase2f-approval-a-ledger-baseline',
               'fcf69fc2d3b5e6419e2d94a6d92abc03c9b4424204e9bd129b85ea749ebed4a5')
        ),
        differences as (
            select coalesce(expected.migration_id, actual.migration_id)
            from expected
            full join public.schema_migration_ledger actual using (migration_id)
            where actual.migration_id is null
               or expected.migration_id is null
               or actual.schema_version is distinct from expected.schema_version
               or actual.applied_at is distinct from expected.applied_at
               or actual.release_version is distinct from expected.release_version
               or actual.checksum is distinct from expected.checksum
        )
        select 1 from differences
    ) or (select count(*) from public.schema_migration_ledger) <> 6 then
        raise exception 'precondition_failed: exact six-row ledger state';
    end if;

    -- Supabase history independently proves 004, 005, 006 and 012 ran.
    if to_regclass('supabase_migrations.schema_migrations') is null
       or to_regprocedure('extensions.digest(bytea,text)') is null then
        raise exception 'precondition_failed: Supabase history proof unavailable';
    end if;
    select count(*) into observed_count
    from supabase_migrations.schema_migrations h
    where cardinality(h.statements) = 1
      and (
        (h.version = '20260818094700' and h.name = 'add_pilot_evidence'
         and encode(extensions.digest(convert_to(h.statements[1], 'UTF8'), 'sha256'), 'hex')
             = 'ba2a3f21605983f13b16648e344e3a71baf677ee7e086d155a39dc9b2220b516')
        or
        (h.version = '20260818094730' and h.name = 'add_pilot_security_indexes'
         and encode(extensions.digest(convert_to(h.statements[1], 'UTF8'), 'sha256'), 'hex')
             = '7da6cffddc6a715bfc041fe37eb9ebf19574e30ef5379a4917db6bc634614d3c')
        or
        (h.version = '20260818094742' and h.name = 'add_tax_analysis_history'
         and encode(extensions.digest(convert_to(h.statements[1], 'UTF8'), 'sha256'), 'hex')
             = 'cc0e6bc09b4f0736c6ddb012ff34912db0385339c93d329d39203e696dc3d1c0')
        or
        (h.version = '20260828031611' and h.name = 'security_rls_deny_by_default'
         and encode(extensions.digest(convert_to(h.statements[1], 'UTF8'), 'sha256'), 'hex')
             in (
                 -- Exact deployed text, then the equivalent canonical registry
                 -- text accepted only for the disposable rehearsal fixture.
                 'be150b2576aca111f0b6bc3075532c4b0808174b912ac46abb5a8409bdfaa6e0',
                 'bb1551d4e7fda1d3c7df99e3fd64a53f7fb05a8dcfb7ec0049c18ae6c2dfa056'
             ))
      );
    if observed_count <> 4 then
        raise exception 'precondition_failed: Supabase history mismatch';
    end if;

    -- Exact selected columns introduced by 001 and both 002 files.
    select count(*), md5(string_agg(
               concat_ws('|', c.table_name, c.column_name, c.ordinal_position,
                         c.udt_schema, c.udt_name, c.is_nullable,
                         coalesce(c.column_default, '')),
               E'\n' order by c.table_name, c.ordinal_position))
      into observed_count, observed_hash
      from information_schema.columns c
     where c.table_schema = 'public'
       and c.table_name in ('real_price_transactions', 'valuation_import_runs')
       and c.column_name in (
           'dedupe_key', 'city_scope', 'district_scope', 'road_scope',
           'input_file_count', 'read_rows', 'accepted_rows', 'inserted_rows',
           'updated_rows', 'skipped_duplicate_rows', 'excluded_rows');
    if observed_count <> 11 or observed_hash <> '6dd82bcb2ecc516651cc28c428a16a6d' then
        raise exception 'precondition_failed: 001/002 columns mismatch';
    end if;

    select count(*), md5(string_agg(
               concat_ws('|', i.indexname, i.indexdef),
               E'\n' order by i.indexname))
      into observed_count, observed_hash
      from pg_indexes i
     where i.schemaname = 'public'
       and i.indexname in (
           'uq_real_price_source_dedupe_key',
           'idx_market_direct_query_county_period',
           'idx_market_direct_query_county_district_period');
    if observed_count <> 3 or observed_hash <> '6e8bd68e3b5aa27299cdd744376e5439' then
        raise exception 'precondition_failed: 001/002 indexes mismatch';
    end if;

    -- Exact 003 catalog and proof that the similar 008 shape is absent.
    select count(*), md5(string_agg(
               concat_ws('|', c.table_name, c.column_name, c.ordinal_position,
                         c.udt_schema, c.udt_name, c.is_nullable,
                         coalesce(c.column_default, '')),
               E'\n' order by c.table_name, c.ordinal_position))
      into observed_count, observed_hash
      from information_schema.columns c
     where c.table_schema = 'public'
       and c.table_name = 'market_region_coverage';
    if observed_count <> 6 or observed_hash <> 'f681f236cccbecce6fd558f1b287e678'
       or exists (
           select 1 from information_schema.columns
           where table_schema = 'public'
             and table_name = 'market_region_coverage'
             and column_name = 'release_id'
       ) then
        raise exception 'precondition_failed: 003 catalog mismatch';
    end if;

    -- Exact 004 columns/constraints and the complete 004+005 index set.
    select count(*), md5(string_agg(
               concat_ws('|', c.table_name, c.column_name, c.ordinal_position,
                         c.udt_schema, c.udt_name, c.is_nullable,
                         coalesce(c.column_default, '')),
               E'\n' order by c.table_name, c.ordinal_position))
      into observed_count, observed_hash
      from information_schema.columns c
     where c.table_schema = 'public'
       and c.table_name in (
           'pilot_campaigns', 'pilot_sessions', 'pilot_consents',
           'pilot_profiles', 'pilot_contacts', 'pilot_events',
           'pilot_feedback', 'professional_reviews');
    if observed_count <> 88 or observed_hash <> 'b04525126e78daaa099fabe0d9e1a77c' then
        raise exception 'precondition_failed: 004 columns mismatch';
    end if;

    select count(*), md5(string_agg(
               concat_ws('|', r.relname, x.conname, x.contype,
                         pg_get_constraintdef(x.oid, true)),
               E'\n' order by r.relname, x.conname))
      into observed_count, observed_hash
      from pg_class r
      join pg_namespace n on n.oid = r.relnamespace and n.nspname = 'public'
      join pg_constraint x on x.conrelid = r.oid
     where r.relname in (
           'pilot_campaigns', 'pilot_sessions', 'pilot_consents',
           'pilot_profiles', 'pilot_contacts', 'pilot_events',
           'pilot_feedback', 'professional_reviews');
    if observed_count <> 22 or observed_hash <> '397b9530a6fda39661d06cb7ceaca985' then
        raise exception 'precondition_failed: 004 constraints mismatch';
    end if;

    select count(*), md5(string_agg(
               concat_ws('|', i.indexname, i.indexdef),
               E'\n' order by i.indexname))
      into observed_count, observed_hash
      from pg_indexes i
     where i.schemaname = 'public'
       and i.tablename in (
           'pilot_campaigns', 'pilot_sessions', 'pilot_consents',
           'pilot_profiles', 'pilot_contacts', 'pilot_events',
           'pilot_feedback', 'professional_reviews');
    if observed_count <> 16 or observed_hash <> 'b165db9aa7dd12f6d1e4b5e3449666b7' then
        raise exception 'precondition_failed: 004/005 indexes mismatch';
    end if;

    -- Exact 006 catalog.
    select count(*), md5(string_agg(
               concat_ws('|', c.table_name, c.column_name, c.ordinal_position,
                         c.udt_schema, c.udt_name, c.is_nullable,
                         coalesce(c.column_default, '')),
               E'\n' order by c.table_name, c.ordinal_position))
      into observed_count, observed_hash
      from information_schema.columns c
     where c.table_schema = 'public'
       and c.table_name = 'tax_analysis_history';
    if observed_count <> 8 or observed_hash <> '22f2bd72fccef149e338520c817db037' then
        raise exception 'precondition_failed: 006 columns mismatch';
    end if;

    select count(*), md5(string_agg(
               concat_ws('|', i.indexname, i.indexdef),
               E'\n' order by i.indexname))
      into observed_count, observed_hash
      from pg_indexes i
     where i.schemaname = 'public'
       and i.tablename = 'tax_analysis_history';
    if observed_count <> 3 or observed_hash <> '3790479b830d9529b39bf2090076b916' then
        raise exception 'precondition_failed: 006 indexes mismatch';
    end if;

    -- Exact 007 structure; no trigger may redirect ledger writes.
    select count(*), md5(string_agg(
               concat_ws('|', c.table_name, c.column_name, c.ordinal_position,
                         c.udt_schema, c.udt_name, c.is_nullable,
                         coalesce(c.column_default, '')),
               E'\n' order by c.table_name, c.ordinal_position))
      into observed_count, observed_hash
      from information_schema.columns c
     where c.table_schema = 'public'
       and c.table_name = 'schema_migration_ledger';
    if observed_count <> 5 or observed_hash <> 'a1391c16b5ab6450d4f2980064fcad25'
       or exists (
           select 1 from pg_trigger t
           where t.tgrelid = 'public.schema_migration_ledger'::regclass
             and not t.tgisinternal
       ) then
        raise exception 'precondition_failed: 007 catalog mismatch';
    end if;

    -- Exact 010 columns, constraints, indexes, triggers, functions, views,
    -- and comments; the row itself is later verified unchanged.
    select count(*), md5(string_agg(
               concat_ws('|', c.table_name, c.column_name, c.ordinal_position,
                         c.udt_schema, c.udt_name, c.is_nullable,
                         coalesce(c.column_default, '')),
               E'\n' order by c.table_name, c.ordinal_position))
      into observed_count, observed_hash
      from information_schema.columns c
     where c.table_schema = 'public'
       and c.table_name in (
           'plvr_dataset_generations', 'plvr_generation_transactions',
           'plvr_generation_market_aggregates',
           'plvr_generation_region_coverage', 'plvr_active_dataset',
           'plvr_generation_load_checkpoints');
    if observed_count <> 86 or observed_hash <> '5789d4ae6c0ddacc6b7d530fbd412ebb' then
        raise exception 'precondition_failed: 010 columns mismatch';
    end if;

    select count(*), md5(string_agg(
               concat_ws('|', r.relname, x.conname, x.contype,
                         pg_get_constraintdef(x.oid, true)),
               E'\n' order by r.relname, x.conname))
      into observed_count, observed_hash
      from pg_class r
      join pg_namespace n on n.oid = r.relnamespace and n.nspname = 'public'
      join pg_constraint x on x.conrelid = r.oid
     where r.relname in (
           'plvr_dataset_generations', 'plvr_generation_transactions',
           'plvr_generation_market_aggregates',
           'plvr_generation_region_coverage', 'plvr_active_dataset',
           'plvr_generation_load_checkpoints');
    if observed_count <> 31 or observed_hash <> '94d993dd79acebd0197608179756f1b7' then
        raise exception 'precondition_failed: 010 constraints mismatch';
    end if;

    select count(*), md5(string_agg(
               concat_ws('|', i.indexname, i.indexdef),
               E'\n' order by i.indexname))
      into observed_count, observed_hash
      from pg_indexes i
     where i.schemaname = 'public'
       and i.tablename in (
           'plvr_dataset_generations', 'plvr_generation_transactions',
           'plvr_generation_market_aggregates',
           'plvr_generation_region_coverage', 'plvr_active_dataset',
           'plvr_generation_load_checkpoints');
    if observed_count <> 14 or observed_hash <> 'c45bab43ebc9e0c353ac85834bdcafad' then
        raise exception 'precondition_failed: 010 indexes mismatch';
    end if;

    select count(*), md5(string_agg(
               concat_ws('|', r.relname, t.tgname,
                         pg_get_triggerdef(t.oid, true)),
               E'\n' order by r.relname, t.tgname))
      into observed_count, observed_hash
      from pg_trigger t
      join pg_class r on r.oid = t.tgrelid
      join pg_namespace n on n.oid = r.relnamespace
     where n.nspname = 'public'
       and not t.tgisinternal
       and t.tgname like 'trg_plvr_%';
    if observed_count <> 5 or observed_hash <> '96ebffe557e94ce747a4a32c3dad5cf9' then
        raise exception 'precondition_failed: 010 triggers mismatch';
    end if;

    select count(*), md5(string_agg(
               concat_ws('|', p.proname, p.prosecdef,
                         coalesce(array_to_string(p.proconfig, ','), ''),
                         pg_get_functiondef(p.oid)),
               E'\n' order by p.proname))
      into observed_count, observed_hash
      from pg_proc p
      join pg_namespace n on n.oid = p.pronamespace
     where n.nspname = 'public'
       and p.proname like 'plvr_guard_%';
    if observed_count <> 4 or observed_hash <> 'b1b438a22a8191241dbcbb859c497d37' then
        raise exception 'precondition_failed: 010/012 functions mismatch';
    end if;

    select count(*), md5(string_agg(
               concat_ws('|', v.viewname, v.definition),
               E'\n' order by v.viewname))
      into observed_count, observed_hash
      from pg_views v
     where v.schemaname = 'public'
       and v.viewname in (
           'plvr_active_transactions', 'plvr_active_market_aggregates',
           'plvr_active_region_coverage');
    if observed_count <> 3 or observed_hash <> '63a5a1cee8637f7fcc22760796a1779e' then
        raise exception 'precondition_failed: 010 views mismatch';
    end if;

    select count(*), md5(string_agg(
               concat_ws('|', r.relname, obj_description(r.oid, 'pg_class')),
               E'\n' order by r.relname))
      into observed_count, observed_hash
      from pg_class r
      join pg_namespace n on n.oid = r.relnamespace
     where n.nspname = 'public'
       and r.relname in (
           'plvr_dataset_generations', 'plvr_generation_transactions',
           'plvr_generation_market_aggregates',
           'plvr_generation_region_coverage', 'plvr_active_dataset',
           'plvr_generation_load_checkpoints');
    if observed_count <> 6 or observed_hash <> 'dd71461d748513bf64bfdc168dd85029' then
        raise exception 'precondition_failed: 010 comments mismatch';
    end if;

    -- 012 deny-by-default posture across the exact 22 public base tables.
    select count(*) into observed_count
      from pg_class r
      join pg_namespace n on n.oid = r.relnamespace
     where n.nspname = 'public' and r.relkind = 'r';
    if observed_count <> 22
       or (select count(*) from pg_class r join pg_namespace n on n.oid = r.relnamespace
            where n.nspname = 'public' and r.relkind = 'r' and r.relrowsecurity) <> 22
       or exists (
           select 1 from pg_class r join pg_namespace n on n.oid = r.relnamespace
           where n.nspname = 'public' and r.relkind = 'r' and r.relforcerowsecurity
       )
       or exists (
           select 1 from pg_policy p join pg_class r on r.oid = p.polrelid
           join pg_namespace n on n.oid = r.relnamespace where n.nspname = 'public'
       ) then
        raise exception 'precondition_failed: 012 RLS posture mismatch';
    end if;

    if exists (
        select 1
        from information_schema.table_privileges
        where table_schema = 'public'
          and grantee in ('PUBLIC', 'anon', 'authenticated')
    ) or exists (
        select 1
        from information_schema.routine_privileges
        where specific_schema = 'public'
          and grantee in ('PUBLIC', 'anon', 'authenticated')
    ) or exists (
        select 1
        from information_schema.usage_privileges
        where object_schema = 'public'
          and grantee in ('PUBLIC', 'anon', 'authenticated')
    ) then
        raise exception 'precondition_failed: 012 grants mismatch';
    end if;

    if exists (
        select 1
        from (values ('anon'), ('authenticated')) role_name(name)
        join pg_roles role_record on role_record.rolname = role_name.name
        cross join pg_class relation
        join pg_namespace namespace on namespace.oid = relation.relnamespace
        where namespace.nspname = 'public'
          and relation.relkind in ('r', 'v')
          and (
              has_table_privilege(role_name.name, relation.oid, 'SELECT')
              or has_table_privilege(role_name.name, relation.oid, 'INSERT')
              or has_table_privilege(role_name.name, relation.oid, 'UPDATE')
              or has_table_privilege(role_name.name, relation.oid, 'DELETE')
          )
    ) or exists (
        select 1
        from (values ('anon'), ('authenticated')) role_name(name)
        join pg_roles role_record on role_record.rolname = role_name.name
        cross join pg_class sequence_record
        join pg_namespace namespace on namespace.oid = sequence_record.relnamespace
        where namespace.nspname = 'public'
          and sequence_record.relkind = 'S'
          and (
              has_sequence_privilege(role_name.name, sequence_record.oid, 'USAGE')
              or has_sequence_privilege(role_name.name, sequence_record.oid, 'SELECT')
              or has_sequence_privilege(role_name.name, sequence_record.oid, 'UPDATE')
          )
    ) or exists (
        select 1
        from (values ('anon'), ('authenticated')) role_name(name)
        join pg_roles role_record on role_record.rolname = role_name.name
        cross join pg_proc routine
        join pg_namespace namespace on namespace.oid = routine.pronamespace
        where namespace.nspname = 'public'
          and has_function_privilege(role_name.name, routine.oid, 'EXECUTE')
    ) then
        raise exception 'precondition_failed: 012 effective privileges mismatch';
    end if;

    if exists (
        select 1
        from pg_default_acl d
        join pg_roles owner on owner.oid = d.defaclrole
        join lateral aclexplode(d.defaclacl) a on true
        left join pg_roles grantee on grantee.oid = a.grantee
        where owner.rolname = current_user
          and d.defaclnamespace = 'public'::regnamespace
          and coalesce(grantee.rolname, 'PUBLIC')
              in ('PUBLIC', 'anon', 'authenticated')
    ) then
        raise exception 'precondition_failed: 012 default privileges mismatch';
    end if;

    if obj_description('public.schema_migration_ledger'::regclass, 'pg_class')
       is distinct from
       'Operational migration ledger. RLS enabled (deny-by-default) by migration 012; contains no secrets or business records.' then
        raise exception 'precondition_failed: 012 ledger marker mismatch';
    end if;

    -- Migrations 008, 009, 011 and 013-017 must remain absent.
    if exists (
        select 1
        from unnest(array[
            'public.official_market_releases',
            'public.official_market_artifacts',
            'public.market_transactions',
            'public.market_transaction_quality_events',
            'public.market_region_period_aggregates',
            'public.market_import_runs',
            'public.market_import_checkpoints',
            'public.official_market_region_coverage'
        ]) object_name
        where to_regclass(object_name) is not null
    ) or to_regnamespace('compact_green') is not null
       or to_regnamespace('vnext_core') is not null
       or to_regnamespace('vnext_private') is not null
       or exists (select 1 from pg_roles where rolname = 'vnext_api') then
        raise exception 'precondition_failed: unapplied migration effect present';
    end if;

    -- The preservation sentinel must be exact.
    select to_jsonb(h) into history_before
    from public.tax_analysis_history h
    where h.id = 1 and h.case_id = 'HISTORY-001';
    if history_before is null
       or (select count(*) from public.tax_analysis_history
           where case_id = 'HISTORY-001') <> 1 then
        raise exception 'precondition_failed: HISTORY-001 sentinel mismatch';
    end if;

    select array[
        (select count(*) from public.pilot_campaigns),
        (select count(*) from public.pilot_sessions),
        (select count(*) from public.pilot_consents),
        (select count(*) from public.pilot_profiles),
        (select count(*) from public.pilot_contacts),
        (select count(*) from public.pilot_events),
        (select count(*) from public.pilot_feedback),
        (select count(*) from public.professional_reviews),
        (select count(*) from public.tax_analysis_history)
    ] into business_counts_before;

    -- The only UPDATE: five exact historical CRLF checksum normalizations.
    update public.schema_migration_ledger actual
       set checksum = expected.canonical_checksum
      from (values
        ('001_add_dedupe_key_to_real_price_transactions',
         '557eef5065a66083aadb1c189ed68dc1271cfdfff48547abcf7f54be9fee0bcd',
         '2eb4a3e8652d3f18cac9c200d38b3bf350e77bd36aa103f8b76ecf4004143223'),
        ('002_add_market_direct_query_indexes',
         'ca201d932388090018e5543f89d69d43d812c6596e995d354b30b50f52e1203f',
         '2cb6da19a01415ffee34845aa294843257cce7f9991803e0ca470e3405cfc310'),
        ('002_expand_valuation_import_runs',
         'da83474b55277316a7e8a35c490eb2a31595781bc2331f2d1aba69caea2c8caa',
         '0108c13fad4d0310e291c0d2e041868c7d59b8fb2f47739831139fa3039b2d64'),
        ('003_add_market_region_coverage',
         '34171ca38e64509c29ae2075874388cf9736ae3df7752c6ae105118d3ee90ce5',
         '267db5dcba4c12646b78f480b289cbd289a323bc205a0a8fe5ba507290efb16b'),
        ('007_add_schema_migration_ledger',
         'f4a8ef650ab6bbce8bd1909345785411f350eb6aabe23d0d377fb674ef5934f5',
         '1d1d20edf40b9d2782dd9e314d7e4a2d35ac0aaac5d1570494e58f3e3d982996')
      ) expected(migration_id, historical_checksum, canonical_checksum)
     where actual.migration_id = expected.migration_id
       and actual.checksum = expected.historical_checksum;
    get diagnostics changed_rows = row_count;
    if changed_rows <> 5 then
        raise exception 'mutation_failed: expected five checksum updates';
    end if;

    -- The only INSERT: four truthful ledger baselines recorded now.
    insert into public.schema_migration_ledger (
        migration_id, schema_version, applied_at, release_version, checksum
    ) values
      ('004_add_pilot_evidence', 'schema-004', baseline_recorded_at,
       'stage1-ledger-reconciliation-v1',
       'ba2a3f21605983f13b16648e344e3a71baf677ee7e086d155a39dc9b2220b516'),
      ('005_add_pilot_security_indexes', 'schema-005', baseline_recorded_at,
       'stage1-ledger-reconciliation-v1',
       '7da6cffddc6a715bfc041fe37eb9ebf19574e30ef5379a4917db6bc634614d3c'),
      ('006_add_tax_analysis_history', 'schema-006', baseline_recorded_at,
       'stage1-ledger-reconciliation-v1',
       'cc0e6bc09b4f0736c6ddb012ff34912db0385339c93d329d39203e696dc3d1c0'),
      ('012_security_rls_deny_by_default', 'schema-012', baseline_recorded_at,
       'stage1-ledger-reconciliation-v1',
       'bb1551d4e7fda1d3c7df99e3fd64a53f7fb05a8dcfb7ec0049c18ae6c2dfa056');
    get diagnostics changed_rows = row_count;
    if changed_rows <> 4 then
        raise exception 'mutation_failed: expected four baseline inserts';
    end if;

    -- Exact ten-row target. 010 and all historical metadata stay unchanged;
    -- the four baselines share only the truthful reconciliation timestamp.
    if exists (
        with expected(
            migration_id, schema_version, applied_at, release_version, checksum
        ) as (
            values
              ('001_add_dedupe_key_to_real_price_transactions', 'schema-001',
               '2026-08-14 03:43:49.208983+00'::timestamptz,
               'phase2f-approval-a-ledger-baseline',
               '2eb4a3e8652d3f18cac9c200d38b3bf350e77bd36aa103f8b76ecf4004143223'),
              ('002_add_market_direct_query_indexes', 'schema-002',
               '2026-08-14 03:43:49.208983+00'::timestamptz,
               'phase2f-approval-a-ledger-baseline',
               '2cb6da19a01415ffee34845aa294843257cce7f9991803e0ca470e3405cfc310'),
              ('002_expand_valuation_import_runs', 'schema-002',
               '2026-08-14 03:43:49.208983+00'::timestamptz,
               'phase2f-approval-a-ledger-baseline',
               '0108c13fad4d0310e291c0d2e041868c7d59b8fb2f47739831139fa3039b2d64'),
              ('003_add_market_region_coverage', 'schema-003',
               '2026-08-14 03:43:49.208983+00'::timestamptz,
               'phase2f-approval-a-ledger-baseline',
               '267db5dcba4c12646b78f480b289cbd289a323bc205a0a8fe5ba507290efb16b'),
              ('004_add_pilot_evidence', 'schema-004', baseline_recorded_at,
               'stage1-ledger-reconciliation-v1',
               'ba2a3f21605983f13b16648e344e3a71baf677ee7e086d155a39dc9b2220b516'),
              ('005_add_pilot_security_indexes', 'schema-005', baseline_recorded_at,
               'stage1-ledger-reconciliation-v1',
               '7da6cffddc6a715bfc041fe37eb9ebf19574e30ef5379a4917db6bc634614d3c'),
              ('006_add_tax_analysis_history', 'schema-006', baseline_recorded_at,
               'stage1-ledger-reconciliation-v1',
               'cc0e6bc09b4f0736c6ddb012ff34912db0385339c93d329d39203e696dc3d1c0'),
              ('007_add_schema_migration_ledger', 'schema-007',
               '2026-08-14 03:43:49.208983+00'::timestamptz,
               'phase2f-approval-a-ledger-baseline',
               '1d1d20edf40b9d2782dd9e314d7e4a2d35ac0aaac5d1570494e58f3e3d982996'),
              ('010_add_plvr_generation_schema', 'schema-010',
               '2026-08-14 03:43:49.208983+00'::timestamptz,
               'phase2f-approval-a-ledger-baseline',
               'fcf69fc2d3b5e6419e2d94a6d92abc03c9b4424204e9bd129b85ea749ebed4a5'),
              ('012_security_rls_deny_by_default', 'schema-012', baseline_recorded_at,
               'stage1-ledger-reconciliation-v1',
               'bb1551d4e7fda1d3c7df99e3fd64a53f7fb05a8dcfb7ec0049c18ae6c2dfa056')
        ),
        differences as (
            select coalesce(expected.migration_id, actual.migration_id)
            from expected
            full join public.schema_migration_ledger actual using (migration_id)
            where actual.migration_id is null
               or expected.migration_id is null
               or actual.schema_version is distinct from expected.schema_version
               or actual.applied_at is distinct from expected.applied_at
               or actual.release_version is distinct from expected.release_version
               or actual.checksum is distinct from expected.checksum
        )
        select 1 from differences
    ) or (select count(*) from public.schema_migration_ledger) <> 10 then
        raise exception 'postcondition_failed: exact ten-row ledger target';
    end if;

    if history_before is distinct from (
        select to_jsonb(h) from public.tax_analysis_history h
        where h.id = 1 and h.case_id = 'HISTORY-001'
    ) or business_counts_before is distinct from array[
        (select count(*) from public.pilot_campaigns),
        (select count(*) from public.pilot_sessions),
        (select count(*) from public.pilot_consents),
        (select count(*) from public.pilot_profiles),
        (select count(*) from public.pilot_contacts),
        (select count(*) from public.pilot_events),
        (select count(*) from public.pilot_feedback),
        (select count(*) from public.professional_reviews),
        (select count(*) from public.tax_analysis_history)
    ] then
        raise exception 'postcondition_failed: business preservation';
    end if;

    if to_regnamespace('compact_green') is not null
       or to_regnamespace('vnext_core') is not null
       or to_regnamespace('vnext_private') is not null
       or exists (select 1 from pg_roles where rolname = 'vnext_api')
       or exists (
           select 1
           from unnest(array[
               'public.official_market_releases',
               'public.official_market_artifacts',
               'public.market_transactions',
               'public.market_transaction_quality_events',
               'public.market_region_period_aggregates',
               'public.market_import_runs',
               'public.market_import_checkpoints',
               'public.official_market_region_coverage'
           ]) object_name
           where to_regclass(object_name) is not null
       ) then
        raise exception 'postcondition_failed: unapplied state changed';
    end if;

    -- Reassert the core 012 posture after the ledger-only writes.
    if (select count(*) from pg_class r join pg_namespace n on n.oid = r.relnamespace
        where n.nspname = 'public' and r.relkind = 'r' and r.relrowsecurity) <> 22
       or exists (
           select 1 from pg_policy p join pg_class r on r.oid = p.polrelid
           join pg_namespace n on n.oid = r.relnamespace where n.nspname = 'public'
       )
       or exists (
           select 1 from information_schema.table_privileges
           where table_schema = 'public'
             and grantee in ('PUBLIC', 'anon', 'authenticated')
       ) then
        raise exception 'postcondition_failed: 012 security posture changed';
    end if;
end
$stage1_ledger_reconciliation$;

-- Capture this result in the operator record after all postconditions pass.
select migration_id, schema_version, applied_at, release_version, checksum
from public.schema_migration_ledger
order by migration_id;

commit;
