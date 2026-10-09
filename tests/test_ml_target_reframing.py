"""Synthetic-only observed-transaction research contract proofs."""
from copy import deepcopy
from decimal import Decimal
import importlib
import json

import pytest

from scripts.ml import lineage as l, semantics as s, temporal as t


def b():
    return importlib.import_module('scripts.ml.observed_transaction')


def proof():
    return {'sha256': 'b'*64, 'locator': 'synthetic-reviewed-proof', 'version': 'synthetic-v1'}


def item(number=1, **changes):
    raw = {'交易標的': '房地(土地+建物)', '主要用途': '住家用', '建物型態': '公寓(5樓含以下無電梯)',
           '交易年月日': '1130615', '交易筆棟數': '土地2建物1車位0', '車位類別': '',
           '車位總價元': '0', '車位移轉總面積平方公尺': '0', '建物移轉總面積平方公尺': '100',
           '總價元': '10000000', '單價元平方公尺': '100000', '移轉層次': '三層', '總樓層數': '五層',
           '鄉鎮市區': '大安區', '縣市': '臺北市', '編號': f'SYNTHETIC-{number}', '備註': ''}
    raw.update(changes)
    ctx = {'member_name': 'a_lvr_land_a.csv', 'schema_evidence': proof(), 'source_schema_version': 'synthetic-v1',
           'parking_evidence': proof(), 'parking_detail_count': 0, 'blank_parking_means_absent': False,
           'area_evidence': proof(), 'area_basis': s.AREA_VERSION, 'full_rights': None, 'one_dwelling': None}
    return {'raw': raw, 'context': ctx, 'member_name': ctx['member_name'], 'source_dataset_id': s.SOURCE_DATASET_ID,
            'release_id': 'synthetic-release', 'archive_sha256': 'a'*64, 'member_sha256': 'c'*64,
            'physical_row_number': number, 'parse_error': None, 'import_batch_id': 'synthetic-batch',
            'parser_version': s.PARSER_VERSION, 'transform_version': s.TRANSFORM_VERSION,
            'ingested_at': '2024-07-01T00:00:00+08:00', 'transformed_at': '2024-07-01T00:00:00+08:00',
            'identity_evidence': proof(), 'cancellation_state_evidenced': True, 'cancelled': False,
            'supersedes_version_id': None, 'source_release_available_at': '2024-07-01T00:00:00+08:00',
            'availability_evidence': proof(), 'availability_quality': 'EXACT_PUBLICATION_TIME',
            'area_contract': {'field': '建物移轉總面積平方公尺', 'unit': 'm²'},
            'details_complete': True, 'main_key_unique': True,
            'details': {'build': [{'主要用途': '住家用', '建物移轉面積平方公尺': '100', '移轉情形': '持分移轉'}],
                        'land': [{'土地移轉面積平方公尺': '20', '移轉情形': '持分移轉'}], 'park': []}}


CUTOFF = '2024-08-01T00:00:00+08:00'


def test_target_b_is_an_observed_transfer_not_a_whole_dwelling():
    x = b().classify(item(), CUTOFF)
    assert x['target_valid']
    assert x['observation_unit'] == 'reported_transaction_occurrence'
    assert x['rights_status'] == 'UNVERIFIED_COMPLETE_DWELLING_RIGHTS'
    assert x['dwelling_status'] == 'UNVERIFIED_REGISTERED_UNIT_COUNT'
    assert Decimal(x['target']['area_ping']) == Decimal('30.2500')
    assert Decimal(x['target']['unit_price_ntd_ping']) == Decimal('10000000') / Decimal('30.25')
    assert x['target']['target_version'] != s.TARGET_VERSION
    assert x['special_status'] == 'NO_REPORTED_NOTE_NOT_PROOF_OF_ORDINARY_SALE'


@pytest.mark.parametrize('change,reason', [
    ({'交易標的': '房地(土地+建物)+車位'}, 'UNSUPPORTED_TRANSACTION_TYPE'),
    ({'交易標的': '土地'}, 'UNSUPPORTED_TRANSACTION_TYPE'),
    ({'交易標的': '車位'}, 'UNSUPPORTED_TRANSACTION_TYPE'),
    ({'主要用途': '商業用'}, 'NON_RESIDENTIAL_USE'),
    ({'交易筆棟數': '土地1建物2車位0'}, 'REPORTED_BUILDING_COUNT_NOT_ONE'),
    ({'交易筆棟數': ''}, 'OBJECT_COUNTS_UNPARSEABLE'),
    ({'交易筆棟數': '土地0建物1車位0'}, 'NO_REPORTED_LAND'),
    ({'車位總價元': '1'}, 'PARKING_PRESENT'),
    ({'車位移轉總面積平方公尺': '1'}, 'PARKING_PRESENT'),
    ({'車位總價元': ''}, 'PARKING_SEMANTICS_AMBIGUOUS'),
    ({'備註': '含車位'}, 'PARKING_SEMANTICS_AMBIGUOUS'),
    ({'備註': '親友交易'}, 'REPORTED_NOTE_REQUIRES_REVIEW'),
    ({'建物移轉總面積平方公尺': '0'}, 'INVALID_AREA'),
    ({'建物移轉總面積平方公尺': '-1'}, 'INVALID_AREA'),
    ({'總價元': 'NaN'}, 'INVALID_PRICE'),
    ({'總價元': '0'}, 'INVALID_PRICE'),
    ({'總價元': '-10'}, 'INVALID_PRICE'),
    ({'單價元平方公尺': '1'}, 'TARGET_RECONCILIATION_FAILED'),
    ({'單價元平方公尺': ''}, 'OFFICIAL_UNIT_PRICE_REQUIRED'),
    ({'移轉層次': '三層,四層'}, 'FLOOR_AMBIGUOUS'),
    ({'鄉鎮市區': '板橋區'}, 'INVALID_GEOGRAPHY'),
    ({'縣市': '新北市'}, 'INVALID_GEOGRAPHY'),
    ({'交易年月日': '11306'}, 'TRANSACTION_DAY_REQUIRED'),
    ({'交易年月日': '1150101'}, 'EFFECTIVE_AFTER_AVAILABILITY_OR_CUTOFF'),
])
def test_transaction_target_exclusions(change, reason):
    result = b().classify(item(**change), CUTOFF)
    assert not result['target_valid']
    assert reason in result['all_reasons']


@pytest.mark.parametrize('case', ['missing', 'parking', 'area', 'mixed', 'duplicate', 'incomplete', 'nonunique'])
def test_detail_ambiguity_fails_closed(case):
    x = item()
    if case == 'missing': x['details']['build'] = []
    if case == 'parking': x['details']['build'][0]['主要用途'] = '共有部分含停車空間'
    if case == 'area': x['details']['build'][0]['建物移轉面積平方公尺'] = '90'
    if case == 'mixed': x['details']['build'][0]['主要用途'] = '商業用'
    if case == 'duplicate': x['details']['build'] *= 2
    if case == 'incomplete': x['details_complete'] = False
    if case == 'nonunique': x['main_key_unique'] = False
    assert not b().classify(x, CUTOFF)['target_valid']


def test_common_detail_multiplicity_never_proves_single_unit():
    x = item()
    x['details']['build'][0]['建物移轉面積平方公尺'] = '80'
    x['details']['build'].append({'主要用途': '共有部分', '建物移轉面積平方公尺': '20', '移轉情形': '持分移轉'})
    result = b().classify(x, CUTOFF)
    assert result['target_valid']
    assert result['detail_composition'] == 'MULTIPLE_REGISTERED_PORTIONS_UNIT_ROLES_UNVERIFIED'
    assert result['dwelling_status'] == 'UNVERIFIED_REGISTERED_UNIT_COUNT'


def test_candidate_pit_and_approval_are_separate_and_conserved():
    x = item(); x['identity_evidence'] = None
    result = b().build_candidates([x, item(2, 總價元='0')], CUTOFF)
    assert result['counts'] == {'raw_observations': 2, 'structurally_valid_observations': 2,
                               'target_valid_candidates': 1, 'point_in_time_valid_observations': 0}
    assert len(result['ledger']) == 2
    assert len(result['candidates']) + len(result['candidate_exclusions']) == 2
    assert result['ledger'][0]['approved_training'] is False


@pytest.mark.parametrize('field,value', [('source_dataset_id', 'wrong'), ('member_sha256', 'bad'),
                                       ('archive_sha256', 'bad'), ('physical_row_number', 0)])
def test_source_identity_is_required(field, value):
    x = item(); x[field] = value
    assert not b().classify(x, CUTOFF)['structurally_valid']


def test_future_publication_cannot_enter_historical_pit():
    result = b().build_candidates([item()], '2024-06-30T00:00:00+08:00')
    assert len(result['candidates']) == 1
    assert not result['selected_rows']
    assert result['ledger'][0]['pit_reason'] == 'after_availability_cutoff'


def test_future_correction_does_not_overwrite_and_ineligible_current_does_not_resurrect():
    old = item(); future = deepcopy(old)
    future.update(release_id='synthetic-new-release', archive_sha256='d'*64,
                  source_release_available_at='2024-09-01T00:00:00+08:00',
                  supersedes_version_id=l.identify(old)['version_id'], revision_kind='CORRECTION', revision_evidence=proof())
    future['raw']['總價元'] = '0'
    assert len(b().build_candidates([future, old], CUTOFF)['selected_rows']) == 1
    assert not b().build_candidates([future, old], '2024-10-01T00:00:00+08:00')['selected_rows']


def test_duplicate_ids_cannot_enter_twice_and_input_order_is_deterministic():
    x = item(); duplicate = deepcopy(x); duplicate['physical_row_number'] = 2
    result = b().build_candidates([duplicate, x], CUTOFF)
    assert len(result['selected_rows']) == 1
    assert result == b().build_candidates([x, duplicate], CUTOFF)
    with pytest.raises(ValueError, match='duplicate_physical_occurrence'):
        b().build_candidates([x, x], CUTOFF)


def test_historical_freezes_use_target_b_and_never_arbitrary_dates():
    from scripts.ml import chronology
    x = item()
    result = b().build_candidates([x], CUTOFF)
    rows = chronology.split_rows_from_items(result['selected_rows'])
    splits = chronology.design_splits(rows, coverage_evidence=None, ledger_items=[x],
                                     label_observation_cutoff=CUTOFF, cohort_selector=b().build_candidates)
    assert not splits['viable']
    assert splits['assignments'] == []
    assert 'INSUFFICIENT_CHRONOLOGICAL_MONTHS' in splits['blockers']


def test_features_are_allowlisted_and_prediction_calendar_is_explicit():
    x = item(); x['raw']['建築完成年月'] = '1000101'; x['current_routes'] = {'minutes': 3}
    target = b().classify(x, CUTOFF)['target']
    values = b().feature_values(x, target)
    assert set(values) == set(b().FEATURE_COLUMNS)
    assert not any(key in values for key in ['總價元', '單價元平方公尺', 'current_routes', 'age', 'revision_kind'])
    assert values['prediction_month'] == 6


def test_baselines_require_frozen_fit_versions_and_target_b():
    x = item(); ids = l.identify(x)
    kwargs = {'prediction_at': CUTOFF, 'fitting_cutoff': CUTOFF, 'subject_family': 'synthetic-other',
              'fitting_versions': {ids['transaction_family_id']: ids['version_id']}}
    assert len(b().baseline_history([x], **kwargs)) == 1
    assert b().baseline_history([x], **{**kwargs, 'subject_family': ids['transaction_family_id']}) == []
    assert b().baseline_history([x], **{**kwargs, 'fitting_versions': {ids['transaction_family_id']: 'wrong'}}) == []
    with pytest.raises(ValueError, match='frozen_fit_versions'):
        b().baseline_history([x], **{**kwargs, 'fitting_versions': None})


def test_date_only_and_current_observation_are_never_backdated():
    record = {'quality': 'DATE_ONLY_PUBLICATION', 'release_id': 'synthetic', 'archive_sha256': 'a'*64,
              'value': '2024-07-01', 'evidence': proof()}
    resolved = t.resolve_availability(record, 'synthetic', 'a'*64)
    assert not t.available_by(resolved, '2024-07-01T23:59:59+08:00')
    assert t.available_by(resolved, '2024-07-02T00:00:00+08:00')
    record.update(quality='CONSERVATIVE_UPPER_BOUND', value='2026-10-08T00:00:00+08:00')
    assert not t.available_by(t.resolve_availability(record, 'synthetic', 'a'*64), CUTOFF)


def test_contract_and_committed_aggregate_cannot_contain_transaction_rows():
    root = s.ROOT/'docs/ml'
    contract = json.loads((root/'contracts/observed-transaction-target-v1.json').read_text(encoding='utf-8'))
    assert contract['production_valuation_approval'] is False
    assert contract['observation_unit'] == 'reported_transaction_occurrence'
    evidence_path = root/'valuation-target-reframing-evidence-v1.json'
    if evidence_path.exists():
        data = evidence_path.read_text(encoding='utf-8')
        for private in ['physical_occurrence_id', 'transaction_family_id', 'source_record_version_id', '土地位置建物門牌', 'SYNTHETIC-']:
            assert private not in data


def test_offline_builder_is_create_only_and_two_builds_match(monkeypatch, tmp_path):
    audit = importlib.import_module('scripts.ml.audit_target_reframing')
    source = {'release_version': '112S3', 'source_archive_id': 'synthetic-release', 'sha256': 'a'*64,
              'checksum_status': 'EXACT_MATCH', 'package_valid': True, 'byte_size': 123,
              'official_url': 'https://example.invalid/synthetic.zip', 'retrieved_at': CUTOFF}
    monkeypatch.setattr(audit, 'stage_sources', lambda *args: ([item()], {'sources': [source]},
                        {'source_bindings': [], 'joins': [], 'raw_detail_count': 2, 'availability_bounds': []}))
    monkeypatch.setattr(audit.r, 'ignored_destination', lambda path: path)
    first = audit.build({}, [], tmp_path/'one', CUTOFF, CUTOFF)
    second = audit.build({}, [], tmp_path/'two', CUTOFF, CUTOFF)
    assert first == second
    assert first['counts']['target_valid_candidates'] == 1
    assert first['counts']['point_in_time_valid_observations'] == 1
    assert first['counts']['approved_training_cohort'] == 0
    assert first['target_b_status'] == 'BLOCKED'
    assert first['hashes'] == second['hashes']
    assert all(p.read_bytes() == (tmp_path/'two'/p.name).read_bytes() for p in (tmp_path/'one').iterdir())
    assert (tmp_path/'one'/'approved-membership.jsonl').read_bytes() == b''
    with pytest.raises(ValueError, match='clean_build_destination'):
        audit.build({}, [], tmp_path/'one', CUTOFF, CUTOFF)


def test_archive_verification_precedes_parsing(monkeypatch):
    audit = importlib.import_module('scripts.ml.audit_target_reframing')
    monkeypatch.setattr(audit.r, 'build_manifest', lambda *args: {'sources': []})
    with pytest.raises(ValueError, match='exact_bounded_two_release'):
        audit.stage_sources({}, [], CUTOFF)


def test_builder_disallows_cutoff_later_than_logical_observation(tmp_path):
    audit = importlib.import_module('scripts.ml.audit_target_reframing')
    with pytest.raises(ValueError, match='cutoff_after_observation'):
        audit.build({}, [], tmp_path/'one', CUTOFF, '2024-01-01T00:00:00+08:00')


def test_complete_chronological_b_cohort_uses_b_not_a(monkeypatch):
    from datetime import date
    from scripts.ml import chronology
    ledger = []
    for n in range(21):
        year, month = 2022+n//12, n%12+1
        x = item(n+1, 交易年月日=f'{year-1911:03d}{month:02d}15')
        x.update(release_id=f'synthetic-release-{n}', archive_sha256=l.digest(n),
                 source_release_available_at=f'{year:04d}-{month:02d}-20T00:00:00+08:00')
        ledger.append(x)
    cutoff = '2023-10-01T00:00:00+08:00'
    result = b().build_candidates(ledger, cutoff)
    rows = chronology.split_rows_from_items(result['selected_rows'])
    args = {'coverage_evidence': proof(), 'ledger_items': ledger, 'label_observation_cutoff': cutoff,
            'min_month_rows': 1, 'min_block_subgroup_rows': 1}
    splits = chronology.design_splits(rows, **args, cohort_selector=b().build_candidates)
    assert splits['viable']
    assert len(splits['assignments']) == 21
    assert set(x['split'] for x in splits['assignments']) == {'TRAIN', 'VALIDATION', 'CALIBRATION', 'TEST'}
    assert not chronology.design_splits(rows, **args)['viable']  # A still rejects unproved rights.
    assert chronology.design_splits([*rows, rows[0]], **args, cohort_selector=b().build_candidates)['assignments'] == []


def test_baselines_exclude_labels_available_at_prediction_boundary():
    x = item(); ids = l.identify(x)
    assert b().baseline_history([x], prediction_at=x['source_release_available_at'], fitting_cutoff=CUTOFF,
              subject_family='other', fitting_versions={ids['transaction_family_id']: ids['version_id']}) == []


def test_enriched_source_manifest_remains_the_bound_availability_evidence(monkeypatch):
    audit = importlib.import_module('scripts.ml.audit_target_reframing')
    sources = []
    for season in ('112S3', '115S2'):
        sources.append({'release_version': season, 'source_archive_id': 'synthetic-'+season,
                        'sha256': 'a'*64, 'expected_sha256': 'a'*64, 'checksum_status': 'EXACT_MATCH',
                        'package_valid': True, 'local_recovered_path': 'synthetic.zip', 'download_attempts': 1,
                        'official_url': 'https://plvr.land.moi.gov.tw/synthetic',
                        'http_download': {'status_code': 200, 'final_url': 'https://plvr.land.moi.gov.tw/synthetic'},
                        'retrieval_started_at': '2024-07-01T00:00:00+08:00',
                        'retrieved_at': '2024-07-01T01:00:00+08:00'})
    monkeypatch.setattr(audit.r, 'build_manifest', lambda *args: {'sources': deepcopy(sources)})
    class Archive:
        def __init__(self, *args): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
    monkeypatch.setattr(audit.zipfile, 'ZipFile', Archive)
    def tables(archive, source, members):
        source['schema_identity'] = [{'sha256': 'd'*64}]
        synthetic = item()
        family = {}
        for kind in ('main', 'build', 'land', 'park'):
            raws = [synthetic['raw']] if kind == 'main' else synthetic['details'][kind]
            raws = [{**r, '編號': 'SYNTHETIC-1'} for r in raws]
            family[kind] = {'records': [{'raw': r, 'parse_error': None, 'record_number': n+1,
                                        'start_line': n+1, 'end_line': n+1} for n, r in enumerate(raws)],
                            'sha256': 'e'*64}
        return {'a_lvr_land_a.csv': family}
    monkeypatch.setattr(audit.a, '_load_members', tables)
    rows, manifest, _ = audit.stage_sources({}, [], CUTOFF)
    assert all(x['availability_evidence']['sha256'] == l.digest(manifest) for x in rows)


def test_building_type_normalization_is_consistent_in_candidates_and_splits():
    from scripts.ml import chronology
    x = item(建物型態=' 公寓(5樓含以下無電梯) ')
    assert b().classify(x, CUTOFF)['target_valid']
    result = b().build_candidates([x], CUTOFF)
    assert result['candidates'][0]['features']['building_type'] == '公寓'
    assert chronology.split_rows_from_items(result['selected_rows'])[0]['building_type'] == '公寓'
