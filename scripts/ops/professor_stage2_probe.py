#!/usr/bin/env python3
"""Operator-invoked, read-only stage-2 contracts; stdout is safe fixed JSON only.

Supports ``python -c SOURCE --database`` in the existing API container. Imports
of psycopg and application modules occur only inside database mode. No provider
activation, Docker invocation, subprocess, report writes, or external HTTP.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener
from zoneinfo import ZoneInfo

WRA_POINT = (120.5340143447583, 24.083055294020838)
WRA_SHA256 = '13b0bf6e0029259ead7e6fd4688ac030f5a2f500a171418f59377c50033cf631'
KNOWN_FACT_SHA256 = '4b3787fe56703bd6a2d1d422b4ac3ae86d7568840a4b053fefd557925e7a9c4d'
LOOPBACK_BASE = 'http://127.0.0.1:8080'
DATABASES = (
    ('app', 'app_runtime', 'proptech_app'),
    ('usage', 'proptech_usage_runtime_v1', 'proptech_api_usage'),
    ('valuation', 'valuation_runtime', 'proptech_valuation'),
)
VALUATION_OBJECTS = (
    'real_price_transactions', 'valuation_import_runs',
    'market_district_period_aggregates', 'market_region_coverage',
    'market_read_model_metadata', 'community_buildings',
    'market_serving_exclusions', 'market_serving_transactions',
    'market_serving_district_periods',
)

IDENTITY_SQL = """SELECT /* identity */ current_user,session_user,current_database(),
rolcanlogin,rolsuper,rolbypassrls,rolcreatedb,rolcreaterole,rolreplication
FROM pg_roles WHERE rolname=current_user"""
# pg_has_role(MEMBER) includes transitive SET ROLE authority, not just inheritance.
# The usage login intentionally has the scoped guard and writer memberships.
ESCALATION_SQL = """SELECT /* escalation */
 has_database_privilege(current_user,current_database(),'CREATE')
 OR EXISTS (SELECT FROM pg_database WHERE datname=current_database()
            AND pg_has_role(current_user,datdba,'MEMBER'))
 OR EXISTS (SELECT FROM pg_namespace WHERE nspname !~ '^pg_' AND nspname<>'information_schema'
            AND (has_schema_privilege(current_user,oid,'CREATE') OR pg_has_role(current_user,nspowner,'MEMBER')))
 OR EXISTS (SELECT FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
            WHERE n.nspname !~ '^pg_' AND n.nspname<>'information_schema'
            AND pg_has_role(current_user,c.relowner,'MEMBER'))
 OR EXISTS (SELECT FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
            WHERE n.nspname !~ '^pg_' AND n.nspname<>'information_schema'
            AND pg_has_role(current_user,p.proowner,'MEMBER'))
 OR EXISTS (SELECT FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
            WHERE n.nspname='public' AND c.relkind IN ('r','p') AND
            (has_table_privilege(current_user,c.oid,'INSERT')
             OR has_table_privilege(current_user,c.oid,'UPDATE')
             OR has_table_privilege(current_user,c.oid,'DELETE')
             OR has_table_privilege(current_user,c.oid,'TRUNCATE')
             OR has_table_privilege(current_user,c.oid,'TRIGGER')))
 OR EXISTS (SELECT FROM pg_roles r WHERE r.rolname<>current_user
            AND pg_has_role(current_user,r.oid,'MEMBER') AND
            (r.rolsuper OR r.rolbypassrls OR r.rolcreatedb OR r.rolcreaterole OR r.rolreplication
             OR r.rolcanlogin OR NOT (r.rolname=ANY(%s))))
 OR EXISTS (SELECT FROM pg_auth_members m WHERE m.admin_option
            AND pg_has_role(current_user,m.member,'MEMBER'))"""
PERMISSIONS_SQL = """SELECT /* permissions */
 has_table_privilege(current_user,%s,'SELECT'),
 has_table_privilege(current_user,%s,'INSERT'),
 has_table_privilege(current_user,%s,'UPDATE'),
 has_table_privilege(current_user,%s,'DELETE'),
 has_table_privilege(current_user,%s,'TRUNCATE'),
 has_table_privilege(current_user,%s,'TRIGGER'),
 has_table_privilege(current_user,%s,'REFERENCES')"""
USAGE_SQL = """SELECT /* usage */
 has_function_privilege(current_user,'api_usage.consume(text,text,text,text,uuid)','EXECUTE')
 AND (SELECT bool_and(has_table_privilege(current_user,'api_usage.hourly',p))
      FROM unnest(ARRAY['SELECT','INSERT','UPDATE','DELETE']) privileges(p))
 AND (SELECT bool_and(has_table_privilege(current_user,'api_usage.flush_batches',p))
      FROM unnest(ARRAY['SELECT','INSERT','UPDATE','DELETE']) privileges(p))
 AND (SELECT count(*)=2 AND bool_and(r.rolname IN ('proptech_usage_guard','proptech_usage_writer')
      AND NOT m.admin_option
      AND coalesce((to_jsonb(m)->>'inherit_option')::boolean,false)
      AND NOT coalesce((to_jsonb(m)->>'set_option')::boolean,true))
      FROM pg_auth_members m JOIN pg_roles r ON r.oid=m.roleid
      WHERE m.member=(SELECT oid FROM pg_roles WHERE rolname=current_user))
 AND NOT EXISTS (
      SELECT FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
      CROSS JOIN unnest(ARRAY['SELECT','INSERT','UPDATE','DELETE','TRUNCATE','REFERENCES','TRIGGER']) privileges(p)
      WHERE n.nspname='api_usage' AND c.relkind IN ('r','p')
      AND has_table_privilege(current_user,c.oid,p)
          IS DISTINCT FROM (c.relname IN ('hourly','flush_batches') AND p IN ('SELECT','INSERT','UPDATE','DELETE')))
 AND (SELECT count(*)=6 FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
      WHERE n.nspname='api_usage' AND c.relkind='r' AND c.relrowsecurity AND c.relforcerowsecurity)"""
RIS_SQL = """SELECT /* ris */ total_population,household_count
FROM public.ris_village_demographics WHERE district_code='65000050016'
ORDER BY statistic_month DESC LIMIT 1"""
POPULATION_SQL = """WITH /* population */ raw AS (
 SELECT count(*) AS total,
 count(*) FILTER (WHERE source='official_plvr_opendata') AS official,
 count(*) FILTER (WHERE source IS DISTINCT FROM 'official_plvr_opendata') AS sample,
 count(*) FILTER (WHERE source='official_plvr_opendata' AND transaction_period>%s) AS future,
 count(*) FILTER (WHERE id=38652 AND source='official_plvr_opendata') AS known
 FROM public.real_price_transactions
), expected_ids AS (
 SELECT id FROM public.real_price_transactions
 EXCEPT SELECT serving_transaction_id FROM public.market_serving_exclusions
), id_difference AS (
 (SELECT id FROM expected_ids EXCEPT SELECT id FROM public.market_serving_transactions)
 UNION ALL
 (SELECT id FROM public.market_serving_transactions EXCEPT SELECT id FROM expected_ids)
)
SELECT total,official,sample,future,known,
 (SELECT count(*) FROM public.market_serving_transactions WHERE id=38652),
 (SELECT count(*) FROM public.market_serving_exclusions),
 (SELECT count(*) FROM public.market_serving_exclusions WHERE
  source_evidence_class IS DISTINCT FROM 'UNIQUE_MATCH'
  OR reason_code IS DISTINCT FROM 'special_note_requires_review'
  OR source_official_id IS NULL OR source_official_id=''
  OR evidence_version IS NULL OR evidence_version=''
  OR fact_sha256 IS NULL OR fact_sha256 !~ '^[0-9a-f]{64}$'),
 (SELECT count(*) FROM public.market_serving_exclusions WHERE serving_transaction_id=38652
  AND source_official_id='RPWNMLNKNHLGFBF78EA'
  AND source_evidence_class='UNIQUE_MATCH' AND reason_code='special_note_requires_review'),
 NOT EXISTS (SELECT FROM id_difference),
 (SELECT count(*)=2 AND bool_and(c.relkind='v'
  AND c.reloptions @> ARRAY['security_barrier=true','security_invoker=true'])
  FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
  WHERE n.nspname='public' AND c.relname IN ('market_serving_transactions','market_serving_district_periods'))
FROM raw"""
KNOWN_FINGERPRINT_SQL = """SELECT /* known_fingerprint */ to_jsonb(t),to_jsonb(e)
FROM public.real_price_transactions t JOIN public.market_serving_exclusions e
ON e.serving_transaction_id=t.id
WHERE t.id=38652 AND t.source='official_plvr_opendata'"""
# Freeze the calendar ceiling once per invocation; canonical keys come from the
# checked-in registry shared with application reads, never a second hardcoded map.
COVERAGE_SQL = r"""WITH /* coverage */ canonical AS (
 SELECT unnest(%s::text[]) AS region_key
), eligible AS (
 SELECT p.*,
 (replace(regexp_replace(trim(county),'\s+','','g'),'臺','台')||'|'||
  replace(regexp_replace(trim(district),'\s+','','g'),'臺','台')) AS region_key
 FROM public.market_serving_district_periods p
 WHERE (replace(regexp_replace(trim(county),'\s+','','g'),'臺','台')||'|'||
        replace(regexp_replace(trim(district),'\s+','','g'),'臺','台')) IN (SELECT region_key FROM canonical)
 AND period<=%s
), active AS (
 SELECT * FROM public.market_district_period_aggregates
 WHERE data_status='available' OR transaction_count>0 OR record_count>0 OR average_unit_price IS NOT NULL
), inventory AS (
 SELECT c.*,
 (replace(regexp_replace(trim(county),'\s+','','g'),'臺','台')||'|'||
  replace(regexp_replace(trim(district),'\s+','','g'),'臺','台')) AS region_key
 FROM public.market_region_coverage c
), expected_coverage AS (
 SELECT region_key,sum(transaction_count)::bigint n,max(source_updated_at) updated
 FROM eligible GROUP BY region_key
), coverage_difference AS (
 SELECT k.region_key FROM canonical k FULL JOIN inventory c USING(region_key)
 LEFT JOIN expected_coverage e ON e.region_key=k.region_key
 WHERE k.region_key IS NULL OR c.region_key IS NULL
 OR c.valid_market_candidate_count IS DISTINCT FROM coalesce(e.n,0)
 OR c.source_updated_at IS DISTINCT FROM e.updated
 OR c.coverage_status IS DISTINCT FROM
    CASE WHEN coalesce(e.n,0)>0 THEN 'covered' ELSE 'coverage_unknown' END
 UNION ALL
 SELECT region_key FROM inventory GROUP BY region_key HAVING count(*)<>1
)
SELECT (SELECT count(DISTINCT region_key) FROM eligible),
 (SELECT count(*) FROM active),
 (SELECT count(*) FROM eligible e FULL JOIN active a USING(county,district,period)
 WHERE e.county IS NULL OR a.county IS NULL
 OR (a.transaction_count,a.record_count,a.average_unit_price,a.source_name,a.source_updated_at,
     a.coverage_status,a.data_status,a.aggregation_method) IS DISTINCT FROM
    (e.transaction_count,e.record_count,e.average_unit_price,e.source_name,e.source_updated_at,
     e.coverage_status,e.data_status,e.aggregation_method)),
 (SELECT count(*) FROM public.market_district_period_aggregates a
 WHERE NOT EXISTS(SELECT FROM eligible e WHERE (e.county,e.district,e.period)=(a.county,a.district,a.period))
 AND (a.transaction_count IS DISTINCT FROM 0 OR a.record_count IS DISTINCT FROM 0
      OR a.average_unit_price IS NOT NULL OR a.source_updated_at IS NOT NULL
      OR a.coverage_status IS DISTINCT FROM 'coverage_unknown' OR a.data_status IS DISTINCT FROM 'unavailable')),
 (SELECT count(*) FROM public.market_region_coverage),
 (SELECT count(*) FROM coverage_difference),
 (SELECT count(*)=1 AND coalesce(bool_and(m.refresh_status='ready' AND m.coverage_status='partial'
 AND m.available_district_count=(SELECT count(DISTINCT (county,district)) FROM eligible)
 AND m.aggregate_region_count=(SELECT count(*) FROM eligible)
 AND m.available_county_count=(SELECT count(DISTINCT county) FROM eligible)
 AND m.source_name='Official PLVR OpenData aggregate'
 AND m.source_updated_at IS NOT DISTINCT FROM (SELECT max(source_updated_at) FROM eligible)
 AND m.earliest_period IS NOT DISTINCT FROM (SELECT min(period) FROM eligible)
 AND m.latest_period IS NOT DISTINCT FROM (SELECT max(period) FROM eligible)),false)
 FROM public.market_read_model_metadata m WHERE read_model_version='v1')"""


class ContractFailed(Exception):
    """Carries no deployment values or database error text."""


def _require(condition):
    if not condition:
        raise ContractFailed()


def _summary(mode, checks, counts=None):
    result = {'mode': mode, 'status': 'PASS' if checks and all(c['status'] == 'PASS' for c in checks) else 'BLOCKED', 'checks': checks}
    if counts is not None:
        result['counts'] = counts
    return result


def _check(name, passed, reason='contract_mismatch'):
    result = {'name': name, 'status': 'PASS' if passed else 'BLOCKED'}
    if not passed:
        result['reason'] = reason
    return result


def _coverage_consistent(row, canonical_count):
    """All canonical regions must exist; only positive candidates are covered."""
    return (isinstance(row, tuple) and len(row) == 7
            and all(isinstance(value, int) and not isinstance(value, bool) for value in row[:6])
            and 0 < row[0] <= canonical_count
            and row[1:6] == (7500, 0, 0, canonical_count, 0) and row[6] is True)


def probe_databases(*, connect=None, read_secret=None, region_keys=None, as_of=None, fact_hasher=None):
    """Read three fixed runtime secrets internally; never return URLs or errors.

    Dependency arguments exist for synthetic tests only. The CLI exposes none.
    A missing dependency or failed contract always yields fixed BLOCKED JSON.
    """
    checks = []
    counts = None
    try:
        if connect is None:
            import psycopg
            connect = psycopg.connect
        if read_secret is None:
            read_secret = lambda path: path.read_text().strip()
        if region_keys is None:
            from services.plvr_data_integrity import canonical_region_storage_keys
            region_keys = canonical_region_storage_keys()
        _require(len(region_keys) == len(set(region_keys)) == 368)
        ceiling = as_of or datetime.now(ZoneInfo('Asia/Taipei')).strftime('%Y-%m')
        _require(isinstance(ceiling, str) and re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])', ceiling))
        for kind, role, database in DATABASES:
            try:
                # Default read-only is effective from the first query. A single
                # transaction per connection ensures all facts share a snapshot.
                url = read_secret(Path('/run/secrets') / (kind + '_database_url'))
                with connect(url, connect_timeout=5, sslmode='verify-full',
                             sslrootcert='/run/selfhost-ca/ca.crt',
                             options='-c default_transaction_read_only=on -c default_transaction_isolation=repeatable\\ read -c statement_timeout=20000 -c lock_timeout=1000 -c timezone=UTC') as db:
                    del url
                    _require(db.execute(IDENTITY_SQL).fetchone() == (role, role, database, True, False, False, False, False, False))
                    _require(db.execute("SELECT /* tls */ ssl FROM pg_stat_ssl WHERE pid=pg_backend_pid()").fetchone() == (True,))
                    _require(db.execute("SELECT /* readonly */ current_setting('transaction_read_only')").fetchone() == ('on',))
                    allowed = ['proptech_usage_guard', 'proptech_usage_writer'] if kind == 'usage' else []
                    _require(db.execute(ESCALATION_SQL, (allowed,)).fetchone() == (False,))
                    objects = ('ris_village_demographics',) if kind == 'app' else VALUATION_OBJECTS if kind == 'valuation' else ()
                    for name in objects:
                        _require(db.execute(PERMISSIONS_SQL, ('public.' + name,) * 7).fetchone() == (True, False, False, False, False, False, False))
                    if kind == 'usage':
                        _require(db.execute(USAGE_SQL).fetchone() == (True,))
                    if kind == 'app':
                        _require(db.execute(RIS_SQL).fetchone() == (6134, 3834))
                    if kind == 'valuation':
                        _require(db.execute(POPULATION_SQL, (ceiling,)).fetchone() == (451744, 451672, 72, 0, 1, 0, 117986, 0, 1, True, True))
                        coverage = db.execute(COVERAGE_SQL, (list(region_keys), ceiling)).fetchone()
                        _require(_coverage_consistent(coverage, len(region_keys)))
                        if fact_hasher is None:
                            from services.plvr_serving_quality import fact_fingerprint
                            fact_hasher = fact_fingerprint
                        facts = db.execute(KNOWN_FINGERPRINT_SQL).fetchone()
                        _require(isinstance(facts, tuple) and len(facts) == 2
                                 and all(isinstance(value, dict) and value for value in facts))
                        _require(fact_hasher(facts[0]) == KNOWN_FACT_SHA256
                                 and facts[1].get('fact_sha256') == KNOWN_FACT_SHA256)
                        # Both records stay inside the process. The fixed known
                        # fact hash checks the reviewed baseline; this additional
                        # digest lets the operator compare every field pre/post.
                        known_digest = hashlib.sha256(json.dumps(
                            facts, sort_keys=True, default=str, ensure_ascii=True,
                            separators=(',', ':'), allow_nan=False).encode()).hexdigest()
                        del facts
                        counts = {'raw_rows': 451744, 'official_rows': 451672, 'sample_rows': 72,
                                  'future_official_rows': 0, 'known_raw_rows': 1, 'known_serving_rows': 0,
                                  'exclusions': 117986, 'coverage_regions': 368, 'active_aggregates': 7500,
                                  'eligible_regions': coverage[0], 'zero_candidate_regions': len(region_keys)-coverage[0],
                                  'known_row_and_exclusion_sha256': known_digest}
                checks.append(_check(kind, True))
            except Exception:
                checks.append(_check(kind, False, 'database_contract_failed'))
        return _summary('database', checks, counts)
    except Exception:
        return _summary('database', [_check('database', False, 'database_probe_failed')])


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _fetch_loopback(name, method, path, payload):
    # A fixed literal base, no proxies and no redirects prevent arbitrary egress.
    opener = build_opener(ProxyHandler({}), _NoRedirect())
    request = Request(LOOPBACK_BASE + path,
                      data=json.dumps(payload).encode() if payload is not None else None,
                      headers={'Content-Type': 'application/json', 'Host': 'localhost'}, method=method)
    with opener.open(request, timeout=60) as response:
        body = response.read(2_000_001)
        _require(len(body) <= 2_000_000)
        return response.status, json.loads(body)


def _object(value):
    return value if isinstance(value, dict) else {}


def _positive(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value > 0


def _count(value, minimum=0):
    return isinstance(value, int) and not isinstance(value, bool) and value >= minimum


def _query_provenance(data, capability):
    details = _object(data.get('source_details'))
    return (details.get('query_status') == 'ok' and details.get('provider_active') == 'postgres'
            and details.get('backend') == 'blue' and details.get('capability') == capability
            and _count(details.get('candidate_pool_size')) and _count(details.get('db_rows_returned'))
            and details['candidate_pool_size'] == details['db_rows_returned'])


def _period(value):
    return (isinstance(value, str) and re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])', value) is not None
            and value <= datetime.now(ZoneInfo('UTC')).strftime('%Y-%m'))


def _official_transaction(row, *, finder=False):
    if not isinstance(row, dict):
        return False
    official = (row.get('source_label') == '官方 PLVR'
                and row.get('source', 'official_plvr_opendata') == 'official_plvr_opendata') if finder else row.get('source') == 'official_plvr_opendata'
    return (official and _period(row.get('transaction_period'))
            and all(_positive(row.get(key)) for key in ('total_price', 'area_ping', 'unit_price_per_ping'))
            and (not finder or (row['total_price'] <= 2000 and row['unit_price_per_ping'] <= 500)))


def _available_estimate(data):
    rows = data.get('comparables')
    price_range = _object(data.get('price_range'))
    prices = [price_range.get(key) for key in ('low', 'mid', 'high')]
    score = data.get('confidence_score')
    return (data.get('valuation_reason_code') == 'official_result_available'
            and data.get('source') == 'postgres' and data.get('result_origin') == 'official'
            and data.get('is_actionable') is True
            and all(_positive(data.get(key)) for key in ('estimate_total_price', 'estimate_unit_price_per_ping'))
            and isinstance(rows, list) and len(rows) >= 3
            and all(_official_transaction(row) for row in rows)
            and data['source_details']['db_rows_returned'] >= len(rows)
            and all(_positive(value) for value in prices) and prices == sorted(prices)
            and price_range['mid'] == data['estimate_total_price']
            and isinstance(score, (int, float)) and not isinstance(score, bool)
            and math.isfinite(score) and 0 <= score <= 100
            and isinstance(data.get('methodology'), list) and bool(data['methodology'])
            and isinstance(data.get('disclaimer'), str) and bool(data['disclaimer'].strip()))


def _available_trend(data):
    rows = data.get('monthly_series')
    if (data.get('source') != 'official_plvr_opendata'
            or data.get('result_origin', 'official') != 'official'
            or data.get('trend_reason_code') != 'official_result_available'
            or data.get('is_actionable') is not True or not _count(data.get('sample_count'), 2)
            or data.get('data_scope') not in {'road', 'district_type', 'district'}
            or not _positive(data.get('recent_median_unit_price'))
            or not isinstance(rows, list) or len(rows) < 2):
        return False
    for row in rows:
        if not isinstance(row, dict) or not _period(row.get('period')) or not _count(row.get('transaction_count'), 1):
            return False
        prices = [row.get(key) for key in ('p25_unit_price_per_ping', 'median_unit_price_per_ping', 'p75_unit_price_per_ping')]
        if not all(_positive(value) for value in prices) or prices != sorted(prices):
            return False
    periods = [row['period'] for row in rows]
    return (periods == sorted(set(periods))
            and sum(row['transaction_count'] for row in rows) == data['sample_count']
            and data['source_details']['db_rows_returned'] >= data['sample_count']
            and data.get('period_min') == data.get('effective_period_min') == periods[0]
            and data.get('period_max') == data.get('effective_period_max') == periods[-1])


def _available_finder(data):
    summary = _object(data.get('summary'))
    rows = data.get('matched_transactions')
    return (data.get('search_reason_code') == 'official_result_available'
            and data.get('is_actionable') is True
            and data.get('source') in (None, 'postgres', 'official_plvr_opendata')
            and data.get('result_origin', 'official') == 'official'
            and summary.get('data_source_label') == '官方 PLVR 實價登錄'
            and _count(summary.get('matched_count'), 1)
            and data['source_details']['db_rows_returned'] >= summary['matched_count']
            and isinstance(rows, list) and 1 <= len(rows) <= min(5, summary['matched_count'])
            and all(_official_transaction(row, finder=True) for row in rows)
            and _period(summary.get('period_min')) and _period(summary.get('period_max'))
            and summary['period_min'] <= summary['period_max']
            and all(summary['period_min'] <= row['transaction_period'] <= summary['period_max'] for row in rows))


def _api_contract(name, data):
    if not isinstance(data, dict):
        return False
    if name == 'health':
        return data.get('status') == 'ok' and data.get('readiness') == 'ready'
    if name == 'readiness':
        return data.get('status') == 'ready'
    if name in {'demographics_village', 'demographics_location'}:
        obs = _object(data.get('observation' if name == 'demographics_village' else 'demographics'))
        code = obs.get('district_code') if name == 'demographics_village' else _object(data.get('village_resolution')).get('district_code')
        return code == '65000050016' and obs.get('total_population') == 6134 and obs.get('household_count') == 3834
    if name == 'valuation_status':
        return data.get('official_records_count') == 451672 and data.get('sample_records_count') == 72 and data.get('active_source') == 'postgres'
    if name in {'valuation_estimate', 'valuation_trend', 'finder'}:
        capability = {'valuation_estimate': 'valuation', 'valuation_trend': 'trend', 'finder': 'finder'}[name]
        if not _query_provenance(data, capability):
            return False
        key = {'valuation_estimate': 'valuation_status', 'valuation_trend': 'trend_status', 'finder': 'search_status'}[name]
        if data.get(key) == 'available':
            return {'valuation_estimate': _available_estimate, 'valuation_trend': _available_trend, 'finder': _available_finder}[name](data)
        return name == 'valuation_estimate' and data.get(key) == 'no_data' and (
            data.get('valuation_reason_code') == 'official_comparables_insufficient'
            and data.get('result_origin') == 'official' and data.get('source') == 'postgres'
            and data.get('is_actionable') is False
            and 'estimate_total_price' in data and data['estimate_total_price'] is None
            and 'estimate_unit_price_per_ping' in data and data['estimate_unit_price_per_ping'] is None
            and data.get('comparables') == []
            and isinstance(data.get('price_range'), dict)
            and all(key in data['price_range'] and data['price_range'][key] is None for key in ('low', 'mid', 'high')))
    if name == 'market':
        return data.get('data_status') == 'available' and _positive(data.get('transaction_count')) and _positive(data.get('average_unit_price'))
    if name == 'market_known_special_period':
        return (data.get('data_status') == 'no_data' and data.get('coverage_status') == 'covered'
                and data.get('average_unit_price') is None and data.get('transaction_count') in (None, 0)
                and data.get('reason_code') == 'market_summary_missing')
    if name in {'wra_matched', 'wra_no_match'}:
        flood = _object(_object(data.get('hazards')).get('flood'))
        source = _object(flood.get('source'))
        return (flood.get('status') == 'available' and flood.get('matched') is (name == 'wra_matched')
                and source.get('storage_backend') == 'local' and source.get('scenario') == '24h-350mm'
                and source.get('artifact_sha256') == WRA_SHA256
                and (flood.get('level') == 'unknown' if name == 'wra_no_match' else flood.get('level') in {'medium', 'high'}))
    return False


def probe_api(*, fetch=None):
    """Run twelve focused loopback contracts; expose only fixed check summaries."""
    fetch = fetch or _fetch_loopback
    target = {'city': '新北市', 'district': '新莊區', 'road': '中正路', 'building_type': '華廈', 'area_ping': 34, 'building_age_years': 20, 'floor': 2}
    cases = [
        ('health', 'GET', '/health', None), ('readiness', 'GET', '/readiness', None),
        ('demographics_village', 'GET', '/demographics/villages/65000050016/latest', None),
        ('demographics_location', 'GET', '/demographics/location?' + urlencode({'latitude': 25.035570879000026, 'longitude': 121.4525876531026}), None),
        ('valuation_status', 'GET', '/valuation/data-status', None),
        ('valuation_estimate', 'POST', '/valuation/estimate', target),
        ('valuation_trend', 'POST', '/valuation/trend', {k: v for k, v in target.items() if k != 'floor'}),
        ('finder', 'POST', '/valuation/property-search', {'city': '新北市', 'districts': ['新莊區'], 'budget_max': 2000, 'limit': 5}),
        ('market', 'POST', '/market-insights/query', {'county': '新北市', 'district': '新莊區', 'road': '中正路'}),
        ('market_known_special_period', 'POST', '/market-insights/query', {'county': '新北市', 'district': '新莊區', 'period': '2026-05'}),
        ('wra_matched', 'POST', '/terrain-risk/analyze', {'latitude': WRA_POINT[1], 'longitude': WRA_POINT[0], 'include_layers': ['flood']}),
        ('wra_no_match', 'POST', '/terrain-risk/analyze', {'latitude': 0, 'longitude': 0, 'include_layers': ['flood']}),
    ]
    checks = []
    for name, method, path, payload in cases:
        try:
            code, data = fetch(name, method, path, payload)
            checks.append(_check(name, code == 200 and _api_contract(name, data)))
        except Exception:
            checks.append(_check(name, False, 'request_failed'))
    return _summary('api', checks)


def main(argv=None):
    try:
        # Custom parsing avoids argparse reflecting arbitrary caller arguments.
        args = list(argv) if argv is not None else __import__('sys').argv[1:]
        if args == ['--database']:
            result = probe_databases()
        elif args == ['--api']:
            result = probe_api()
        else:
            result = {'status': 'BLOCKED', 'reason': 'invalid_probe_mode'}
    except Exception:
        result = {'status': 'BLOCKED', 'reason': 'probe_failed'}
    print(json.dumps(result, sort_keys=True, separators=(',', ':')))
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
