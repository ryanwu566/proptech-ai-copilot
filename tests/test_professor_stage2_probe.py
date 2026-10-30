"""Synthetic acceptance contracts: never open sockets or read deployment secrets."""
import importlib.util
import json
from pathlib import Path

import pytest

SOURCE = Path(__file__).resolve().parents[1] / 'scripts/ops/professor_stage2_probe.py'
KNOWN_FACT_SHA256 = '4b3787fe56703bd6a2d1d422b4ac3ae86d7568840a4b053fefd557925e7a9c4d'


def load_probe():
    assert SOURCE.exists(), 'stage-2 probe implementation is missing'
    spec = importlib.util.spec_from_file_location('stage2_probe', SOURCE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def query_metadata(capability, rows=5):
    return {'query_status': 'ok', 'provider_active': 'postgres', 'backend': 'blue', 'capability': capability, 'candidate_pool_size': rows, 'db_rows_returned': rows}


def official_transaction():
    return {'source': 'official_plvr_opendata', 'source_label': '官方 PLVR', 'transaction_period': '2026-04', 'city': '新北市', 'district': '新莊區', 'total_price': 1360, 'area_ping': 34, 'unit_price_per_ping': 40}


def available_estimate():
    return {'valuation_status': 'available', 'valuation_reason_code': 'official_result_available', 'source': 'postgres', 'result_origin': 'official', 'is_actionable': True, 'estimate_total_price': 1360, 'estimate_unit_price_per_ping': 40, 'comparables': [official_transaction() for _ in range(3)], 'price_range': {'low': 1200, 'mid': 1360, 'high': 1500}, 'confidence_score': 60, 'methodology': ['synthetic official sample method'], 'disclaimer': 'synthetic reference only', 'source_details': query_metadata('valuation')}


def api_responses(module):
    return {
        'health': {'status': 'ok', 'readiness': 'ready'},
        'readiness': {'status': 'ready'},
        'demographics_village': {'observation': {'district_code': '65000050016', 'total_population': 6134, 'household_count': 3834}},
        'demographics_location': {'village_resolution': {'district_code': '65000050016'}, 'demographics': {'total_population': 6134, 'household_count': 3834}},
        'valuation_status': {'official_records_count': 451672, 'sample_records_count': 72, 'active_source': 'postgres'},
        'valuation_estimate': {'valuation_status': 'no_data', 'valuation_reason_code': 'official_comparables_insufficient', 'result_origin': 'official', 'source': 'postgres', 'is_actionable': False, 'estimate_total_price': None, 'estimate_unit_price_per_ping': None, 'comparables': [], 'price_range': {'low': None, 'mid': None, 'high': None}, 'source_details': query_metadata('valuation')},
        'valuation_trend': {'trend_status': 'available', 'trend_reason_code': 'official_result_available', 'source': 'official_plvr_opendata', 'is_actionable': True, 'data_scope': 'district', 'sample_count': 5, 'period_min': '2026-04', 'period_max': '2026-05', 'effective_period_min': '2026-04', 'effective_period_max': '2026-05', 'recent_median_unit_price': 42, 'monthly_series': [{'period': '2026-04', 'transaction_count': 2, 'median_unit_price_per_ping': 40, 'p25_unit_price_per_ping': 38, 'p75_unit_price_per_ping': 42}, {'period': '2026-05', 'transaction_count': 3, 'median_unit_price_per_ping': 42, 'p25_unit_price_per_ping': 40, 'p75_unit_price_per_ping': 44}], 'source_details': query_metadata('trend')},
        'finder': {'search_status': 'available', 'search_reason_code': 'official_result_available', 'is_actionable': True, 'summary': {'matched_count': 1, 'data_source_label': '官方 PLVR 實價登錄', 'period_min': '2026-04', 'period_max': '2026-04'}, 'matched_transactions': [official_transaction()], 'source_details': query_metadata('finder')},
        'market': {'data_status': 'available', 'transaction_count': 18, 'average_unit_price': 42.3},
        'market_known_special_period': {'data_status': 'no_data', 'coverage_status': 'covered', 'transaction_count': 0, 'average_unit_price': None, 'reason_code': 'market_summary_missing'},
        'wra_matched': {'hazards': {'flood': {'status': 'available', 'matched': True, 'level': 'medium', 'source': {'storage_backend': 'local', 'scenario': '24h-350mm', 'artifact_sha256': module.WRA_SHA256}}}},
        'wra_no_match': {'hazards': {'flood': {'status': 'available', 'matched': False, 'level': 'unknown', 'source': {'storage_backend': 'local', 'scenario': '24h-350mm', 'artifact_sha256': module.WRA_SHA256}}}},
    }


def run_api(module, responses, *, status=200):
    requests = []
    def fetch(name, method, path, payload):
        requests.append((name, method, path, payload))
        return status, responses[name]
    return module.probe_api(fetch=fetch), requests


def test_twelve_api_contracts_and_no_raw_data_output():
    module = load_probe()
    responses = api_responses(module)
    responses['health']['untrusted'] = 'postgres://private-password@example/private-address'
    result, requests = run_api(module, responses)
    assert result['status'] == 'PASS'
    assert len(result['checks']) == len(requests) == 12
    assert all(row['status'] == 'PASS' for row in result['checks'])
    assert 'private' not in json.dumps(result)
    assert requests[-1][3]['latitude'] == requests[-1][3]['longitude'] == 0
    assert all('/operator' not in row[2] for row in requests)


@pytest.mark.parametrize('name,mutation', [
    ('health', {'status': 'ok', 'readiness': 'degraded'}),
    ('demographics_location', {'village_resolution': {'district_code': '65000050016'}, 'demographics': {'total_population': 6134, 'household_count': 0}}),
    ('valuation_estimate', {'valuation_status': 'no_data', 'valuation_reason_code': 'official_comparables_insufficient', 'source': 'postgres', 'is_actionable': True}),
    ('valuation_trend', {'trend_status': 'available', 'source_details': {'query_status': 'failed'}}),
    ('market_known_special_period', {'data_status': 'available', 'transaction_count': 1, 'average_unit_price': 10.15}),
    ('wra_no_match', {'hazards': {'flood': {'status': 'available', 'matched': False, 'level': 'safe', 'source': {'storage_backend': 'local'}}}}),
    ('finder', []),
])
def test_api_contracts_fail_closed(name, mutation):
    module = load_probe()
    responses = api_responses(module)
    responses[name] = mutation
    result, _ = run_api(module, responses)
    assert result['status'] == 'BLOCKED'
    assert next(row for row in result['checks'] if row['name'] == name)['status'] == 'BLOCKED'


def test_exceptions_and_http_failure_never_reflect_payload():
    module = load_probe()
    def fail(*args):
        raise RuntimeError('postgres://canary-secret@canary-host/private')
    result = module.probe_api(fetch=fail)
    assert result['status'] == 'BLOCKED'
    assert 'canary' not in json.dumps(result)
    result, _ = run_api(module, api_responses(module), status=503)
    assert all(row['status'] == 'BLOCKED' for row in result['checks'])


class FakeDB:
    def __init__(self, kind, changes=None):
        self.kind, self.changes, self.queries = kind, changes or {}, []
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def execute(self, sql, params=None):
        self.queries.append((sql, params))
        marker = sql.split('/* ', 1)[1].split(' */', 1)[0]
        roles = {'app': ('app_runtime', 'proptech_app'), 'usage': ('proptech_usage_runtime_v1', 'proptech_api_usage'), 'valuation': ('valuation_runtime', 'proptech_valuation')}
        role, database = roles[self.kind]
        values = {
            'identity': (role, role, database, True, False, False, False, False, False),
            'tls': (True,), 'readonly': ('on',), 'escalation': (False,),
            'permissions': (True, False, False, False, False, False, False),
            'usage': (True,), 'ris': (6134, 3834),
            'population': (451744, 451672, 72, 0, 1, 0, 117986, 0, 1, True, True),
            'coverage': (368, 7500, 0, 0, 368, 0, True),
            'known_fingerprint': ({'id': 38652, 'address': 'canary-private-address', 'total_price': 100}, {'serving_transaction_id': 38652, 'note': 'canary-private-note', 'fact_sha256': KNOWN_FACT_SHA256}),
        }
        value = self.changes.get(marker, values.get(marker))
        class Cursor:
            def fetchone(self):
                return value
        return Cursor()


def run_db(module, changes=None):
    connections, options, reads = [], [], []
    def connect(url, **kwargs):
        options.append(kwargs)
        db = FakeDB(url, changes)
        connections.append(db)
        return db
    def read_secret(path):
        reads.append(str(path))
        return Path(path).name.removesuffix('_database_url')
    result = module.probe_databases(connect=connect, read_secret=read_secret, region_keys=tuple(f'r{i}' for i in range(368)), as_of='2026-10', fact_hasher=lambda row: row.get('synthetic_fact_sha256', KNOWN_FACT_SHA256))
    return result, connections, options, reads


def test_database_readonly_contracts_with_synthetic_connections():
    module = load_probe()
    result, dbs, options, reads = run_db(module)
    assert result['status'] == 'PASS'
    assert len(dbs) == 3
    assert set(reads) == {f'/run/secrets/{kind}_database_url' for kind in ('app', 'usage', 'valuation')}
    for opts in options:
        assert opts['sslmode'] == 'verify-full'
        assert opts['sslrootcert'] == '/run/selfhost-ca/ca.crt'
        assert 'default_transaction_read_only=on' in opts['options']
        assert 'lock_timeout=1000' in opts['options']
    for db in dbs:
        assert all(sql.lstrip().startswith(('SELECT', 'WITH')) for sql, _ in db.queries)
    assert result['counts']['raw_rows'] == 451744
    assert result['counts']['exclusions'] == 117986
    assert result['counts']['active_aggregates'] == 7500
    assert 'canary' not in json.dumps(result)


@pytest.mark.parametrize('changes', [
    {'escalation': (True,)}, {'tls': (False,)}, {'readonly': ('off',)},
    {'permissions': (True, True, False, False, False, False, False)},
    {'population': (451744, 451672, 72, 0, 1, 1, 117986, 0, 1, True, True)},
    {'population': (451744, 451672, 72, 0, 1, 0, 117986, 1, 1, True, True)},
    {'population': (451744, 451672, 72, 0, 1, 0, 117986, 0, 1, False, True)},
    {'coverage': (368, 7500, 1, 0, 368, 0, True)},
    {'coverage': (368, 7500, 0, 0, 368, 0, False)},
])
def test_database_drift_blocks_acceptance(changes):
    module = load_probe()
    result, *_ = run_db(module, changes)
    assert result['status'] == 'BLOCKED'


def test_database_exception_redacted_and_counts_not_fabricated():
    module = load_probe()
    def fail(*args, **kwargs):
        raise RuntimeError('postgres://canary-secret@canary-host/private')
    result = module.probe_databases(connect=fail, read_secret=lambda _: 'synthetic', region_keys=('synthetic',) * 368, as_of='2026-10')
    assert result['status'] == 'BLOCKED'
    assert not result.get('counts')
    assert 'canary' not in json.dumps(result)


def test_usage_query_requires_each_scoped_privilege_and_rejects_broader_authority():
    module = load_probe()
    # PostgreSQL's comma privilege list means ANY; it cannot certify a writer.
    assert "'SELECT,INSERT" not in module.USAGE_SQL
    assert 'pg_proc' in module.ESCALATION_SQL
    assert "has_table_privilege(current_user,c.oid,'INSERT')" in module.ESCALATION_SQL


def test_main_invalid_mode_redacts_arguments_and_exits_blocked(capsys):
    module = load_probe()
    assert module.main(['--canary-secret-private-url']) == 1
    captured = capsys.readouterr()
    assert json.loads(captured.out) == {'status': 'BLOCKED', 'reason': 'invalid_probe_mode'}
    assert not captured.err


def test_loopback_transport_disables_proxies_and_redirects_without_network(monkeypatch):
    module = load_probe()
    seen = {}
    class Response:
        status = 200
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def read(self, limit):
            seen['limit'] = limit
            return b'{"status":"ok","untrusted":"canary-address"}'
    class Opener:
        def open(self, request, timeout):
            seen['request'], seen['timeout'] = request, timeout
            return Response()
    def build(*handlers):
        seen['handlers'] = handlers
        return Opener()
    monkeypatch.setattr(module, 'build_opener', build)
    code, value = module._fetch_loopback('health', 'GET', '/health', None)
    assert code == 200 and value['status'] == 'ok'
    assert seen['request'].full_url == 'http://127.0.0.1:8080/health'
    assert seen['request'].get_header('Host') == 'localhost'
    assert seen['handlers'][0].proxies == {}
    assert seen['handlers'][1].redirect_request(None, None, None, None, None, 'https://canary.invalid') is None
    assert seen['limit'] == 2_000_001


def test_main_returns_single_safe_json_for_api_result(monkeypatch, capsys):
    module = load_probe()
    expected, _ = run_api(module, api_responses(module))
    monkeypatch.setattr(module, 'probe_api', lambda: expected)
    assert module.main(['--api']) == 0
    captured = capsys.readouterr()
    assert json.loads(captured.out) == expected
    assert captured.out.count('\n') == 1 and not captured.err


def test_wra_unknown_hit_level_is_rejected():
    module = load_probe()
    responses = api_responses(module)
    responses['wra_matched']['hazards']['flood']['level'] = 'moderate'
    result, _ = run_api(module, responses)
    assert result['status'] == 'BLOCKED'


@pytest.mark.parametrize('name', ['valuation_estimate', 'valuation_trend', 'finder'])
@pytest.mark.parametrize('bad_metadata', [
    {}, {'query_status': 'success'},
    {**query_metadata('valuation'), 'provider_active': 'demo'},
    {**query_metadata('valuation'), 'backend': 'demo'},
])
def test_available_valuation_requires_successful_official_query(name, bad_metadata):
    module = load_probe()
    responses = api_responses(module)
    responses['valuation_estimate'] = available_estimate()
    responses[name]['source_details'] = bad_metadata
    result, _ = run_api(module, responses)
    assert next(row for row in result['checks'] if row['name'] == name)['status'] == 'BLOCKED'


@pytest.mark.parametrize('name,field,value', [
    ('valuation_estimate', 'source', 'demo'),
    ('valuation_estimate', 'result_origin', 'demo'),
    ('valuation_estimate', 'is_actionable', False),
    ('valuation_estimate', 'estimate_total_price', None),
    ('valuation_estimate', 'estimate_unit_price_per_ping', float('nan')),
    ('valuation_estimate', 'comparables', []),
    ('valuation_estimate', 'comparables', [{'source': 'demo'}] * 3),
    ('valuation_estimate', 'price_range', {'low': 1500, 'mid': 1360, 'high': 1200}),
    ('valuation_estimate', 'confidence_score', float('inf')),
    ('valuation_trend', 'source', 'demo'),
    ('valuation_trend', 'is_actionable', False),
    ('valuation_trend', 'sample_count', 0),
    ('valuation_trend', 'monthly_series', []),
    ('finder', 'is_actionable', False),
    ('finder', 'matched_transactions', []),
    ('finder', 'summary', {'matched_count': 1, 'data_source_label': '展示資料'}),
])
def test_available_valuation_requires_meaningful_official_results(name, field, value):
    module = load_probe()
    responses = api_responses(module)
    responses['valuation_estimate'] = available_estimate()
    responses[name][field] = value
    result, _ = run_api(module, responses)
    assert next(row for row in result['checks'] if row['name'] == name)['status'] == 'BLOCKED'


def test_available_official_estimate_passes_complete_contract():
    module = load_probe()
    responses = api_responses(module)
    responses['valuation_estimate'] = available_estimate()
    result, _ = run_api(module, responses)
    assert result['status'] == 'PASS'


def test_no_data_estimate_still_requires_successful_query_provenance():
    module = load_probe()
    responses = api_responses(module)
    responses['valuation_estimate']['source_details'] = {}
    result, _ = run_api(module, responses)
    assert result['status'] == 'BLOCKED'


def test_known_fingerprint_pins_facts_without_reflecting_rows():
    module = load_probe()
    before, *_ = run_db(module)
    after, *_ = run_db(module, {'known_fingerprint': ({'id': 38652, 'address': 'canary-private-address', 'total_price': 100, 'imported_at': 'synthetic-changed-time'}, {'serving_transaction_id': 38652, 'note': 'canary-private-note', 'fact_sha256': KNOWN_FACT_SHA256})})
    assert before['status'] == after['status'] == 'PASS'
    left = before['counts']['known_row_and_exclusion_sha256']
    right = after['counts']['known_row_and_exclusion_sha256']
    assert len(left) == len(right) == 64 and left != right
    assert 'canary' not in json.dumps(before) + json.dumps(after)


@pytest.mark.parametrize('transaction,exclusion', [
    ({'id': 38652, 'synthetic_fact_sha256': '0' * 64}, {'fact_sha256': KNOWN_FACT_SHA256}),
    ({'id': 38652}, {'fact_sha256': '0' * 64}),
    ({'id': 38652, 'synthetic_fact_sha256': None}, {'fact_sha256': KNOWN_FACT_SHA256}),
])
def test_known_transaction_and_exclusion_require_exact_reviewed_fact_hash(transaction, exclusion):
    module = load_probe()
    result, *_ = run_db(module, {'known_fingerprint': (transaction, exclusion)})
    assert result['status'] == 'BLOCKED'
    assert not result.get('counts')


@pytest.mark.parametrize('name', ['valuation_estimate', 'valuation_trend', 'finder'])
def test_available_query_counters_must_describe_the_same_database_result(name):
    module = load_probe()
    responses = api_responses(module)
    responses['valuation_estimate'] = available_estimate()
    responses[name]['source_details']['candidate_pool_size'] = 0
    result, _ = run_api(module, responses)
    assert next(row for row in result['checks'] if row['name'] == name)['status'] == 'BLOCKED'


def test_finder_rejects_contradictory_demo_source_inside_official_labeled_rows():
    module = load_probe()
    responses = api_responses(module)
    responses['finder']['matched_transactions'][0]['source'] = 'demo'
    result, _ = run_api(module, responses)
    assert result['status'] == 'BLOCKED'


def test_partial_available_regions_are_distinct_from_full_canonical_inventory():
    module=load_probe()
    result,*_=run_db(module,{'coverage':(322,7500,0,0,368,0,True)})
    assert result['status']=='PASS'
    assert result['counts']['eligible_regions']==322
    assert result['counts']['zero_candidate_regions']==46


@pytest.mark.parametrize('row',[
    (0,7500,0,0,368,0,True),(369,7500,0,0,368,0,True),
    (322,7499,0,0,368,0,True),(322,7500,1,0,368,0,True),
    (322,7500,0,1,368,0,True),(322,7500,0,0,367,0,True),
    (322,7500,0,0,368,1,True),(322,7500,0,0,368,0,False),
    (True,7500,0,0,368,0,True),(322,7500,False,0,368,0,True),
    (322,7500,0,0,368,0,1),None,(322,7500),
])
def test_partial_coverage_does_not_relax_other_acceptance_invariants(row):
    assert load_probe()._coverage_consistent(row,368) is False
