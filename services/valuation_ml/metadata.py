"""Semantic artifact admission, in addition to byte integrity."""
from datetime import date, datetime
import math
import re

from services.valuation_ml.admission import SPLITS, WINDOW, gate_decision


def _require(condition):
    if not condition:
        raise ValueError('artifact_metadata_contract')


def _hash(value):
    return isinstance(value,str) and re.fullmatch('[0-9a-f]{64}',value) is not None


def _finite(value):
    if isinstance(value,float):
        _require(math.isfinite(value))
    elif isinstance(value,dict):
        for item in value.values():_finite(item)
    elif isinstance(value,list):
        for item in value:_finite(item)


def validate_metadata(meta: dict):
    """All fields consumed by serving and their cross-contract invariants."""
    try:
        _finite(meta)
        _require(meta['training_authorization']==gate_decision(verified=True))
        _require(_hash(meta['dataset_fingerprint']))
        _require(isinstance(meta['model_version'],str) and
                 re.fullmatch('[A-Za-z0-9._-]{1,128}',meta['model_version']) is not None)
        generated=datetime.fromisoformat(meta['generated_at'])
        _require(generated.tzinfo is not None)
        fitted=date.fromisoformat(meta['fitted_through'])
        minimum=date.fromisoformat(meta['prediction_date_min']);maximum=date.fromisoformat(meta['prediction_date_max'])
        _require(fitted < minimum <= maximum)
        _require(meta['split_definition']==SPLITS)
        counts=meta['split_counts']
        _require(set(counts)==set(SPLITS) and all(type(n) is int and n>0 for n in counts.values()))
        _require(type(meta['admitted_rows']) is int and sum(counts.values())==meta['admitted_rows'])
        _require(SPLITS['validation']['start']<=meta['fitted_through']<=SPLITS['validation']['end'])
        window=meta['admitted_window']
        _require((window['start'],window['end'])==WINDOW and window['release_count']==40
                 and window['historical_publication_proven'] is False
                 and window['population_completeness_proven'] is False)
        provenance=meta['provenance']
        _require(set(provenance)>={'source_artifact_hashes','source_transform_sha256',
                                  'stage3_code_sha256','split_identity_sha256'})
        _require(set(provenance['source_artifact_hashes'])==
                 {'coverage.json','lineage.sqlite','provenance-manifest.json','schema.json','transactions.jsonl.gz'})
        _require(set(provenance['split_identity_sha256'])==set(SPLITS))
        for name in ('source_artifact_hashes','source_transform_sha256','stage3_code_sha256','split_identity_sha256'):
            _require(isinstance(provenance[name],dict) and bool(provenance[name]) and
                     all(_hash(h) for h in provenance[name].values()))
        _require(isinstance(meta['limitations'],list) and 3<=len(meta['limitations'])<=30
                 and all(isinstance(s,str) and 1<=len(s)<=1024 for s in meta['limitations']))
        _require(isinstance(meta['evaluation']['overall'],dict)
                 and isinstance(meta['evaluation']['slices']['geography'],dict))
        _require(set(meta['libraries'])>={'python','numpy','scipy','scikit-learn','lightgbm','fastapi','pydantic'})
        support=meta['support']
        _require(support['minimum_fit_rows']==50 and support['minimum_recent_rows']==20
                 and support['low_support_below']==200)
        _require(isinstance(support['cells'],dict) and len(support['cells'])<=1200)
        fit_count=counts['train']+counts['validation']
        for key,cell in support['cells'].items():
            _require(re.fullmatch(r'[0-9]{1,4}\|[0-9]{1,2}',key) is not None)
            _require(type(cell['fit_rows']) is int and type(cell['recent_36_month_rows']) is int
                     and 0<=cell['recent_36_month_rows']<=cell['fit_rows']<=fit_count)
        _require(isinstance(support['numeric_bounds'],dict))
        from services.valuation_ml.contract import NUMERIC
        _require(set(support['numeric_bounds'])<=set(NUMERIC))
        for bounds in support['numeric_bounds'].values():
            _require(bounds['min']<=bounds['p01']<=bounds['p99']<=bounds['max'])
    except (KeyError,TypeError,AttributeError,OverflowError) as exc:
        raise ValueError('artifact_metadata_contract') from exc
