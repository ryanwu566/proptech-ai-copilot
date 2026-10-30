"""Stage 2 uses synthetic credentials and disposable files; no real secret reads."""
from pathlib import Path
import io
import json
import logging
import os
import subprocess
import sys
from urllib.parse import quote

import pytest

ROOT = Path(__file__).resolve().parents[1]


def synthetic_mount(tmp_path):
    directory = tmp_path / 'mount'
    directory.mkdir(mode=0o700)
    values = {
        'app_database_url': 'postgresql://app_runtime:synthetic_password_0123456789@postgres_app/proptech_app',
        'usage_database_url': 'postgresql://proptech_usage_runtime_v1:synthetic_password_0123456789@postgres_usage/proptech_api_usage',
        'valuation_database_url': 'postgresql://valuation_runtime:synthetic_password_0123456789@postgres_app/proptech_valuation',
        'usage_peer_hmac_key': 'a' * 64,
        'pilot_session_signing_key': 'synthetic_session_signing_material_0123456789',
    }
    for name, value in values.items():
        p = directory / name
        p.write_text(value)
        p.chmod(0o440)
    return directory, values


def guards():
    return {
        **{'ANTI_ABUSE_' + key + '_DISABLED': 'true' for key in (
            'MARKET_OPS', 'GEOCODING', 'PLACES', 'ROUTES', 'SATELLITE', 'LOCATION',
            'PARCEL', 'ARDSWC', 'LIQUEFACTION', 'NLSC', 'TGOS')},
        'EARTH_ENGINE_SATELLITE_REFERENCE_V1': 'false',
        'PLVR_SERVING_EXCLUSIONS_ENABLED': 'true',
        'WRA_FLOOD_LOCAL_ROOT': '/srv/proptech/datasets/wra/flood/v1',
        'POSTGRES_SSLMODE': 'verify-full', 'PGSSLROOTCERT': '/run/selfhost-ca/ca.crt',
        'APP_ENV': 'preview',
    }


def test_core_file_loading_pins_tls_and_preserves_local_data_guards(tmp_path):
    from services.selfhost_secret_files import runtime_environment
    directory, values = synthetic_mount(tmp_path)
    result = runtime_environment(directory, guards(), owner=os.getuid(), gid=os.getgid())
    assert result['DATABASE_URL'] == values['app_database_url']
    assert result['API_USAGE_DATABASE_URL'] == values['usage_database_url']
    assert result['VALUATION_DATABASE_URL'].endswith('sslmode=verify-full&sslrootcert=%2Frun%2Fselfhost-ca%2Fca.crt')
    assert result['ANTI_ABUSE_MARKET_OPS_DISABLED'] == 'true'
    assert result['PLVR_SERVING_EXCLUSIONS_ENABLED'] == 'true'


@pytest.mark.parametrize('mode', [0o644, 0o444, 0o660, 0o600])
def test_runtime_secret_permissions_fail_closed(tmp_path, mode):
    from services.selfhost_secret_files import runtime_environment, SecretRefused
    directory, _ = synthetic_mount(tmp_path)
    (directory / 'app_database_url').chmod(mode)
    with pytest.raises(SecretRefused, match='secret_metadata_unsafe'):
        runtime_environment(directory, guards(), owner=os.getuid(), gid=os.getgid())


def test_secret_symlinks_parent_symlinks_and_hardlinks_are_refused(tmp_path):
    from services.selfhost_secret_files import read_secret, SecretRefused
    directory, _ = synthetic_mount(tmp_path)
    source = directory / 'app_database_url'
    link = directory / 'linked'
    link.symlink_to(source)
    with pytest.raises(SecretRefused):
        read_secret(directory, 'linked', owner=os.getuid(), gid=os.getgid())
    alias = tmp_path / 'alias'
    alias.symlink_to(directory, target_is_directory=True)
    with pytest.raises(SecretRefused):
        read_secret(alias, 'app_database_url', owner=os.getuid(), gid=os.getgid())
    os.link(source, directory / 'hardlink')
    with pytest.raises(SecretRefused, match='secret_metadata_unsafe'):
        read_secret(directory, 'app_database_url', owner=os.getuid(), gid=os.getgid())


@pytest.mark.parametrize('value', ['', 'synthetic\nINJECT=bad', 'synthetic\x00bad', 'x' * 8193])
def test_invalid_secret_content_is_not_reflected(tmp_path, value):
    from services.selfhost_secret_files import read_secret, SecretRefused
    directory, _ = synthetic_mount(tmp_path)
    p = directory / 'app_database_url'
    p.chmod(0o600); p.write_text(value); p.chmod(0o440)
    with pytest.raises(SecretRefused) as caught:
        read_secret(directory, 'app_database_url', owner=os.getuid(), gid=os.getgid())
    assert str(caught.value) in {'secret_content_invalid', 'secret_metadata_unsafe'}


@pytest.mark.parametrize('name', ['GOOGLE_MAPS_API_KEY', 'PILOT_EVIDENCE_DATABASE_URL',
    'PGOPTIONS', 'PGPASSFILE', 'PGHOSTADDR', 'NEXT_PUBLIC_PILOT_SESSION_SIGNING_KEY',
    'POSTGRES_PASSWORD', 'POSTGRES_PASSWORD_FILE', 'AWS_SECRET_ACCESS_KEY'])
def test_inherited_credentials_and_libpq_authority_are_refused(tmp_path, name):
    from services.selfhost_secret_files import runtime_environment, SecretRefused
    directory, _ = synthetic_mount(tmp_path)
    with pytest.raises(SecretRefused, match='inherited_credential_or_authority'):
        runtime_environment(directory, {**guards(), name: 'synthetic_never_log'}, owner=os.getuid(), gid=os.getgid())


@pytest.mark.parametrize('change', [
    {'ANTI_ABUSE_MARKET_OPS_DISABLED': 'false'}, {'ANTI_ABUSE_PLACES_DISABLED': 'false'},
    {'EARTH_ENGINE_SATELLITE_REFERENCE_V1': 'true'}, {'FEATURE_IDENTITY_V1': 'true'},
    {'PLVR_SERVING_EXCLUSIONS_ENABLED': 'false'},
    {'APP_ENV': 'development'},
])
def test_local_profile_never_enables_paid_or_unready_features(tmp_path, change):
    from services.selfhost_secret_files import runtime_environment, SecretRefused
    directory, _ = synthetic_mount(tmp_path)
    with pytest.raises(SecretRefused, match='local_profile_guard_invalid'):
        runtime_environment(directory, {**guards(), **change}, owner=os.getuid(), gid=os.getgid())


def test_unused_admin_and_optional_secret_mounts_are_refused(tmp_path):
    from services.selfhost_secret_files import runtime_environment, SecretRefused
    directory, _ = synthetic_mount(tmp_path)
    (directory / 'usage_bootstrap_database_url').write_text('synthetic')
    with pytest.raises(SecretRefused, match='unexpected_secret_mount'):
        runtime_environment(directory, guards(), owner=os.getuid(), gid=os.getgid())


@pytest.mark.parametrize('value', ['b' * 48, 'z' * 64])
def test_hmac_contract_is_exactly_64_hex_characters(tmp_path, value):
    from services.selfhost_secret_files import runtime_environment, SecretRefused
    directory, _ = synthetic_mount(tmp_path)
    p = directory / 'usage_peer_hmac_key'
    p.chmod(0o600); p.write_text(value); p.chmod(0o440)
    with pytest.raises(SecretRefused, match='secret_contract_invalid'):
        runtime_environment(directory, guards(), owner=os.getuid(), gid=os.getgid())


@pytest.mark.parametrize('url', [
    'postgresql://postgres:synthetic_password_0123456789@postgres_app/proptech_valuation',
    'postgresql://valuation_runtime:synthetic_password_0123456789@remote.invalid/proptech_valuation',
    'postgresql://valuation_runtime:synthetic_password_0123456789@postgres_app:9999/proptech_valuation',
    'postgresql://valuation_runtime:synthetic_password_0123456789@postgres_app/proptech_valuation?options=unsafe',
])
def test_valuation_url_cannot_change_authority(tmp_path, url):
    from services.selfhost_secret_files import runtime_environment, SecretRefused
    directory, _ = synthetic_mount(tmp_path)
    p = directory / 'valuation_database_url'
    p.chmod(0o600); p.write_text(url); p.chmod(0o440)
    with pytest.raises(SecretRefused, match='secret_contract_invalid'):
        runtime_environment(directory, guards(), owner=os.getuid(), gid=os.getgid())


def test_log_redaction_covers_url_encoding_exceptions_and_access_log_args():
    from services.selfhost_secret_files import install_log_redaction
    secret = 'synthetic/private?credential=123456789'
    output = io.StringIO(); handler = logging.StreamHandler(output)
    logger = logging.getLogger('professor.synthetic'); logger.addHandler(handler)
    logger.setLevel(logging.INFO); logger.propagate = False
    restore = install_log_redaction([secret])
    try:
        logger.info('credential=%s encoded=%s', secret, quote(secret, safe=''))
        try:
            raise ValueError(secret)
        except ValueError:
            logger.exception('sanitized provider failure')
        from uvicorn.logging import AccessFormatter
        record = logging.LogRecord('uvicorn.access', logging.INFO, '', 0, '%s - "%s %s HTTP/%s" %d',
            ('127.0.0.1', 'GET', '/health', '1.1', 200), None)
        AccessFormatter('%(client_addr)s %(request_line)s %(status_code)s', use_colors=False).format(record)
    finally:
        restore(); logger.removeHandler(handler)
    assert secret not in output.getvalue() and quote(secret, safe='') not in output.getvalue()
    assert 'sanitized provider failure' in output.getvalue() and 'Traceback' not in output.getvalue()


def test_encoded_password_fragments_are_redacted_in_all_percent_escape_cases():
    from services.selfhost_secret_files import install_log_redaction
    url = 'postgresql://app_runtime:synthetic%2fprivate%3fpassword_0123456789@postgres_app/proptech_app'
    output = io.StringIO(); handler = logging.StreamHandler(output)
    logger = logging.getLogger('professor.synthetic.percent'); logger.addHandler(handler)
    logger.setLevel(logging.INFO); logger.propagate = False
    restore = install_log_redaction([url])
    variants = ['synthetic%2fprivate%3fpassword_0123456789',
                'synthetic%2Fprivate%3Fpassword_0123456789',
                'synthetic%2fprivate%3Fpassword_0123456789']
    try:
        for value in variants: logger.info('encoded=%s', value)
    finally:
        restore(); logger.removeHandler(handler)
    assert all(value not in output.getvalue() for value in variants)


@pytest.mark.parametrize('name,value', [
    ('pilot_session_signing_key', 'x'*8193),
    ('pilot_session_signing_key', 'x'*40+'\x7f'),
    ('pilot_session_signing_key', '字'*16),
    ('metrics_scrape_token', 'x'*513),
    ('metrics_scrape_token', 'x'*32+' '),
    ('tgos_api_key', 'x'*32+'\n'),
])
def test_installer_rejects_content_the_runtime_cannot_use(name, value):
    from services.selfhost_secret_files import validate_credential, SecretRefused
    with pytest.raises(SecretRefused, match='secret_contract_invalid'):
        validate_credential(name, value)


def test_app_and_usage_authority_matches_legacy_health_contract():
    from services.selfhost_secret_files import validate_credential, SecretRefused
    with pytest.raises(SecretRefused, match='secret_contract_invalid'):
        validate_credential('app_database_url',
            'postgresql://app_runtime:synthetic_password_0123456789@proptech-selfhost-postgres_app-1/proptech_app')


def test_atomic_installer_preserves_existing_and_refuses_link_targets(tmp_path):
    from services.selfhost_secret_files import atomic_secret_write, SecretRefused
    directory = tmp_path / 'private'; directory.mkdir(mode=0o700)
    atomic_secret_write(directory, 'google_maps_api_key', 'synthetic_first', owner=os.getuid(), gid=os.getgid())
    p = directory / 'google_maps_api_key'
    assert p.read_text() == 'synthetic_first' and p.stat().st_mode & 0o777 == 0o600
    with pytest.raises(SecretRefused, match='secret_already_exists'):
        atomic_secret_write(directory, 'google_maps_api_key', 'synthetic_second', owner=os.getuid(), gid=os.getgid())
    assert p.read_text() == 'synthetic_first'
    target = tmp_path / 'outside'; target.write_text('outside_unmodified')
    (directory / 'tgos_api_key').symlink_to(target)
    with pytest.raises(SecretRefused):
        atomic_secret_write(directory, 'tgos_api_key', 'synthetic_second', owner=os.getuid(), gid=os.getgid(), replace=True)
    assert target.read_text() == 'outside_unmodified'


def test_operator_cli_does_not_reflect_accidental_secret_arguments():
    result = subprocess.run([sys.executable, str(ROOT/'scripts/ops/professor_server_secrets.py'),
        'install', 'GOOGLE_MAPS_API_KEY', 'synthetic_must_not_reflect'],
        cwd=ROOT, env={'PATH':os.defpath}, capture_output=True, text=True)
    assert result.returncode != 0
    assert 'synthetic_must_not_reflect' not in result.stdout + result.stderr
    assert json.loads(result.stdout)['status'] == 'refused'


def test_secret_names_in_nonsecret_env_file_are_refused_without_reflection():
    from services.selfhost_secret_files import validate_nonsecret_env, SecretRefused
    validate_nonsecret_env('APP_ENV=preview\nANTI_ABUSE_MARKET_OPS_DISABLED=true\n')
    with pytest.raises(SecretRefused, match='credential_in_configuration'):
        validate_nonsecret_env('GOOGLE_MAPS_API_KEY=synthetic_never_print\n')


@pytest.mark.parametrize('setting', [
    'ANTI_ABUSE_ENFORCEMENT_MODE=local_only\n',
    'TAIPEI_PLANNING_SOURCE_MODE=manual_evidence\n',
])
def test_stage1_supported_mode_identifiers_are_valid_host_configuration(setting):
    # These two names were already inventoried and consumed by the application,
    # but omitted from the smaller hosted-environment manifest/host allowlist.
    from services.selfhost_secret_files import validate_nonsecret_env
    validate_nonsecret_env(setting)


@pytest.mark.parametrize('setting', [
    'ANTI_ABUSE_ENFORCEMENT_MODE=postgres\n',
    'ANTI_ABUSE_ENFORCEMENT_MODE=disabled\n',
    'ANTI_ABUSE_ENFORCEMENT_MODE=\n',
    'TAIPEI_PLANNING_SOURCE_MODE=live_api\n',
    'TAIPEI_PLANNING_SOURCE_MODE=\n',
])
def test_recognized_mode_names_cannot_select_unsupported_runtime_behavior(setting):
    from services.selfhost_secret_files import validate_nonsecret_env, SecretRefused
    with pytest.raises(SecretRefused, match='configuration_guard_invalid'):
        validate_nonsecret_env(setting)


@pytest.mark.parametrize('setting', [
    'UNREVIEWED_CONFIGURATION=synthetic\n',
    'COMPOSE_PROJECT_NAME=another-project\n',
])
def test_mode_fix_does_not_allow_unknown_names_or_new_project_authority(setting):
    from services.selfhost_secret_files import validate_nonsecret_env, SecretRefused
    with pytest.raises(SecretRefused, match='configuration_name_unsupported'):
        validate_nonsecret_env(setting)


@pytest.mark.parametrize('text', ['POSTGRES_SSLMODE=disable\n',
    'PGSSLROOTCERT=/tmp/untrusted\n', 'ANTI_ABUSE_MARKET_OPS_DISABLED=false\n',
    'EARTH_ENGINE_SATELLITE_REFERENCE_V1=true\n'])
def test_nonsecret_configuration_cannot_weaken_security_guards(text):
    from services.selfhost_secret_files import validate_nonsecret_env, SecretRefused
    with pytest.raises(SecretRefused, match='configuration_guard_invalid'):
        validate_nonsecret_env(text)


def test_existing_operator_repository_is_not_required_to_be_root_owned(tmp_path, monkeypatch):
    from scripts.ops import professor_server_secrets as installer
    from types import SimpleNamespace
    monkeypatch.setattr(installer, 'REPO', tmp_path)
    monkeypatch.setattr(installer, 'STORE', Path('/etc/stage2-synthetic-not-created'))
    monkeypatch.setattr(installer, 'STAGING', Path('/run/stage2-synthetic-not-created'))
    monkeypatch.setattr(installer.subprocess, 'run', lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout='tmpfs\n'))
    installer.storage_boundary()


def test_existing_destination_mount_is_checked_before_writing(tmp_path, monkeypatch):
    from scripts.ops import professor_server_secrets as installer
    from services.selfhost_secret_files import SecretRefused
    from types import SimpleNamespace
    monkeypatch.setattr(installer, 'REPO', Path('/usr'))
    monkeypatch.setattr(installer, 'STORE', Path('/etc'))
    monkeypatch.setattr(installer, 'STAGING', Path('/run'))
    def boundary(args, **kwargs):
        return SimpleNamespace(returncode=0, stdout='/dev/sda1\n' if args[-1] == '/etc' else 'tmpfs\n')
    monkeypatch.setattr(installer.subprocess, 'run', boundary)
    with pytest.raises(SecretRefused, match='forbidden_or_unknown_storage'):
        installer.storage_boundary()


def test_operator_bootstrap_install_uses_actual_ops_filename():
    from scripts.ops.professor_server_secrets import credential_spec
    assert credential_spec('API_USAGE_BOOTSTRAP_DATABASE_URL')['secret_file'] == 'usage_bootstrap_database_url'


def test_tls_private_key_validation_is_metadata_only(tmp_path, monkeypatch):
    from services.selfhost_secret_files import validate_tls_key_metadata, SecretRefused
    key = tmp_path/'server.key'; key.write_text('synthetic_not_read'); key.chmod(0o440)
    def never_read(*args, **kwargs):
        pytest.fail('TLS key bytes must not be read by metadata validation')
    monkeypatch.setattr(os, 'read', never_read)
    validate_tls_key_metadata(key, owner=os.getuid(), gid=os.getgid())
    key.chmod(0o644)
    with pytest.raises(SecretRefused, match='tls_metadata_unsafe'):
        validate_tls_key_metadata(key, owner=os.getuid(), gid=os.getgid())


def test_authored_nonsecret_template_is_accepted():
    from services.selfhost_secret_files import validate_nonsecret_env
    validate_nonsecret_env((ROOT/'infra/selfhost/professor-secrets.env.example').read_text())


def test_sanitized_inventory_is_trackable_but_credential_files_are_ignored():
    def ignored(name):
        return subprocess.run(['git', 'check-ignore', '--no-index', '-q', name],
            cwd=ROOT, env={'PATH': os.defpath}).returncode == 0
    assert not ignored('config/professor-server-credentials.json')
    for name in ['private/service-account-prod.json', 'frontend_next/.env.production',
                 'private/application_default_credentials.json', 'private/server.key']:
        assert ignored(name)


def test_composed_api_receives_only_five_core_files_and_keeps_security_boundaries(tmp_path):
    import shutil
    if not shutil.which('docker'):
        pytest.skip('Compose CLI unavailable; no daemon is required')
    runtime = tmp_path/'runtime.env'; runtime.write_text('API_ALLOWED_HOSTS=localhost\n')
    environment = {'PATH':os.defpath,'SELFHOST_SECRETS_DIR':str(tmp_path),
        'SELFHOST_TLS_DIR':str(tmp_path),'SELFHOST_RUNTIME_ENV_FILE':str(runtime),
        'SELFHOST_BACKEND_IMAGE':'backend@sha256:'+'a'*64,
        'SELFHOST_PROXY_IMAGE':'nginx@sha256:'+'b'*64,
        'PROFESSOR_SERVER_API_IMAGE':'professor-stage2@sha256:'+'c'*64}
    # Real secret contents must never be interpolated, even if files exist.
    (tmp_path/'app_database_url').write_text('synthetic_not_in_compose_output')
    drift = tmp_path/'old-override.json'
    drift.write_text(json.dumps({'services':{'api':{'secrets':['legacy_extra']}},
        'secrets':{'legacy_extra':{'file':str(tmp_path/'legacy-extra')}}}))
    result = subprocess.run(['docker','compose','-f','docker-compose.selfhost.yml','-f',str(drift),'-f',
        'infra/selfhost/professor-secrets.override.yml','config','--format','json'],
        cwd=ROOT,env=environment,capture_output=True,text=True,timeout=15)
    assert result.returncode == 0
    assert 'synthetic_not_in_compose_output' not in result.stdout + result.stderr
    model = json.loads(result.stdout); api = model['services']['api']
    assert api['image'] == 'professor-stage2@sha256:'+'c'*64
    assert {v['source'] for v in api['secrets']} == {'app_database_url','usage_database_url','valuation_database_url','usage_peer_hmac_key','pilot_session_signing_key'}
    assert {v['source'] for v in model['services']['postgres_app']['secrets']} == {'app_admin_password'}
    assert {v['source'] for v in model['services']['postgres_usage']['secrets']} == {'usage_admin_password'}
    assert api['environment']['ANTI_ABUSE_MARKET_OPS_DISABLED'] == 'true'
    assert api['environment']['EARTH_ENGINE_SATELLITE_REFERENCE_V1'] == 'false'
    assert not api.get('ports') and not model['services']['postgres_app'].get('ports')
    assert model['services']['reverse_proxy']['ports'][0]['host_ip'] == '127.0.0.1'
    assert model['networks']['app_db']['internal'] and model['networks']['usage_db']['internal']
