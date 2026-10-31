"""Unprivileged installer regressions using disposable synthetic files only.

Only the helper owner/group boundary is adapted to the current user. Secret
parsing, filesystem writes, modes, backups, and replacement remain real.
"""
from __future__ import annotations

import io
import json
import os
import shutil
import stat
from types import SimpleNamespace

import pytest


@pytest.fixture
def synthetic_operator(tmp_path, monkeypatch):
    from scripts.ops import professor_server_secrets as installer
    from services import selfhost_secret_files as secret_files

    if os.geteuid() == 0:
        pytest.skip('Installer fixtures must run without root privileges')
    owner, group = os.getuid(), os.getgid()
    store = tmp_path / 'persistent' / 'secrets'
    staging = tmp_path / 'volatile' / 'secrets'
    store.parent.mkdir(mode=0o700)
    staging.parent.mkdir(mode=0o700)
    staging.mkdir(mode=0o700)
    values = {
        'app_database_url': 'postgresql://app_runtime:synthetic_password_0123456789@postgres_app/proptech_app',
        'usage_database_url': 'postgresql://proptech_usage_runtime_v1:synthetic_password_0123456789@postgres_usage/proptech_api_usage',
        'valuation_database_url': 'postgresql://valuation_runtime:synthetic_password_0123456789@postgres_app/proptech_valuation',
        'usage_peer_hmac_key': 'a' * 64,
        'pilot_session_signing_key': 'synthetic_session_signing_material_0123456789',
        'app_admin_password': 'synthetic_app_admin_password_0123456789',
        'app_runtime_password': 'synthetic_app_runtime_password_0123456789',
        'usage_admin_password': 'synthetic_usage_admin_password_0123456789',
        'usage_migration_password': 'synthetic_migration_password_0123456789',
        'usage_bootstrap_database_url': 'postgresql://usage_migration:synthetic_password_0123456789@postgres_usage/proptech_api_usage',
        'usage_runtime_password': 'synthetic_usage_runtime_password_0123456789',
    }
    for name, value in values.items():
        path = staging / name
        path.write_text(value, encoding='utf-8')
        path.chmod(0o440)

    real_read = secret_files.read_secret
    real_write = secret_files.atomic_secret_write
    real_open = secret_files.open_directory
    requested_writes = []

    def read(directory, name, **kwargs):
        kwargs.update(owner=owner, gid=group)
        return real_read(directory, name, **kwargs)

    def write(directory, name, value, **kwargs):
        requested_writes.append((name, kwargs.get('gid', 0), kwargs.get('mode', 0o600)))
        kwargs.update(owner=owner, gid=group)
        return real_write(directory, name, value, **kwargs)

    def open_directory(directory, **kwargs):
        kwargs['owner'] = owner
        return real_open(directory, **kwargs)

    monkeypatch.setattr(installer, 'STORE', store)
    monkeypatch.setattr(installer, 'STAGING', staging)
    monkeypatch.setattr(installer, 'read_secret', read)
    monkeypatch.setattr(installer, 'atomic_secret_write', write)
    monkeypatch.setattr(installer, 'open_directory', open_directory)
    return SimpleNamespace(
        installer=installer, secret_files=secret_files, store=store, staging=staging,
        values=values, writes=requested_writes, owner=owner, group=group,
    )


def test_app_username_must_match_the_health_check_contract():
    from services.selfhost_secret_files import SecretRefused, validate_credential

    with pytest.raises(SecretRefused, match='secret_contract_invalid'):
        validate_credential('app_database_url',
            'postgresql://%61pp_runtime:synthetic_password_0123456789@postgres_app/proptech_app')


def test_stage_recreates_the_volatile_parent_after_reboot(synthetic_operator):
    fixture = synthetic_operator
    fixture.installer.adopt_existing()
    shutil.rmtree(fixture.staging.parent)

    result = fixture.installer.stage_runtime()

    assert result['status'] == 'pass'
    assert stat.S_IMODE(fixture.staging.parent.stat().st_mode) == 0o700
    assert (fixture.staging / 'usage_peer_hmac_key').read_text() == 'a' * 64


def test_repeat_adoption_accepts_valid_unicode_credentials(synthetic_operator):
    fixture = synthetic_operator
    key = fixture.staging / 'pilot_session_signing_key'
    key.chmod(0o600)
    key.write_text('字' * 32, encoding='utf-8')
    key.chmod(0o440)
    fixture.installer.adopt_existing()
    original_inode = (fixture.store / key.name).stat().st_ino

    result = fixture.installer.adopt_existing()

    assert result['status'] == 'pass'
    assert (fixture.store / key.name).stat().st_ino == original_inode
    assert (fixture.store / key.name).read_text(encoding='utf-8') == '字' * 32


def test_adoption_preserves_values_runtime_inodes_and_private_metadata(synthetic_operator, capsys):
    fixture = synthetic_operator
    original_inodes = {name: (fixture.staging / name).stat().st_ino for name in fixture.values}

    result = fixture.installer.adopt_existing()

    assert result['values_preserved'] is True
    assert result['runtime_files_changed'] is False
    assert stat.S_IMODE(fixture.store.stat().st_mode) == 0o700
    for name, value in fixture.values.items():
        stored = fixture.store / name
        assert stored.read_text(encoding='utf-8') == value
        assert stat.S_IMODE(stored.stat().st_mode) == 0o600
        assert stored.stat().st_uid == fixture.owner
        assert stored.stat().st_nlink == 1
        assert (fixture.staging / name).stat().st_ino == original_inodes[name]
    diagnostic = json.dumps(result) + capsys.readouterr().out
    assert all(value not in diagnostic for value in fixture.values.values())


def test_repeat_adoption_leaves_persistent_files_unchanged(synthetic_operator):
    fixture = synthetic_operator
    fixture.installer.adopt_existing()
    before = {name: (fixture.store / name).stat().st_ino for name in fixture.values}

    fixture.installer.adopt_existing()

    assert {name: (fixture.store / name).stat().st_ino for name in fixture.values} == before


def test_adoption_conflict_does_not_write_any_persistent_file(synthetic_operator):
    fixture = synthetic_operator
    fixture.installer.adopt_existing()
    before = {name: (fixture.store / name).read_text() for name in fixture.values}
    key = fixture.staging / 'usage_peer_hmac_key'
    key.chmod(0o600)
    key.write_text('b' * 64)
    key.chmod(0o440)

    with pytest.raises(fixture.secret_files.SecretRefused, match='existing_secret_conflict'):
        fixture.installer.adopt_existing()

    assert {name: (fixture.store / name).read_text() for name in fixture.values} == before


def test_install_never_overwrites_an_existing_value_by_default(synthetic_operator):
    fixture = synthetic_operator
    fixture.installer.put_credential('google_maps_api_key', 'synthetic_first_provider_key_0123456789')
    target = fixture.store / 'google_maps_api_key'
    original_inode = target.stat().st_ino

    with pytest.raises(fixture.secret_files.SecretRefused, match='secret_already_exists'):
        fixture.installer.put_credential('google_maps_api_key', 'synthetic_second_provider_key_0123456789')

    assert target.read_text() == 'synthetic_first_provider_key_0123456789'
    assert target.stat().st_ino == original_inode
    assert not (fixture.store / 'backups').exists()


def test_explicit_replacement_keeps_a_private_backup(synthetic_operator):
    fixture = synthetic_operator
    fixture.installer.put_credential('google_maps_api_key', 'synthetic_first_provider_key_0123456789')

    fixture.installer.put_credential('google_maps_api_key',
        'synthetic_second_provider_key_0123456789', replace=True)

    assert (fixture.store / 'google_maps_api_key').read_text() == 'synthetic_second_provider_key_0123456789'
    backups = list((fixture.store / 'backups').iterdir())
    assert len(backups) == 1
    assert backups[0].read_text() == 'synthetic_first_provider_key_0123456789'
    assert stat.S_IMODE(backups[0].stat().st_mode) == 0o600
    assert stat.S_IMODE(backups[0].parent.stat().st_mode) == 0o700


def test_invalid_replacement_preserves_the_target_without_creating_a_backup(synthetic_operator):
    fixture = synthetic_operator
    fixture.installer.put_credential('pilot_session_signing_key',
        'synthetic_first_session_signing_key_0123456789')

    with pytest.raises(fixture.secret_files.SecretRefused, match='secret_contract_invalid'):
        fixture.installer.put_credential('pilot_session_signing_key', 'x' * 8193, replace=True)

    assert (fixture.store / 'pilot_session_signing_key').read_text() == 'synthetic_first_session_signing_key_0123456789'
    assert not (fixture.store / 'backups').exists()


def test_default_staging_restores_nine_files_with_consumer_groups(synthetic_operator):
    fixture = synthetic_operator
    fixture.installer.adopt_existing()
    fixture.installer.put_credential('google_maps_api_key', 'synthetic_unmounted_provider_key_0123456789')
    shutil.rmtree(fixture.staging)
    fixture.writes.clear()

    result = fixture.installer.stage_runtime()

    expected_groups = {
        'app_database_url': 10001,
        'usage_database_url': 10001,
        'valuation_database_url': 10001,
        'usage_peer_hmac_key': 10001,
        'pilot_session_signing_key': 10001,
        'app_admin_password': 70,
        'app_runtime_password': 70,
        'usage_admin_password': 70,
        'usage_migration_password': 70,
    }
    assert result['staged_files'] == 9
    assert result['services_recreated'] is False
    assert {path.name for path in fixture.staging.iterdir()} == set(expected_groups)
    assert {name: group for name, group, _ in fixture.writes} == expected_groups
    assert all(mode == 0o440 for _, _, mode in fixture.writes)
    for name in expected_groups:
        path = fixture.staging / name
        assert path.read_text() == fixture.values[name]
        assert stat.S_IMODE(path.stat().st_mode) == 0o440
    assert not (fixture.staging / 'google_maps_api_key').exists()


def test_explicit_ops_staging_adds_only_the_two_ops_credentials(synthetic_operator):
    fixture = synthetic_operator
    fixture.installer.adopt_existing()
    shutil.rmtree(fixture.staging)
    fixture.writes.clear()

    result = fixture.installer.stage_runtime(ops=True)

    assert result['staged_files'] == 11
    assert {path.name for path in fixture.staging.iterdir()} == set(fixture.values)
    for name in ('usage_bootstrap_database_url', 'usage_runtime_password'):
        assert (fixture.staging / name).read_text() == fixture.values[name]
        assert (name, 10001, 0o440) in fixture.writes


def test_protected_operator_file_can_be_imported(synthetic_operator, tmp_path, monkeypatch):
    fixture = synthetic_operator
    directory = tmp_path / 'operator-input'
    directory.mkdir(mode=0o700)
    source = directory / 'synthetic-provider-input'
    source.write_text('synthetic_imported_provider_key_0123456789')
    source.chmod(0o600)
    monkeypatch.setattr(fixture.installer.os, 'environ', {'SUDO_UID': str(fixture.owner)})
    monkeypatch.setattr(fixture.installer, 'check_backing_storage', lambda path: None)

    value = fixture.installer.import_file(source, multiline=False)
    fixture.installer.put_credential('google_maps_api_key', value)

    assert (fixture.store / 'google_maps_api_key').read_text() == 'synthetic_imported_provider_key_0123456789'
    assert not (fixture.staging / 'google_maps_api_key').exists()


@pytest.mark.parametrize('kind', ['permissive', 'symlink', 'hardlink'])
def test_unsafe_import_files_are_refused(synthetic_operator, tmp_path, monkeypatch, kind):
    fixture = synthetic_operator
    directory = tmp_path / 'operator-input'
    directory.mkdir(mode=0o700)
    source = directory / 'synthetic-provider-input'
    source.write_text('synthetic_imported_provider_key_0123456789')
    source.chmod(0o600)
    candidate = source
    if kind == 'permissive':
        source.chmod(0o644)
    elif kind == 'symlink':
        candidate = directory / 'synthetic-link'
        candidate.symlink_to(source)
    else:
        os.link(source, directory / 'synthetic-hardlink')
    monkeypatch.setattr(fixture.installer.os, 'environ', {'SUDO_UID': str(fixture.owner)})
    monkeypatch.setattr(fixture.installer, 'check_backing_storage', lambda path: None)

    with pytest.raises(fixture.secret_files.SecretRefused, match='import_file_unsafe'):
        fixture.installer.import_file(candidate, multiline=False)

    assert source.read_text() == 'synthetic_imported_provider_key_0123456789'
    assert not fixture.store.exists()


def test_hidden_input_refuses_non_tty_streams(synthetic_operator, monkeypatch):
    fixture = synthetic_operator
    monkeypatch.setattr(fixture.installer.sys, 'stdin', io.StringIO('synthetic_not_an_argument'))

    with pytest.raises(fixture.secret_files.SecretRefused, match='interactive_tty_required'):
        fixture.installer.hidden_input('Synthetic credential: ')


def test_hidden_tty_input_returns_the_value_without_printing_it(synthetic_operator, monkeypatch, capsys):
    fixture = synthetic_operator

    class SyntheticTTY(io.StringIO):
        def isatty(self):
            return True

    input_stream, error_stream = SyntheticTTY(), SyntheticTTY()
    monkeypatch.setattr(fixture.installer.sys, 'stdin', input_stream)
    monkeypatch.setattr(fixture.installer.sys, 'stderr', error_stream)
    monkeypatch.setattr(fixture.installer.getpass, 'getpass',
        lambda prompt: 'synthetic_hidden_provider_key_0123456789')

    value = fixture.installer.hidden_input('Enter GOOGLE_MAPS_API_KEY (hidden): ')

    assert value == 'synthetic_hidden_provider_key_0123456789'
    assert input_stream.getvalue() == error_stream.getvalue() == ''
    assert capsys.readouterr().out == ''


def test_atomic_replace_failure_preserves_the_old_file_and_cleans_temporary_files(tmp_path, monkeypatch):
    from services import selfhost_secret_files as secret_files

    if os.geteuid() == 0:
        pytest.skip('Installer fixtures must run without root privileges')
    directory = tmp_path / 'private'
    directory.mkdir(mode=0o700)
    target = directory / 'synthetic_key'
    target.write_text('synthetic_old_value')
    target.chmod(0o600)
    original_inode = target.stat().st_ino

    def fail_replace(*args, **kwargs):
        raise OSError('synthetic replacement failure')

    monkeypatch.setattr(secret_files.os, 'replace', fail_replace)
    with pytest.raises(secret_files.SecretRefused, match='secret_write_failed'):
        secret_files.atomic_secret_write(directory, target.name, 'synthetic_new_value',
            owner=os.getuid(), gid=os.getgid(), replace=True)

    assert target.read_text() == 'synthetic_old_value'
    assert target.stat().st_ino == original_inode
    assert {path.name for path in directory.iterdir()} == {'synthetic_key'}


def test_host_validation_refuses_a_valid_but_different_staged_key(synthetic_operator, monkeypatch):
    fixture = synthetic_operator
    fixture.installer.adopt_existing()
    fixture.installer.stage_runtime()
    key = fixture.staging / 'usage_peer_hmac_key'
    key.chmod(0o600)
    key.write_text('b' * 64)
    key.chmod(0o440)
    # Actual configuration remains forbidden; only the synthetic credential
    # equality boundary is under review here.
    monkeypatch.setattr(fixture.installer, 'configuration_check', lambda path: None)

    with pytest.raises(fixture.secret_files.SecretRefused, match='staged_secret_mismatch'):
        fixture.installer.validate_host()
