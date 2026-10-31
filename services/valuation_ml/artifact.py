"""Hash-verified, bounded, native model artifacts. Never deserialize pickle."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import platform
import uuid

from services.valuation_ml.contract import feature_contract

FILES = {'model.txt':32*1024**2, 'contract.json':128*1024,
         'preprocessing.json':512*1024, 'metadata.json':16*1024**2}


def digest(path: Path) -> str:
    with path.open('rb') as f:
        return hashlib.file_digest(f,'sha256').hexdigest()


def write_json(path: Path, value):
    temporary=path.with_name(path.name+'.tmp-'+uuid.uuid4().hex)
    with temporary.open('w',encoding='utf-8') as f:
        json.dump(value,f,ensure_ascii=False,sort_keys=True,indent=2,allow_nan=False)
        f.write('\n');f.flush();os.fsync(f.fileno())
    os.replace(temporary,path)


def export_artifact(folder: Path, booster, preprocessing: dict, metadata: dict):
    folder=Path(folder)
    if folder.exists():
        raise ValueError('immutable_artifact_exists')
    folder.parent.mkdir(parents=True,exist_ok=True)
    staging=folder.parent/('.building-'+folder.name+'-'+uuid.uuid4().hex)
    staging.mkdir(mode=0o750)
    booster.save_model(str(staging/'model.txt'))
    write_json(staging/'contract.json',feature_contract())
    write_json(staging/'preprocessing.json',preprocessing)
    write_json(staging/'metadata.json',metadata)
    manifest=dict(format='plvr-native-lightgbm-v1',model_version=metadata['model_version'],
                  files={name:digest(staging/name) for name in FILES})
    write_json(staging/'manifest.json',manifest)
    load_artifact(staging)
    for path in staging.iterdir():
        path.chmod(0o440)
    staging.chmod(0o550)
    staging.rename(folder)
    return manifest


def load_artifact(folder: Path, expected_manifest_sha256: str | None = None) -> dict:
    folder=Path(folder)
    manifest_path=folder/'manifest.json'
    if manifest_path.is_symlink() or manifest_path.stat().st_size>32768:
        raise ValueError('artifact_manifest_invalid')
    if expected_manifest_sha256 and digest(manifest_path)!=expected_manifest_sha256:
        raise ValueError('artifact_manifest_checksum')
    manifest=json.loads(manifest_path.read_text())
    if manifest.get('format')!='plvr-native-lightgbm-v1' or set(manifest.get('files',{}))!=set(FILES):
        raise ValueError('artifact_manifest_contract')
    for name, maximum in FILES.items():
        path=folder/name
        if path.is_symlink() or not path.is_file() or path.stat().st_size>maximum:
            raise ValueError('artifact_size_or_path')
        if digest(path)!=manifest['files'][name]:
            raise ValueError('artifact_checksum_mismatch')
    contract=json.loads((folder/'contract.json').read_text())
    preprocessing=json.loads((folder/'preprocessing.json').read_text())
    metadata=json.loads((folder/'metadata.json').read_text())
    if contract!=feature_contract():
        raise ValueError('artifact_feature_contract_mismatch')
    if metadata.get('model_version')!=manifest.get('model_version'):
        raise ValueError('artifact_model_version_mismatch')
    from services.valuation_ml.metadata import validate_metadata
    validate_metadata(metadata)
    import lightgbm
    import numpy
    if metadata['libraries']['lightgbm']!=lightgbm.__version__ or metadata['libraries']['numpy']!=numpy.__version__:
        raise ValueError('artifact_library_version_mismatch')
    if metadata['libraries']['python'].split('.')[:2] != platform.python_version().split('.')[:2]:
        raise ValueError('artifact_python_version_mismatch')
    from services.valuation_ml.training import fixed_encoder
    if preprocessing!=fixed_encoder():
        raise ValueError('artifact_preprocessing_mismatch')
    # Native text parser only after bounded file, checksum and semantic validation.
    model=lightgbm.Booster(model_file=str(folder/'model.txt'))
    if model.num_feature()!=len(contract['features']) or model.feature_name()!=contract['features']:
        raise ValueError('artifact_model_features_mismatch')
    return dict(model=model,contract=contract,preprocessing=preprocessing,metadata=metadata,
                manifest=manifest,manifest_sha256=digest(manifest_path))
