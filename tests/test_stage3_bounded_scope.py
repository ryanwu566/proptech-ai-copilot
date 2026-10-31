"""Evidence omissions must restrict claims without pretending to resolve them."""
import importlib
import importlib.util

import pytest
from tests.test_stage3_ml_api import artifact


def policy():
    assert importlib.util.find_spec('services.plvr_ml_admissibility'), 'explicit bounded evidence policy required'
    return importlib.import_module('services.plvr_ml_admissibility')


def family(**changes):
    evidence=dict(official_serial='RP12345678901234567',version_count=1,identity_has_note=False,
                  fact_has_note=False,fact_identity_count=1,quality_reason=None,
                  explicit_cancelled=False,explicit_superseded=False)
    evidence.update(changes);return evidence


def test_snapshot_is_permitted_without_claiming_publication_or_active_legal_status():
    r=policy().family_admissibility(family())
    assert r['admit_archive_observation'] is True
    assert r['historical_pit_proven'] is False
    assert r['current_cancellation_state_proven'] is False


@pytest.mark.parametrize('changes,reason',[
    ({'version_count':2},'observed_revision_conflict'),
    ({'identity_has_note':True},'observed_special_note'),
    ({'fact_has_note':True},'note_tainted_fact_family'),
    ({'fact_identity_count':2},'ambiguous_identity'),
    ({'explicit_cancelled':True},'explicit_cancellation'),
    ({'explicit_superseded':True},'explicit_supersession'),
    ({'official_serial':'RPWNMLNKNHLGFBF78EA'},'known_related_party_38652'),
])
def test_known_ineligible_family_cannot_be_admitted(changes,reason):
    r=policy().family_admissibility(family(**changes))
    assert r['admit_archive_observation'] is False and r['reason']==reason


def test_disappearance_or_release_label_never_becomes_cancellation_evidence():
    r=policy().family_admissibility(family(later_release_absent=True,last_release='115S3'))
    assert r['admit_archive_observation'] is True
    assert r['current_cancellation_state_proven'] is False
    assert r['historical_pit_proven'] is False


def test_unknown_rights_are_transfer_observations_never_whole_dwelling_proof():
    p=policy()
    assert p.rights_eligibility('UNVERIFIED','reported_transfer')['eligible'] is True
    assert p.rights_eligibility('UNVERIFIED','whole_dwelling')['eligible'] is False
    assert p.rights_eligibility('FULL_RIGHTS_CONFIRMED','whole_dwelling')['eligible'] is False
    assert p.rights_eligibility('PARTIAL_RIGHTS','reported_transfer')['eligible'] is False


def test_parking_features_and_whole_property_claims_are_explicitly_absent():
    scope=policy().public_scope()
    assert scope['parking_features_included'] is False
    assert scope['parking_exclusive_value_supported'] is False
    assert scope['whole_dwelling_value_supported'] is False
    assert scope['requested_value_basis']=='reported_transfer'
    assert scope['publication_evidence']=='bounded_archive_snapshot'
    assert scope['unobserved_cancellation_risk']=='not_eliminated'
    assert scope['cancellation_event_ledger_available'] is False


def test_audit_requires_exact_bytes_bound_to_prior_full_verification(tmp_path):
    import hashlib,json
    assert importlib.util.find_spec('scripts.ml.audit_stage3_bounds'), 'streaming audit required'
    from scripts.ml.audit_stage3_bounds import verify_inputs
    names=['coverage.json','lineage.sqlite','provenance-manifest.json','schema.json','transactions.jsonl.gz']
    for name in names:(tmp_path/name).write_text('{}')
    summary={'schema':'plvr-local-canonical-history-v1','dataset_fingerprint':'a'*64,
        'logical_dataset_sha256':'b'*64,'counts':{'clean_transactions':1},
        'artifact_hashes':{name:hashlib.sha256(b'{}').hexdigest() for name in names}}
    (tmp_path/'summary.json').write_text(json.dumps(summary))
    (tmp_path/'COMPLETE.json').write_text(json.dumps({'dataset_fingerprint':'a'*64,
        'summary_sha256':hashlib.sha256((tmp_path/'summary.json').read_bytes()).hexdigest()}))
    verification={'status':'PASS','dataset_fingerprint':'a'*64,'clean_transactions':1,'logical_dataset_sha256':'b'*64}
    admission={'dataset_fingerprint':'a'*64,'source_artifact_hashes':dict(summary['artifact_hashes']),
               'source_summary_sha256':hashlib.sha256((tmp_path/'summary.json').read_bytes()).hexdigest()}
    verify_inputs(tmp_path,verification,admission)
    (tmp_path/'transactions.jsonl.gz').write_text('changed')
    with pytest.raises(ValueError,match='checksum'):verify_inputs(tmp_path,verification,admission)
    with pytest.raises(ValueError,match='verification'):verify_inputs(tmp_path,{'status':'BLOCKED'},admission)


def test_rewritten_summary_cannot_rebind_changed_bytes_to_prior_verification(tmp_path):
    import hashlib,json
    from scripts.ml.audit_stage3_bounds import verify_inputs
    names=['coverage.json','lineage.sqlite','provenance-manifest.json','schema.json','transactions.jsonl.gz']
    h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    for name in names:(tmp_path/name).write_text('{}')
    summary={'schema':'plvr-local-canonical-history-v1','dataset_fingerprint':'a'*64,
        'logical_dataset_sha256':'b'*64,'counts':{'clean_transactions':1},
        'artifact_hashes':{name:h(tmp_path/name) for name in names}}
    (tmp_path/'summary.json').write_text(json.dumps(summary))
    frozen={'dataset_fingerprint':'a'*64,'source_artifact_hashes':dict(summary['artifact_hashes']),
            'source_summary_sha256':h(tmp_path/'summary.json')}
    (tmp_path/'transactions.jsonl.gz').write_text('different bytes')
    summary['artifact_hashes']['transactions.jsonl.gz']=h(tmp_path/'transactions.jsonl.gz')
    (tmp_path/'summary.json').write_text(json.dumps(summary))
    (tmp_path/'COMPLETE.json').write_text(json.dumps({'dataset_fingerprint':'a'*64,
        'summary_sha256':h(tmp_path/'summary.json')}))
    verification={'status':'PASS','dataset_fingerprint':'a'*64,'clean_transactions':1,'logical_dataset_sha256':'b'*64}
    with pytest.raises(ValueError,match='prior_admission_checksum'):verify_inputs(tmp_path,verification,frozen)


@pytest.mark.parametrize('note',['部分持分交易','僅移轉二分之一權利','契約解除／交易撤銷','更正前案／取代舊案'])
def test_observed_partial_cancel_or_supersession_note_cannot_resurrect_old_version(tmp_path,note):
    from tests.test_plvr_historical_dataset import build,row
    # An earlier ordinary-looking version must not survive a later disqualifying observation.
    _,result=build(tmp_path,[('113S1',[row()]),('113S2',[row(備註=note)])])
    assert result['counts']['clean_transactions']==0
    assert result['exclusions_by_reason']['special_note_requires_review']==1


def test_later_quarter_absence_does_not_silently_delete_an_archive_observation(tmp_path):
    from tests.test_plvr_historical_dataset import build,row
    _,result=build(tmp_path,[('113S1',[row()]),('113S2',[])])
    assert result['counts']['clean_transactions']==1
    assert result['training_authorized'] is False


@pytest.mark.parametrize('unsupported',['whole_dwelling','parking_exclusive','partial_rights','whole_property'])
def test_api_rejects_unsupported_value_basis_before_loading_model(monkeypatch,unsupported):
    from tests.test_stage3_ml_api import client_for,payload,inference
    client=client_for(monkeypatch,inference().InferenceService(None,None))
    r=client.post('/valuation/ml/v1/estimate',json={**payload(),'requested_value_basis':unsupported})
    assert r.status_code==422


def test_reported_transfer_request_has_identical_model_features_and_explicit_scope():
    from backend.api.routes_valuation_ml import MLValuationRequest
    from services.valuation_ml.contract import Subject,feature_values
    from tests.test_stage3_ml_api import payload
    base=Subject(**payload());request=MLValuationRequest(**payload(),requested_value_basis='reported_transfer')
    assert feature_values(base)==feature_values(request)
    assert request.model_dump(exclude={'requested_value_basis'})==base.model_dump()


def test_api_status_includes_explicit_scope_without_changing_model_identity(monkeypatch,artifact):
    from tests.test_stage3_ml_api import client_for,inference,payload
    client=client_for(monkeypatch,inference().InferenceService(*artifact))
    r=client.get('/valuation/ml/v1/status')
    assert r.status_code==200 and r.json()['model_version']=='test-native-v1'
    assert r.json()['scope']['whole_dwelling_value_supported'] is False
    assert r.json()['scope']['unobserved_cancellation_risk']=='not_eliminated'
    estimate=client.post('/valuation/ml/v1/estimate',json={**payload(),'requested_value_basis':'reported_transfer'})
    assert estimate.status_code==200 and estimate.json()['model_version']=='test-native-v1'
    assert estimate.json()['scope']==r.json()['scope']
    assert estimate.json()['dataset_fingerprint']=='a'*64


@pytest.mark.parametrize('extra',[{'ownership_fraction':0.5},{'rights_status':'PARTIAL_RIGHTS'},
                                  {'parking_count_reported':0},{'parking_price_ntd':0}])
def test_share_or_parking_inputs_are_rejected_without_semantic_imputation(monkeypatch,extra):
    from tests.test_stage3_ml_api import client_for,payload,inference
    client=client_for(monkeypatch,inference().InferenceService(None,None))
    assert client.post('/valuation/ml/v1/estimate',json={**payload(),**extra}).status_code==422
