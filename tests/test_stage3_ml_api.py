"""Real FastAPI boundary and a tiny native artifact, no network or serving DB."""
import importlib
import importlib.util
import json
import threading

from fastapi import FastAPI
from fastapi.testclient import TestClient
import numpy as np
import pytest


def inference():
    assert importlib.util.find_spec('services.valuation_ml.inference'), 'ML inference implementation required'
    return importlib.import_module('services.valuation_ml.inference')


def payload(**changes):
    return dict(transaction_date='2026-10-29',city='新北市',district='新莊區',main_use='住家用',
                building_type='公寓(5樓含以下無電梯)',area_ping=30.,floor=3,total_floor=5,
                building_age_years=10.,**changes)


@pytest.fixture
def artifact(tmp_path):
    from lightgbm import LGBMRegressor
    from services.valuation_ml.artifact import export_artifact, digest
    from services.valuation_ml.contract import Subject, feature_values, FEATURES
    from services.valuation_ml.training import encode, fixed_encoder, library_versions
    enc=fixed_encoder();v=encode(feature_values(Subject(**payload())),enc)
    x=np.tile(v,(80,1));x[:,0]=np.arange(80)
    model=LGBMRegressor(n_estimators=3,num_leaves=3,min_child_samples=5,n_jobs=1,verbosity=-1,
                        deterministic=True,force_col_wise=True).fit(x,np.log(np.arange(80)+300000),feature_name=list(FEATURES))
    cell=f'{int(v[7])}|{int(v[8])}'
    from tests.stage3_ml_fixtures import metadata
    meta=metadata('test-native-v1')
    meta['support']['cells']={cell:{'fit_rows':80,'recent_36_month_rows':40}}
    folder=tmp_path/'artifact';export_artifact(folder,model.booster_,enc,meta)
    return folder,digest(folder/'manifest.json')


def client_for(monkeypatch, service):
    m=inference()
    routes=importlib.import_module('backend.api.routes_valuation_ml')
    monkeypatch.setattr(routes,'get_service',lambda:service)
    app=FastAPI();app.include_router(routes.router)
    return TestClient(app)


def test_model_unavailable_returns_explicit_503_without_model_dependencies(monkeypatch):
    m=inference();service=m.InferenceService(None,None)
    client=client_for(monkeypatch,service)
    r=client.post('/valuation/ml/v1/estimate',json=payload())
    assert r.status_code==503
    assert r.json()['status']=='unavailable'
    assert r.json()['estimate_unit_price_ntd_ping'] is None
    assert client.get('/valuation/ml/v1/status').json()['reason_code']=='model_not_configured'


def test_deterministic_native_inference_has_provenance_and_honest_support(monkeypatch,artifact):
    m=inference();client=client_for(monkeypatch,m.InferenceService(*artifact))
    a=client.post('/valuation/ml/v1/estimate',json=payload())
    b=client.post('/valuation/ml/v1/estimate',json=payload())
    assert a.status_code==200 and a.json()==b.json()
    r=a.json()
    assert 290000<r['estimate_unit_price_ntd_ping']<310000
    assert r['estimate_total_price_ntd']==pytest.approx(r['estimate_unit_price_ntd_ping']*30,abs=1)
    assert r['model_version']=='test-native-v1'
    assert r['dataset_fingerprint']=='a'*64
    assert r['coverage']['fit_rows']==80
    assert 'low_sample_support' in r['coverage']['flags']
    assert r['is_actionable'] is False and r['confidence_probability'] is None
    assert r['target']=='reported-gross-transfer-ntd-per-registered-ping-v1'
    assert r['historical_point_in_time_verified'] is False
    assert 'artifact' not in str(r)


@pytest.mark.parametrize('changes', [
    {'area_ping':-1},{'area_ping':'30'},{'floor':90},{'floor':True},
    {'total_floor':2},{'parking_spaces':1},{'district':'錯誤'},
    {'building_type':'工廠'},{'main_use':'商業用'},{'transaction_date':'2027-01-01'},
])
def test_api_invalid_inputs_are_422_before_model_loading(monkeypatch,changes):
    m=inference();client=client_for(monkeypatch,m.InferenceService(None,None))
    p=payload();p.update(changes)
    assert client.post('/valuation/ml/v1/estimate',json=p).status_code==422


def test_unseen_or_sparse_geography_and_date_are_honest_abstentions(monkeypatch,artifact):
    m=inference();client=client_for(monkeypatch,m.InferenceService(*artifact))
    for changes in ({'district':'板橋區'},{'transaction_date':'2024-01-01'}):
        p=payload();p.update(changes)
        r=client.post('/valuation/ml/v1/estimate',json=p)
        assert r.status_code==422 and r.json()['status']=='unsupported'
        assert r.json()['estimate_unit_price_ntd_ping'] is None


def test_wrong_manifest_pin_and_corrupt_model_never_serve(monkeypatch,artifact):
    m=inference();folder,pin=artifact
    client=client_for(monkeypatch,m.InferenceService(folder,'0'*64))
    r=client.post('/valuation/ml/v1/estimate',json=payload())
    assert r.status_code==503 and r.json()['reason_code']=='model_integrity_or_runtime_error'
    assert str(folder) not in r.text


def test_concurrency_is_bounded_without_a_waiting_queue(artifact):
    m=inference();service=m.InferenceService(*artifact)
    from services.valuation_ml.contract import Subject
    assert service._slot.acquire(blocking=False)
    try:
        r=service.estimate(Subject(**payload()))
        assert r['status']=='busy'
    finally:
        service._slot.release()


def test_pure_inference_makes_no_provider_network_calls(monkeypatch,artifact):
    m=inference()
    import httpx
    def forbidden(*args,**kwargs):
        pytest.fail('pure ML inference attempted a network call')
    monkeypatch.setattr(httpx.Client,'send',forbidden)
    monkeypatch.setattr(httpx.AsyncClient,'send',forbidden)
    from services.valuation_ml.contract import Subject
    assert m.InferenceService(*artifact).estimate(Subject(**payload()))['status']=='available'


def test_global_missing_model_does_not_affect_existing_application_health(monkeypatch):
    # Importing the main app must not require loading ML packages or artifacts.
    from backend.api_main import app
    monkeypatch.delenv('VALUATION_ML_ARTIFACT_DIR',raising=False)
    monkeypatch.delenv('VALUATION_ML_MANIFEST_SHA256',raising=False)
    inference().get_service.cache_clear()
    client=TestClient(app)
    assert client.get('/health').status_code==200
    r=client.post('/valuation/ml/v1/estimate',json=payload())
    assert r.status_code==503 and r.json()['status']=='unavailable'


@pytest.mark.parametrize('numeric',['NaN','Infinity','1e309'])
@pytest.mark.parametrize('entrypoint',['router','main','companion'])
def test_nonfinite_json_is_sanitized_422_on_every_entrypoint(monkeypatch,numeric,entrypoint):
    m=inference();service=m.InferenceService(None,None)
    if entrypoint=='router':
        client=client_for(monkeypatch,service)
    else:
        module='backend.api_main' if entrypoint=='main' else 'scripts.ops.serve_valuation_ml'
        client=TestClient(importlib.import_module(module).app,raise_server_exceptions=False)
    body=json.dumps(payload()).replace('30.0',numeric)
    r=client.post('/valuation/ml/v1/estimate',content=body,headers={'content-type':'application/json'})
    assert r.status_code==422
    assert r.headers['cache-control']=='no-store'
    assert all('input' not in error and 'ctx' not in error for error in r.json()['detail'])


def test_invalid_dto_also_has_no_store_header(monkeypatch):
    client=client_for(monkeypatch,inference().InferenceService(None,None))
    p=payload();p['area_ping']='30'
    r=client.post('/valuation/ml/v1/estimate',json=p)
    assert r.status_code==422 and r.headers.get('cache-control')=='no-store'


@pytest.mark.parametrize('corruption',['authorization','missing_date','provenance','support_policy','nonfinite'])
def test_semantically_invalid_metadata_is_rejected_even_with_correct_file_hashes(monkeypatch,artifact,corruption):
    from services.valuation_ml.artifact import digest
    folder,_=artifact
    folder.chmod(0o750)
    p=folder/'metadata.json';p.chmod(0o640);meta=json.loads(p.read_text())
    if corruption=='authorization':meta['training_authorization']['authorized_target']='different-target'
    elif corruption=='missing_date':del meta['prediction_date_min']
    elif corruption=='provenance':meta['provenance']={}
    elif corruption=='support_policy':meta['support']['minimum_fit_rows']=0
    else:meta['evaluation']['overall']['mae_ntd_ping']=float('nan')
    p.write_text(json.dumps(meta))
    manifest_path=folder/'manifest.json';manifest_path.chmod(0o640)
    manifest=json.loads(manifest_path.read_text());manifest['files']['metadata.json']=digest(p)
    manifest_path.write_text(json.dumps(manifest))
    service=inference().InferenceService(folder,digest(manifest_path))
    client=client_for(monkeypatch,service)
    r=client.get('/valuation/ml/v1/status')
    assert r.status_code==503 and r.json()['reason_code']=='model_integrity_or_runtime_error'
