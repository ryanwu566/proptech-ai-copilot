'''Local PostgreSQL 17 rehearsal for the Stage 1 ledger-only operation.'''

from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest
from psycopg import Error, sql

from scripts import apply_production_migrations as runner
from scripts.validate_postgres_migration import _split_sql, _statements
from services.postgres_runtime import connect


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / 'ops' / 'stage1' / 'reconcile_migration_ledger.sql'
DATABASE_URL = os.getenv('VNEXT_RLS_POSTGRES_URL', '').strip()
DISPOSABLE = os.getenv('VNEXT_RLS_POSTGRES_DISPOSABLE') == '1'
HISTORICAL_APPLIED_AT = '2026-08-14 03:43:49.208983+00'
HISTORICAL_RELEASE = 'phase2f-approval-a-ledger-baseline'
BASELINE_RELEASE = 'stage1-ledger-reconciliation-v1'

HISTORICAL_CHECKSUMS = {
    '001_add_dedupe_key_to_real_price_transactions':
        '557eef5065a66083aadb1c189ed68dc1271cfdfff48547abcf7f54be9fee0bcd',
    '002_add_market_direct_query_indexes':
        'ca201d932388090018e5543f89d69d43d812c6596e995d354b30b50f52e1203f',
    '002_expand_valuation_import_runs':
        'da83474b55277316a7e8a35c490eb2a31595781bc2331f2d1aba69caea2c8caa',
    '003_add_market_region_coverage':
        '34171ca38e64509c29ae2075874388cf9736ae3df7752c6ae105118d3ee90ce5',
    '007_add_schema_migration_ledger':
        'f4a8ef650ab6bbce8bd1909345785411f350eb6aabe23d0d377fb674ef5934f5',
}

CANONICAL_CHECKSUMS = {
    '001_add_dedupe_key_to_real_price_transactions':
        '2eb4a3e8652d3f18cac9c200d38b3bf350e77bd36aa103f8b76ecf4004143223',
    '002_add_market_direct_query_indexes':
        '2cb6da19a01415ffee34845aa294843257cce7f9991803e0ca470e3405cfc310',
    '002_expand_valuation_import_runs':
        '0108c13fad4d0310e291c0d2e041868c7d59b8fb2f47739831139fa3039b2d64',
    '003_add_market_region_coverage':
        '267db5dcba4c12646b78f480b289cbd289a323bc205a0a8fe5ba507290efb16b',
    '004_add_pilot_evidence':
        'ba2a3f21605983f13b16648e344e3a71baf677ee7e086d155a39dc9b2220b516',
    '005_add_pilot_security_indexes':
        '7da6cffddc6a715bfc041fe37eb9ebf19574e30ef5379a4917db6bc634614d3c',
    '006_add_tax_analysis_history':
        'cc0e6bc09b4f0736c6ddb012ff34912db0385339c93d329d39203e696dc3d1c0',
    '007_add_schema_migration_ledger':
        '1d1d20edf40b9d2782dd9e314d7e4a2d35ac0aaac5d1570494e58f3e3d982996',
    '010_add_plvr_generation_schema':
        'fcf69fc2d3b5e6419e2d94a6d92abc03c9b4424204e9bd129b85ea749ebed4a5',
    '012_security_rls_deny_by_default':
        'bb1551d4e7fda1d3c7df99e3fd64a53f7fb05a8dcfb7ec0049c18ae6c2dfa056',
}

MIGRATIONS = {
    key: ROOT / 'database' / 'migrations' / filename
    for key, filename in {
        '001': '001_add_dedupe_key_to_real_price_transactions.sql',
        '002_direct': '002_add_market_direct_query_indexes.sql',
        '002_valuation': '002_expand_valuation_import_runs.sql',
        '003': '003_add_market_region_coverage.sql',
        '004': '004_add_pilot_evidence.sql',
        '005': '005_add_pilot_security_indexes.sql',
        '006': '006_add_tax_analysis_history.sql',
        '007': '007_add_schema_migration_ledger.sql',
        '010': '010_add_plvr_generation_schema.sql',
        '012': '012_security_rls_deny_by_default.sql',
    }.items()
}

pytestmark = [
    pytest.mark.external_database,
    pytest.mark.skipif(
        not DATABASE_URL or not DISPOSABLE,
        reason='requires the explicitly disposable VNext PostgreSQL database',
    ),
]


def _assert_disposable(connection) -> None:
    name = str(connection.execute('select current_database()').fetchone()[0])
    assert name.startswith('vnext_rls_test')
    version = connection.execute(
        '''select current_setting('server_version_num')::integer'''
    ).fetchone()[0]
    assert int(version) // 10000 == 17


def _execute_file(connection, path: Path) -> None:
    for statement in _statements(path):
        connection.execute(statement)


def _reset_and_build_fixture(connection) -> None:
    _assert_disposable(connection)
    connection.execute('drop extension if exists pgcrypto cascade')
    for schema in (
        'vnext_private', 'vnext_core', 'compact_green',
        'supabase_migrations', 'extensions', 'public',
    ):
        connection.execute(
            sql.SQL('drop schema if exists {} cascade').format(
                sql.Identifier(schema)
            )
        )
    connection.execute('create schema public')
    connection.execute('create schema extensions')
    connection.execute('create extension pgcrypto with schema extensions')
    connection.execute('create schema supabase_migrations')
    connection.execute(
        'create table supabase_migrations.schema_migrations ('
        'version text primary key, name text not null, statements text[] not null)'
    )
    connection.execute(
        '''do $$ begin
        if not exists (select 1 from pg_roles where rolname='anon')
        then create role anon nologin; end if;
        if not exists (select 1 from pg_roles where rolname='authenticated')
        then create role authenticated nologin; end if;
        if not exists (select 1 from pg_roles where rolname='service_role')
        then create role service_role nologin; end if;
        end $$'''
    )
    connection.execute(
        '''
        create table public.real_price_transactions (
            id bigint not null,
            transaction_period varchar(7) not null,
            city text not null,
            district text not null,
            road text not null,
            address_text text default '',
            building_type text not null,
            area_ping numeric not null,
            building_age_years numeric not null default 0,
            floor integer not null default 0,
            total_floor integer,
            unit_price_per_ping numeric not null,
            total_price numeric not null,
            lat double precision,
            lng double precision,
            source text not null,
            imported_at timestamptz not null default now(),
            raw_note text default ''
        )
        '''
    )
    connection.execute(
        '''
        create table public.valuation_import_runs (
            id bigint not null,
            source_name text not null,
            source_period text,
            imported_at timestamptz not null default now(),
            record_count integer not null default 0,
            status text not null,
            note text default ''
        )
        '''
    )
    connection.execute(
        'create table public.community_buildings (id bigint primary key)'
    )
    connection.execute(
        'create table public.market_district_period_aggregates '
        '(id bigint primary key)'
    )
    connection.execute(
        'create table public.market_read_model_metadata (id bigint primary key)'
    )

    for key in (
        '001', '002_direct', '002_valuation', '003', '004',
        '005', '006', '007', '010', '012',
    ):
        _execute_file(connection, MIGRATIONS[key])

    history_rows = (
        ('20260818094700', 'add_pilot_evidence', '004'),
        ('20260818094730', 'add_pilot_security_indexes', '005'),
        ('20260818094742', 'add_tax_analysis_history', '006'),
        ('20260828031611', 'security_rls_deny_by_default', '012'),
    )
    for version, name, key in history_rows:
        connection.execute(
            'insert into supabase_migrations.schema_migrations '
            '(version, name, statements) values (%s, %s, %s)',
            (version, name, [MIGRATIONS[key].read_text(encoding='utf-8')]),
        )

    ledger_rows = (
        ('001_add_dedupe_key_to_real_price_transactions', 'schema-001'),
        ('002_add_market_direct_query_indexes', 'schema-002'),
        ('002_expand_valuation_import_runs', 'schema-002'),
        ('003_add_market_region_coverage', 'schema-003'),
        ('007_add_schema_migration_ledger', 'schema-007'),
        ('010_add_plvr_generation_schema', 'schema-010'),
    )
    for migration_id, schema_version in ledger_rows:
        checksum = (
            HISTORICAL_CHECKSUMS.get(migration_id)
            or CANONICAL_CHECKSUMS[migration_id]
        )
        connection.execute(
            'insert into public.schema_migration_ledger '
            '(migration_id,schema_version,applied_at,release_version,checksum) '
            'values (%s,%s,%s::timestamptz,%s,%s)',
            (
                migration_id, schema_version, HISTORICAL_APPLIED_AT,
                HISTORICAL_RELEASE, checksum,
            ),
        )

    # Nonempty rows make the business-data preservation assertion meaningful.
    connection.execute(
        '''insert into public.real_price_transactions
        (id,transaction_period,city,district,road,building_type,area_ping,
         building_age_years,floor,unit_price_per_ping,total_price,source,dedupe_key)
        values (1,'2026-01','Taipei','Xinyi','Road','home',10,2,3,100,1000,
                'official_plvr_opendata','fixture')'''
    )
    connection.execute(
        '''insert into public.valuation_import_runs
        (id,source_name,status) values (1,'fixture','complete')'''
    )
    connection.execute(
        '''insert into public.market_region_coverage
        (county,district,coverage_status,reconciled_at)
        values ('Taipei','Xinyi','partial',now())'''
    )
    connection.execute(
        '''insert into public.pilot_campaigns
        (campaign_id,access_code_hash) values ('campaign-1','hash')'''
    )
    connection.execute(
        '''insert into public.pilot_sessions
        (session_id,session_token_hash,campaign_id,participant_hash,workflow_id,
         locale,device_class,viewport_class,started_at)
        values ('session-1','token','campaign-1','participant','workflow',
                'en','desktop','wide',now())'''
    )
    connection.execute(
        '''insert into public.pilot_consents
        (session_id,participation,interaction_metrics,written_feedback,
         follow_up_contact,publication,version)
        values ('session-1',true,true,true,false,false,'v1')'''
    )
    connection.execute(
        '''insert into public.pilot_profiles (session_id,profile_json)
        values ('session-1',jsonb_build_object('kind','fixture'))'''
    )
    connection.execute(
        '''insert into public.pilot_contacts (session_id,contact_ciphertext)
        values ('session-1','ciphertext')'''
    )
    connection.execute(
        '''insert into public.pilot_events
        (event_id,session_id,event_type,metadata_json,idempotency_key)
        values ('event-1','session-1','opened','{}'::jsonb,'event-key')'''
    )
    connection.execute(
        '''insert into public.pilot_feedback
        (session_id,task_completion,result_clarity,source_clarity,
         limitation_clarity,entry_ease,meeting_usefulness,trust_level,
         reuse_likelihood)
        values ('session-1','complete',5,5,5,5,5,5,5)'''
    )
    connection.execute(
        '''insert into public.professional_reviews
        (review_id,reviewer_role,qualification,reviewed_capability,
         reviewed_rule_version,reviewed_product_version,review_scope,outcome)
        values ('review-1','reviewer','qualified','valuation','v1','v1',
                'fixture','accepted')'''
    )
    connection.execute(
        '''insert into public.tax_analysis_history
        (id,case_id,client_name,eligibility_status,risk_score,signal_color,
         payload_json)
        values (1,'HISTORY-001','Preserve','unknown',0,'gray',
                jsonb_build_object('sentinel',true))'''
    )


def _ledger_snapshot(connection) -> list[tuple[object, ...]]:
    return connection.execute(
        'select migration_id,schema_version,applied_at,release_version,checksum '
        'from public.schema_migration_ledger order by migration_id'
    ).fetchall()


def _business_snapshot(connection) -> dict[str, str]:
    tables = [
        row[0]
        for row in connection.execute(
            '''select tablename from pg_tables where schemaname='public'
            and tablename <> 'schema_migration_ledger' order by tablename'''
        ).fetchall()
    ]
    snapshot: dict[str, str] = {}
    for table in tables:
        query = sql.SQL(
            '''select coalesce(
                jsonb_agg(to_jsonb(t) order by to_jsonb(t)::text),
                '[]'::jsonb
            )::text from {} t'''
        ).format(sql.Identifier('public', table))
        snapshot[table] = str(connection.execute(query).fetchone()[0])
    return snapshot


def _run_artifact(connection, artifact_sql: str | None = None) -> None:
    source = (
        artifact_sql
        if artifact_sql is not None
        else ARTIFACT.read_text(encoding='utf-8')
    )
    for statement in _split_sql(source):
        connection.execute(statement)


def _expected_pending(connection) -> list[str]:
    ledger_ids = {
        row[0]
        for row in connection.execute(
            'select migration_id from public.schema_migration_ledger'
        ).fetchall()
    }
    return [
        path.name for path in runner.MIGRATIONS if path.stem not in ledger_ids
    ]


def test_reconciliation_success_checksum_provenance_and_runner_remainder() -> None:
    with connect(DATABASE_URL) as connection:
        connection.autocommit = True
        _reset_and_build_fixture(connection)
        before_ledger = {
            row[0]: row for row in _ledger_snapshot(connection)
        }
        before_business = _business_snapshot(connection)

        for migration_id, expected in HISTORICAL_CHECKSUMS.items():
            path = next(
                path for path in MIGRATIONS.values()
                if path.stem == migration_id
            )
            canonical = path.read_bytes().replace(b'\r\n', b'\n')
            historical_crlf = canonical.replace(b'\n', b'\r\n')
            assert hashlib.sha256(historical_crlf).hexdigest() == expected

        _run_artifact(connection)

        ledger = _ledger_snapshot(connection)
        assert len(ledger) == 10
        assert {row[0]: row[4] for row in ledger} == CANONICAL_CHECKSUMS
        baseline_ids = {
            '004_add_pilot_evidence',
            '005_add_pilot_security_indexes',
            '006_add_tax_analysis_history',
            '012_security_rls_deny_by_default',
        }
        historical_rows = [row for row in ledger if row[0] not in baseline_ids]
        for row in historical_rows:
            assert row[1:4] == before_ledger[row[0]][1:4]
        baseline_rows = [row for row in ledger if row[0] in baseline_ids]
        assert len({row[2] for row in baseline_rows}) == 1
        assert all(row[3] == BASELINE_RELEASE for row in baseline_rows)
        assert _business_snapshot(connection) == before_business
        assert _expected_pending(connection) == [
            '008_add_official_market_pipeline.sql',
            '009_separate_official_market_region_coverage.sql',
            '013_vnext_workspace_case_foundation.sql',
            '014_vnext_property_graph_evidence_foundation.sql',
            '015_vnext_identity_resolution_candidates.sql',
            '016_vnext_identity_confirmation_case_links.sql',
            '017_vnext_legacy_saved_case_import.sql',
        ]
        assert not any(
            path.name.startswith('011_') for path in runner.MIGRATIONS
        )


def _inject_failure(connection, case: str) -> str | None:
    if case == 'wrong_checksum':
        connection.execute(
            'update public.schema_migration_ledger set checksum=%s '
            '''where migration_id=
            '001_add_dedupe_key_to_real_price_transactions' ''',
            ('0' * 64,),
        )
    elif case == 'missing_row':
        connection.execute(
            '''delete from public.schema_migration_ledger
            where migration_id='003_add_market_region_coverage' '''
        )
    elif case == 'extra_row':
        connection.execute(
            '''insert into public.schema_migration_ledger
            (migration_id,schema_version,release_version,checksum)
            values ('unexpected','schema-x','fixture','x')'''
        )
    elif case == 'existing_004_baseline':
        connection.execute(
            '''insert into public.schema_migration_ledger
            (migration_id,schema_version,release_version,checksum)
            values ('004_add_pilot_evidence','schema-004','fixture',%s)''',
            (CANONICAL_CHECKSUMS['004_add_pilot_evidence'],),
        )
    elif case == 'catalog_mismatch':
        connection.execute(
            'alter table public.pilot_campaigns add column unexpected text'
        )
    elif case == 'history_missing':
        connection.execute(
            '''delete from public.tax_analysis_history
            where id=1 and case_id='HISTORY-001' '''
        )
    elif case == 'vnext_present':
        connection.execute('create schema vnext_core')
    elif case == 'postcondition_mismatch':
        artifact_sql = ARTIFACT.read_text(encoding='utf-8')
        needle = (
            ') or (select count(*) from public.schema_migration_ledger) '
            '<> 10 then'
        )
        assert artifact_sql.count(needle) == 1
        return artifact_sql.replace(
            needle,
            ') or (select count(*) from public.schema_migration_ledger) '
            '<> 11 then',
        )
    else:  # pragma: no cover
        raise AssertionError(case)
    return None


@pytest.mark.parametrize(
    'case',
    [
        'wrong_checksum',
        'missing_row',
        'extra_row',
        'existing_004_baseline',
        'catalog_mismatch',
        'history_missing',
        'vnext_present',
        'postcondition_mismatch',
    ],
)
def test_reconciliation_failure_rolls_back_without_partial_changes(
    case: str,
) -> None:
    with connect(DATABASE_URL) as connection:
        connection.autocommit = True
        _reset_and_build_fixture(connection)
        artifact_sql = _inject_failure(connection, case)
        before_ledger = _ledger_snapshot(connection)
        before_business = _business_snapshot(connection)

        with pytest.raises(Error):
            _run_artifact(connection, artifact_sql)
        connection.execute('rollback')

        assert _ledger_snapshot(connection) == before_ledger
        assert _business_snapshot(connection) == before_business
