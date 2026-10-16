"""Value-free secret entrypoint and bounded private selfhost database probes.

NEW infrastructure interface only; application configuration remains upstream.
No dotenv files, inherited database credentials, or remote target arguments.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

RUNTIME = {
    'app_database_url': 'DATABASE_URL',
    'usage_database_url': 'API_USAGE_DATABASE_URL',
    'usage_peer_hmac_key': 'API_USAGE_PEER_HMAC_KEY',
    'pilot_session_signing_key': 'PILOT_SESSION_SIGNING_KEY',
}
ADMIN_FILES = ('app_admin_password', 'app_runtime_password', 'usage_admin_password',
               'usage_migration_password', 'usage_bootstrap_database_url', 'usage_runtime_password')


class Refused(Exception):
    """A fixed reason code, never exception details or secret values."""


def read_secret(directory: Path, name: str) -> str:
    try:
        path = directory / name
        if not path.is_file() or path.stat().st_size > 8192:
            raise Refused('secret_missing_or_invalid')
        value = path.read_text(encoding='utf-8').removesuffix('\n').removesuffix('\r')
        if not value or value != value.strip() or any(ord(char) < 32 for char in value):
            raise Refused('secret_missing_or_invalid')
        return value
    except (OSError, UnicodeError):
        raise Refused('secret_missing_or_unreadable') from None


def database_url(value: str, kind: str) -> str:
    expected = {
        'app': ('app_runtime', 'postgres_app', '/proptech_app'),
        'usage': ('proptech_usage_runtime_v1', 'postgres_usage', '/proptech_api_usage'),
        'bootstrap': ('usage_migration', 'postgres_usage', '/proptech_api_usage'),
    }[kind]
    try:
        parsed = urlsplit(value)
        if (parsed.scheme not in {'postgres', 'postgresql'}
                or (parsed.username, parsed.hostname, parsed.path) != expected
                or parsed.port not in (None, 5432) or not parsed.password
                or parsed.query or parsed.fragment):
            raise ValueError()
    except ValueError:
        raise Refused('invalid_' + kind + '_database_url') from None
    return value


def runtime_environment(directory: Path) -> dict[str, str]:
    if any((directory / name).exists() for name in ADMIN_FILES):
        raise Refused('administrative_secret_in_runtime_mount')
    values = {env: read_secret(directory, name) for name, env in RUNTIME.items()}
    database_url(values['DATABASE_URL'], 'app')
    database_url(values['API_USAGE_DATABASE_URL'], 'usage')
    if any(len(values[name]) < 32 for name in ('API_USAGE_PEER_HMAC_KEY', 'PILOT_SESSION_SIGNING_KEY')):
        raise Refused('secret_too_short')
    # Explicitly suppress the legacy application URL alias and bootstrap actor.
    environment = {key: value for key, value in os.environ.items() if not key.startswith('PG') and key not in {
        *RUNTIME.values(), 'PILOT_EVIDENCE_DATABASE_URL', 'API_USAGE_BOOTSTRAP_DATABASE_URL',
    }}
    environment.update(values)
    environment.update(POSTGRES_SSLMODE='verify-full', PGSSLROOTCERT='/run/selfhost-ca/ca.crt')
    return environment


def bootstrap_environment(directory: Path) -> dict[str, str]:
    value = database_url(read_secret(directory, 'usage_bootstrap_database_url'), 'bootstrap')
    # Administrative profile has only the one administrative secret mount.
    environment = {key: value for key, value in os.environ.items()
                   if not key.startswith('PG') and key not in {*RUNTIME.values(), 'PILOT_EVIDENCE_DATABASE_URL'}}
    environment.update(API_USAGE_BOOTSTRAP_DATABASE_URL=value,
                       PGSSLROOTCERT='/run/selfhost-ca/ca.crt')
    return environment


def preflight(directory: Path) -> dict:
    """Read-only catalog freshness check; bootstrap repeats checks transactionally."""
    environment = bootstrap_environment(directory)
    os.environ.clear()
    os.environ.update(environment)
    from services.postgres_runtime import connect
    from scripts.bootstrap_usage_database import _actor, _fresh
    with connect(environment['API_USAGE_BOOTSTRAP_DATABASE_URL'], connect_timeout=3,
                 sslmode='verify-full') as connection:
        with connection.transaction():
            connection.execute('SET TRANSACTION READ ONLY')
            connection.execute("SET LOCAL statement_timeout='5000ms'")
            connection.execute("SET LOCAL lock_timeout='1000ms'")
            _actor(connection, 'proptech_api_usage')
            _fresh(connection)
    return {'status': 'pass', 'freshness': 'fresh', 'read_only': True,
            'warning': 'bootstrap_rechecks_freshness_transactionally'}


def runtime_probe(directory: Path) -> dict:
    environment = runtime_environment(directory)
    os.environ.clear()
    os.environ.update(environment)
    from services.postgres_runtime import connect
    from services.usage_guard import PostgresQuotaGuard
    from services.usage_ledger import PostgresUsageStore
    def bounded_connect(url):
        import psycopg
        return psycopg.connect(url, connect_timeout=3, sslmode='verify-full',
                               options='-c statement_timeout=5000 -c lock_timeout=1000')
    with bounded_connect(environment['DATABASE_URL']) as connection:
        row = connection.execute("SELECT current_user,session_user,current_database(),r.rolsuper,r.rolbypassrls,r.rolcreaterole,r.rolcreatedb,r.rolreplication,d.datdba=r.oid FROM pg_roles r JOIN pg_database d ON d.datname=current_database() WHERE r.rolname=current_user").fetchone()
        if row != ('app_runtime', 'app_runtime', 'proptech_app', False, False, False, False, False, False):
            raise Refused('unsafe_app_runtime')
    PostgresQuotaGuard(environment['API_USAGE_DATABASE_URL'], connection_factory=bounded_connect).check()
    # This existing startup probe writes only inside a forced rollback transaction.
    PostgresUsageStore(environment['API_USAGE_DATABASE_URL'], connection_factory=bounded_connect).check()
    return {'status': 'pass', 'app_runtime': 'direct_login', 'usage_guard': 'available',
            'usage_writer': 'rollback_probe_passed', 'application_schema': 'not_certified'}


def activate_runtime(directory: Path) -> dict:
    """Explicit credential activation after the unmodified provisioning CLI.

    This rotates only the exact dedicated runtime actor; no URL/password in argv.
    Catalog security verification and credential change share a transaction.
    """
    password = read_secret(directory, 'usage_runtime_password')
    if len(password) < 32:
        raise Refused('secret_too_short')
    environment = bootstrap_environment(directory)
    os.environ.clear()
    os.environ.update(environment)
    from psycopg import sql
    from services.postgres_runtime import connect
    from scripts.bootstrap_usage_database import _actor, _settings, migration_source
    from scripts.usage_database_security import verify_security
    with connect(environment['API_USAGE_BOOTSTRAP_DATABASE_URL'], connect_timeout=3,
                 sslmode='verify-full') as connection:
        with connection.transaction():
            actor = _actor(connection, 'proptech_api_usage')
            _settings(connection)
            verify_security(connection, actor=actor, migration_text=migration_source(), runtime=True)
            verifier = connection.pgconn.encrypt_password(password.encode(), b'proptech_usage_runtime_v1', b'scram-sha-256').decode()
            connection.execute(sql.SQL('ALTER ROLE proptech_usage_runtime_v1 PASSWORD {}').format(sql.Literal(verifier)))
            connection.execute('GRANT CONNECT ON DATABASE proptech_api_usage TO proptech_usage_runtime_v1')
            verify_security(connection, actor=actor, migration_text=migration_source(), runtime=True)
    return {'status': 'pass', 'runtime_credentials': 'activated'}


def health(directory: Path) -> dict:
    """Ongoing read-only guard/telemetry checks plus real local HTTP readiness."""
    environment = runtime_environment(directory)
    os.environ.clear()
    os.environ.update(environment)
    import psycopg
    from services.usage_guard import PostgresQuotaGuard
    def readonly_connect(url):
        return psycopg.connect(url, connect_timeout=2, sslmode='verify-full',
            options='-c default_transaction_read_only=on -c statement_timeout=3000 -c lock_timeout=500')
    PostgresQuotaGuard(environment['API_USAGE_DATABASE_URL'], connection_factory=readonly_connect).check()
    with readonly_connect(environment['API_USAGE_DATABASE_URL']) as connection:
        role = connection.execute('SELECT current_user,session_user').fetchone()
        if role != ('proptech_usage_runtime_v1', 'proptech_usage_runtime_v1'):
            raise Refused('unsafe_usage_runtime')
        connection.execute('SELECT bucket_start FROM api_usage.hourly LIMIT 1').fetchone()
        connection.execute('SELECT batch_id FROM api_usage.flush_batches LIMIT 1').fetchone()
        for table, privileges in (('hourly', ('SELECT', 'INSERT', 'UPDATE', 'DELETE')),
                                  ('flush_batches', ('SELECT', 'INSERT', 'DELETE'))):
            for privilege in privileges:
                if not connection.execute('SELECT has_table_privilege(current_user,%s,%s)',
                                          ('api_usage.' + table, privilege)).fetchone()[0]:
                    raise Refused('usage_writer_grant_unavailable')
        if connection.execute("SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='api_usage' AND c.relkind='r' AND c.relrowsecurity AND c.relforcerowsecurity").fetchone()[0] != 6:
            raise Refused('usage_rls_unavailable')
    http_readiness()
    return {'status': 'pass', 'read_only': True, 'usage_guard': 'available', 'http_readiness': 'ready'}


def http_readiness() -> None:
    from urllib.request import build_opener, ProxyHandler, HTTPRedirectHandler
    class RefuseRedirect(HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None
    opener = build_opener(ProxyHandler({}), RefuseRedirect())
    for endpoint in ('health', 'readiness'):
        with opener.open('http://127.0.0.1:8080/' + endpoint, timeout=3) as response:
            body = response.read(65537)
            if len(body) > 65536:
                raise Refused('http_response_too_large')
            payload = json.loads(body)
            ready = (payload.get('readiness') == 'ready' if endpoint == 'health'
                     else payload.get('runtime') == {'mode': 'preview', 'ready': True})
            if response.status != 200 or not ready:
                raise Refused('http_readiness_unavailable')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('api', 'bootstrap', 'preflight', 'runtime-probe', 'validate-secrets', 'activate-runtime', 'health'))
    parser.add_argument('--secrets-dir', type=Path, default=Path('/run/secrets'))
    args, remaining = parser.parse_known_args(argv)
    try:
        if args.operation == 'api':
            if remaining:
                raise Refused('unexpected_arguments')
            environment = runtime_environment(args.secrets_dir)
            os.execve(sys.executable, [sys.executable, '-m', 'uvicorn', 'backend.api_main:app',
                      '--host', '0.0.0.0', '--port', '8080', '--no-proxy-headers'], environment)
        elif args.operation == 'bootstrap':
            environment = bootstrap_environment(args.secrets_dir)
            os.execve(sys.executable, [sys.executable, str(ROOT / 'scripts/bootstrap_usage_database.py'),
                      *remaining], environment)
        else:
            if remaining:
                raise Refused('unexpected_arguments')
            if args.operation == 'validate-secrets':
                runtime_environment(args.secrets_dir)
                result = {'status': 'pass', 'runtime_secrets': 'validated'}
            elif args.operation == 'preflight':
                result = preflight(args.secrets_dir)
            elif args.operation == 'activate-runtime':
                result = activate_runtime(args.secrets_dir)
            elif args.operation == 'health':
                result = health(args.secrets_dir)
            else:
                result = runtime_probe(args.secrets_dir)
            print(json.dumps(result))
        return 0
    except Refused as exc:
        print(json.dumps({'status': 'refused', 'reason': str(exc)}))
    except Exception as exc:
        from scripts.usage_database_security import BootstrapRefused
        if isinstance(exc, BootstrapRefused):
            print(json.dumps({'status': 'refused', 'reason': str(exc)}))
        else:
            print(json.dumps({'status': 'failed', 'reason': 'details_suppressed',
                              'error_type': type(exc).__name__}))
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
