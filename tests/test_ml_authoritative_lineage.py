"""ML-A3 contracts; all positive external evidence here is synthetic."""
from copy import deepcopy
import importlib
import importlib.util
import json

import pytest

from scripts.ml import historical as h, lineage as l
from tests.test_ml_authoritative_history import publication, certification, later
from tests.test_ml_target_reframing import item, proof, CUTOFF


def record(x):
    return {'source_id': x['release_id'], 'source_type': 'OFFICIAL_ARCHIVE',
            'publication_period': 'synthetic-period',
            'publication_timestamp': x['source_release_available_at'],
            'retrieval_timestamp': '2026-10-10T00:00:00+08:00',
            'official_url': 'https://plvr.land.moi.gov.tw/synthetic',
            'hash': x['archive_sha256'], 'proof_class': 'AUTHENTICATED_HISTORICAL',
            'proof_basis': 'Synthetic reviewed provider hash/time binding',
            'limitations': ['Synthetic only'], 'evidence': proof(),
            'exact_byte_publication_binding': True}


@pytest.mark.parametrize('change', [dict(proof_class='CURRENT_ONLY'),
    dict(exact_byte_publication_binding=False), dict(hash='e'*64),
    dict(publication_timestamp=None), dict(evidence=None)])
def test_current_or_unbound_proof_cannot_be_promoted(change):
    x = item(); evidence = record(x); evidence.update(change)
    assert h.historical_proof(evidence, x)['available_at'] is None


def test_reviewed_proof_binds_exact_release_hash_and_time():
    x = item()
    assert h.historical_proof(record(x), x)['available_at'] == '2024-06-30T16:00:00+00:00'


def test_v3_publication_consumes_machine_proof_and_rejects_impossible_capture_clock():
    x = item(); x['historical_proof_record'] = record(x)
    x['required_source_dependencies'] = []
    assert h.publication(x)['available_at'] == '2024-06-30T16:00:00+00:00'
    assert len(select([x])['selected']) == 1
    x['historical_proof_record']['retrieval_timestamp'] = '2024-06-01T00:00:00+08:00'
    assert h.publication(x)['available_at'] is None


@pytest.mark.parametrize('value', ['bad', None, 42])
def test_proof_hash_requires_a_checksum_not_just_equal_strings(value):
    x = item(); x['archive_sha256'] = value
    evidence = record(x)
    assert h.historical_proof(evidence, x)['available_at'] is None


def v3(x):
    x = publication(x)
    x['required_source_dependencies'] = []  # explicitly no external supplements
    return x


def select(xs, cutoff=CUTOFF):
    return h.select_pit_v3(xs, cutoff, history_certificate=certification(xs, cutoff))


@pytest.mark.parametrize('cancelled,replacement', [(False, False), (True, False), (False, True)])
def test_v3_later_event_preserves_earlier_snapshot(cancelled, replacement):
    x = v3(item()); y = later(x, cancelled=cancelled, replacement=replacement)
    assert select([x, y])['selected'] == select([x])['selected']
    after = select([x, y], '2024-10-01T00:00:00+08:00')
    assert len(after['selected']) == (0 if cancelled else 1)


def test_missing_dependency_declaration_fails_closed():
    x = publication(item())
    assert select([x])['excluded_reasons'] == {'SOURCE_DEPENDENCIES_UNPROVEN': 1}


def test_duplicate_versions_with_conflicting_dependencies_fail_closed():
    x = v3(item()); y = deepcopy(x); y['physical_row_number'] = 2
    y['required_source_dependencies'] = [{'source_id': 'unproven', 'sha256': 'b'*64}]
    assert select([x, y])['excluded_reasons'] == {'semantic_evidence_conflict': 2}


def test_malformed_dependency_hash_cannot_qualify():
    x = v3(item())
    x['required_source_dependencies'] = [{'source_id': 'supplement', 'sha256': 'bad',
        'publication_evidence': {'classification': 'AUTHENTICATED', 'release_id': 'supplement',
            'archive_sha256': 'bad', 'quality': 'EXACT_PUBLICATION_TIME',
            'value': '2024-07-01T00:00:00+08:00', 'evidence': proof()}}]
    assert select([x])['selected'] == []


def test_later_dependency_excludes_revision_without_restoring_original():
    x = v3(item()); y = later(x)
    y['required_source_dependencies'] = [{'source_id': 'supplement', 'sha256': 'b'*64,
        'publication_evidence': {'classification': 'AUTHENTICATED', 'release_id': 'supplement',
            'archive_sha256': 'b'*64, 'quality': 'EXACT_PUBLICATION_TIME',
            'value': '2024-11-01T00:00:00+08:00', 'evidence': proof()}}]
    after = select([x, y], '2024-10-01T00:00:00+08:00')
    assert after['selected'] == []
    assert after['excluded_reasons'] == {'SOURCE_DEPENDENCIES_UNPROVEN': 1, 'superseded_version': 1}
    assert len(select([x, y])['selected']) == 1


@pytest.mark.parametrize('kind,expected', [('CORRECTION', 'REVISION'),
    ('CANCELLATION', 'CANCELLATION'), ('SUPERSESSION', 'REPLACEMENT')])
def test_lineage_event_classification_requires_qualified_history(kind, expected):
    x = v3(item()); y = later(x, cancelled=kind == 'CANCELLATION', replacement=kind == 'SUPERSESSION')
    cutoff = '2024-10-01T00:00:00+08:00'
    events = h.lineage_events([x, y], cutoff, history_certificate=certification([x, y], cutoff))
    assert [event['change_type'] for event in events] == ['ORIGINAL', expected]
    assert events[-1]['effective_publication_timestamp'] == '2024-08-31T16:00:00+00:00'


def test_multiple_revisions_and_duplicate_release():
    x = v3(item()); y = later(x); z = later(y)
    z.update(release_id='synthetic-third', archive_sha256='e'*64,
             source_release_available_at='2024-09-15T00:00:00+08:00')
    z['raw']['總價元'] = '12000000'; z['raw']['單價元平方公尺'] = '120000'; publication(z)
    duplicate = deepcopy(z); duplicate['physical_row_number'] = 2
    cutoff = '2024-10-01T00:00:00+08:00'
    xs = [x, y, z, duplicate]
    events = h.lineage_events(xs, cutoff, history_certificate=certification(xs, cutoff))
    assert [event['change_type'] for event in events] == ['ORIGINAL', 'REVISION', 'REVISION', 'DUPLICATE_RELEASE']
    assert select(xs, cutoff)['selected'][0]['raw']['總價元'] == '12000000'


def test_superseded_version_duplicates_are_still_duplicate_events():
    x = v3(item()); duplicate = deepcopy(x); duplicate['physical_row_number'] = 2
    y = later(x); xs = [x, duplicate, y]
    cutoff = '2024-10-01T00:00:00+08:00'
    events = h.lineage_events(xs, cutoff, history_certificate=certification(xs, cutoff))
    assert [event['change_type'] for event in events] == ['ORIGINAL', 'DUPLICATE_RELEASE', 'REVISION']
    reversed_events = h.lineage_events(list(reversed(xs)), cutoff, history_certificate=certification(xs, cutoff))
    assert reversed_events == events


def test_collision_and_conflicting_lineage_never_select():
    x = v3(item()); y = deepcopy(x); y['physical_row_number'] = 2
    y['raw']['總價元'] = '12000000'
    assert select([x, y])['selected'] == []
    y = later(x); y['supersedes_version_id'] = 'e'*64
    assert select([x, y], '2024-10-01T00:00:00+08:00')['selected'] == []


def test_namespace_is_derived_and_alternate_collisions_remain_unresolved():
    xs = [item(1, 移轉編號='SYNTHETIC'), item(2, 移轉編號='SYNTHETIC'), item(3)]
    result = h.namespace_analysis(xs)
    assert result['identifier_kind'] == 'DERIVED_RESEARCH_TRANSACTION_ID'
    assert result['candidate_fields']['transfer_number']['unresolved_groups'] == 1
    assert result['cross_release_stability'] == 'UNPROVEN'


def admission_inputs():
    return dict(approved_cohort=420, historical_publication=True, lineage=True,
        stable_namespace=True, no_known_temporal_leakage=True, chronological_coverage=True,
        deterministic_rebuild=True, privacy=True, target_contract_frozen=True)


@pytest.mark.parametrize('failed', list(admission_inputs()))
def test_each_admission_condition_is_required(failed):
    inputs = admission_inputs(); inputs[failed] = 0 if failed == 'approved_cohort' else False
    result = h.ml_b_admission(**inputs)
    assert result['result'] == 'BLOCKED'
    assert result['may_begin'] is False


def test_admission_pass_requires_the_entire_conjunction():
    assert h.ml_b_admission(**admission_inputs())['result'] == 'PASS'
    inputs = admission_inputs(); inputs['privacy'] = 'PASS'
    assert h.ml_b_admission(**inputs)['result'] == 'BLOCKED'


def test_v3_waterfall_has_explicit_chronological_stage():
    x = v3(item())
    result = h.data_gate([x], CUTOFF, history_certificate=certification([x]), coverage_evidence=None, pit_v3=True)
    assert result['version'] == 'ml-data-gate-v3'
    assert result['counts']['PIT_valid'] == 1
    assert result['counts']['chronological_viable'] == 0
    assert result['waterfall'][-2]['stage'] == 'chronological_viable'
    assert result['counts']['approved_training'] == 0


def test_v3_builder_and_verifier_preserve_zero_gate_and_byte_determinism(monkeypatch, tmp_path):
    assert importlib.util.find_spec('scripts.ml.audit_authoritative_lineage') is not None
    builder = importlib.import_module('scripts.ml.audit_authoritative_lineage')
    from scripts.ml import audit_target_reframing as previous
    from scripts.ml import source_recovery as r
    from scripts.ml.verify_authoritative_history_builds import compare
    x = item(); x['identity_evidence'] = None; x['cancellation_state_evidenced'] = False
    manifest = {'sources': [{'source_archive_id': 'synthetic-release', 'release_version': 'synthetic',
        'official_url': 'https://plvr.land.moi.gov.tw/synthetic', 'expected_sha256': 'a'*64,
        'sha256': 'a'*64, 'byte_size': 100, 'checksum_status': 'EXACT_MATCH',
        'package_valid': True, 'retrieved_at': '2024-07-01T00:00:00+08:00'}]}
    # Replace private source I/O only; all gate, lineage, aggregate and verifier logic is real.
    monkeypatch.setattr(previous, 'stage_sources', lambda *_: ([deepcopy(x)], manifest,
        {'source_bindings': [], 'joins': [], 'raw_detail_count': 0}))
    monkeypatch.setattr(r, 'ignored_destination', lambda path: path)
    first, second = tmp_path/'a', tmp_path/'b'
    for out in (first, second):
        builder.build({}, [], out, CUTOFF, '2026-10-10T23:30:00+08:00')
    result = compare(first, second)
    assert result['matched_files'] == 5
    data = json.loads((first/'evidence.json').read_text(encoding='utf-8'))
    assert data['counts']['official_main'] == 1
    assert data['counts']['PIT_valid'] == data['counts']['approved_training'] == 0
    assert data['ml_b_admission']['result'] == 'BLOCKED'
    assert data['ml_b_admission']['conditions']['deterministic_rebuild'] is False
    assert data['parking']['profiles']['candidates'] == {'NO_PARKING_INCLUDED': 1}


def test_build_output_privacy_rejects_owner_and_contact_fields():
    from scripts.ml.verify_authoritative_history_builds import check_privacy
    for payload in ({'owner_identity': 'synthetic'}, {'name': 'synthetic'}, {'phone_number': 'synthetic'}):
        with pytest.raises(ValueError, match='privacy'):
            check_privacy(payload)
