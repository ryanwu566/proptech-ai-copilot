"""One-slot lazy, local, deterministic inference. No providers or request training."""
from __future__ import annotations

from datetime import date
from functools import lru_cache
import math
import os
from pathlib import Path
import re
import threading

from services.valuation_ml.contract import Subject, TARGET, VERSION, feature_values


def unavailable(reason, status='unavailable'):
    return dict(status=status,reason_code=reason,estimate_unit_price_ntd_ping=None,
                estimate_total_price_ntd=None,is_actionable=False)


class InferenceService:
    def __init__(self, folder: Path | None, manifest_sha256: str | None):
        self.folder=Path(folder) if folder else None
        self.pin=manifest_sha256
        self._slot=threading.BoundedSemaphore(1)
        self._artifact=None
        self._failure=None

    def _load(self):
        if self._failure:
            return self._failure
        if not self.folder or not self.pin:
            return 'model_not_configured'
        if not re.fullmatch('[0-9a-f]{64}',self.pin):
            return 'model_manifest_pin_invalid'
        if self._artifact is None:
            try:
                from services.valuation_ml.artifact import load_artifact
                self._artifact=load_artifact(self.folder,self.pin)
            except Exception:
                # Cache failure until restart; never disclose paths or parser exception text.
                self._failure='model_integrity_or_runtime_error'
                return self._failure
        return None

    def status(self):
        if not self._slot.acquire(blocking=False):
            return unavailable('inference_capacity_reached','busy')
        try:
            failure=self._load()
            if failure:
                return unavailable(failure)
            meta=self._artifact['metadata']
            return dict(status='available',model_version=meta['model_version'],target=TARGET,
                        feature_contract_version=VERSION,dataset_fingerprint=meta['dataset_fingerprint'],
                        fitted_through=meta['fitted_through'],historical_point_in_time_verified=False,
                        prediction_date_min=meta['prediction_date_min'],prediction_date_max=meta['prediction_date_max'],
                        manifest_sha256=self._artifact['manifest_sha256'],is_actionable=False,
                        limitations=meta['limitations'])
        except Exception:
            self._failure='model_integrity_or_runtime_error'
            return unavailable(self._failure)
        finally:
            self._slot.release()

    def estimate(self, subject: Subject):
        if not self._slot.acquire(blocking=False):
            return unavailable('inference_capacity_reached','busy')
        try:
            failure=self._load()
            if failure:
                return unavailable(failure)
            artifact=self._artifact;meta=artifact['metadata']
            day=subject.transaction_date.isoformat()
            if not meta['prediction_date_min']<=day<=min(meta['prediction_date_max'],date.today().isoformat()):
                return unavailable('outside_model_date_support','unsupported')
            from services.valuation_ml.training import encode
            values=feature_values(subject);vector=encode(values,artifact['preprocessing'])
            cell=f'{int(vector[7])}|{int(vector[8])}'
            support=meta['support'];counts=support['cells'].get(cell,{'fit_rows':0,'recent_36_month_rows':0})
            if counts['fit_rows']<support['minimum_fit_rows'] or counts['recent_36_month_rows']<support['minimum_recent_rows']:
                result=unavailable('insufficient_training_support','unsupported')
                result.update(model_version=meta['model_version'],dataset_fingerprint=meta['dataset_fingerprint'],coverage=counts)
                return result
            flags=[]
            if counts['fit_rows']<support['low_support_below']:
                flags.append('low_sample_support')
            if any(v is None for k,v in values.items() if k in ('floor','total_floor','age_years')):
                flags.append('missing_structural_facts')
            if day>meta['fitted_through']:
                flags.append('temporal_extrapolation')
            for i,name in enumerate(artifact['contract']['numeric']):
                bounds=support['numeric_bounds'].get(name)
                if bounds and math.isfinite(float(vector[i])) and not bounds['p01']<=vector[i]<=bounds['p99']:
                    flags.append(f'{name}_outside_fit_1_99_percent')
            geography=meta['evaluation']['slices'].get('geography',{}).get(values['geography'],{})
            if geography.get('mape_percent',0)>35:
                flags.append('weak_geography_holdout_errors')
            predicted=float(artifact['model'].predict(vector.reshape(1,-1),num_threads=1)[0])
            unit=math.exp(predicted)
            if not math.isfinite(unit) or not 1000<=unit<=10000000:
                return unavailable('prediction_outside_safety_bounds','unsupported')
            unit=round(unit,2)
            return dict(status='available',reason_code='observed_gross_transfer_estimate',target=TARGET,
                estimate_unit_price_ntd_ping=unit,estimate_total_price_ntd=round(unit*subject.area_ping,2),
                is_actionable=False,confidence_probability=None,
                coverage={**counts,'flags':flags,'confidence_basis':'fitting sample support only; no probability calibration'},
                model_version=meta['model_version'],feature_contract_version=VERSION,
                dataset_fingerprint=meta['dataset_fingerprint'],model_generated_at=meta['generated_at'],
                model_manifest_sha256=artifact['manifest_sha256'],fitted_through=meta['fitted_through'],
                historical_point_in_time_verified=False,limitations=meta['limitations'])
        except Exception:
            return unavailable('model_inference_error')
        finally:
            self._slot.release()


@lru_cache(maxsize=1)
def get_service():
    return InferenceService(os.environ.get('VALUATION_ML_ARTIFACT_DIR'),os.environ.get('VALUATION_ML_MANIFEST_SHA256'))
