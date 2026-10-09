"""Authoritative inventory of production artifact contracts; no remote reads."""
from __future__ import annotations

import hashlib
import gzip
import json
import re
from datetime import date
from pathlib import Path
from typing import Mapping

from services.production_closure import SCHEMA

ROOT = Path(__file__).resolve().parents[1]
# Required means required to accept this capability, not required for API liveness.
REGISTRY = (
    ('wra-flood', 'WRA', 'r2', 'processed/wra/flood/v1/{scenario}/features.json.gz', 'wra_flood_processed_v1', 'v1', True),
    ('gsmma-sensitivity', 'GSMMA', 'r2', 'processed/gsmma/geological-sensitivity/v1/{dataset_version}/features.json.gz', 'gsmma_geological_sensitivity_features:1', None, True),
    ('ardswc-landslide', 'ARDSWC', 'remote_mvt', 'ardswc/potential_landslide+potential_landslide_affect', 'official-mvt', '113-public-mvt', True),
    ('ardswc-debris-flow', 'ARDSWC', 'remote_mvt', 'ardswc/debris_flow+debris_affect', 'official-mvt', '113-public-mvt', True),
    ('gsmma-liquefaction', 'GSMMA', 'remote_api', 'GeologyCloud/liquefaction', 'official-liquefaction-v1', None, True),
    ('nlsc-village-boundary', 'NLSC', 'local_or_r2', 'NLSC_VILLAGE_BOUNDARY_ARTIFACT_PATH|NLSC_VILLAGE_BOUNDARY_R2_KEY', 'GeoJSON-FeatureCollection', None, True),
    ('nlsc-terrain', 'NLSC', 'remote_gateway', 'NLSC_GATEWAY_BASE_URL', 'nlsc-numeric-terrain', None, True),
    ('ris-population', 'RIS', 'database', 'RIS monthly observations; raw/ris/population/{month}/manifest.json', 'ris-raw-archive-manifest-v1', None, True),
    ('plvr-blue', 'PLVR', 'database', 'VALUATION_DATABASE_URL', 'official_market_releases+official_market_artifacts+market_transactions', None, True),
    ('plvr-green', 'PLVR', 'database', 'COMPACT_GREEN_DATABASE_URL', 'compact-green-v1', None, False),
    ('tdx-mrt', 'TDX', 'process_memory', 'services.commute_service._snapshot', 'tdx-mrt-v1', None, True),
    ('road-display', 'repository-road-catalog', 'local', 'data/road-display-catalog-v2/manifest.json', 'road-display-v2', 'v2', True),
    ('road-source', 'repository-road-catalog', 'local', 'data/taiwan_roads.csv', 'city,site_id,road', None, True),
)


def freshness(published: str | None, as_of: date, max_age_days: int | None) -> str:
    # No inferred January 1 dates, mtime, retrieval date or processor version.
    if not isinstance(published, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', published) or max_age_days is None:
        return 'UNKNOWN'
    try:
        age = (as_of - date.fromisoformat(published)).days
    except ValueError:
        return 'UNKNOWN'
    return 'UNKNOWN' if age < 0 else 'STALE' if age > max_age_days else 'FRESH'


def artifact_projection(values: Mapping[str, str], *, as_of: date, root: Path = ROOT) -> list[dict]:
    rows = []
    for logical, provider, storage, location, schema, version, required in REGISTRY:
        if logical == 'gsmma-sensitivity':
            from services.provider_config_contract import exact_version
            selected = values.get('GSMMA_GEOLOGICAL_SENSITIVITY_DATASET_VERSION', '')
            version = selected if exact_version(selected) else None
        if logical == 'plvr-green':
            required = values.get('PLVR_DATA_BACKEND', 'blue').lower() == 'green'
        row = {'logical_name': logical, 'provider': provider, 'storage_kind': storage,
               'expected_storage': location, 'expected_schema': schema, 'dataset_version': version,
               'published_at': None, 'retrieved_at': None, 'built_at': None, 'sha256': None,
               'presence': 'UNKNOWN', 'freshness': 'UNKNOWN', 'freshness_as_of': as_of.isoformat(),
               'production_required': required, 'production_active': 'UNKNOWN', 'status': 'UNKNOWN',
               'limitation': 'Active deployed artifact, source date, checksum and coverage require operator evidence.'}
        if storage == 'local':
            path = root / location
            row['presence'] = 'PRESENT' if path.is_file() else 'ABSENT'
            if path.is_file() and path.stat().st_size <= 1_000_000:
                row['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
                try:
                    if path.suffix == '.json':
                        payload = json.loads(path.read_text(encoding='utf-8'))
                        row['local_contract'] = 'PASS' if isinstance(payload, dict) and payload.get('schema_version') == schema else 'BLOCKED'
                    else:
                        row['local_contract'] = 'UNKNOWN'
                except (ValueError, OSError):
                    row['local_contract'] = 'BLOCKED'
            row['limitation'] = 'Local manifest presence/schema only; member integrity, publication and deployed activation unverified.'
        rows.append(row)
    return rows


def artifact_section(values: Mapping[str, str], *, as_of: date) -> dict:
    return {'schema_version': SCHEMA, 'status': 'BLOCKED', 'scope': 'local_inventory',
            'records': artifact_projection(values, as_of=as_of), 'network_requests': 0}


def verify_local_artifact(logical_name: str, manifest_path: Path, artifact_path: Path, *,
                          scenario: str = '24h-350mm', dataset_version: str | None = None) -> dict:
    """Verify saved bytes with real runtime validators; never claim deployed activation."""
    result = {'logical_name': logical_name, 'scope': 'local_offline_artifact', 'local_contract': 'BLOCKED',
              'production_active': 'UNKNOWN', 'published_at': None, 'retrieved_at': None,
              'freshness': 'UNKNOWN', 'sha256': None, 'network_requests': 0,
              'reason_code': 'artifact_contract_invalid'}
    try:
        if logical_name not in {'wra-flood', 'gsmma-sensitivity'}:
            return result
        if manifest_path.stat().st_size > 1_000_000 or artifact_path.stat().st_size > 16_000_000:
            return {**result, 'reason_code': 'artifact_size_ceiling'}
        with gzip.open(artifact_path, 'rb') as stream:
            total = 0
            while chunk := stream.read(64 * 1024):
                total += len(chunk)
                if total > 64_000_000:
                    return {**result, 'reason_code': 'decompressed_size_ceiling'}
        from services.provider_artifact_acceptance import validate_wra_artifact, validate_gsmma_artifact
        manifest, artifact = manifest_path.read_bytes(), artifact_path.read_bytes()
        details = (validate_wra_artifact(manifest, artifact, scenario=scenario) if logical_name == 'wra-flood'
                   else validate_gsmma_artifact(manifest, artifact, dataset_version=dataset_version))
        return {**result, 'local_contract': 'PASS', 'sha256': details['artifact_sha256'],
                'reason_code': 'offline_runtime_contract_verified'}
    except Exception:
        return result
