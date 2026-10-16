"""Behavioral safety tests; external Docker/age operations are injected at the boundary."""
import importlib.util
import json
import hashlib
from pathlib import Path

import pytest

from tests.test_usage_database_bootstrap import target, install

MODULE = Path(__file__).resolve().parents[1] / 'scripts/ops/ops_backup_tools.py'


@pytest.fixture
def ops():
    assert MODULE.exists(), 'operations implementation missing'
    spec = importlib.util.spec_from_file_location('backup_ops', MODULE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_remote_endpoint_refused_before_docker_contact(ops, monkeypatch):
    monkeypatch.setenv('DOCKER_HOST', 'tcp://real-server:2376')
    monkeypatch.setattr(ops, 'run', lambda *a, **k: pytest.fail('remote Docker contacted'))
    with pytest.raises(ValueError):
        ops.local_docker()


def test_backup_refuses_symlink_parent_without_contact(ops, tmp_path, monkeypatch):
    actual = tmp_path / 'actual'
    actual.mkdir()
    link = tmp_path / 'link'
    try:
        link.symlink_to(actual, target_is_directory=True)
    except OSError:
        pytest.skip('symlink creation unavailable')
    monkeypatch.setattr(ops, 'local_docker', lambda: pytest.fail('Docker contacted'))
    with pytest.raises(ValueError):
        ops.backup(link / 'output', tmp_path / 'recipients', 'test')


def test_pipeline_failure_never_marks_backup_success_or_overwrites_copy(ops, tmp_path, monkeypatch):
    recipients = tmp_path / 'recipients'
    recipients.write_text('age1testrecipient\n')
    output = tmp_path / 'backups'
    output.mkdir()
    good = output / 'prior-copy'
    good.mkdir()
    (good / 'SUCCESS').write_text('untouched')
    monkeypatch.setattr(ops, 'local_docker', lambda: ['docker', '--host', 'unix:///local'])
    monkeypatch.setattr(ops, 'run', lambda *a, **k: b'170010\n')
    def fail(*args, **kwargs):
        raise RuntimeError('pg_dump failed')
    monkeypatch.setattr(ops, 'pipeline', fail)
    with pytest.raises(RuntimeError):
        ops.backup(output, recipients, 'test')
    assert (good / 'SUCCESS').read_text() == 'untouched'
    created = [p for p in output.iterdir() if p != good]
    assert len(created) == 1
    assert not (created[0] / 'SUCCESS').exists()


def test_role_restore_only_skips_validated_default_postgres_creation(ops):
    source = b'-- roles\nCREATE ROLE postgres;\nALTER ROLE postgres WITH SUPERUSER;\nCREATE ROLE usage_migration;\n'
    restored = ops.prepare_roles(source)
    assert b'CREATE ROLE postgres;' not in restored
    assert b'CREATE ROLE usage_migration;' in restored
    assert b'ALTER ROLE postgres WITH SUPERUSER;' in restored
    with pytest.raises(ValueError):
        ops.prepare_roles(source + b'CREATE ROLE postgres;\n')


@pytest.fixture
def valid_bundle(ops, tmp_path):
    def description(content):
        return {'bytes': len(content), 'sha256': hashlib.sha256(content).hexdigest()}
    files = {}
    for name in ('app.dump.age','app.roles.age','usage.dump.age','usage.roles.age'):
        (tmp_path/name).write_bytes(b'ciphertext')
        files[name] = description(b'ciphertext')
    config = {'files': {}}
    for relative in ops.CONFIG_FILES:
        target = tmp_path/'config'/relative
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(b'reviewed configuration')
        config['files'][relative] = description(b'reviewed configuration')
    encoded = json.dumps(config).encode()
    (tmp_path/'config.json').write_bytes(encoded)
    (tmp_path/'SHA256SUMS').write_text('test fixture')
    (tmp_path / 'SUCCESS').write_text('ok\n')
    (tmp_path / 'manifest.json').write_text(json.dumps({'schema_version': 1, 'postgres_major':17, 'files': files, 'configuration':description(encoded)}))
    ops.verify_bundle(tmp_path)
    return tmp_path


def test_restore_rejects_changed_archive_before_daemon_contact(ops, valid_bundle, monkeypatch):
    tmp_path = valid_bundle
    (tmp_path/'app.dump.age').write_bytes(b'changed')
    monkeypatch.setattr(ops, 'local_docker', lambda: pytest.fail('Docker contacted'))
    with pytest.raises(ValueError):
        ops.restore(tmp_path, tmp_path / 'identity')


def test_pipeline_failure_removes_partial_output_and_hides_secret_stderr(ops, tmp_path):
    import sys
    output = tmp_path / 'partial.age'
    source = [sys.executable, '-c', 'import sys;sys.stdout.buffer.write(b"plaintext");sys.stderr.write("SECRET_URL");sys.exit(1)']
    sink = [sys.executable, '-c', 'import sys;sys.stdout.buffer.write(b"encrypted:"+sys.stdin.buffer.read())']
    with pytest.raises(RuntimeError, match='pipeline_failed') as error:
        ops.pipeline(source, sink, output=output)
    assert 'SECRET_URL' not in str(error.value)
    assert not output.exists()


def test_backup_completion_hashes_all_encrypted_archives_in_unique_directories(ops, tmp_path, monkeypatch):
    recipients = tmp_path/'recipients'
    recipients.write_text('age1test\n')
    output = tmp_path/'backup'
    monkeypatch.setattr(ops, 'local_docker', lambda: ['docker', '--host', 'unix:///local'])
    runtime = tmp_path/'runtime.env'
    runtime.write_text('APP_ENV=preview\n')
    monkeypatch.setenv('SELFHOST_RUNTIME_ENV_FILE',str(runtime))
    monkeypatch.setenv('SELFHOST_BACKEND_IMAGE','sha256:'+'a'*64)
    monkeypatch.setenv('SELFHOST_PROXY_IMAGE','nginx@sha256:'+'b'*64)
    def fake_run(command, **kwargs):
        if 'rev-parse' in command:
            return b'0ac46365f35b01d5f13aed978a4eb3ddf00db670\n'
        if 'image' in command:
            return ('sha256:'+'a'*64).encode()
        return b'170010\n'
    monkeypatch.setattr(ops,'run',fake_run)
    def encrypted_fixture(source, sink, *, output):
        output.write_bytes(b'age-encryption.org/v1\ntest-ciphertext')
    monkeypatch.setattr(ops, 'pipeline', encrypted_fixture)
    first = ops.backup(output, recipients, 'test')
    second = ops.backup(output, recipients, 'test')
    assert first != second
    manifest = ops.verify_bundle(output/first)
    assert set(manifest['files']) == {'app.dump.age','app.roles.age','usage.dump.age','usage.roles.age'}
    assert (output/first/'SUCCESS').read_text() == 'encrypted_archives_complete\n'
    assert not list(output.rglob('*.dump'))
    (output/first/'config/infra/selfhost/pg_hba.conf').write_text('tampered')
    with pytest.raises(ValueError, match='config_integrity_failed'):
        ops.verify_bundle(output/first)


@pytest.mark.parametrize('ready,usage_available,expected,guard_expected',
                         [(True,True,'PASS','PASS'),(False,True,'FAIL','PASS'),(True,False,'PASS','FAIL')])
def test_health_checks_readiness_body_and_direct_usage_probe(ops, tmp_path, monkeypatch, ready, usage_available, expected, guard_expected):
    from http.server import BaseHTTPRequestHandler, HTTPServer
    import threading
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200 if self.path in ('/health','/readiness') else 404)
            self.end_headers()
            self.wfile.write(json.dumps({'mode':'preview','readiness':'ready' if ready else 'blocked'} if self.path=='/health' else {'runtime':{'mode':'preview','ready':ready}}).encode())
        def log_message(self, *args):
            pass
    server = HTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    monkeypatch.setattr(ops, 'local_docker', lambda: ['docker', '--host', 'unix:///local'])
    def external(command, **kwargs):
        if 'scripts/ops/selfhost_runtime.py' in command:
            if not usage_available:
                raise RuntimeError('command_failed')
            return b'{"status":"pass","read_only":true,"usage_guard":"available","http_readiness":"ready"}'
        return b''
    monkeypatch.setattr(ops, 'run', external)
    try:
        categories = ops.health(tmp_path, 'test', f'http://127.0.0.1:{server.server_port}', 30)
    finally:
        server.shutdown()
        server.server_close()
        thread.join()
    assert categories['HEALTH'] == expected
    assert categories['READINESS'] == expected
    assert categories['USAGE_GUARD'] == guard_expected


def test_restore_refuses_readable_private_identity_on_unix(ops, valid_bundle, monkeypatch):
    import os
    if os.name == 'nt':
        pytest.skip('Unix identity permissions only')
    identity = valid_bundle/'identity'
    identity.write_text('test-key')
    identity.chmod(0o644)
    monkeypatch.setattr(ops, 'local_docker', lambda: pytest.fail('Docker contacted'))
    with pytest.raises(ValueError):
        ops.restore(valid_bundle, identity)


def test_pipeline_never_overwrites_existing_output(ops, tmp_path):
    import sys
    existing = tmp_path/'archive.age'
    existing.write_bytes(b'only-good-copy')
    with pytest.raises(FileExistsError):
        ops.pipeline([sys.executable, '-c', 'pass'], [sys.executable, '-c', 'pass'], output=existing)
    assert existing.read_bytes() == b'only-good-copy'


def test_subprocess_environment_only_preserves_system_and_documented_infra(ops, monkeypatch):
    monkeypatch.setenv('ODD_PROVIDER_AUTH', 'secret-provider-value')
    monkeypatch.setenv('DATABASE_URL', 'secret-database-value')
    monkeypatch.setenv('COMPOSE_FILE', 'attacker-compose.yml')
    monkeypatch.setenv('SELFHOST_SECRETS_DIR', '/run/private/mount-sources')
    observed = ops.environment()
    assert 'ODD_PROVIDER_AUTH' not in observed
    assert 'DATABASE_URL' not in observed
    assert 'COMPOSE_FILE' not in observed
    assert observed['SELFHOST_SECRETS_DIR'] == '/run/private/mount-sources'


def test_recovery_config_includes_only_allowlisted_inputs_and_rejects_tampering(ops, tmp_path, monkeypatch):
    runtime = tmp_path/'runtime.env'
    runtime.write_text('APP_ENV=preview\nMAINTENANCE_MODE=true\nDATABASE_URL=SECRET_DB\nODD_PROVIDER_AUTH=SECRET_TOKEN\n')
    monkeypatch.setenv('SELFHOST_RUNTIME_ENV_FILE', str(runtime))
    monkeypatch.setenv('SELFHOST_BACKEND_IMAGE', 'sha256:'+'a'*64)
    monkeypatch.setenv('SELFHOST_PROXY_IMAGE', 'nginx@sha256:'+'b'*64)
    monkeypatch.setattr(ops, 'run', lambda command, **k: ('sha256:'+'a'*64).encode() if 'image' in command else b'0ac46365f35b01d5f13aed978a4eb3ddf00db670\n')
    monkeypatch.setattr(ops, 'local_docker', lambda: ['docker','--host','unix:///local'])
    result = ops.capture_config(tmp_path/'config')
    assert result['release_commit'] == '0ac46365f35b01d5f13aed978a4eb3ddf00db670'
    assert result['runtime'] == {'APP_ENV': 'preview', 'MAINTENANCE_MODE': 'true'}
    assert 'docker-compose.selfhost.yml' in result['files']
    assert 'infra/selfhost/pg_hba.conf' in result['files']
    persisted = b''.join(p.read_bytes() for p in (tmp_path/'config').rglob('*') if p.is_file())
    assert b'SECRET_DB' not in persisted and b'SECRET_TOKEN' not in persisted


def test_runtime_restore_probe_connects_as_direct_login_and_refuses_policy_write(ops):
    commands = []
    def target_run(command, *, data=None, **kwargs):
        commands.append(command)
        assert '-h' in command and '127.0.0.1' in command
        assert '-U' in command and 'proptech_usage_runtime_v1' in command
        if b'UPDATE api_usage.quota_policy' in data:
            return b'DO\nDENIED\n'
        return b't\nt\nBEGIN\nt\nROLLBACK\n'
    ops.direct_runtime_probe(['docker','exec','-i','--user','postgres','fresh-owned'], target_run)
    assert len(commands) == 2


def test_runtime_probe_does_not_treat_connection_failure_as_privilege_denial(ops):
    def broken_target(command, *, data):
        if b'UPDATE api_usage.quota_policy' in data:
            raise RuntimeError('connection_failed')
        return b't\nt\nt\n'
    with pytest.raises(RuntimeError, match='connection_failed'):
        ops.direct_runtime_probe(['docker','exec','fresh-owned'], broken_target)


def test_rehearsal_refuses_oversized_backup_before_daemon_contact(ops, tmp_path, monkeypatch):
    monkeypatch.setattr(ops, 'verify_bundle', lambda *a: {'files': {'archive': {'bytes': 64*1024*1024+1}}})
    monkeypatch.setattr(ops, 'local_docker', lambda: pytest.fail('Docker contacted'))
    with pytest.raises(ValueError, match='small_rehearsal_archive_limit'):
        ops.restore(tmp_path, tmp_path/'identity')


def test_catalog_fingerprint_survives_real_quota_insert(ops, target, monkeypatch):
    """Existing explicit disposable-PG17 fixture; no SQL/history forging."""
    import uuid
    install(target, runtime=True)
    def query_catalog(base, service, database, query):
        records = []
        with target.connect('postgres') as connection:
            cursor = connection.execute(query)
            while True:
                if cursor.description:
                    records.extend(json.dumps(row[0],sort_keys=True) for row in cursor.fetchall())
                if not cursor.nextset():
                    break
        return ('\n'.join(records)+'\n').encode()
    monkeypatch.setattr(ops, 'socket_sql', query_catalog)
    before = ops.fingerprint([], 'postgres_usage', target.database)
    with target.connect('proptech_usage_runtime_v1') as connection:
        assert connection.execute("SELECT result FROM api_usage.consume(%s,'anonymous','places','request',%s)",
                                  ('anon:'+'e'*64,uuid.uuid4())).fetchone() == ('admitted',)
    with target.connect('postgres') as connection:
        assert connection.execute('SELECT count(*) FROM api_usage.quota_subjects').fetchone() == (1,)
    assert ops.fingerprint([], 'postgres_usage', target.database) == before
