"""Synthetic evidence contracts; fixtures never establish real source authority."""
from copy import deepcopy
import importlib
import importlib.util
import json

import pytest

from scripts.ml import lineage as l
from tests.test_ml_target_reframing import item, proof, CUTOFF


def h():
    assert importlib.util.find_spec('scripts.ml.historical') is not None, 'strict historical selector missing'
    return importlib.import_module('scripts.ml.historical')


def publication(x):
    x['publication_evidence'] = {
        'classification': 'AUTHENTICATED', 'release_id': x['release_id'],
        'archive_sha256': x['archive_sha256'], 'quality': 'EXACT_PUBLICATION_TIME',
        'value': x['source_release_available_at'], 'evidence': proof(),
    }
    return x


def certification(xs, cutoff=CUTOFF):
    """Synthetic reviewer-supplied history certificate for the visible event set."""
    visible = [x for x in xs if l.timestamp(x['source_release_available_at']) <= l.timestamp(cutoff)]
    return {'evidence': proof(), 'classification': 'AUTHENTICATED',
            'cutoff': cutoff, 'source_dataset_id': item()['source_dataset_id'],
            'visible_ledger_sha256': h().ledger_digest(visible),
            'stable_namespace': True, 'complete_revision_cancellation_history': True,
            'replacement_links_complete': True}


def select(xs, cutoff=CUTOFF):
    return h().select_as_of(xs, cutoff, history_certificate=certification(xs, cutoff))


def later(x, *, cancelled=False, replacement=False):
    y = deepcopy(x)
    y.update(release_id='synthetic-later', archive_sha256='d'*64,
             source_release_available_at='2024-09-01T00:00:00+08:00',
             supersedes_version_id=l.identify(x)['version_id'], cancelled=cancelled,
             revision_kind='CANCELLATION' if cancelled else 'SUPERSESSION' if replacement else 'CORRECTION',
             revision_evidence=proof())
    if not cancelled:
        y['raw']['總價元'] = '11000000'
        y['raw']['單價元平方公尺'] = '110000'
    return publication(y)


@pytest.mark.parametrize('cancelled,replacement', [(False, False), (True, False), (False, True)])
def test_future_event_does_not_change_earlier_version(cancelled, replacement):
    x = publication(item())
    y = later(x, cancelled=cancelled, replacement=replacement)
    assert select([x, y])['selected'] == select([x])['selected']
    after = select([x, y], '2024-10-01T00:00:00+08:00')
    assert len(after['selected']) == (0 if cancelled else 1)
    if not cancelled:
        assert after['selected'][0]['raw']['總價元'] == '11000000'
    assert after['relations'][0]['classification'] == y['revision_kind']


def test_missing_history_certificate_cannot_approve_real_or_synthetic_rows():
    result = h().select_as_of([publication(item())], CUTOFF, history_certificate=None)
    assert result['selected'] == []
    assert result['excluded_reasons'] == {'COMPLETE_HISTORY_UNPROVEN': 1}


@pytest.mark.parametrize('field,value', [('archive_sha256', 'e'*64), ('release_id', 'other'),
                                      ('classification', 'CURRENT_ONLY'), ('quality', 'SYSTEM_FIRST_SEEN')])
def test_publication_must_bind_exact_archive_and_qualify_time(field, value):
    x = publication(item())
    x['publication_evidence'][field] = value
    assert h().select_as_of([x], CUTOFF, history_certificate=None)['selected'] == []


def test_late_retrieval_bound_cannot_prove_historical_publication():
    x = publication(item())
    x['publication_evidence'].update(quality='CONSERVATIVE_UPPER_BOUND', value='2026-10-08T00:00:00+08:00')
    assert h().select_as_of([x], CUTOFF, history_certificate=None)['selected'] == []


def test_duplicate_current_records_select_one_and_report_duplicate():
    x = publication(item())
    y = deepcopy(x); y['physical_row_number'] = 2
    result = select([x, y])
    assert len(result['selected']) == 1
    assert result['excluded_reasons'] == {'exact_duplicate': 1}


def test_conflicting_historical_records_fail_closed():
    x = publication(item())
    y = deepcopy(x); y['raw']['總價元'] = '12000000'
    result = select([x, y])
    assert result['selected'] == []
    assert result['excluded_reasons'] == {'occurrence_conflict': 2}


def test_unknown_lineage_and_missing_cancellation_evidence_fail_closed():
    x = publication(item()); x['cancellation_state_evidenced'] = False
    assert select([x])['selected'] == []
    x['cancellation_state_evidenced'] = True; x['identity_evidence'] = None
    assert select([x])['selected'] == []


def test_changed_identifier_replacement_requires_explicit_cross_family_link():
    x = publication(item()); y = later(x)
    y['raw']['編號'] = 'SYNTHETIC-REPLACEMENT'
    result = select([x, y], '2024-10-01T00:00:00+08:00')
    assert result['selected'] == []
    assert result['excluded_reasons'] == {'CROSS_NAMESPACE_REPLACEMENT_UNRESOLVED': 2}


def test_certificate_cannot_be_reused_for_different_cutoff_or_ledger():
    x = publication(item()); cert = certification([x])
    assert h().select_as_of([x], '2024-08-02T00:00:00+08:00', history_certificate=cert)['selected'] == []
    x['raw']['總價元'] = '12000000'
    assert h().select_as_of([x], CUTOFF, history_certificate=cert)['selected'] == []


def test_date_only_publication_uses_next_taipei_midnight():
    x = publication(item())
    x['publication_evidence'].update(quality='DATE_ONLY_PUBLICATION', value='2024-07-01')
    assert h().select_as_of([x], '2024-07-01T23:59:59+08:00', history_certificate=None)['selected'] == []
    cutoff = '2024-07-02T00:00:00+08:00'
    assert len(select([x], cutoff)['selected']) == 1


@pytest.mark.parametrize('change,expected', [({}, 'NO_PARKING_INCLUDED'),
    ({'車位總價元': ''}, 'MISSING'),
    ({'車位總價元': '1000000', '車位移轉總面積平方公尺': '20', '車位類別': '坡道平面',
      '交易筆棟數': '土地2建物1車位1'}, 'PARKING_SEPARABLE_REPORTED'),
    ({'車位總價元': '0', '車位移轉總面積平方公尺': '0', '車位類別': '坡道平面',
      '交易筆棟數': '土地2建物1車位1'}, 'STRUCTURALLY_INSEPARABLE'),
    ({'備註': '含車位'}, 'AMBIGUOUS')])
def test_parking_categories_never_estimate_deduction(change, expected):
    x = item(**change)
    if expected in {'PARKING_SEPARABLE_REPORTED', 'STRUCTURALLY_INSEPARABLE'}:
        x['details']['park'] = [{'車位總價元': x['raw']['車位總價元']}]
    result = h().parking_treatment(x)
    assert result['category'] == expected
    assert result['target_b_allowed'] == (expected == 'NO_PARKING_INCLUDED')


def test_chronological_profile_reports_actual_gaps_and_contiguous_run():
    result = h().month_profile({'2023-01': 4, '2023-02': 5, '2023-04': 8})
    assert result['unique_months'] == 3
    assert result['longest_contiguous_months'] == 2
    assert result['longest_contiguous_period'] == ['2023-01', '2023-02']
    assert result['missing_months'] == ['2023-03']


def test_nonzero_counts_do_not_approve_without_chronological_contract():
    x = publication(item())
    result = h().data_gate([x], CUTOFF, history_certificate=certification([x]), coverage_evidence=None)
    assert result['counts']['PIT_valid'] == 1
    assert result['counts']['approved_training'] == 0
    assert result['target_b'] == 'BLOCKED'
    assert result['target_a'] == 'BLOCKED'
    assert result['ml_b_may_begin'] is False


def test_duplicate_physical_locator_cannot_inflate_gate_counts():
    x = publication(item())
    with pytest.raises(ValueError, match='duplicate_physical_occurrence_input'):
        h().data_gate([x, deepcopy(x)], CUTOFF, history_certificate=None, coverage_evidence=None)


def test_certificate_bundle_resolves_exact_freeze_only():
    x = publication(item()); cert = certification([x])
    bundle = {'certificates': [cert]}
    assert len(h().select_as_of([x], CUTOFF, history_certificate=bundle)['selected']) == 1
    assert h().select_as_of([x], '2024-08-02T00:00:00+08:00', history_certificate=bundle)['selected'] == []
    assert h().select_as_of([x], CUTOFF, history_certificate={'certificates': [cert, cert]})['selected'] == []


def test_offline_builder_exists_for_create_only_aggregate_builds():
    assert importlib.util.find_spec('scripts.ml.audit_authoritative_history') is not None


def test_revision_requires_explicit_kind_and_authoritative_edge_evidence():
    x = publication(item()); y = later(x)
    y.pop('revision_kind'); y.pop('revision_evidence')
    assert select([x, y], '2024-10-01T00:00:00+08:00')['selected'] == []


def test_cancellation_state_must_be_explicit_even_for_first_observed_version():
    x = publication(item()); x.pop('cancellation_state_evidenced')
    assert select([x])['selected'] == []


def mature_panel():
    rows = []
    for m in range(21):
        year, month = 2023 + m//12, m%12 + 1
        for number in range(20):
            x = item(m*20 + number + 1, 交易年月日=f'{year-1911:03d}{month:02d}15')
            x.update(release_id=f'synthetic-{year}-{month:02d}', archive_sha256=l.digest([year, month]),
                     source_release_available_at=f'{year}-{month:02d}-20T00:00:00+08:00')
            rows.append(publication(x))
    return rows


def test_gate_can_pass_only_with_complete_mature_freeze_certificates():
    rows = mature_panel(); cutoff = '2024-10-01T00:00:00+08:00'
    freezes = ['2023-12-31T23:59:59.999999+08:00', '2024-03-31T23:59:59.999999+08:00',
               '2024-06-30T23:59:59.999999+08:00', cutoff]
    bundle = {'certificates': [certification(rows, freeze) for freeze in freezes]}
    result = h().data_gate(rows, cutoff, history_certificate=bundle, coverage_evidence=proof())
    assert result['counts']['approved_training'] == 420
    assert result['target_b'] == 'PASS'
    assert result['ml_b_may_begin'] is True
    assert result['target_a'] == 'BLOCKED'
    assert set(x['split'] for x in result['chronology']['assignments']) == {'TRAIN', 'VALIDATION', 'CALIBRATION', 'TEST'}
    bundle['certificates'] = bundle['certificates'][1:]
    blocked = h().data_gate(rows, cutoff, history_certificate=bundle, coverage_evidence=proof())
    assert blocked['counts']['approved_training'] == 0
    assert 'HISTORICAL_MEMBERSHIP_DIFFERS' in blocked['chronology']['blockers']


def test_replacement_without_predecessor_cannot_leave_both_sales_active():
    x = publication(item()); y = later(x, replacement=True)
    y['raw']['編號'] = 'SYNTHETIC-NEW-ID'; y['supersedes_version_id'] = None
    result = select([x, y], '2024-10-01T00:00:00+08:00')
    assert result['selected'] == []


def test_legacy_blank_parking_override_never_qualifies_history_gate():
    x = publication(item(車位總價元=''))
    x['context']['blank_parking_means_absent'] = True
    assert h().parking_treatment(x)['category'] == 'MISSING'
    gate = h().data_gate([x], CUTOFF, history_certificate=certification([x]), coverage_evidence=None)
    assert gate['counts']['PIT_valid'] == 0


def test_duplicate_main_payload_with_conflicting_detail_content_fails_closed():
    x = publication(item()); y = deepcopy(x); y['physical_row_number'] = 2
    y['details']['build'][0]['主要用途'] = '共有部分停車位'
    assert select([x, y])['selected'] == []


def test_publication_proof_clock_controls_every_gate_count():
    x = publication(item()); x['source_release_available_at'] = '2020-01-01T00:00:00+08:00'
    cert = certification([x])
    gate = h().data_gate([x], CUTOFF, history_certificate=cert, coverage_evidence=None)
    assert gate['counts']['structurally_valid'] == 1
    assert gate['counts']['target_valid'] == 1
    assert gate['counts']['historically_supported'] == 1
    assert gate['counts']['PIT_valid'] == 1
    assert gate['waterfall'][-2]['accepted_count'] == 1


def test_future_unverified_revision_cannot_change_target_a_earlier_membership():
    x = publication(item())
    x['context'].update(full_rights=True, one_dwelling=True, rights_evidence=proof(), special_transaction=False)
    x['semantic'] = {'rights': 'FULL_RIGHTS_CONFIRMED', 'dwelling': 'SINGLE_DWELLING_CONFIRMED',
                     'parking': 'NO_PARKING_CONFIRMED'}
    y = later(x); y['identity_evidence'] = None
    alone = h().data_gate([x], CUTOFF, history_certificate=certification([x]), coverage_evidence=None)
    with_future = h().data_gate([x, y], CUTOFF, history_certificate=certification([x, y]), coverage_evidence=None)
    assert alone['target_a_pit_count'] == with_future['target_a_pit_count'] == 1


def test_duplicate_main_with_conflicting_join_flags_cannot_select_representative():
    x = publication(item()); y = deepcopy(x); y['physical_row_number'] = 2
    y['details_complete'] = False
    assert select([x, y])['selected'] == []


def verifier():
    assert importlib.util.find_spec('scripts.ml.verify_authoritative_history_builds') is not None
    return importlib.import_module('scripts.ml.verify_authoritative_history_builds')


@pytest.mark.parametrize('payload', [{'編號': 'SYNTHETIC'}, {'occurrence_id': 'a'*64},
    {'raw': {'address': 'SYNTHETIC'}}, {'path': 'C:/machine/private'},
    {'target': '123456.7'}, {'姓名': 'SYNTHETIC'}])
def test_output_privacy_rejects_row_fields_and_absolute_paths(payload):
    with pytest.raises(ValueError, match='privacy'):
        verifier().check_privacy(payload)


def synthetic_outputs(destination, *, bad_hash=False):
    destination.mkdir()
    hashes = {}
    for name in ('evidence.json', 'data-gate.json', 'source-inventory.json', 'build-manifest.json'):
        data = l.canonical_bytes({'safe_counts': {'approved_training': 0}})+b'\n'
        (destination/name).write_bytes(data)
        import hashlib
        hashes[name] = hashlib.sha256(data).hexdigest()
    if bad_hash:
        hashes['data-gate.json'] = 'e'*64
    (destination/'output-hashes.json').write_bytes(l.canonical_bytes(hashes)+b'\n')


def test_build_verifier_compares_all_bytes_and_checks_manifest_hashes(tmp_path):
    first, second = tmp_path/'a', tmp_path/'b'
    synthetic_outputs(first); synthetic_outputs(second)
    assert verifier().compare(first, second)['matched_files'] == 5
    (second/'data-gate.json').write_bytes(b'{}\n')
    with pytest.raises(ValueError):
        verifier().compare(first, second)


def test_identically_corrupted_manifests_cannot_pass_determinism(tmp_path):
    first, second = tmp_path/'a', tmp_path/'b'
    synthetic_outputs(first, bad_hash=True); synthetic_outputs(second, bad_hash=True)
    with pytest.raises(ValueError, match='hash'):
        verifier().compare(first, second)


def test_unknown_output_artifact_cannot_skip_privacy_audit(tmp_path):
    first, second = tmp_path/'a', tmp_path/'b'
    synthetic_outputs(first); synthetic_outputs(second)
    for destination in (first, second):
        (destination/'raw-rows.json').write_text('{}', encoding='utf-8')
    with pytest.raises(ValueError, match='artifact'):
        verifier().compare(first, second)


def test_namespace_analysis_measures_both_reported_identifier_fields():
    xs = [item(1, 移轉編號='SYNTHETIC-ALTERNATIVE'), item(2, 移轉編號='SYNTHETIC-ALTERNATIVE'), item(3)]
    result = h().namespace_analysis(xs)
    serial, alternative = result['candidate_fields']['main_serial'], result['candidate_fields']['transfer_number']
    assert serial['unique_nonblank_scoped_keys'] == 3
    assert alternative['missing_observations'] == 1
    assert alternative['repeated_key_groups'] == 1
    assert alternative['different_main_serial_groups'] == 1
    assert result['verdict'] == 'UNVERIFIED_STABLE_NAMESPACE'
    assert 'SYNTHETIC-ALTERNATIVE' not in json.dumps(result)
