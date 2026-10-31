"""Admission must enforce a different target without weakening ML-A/B gates."""
import copy
import importlib
import importlib.util

import pytest


def module(name):
    assert importlib.util.find_spec(name), f'{name} must implement the Stage 3 contract'
    return importlib.import_module(name)


def record(**changes):
    r = dict(official_serial='RP12345678901234567', transaction_date='2024-06-30',
             city='新北市', district='新莊區', geographic_unit_kind='district',
             building_type='公寓(5樓含以下無電梯)', main_use='住家用', area_ping='30.25',
             total_price_ntd='10000000', gross_unit_price_ntd_ping='330578.5123966942148760330579',
             floor=3, total_floor=5, building_age_months_at_transaction=120,
             parking_basis='UNVERIFIED', rights_status='UNVERIFIED', training_authorized=False,
             historical_publication_proven=False, source_release_available_at=None,
             ordinary_sale_status='NO_REPORTED_NOTE_NOT_PROOF_OF_ARMS_LENGTH',
             provenance={'release':'113S2'})
    r.update(changes)
    return r


def test_gross_contract_authorizes_only_snapshot_target_with_unverified_rights():
    a = module('services.valuation_ml.admission')
    result = a.gate_decision(verified=True)
    assert result['training_authorized'] is True
    assert result['historical_point_in_time_authorized'] is False
    assert result['whole_dwelling_authorized'] is False
    assert result['parking_exclusive_authorized'] is False
    assert a.cohort_reason(record()) is None
    assert a.gate_decision(verified=False)['training_authorized'] is False


@pytest.mark.parametrize('changes,reason', [
    ({'official_serial':'RPWNMLNKNHLGFBF78EA'}, 'known_related_party_38652'),
    ({'official_serial':'DEMO12345678'}, 'sample_or_invalid_identity'),
    ({'official_serial':'SAMPLE12345678'}, 'sample_or_invalid_identity'),
    ({'transaction_date':'2027-01-01'}, 'outside_release_supported_window'),
    ({'transaction_date':'2013-01-01'}, 'outside_release_supported_window'),
    ({'ordinary_sale_status':'AMBIGUOUS'}, 'unresolved_note_status'),
    ({'main_use':None}, 'unsupported_use'),
    ({'geographic_unit_kind':'city'}, 'unsupported_geography'),
    ({'building_type':'工廠'}, 'unsupported_building_type'),
    ({'area_ping':'NaN'}, 'invalid_area'),
    ({'gross_unit_price_ntd_ping':'0'}, 'invalid_target'),
    ({'floor':7,'total_floor':5}, 'inconsistent_floors'),
])
def test_cohort_fails_closed(changes, reason):
    assert module('services.valuation_ml.admission').cohort_reason(record(**changes)) == reason


def test_temporal_split_and_source_release_membership_are_ordered():
    a = module('services.valuation_ml.admission')
    assert a.split_for(record()) == 'train'
    assert a.split_for(record(transaction_date='2024-07-01',provenance={'release':'114S2'})) == 'validation'
    assert a.split_for(record(transaction_date='2025-07-01',provenance={'release':'115S3'})) == 'holdout'
    assert a.split_for(record(provenance={'release':'115S3'})) is None
    assert a.split_for(record(transaction_date='2025-06-30',provenance={'release':'115S1'})) is None


def test_shared_feature_contract_never_consumes_targets_rights_parking_or_entity_ids():
    c = module('services.valuation_ml.contract')
    raw = record()
    subject = c.subject_from_record(raw)
    first = c.feature_values(subject)
    changed = copy.deepcopy(raw)
    changed.update(total_price_ntd='999999999',gross_unit_price_ntd_ping='999999',
                   road='Other Road',address_sha256='f'*64,canonical_id='e'*64,
                   parking_count_reported=4,rights_status='FULL',official_unit_price_ntd_sqm='5')
    assert c.feature_values(c.subject_from_record(changed)) == first
    assert c.feature_values(c.Subject.model_validate(subject.model_dump())) == first
    assert subject.city == '新北市'
    assert c.Subject.model_validate({**subject.model_dump(),'city':'臺北市','district':'大安區'}).city == '台北市'


@pytest.mark.parametrize('changes', [
    {'area_ping':True}, {'area_ping':float('inf')}, {'floor':0}, {'floor':6,'total_floor':5},
    {'building_type':'工廠'}, {'district':'不存在'}, {'transaction_date':'2027-01-01'},
    {'parking_spaces':1}, {'area_ping':'30'}, {'building_age_years':-1},
])
def test_subject_rejects_unsupported_and_fabricated_inputs(changes):
    c = module('services.valuation_ml.contract')
    valid=c.subject_from_record(record()).model_dump()
    with pytest.raises(ValueError):
        c.Subject.model_validate({**valid,**changes})


def test_unknown_structural_values_are_preserved_as_missing():
    c = module('services.valuation_ml.contract')
    s=c.subject_from_record(record(floor=None,total_floor=None,building_age_months_at_transaction=None))
    values=c.feature_values(s)
    assert values['floor'] is None and values['age_years'] is None and values['floor_ratio'] is None


def test_release_gaps_cannot_be_labeled_as_continuous_training_coverage():
    a=module('services.valuation_ml.admission')
    with pytest.raises(ValueError,match='release_coverage_gap'):
        a.continuous_window({'releases':[{'release':'105S4'},{'release':'115S3'}]})


def test_unverified_parking_values_never_change_gross_cohort_admission():
    a=module('services.valuation_ml.admission')
    for count in (None,0,1,5):
        assert a.cohort_reason(record(parking_count_reported=count)) is None
