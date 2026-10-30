#!/usr/bin/env python3
"""Operator-only credential installation. No Docker/service/database/cloud apply.

Never pass a credential value as an argument. This CLI accepts only a known
variable identifier, an optional protected source filename, and action flags.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import getpass
import hmac
import json
import os
from pathlib import Path
import resource
import secrets
import stat
import subprocess
import sys
import warnings

REPO = Path(__file__).resolve().parents[2]
sys.dont_write_bytecode = True
sys.path.insert(0, str(REPO))
from services.selfhost_secret_files import (
    CORE, DB_FILES, OPS_FILES, SecretRefused, atomic_secret_write, inventory,
    open_directory, read_secret, validate_credential, validate_nonsecret_env, validate_tls_key_metadata,
)

STORE = Path('/etc/proptech-selfhost/secrets')
STAGING = Path('/run/proptech-selfhost/secrets')
GENERATED = {'API_USAGE_PEER_HMAC_KEY', 'PILOT_SESSION_SIGNING_KEY', 'VNEXT_CURSOR_SIGNING_KEY',
             'PILOT_ADMIN_TOKEN', 'PILOT_REVIEW_TOKEN', 'METRICS_SCRAPE_TOKEN',
             'COMMUTE_REFRESH_TOKEN', 'MARKET_READ_MODEL_REFRESH_TOKEN'}


class SafeParser(argparse.ArgumentParser):
    def error(self, message):
        # argparse normally reflects unknown arguments, possibly an accidental key.
        raise SecretRefused('invalid_arguments')


def ensure_private(directory: Path) -> None:
    parent = open_directory(directory.parent)
    try:
        try: os.mkdir(directory.name, 0o700, dir_fd=parent)
        except FileExistsError: pass
    finally:
        os.close(parent)
    os.close(open_directory(directory, private=True))


def check_backing_storage(path: Path) -> None:
    # Check the actual existing destination, including a separate bind mount.
    # For a new target inspect its nearest existing parent before any write.
    while not path.exists() and path != path.parent:
        path = path.parent
    result = subprocess.run(['findmnt', '-rn', '-o', 'SOURCE', '--target', str(path)],
        env={'PATH': os.defpath}, capture_output=True, text=True, timeout=10)
    source = result.stdout.strip().split('[', 1)[0]
    if (result.returncode or not source or source.startswith('/dev/sda')
            or source.startswith('/dev/') and os.path.realpath(source).startswith('/dev/sda')):
        raise SecretRefused('forbidden_or_unknown_storage')


def storage_boundary() -> None:
    for path in [STORE, STAGING]:
        existing = path
        while not existing.exists() and existing != existing.parent:
            existing = existing.parent
        os.close(open_directory(existing))
        check_backing_storage(path)
    # The operator's reviewed checkout is intentionally owned by the operator.
    # No credential is written there; only its backing-device metadata is read.
    check_backing_storage(REPO)


def hidden_input(prompt: str) -> str:
    if not sys.stdin.isatty() or not sys.stderr.isatty():
        raise SecretRefused('interactive_tty_required')
    with warnings.catch_warnings():
        warnings.simplefilter('error', getpass.GetPassWarning)
        try: return getpass.getpass(prompt)
        except (getpass.GetPassWarning, EOFError):
            raise SecretRefused('interactive_tty_required') from None


def credential_spec(name: str) -> dict:
    result = next((row for row in inventory()['credentials'] if row['name'] == name), None)
    if not result or not result['secret_file'] or result['classification'] not in {'secret', 'credential_file', 'public_client_credential'}:
        raise SecretRefused('credential_not_installable')
    return result


def import_file(path: Path, *, multiline: bool) -> str:
    if (not path.is_absolute() or '..' in path.parts or path.is_relative_to(REPO)
            or str(path).startswith(('/dev/', '/run/media/andy/Crucial X9/'))):
        raise SecretRefused('import_path_unsafe')
    check_backing_storage(path)
    info = path.lstat()
    operator_uid = int(os.environ.get('SUDO_UID', '0'))
    if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_uid not in {0, operator_uid}
            or stat.S_IMODE(info.st_mode) not in {0o400, 0o600}):
        raise SecretRefused('import_file_unsafe')
    return read_secret(path.parent, path.name, owner=info.st_uid, gid=None,
        mode=stat.S_IMODE(info.st_mode), limit=1024*1024 if multiline else 8192, multiline=multiline)


def put_credential(name: str, value: str, *, replace: bool = False) -> None:
    value = validate_credential(name, value)
    ensure_private(STORE)
    if replace:
        # Explicit replacement keeps a protected old copy; neither value is shown.
        old_path = STORE / name
        try: old_path.lstat()
        except FileNotFoundError: pass
        else:
            old = read_secret(STORE, name, gid=0, mode=0o600,
                limit=1024*1024 if name == 'earth_engine_adc_json' else 8192,
                multiline=name == 'earth_engine_adc_json')
            backup = STORE / 'backups'; ensure_private(backup)
            suffix = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + secrets.token_hex(4)
            atomic_secret_write(backup, name + '-' + suffix, old)
    atomic_secret_write(STORE, name, value, replace=replace)


def adopt_existing() -> dict:
    ensure_private(STORE)
    # Validate the complete mandatory population before writing any new file.
    values = {name: validate_credential(name, read_secret(STAGING, name, gid=None, mode=None))
              for name in (*CORE, *DB_FILES)}
    for name in OPS_FILES:
        try: (STAGING/name).lstat()
        except FileNotFoundError: continue
        values[name] = read_secret(STAGING, name, gid=None, mode=None)
    pending = {}
    for name, value in values.items():
        try: (STORE/name).lstat()
        except FileNotFoundError:
            pending[name] = value
        else:
            existing = read_secret(STORE, name, gid=0, mode=0o600)
            if not hmac.compare_digest(value.encode('utf-8'), existing.encode('utf-8')):
                raise SecretRefused('existing_secret_conflict')
    for name, value in pending.items(): atomic_secret_write(STORE, name, value)
    return {'status': 'pass', 'operation': 'adopt-existing', 'values_preserved': True,
            'runtime_files_changed': False, 'credential_values_returned': False}


def stage_runtime(*, ops: bool = False) -> dict:
    names = (*CORE, *DB_FILES, *(OPS_FILES if ops else ()))
    values = {name: validate_credential(name, read_secret(STORE, name, gid=0, mode=0o600)) for name in names}
    # /run is volatile. Recreate only our root-owned parent after reboot,
    # preserving an existing safe root-owned parent's permissions.
    parent = open_directory(STAGING.parent.parent)
    try:
        try: os.mkdir(STAGING.parent.name, 0o700, dir_fd=parent)
        except FileExistsError: pass
    finally:
        os.close(parent)
    os.close(open_directory(STAGING.parent))
    ensure_private(STAGING)
    for name, value in values.items():
        atomic_secret_write(STAGING, name, value, gid=70 if name in DB_FILES else 10001,
                            mode=0o440, replace=True)
    return {'status': 'pass', 'operation': 'stage', 'staged_files': len(names),
            'services_recreated': False, 'note': 'existing_container_file_binds_require_controlled_recreation'}


def configuration_check(path: Path) -> None:
    # Configuration is read only by this operator-run validator, never by Codex.
    parent = open_directory(path.parent)
    fd = None
    try:
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_nlink != 1
                or stat.S_IMODE(info.st_mode) not in {0o600, 0o640} or info.st_size > 262144):
            raise SecretRefused('configuration_metadata_unsafe')
        with os.fdopen(fd, 'rb') as stream:
            fd = None; text = stream.read(262145).decode('utf-8')
        if len(text.encode()) > 262144: raise SecretRefused('configuration_metadata_unsafe')
        validate_nonsecret_env(text)
    finally:
        if fd is not None: os.close(fd)
        os.close(parent)


def validate_host() -> dict:
    os.close(open_directory(STORE, private=True)); os.close(open_directory(STAGING, private=True))
    for name in (*CORE, *DB_FILES):
        stored = validate_credential(name, read_secret(STORE, name, gid=0, mode=0o600))
        staged = validate_credential(name, read_secret(STAGING, name, gid=70 if name in DB_FILES else 10001))
        if not hmac.compare_digest(stored.encode('utf-8'), staged.encode('utf-8')):
            raise SecretRefused('staged_secret_mismatch')
    configuration_check(Path('/etc/proptech-selfhost/runtime.env'))
    configuration_check(Path('/etc/proptech-selfhost/compose.env'))
    for kind in ('app', 'usage'):
        validate_tls_key_metadata(Path('/run/proptech-selfhost/tls')/kind/'server.key')
    ca_key = Path('/run/proptech-selfhost/tls/ca.key')
    if ca_key.exists(): validate_tls_key_metadata(ca_key, gid=0, modes=(0o600,))
    return {'status': 'pass', 'operation': 'validate-host', 'root_owned_files': True,
            'least_privilege_modes': True, 'nonsecret_configuration': True,
            'tls_key_metadata_valid': True, 'tls_key_contents_read': False,
            'provider_calls': 0, 'live_stage2_activation_certified': False}


def main(argv=None) -> int:
    try:
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0)); os.umask(0o077)
        parser = SafeParser(description=__doc__)
        parser.add_argument('operation', choices=('inventory', 'adopt-existing', 'install', 'generate', 'stage', 'validate-host'))
        parser.add_argument('name', nargs='?')
        parser.add_argument('--from-file', type=Path)
        parser.add_argument('--replace', action='store_true')
        parser.add_argument('--ops', action='store_true')
        args = parser.parse_args(argv)
        if args.operation == 'inventory':
            if args.name or args.from_file or args.replace or args.ops: raise SecretRefused('invalid_arguments')
            print(json.dumps(inventory())); return 0
        if os.geteuid() != 0: raise SecretRefused('operator_root_required')
        if args.operation in {'install', 'generate'}:
            spec = credential_spec(args.name)
            if args.ops or args.operation == 'generate' and (args.from_file or args.name not in GENERATED):
                raise SecretRefused('invalid_arguments')
            if args.replace and hidden_input('Confirm replacement with REPLACE (hidden): ') != 'REPLACE':
                raise SecretRefused('replacement_not_confirmed')
            storage_boundary()
            if args.operation == 'generate':
                value = secrets.token_hex(32) if args.name == 'API_USAGE_PEER_HMAC_KEY' else secrets.token_urlsafe(48)
            elif args.from_file:
                value = import_file(args.from_file, multiline=spec['classification'] == 'credential_file')
            else:
                if spec['classification'] == 'credential_file': raise SecretRefused('protected_import_file_required')
                value = hidden_input('Enter ' + args.name + ' (hidden): ')
            put_credential(spec['secret_file'], value, replace=args.replace)
            result = {'status': 'pass', 'operation': args.operation, 'credential': args.name,
                      'stored_only': True, 'mounted_or_enabled': False}
        else:
            if args.name or args.from_file or args.replace or args.ops and args.operation != 'stage': raise SecretRefused('invalid_arguments')
            storage_boundary()
            result = (adopt_existing() if args.operation == 'adopt-existing' else
                      stage_runtime(ops=args.ops) if args.operation == 'stage' else validate_host())
        print(json.dumps(result)); return 0
    except SecretRefused as error:
        print(json.dumps({'status': 'refused', 'reason_code': str(error)})); return 1
    except (Exception, KeyboardInterrupt):
        print(json.dumps({'status': 'refused', 'reason_code': 'operation_failed_details_suppressed'})); return 1


if __name__ == '__main__':
    raise SystemExit(main())
