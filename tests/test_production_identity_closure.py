import json
from pathlib import Path

import pytest

from services import production_identity as identity


def test_missing_build_never_promotes_runtime_sha(tmp_path):
    result = identity.backend_identity(tmp_path / 'missing', {'RELEASE_COMMIT_SHA': 'a' * 40})
    assert result['commit_sha'] == 'unconfigured'
    assert result['identity_status'] == 'UNKNOWN'


def test_build_is_authoritative_and_strips_extra_fields(tmp_path):
    path = tmp_path / 'build.json'
    payload = {'schema_version': 'backend-build-v1', 'commit_sha': 'a' * 40,
               'build_timestamp': '2026-10-09T01:00:00Z', 'build_id': 'sha256:' + 'b' * 64,
               'service': 'proptech-api', 'source': 'git-checkout', 'secret': 'private-secret'}
    path.write_text(json.dumps(payload))
    result = identity.backend_identity(path, {'RELEASE_COMMIT_SHA': 'c' * 40})
    assert result['commit_sha'] == 'a' * 40
    assert result['identity_status'] == 'PASS'
    assert result['runtime_sha_matches_build'] is False
    assert 'private-secret' not in json.dumps(result)


@pytest.mark.parametrize('payload', [{}, [], {'schema_version': 'backend-build-v1', 'commit_sha': 'x' * 40}])
def test_malformed_build_is_unknown(tmp_path, payload):
    path = tmp_path / 'build.json'
    path.write_text(json.dumps(payload))
    assert identity.backend_identity(path, {})['identity_status'] == 'UNKNOWN'


def test_writer_uses_git_not_runtime_claim(tmp_path, monkeypatch):
    from scripts.write_backend_build_identity import write_identity
    monkeypatch.setenv('RELEASE_COMMIT_SHA', 'c' * 40)
    path = tmp_path / 'build.json'
    write_identity(path, root=Path(__file__).resolve().parents[1])
    result = identity.backend_identity(path, {})
    assert result['identity_status'] == 'PASS'
    assert result['commit_sha'] != 'c' * 40


def test_no_git_build_requires_explicit_ci_sha(tmp_path, monkeypatch):
    from scripts.write_backend_build_identity import write_identity
    import subprocess
    monkeypatch.delenv('RENDER_GIT_COMMIT', raising=False)
    monkeypatch.setattr(subprocess, 'run', lambda *args, **kwargs: (_ for _ in ()).throw(subprocess.CalledProcessError(128, 'git')))
    with pytest.raises(subprocess.CalledProcessError):
        write_identity(tmp_path / 'missing.json', root=tmp_path)
    write_identity(tmp_path / 'build.json', root=tmp_path, commit='a' * 40)
    assert identity.backend_identity(tmp_path / 'build.json', {})['identity_status'] == 'PASS'


def test_deployment_requires_separate_expected_sha_observations():
    from services.production_closure import deployment_projection
    smoke = {'mode': 'local', 'status': 'pass', 'release_identity': {'frontend_sha': 'a' * 40, 'backend_sha': 'b' * 40}}
    assert deployment_projection(smoke, 'a' * 40, 'b' * 40)['status'] == 'UNKNOWN'
    smoke['mode'] = 'hosted'
    assert deployment_projection(smoke, 'a' * 40, 'c' * 40)['status'] == 'BLOCKED'
