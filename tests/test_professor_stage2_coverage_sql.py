"""Execute production coverage SELECT against synthetic CTEs on an opt-in test PG.

No tables, schemas, databases, roles or serving data are created or modified. The
single SELECT substitutes fixed synthetic relations for four production names.
"""
import importlib.util
import os
from pathlib import Path
import stat

import pytest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('coverage_probe',ROOT/'scripts/ops/professor_stage2_probe.py')
probe=importlib.util.module_from_spec(spec);spec.loader.exec_module(probe)


@pytest.fixture(scope='module')
def connection():
    name=os.environ.get('PROFESSOR_COVERAGE_SQL_TEST_SOCKET')
    if not name:pytest.skip('opt-in local disposable PostgreSQL socket not supplied')
    socket=Path(name)
    assert socket.is_relative_to(Path('/tmp')) and socket.name.startswith('professor-quality-')
    info=socket.stat()
    assert info.st_uid==os.getuid() and stat.S_IMODE(info.st_mode)==0o700
    import psycopg
    with psycopg.connect(host=str(socket),hostaddr='',port=5432,dbname='postgres',user='quality_admin',
            password='',passfile='/nonexistent-professor-synthetic-passfile',sslmode='disable',connect_timeout=3,
            options='-c default_transaction_read_only=on -c statement_timeout=10000') as db:
        assert db.execute("SELECT current_setting('transaction_read_only')").fetchone()==('on',)
        yield db


def query(connection,mutation=None,eligible_regions=322):
    assert eligible_regions in {322,368}
    inventory_extra=" UNION ALL SELECT 'c','d999',0::bigint,NULL::date,'coverage_unknown'" if mutation=='extra_inventory' else ''
    inventory_filter=" WHERE r<>368" if mutation=='missing_inventory' else ''
    district="CASE WHEN r=368 THEN 'd1' ELSE 'd'||r END" if mutation=='duplicate_inventory' else "'d'||r"
    count="CASE WHEN r=368 THEN 1::bigint ELSE coalesce(n,0) END" if mutation=='zero_count' else 'coalesce(n,0)'
    if mutation=='positive_count':count='coalesce(n,0)+CASE WHEN r=1 THEN 1 ELSE 0 END'
    date="CASE WHEN r=368 THEN DATE '2026-06-08' ELSE updated END" if mutation=='zero_date' else 'updated'
    status="CASE WHEN coalesce(n,0)>0 THEN 'covered' ELSE 'coverage_unknown' END"
    if mutation=='zero_covered':status="CASE WHEN r=368 OR coalesce(n,0)>0 THEN 'covered' ELSE 'coverage_unknown' END"
    if mutation=='positive_unknown':status="CASE WHEN r=1 THEN 'coverage_unknown' WHEN coalesce(n,0)>0 THEN 'covered' ELSE 'coverage_unknown' END"
    metadata_districts='368' if mutation=='wrong_available_total' else str(eligible_regions)
    metadata_status="'covered'" if mutation=='false_full_coverage' else "'partial'"
    metadata_filter=' WHERE false' if mutation=='missing_metadata' else ''
    average="CASE WHEN district='d1' THEN 1::numeric ELSE average_unit_price END" if mutation=='aggregate_price' else 'average_unit_price'
    fixture=f"""
 _test_source AS (
   SELECT 'c'::text county,'d'||(mod(n-1,{eligible_regions})+1) district,
     to_char(DATE '2023-01-01'+((n-1)/{eligible_regions})*INTERVAL '1 month','YYYY-MM') period,
     40::numeric average_unit_price,3::integer transaction_count,3::integer record_count,
     'Official PLVR OpenData aggregate'::text source_name,DATE '2026-06-08' source_updated_at,
     'partial'::text coverage_status,'available'::text data_status,
     'avg_unit_price_per_ping_by_city_district_period'::text aggregation_method
   FROM generate_series(1,7500) n
 ), _test_aggregates AS (
   SELECT county,district,period,{average} average_unit_price,transaction_count,record_count,
     source_name,source_updated_at,coverage_status,data_status,aggregation_method FROM _test_source
 ), _test_region_totals AS (
   SELECT district,sum(transaction_count)::bigint n,max(source_updated_at) updated FROM _test_source GROUP BY district
 ), _test_coverage AS (
   SELECT 'c'::text county,{district} district,{count} valid_market_candidate_count,
     {date} source_updated_at,{status} coverage_status
   FROM generate_series(1,368) r LEFT JOIN _test_region_totals a ON a.district='d'||r
   {inventory_filter}{inventory_extra}
 ), _test_metadata AS (
   SELECT 'v1'::text read_model_version,'ready'::text refresh_status,{metadata_status}::text coverage_status,
     1::integer available_county_count,{metadata_districts}::integer available_district_count,
     7500::integer aggregate_region_count,'Official PLVR OpenData aggregate'::text source_name,
     DATE '2026-06-08' source_updated_at,(SELECT min(period) FROM _test_source) earliest_period,(SELECT max(period) FROM _test_source) latest_period
   {metadata_filter}
 ),
 """
    statement=probe.COVERAGE_SQL.replace('WITH /* coverage */','WITH /* coverage */'+fixture,1)
    for original,synthetic in [('public.market_serving_district_periods','_test_source'),
        ('public.market_district_period_aggregates','_test_aggregates'),
        ('public.market_region_coverage','_test_coverage'),('public.market_read_model_metadata','_test_metadata')]:
        statement=statement.replace(original,synthetic)
    assert 'public.' not in statement and statement.lstrip().startswith('WITH')
    return connection.execute(statement,([f'c|d{i}' for i in range(1,369)],'2026-10')).fetchone()


def test_322_available_regions_and_46_unknown_regions_are_consistent(connection):
    assert query(connection)==(322,7500,0,0,368,0,True)


@pytest.mark.parametrize('mutation,failed_column',[
    ('zero_covered',5),('zero_date',5),('zero_count',5),('positive_unknown',5),('positive_count',5),
    ('extra_inventory',5),('missing_inventory',5),('duplicate_inventory',5),
    ('aggregate_price',2),('wrong_available_total',6),('false_full_coverage',6),('missing_metadata',6),
])
def test_partial_coverage_does_not_hide_actual_data_or_metadata_drift(connection,mutation,failed_column):
    row=query(connection,mutation)
    if failed_column==6:assert row[failed_column] is False
    else:assert row[failed_column]>0


def test_all_canonical_regions_may_have_candidates_without_hardcoded_322(connection):
    assert query(connection,eligible_regions=368)==(368,7500,0,0,368,0,True)
