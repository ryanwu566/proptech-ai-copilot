"""Small real computations pin leakage, metrics and native artifact integrity."""
import importlib
import importlib.util
import json

import numpy as np
import pytest


def engine():
    assert importlib.util.find_spec('services.valuation_ml.training'), 'bounded training implementation required'
    return importlib.import_module('services.valuation_ml.training')


def test_error_metrics_have_explicit_units_and_hand_computed_values():
    result=engine().metrics(np.array([100.,200.,400.]),np.array([110.,180.,440.]))
    assert result['mae_ntd_ping'] == pytest.approx(70/3)
    assert result['rmse_ntd_ping'] == pytest.approx(np.sqrt(700))
    assert result['median_absolute_error_ntd_ping'] == 20
    assert result['median_absolute_percentage_error'] == pytest.approx(10)
    assert result['wape_percent'] == pytest.approx(10)
    assert result['absolute_error_quantiles_ntd_ping']['p50'] == 20


def test_baseline_uses_only_fitting_targets_and_recent_fitting_months():
    m=engine()
    # columns: six numeric, then fixed city/geography/type codes
    x=np.array([[0,3,3,5,10,.6,0,0,0],[60,3,3,5,10,.6,0,0,0],
                [61,3,3,5,10,.6,0,0,0],[62,3,3,5,10,.6,0,0,0]],dtype=np.float32)
    b=m.MarketMedian(minimum=2).fit(x,np.array([10.,100.,200.,300.]))
    pred=b.predict(x[-1:])
    assert pred[0] == 200
    # A request in an unseen geography falls back to the recent fitting median.
    unseen=x[-1:].copy();unseen[0,7]=999
    assert b.predict(unseen)[0] == 200


def test_fixed_administrative_encoder_has_feature_parity_and_no_target_fit():
    from services.valuation_ml.contract import Subject, feature_values
    m=engine()
    enc=m.fixed_encoder()
    values=feature_values(Subject(transaction_date='2024-01-01',city='新北市',district='新莊區',
                                 building_type='公寓(5樓含以下無電梯)',main_use='住家用',area_ping=30.))
    a=m.encode(values,enc)
    assert a.shape == (9,)
    assert a[0] == 84
    assert np.isnan(a[2])
    assert a[7] >= 0
    assert np.array_equal(m.encode(values,json.loads(json.dumps(enc))),a,equal_nan=True)


def test_small_tree_artifact_roundtrip_and_tamper_fail_closed(tmp_path):
    m=engine()
    from lightgbm import LGBMRegressor
    from services.valuation_ml.artifact import export_artifact, load_artifact
    x=np.array([[i,3,3,5,10,.6,0,0,0] for i in range(80)],dtype=np.float32)
    model=LGBMRegressor(n_estimators=3,num_leaves=3,min_child_samples=5,n_jobs=1,verbosity=-1,
                        deterministic=True,force_col_wise=True).fit(x,np.log(np.arange(80)+100),
                            feature_name=['month_index','log_area_ping','floor','total_floor','age_years',
                                          'floor_ratio','city','geography','building_type'])
    from tests.stage3_ml_fixtures import metadata
    meta=metadata()
    export_artifact(tmp_path/'model',model.booster_,m.fixed_encoder(),meta)
    loaded=load_artifact(tmp_path/'model')
    assert loaded['metadata']['model_version'] == 'test-v1'
    assert np.allclose(loaded['model'].predict(x,num_threads=1),model.booster_.predict(x,num_threads=1))
    path=tmp_path/'model'/'model.txt';path.chmod(0o640);path.write_bytes(path.read_bytes()+b'\n')
    with pytest.raises(ValueError,match='checksum'):
        load_artifact(tmp_path/'model')


def test_artifact_rejects_feature_contract_and_oversized_payload_before_model_load(tmp_path):
    m=engine()
    from services.valuation_ml.artifact import load_artifact
    (tmp_path/'manifest.json').write_text(json.dumps({'files':{'../outside':'a'*64}}))
    with pytest.raises(ValueError):
        load_artifact(tmp_path)


def test_group_evaluation_distinguishes_seen_address_and_road():
    m=engine()
    groups=np.array([[1,10],[2,20],[1,10],[3,10],[4,40]],dtype=np.uint64)
    result=m.entity_overlap(groups,np.array([0,1]),np.array([2,3,4]))
    assert result['seen_address'].tolist() == [True,False,False]
    assert result['seen_road'].tolist() == [True,True,False]


def test_missing_roads_do_not_claim_seen_or_disjoint_entity_evidence():
    result=engine().entity_overlap(np.array([['a',''],['b',''],['c','road']],dtype='S64'),
                                   np.array([0]),np.array([1,2]))
    assert result['seen_road'].tolist() == [False,False]
    assert result['unknown_road'].tolist() == [True,False]


def test_preparation_cannot_start_without_independent_dataset_verification(tmp_path):
    engine()
    from services.valuation_ml.offline import prepare
    (tmp_path/'summary.json').write_text(json.dumps({'dataset_fingerprint':'a'*64,
                                                   'counts':{'clean_transactions':10}}))
    with pytest.raises(ValueError,match='independent_verification_required'):
        prepare(tmp_path,tmp_path/'work',{'status':'BLOCKED'})
    assert not (tmp_path/'work').exists()


def test_training_rejects_unadmitted_checkpoint_before_fitting(tmp_path):
    engine()
    from services.valuation_ml.offline import train
    (tmp_path/'prepared.json').write_text(json.dumps({'status':'BLOCKED'}))
    with pytest.raises(ValueError,match='training_not_admitted'):
        train(tmp_path,tmp_path/'models')
    assert not (tmp_path/'models').exists()


def test_training_rejects_changed_preparation_code_before_reading_arrays(tmp_path):
    engine()
    from services.valuation_ml.offline import train
    (tmp_path/'prepared.json').write_text(json.dumps({'status':'PASS',
        'training_authorization':{'training_authorized':True},'cache_identity':'old-code',
        'dataset_fingerprint':'a'*64,'array_hashes':{}}))
    with pytest.raises(ValueError,match='preparation_checkpoint_identity'):
        train(tmp_path,tmp_path/'models')


def test_checkpoint_binding_and_checksum_are_checked_before_native_parsing(tmp_path):
    engine()
    from services.valuation_ml.offline import load_checkpoint
    model=tmp_path/'candidate.txt';model.write_text('invalid native text must never be parsed')
    certificate=model.with_suffix('.json')
    certificate.write_text(json.dumps({'binding':'different-data','model_sha256':'0'*64}))
    with pytest.raises(ValueError,match='checkpoint_binding'):
        load_checkpoint(model,'expected-data')
    certificate.write_text(json.dumps({'binding':'expected-data','model_sha256':'0'*64}))
    with pytest.raises(ValueError,match='checkpoint_checksum'):
        load_checkpoint(model,'expected-data')
    certificate.unlink()
    with pytest.raises(ValueError,match='checkpoint_not_committed'):
        load_checkpoint(model,'expected-data')


def test_native_checkpoint_commits_and_reloads_atomically(tmp_path):
    engine()
    from lightgbm import LGBMRegressor
    from services.valuation_ml.offline import save_checkpoint,load_checkpoint
    x=np.arange(80).reshape(-1,1)
    model=LGBMRegressor(n_estimators=3,min_child_samples=5,n_jobs=1,verbosity=-1).fit(x,x[:,0])
    p=tmp_path/'final-model.txt'
    save_checkpoint(p,model.booster_,'bound-data-config-and-code',{'iterations':3})
    loaded,record=load_checkpoint(p,'bound-data-config-and-code')
    assert record['iterations']==3
    assert np.allclose(loaded.predict(x,num_threads=1),model.booster_.predict(x,num_threads=1))
    assert not list(tmp_path.glob('*.tmp'))


def test_invalid_checkpoint_is_quarantined_for_safe_refitting(tmp_path):
    from services.valuation_ml.offline import reusable_checkpoint
    p=tmp_path/'final-model.txt';p.write_text('partial native save')
    assert reusable_checkpoint(p,'bound-fit') is None
    assert not p.exists()
    assert len(list((tmp_path/'rejected-checkpoints').iterdir()))==1


def test_failed_artifact_export_does_not_publish_a_partial_version(tmp_path):
    from lightgbm import LGBMRegressor
    from services.valuation_ml.artifact import export_artifact
    from services.valuation_ml.contract import FEATURES
    from tests.stage3_ml_fixtures import metadata
    m=engine();x=np.tile(np.arange(9),(80,1))
    model=LGBMRegressor(n_estimators=1,n_jobs=1,verbosity=-1).fit(x,np.zeros(80),feature_name=list(FEATURES))
    bad=metadata();bad['training_authorization']['authorized_target']='wrong'
    folder=tmp_path/'published'
    with pytest.raises(ValueError):export_artifact(folder,model.booster_,m.fixed_encoder(),bad)
    assert not folder.exists()
    export_artifact(folder,model.booster_,m.fixed_encoder(),metadata())
    assert (folder/'manifest.json').is_file()
