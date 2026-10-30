"""Bounded shared encoding and small offline baselines; no provider access."""
from __future__ import annotations

from collections import defaultdict
import hashlib
import importlib.metadata
import platform

import numpy as np

from services.taiwan_admin_registry import iter_taiwan_regions
from services.valuation_ml.contract import NUMERIC, CATEGORICAL, FEATURES, TYPES


def library_versions() -> dict:
    return {'python':platform.python_version(),**{name:importlib.metadata.version(name)
            for name in ('numpy','scipy','scikit-learn','lightgbm','pydantic','fastapi')}}


def fixed_encoder() -> dict:
    geographies=sorted({f'{r.county}|{r.district}'.replace('臺','台') for r in iter_taiwan_regions()})
    cities=sorted({g.split('|')[0] for g in geographies})
    return dict(features=list(FEATURES),numeric=list(NUMERIC),categorical=list(CATEGORICAL),
                vocabularies={'city':{x:i for i,x in enumerate(cities)},
                              'geography':{x:i for i,x in enumerate(geographies)},
                              'building_type':{x:i for i,x in enumerate(TYPES)}},
                vocabulary_source='pre-existing administrative registry and declared building-type allowlist; no target fit')


def encode(values: dict, state: dict) -> np.ndarray:
    numeric=[np.nan if values[k] is None else values[k] for k in NUMERIC]
    categories=[state['vocabularies'][k].get(values[k],-1) for k in CATEGORICAL]
    return np.array(numeric+categories,dtype=np.float32)


def metrics(actual, predicted) -> dict:
    actual=np.asarray(actual,dtype=np.float64);predicted=np.asarray(predicted,dtype=np.float64)
    if not len(actual):
        return {'rows':0}
    if not np.isfinite(actual).all() or not np.isfinite(predicted).all() or np.min(actual)<=0 or np.min(predicted)<=0:
        raise ValueError('invalid_metric_values')
    error=np.abs(actual-predicted);ape=error/actual*100
    return dict(rows=len(actual),mae_ntd_ping=float(np.mean(error)),
                rmse_ntd_ping=float(np.sqrt(np.mean(np.square(error)))),
                median_absolute_error_ntd_ping=float(np.median(error)),
                mape_percent=float(np.mean(ape)),median_absolute_percentage_error=float(np.median(ape)),
                wape_percent=float(error.sum()/actual.sum()*100),
                smape_percent=float(np.mean(2*error/(actual+predicted))*100),
                signed_bias_ntd_ping=float(np.mean(predicted-actual)),
                absolute_error_quantiles_ntd_ping={f'p{int(q*100)}':float(np.quantile(error,q))
                    for q in (.5,.75,.9,.95,.99,1)},
                absolute_percentage_error_quantiles={f'p{int(q*100)}':float(np.quantile(ape,q))
                    for q in (.5,.75,.9,.95,.99)})


class MarketMedian:
    """Last 12 fitting months district/type median; global fallback. No future lookup."""
    def __init__(self,minimum=50):
        self.minimum=minimum

    def fit(self,x,y):
        recent=x[:,0]>=np.max(x[:,0])-11
        self.global_median=float(np.median(y[recent]))
        grouped=defaultdict(list)
        for key,value in zip(x[recent,7:9].astype(int),y[recent]):
            grouped[tuple(key)].append(float(value))
        self.groups={key:float(np.median(values)) for key,values in grouped.items() if len(values)>=self.minimum}
        return self

    def predict(self,x):
        return np.array([self.groups.get(tuple(key),self.global_median) for key in x[:,7:9].astype(int)])


def linear_baseline():
    from sklearn.compose import ColumnTransformer
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import OneHotEncoder, StandardScaler
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import Ridge
    preprocessing=ColumnTransformer([
        ('numeric',make_pipeline(SimpleImputer(strategy='median',add_indicator=True),StandardScaler()),list(range(6))),
        ('categorical',OneHotEncoder(handle_unknown='ignore',sparse_output=True),[6,7,8])],sparse_threshold=1)
    return make_pipeline(preprocessing,Ridge(alpha=100,solver='lsqr',tol=1e-4))


def entity_overlap(groups, fit_indices, evaluation_indices) -> dict:
    road=groups[evaluation_indices,1]
    unknown=(road==b'') if groups.dtype.kind=='S' else (road=='')
    return {'seen_address':np.isin(groups[evaluation_indices,0],groups[fit_indices,0]),
            'seen_road':np.isin(road,groups[fit_indices,1]) & ~unknown,'unknown_road':unknown}


def resource_guard(folder):
    import shutil
    from pathlib import Path
    mem={line.split(':')[0]:int(line.split()[1])*1024 for line in Path('/proc/meminfo').read_text().splitlines()
         if line.startswith(('MemAvailable:','MemTotal:'))}
    if mem['MemAvailable'] < 2*1024**3:
        raise RuntimeError('resource_guard_available_memory_below_2GiB')
    if shutil.disk_usage(folder).free < 8*1024**3:
        raise RuntimeError('resource_guard_free_disk_below_8GiB')
    return dict(available_memory_bytes=mem['MemAvailable'],free_disk_bytes=shutil.disk_usage(folder).free)
