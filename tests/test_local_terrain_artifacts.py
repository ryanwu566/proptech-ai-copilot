"""Exercise real artifact validation over local files; network is forbidden."""
import json

import pytest

from services.wra_flood_runtime import (
    WraFloodRuntime, SourceUnavailableError, ChecksumMismatchError, ArtifactInvalidError,
)
from services.gsmma_geological_sensitivity_runtime import GsmmaGeologicalSensitivityRuntime
from tests.test_wra_flood_runtime import _make_artifact
from tests.test_gsmma_geological_sensitivity_runtime import _build_objects, VERSION


def no_network():
    raise AssertionError('local mode attempted R2')


def write_wra(root, manifest=None, artifact=None):
    m, a, _ = _make_artifact('6h-150mm')
    directory = root / '6h-150mm'
    directory.mkdir(parents=True)
    (directory / 'manifest.json').write_bytes(m if manifest is None else manifest)
    (directory / 'features.json.gz').write_bytes(a if artifact is None else artifact)


def test_wra_local_load_and_no_match_without_r2(tmp_path, monkeypatch):
    write_wra(tmp_path)
    monkeypatch.setenv('WRA_FLOOD_LOCAL_ROOT', str(tmp_path))
    runtime = WraFloodRuntime(client_factory=no_network)
    loaded = runtime.load_scenario('6h-150mm')
    point = loaded.geometries[0].representative_point()
    result = runtime.query_point('6h-150mm', point.x, point.y)
    assert result['matched'] is True
    assert result['storage_backend'] == 'local'
    assert result['artifact_sha256'] == loaded.artifact_sha256
    miss = runtime.query_point('6h-150mm', 0, 0)
    assert miss['status'] == 'no_match'
    assert 'safe' not in miss
    assert runtime.cold_load_count == 1


def test_wra_local_missing_never_falls_back(tmp_path):
    with pytest.raises(SourceUnavailableError):
        WraFloodRuntime(client_factory=no_network, local_root=tmp_path).load_scenario('6h-150mm')


def test_wra_local_checksum_fails_closed(tmp_path):
    write_wra(tmp_path, artifact=b'corrupt')
    with pytest.raises(ChecksumMismatchError):
        WraFloodRuntime(client_factory=no_network, local_root=tmp_path).load_scenario('6h-150mm')


def test_wra_local_malformed_manifest(tmp_path):
    write_wra(tmp_path, manifest=b'[]')
    with pytest.raises(ArtifactInvalidError):
        WraFloodRuntime(client_factory=no_network, local_root=tmp_path).load_scenario('6h-150mm')


def test_wra_local_matching_checksum_invalid_gzip(tmp_path):
    import hashlib
    m, _, _ = _make_artifact('6h-150mm')
    manifest = json.loads(m)
    manifest['artifact_sha256'] = hashlib.sha256(b'bad gzip').hexdigest()
    write_wra(tmp_path, manifest=json.dumps(manifest).encode(), artifact=b'bad gzip')
    with pytest.raises(ArtifactInvalidError):
        WraFloodRuntime(client_factory=no_network, local_root=tmp_path).load_scenario('6h-150mm')


def test_local_symlink_escape_fails_closed(tmp_path):
    root = tmp_path / 'root'
    root.mkdir()
    outside = tmp_path / 'outside'
    write_wra(outside)
    (root / '6h-150mm').symlink_to(outside / '6h-150mm', target_is_directory=True)
    with pytest.raises(SourceUnavailableError):
        WraFloodRuntime(client_factory=no_network, local_root=root).load_scenario('6h-150mm')


def test_gsmma_local_same_contract(tmp_path, monkeypatch):
    objects = _build_objects(tmp_path)
    root = tmp_path / 'local'
    for key, payload in objects.items():
        path = root / VERSION / key.rsplit('/', 1)[1]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
    monkeypatch.setenv('GSMMA_GEOLOGICAL_SENSITIVITY_LOCAL_ROOT', str(root))
    runtime = GsmmaGeologicalSensitivityRuntime(client_factory=no_network, dataset_version=VERSION)
    loaded = runtime.load_dataset()
    point = loaded.geometries[0].representative_point()
    result = runtime.query_point(point.x, point.y)
    assert result['matched'] is True
    assert result['storage_backend'] == 'local'
    assert runtime.query_point(0, 0)['status'] == 'no_match'


def test_gsmma_local_missing_never_falls_back(tmp_path, monkeypatch):
    monkeypatch.setenv("R2_BUCKET", "must-not-use")
    from services.gsmma_geological_sensitivity_runtime import SourceUnavailableError as GsmmaUnavailable
    calls = []
    def forbidden_factory():
        calls.append(True)
        raise AssertionError('local mode attempted R2')
    with pytest.raises(GsmmaUnavailable):
        GsmmaGeologicalSensitivityRuntime(
            client_factory=forbidden_factory, dataset_version=VERSION, local_root=tmp_path,
        ).load_dataset()
    assert calls == []


@pytest.mark.parametrize('version', ['latest', '../escape', '/tmp/escape', '..'])
def test_gsmma_local_version_rejected_before_file_access(tmp_path, version):
    from services.gsmma_geological_sensitivity_runtime import UnsupportedDatasetRuntimeError
    with pytest.raises(UnsupportedDatasetRuntimeError):
        GsmmaGeologicalSensitivityRuntime(
            client_factory=no_network, dataset_version=version, local_root=tmp_path,
        ).load_dataset()


def test_local_relative_root_rejected(tmp_path):
    with pytest.raises(SourceUnavailableError):
        WraFloodRuntime(client_factory=no_network, local_root='relative').load_scenario('6h-150mm')


def test_gsmma_local_checksum_fails_closed(tmp_path):
    from services.gsmma_geological_sensitivity_runtime import ChecksumMismatchError as GsmmaChecksum
    objects = _build_objects(tmp_path)
    root = tmp_path / 'local'
    for key, payload in objects.items():
        path = root / VERSION / key.rsplit('/', 1)[1]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload if path.name == 'manifest.json' else b'corrupt')
    with pytest.raises(GsmmaChecksum):
        GsmmaGeologicalSensitivityRuntime(
            client_factory=no_network, dataset_version=VERSION, local_root=root,
        ).load_dataset()


def test_local_wra_provider_provenance(tmp_path):
    from services.terrain_risk_providers.wra_flood_provider import WraFloodProvider
    write_wra(tmp_path)
    runtime = WraFloodRuntime(client_factory=no_network, local_root=tmp_path)
    loaded = runtime.load_scenario('6h-150mm')
    point = loaded.geometries[0].representative_point()
    provider = WraFloodProvider(query_point=runtime.query_point, scenario='6h-150mm')
    layer = provider.analyze(point.y, point.x, 500)
    assert layer['status'] == 'available'
    assert layer['matched'] is True
    assert layer['source']['storage_backend'] == 'local'
    assert layer['source']['artifact_sha256'] == loaded.artifact_sha256


def test_local_gsmma_provider_provenance(tmp_path):
    from services.terrain_risk_providers.gsmma_geological_sensitivity_provider import GsmmaGeologicalSensitivityProvider
    objects = _build_objects(tmp_path)
    root = tmp_path / 'local'
    for key, payload in objects.items():
        path = root / VERSION / key.rsplit('/', 1)[1]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
    runtime = GsmmaGeologicalSensitivityRuntime(
        client_factory=no_network, dataset_version=VERSION, local_root=root,
    )
    point = runtime.load_dataset().geometries[0].representative_point()
    layer = GsmmaGeologicalSensitivityProvider(runtime=runtime).analyze(point.y, point.x, 500)
    assert layer['status'] == 'available'
    assert layer['level'] == 'unknown'
    assert layer['source']['storage_backend'] == 'local'
    assert layer['source']['dataset_version'] == VERSION


def test_local_symlink_cannot_be_swapped_between_validation_and_read(tmp_path, monkeypatch):
    from pathlib import Path
    from services.local_artifact_store import LocalArtifactStore
    root = tmp_path / 'root'
    outside = tmp_path / 'outside'
    write_wra(root)
    write_wra(outside, manifest=b'outside-root')
    original_open = Path.open
    def swap_then_open(path, *args, **kwargs):
        if path == root / '6h-150mm' / 'manifest.json':
            (root / '6h-150mm').rename(root / 'old')
            (root / '6h-150mm').symlink_to(outside / '6h-150mm', target_is_directory=True)
        return original_open(path, *args, **kwargs)
    monkeypatch.setattr(Path, 'open', swap_then_open)
    result = LocalArtifactStore(root, 'processed/wra/flood/v1').get_object(
        Bucket='local', Key='processed/wra/flood/v1/6h-150mm/manifest.json',
    )['Body'].read()
    assert result != b'outside-root'


def test_local_open_pins_directory_against_concurrent_replacement(tmp_path, monkeypatch):
    import os
    from services.local_artifact_store import LocalArtifactStore
    root = tmp_path / 'root'
    outside = tmp_path / 'outside'
    write_wra(root)
    write_wra(outside, manifest=b'outside-root')
    original_open = os.open
    swapped = []
    def swapping_open(path, flags, *args, **kwargs):
        fd = original_open(path, flags, *args, **kwargs)
        if path == '6h-150mm' and not swapped:
            (root / '6h-150mm').rename(root / 'old')
            (root / '6h-150mm').symlink_to(outside / '6h-150mm', target_is_directory=True)
            swapped.append(True)
        return fd
    monkeypatch.setattr(os, 'open', swapping_open)
    payload = LocalArtifactStore(root, 'processed/wra/flood/v1').get_object(
        Bucket='local', Key='processed/wra/flood/v1/6h-150mm/manifest.json',
    )['Body'].read()
    assert swapped == [True]
    assert json.loads(payload)['scenario'] == '6h-150mm'


@pytest.mark.parametrize(('capability', 'env_name', 'logical'), [
    ('wra', 'WRA_FLOOD_LOCAL_ROOT', 'wra-flood'),
    ('gsmma', 'GSMMA_GEOLOGICAL_SENSITIVITY_LOCAL_ROOT', 'gsmma-sensitivity'),
])
def test_passive_configuration_recognizes_local_mode(capability, env_name, logical):
    from datetime import date
    from services.provider_config_contract import configuration_status
    from services.production_artifact_registry import artifact_projection
    environ = {env_name: '/srv/immutable', 'GSMMA_GEOLOGICAL_SENSITIVITY_DATASET_VERSION': VERSION}
    status = configuration_status(capability, environ)
    assert status[env_name] == 'present'
    assert not any(name.startswith('R2_') for name in status)
    row = next(r for r in artifact_projection(environ, as_of=date(2026, 10, 28)) if r['logical_name'] == logical)
    assert row['storage_kind'] == 'local'
    assert env_name in row['expected_storage']
    assert row['production_active'] == 'UNKNOWN'
    assert row['presence'] == 'UNKNOWN'
    assert configuration_status(capability, {env_name: 'relative'})[env_name] == 'invalid-contract'
