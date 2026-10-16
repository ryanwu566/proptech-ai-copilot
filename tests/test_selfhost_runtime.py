"""Behavioral tests for private selfhost secret boundaries and refusal output."""
from pathlib import Path
import json
import os
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/ops/selfhost_runtime.py'


def cli(*args, env=None):
    return subprocess.run([sys.executable, str(SCRIPT), *args], cwd=ROOT,
                          env={**os.environ, **(env or {})}, capture_output=True, text=True, timeout=10)


def secret_files(tmp_path):
    values = {
        'app_database_url': 'postgresql://app_runtime:test%40password@postgres_app/proptech_app',
        'usage_database_url': 'postgresql://proptech_usage_runtime_v1:testpassword@postgres_usage/proptech_api_usage',
        'usage_peer_hmac_key': 'h' * 48,
        'pilot_session_signing_key': 's' * 48,
    }
    for name, value in values.items():
        (tmp_path / name).write_text(value + '\n', encoding='utf-8')
    return values


def test_missing_runtime_secret_refuses_without_inherited_fallback(tmp_path):
    values = secret_files(tmp_path)
    (tmp_path / 'usage_database_url').unlink()
    result = cli('validate-secrets', '--secrets-dir', str(tmp_path), env={
        'API_USAGE_DATABASE_URL': values['usage_database_url'], 'DATABASE_URL': 'SENTINEL_SECRET',
    })
    assert result.returncode == 1
    assert json.loads(result.stdout)['status'] == 'refused'
    assert 'SENTINEL_SECRET' not in result.stdout + result.stderr
    assert values['usage_database_url'] not in result.stdout + result.stderr


def test_only_runtime_identity_is_accepted_without_disclosing_dsn(tmp_path):
    secret_files(tmp_path)
    value = 'postgresql://usage_migration:never-print-password@postgres_usage/proptech_api_usage'
    (tmp_path / 'usage_database_url').write_text(value)
    result = cli('validate-secrets', '--secrets-dir', str(tmp_path))
    assert result.returncode == 1
    assert 'never-print-password' not in result.stdout + result.stderr
    assert json.loads(result.stdout)['reason'] == 'invalid_usage_database_url'


@pytest.mark.parametrize('value', [
    'postgresql://proptech_usage_runtime_v1:pw@remote.invalid/proptech_api_usage',
    'postgresql://proptech_usage_runtime_v1:pw@postgres_usage/wrong',
    'postgresql://proptech_usage_runtime_v1:pw@postgres_usage/proptech_api_usage?sslmode=disable',
    'postgresql://proptech_usage_runtime_v1:pw@postgres_usage:5555/proptech_api_usage',
])
def test_unexpected_database_boundary_is_refused(tmp_path, value):
    secret_files(tmp_path)
    (tmp_path / 'usage_database_url').write_text(value)
    result = cli('validate-secrets', '--secrets-dir', str(tmp_path))
    assert result.returncode == 1
    assert json.loads(result.stdout)['status'] == 'refused'
    assert value not in result.stdout + result.stderr


def test_valid_secrets_are_value_free_and_unused_admin_mount_is_refused(tmp_path):
    values = secret_files(tmp_path)
    result = cli('validate-secrets', '--secrets-dir', str(tmp_path))
    assert result.returncode == 0
    assert json.loads(result.stdout) == {'status': 'pass', 'runtime_secrets': 'validated'}
    for value in values.values():
        assert value not in result.stdout + result.stderr
    (tmp_path / 'usage_bootstrap_database_url').write_text('postgresql://admin:secret@remote/app')
    result = cli('validate-secrets', '--secrets-dir', str(tmp_path))
    assert result.returncode == 1
    assert json.loads(result.stdout)['reason'] == 'administrative_secret_in_runtime_mount'


def test_empty_and_multiline_secrets_fail_closed(tmp_path):
    secret_files(tmp_path)
    (tmp_path / 'usage_peer_hmac_key').write_text('a' * 48 + '\nINJECT=secret')
    result = cli('validate-secrets', '--secrets-dir', str(tmp_path))
    assert result.returncode == 1
    assert 'INJECT' not in result.stdout + result.stderr


def test_preflight_refuses_wrong_actor_before_network(tmp_path):
    (tmp_path / 'usage_bootstrap_database_url').write_text('postgresql://postgres:SECRET@postgres_usage/proptech_api_usage')
    result = cli('preflight', '--secrets-dir', str(tmp_path))
    assert result.returncode == 1
    assert json.loads(result.stdout)['reason'] == 'invalid_bootstrap_database_url'
    assert 'SECRET' not in result.stdout + result.stderr

def test_runtime_password_activation_requires_explicit_secret_without_inherited_fallback(tmp_path):
    (tmp_path / 'usage_bootstrap_database_url').write_text('postgresql://usage_migration:dummy@postgres_usage/proptech_api_usage')
    result = cli('activate-runtime', '--secrets-dir', str(tmp_path), env={'PGPASSWORD': 'NEVER_PRINT'})
    assert result.returncode == 1
    assert json.loads(result.stdout)['reason'] == 'secret_missing_or_invalid'
    assert 'NEVER_PRINT' not in result.stdout + result.stderr

def test_runtime_environment_drops_libpq_and_administrative_overrides(tmp_path, monkeypatch):
    from scripts.ops.selfhost_runtime import runtime_environment
    secret_files(tmp_path)
    for name in ('PGPASSWORD', 'PGPASSFILE', 'PGOPTIONS', 'PGSSLMODE', 'PGSERVICEFILE',
                 'API_USAGE_BOOTSTRAP_DATABASE_URL', 'PILOT_EVIDENCE_DATABASE_URL'):
        monkeypatch.setenv(name, 'inherited-administrative-value')
    environment = runtime_environment(tmp_path)
    for name in ('PGPASSWORD', 'PGPASSFILE', 'PGOPTIONS', 'PGSSLMODE', 'PGSERVICEFILE',
                 'API_USAGE_BOOTSTRAP_DATABASE_URL', 'PILOT_EVIDENCE_DATABASE_URL'):
        assert name not in environment
    assert environment['POSTGRES_SSLMODE'] == 'verify-full'
    assert environment['PGSSLROOTCERT'] == '/run/selfhost-ca/ca.crt'

def test_compose_runtime_mounts_are_valid_and_do_not_publish_database_or_api(tmp_path):
    """Parsed Compose model catches malformed tmpfs paths before Docker launch."""
    import shutil
    if not shutil.which('docker'):
        pytest.skip('Docker Compose CLI is unavailable')
    runtime_env = tmp_path / 'runtime.env'
    runtime_env.write_text('API_ALLOWED_HOSTS=localhost\n')
    environment = {**os.environ,
        'SELFHOST_SECRETS_DIR': str(tmp_path), 'SELFHOST_TLS_DIR': str(tmp_path),
        'SELFHOST_RUNTIME_ENV_FILE': str(runtime_env),
        'SELFHOST_BACKEND_IMAGE': 'backend@sha256:' + 'a' * 64,
        'SELFHOST_PROXY_IMAGE': 'nginx@sha256:' + 'b' * 64,
    }
    result = subprocess.run(['docker', 'compose', '-f', 'docker-compose.selfhost.yml',
        '--profile', 'usage_ops', 'config', '--format', 'json'], cwd=ROOT, env=environment,
        text=True, encoding='utf-8', capture_output=True, timeout=15, check=True)
    model = json.loads(result.stdout)
    for service in model['services'].values():
        assert all(mount.split(':')[0].startswith('/') for mount in service.get('tmpfs', []))
    for name in ('postgres_app', 'postgres_usage', 'api', 'usage_ops'):
        assert not model['services'][name].get('ports')
    assert model['services']['reverse_proxy']['ports'][0]['host_ip'] == '127.0.0.1'
    assert set(model['services']['usage_ops']['networks']) == {'usage_db'}
    assert all(model['networks'][name]['internal'] for name in ('app_db','usage_db'))

def test_local_rehearsal_rejects_remote_docker_before_any_subprocess(monkeypatch):
    from scripts.ops import selfhost_rehearsal
    monkeypatch.setenv('DOCKER_HOST', 'ssh://production.invalid')
    monkeypatch.setenv('SELFHOST_BACKEND_IMAGE', 'backend@sha256:' + 'a' * 64)
    monkeypatch.setenv('SELFHOST_PROXY_IMAGE', 'nginx@sha256:' + 'b' * 64)
    def forbidden(*args, **kwargs):
        pytest.fail('Remote Docker was contacted before refusing locality')
    monkeypatch.setattr(subprocess, 'run', forbidden)
    with pytest.raises(ValueError, match='local_docker_socket_required'):
        selfhost_rehearsal.main([])


def test_bootstrap_preflight_installs_clean_libpq_environment_before_connection(tmp_path, monkeypatch):
    from scripts.ops import selfhost_runtime
    (tmp_path / 'usage_bootstrap_database_url').write_text('postgresql://usage_migration:dummy@postgres_usage/proptech_api_usage')
    monkeypatch.setenv('PGHOSTADDR', '203.0.113.1')
    monkeypatch.setenv('PGOPTIONS', 'unsafe-option')
    def stopped(url, **kwargs):
        assert 'PGHOSTADDR' not in os.environ
        assert 'PGOPTIONS' not in os.environ
        assert os.environ['PGSSLROOTCERT'] == '/run/selfhost-ca/ca.crt'
        raise RuntimeError('stop_before_network')
    monkeypatch.setattr('services.postgres_runtime.connect', stopped)
    original = dict(os.environ)
    try:
        with pytest.raises(RuntimeError, match='stop_before_network'):
            selfhost_runtime.preflight(tmp_path)
    finally:
        os.environ.clear()
        os.environ.update(original)


def test_health_missing_secret_is_closed_and_redacted(tmp_path):
    result = cli('health', '--secrets-dir', str(tmp_path), env={'DATABASE_URL':'secret-inherited'})
    assert result.returncode == 1
    assert json.loads(result.stdout)['status'] == 'refused'
    assert 'secret-inherited' not in result.stdout + result.stderr

def test_rehearsal_http_ignores_proxy_and_refuses_redirects(monkeypatch):
    from scripts.ops import selfhost_rehearsal
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    from threading import Thread
    from urllib.error import HTTPError
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass
        def do_GET(self):
            if self.path == '/health':
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b'{"readiness":"ready"}')
            else:
                self.send_response(302)
                self.send_header('Location', 'https://remote.invalid/forbidden')
                self.end_headers()
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    monkeypatch.setenv('HTTP_PROXY', 'http://127.0.0.1:9')
    monkeypatch.setenv('ALL_PROXY', 'http://127.0.0.1:9')
    monkeypatch.setenv('NO_PROXY', '')
    base = 'http://127.0.0.1:' + str(server.server_port)
    try:
        assert selfhost_rehearsal.local_http_json(base + '/health') == {'readiness': 'ready'}
        with pytest.raises(HTTPError):
            selfhost_rehearsal.local_http_json(base + '/readiness')
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

def test_http_200_without_database_readiness_is_refused(monkeypatch):
    from scripts.ops import selfhost_runtime
    class Response:
        status = 200
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def read(self, *args):
            return b'{"status":"ok","readiness":"unavailable"}'
    class Opener:
        def open(self, url, timeout):
            return Response()
    monkeypatch.setattr('urllib.request.build_opener', lambda *args: Opener())
    with pytest.raises(selfhost_runtime.Refused, match='http_readiness_unavailable'):
        selfhost_runtime.http_readiness()

def test_rehearsal_images_are_uuid_scoped_before_build(tmp_path):
    from scripts.ops import selfhost_rehearsal
    project = 'selfhost_rehearsal_ab12cd34ef56'
    override = tmp_path / 'rehearsal.yml'
    override.write_text(selfhost_rehearsal.rehearsal_override(project), encoding='utf-8')
    runtime = tmp_path / 'runtime.env'
    runtime.write_text('API_ALLOWED_HOSTS=localhost\n')
    environment = {**os.environ, 'SELFHOST_SECRETS_DIR': str(tmp_path),
        'SELFHOST_TLS_DIR': str(tmp_path), 'SELFHOST_RUNTIME_ENV_FILE': str(runtime),
        'SELFHOST_BACKEND_IMAGE': 'backend@sha256:' + 'a' * 64,
        'SELFHOST_PROXY_IMAGE': 'nginx@sha256:' + 'b' * 64}
    result = subprocess.run(['docker','compose','-f',str(ROOT/'docker-compose.selfhost.yml'),
        '-f',str(override),'--profile','usage_ops','config','--format','json'], env=environment,
        capture_output=True,text=True,encoding='utf-8',check=True,timeout=15)
    model = json.loads(result.stdout)
    assert model['services']['api']['image'] == 'selfhost_rehearsal_ab12cd34ef56-api:local'
    assert model['services']['usage_ops']['image'] == 'selfhost_rehearsal_ab12cd34ef56-api:local'
