"""Professor local-profile credential boundary; never return values in diagnostics.

Only operator installation and application startup consume credential bytes.
The agent tests these interfaces exclusively with disposable synthetic fixtures.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
import re
import secrets
import stat
from urllib.parse import parse_qsl, quote, quote_plus, unquote, urlencode, urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / 'config/professor-server-credentials.json'
CORE = {
    'app_database_url': 'DATABASE_URL',
    'usage_database_url': 'API_USAGE_DATABASE_URL',
    'valuation_database_url': 'VALUATION_DATABASE_URL',
    'usage_peer_hmac_key': 'API_USAGE_PEER_HMAC_KEY',
    'pilot_session_signing_key': 'PILOT_SESSION_SIGNING_KEY',
}
DB_FILES = ('app_admin_password', 'app_runtime_password', 'usage_admin_password', 'usage_migration_password')
OPS_FILES = ('usage_bootstrap_database_url', 'usage_runtime_password')
DISABLED = ('MARKET_OPS', 'GEOCODING', 'PLACES', 'ROUTES', 'SATELLITE', 'LOCATION',
            'PARCEL', 'ARDSWC', 'LIQUEFACTION', 'NLSC', 'TGOS')
OFF_FEATURES = ('FEATURE_IDENTITY_V1', 'FEATURE_LEGACY_CASE_IMPORT_V1',
                'FEATURE_CASE_PARCEL_SET_V1', 'TAIPEI_PLANNING_READ_V1')
CA = '/run/selfhost-ca/ca.crt'


class SecretRefused(Exception):
    """Only fixed application reason codes are accepted at call sites."""


def inventory() -> dict:
    return json.loads(INVENTORY.read_text())


def credential_names() -> set[str]:
    return {row['name'] for row in inventory()['credentials']
            if row['classification'] in {'secret', 'credential_file', 'unsupported', 'internal_ephemeral', 'file_reference'}}


def sensitive_name(name: str) -> bool:
    return name in credential_names() or bool(re.search(
        r'(?:_API_KEY|_ACCESS_KEY_ID|_SECRET_ACCESS_KEY|_PASSWORD|_TOKEN|_SIGNING_KEY|_CREDENTIALS|_PRIVATE_KEY)$', name))


def _filename(name: str) -> None:
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}', name) or name in {'.', '..'}:
        raise SecretRefused('secret_name_invalid')


def open_directory(path: Path, *, owner: int = 0, private: bool = False) -> int:
    """Pin each directory component, refusing symlinks and unsafe ownership."""
    if not path.is_absolute() or '..' in path.parts or str(path).startswith('/dev/sda'):
        raise SecretRefused('secret_directory_unsafe')
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
    try:
        for component in path.parts[1:]:
            new = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd); fd = new
            info = os.fstat(fd)
            sticky_root = info.st_uid == 0 and bool(info.st_mode & stat.S_ISVTX)
            if info.st_uid not in {0, owner} or info.st_mode & 0o022 and not sticky_root:
                raise SecretRefused('secret_directory_unsafe')
        info = os.fstat(fd)
        if info.st_uid != owner or private and stat.S_IMODE(info.st_mode) != 0o700:
            raise SecretRefused('secret_directory_unsafe')
        return fd
    except (OSError, SecretRefused):
        os.close(fd)
        raise SecretRefused('secret_directory_unsafe') from None


def read_secret(directory: Path, name: str, *, owner: int = 0,
                gid: int | None = 10001, mode: int | None = 0o440,
                limit: int = 8192, multiline: bool = False) -> str:
    _filename(name)
    parent = open_directory(directory, owner=owner)
    fd = None
    try:
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        before = os.fstat(fd)
        if (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_uid != owner
                or gid is not None and before.st_gid != gid
                or mode is not None and stat.S_IMODE(before.st_mode) != mode
                or mode is None and before.st_mode & 0o022
                or not 0 < before.st_size <= limit):
            raise SecretRefused('secret_metadata_unsafe')
        with os.fdopen(fd, 'rb') as stream:
            fd = None
            raw = stream.read(limit + 1)
            after = os.fstat(stream.fileno())
        if (before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (after.st_size, after.st_mtime_ns, after.st_ctime_ns):
            raise SecretRefused('secret_changed_during_read')
        value = raw.decode('utf-8').removesuffix('\n').removesuffix('\r')
        if (len(raw) > limit or not value or value != value.strip()
                or '\x00' in value or not multiline and any(ord(c) < 32 or ord(c) == 127 for c in value)):
            raise SecretRefused('secret_content_invalid')
        return value
    except (OSError, UnicodeError):
        raise SecretRefused('secret_unreadable') from None
    finally:
        if fd is not None: os.close(fd)
        os.close(parent)


def atomic_secret_write(directory: Path, name: str, value: str, *, owner: int = 0,
                        gid: int = 0, mode: int = 0o600, replace: bool = False) -> None:
    _filename(name)
    parent = open_directory(directory, owner=owner, private=True)
    temporary = '.install-' + secrets.token_hex(16)
    fd = None
    try:
        try:
            existing = os.stat(name, dir_fd=parent, follow_symlinks=False)
        except FileNotFoundError:
            existing = None
        if existing:
            if not stat.S_ISREG(existing.st_mode) or existing.st_nlink != 1 or existing.st_uid != owner:
                raise SecretRefused('secret_metadata_unsafe')
            if not replace: raise SecretRefused('secret_already_exists')
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=parent)
        os.fchown(fd, owner, gid); os.fchmod(fd, mode)
        with os.fdopen(fd, 'wb') as stream:
            fd = None
            stream.write(value.encode('utf-8')); stream.flush(); os.fsync(stream.fileno())
        if replace:
            os.replace(temporary, name, src_dir_fd=parent, dst_dir_fd=parent)
        else:
            os.link(temporary, name, src_dir_fd=parent, dst_dir_fd=parent, follow_symlinks=False)
        os.fsync(parent)
    except FileExistsError:
        raise SecretRefused('secret_already_exists') from None
    except OSError:
        raise SecretRefused('secret_write_failed') from None
    finally:
        if fd is not None: os.close(fd)
        try: os.unlink(temporary, dir_fd=parent)
        except FileNotFoundError: pass
        os.close(parent)


def validate_tls_key_metadata(path: Path, *, owner: int = 0, gid: int = 70,
                              modes: tuple[int, ...] = (0o440, 0o640)) -> None:
    """Validate an existing TLS key without opening it for content access."""
    parent = open_directory(path.parent, owner=owner)
    fd = None
    try:
        fd = os.open(path.name, os.O_PATH | os.O_NOFOLLOW, dir_fd=parent)
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_uid != owner
                or info.st_gid != gid or stat.S_IMODE(info.st_mode) not in modes):
            raise SecretRefused('tls_metadata_unsafe')
    except OSError:
        raise SecretRefused('tls_metadata_unsafe') from None
    finally:
        if fd is not None: os.close(fd)
        os.close(parent)


def validate_credential(name: str, value: str) -> str:
    """Validate shape/authority only; never connect to any provider/database."""
    limit = 1024*1024 if name == 'earth_engine_adc_json' else 8192
    if (not isinstance(value, str) or not value or len(value.encode('utf-8')) > limit
            or value != value.strip() or '\x00' in value
            or name != 'earth_engine_adc_json' and any(ord(c) < 32 or ord(c) == 127 for c in value)):
        raise SecretRefused('secret_contract_invalid')
    if name in CORE and name.endswith('_database_url'):
        role, host, db = {
            'app_database_url': ('app_runtime', 'postgres_app', 'proptech_app'),
            'usage_database_url': ('proptech_usage_runtime_v1', 'postgres_usage', 'proptech_api_usage'),
            'valuation_database_url': ('valuation_runtime', 'postgres_app', 'proptech_valuation'),
        }[name]
        try:
            p = urlsplit(value)
            query = parse_qsl(p.query, keep_blank_values=True, strict_parsing=True)
            allowed = {'sslmode': {'require', 'verify-full'}, 'sslrootcert': {CA}}
            hosts = {host, 'proptech-selfhost-' + host + '-1'} if name == 'valuation_database_url' else {host}
            valid = (p.scheme in {'postgres', 'postgresql'} and p.username == role
                and p.hostname in hosts and p.path == '/' + db
                and p.port in {None, 5432} and len(unquote(p.password or '')) >= 16
                and not p.fragment and len({k for k, _ in query}) == len(query)
                and all(k in allowed and v in allowed[k] for k, v in query))
            if name != 'valuation_database_url' and query: valid = False
            if not valid: raise ValueError()
        except (ValueError, UnicodeError):
            raise SecretRefused('secret_contract_invalid') from None
    elif name == 'usage_peer_hmac_key':
        if not re.fullmatch(r'[0-9a-fA-F]{64}', value): raise SecretRefused('secret_contract_invalid')
    elif name == 'metrics_scrape_token':
        from services.metrics import valid_scrape_token
        if not valid_scrape_token(value): raise SecretRefused('secret_contract_invalid')
    elif name in {'pilot_session_signing_key', 'pilot_admin_token', 'pilot_review_token',
                  'commute_refresh_token', 'market_read_model_refresh_token'}:
        if len(value) < 32: raise SecretRefused('secret_contract_invalid')
    elif name == 'vnext_cursor_signing_key':
        if len(value.encode()) < 32: raise SecretRefused('secret_contract_invalid')
    elif name == 'earth_engine_adc_json':
        from services.earth_engine_adc import validate_keyless_adc
        try:
            validate_keyless_adc(value)
        except ValueError:
            raise SecretRefused('earth_engine_adc_contract_invalid') from None
    elif not value or value != value.strip() or any(ord(c) < 32 for c in value):
        raise SecretRefused('secret_contract_invalid')
    return value


def validate_local_guards(environ: dict[str, str]) -> None:
    if (environ.get('APP_ENV') != 'preview'
            or any(environ.get('ANTI_ABUSE_' + key + '_DISABLED', '').lower() != 'true' for key in DISABLED)
            or environ.get('EARTH_ENGINE_SATELLITE_REFERENCE_V1', '').lower() != 'false'
            or environ.get('PLVR_SERVING_EXCLUSIONS_ENABLED', '').lower() != 'true'
            or any(environ.get(key, 'false').lower() not in {'false', '0'} for key in OFF_FEATURES)
            or environ.get('PLVR_DATA_BACKEND', 'blue') != 'blue'
            or environ.get('VALUATION_DEMO_MODE', 'false').lower() != 'false'
            or environ.get('WRA_FLOOD_LOCAL_ROOT') != '/srv/proptech/datasets/wra/flood/v1'):
        raise SecretRefused('local_profile_guard_invalid')


def runtime_environment(directory: Path, environ: dict[str, str], *, owner: int = 0, gid: int = 10001) -> dict[str, str]:
    for name in environ:
        if (sensitive_name(name) or name.startswith('NEXT_PUBLIC_')
                or name.startswith('PG') and not (name == 'PGSSLROOTCERT' and environ[name] == CA)):
            raise SecretRefused('inherited_credential_or_authority')
    validate_local_guards(environ)
    parent = open_directory(directory, owner=owner)
    try:
        if set(os.listdir(parent)) != set(CORE): raise SecretRefused('unexpected_secret_mount')
    finally:
        os.close(parent)
    values = {env: validate_credential(name, read_secret(directory, name, owner=owner, gid=gid))
              for name, env in CORE.items()}
    result = dict(environ)
    result.update(values)
    p = urlsplit(values['VALUATION_DATABASE_URL'])
    result['VALUATION_DATABASE_URL'] = urlunsplit((p.scheme, p.netloc, p.path,
        urlencode({'sslmode': 'verify-full', 'sslrootcert': CA}), ''))
    result.update(POSTGRES_SSLMODE='verify-full', PGSSLROOTCERT=CA)
    return result


def validate_nonsecret_env(text: str) -> None:
    manifest = json.loads((ROOT/'config/hosted-environment-manifest.json').read_text())
    allowed = {row['name'] for row in manifest['variables']} | set(OFF_FEATURES) | {
        'API_ALLOWED_HOSTS', 'API_USAGE_FLUSH_SECONDS', 'WRA_FLOOD_LOCAL_ROOT',
        'GSMMA_GEOLOGICAL_SENSITIVITY_LOCAL_ROOT', 'PLVR_SERVING_EXCLUSIONS_ENABLED',
        'PGSSLROOTCERT', 'POSTGRES_SSLMODE', 'SELFHOST_SECRETS_DIR', 'SELFHOST_TLS_DIR',
        'SELFHOST_RUNTIME_ENV_FILE', 'SELFHOST_BACKEND_IMAGE', 'SELFHOST_PROXY_IMAGE', 'SELFHOST_RESTORE_MODE',
        'PROFESSOR_SERVER_API_IMAGE', 'ANTI_ABUSE_ENFORCEMENT_MODE', 'TAIPEI_PLANNING_SOURCE_MODE',
    }
    seen = set()
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith('#'): continue
        key, separator, value = line.partition('=')
        if not separator or key != key.strip() or key in seen: raise SecretRefused('configuration_syntax_invalid')
        if sensitive_name(key) or key.startswith('NEXT_PUBLIC_'): raise SecretRefused('credential_in_configuration')
        if key not in allowed: raise SecretRefused('configuration_name_unsupported')
        exact = {'POSTGRES_SSLMODE': 'verify-full', 'PGSSLROOTCERT': CA,
                 'APP_ENV': 'preview', 'PLVR_DATA_BACKEND': 'blue',
                 'PLVR_SERVING_EXCLUSIONS_ENABLED': 'true', 'VALUATION_DEMO_MODE': 'false',
                 'EARTH_ENGINE_SATELLITE_REFERENCE_V1': 'false',
                 'ANTI_ABUSE_ENFORCEMENT_MODE': 'local_only',
                 'TAIPEI_PLANNING_SOURCE_MODE': 'manual_evidence',
                 'WRA_FLOOD_LOCAL_ROOT': '/srv/proptech/datasets/wra/flood/v1',
                 **{'ANTI_ABUSE_' + operation + '_DISABLED': 'true' for operation in DISABLED}}
        # These protected files have a deliberately simple dotenv contract:
        # no quoting/interpolation of security guards, nor alternate authorities.
        if (key in exact and value != exact[key]
                or key in OFF_FEATURES and value.lower() not in {'false', '0'}):
            raise SecretRefused('configuration_guard_invalid')
        seen.add(key)


def install_log_redaction(values):
    """Sanitize standard logging in this process, including exception chains.

    Preserve tuple/mapping argument structure for Uvicorn's access formatter.
    Never exec after installation: that would discard the redaction boundary.
    """
    markers = set()
    for value in values:
        candidates = [value]
        try:
            p = urlsplit(value)
            if p.password: candidates.extend([p.password, unquote(p.password)])
        except ValueError: pass
        for candidate in candidates:
            if len(candidate) >= 4: markers.update({candidate, quote(candidate, safe=''), quote_plus(candidate, safe='')})
    patterns = [re.compile(re.sub(r'%[0-9a-fA-F]{2}', lambda m: '(?i:' + m.group() + ')', re.escape(marker)))
                for marker in sorted(markers, key=len, reverse=True)]
    def safe(value):
        if isinstance(value, str):
            for pattern in patterns: value = pattern.sub('[REDACTED]', value)
            return value
        if isinstance(value, tuple): return tuple(safe(v) for v in value)
        if isinstance(value, list): return [safe(v) for v in value]
        if isinstance(value, dict): return {safe(k): safe(v) for k, v in value.items()}
        if value is None or isinstance(value, (bool, int, float)): return value
        return safe(str(value))
    def clean(record):
        try:
            for key, value in list(record.__dict__.items()):
                if key in {'exc_info', 'exc_text', 'stack_info'}: record.__dict__[key] = None
                else: record.__dict__[key] = safe(value)
        except Exception:
            record.msg = 'runtime_log_details_suppressed'; record.args = ()
            record.exc_info = record.exc_text = record.stack_info = None
        return record
    original_factory = logging.getLogRecordFactory()
    original_make = logging.Logger.makeRecord
    def factory(*args, **kwargs): return clean(original_factory(*args, **kwargs))
    def make(logger, *args, **kwargs): return clean(original_make(logger, *args, **kwargs))
    logging.setLogRecordFactory(factory); logging.Logger.makeRecord = make
    def restore():
        logging.setLogRecordFactory(original_factory); logging.Logger.makeRecord = original_make
    return restore
