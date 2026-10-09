import json
from datetime import date

import pytest

from services import production_closure as closure


def test_configuration_placeholder_is_not_proof():
    result = closure.configuration_projection({'APP_ENV': 'production', 'PILOT_SESSION_SIGNING_KEY': 'changeme' * 8})
    assert result['items']['session_secret']['status'] == 'BLOCKED'
    assert 'changeme' not in json.dumps(result)


def test_malformed_optional_metrics_configuration_blocks_projection():
    values = {'APP_ENV': 'production', 'DATABASE_URL': 'postgresql://db.gov.tw/app',
        'PILOT_SESSION_SIGNING_KEY': 's' * 32, 'CORS_ALLOWED_ORIGINS': 'https://app.gov.tw',
        'PUBLIC_APP_BASE_URL': 'https://app.gov.tw', 'RELEASE_VERSION': 'release-1',
        'API_CONTRACT_VERSION': 'api-contract-v1', 'SCHEMA_VERSION': 'schema-007',
        'METRICS_SCRAPE_TOKEN': 'bad'}
    result = closure.configuration_projection(values)
    assert result['status'] == 'BLOCKED'
    assert result['items']['runtime_readiness']['status'] == 'BLOCKED'


@pytest.mark.parametrize('host', ['example.com', 'api.example.org', 'db.example.net.', 'localhost.'])
def test_reserved_default_origins_cannot_prove_production_configuration(host):
    values = {'APP_ENV': 'production', 'DATABASE_URL': 'postgresql://'+host+'/app',
        'PILOT_SESSION_SIGNING_KEY': 'acceptance-fixture-signing-key-42',
        'CORS_ALLOWED_ORIGINS': 'https://'+host, 'PUBLIC_APP_BASE_URL': 'https://'+host,
        'BACKEND_PUBLIC_URL': 'https://'+host, 'RELEASE_VERSION': 'release-1',
        'API_CONTRACT_VERSION': 'api-contract-v1', 'SCHEMA_VERSION': 'schema-007'}
    result = closure.configuration_projection(values)
    assert result['items']['database']['status'] == 'BLOCKED'
    assert result['items']['cors_origins']['status'] == 'BLOCKED'
    assert result['items']['public_base_url']['status'] == 'BLOCKED'
    assert result['items']['backend_public_origin']['status'] == 'BLOCKED'


def test_tgos_production_integration_is_not_omitted():
    row = closure.provider_projection('tgos', {})
    assert row['provider'] == 'TGOS'
    assert row['status'] == 'BLOCKED'


def test_fixture_pass_never_authorizes_provider():
    row = closure.provider_projection('geocoding', {'GOOGLE_MAPS_API_KEY': 'private-key-value'},
        {'test_mode': 'offline-fixture', 'result': 'pass', 'provider_status': 'pass'})
    assert row['authorized'] == 'NOT_TESTED'
    assert row['status'] != 'PASS'
    assert row['contract_compatible'] == 'PASS'
    assert 'private-key-value' not in json.dumps(row)


def test_disabled_satellite_remains_intentionally_unavailable():
    row = closure.provider_projection('satellite', {'EARTH_ENGINE_SATELLITE_REFERENCE_V1': 'false'})
    assert row['unavailable'] is True
    assert row['reason_code'] == 'intentionally_disabled'
    assert row['status'] == 'NOT_APPLICABLE'


def test_runtime_provider_kill_switch_is_honest_unavailability():
    row = closure.provider_projection('geocoding', {'GOOGLE_MAPS_API_KEY': 'private-key', 'ANTI_ABUSE_GEOCODING_DISABLED': 'true'})
    assert row['unavailable'] is True
    assert row['status'] == 'BLOCKED'
    assert row['reason_code'] == 'runtime_kill_switch'


def test_empty_config_public_provider_is_not_accepted():
    row = closure.provider_projection('ardswc', {})
    assert row['configured'] == 'NOT_APPLICABLE'
    assert row['reachable'] == 'NOT_TESTED'
    assert row['status'] == 'UNKNOWN'


@pytest.mark.parametrize('published,expected', [(None, 'UNKNOWN'), ('113', 'UNKNOWN'),
    ('2020-01-01', 'STALE'), ('2026-10-10', 'UNKNOWN'), ('2026-10-01', 'FRESH')])
def test_freshness_uses_publication_not_processing_time(published, expected):
    from services.production_artifact_registry import freshness
    assert freshness(published, date(2026, 10, 9), 365) == expected


def test_registry_has_actual_sources_and_no_remote_presence_claim():
    from services.production_artifact_registry import artifact_projection
    rows = artifact_projection({}, as_of=date(2026, 10, 9))
    assert {'WRA', 'GSMMA', 'ARDSWC', 'NLSC', 'RIS', 'PLVR', 'TDX'} <= {r['provider'] for r in rows}
    assert all(row['production_active'] == 'UNKNOWN' for row in rows)
    assert all(row['freshness'] != 'FRESH' for row in rows)


def test_missing_acceptance_sections_cannot_pass():
    result = closure.acceptance_projection({})
    assert result['lane_status'] == 'BLOCKED'
    assert result['product_go'] is False
    assert len(result['blockers']) == 5


def test_empty_pass_labels_cannot_pass_acceptance():
    sections = {name: {'schema_version': closure.SCHEMA, 'status': 'PASS'}
                for name in ('deployment', 'configuration', 'artifacts', 'providers', 'runtime_dependencies')}
    assert closure.acceptance_projection(sections)['lane_status'] == 'BLOCKED'


def test_required_artifact_flags_cannot_be_overridden_by_input():
    from services.production_artifact_registry import REGISTRY
    section = {'schema_version': closure.SCHEMA, 'status': 'PASS', 'scope': 'deployed_observation',
        'records': [{'logical_name': entry[0], 'production_required': False} for entry in REGISTRY]}
    assert closure._complete_section('artifacts', section) is False


def test_deployed_runtime_labels_without_audit_cannot_pass():
    section = {'schema_version': closure.SCHEMA, 'status': 'PASS', 'scope': 'deployed_observation',
        'deployment_resolution_locked': True, 'python': {'status': 'PASS', 'deployed_runtime': 'PASS'},
        'frontend': {'status': 'PASS', 'deployed_runtime': 'PASS'}}
    assert closure._complete_section('runtime_dependencies', section) is False


def test_imported_deployment_pass_label_is_not_observation():
    section = {'schema_version': closure.SCHEMA, 'status': 'PASS', 'frontend_sha': 'a' * 40,
        'backend_sha': 'b' * 40, 'reason_code': 'hosted_identities_verified'}
    assert closure._complete_section('deployment', section) is False


@pytest.mark.parametrize('sections', [None, [], 'PASS'])
def test_malformed_sections_remain_blocked(sections):
    assert closure.acceptance_projection(sections)['lane_status'] == 'BLOCKED'


def test_collector_is_provider_free_and_output_is_value_free(monkeypatch):
    from scripts.collect_production_closure import collect
    import socket
    monkeypatch.setattr(socket, 'create_connection', lambda *a, **kw: pytest.fail('network'))
    result = collect(as_of=date(2026, 10, 9), values={'GOOGLE_MAPS_API_KEY': 'private-provider-key'})
    assert result['network_requests'] == 0
    assert result['acceptance']['product_go'] is False
    assert 'private-provider-key' not in json.dumps(result)


def test_collector_accepts_bounded_powershell_json_encoding(tmp_path):
    from scripts.collect_production_closure import read_json
    path = tmp_path / 'audit.json'
    path.write_text('{"auditReportVersion": 2}', encoding='utf-16')
    assert read_json(path)['auditReportVersion'] == 2


def test_release_evidence_v2_reprojects_missing_sections():
    from scripts.generate_release_evidence import build_evidence
    result = build_evidence(release_id='closure-v1', commit='a' * 40, schema_version='declared',
        closure={'schema_version': closure.SCHEMA, 'acceptance': {'lane_status': 'PASS', 'product_go': True}, 'sections': {}})
    assert result['closure_acceptance']['lane_status'] == 'BLOCKED'
    assert result['closure_acceptance']['product_go'] is False


@pytest.mark.parametrize('flag', ['true', 'malformed'])
def test_live_kill_switch_prevents_request(monkeypatch, flag):
    from scripts import provider_acceptance
    monkeypatch.setattr(provider_acceptance, '_geocoding', lambda **kw: pytest.fail('network'))
    result = provider_acceptance.run(capability='geocoding', mode='bounded-live', allow_live=True,
        environ={'GOOGLE_MAPS_API_KEY': 'key', 'PROVIDER_ACCEPTANCE_DISABLED': flag})
    assert result['result'] == 'configuration_required'
    assert result['network_requests'] == 0


def test_live_zero_request_ceiling_prevents_request(monkeypatch):
    from scripts import provider_acceptance
    monkeypatch.setattr(provider_acceptance, '_geocoding', lambda **kw: pytest.fail('network'))
    result = provider_acceptance.run(capability='geocoding', mode='bounded-live', allow_live=True,
        max_requests=0, environ={'GOOGLE_MAPS_API_KEY': 'key'})
    assert result['network_requests'] == 0
    assert result['result'] == 'configuration_required'


def test_local_artifact_receipt_verifies_checksum_without_claiming_activation(tmp_path):
    from services.production_artifact_registry import verify_local_artifact
    from tests.test_wra_flood_runtime import _make_artifact
    manifest, artifact, _ = _make_artifact('24h-350mm')
    payload = json.loads(manifest)
    payload['source_vintage'] = 'official-fixture-2024'
    manifest_path = tmp_path / 'manifest.json'
    artifact_path = tmp_path / 'features.json.gz'
    manifest_path.write_text(json.dumps(payload))
    artifact_path.write_bytes(artifact)
    receipt = verify_local_artifact('wra-flood', manifest_path, artifact_path)
    assert receipt['local_contract'] == 'PASS'
    assert receipt['production_active'] == 'UNKNOWN'
    assert receipt['published_at'] is None
    assert receipt['freshness'] == 'UNKNOWN'
    artifact_path.write_bytes(artifact + b'corrupt')
    assert verify_local_artifact('wra-flood', manifest_path, artifact_path)['local_contract'] == 'BLOCKED'


def test_artifact_verification_rejects_oversized_input(tmp_path):
    from services.production_artifact_registry import verify_local_artifact
    manifest = tmp_path / 'manifest.json'
    artifact = tmp_path / 'features.json.gz'
    manifest.write_bytes(b'{}')
    with artifact.open('wb') as file:
        file.truncate(16_000_001)
    assert verify_local_artifact('wra-flood', manifest, artifact)['local_contract'] == 'BLOCKED'
