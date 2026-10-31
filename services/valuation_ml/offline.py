"""Checkpointed streaming preparation, rational model comparison and final scoring."""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import gzip
import hashlib
import json
import os
from pathlib import Path
import resource
import time
import uuid

import numpy as np

from services.valuation_ml.admission import (SPLITS, cohort_reason, continuous_window, gate_decision, split_for)
from services.valuation_ml.artifact import digest, export_artifact, write_json
from services.valuation_ml.contract import FEATURES, feature_contract, feature_values, subject_from_record
from services.valuation_ml.training import (MarketMedian, encode, entity_overlap, fixed_encoder,
                                           library_versions, linear_baseline, metrics, resource_guard)


def _code_hashes():
    return {p.name:digest(p) for p in sorted(Path(__file__).parent.glob('*.py'))}


def _identity(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,allow_nan=False).encode()).hexdigest()


def preparation_identity(fingerprint):
    return _identity(dict(dataset=fingerprint,features=feature_contract(),splits=SPLITS,code=_code_hashes()))


def save_checkpoint(path, booster, binding, record):
    """Publish native bytes first, then an atomic completion certificate.

    A crash between the two replacements yields a missing or mismatched
    certificate; neither state is a loadable checkpoint.
    """
    path=Path(path);temporary=path.with_suffix('.txt.tmp')
    booster.save_model(str(temporary))
    with temporary.open('rb') as f:os.fsync(f.fileno())
    os.replace(temporary,path)
    certificate=path.with_suffix('.json');temporary=certificate.with_suffix('.json.tmp')
    result={**record,'binding':binding,'model_sha256':digest(path)}
    write_json(temporary,result)
    with temporary.open('rb') as f:os.fsync(f.fileno())
    os.replace(temporary,certificate)
    return result


def load_checkpoint(path,binding):
    path=Path(path);certificate=path.with_suffix('.json')
    if not path.is_file() or not certificate.is_file() or certificate.stat().st_size>65536:
        raise ValueError('checkpoint_not_committed')
    record=json.loads(certificate.read_text())
    if record.get('binding')!=binding:
        raise ValueError('checkpoint_binding_mismatch')
    if path.is_symlink() or path.stat().st_size>32*1024**2 or digest(path)!=record.get('model_sha256'):
        raise ValueError('checkpoint_checksum_mismatch')
    import lightgbm
    return lightgbm.Booster(model_file=str(path)),record


def reusable_checkpoint(path,binding):
    """Uncommitted/stale work is preserved for inspection and refitted safely."""
    path=Path(path);certificate=path.with_suffix('.json')
    if not path.exists() and not certificate.exists():
        return None
    try:
        return load_checkpoint(path,binding)
    except (ValueError,OSError):
        rejected=path.parent/'rejected-checkpoints';rejected.mkdir(exist_ok=True,mode=0o700)
        suffix=uuid.uuid4().hex
        for item in (path,certificate):
            if item.exists():os.replace(item,rejected/f'{item.name}.{suffix}')
        return None


def prepare(dataset: Path, work: Path, verification: dict, progress=print) -> dict:
    """The full verifier is run separately and must bind exact bytes and row count."""
    summary=json.loads((dataset/'summary.json').read_text())
    if (verification.get('status')!='PASS' or verification.get('dataset_fingerprint')!=summary['dataset_fingerprint']
            or verification.get('clean_transactions')!=summary['counts']['clean_transactions']
            or verification.get('logical_dataset_sha256')!=summary['logical_dataset_sha256']):
        raise ValueError('independent_verification_required')
    complete=json.loads((dataset/'COMPLETE.json').read_text())
    if digest(dataset/'summary.json')!=complete['summary_sha256']:
        raise ValueError('dataset_summary_changed')
    for name in ('schema.json','provenance-manifest.json','transactions.jsonl.gz'):
        if digest(dataset/name)!=summary['artifact_hashes'][name]:
            raise ValueError('dataset_changed_after_verification')
    manifest=json.loads((dataset/'provenance-manifest.json').read_text())
    window=continuous_window(manifest)
    work.mkdir(parents=True,exist_ok=True,mode=0o700)
    resource_guard(work)
    cache_identity=preparation_identity(summary['dataset_fingerprint'])
    ready=work/'prepared.json'
    if ready.exists():
        cached=json.loads(ready.read_text())
        if cached['cache_identity']!=cache_identity:
            raise ValueError('checkpoint_contract_changed_use_new_work_directory')
        if any(digest(work/name)!=h for name,h in cached['array_hashes'].items()):
            raise ValueError('checkpoint_checksum_mismatch')
        return cached
    maximum=summary['counts']['clean_transactions']
    x=np.lib.format.open_memmap(work/'x.npy',mode='w+',dtype=np.float32,shape=(maximum,9))
    y=np.lib.format.open_memmap(work/'y.npy',mode='w+',dtype=np.float64,shape=(maximum,))
    split=np.lib.format.open_memmap(work/'split.npy',mode='w+',dtype=np.uint8,shape=(maximum,))
    groups=np.lib.format.open_memmap(work/'groups.npy',mode='w+',dtype='S64',shape=(maximum,2))
    state=fixed_encoder();count=0;scanned=0;excluded=Counter();monthly=Counter();split_counts=Counter()
    split_dates={s:[None,None] for s in SPLITS};hashes={s:hashlib.sha256() for s in SPLITS}
    split_codes={'train':0,'validation':1,'holdout':2};missing=Counter();actual_support=Counter()
    with gzip.open(dataset/'transactions.jsonl.gz','rt',encoding='utf-8') as f:
        for line in f:
            scanned+=1;row=json.loads(line)
            reason=cohort_reason(row)
            if reason:
                excluded[reason]+=1;continue
            part=split_for(row)
            if part is None:
                excluded['source_release_later_than_split_freeze']+=1;continue
            values=feature_values(subject_from_record(row));x[count]=encode(values,state)
            y[count]=float(row['gross_unit_price_ntd_ping']);split[count]=split_codes[part]
            groups[count,0]=row['address_sha256'].encode()
            # All address/road identity is used for diagnostics only, never as a feature.
            road=f"{row['city']}|{row['district']}|{row['road']}"
            groups[count,1]=(hashlib.sha256(road.encode()).hexdigest() if row['road'] else '').encode()
            split_counts[part]+=1;monthly[row['transaction_period']]+=1
            actual_support[(part,values['geography'],row['building_type'])]+=1
            dates=split_dates[part];day=row['transaction_date']
            dates[0]=min(dates[0] or day,day);dates[1]=max(dates[1] or day,day)
            hashes[part].update((row['canonical_id']+'\n').encode())
            for key in ('floor','total_floor','age_years'):
                missing[key]+=values[key] is None
            count+=1
            if count%50000==0:
                resource_guard(work);progress(json.dumps({'phase':'prepare','scanned':scanned,'admitted':count}),flush=True)
    for array in (x,y,split,groups):
        array.flush()
    if scanned!=maximum or sum(split_counts.values())!=count:
        raise ValueError('preparation_row_conservation')
    if not all(split_counts[s]>=1000 for s in SPLITS):
        raise ValueError('insufficient_temporal_split_support')
    admission=dict(status='PASS',version='stage3-dataset-admission-v1',dataset_fingerprint=summary['dataset_fingerprint'],
        independent_verification=verification,canonical_clean_rows=maximum,admitted_rows=count,
        excluded_from_v1=dict(excluded),admitted_window=window,split_definition=SPLITS,
        split_counts=dict(split_counts),split_dates=split_dates,split_identity_sha256={s:h.hexdigest() for s,h in hashes.items()},
        monthly_rows=dict(sorted(monthly.items())),missing_feature_rows=dict(missing),
        known_related_party={'legacy_serving_row':38652,'official_serial':'RPWNMLNKNHLGFBF78EA','admitted_rows':0},
        training_authorization=gate_decision(verified=True),
        source_summary_sha256=complete['summary_sha256'],source_artifact_hashes=summary['artifact_hashes'],
        source_transform_sha256=manifest['transform_code_sha256'],cache_identity=cache_identity,
        array_hashes={name:digest(work/name) for name in ('x.npy','y.npy','split.npy','groups.npy')})
    write_json(ready,admission)
    return admission


def _tree(parameters):
    from lightgbm import LGBMRegressor
    return LGBMRegressor(objective='regression_l1',learning_rate=.06,n_estimators=500,max_bin=127,
        min_child_samples=100,n_jobs=2,random_state=20261029,verbosity=-1,deterministic=True,
        force_col_wise=True,**parameters)


def _predict(booster,x):
    chunks=[]
    for start in range(0,len(x),20000):
        chunks.append(np.exp(booster.predict(x[start:start+20000],num_threads=2)))
    return np.concatenate(chunks)


def _support(x,encoder):
    groups=Counter((int(r[7]),int(r[8])) for r in x)
    recent=Counter((int(r[7]),int(r[8])) for r in x[x[:,0]>=np.max(x[:,0])-35])
    return dict(minimum_fit_rows=50,low_support_below=200,minimum_recent_rows=20,
                cells={f'{g}|{t}':{'fit_rows':n,'recent_36_month_rows':recent[(g,t)]} for (g,t),n in groups.items()},
                numeric_bounds={name:{'min':float(np.nanmin(x[:,i])),'p01':float(np.nanquantile(x[:,i],.01)),
                                     'p99':float(np.nanquantile(x[:,i],.99)),'max':float(np.nanmax(x[:,i]))}
                                for i,name in enumerate(FEATURES[:6])})


def _slice_table(actual,predicted,labels,minimum=50):
    table={}
    for label in np.unique(labels):
        mask=labels==label
        if mask.sum()>=minimum:
            table[str(label)]=metrics(actual[mask],predicted[mask])
    return table


def evaluate(x,y,predicted,baseline,groups,fit_idx,test_idx,encoder,support):
    overlap=entity_overlap(groups,fit_idx,test_idx)
    inverses={k:{v:label for label,v in vocab.items()} for k,vocab in encoder['vocabularies'].items()}
    slices={key:_slice_table(y,predicted,np.array([inverses[key][int(code)] for code in x[:,column]]))
            for key,column in [('city',6),('geography',7),('building_type',8)]}
    slices['recency_quarter']=_slice_table(y,predicted,((x[:,0]//3).astype(int)))
    # Absolute fixed bands, independent of holdout target quantiles.
    slices['price_band_ntd_ping']=_slice_table(y,predicted,np.digitize(y,[100000,200000,400000,800000]))
    for entity in ('seen_address','seen_road'):
        seen=overlap[entity]
        known=~overlap['unknown_road'] if entity=='seen_road' else np.ones(len(y),dtype=bool)
        slices[entity]={'seen':metrics(y[seen],predicted[seen]),
                        'unseen':metrics(y[~seen & known],predicted[~seen & known])}
    slices['unknown_road']=metrics(y[overlap['unknown_road']],predicted[overlap['unknown_road']])
    counts=np.array([support['cells'].get(f'{int(r[7])}|{int(r[8])}',{}).get('fit_rows',0) for r in x])
    slices['fit_cell_density']=_slice_table(y,predicted,np.digitize(counts,[50,200,1000]))
    area=(x[:,1]<support['numeric_bounds']['log_area_ping']['p01'])|(x[:,1]>support['numeric_bounds']['log_area_ping']['p99'])
    slices['area_outlier']={'outside_fit_1_99_percent':metrics(y[area],predicted[area]),
                            'inside':metrics(y[~area],predicted[~area])}
    trim=y<=np.quantile(y,.99)
    report=dict(overall=metrics(y,predicted),baseline=metrics(y,baseline),slices=slices,
        entity_overlap={key:{'seen':int(mask.sum()),'unseen':int((~mask &
            (~overlap['unknown_road'] if key=='seen_road' else True)).sum())}
            for key,mask in overlap.items() if key!='unknown_road'},
        unknown_road_rows=int(overlap['unknown_road'].sum()),
        top_one_percent_target_sensitivity={'full':metrics(y,predicted),'excluding_top_percent_for_diagnostic_only':metrics(y[trim],predicted[trim])},
        price_band_edges_ntd_ping=[100000,200000,400000,800000],
        building_community_identity='Unavailable. Full normalized-address hash proxy and road groups are diagnostic only; '
            'different units in the same building can still evade this proxy. No complete building-disjoint claim.',
        holdout_reused_for_selection=False)
    return report


def train(work: Path, output_parent: Path, progress=print):
    started=time.monotonic();admission=json.loads((work/'prepared.json').read_text())
    if admission['status']!='PASS' or not admission['training_authorization']['training_authorized']:
        raise ValueError('training_not_admitted')
    if admission.get('cache_identity')!=preparation_identity(admission['dataset_fingerprint']):
        raise ValueError('preparation_checkpoint_identity_mismatch')
    code_hashes=_code_hashes();versions=library_versions()
    fitting_identity=_identity(dict(preparation=admission['cache_identity'],arrays=admission['array_hashes'],
        split_counts=admission['split_counts'],code=code_hashes,libraries=versions,
        schedule={'seed':20261029,'objective':'regression_l1','log_target':True,
                  'learning_rate':.06,'n_estimators':500,'max_bin':127,'min_child_samples':100,
                  'threads':2,'early_stopping_rounds':35}))
    if any(digest(work/name)!=h for name,h in admission['array_hashes'].items()):
        raise ValueError('training_checkpoint_checksum')
    output_parent.mkdir(parents=True,exist_ok=True,mode=0o750);resource_guard(output_parent)
    n=admission['admitted_rows']
    x=np.load(work/'x.npy',mmap_mode='r')[:n];y=np.load(work/'y.npy',mmap_mode='r')[:n]
    split=np.load(work/'split.npy',mmap_mode='r')[:n];groups=np.load(work/'groups.npy',mmap_mode='r')[:n]
    tr=np.flatnonzero(split==0);va=np.flatnonzero(split==1);te=np.flatnonzero(split==2)
    train_x=x[tr];val_x=x[va];train_y=y[tr];val_y=y[va]
    comparison={}
    global_median=float(np.median(train_y))
    comparison['global_median']=metrics(val_y,np.full(len(va),global_median))
    market=MarketMedian().fit(train_x,train_y)
    comparison['recent_district_type_median']=metrics(val_y,market.predict(val_x))
    linear=linear_baseline().fit(train_x,np.log(train_y))
    comparison['ridge_log']=metrics(val_y,np.exp(linear.predict(val_x)))
    progress(json.dumps({'phase':'baselines','validation':comparison}),flush=True)
    from lightgbm import early_stopping
    # Two capacities, same deterministic objective and schedule; no grid search.
    best=None;chosen=None
    for leaves in (31,63):
        resource_guard(output_parent)
        name=f'lightgbm_log_l1_leaves{leaves}'
        checkpoint=work/f'{name}.txt'
        binding=_identity(dict(fitting=fitting_identity,phase='candidate',num_leaves=leaves))
        reused=reusable_checkpoint(checkpoint,binding)
        if reused is not None:
            booster,result=reused
        else:
            model=_tree({'num_leaves':leaves})
            model.fit(train_x,np.log(train_y),feature_name=list(FEATURES),categorical_feature=[6,7,8],
                      eval_set=[(val_x,np.log(val_y))],eval_metric='l1',callbacks=[early_stopping(35,verbose=False)])
            booster=model.booster_;prediction=_predict(booster,val_x)
            result={'metrics':metrics(val_y,prediction),'iterations':booster.current_iteration(),
                    'num_leaves':leaves}
            result=save_checkpoint(checkpoint,booster,binding,result)
        comparison[name]=result['metrics']
        if best is None or result['metrics']['mae_ntd_ping']<best['metrics']['mae_ntd_ping']:
            best=result;chosen=name
        progress(json.dumps({'phase':'candidate','model':name,**result}),flush=True)
    # Serving release requires the efficient tree to improve on both defensible baselines.
    if best['metrics']['mae_ntd_ping']>=min(comparison[k]['mae_ntd_ping'] for k in
            ('recent_district_type_median','ridge_log')):
        write_json(work/'comparison-failed.json',comparison)
        raise ValueError('tree_does_not_beat_validation_baselines')
    write_json(work/'selection.json',dict(chosen=chosen,result=best,comparison=comparison,criterion='validation MAE NTD/ping'))
    del train_x,val_x,linear
    fit_idx=np.concatenate([tr,va]);fit_x=x[fit_idx];fit_y=y[fit_idx]
    final_path=work/'final-model.txt'
    final_binding=_identity(dict(fitting=fitting_identity,phase='train_plus_validation',selected=chosen,
                                 iterations=best['iterations'],num_leaves=best['num_leaves']))
    reused_final=reusable_checkpoint(final_path,final_binding)
    if reused_final is not None:
        final_booster,_=reused_final
    else:
        final=_tree({'num_leaves':best['num_leaves']});final.set_params(n_estimators=best['iterations'])
        final.fit(fit_x,np.log(fit_y),feature_name=list(FEATURES),categorical_feature=[6,7,8])
        save_checkpoint(final_path,final.booster_,final_binding,{'selected':chosen,'iterations':best['iterations']})
        final_booster,_=load_checkpoint(final_path,final_binding)
    encoder=fixed_encoder();support=_support(fit_x,encoder)
    test_x=x[te];test_y=y[te]
    prediction=_predict(final_booster,test_x)
    final_baseline=MarketMedian().fit(fit_x,fit_y)
    evaluation=evaluate(test_x,test_y,prediction,final_baseline.predict(test_x),groups,fit_idx,te,encoder,support)
    # Describe drift using fitting-side bins only.
    drift={}
    for i in (0,1,2,3,4):
        a=fit_x[:,i];b=test_x[:,i];a=a[np.isfinite(a)];b=b[np.isfinite(b)]
        edges=np.unique(np.quantile(a,np.linspace(0,1,11)));edges[0]=-np.inf;edges[-1]=np.inf
        p=np.maximum(np.histogram(a,bins=edges)[0]/len(a),1e-6)
        q=np.maximum(np.histogram(b,bins=edges)[0]/max(len(b),1),1e-6)
        drift[FEATURES[i]]=dict(fit_median=float(np.median(a)),holdout_median=float(np.median(b)),
                               population_stability_index=float(np.sum((q-p)*np.log(q/p))))
    evaluation.update(validation_comparison=comparison,selected_model=chosen,selected_iterations=best['iterations'],
        selection_criterion='Lowest validation MAE among two predeclared tree capacities; must beat market median and ridge.',
        fitted_rows=len(fit_idx),holdout_rows=len(te),drift=drift,
        release_decision='bounded_observational_capability_only')
    model_hash=digest(final_path)
    version=f'plvr-gross-v1-{admission["dataset_fingerprint"][:10]}-{model_hash[:12]}-{fitting_identity[:8]}'
    metadata=dict(model_version=version,dataset_fingerprint=admission['dataset_fingerprint'],
        admitted_window=admission['admitted_window'],admitted_rows=n,
        split_definition=admission['split_definition'],split_counts=admission['split_counts'],
        fitted_through=admission['split_dates']['validation'][1],evaluation=evaluation,
        generated_at=datetime.now(timezone.utc).isoformat(),libraries=versions,support=support,
        training_authorization=admission['training_authorization'],
        provenance={'source_artifact_hashes':admission['source_artifact_hashes'],
                    'source_transform_sha256':admission['source_transform_sha256'],
                    'split_identity_sha256':admission['split_identity_sha256'],
                    'stage3_code_sha256':code_hashes,'fitting_checkpoint_identity':fitting_identity},
        prediction_date_min='2025-07-01',prediction_date_max='2026-12-27',
        limitations=['Gross reported transfer per registered area: parking and dwelling rights unresolved.',
            'Retrospective archive snapshot, not verified as-of-publication backtest; cancellation completeness unproven.',
            'Reported residential use and three multifamily types only; area 5–200 ping; no coordinates or road features.',
            'No calibrated intervals or confidence probability. Support counts describe fitting data, not certainty.',
            'Tree time response is constant beyond fitting time; market drift and property differences remain.',
            'No complete building/community identity; address and road disjoint diagnostics are proxies.',
            'Data reflect only disclosed, blank-note, unambiguous transfers and source price screens. Selection bias remains.'])
    artifact=output_parent/version
    if artifact.exists():
        from services.valuation_ml.artifact import load_artifact
        existing=load_artifact(artifact)
        if (existing['metadata']['provenance'].get('fitting_checkpoint_identity')!=fitting_identity
                or existing['manifest']['files']['model.txt']!=model_hash):
            raise ValueError('immutable_model_version_conflict')
        manifest=existing['manifest']
    else:
        manifest=export_artifact(artifact,final_booster,encoder,metadata)
    result=dict(status='PASS',artifact_path=str(artifact),model_version=version,
                manifest_sha256=digest(artifact/'manifest.json'),model_sha256=manifest['files']['model.txt'],
                evaluation=evaluation,final_checkpoint_reused=reused_final is not None,
                fitting_checkpoint_identity=fitting_identity,
                resource_usage={'elapsed_seconds':time.monotonic()-started,
                    'peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
                    'max_training_threads':2,'inference_threads':1,'nice':__import__('os').getpriority(0,0),
                    **resource_guard(output_parent)})
    write_json(work/'result.json',result)
    return result
