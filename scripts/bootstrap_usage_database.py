"""Dedicated usage DB bootstrap; never run the global application chain here.

CLI defaults to a database-free plan. Only API_USAGE_BOOTSTRAP_DATABASE_URL is
accepted for explicit execution; no application/production URL fallback.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.migration_registry import load_registry
from scripts.usage_database_security import (
    BootstrapRefused, CHECKSUM, MIGRATION_ID, RUNTIME, ROLES, require, verify_security,
)

RELEASE_PATTERN = re.compile(r'^[a-f0-9]{40}$')
SEAMS = tuple(
    f'ALTER FUNCTION {signature} OWNER TO proptech_usage_executor;\n'
    f'REVOKE ALL ON FUNCTION {signature} FROM PUBLIC;\n'
    f'GRANT EXECUTE ON FUNCTION {signature} TO proptech_usage_{role};'
    for signature, role in (
        ('api_usage.consume(text,text,text,text,uuid)','guard'), ('api_usage.prune()','writer'),
    )
)


def migration_source():
    registrations = load_registry()
    registration = next(r for r in registrations if r.path.stem==MIGRATION_ID)
    require(registration.sha256==CHECKSUM, 'migration_checksum_mismatch')
    canonical = registration.path.read_bytes().replace(b'\r\n', b'\n')
    require(hashlib.sha256(canonical).hexdigest()==CHECKSUM, 'migration_checksum_mismatch')
    source = canonical.decode('utf-8')
    require(all(source.count(seam)==1 for seam in SEAMS), 'migration_seam_mismatch')
    return source


def _actor(c, expected_database):
    row = c.execute("SELECT current_database(),current_user,session_user,r.rolsuper,r.rolcreaterole,d.datdba=r.oid,current_setting('server_version_num')::int,r.rolbypassrls,r.rolreplication,r.rolcanlogin FROM pg_roles r JOIN pg_database d ON d.datname=current_database() WHERE r.rolname=current_user").fetchone()
    require(row is not None and row[0]==expected_database, 'wrong_database')
    require(row[1]==row[2] and not row[3] and row[4] and row[5] and not row[7] and not row[8] and row[9], 'unsafe_migration_actor')
    require(170000 <= row[6] < 180000, 'postgresql_17_required')
    return row[1]


def _transaction(c):
    from psycopg.pq import TransactionStatus
    require(c.info.transaction_status==TransactionStatus.IDLE, 'idle_connection_required')
    return c.transaction()


def _settings(c):
    c.execute("SET LOCAL search_path = pg_catalog")
    c.execute("SET LOCAL statement_timeout = '10000ms'")
    c.execute("SET LOCAL lock_timeout = '1000ms'")
    c.execute("SET LOCAL createrole_self_grant = ''")
    c.execute('SELECT pg_advisory_xact_lock(831, 21)')


def _fresh(c):
    require(not c.execute("SELECT EXISTS(SELECT 1 FROM pg_namespace WHERE nspname='api_usage_bootstrap')").fetchone()[0], 'already_provisioned')
    require(not c.execute("SELECT EXISTS(SELECT 1 FROM pg_roles WHERE left(rolname,15)='proptech_usage_')").fetchone()[0], 'usage_roles_already_exist')
    require(not c.execute("SELECT EXISTS(SELECT 1 FROM pg_namespace WHERE nspname NOT LIKE 'pg\\_%' ESCAPE '\\' AND nspname NOT IN ('public','information_schema'))").fetchone()[0], 'target_not_fresh')
    require(not c.execute("SELECT EXISTS(SELECT 1 FROM pg_depend d JOIN pg_namespace n ON n.oid=d.refobjid WHERE d.refclassid='pg_namespace'::regclass AND n.nspname='public')").fetchone()[0], 'target_not_fresh')
    for query in (
        "SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname<>'plpgsql')",
        'SELECT EXISTS(SELECT 1 FROM pg_default_acl)',
        'SELECT EXISTS(SELECT 1 FROM pg_event_trigger)',
        'SELECT EXISTS(SELECT 1 FROM pg_largeobject_metadata)',
        'SELECT EXISTS(SELECT 1 FROM pg_publication)',
        'SELECT EXISTS(SELECT 1 FROM pg_subscription)',
        'SELECT EXISTS(SELECT 1 FROM pg_foreign_server)',
    ):
        require(not c.execute(query).fetchone()[0], 'target_not_fresh')


def _transfer(c, seam, actor):
    from psycopg import sql
    c.execute(sql.SQL('GRANT proptech_usage_executor TO {} WITH INHERIT TRUE, SET TRUE').format(sql.Identifier(actor)))
    c.execute('GRANT CREATE ON SCHEMA api_usage TO proptech_usage_executor')
    c.execute(seam)
    c.execute('REVOKE CREATE ON SCHEMA api_usage FROM proptech_usage_executor')
    # Revoke this actor's own seam grant. PG17's separate creator ADMIN grant
    # remains administrative-only (SET FALSE, INHERIT FALSE).
    c.execute(sql.SQL('REVOKE proptech_usage_executor FROM {}').format(sql.Identifier(actor)))
    require(c.execute("SELECT has_schema_privilege('proptech_usage_executor','api_usage','CREATE'),pg_has_role(%s,'proptech_usage_executor','SET'),pg_has_role(%s,'proptech_usage_executor','USAGE')",(actor,actor)).fetchone()==(False,False,False), 'temporary_privilege_cleanup_failed')


def bootstrap(c, *, expected_database, release_version):
    require(bool(expected_database), 'expected_database_required')
    require(bool(RELEASE_PATTERN.fullmatch(release_version)), 'invalid_release_version')
    source = migration_source()
    with _transaction(c):
        actor = _actor(c, expected_database)
        _settings(c)
        _fresh(c)
        remaining = source
        for seam in SEAMS:
            prefix, remaining = remaining.split(seam, 1)
            if prefix.strip():
                c.execute(prefix)
            _transfer(c, seam, actor)
        if remaining.strip():
            c.execute(remaining)
        c.execute('CREATE SCHEMA api_usage_bootstrap')
        c.execute('REVOKE ALL ON SCHEMA api_usage_bootstrap FROM PUBLIC')
        c.execute('CREATE TABLE api_usage_bootstrap.history (migration_id text PRIMARY KEY, checksum text NOT NULL, bootstrap_version integer NOT NULL, release_version text NOT NULL, actor name NOT NULL, applied_at timestamptz NOT NULL DEFAULT now())')
        c.execute('REVOKE ALL ON api_usage_bootstrap.history FROM PUBLIC')
        c.execute('INSERT INTO api_usage_bootstrap.history(migration_id,checksum,bootstrap_version,release_version,actor) VALUES(%s,%s,1,%s,%s)',(MIGRATION_ID,CHECKSUM,release_version,actor))
        verify_security(c, actor=actor, migration_text=source)
    return {'status':'bootstrapped','migration_id':MIGRATION_ID,'checksum':CHECKSUM}


def provision_runtime(c, *, expected_database):
    source = migration_source()
    with _transaction(c):
        actor = _actor(c, expected_database)
        _settings(c)
        require(not c.execute('SELECT EXISTS(SELECT 1 FROM pg_roles WHERE rolname=%s)',(RUNTIME,)).fetchone()[0], 'runtime_already_exists')
        verify_security(c, actor=actor, migration_text=source)
        c.execute(f'CREATE ROLE {RUNTIME} LOGIN INHERIT NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE NOREPLICATION PASSWORD NULL')
        c.execute(f'GRANT proptech_usage_guard,proptech_usage_writer TO {RUNTIME} WITH INHERIT TRUE, SET FALSE, ADMIN FALSE')
        verify_security(c, actor=actor, migration_text=source, runtime=True)
    return {'status':'runtime_provisioned','role':RUNTIME,'credentials':'not_provisioned'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--operation',choices=('bootstrap','provision-runtime'),default='bootstrap')
    parser.add_argument('--execute',action='store_true')
    parser.add_argument('--acknowledge-fresh-dedicated',action='store_true')
    parser.add_argument('--expected-database')
    parser.add_argument('--release-version')
    args = parser.parse_args(argv)
    try:
        migration_source()
        if not args.execute:
            print(json.dumps({'status':'plan','database_contacted':False,'operation':args.operation,'checksum':CHECKSUM}))
            return 0
        require(args.acknowledge_fresh_dedicated and bool(args.expected_database), 'explicit_dedicated_target_required')
        if args.operation=='bootstrap':
            require(bool(args.release_version and RELEASE_PATTERN.fullmatch(args.release_version)), 'invalid_release_version')
        require(bool(os.getenv('API_USAGE_BOOTSTRAP_DATABASE_URL','').strip()), 'bootstrap_url_required')
        from services.postgres_runtime import connect
        with connect(os.environ['API_USAGE_BOOTSTRAP_DATABASE_URL'],sslmode='require') as c:
            if args.operation=='bootstrap':
                result = bootstrap(c,expected_database=args.expected_database,release_version=args.release_version)
            else:
                result = provision_runtime(c,expected_database=args.expected_database)
        print(json.dumps(result))
        return 0
    except BootstrapRefused as exc:
        print(json.dumps({'status':'refused','reason':str(exc)}))
    except Exception:
        print(json.dumps({'status':'failed','reason':'details_suppressed'}))
    return 1


if __name__=='__main__':
    raise SystemExit(main())
