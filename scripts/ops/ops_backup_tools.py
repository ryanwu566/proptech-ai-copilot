"""Host-only selfhost operations. Never print subprocess diagnostics or credentials.

Operator backups require age; restoration accepts an archive and an identity FILE,
never a database URL, container name, or target. Only UUID local disposable targets
are created. No existing database is modified by restore rehearsal.
"""
from __future__ import annotations

import argparse
from datetime import UTC, datetime
import hashlib
from itertools import islice
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import time
import uuid
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
IMAGE = 'postgres@sha256:742f40ea20b9ff2ff31db5458d127452988a2164df9e17441e191f3b72252193'
DATABASES = {'app': ('postgres_app', 'proptech_app'), 'usage': ('postgres_usage', 'proptech_api_usage')}
ARCHIVES = {f'{scope}.{kind}.age' for scope in DATABASES for kind in ('dump', 'roles')}
CONFIG_FILES = ('docker-compose.selfhost.yml', 'Dockerfile.cloudrun',
    'infra/selfhost/Dockerfile', 'infra/selfhost/init-database.sh',
    'infra/selfhost/pg_hba.conf', 'infra/selfhost/nginx.conf',
    'scripts/ops/selfhost_runtime.py', 'scripts/ops/ops_backup_tools.py',
    'scripts/ops/selfhost-backup.sh', 'scripts/ops/selfhost-restore-rehearsal.sh',
    'scripts/ops/selfhost-health-check.sh')


def environment():
    # Docker/Compose needs host configuration, but never legacy libpq/DB URLs.
    infra_paths = {'SELFHOST_SECRETS_DIR', 'SELFHOST_TLS_DIR', 'SELFHOST_RUNTIME_ENV_FILE',
                   'SELFHOST_BACKEND_IMAGE', 'SELFHOST_PROXY_IMAGE', 'SELFHOST_RESTORE_MODE'}
    system_keys = {'PATH', 'HOME', 'USERPROFILE', 'APPDATA', 'LOCALAPPDATA', 'SYSTEMROOT',
                   'WINDIR', 'COMSPEC', 'PATHEXT', 'TEMP', 'TMP', 'PROGRAMDATA',
                   'LANG', 'LC_ALL', 'TZ'}
    return {k: v for k, v in os.environ.items()
            if k in infra_paths or k.upper() in system_keys}


def run(args, *, data=None, timeout=60):
    result = subprocess.run(args, input=data, stdout=subprocess.PIPE,
                            stderr=subprocess.DEVNULL, timeout=timeout, env=environment())
    if result.returncode:
        raise RuntimeError('command_failed')
    return result.stdout


def local_docker():
    endpoint = os.environ.get('DOCKER_HOST')
    if not endpoint:
        # Context inspection is local configuration; no daemon request yet.
        endpoint = run(['docker', 'context', 'inspect', '--format', '{{.Endpoints.docker.Host}}'], timeout=10).decode().strip()
    if not re.fullmatch(r'(unix:///[^\r\n\x00]+|npipe:////\./pipe/[A-Za-z0-9_.-]+)', endpoint):
        raise ValueError('local_docker_socket_required')
    return ['docker', '--host', endpoint]


def safe_path(path, *, directory=False):
    path = Path(path)
    if not path.is_absolute() or '..' in path.parts:
        raise ValueError('absolute_path_required')
    for component in (path, *path.parents):
        if component.is_symlink() or component.is_junction():
            raise ValueError('symlink_or_junction_refused')
    if path.exists() and (not path.is_dir() if directory else not path.is_file()):
        raise ValueError('invalid_path_type')
    return path


def pipeline(source, sink, *, output=None, timeout=1800):
    """Bounded streaming; plaintext never enters a disk file or exception."""
    first = second = None
    handle = None
    try:
        if output is not None:
            handle = Path(output).open('xb')
        first = subprocess.Popen(source, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, env=environment())
        second = subprocess.Popen(sink, stdin=first.stdout,
                                  stdout=handle if handle else subprocess.DEVNULL,
                                  stderr=subprocess.DEVNULL, env=environment())
        first.stdout.close()
        end = time.monotonic() + timeout
        second.wait(timeout=timeout)
        first.wait(timeout=max(0.1, end-time.monotonic()))
        if first.returncode or second.returncode:
            raise RuntimeError('pipeline_failed')
    except BaseException:
        for process in (second, first):
            if process is not None and process.poll() is None:
                process.kill()
                process.wait()
        if handle:
            handle.close()
            Path(output).unlink(missing_ok=True)  # only the exclusively created partial file
        raise
    finally:
        if handle:
            handle.close()


def compose(docker, project):
    if not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,62}', project):
        raise ValueError('invalid_compose_project')
    return [*docker, 'compose', '--env-file', os.devnull, '--project-name', project, '--file', str(ROOT/'docker-compose.selfhost.yml')]


def socket_sql(base, service, database, query):
    return run([*base, 'exec', '-T', '--user', 'postgres', service, 'psql', '-X', '-At', '-v', 'ON_ERROR_STOP=1', '-d', database], data=("SET statement_timeout='10s';\n"+query).encode())


# OID-independent evidence. Raw history/catalog output remains memory-only;
# the public manifest contains only a digest. Runtime role/password hashes excluded.
SNAPSHOT = """
SELECT row_to_json(t) FROM (SELECT * FROM api_usage_bootstrap.history ORDER BY migration_id) t;
SELECT row_to_json(t) FROM (SELECT nspname,pg_get_userbyid(nspowner) owner,ARRAY(SELECT json_build_array(pg_get_userbyid(a.grantor),CASE WHEN a.grantee=0 THEN 'PUBLIC' ELSE pg_get_userbyid(a.grantee) END,a.privilege_type,a.is_grantable)::text FROM aclexplode(coalesce(nspacl,acldefault('n',nspowner))) a ORDER BY 1) acl FROM pg_namespace WHERE nspname IN ('api_usage','api_usage_bootstrap') ORDER BY nspname) t;
SELECT row_to_json(t) FROM (SELECT datname,pg_get_userbyid(datdba) owner,ARRAY(SELECT json_build_array(pg_get_userbyid(a.grantor),CASE WHEN a.grantee=0 THEN 'PUBLIC' ELSE pg_get_userbyid(a.grantee) END,a.privilege_type,a.is_grantable)::text FROM aclexplode(coalesce(datacl,acldefault('d',datdba))) a ORDER BY 1) acl FROM pg_database WHERE datname=current_database()) t;
SELECT row_to_json(t) FROM (SELECT rolname,rolsuper,rolinherit,rolcreaterole,rolcreatedb,rolcanlogin,rolreplication,rolbypassrls FROM pg_roles WHERE left(rolname,15)='proptech_usage_' OR rolname='usage_migration' ORDER BY rolname) t;
SELECT row_to_json(t) FROM (SELECT c.relname,pg_get_userbyid(c.relowner) owner,c.relrowsecurity,c.relforcerowsecurity,ARRAY(SELECT json_build_array(pg_get_userbyid(a.grantor),CASE WHEN a.grantee=0 THEN 'PUBLIC' ELSE pg_get_userbyid(a.grantee) END,a.privilege_type,a.is_grantable)::text FROM aclexplode(coalesce(c.relacl,acldefault('r',c.relowner))) a ORDER BY 1) acl FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname IN ('api_usage','api_usage_bootstrap') AND c.relkind='r' ORDER BY n.nspname,c.relname) t;
SELECT row_to_json(t) FROM (SELECT tablename,policyname,permissive,roles,cmd,qual,with_check FROM pg_policies WHERE schemaname='api_usage' ORDER BY tablename,policyname) t;
SELECT row_to_json(t) FROM (SELECT p.proname,pg_get_userbyid(p.proowner) owner,p.prosecdef,p.proconfig,p.prosrc,ARRAY(SELECT json_build_array(pg_get_userbyid(a.grantor),CASE WHEN a.grantee=0 THEN 'PUBLIC' ELSE pg_get_userbyid(a.grantee) END,a.privilege_type,a.is_grantable)::text FROM aclexplode(coalesce(p.proacl,acldefault('f',p.proowner))) a ORDER BY 1) acl FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='api_usage' ORDER BY p.proname) t;
SELECT row_to_json(t) FROM (SELECT r.rolname,m.rolname member,g.rolname grantor,a.admin_option,a.inherit_option,a.set_option FROM pg_auth_members a JOIN pg_roles r ON r.oid=a.roleid JOIN pg_roles m ON m.oid=a.member JOIN pg_roles g ON g.oid=a.grantor WHERE left(r.rolname,15)='proptech_usage_' ORDER BY r.rolname,m.rolname,g.rolname) t;
"""
USAGE_CHECK = """
SELECT (SELECT count(*)=1 AND bool_and(checksum='00ed7d4b78de6d92c285ab8cd87241d1477bee2ce6e97caef6bbf6e2f43b98af' AND bootstrap_version=1) FROM api_usage_bootstrap.history)
 AND (SELECT count(*)=6 AND bool_and(relrowsecurity AND relforcerowsecurity) FROM pg_class WHERE relnamespace='api_usage'::regnamespace AND relkind='r')
 AND (SELECT count(*)=8 FROM pg_policy WHERE polrelid IN (SELECT oid FROM pg_class WHERE relnamespace='api_usage'::regnamespace))
 AND has_function_privilege('proptech_usage_runtime_v1','api_usage.consume(text,text,text,text,uuid)','EXECUTE')
 AND NOT has_table_privilege('proptech_usage_runtime_v1','api_usage.quota_policy','SELECT')
 AND NOT has_schema_privilege('proptech_usage_runtime_v1','api_usage_bootstrap','USAGE')
 AND NOT has_schema_privilege('proptech_usage_runtime_v1','api_usage','CREATE')
 AND NOT pg_has_role('proptech_usage_runtime_v1','proptech_usage_executor','MEMBER')
 AND (SELECT NOT (rolsuper OR rolbypassrls OR rolcreaterole OR rolcreatedb OR rolreplication) AND rolcanlogin AND rolinherit FROM pg_roles WHERE rolname='proptech_usage_runtime_v1');
BEGIN; SET LOCAL ROLE proptech_usage_runtime_v1; SELECT count(*)>=0 FROM api_usage.hourly; ROLLBACK;
"""


def fingerprint(base, service, database):
    return hashlib.sha256(socket_sql(base, service, database, SNAPSHOT)).hexdigest()


def metadata(path):
    h = hashlib.sha256()
    with path.open('rb') as archive:
        for chunk in iter(lambda: archive.read(1024*1024), b''):
            h.update(chunk)
    return {'bytes': path.stat().st_size, 'sha256': h.hexdigest()}


def write_new(path, value):
    with path.open('x', encoding='utf-8', newline='\n') as handle:
        handle.write(value)


def capture_config(destination):
    """Recover reviewed infrastructure files; never copy dotenv or secret mounts."""
    destination.mkdir(mode=0o700, exist_ok=False)
    release = run(['git', '-C', str(ROOT), 'rev-parse', 'HEAD']).decode().strip()
    if not re.fullmatch(r'[a-f0-9]{40}', release):
        raise ValueError('invalid_release_commit')
    result = {'release_commit': release, 'files': {}, 'runtime': {}, 'images': {}}
    result['tracked_worktree_dirty'] = bool(run(['git','-C',str(ROOT),'status','--porcelain','--untracked-files=no']).strip())
    for relative in CONFIG_FILES:
        source = safe_path(ROOT/relative)
        target = destination/relative
        target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        with source.open('rb') as original, target.open('xb') as copied:
            shutil.copyfileobj(original, copied)
        result['files'][relative] = metadata(target)
    runtime = safe_path(Path(os.environ.get('SELFHOST_RUNTIME_ENV_FILE', '')))
    if runtime.stat().st_size > 65536:
        raise ValueError('runtime_config_too_large')
    allowed = {'APP_ENV': {'preview'}, 'APP_RUNTIME': {'standard','worker'},
               'MAINTENANCE_MODE': {'true','false'}, 'POSTGRES_SSLMODE': {'verify-full'},
               'API_USAGE_GUARD_MODE': {'postgres'}, 'API_USAGE_LEDGER_REQUIRED': {'true'}}
    for line in runtime.read_text(encoding='utf-8').splitlines():
        name, separator, value = line.partition('=')
        if separator and name in allowed:
            if value not in allowed[name]:
                raise ValueError('unexpected_nonsecret_runtime_value')
            result['runtime'][name] = value
    docker = local_docker()
    for name in ('SELFHOST_BACKEND_IMAGE', 'SELFHOST_PROXY_IMAGE'):
        reference = os.environ.get(name, '')
        if not re.fullmatch(r'(?:[\w./:-]+@)?sha256:[a-f0-9]{64}', reference):
            raise ValueError('immutable_image_reference_required')
        observed = run([*docker, 'image', 'inspect', reference, '--format', '{{.Id}}'], timeout=15).decode().strip()
        if not re.fullmatch(r'sha256:[a-f0-9]{64}', observed):
            raise ValueError('invalid_local_image_identity')
        result['images'][name] = {'reference': reference, 'image_id': observed}
    return result


def backup(output, recipients, project):
    output = safe_path(output, directory=True)
    recipients = safe_path(recipients)
    if not recipients.is_file():
        raise ValueError('recipients_file_required')
    if not output.exists():
        output.mkdir(mode=0o700)  # parent must already exist and was checked
    docker = local_docker()
    base = compose(docker, project)
    identifier = datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid.uuid4().hex
    destination = output/identifier
    destination.mkdir(mode=0o700, exist_ok=False)
    manifest = {'schema_version': 1, 'created_at': datetime.now(UTC).isoformat(),
                'postgres_major': 17, 'encryption': 'age', 'files': {},
                'source': 'compose_local_socket', 'usage_catalog_sha256': None}
    for scope, (service, database) in DATABASES.items():
        version = socket_sql(base, service, database, 'SHOW server_version_num;').decode().strip().splitlines()[-1]
        if not version.isdigit() or not 170000 <= int(version) < 180000:
            raise ValueError('postgres_17_required')
        for kind, command in (
            ('dump', ['pg_dump', '--format=custom', '--compress=6', '--dbname='+database]),
            ('roles', ['pg_dumpall', '--roles-only', '--no-role-passwords']),
        ):
            target = destination/f'{scope}.{kind}.age'
            pipeline([*base, 'exec', '-T', '--user', 'postgres', service, *command],
                     ['age', '--encrypt', '--recipients-file', str(recipients)], output=target)
            manifest['files'][target.name] = metadata(target)
    manifest['usage_catalog_sha256'] = fingerprint(base, 'postgres_usage', 'proptech_api_usage')
    config = capture_config(destination/'config')
    config.update(services=DATABASES, dump_format='custom', password_hashes=False)
    write_new(destination/'config.json', json.dumps(config, indent=2)+'\n')
    manifest['configuration'] = metadata(destination/'config.json')
    write_new(destination/'manifest.json', json.dumps(manifest, indent=2)+'\n')
    write_new(destination/'SHA256SUMS', ''.join(f"{v['sha256']}  {name}\n" for name,v in sorted(manifest['files'].items())))
    write_new(destination/'SUCCESS', 'encrypted_archives_complete\n')
    return identifier


def verify_bundle(directory):
    directory = safe_path(directory, directory=True)
    for name in ('SUCCESS', 'manifest.json', 'config.json', 'SHA256SUMS', *ARCHIVES):
        safe_path(directory/name)
    if not (directory/'SUCCESS').is_file():
        raise ValueError('incomplete_backup')
    manifest = json.loads((directory/'manifest.json').read_text())
    if manifest.get('schema_version') != 1 or set(manifest.get('files', {})) != ARCHIVES or manifest.get('postgres_major') != 17:
        raise ValueError('invalid_manifest')
    for name, expected in manifest['files'].items():
        if metadata(directory/name) != expected or expected['bytes'] < 1:
            raise ValueError('archive_integrity_failed')
    if metadata(directory/'config.json') != manifest.get('configuration'):
        raise ValueError('config_integrity_failed')
    config = json.loads((directory/'config.json').read_text())
    if set(config.get('files', {})) != set(CONFIG_FILES):
        raise ValueError('config_allowlist_mismatch')
    for relative, expected in config['files'].items():
        if metadata(safe_path(directory/'config'/relative)) != expected:
            raise ValueError('config_integrity_failed')
    return manifest


def prepare_roles(source):
    # pg_dumpall includes the cluster's initial postgres role. Skip exactly that
    # known CREATE; preserve every ALTER/GRANT and keep ON_ERROR_STOP enabled.
    if len(re.findall(br'^CREATE ROLE postgres;$', source, re.M)) != 1:
        raise ValueError('unexpected_default_postgres_role')
    return re.sub(br'^CREATE ROLE postgres;$', b'-- default postgres role already exists', source, count=1, flags=re.M)


def direct_runtime_probe(base, runner=run):
    """Direct LOGIN on disposable loopback trust; does not prove password auth."""
    command = [*base, 'psql', '-X', '-At', '-v', 'ON_ERROR_STOP=1',
               '-h', '127.0.0.1', '-U', 'proptech_usage_runtime_v1', '-d', 'proptech_api_usage']
    query = """SET statement_timeout='10s';
SELECT current_user=session_user AND current_user='proptech_usage_runtime_v1';
SELECT count(*)>=0 FROM api_usage.hourly;
BEGIN;
SELECT result='admitted' FROM api_usage.consume('anon:'||repeat('d',64),'anonymous','places','request',gen_random_uuid());
ROLLBACK;
"""
    if runner(command, data=query.encode()).decode().splitlines().count('t') != 3:
        raise ValueError('direct_runtime_probe_failed')
    denied = b"""SET statement_timeout='10s';
BEGIN;
DO $$ BEGIN
  BEGIN
    UPDATE api_usage.quota_policy SET request_hour=99999;
    RAISE EXCEPTION 'runtime_policy_write_not_denied';
  EXCEPTION WHEN insufficient_privilege THEN NULL;
  END;
END $$;
SELECT 'DENIED';
ROLLBACK;
"""
    if 'DENIED' not in runner(command, data=denied).decode().splitlines():
        raise ValueError('runtime_policy_write_not_denied')


def restore(directory, identity):
    directory = Path(directory)
    manifest = verify_bundle(directory)  # before contacting any daemon
    # Deliberately a small fixture rehearsal: 512MiB PGDATA per fresh target.
    # Compression can still exceed that target; such restores fail categorically.
    if sum(item['bytes'] for item in manifest['files'].values()) > 64*1024*1024:
        raise ValueError('small_rehearsal_archive_limit')
    identity = safe_path(identity)
    if not identity.is_file():
        raise ValueError('identity_file_required')
    if os.name != 'nt' and stat.S_IMODE(identity.stat().st_mode) & 0o077:
        raise ValueError('private_identity_permissions_required')
    docker = local_docker()
    image_id = run([*docker, 'image', 'inspect', IMAGE, '--format', '{{.Id}}'], timeout=15).decode().strip()
    if not re.fullmatch(r'sha256:[a-f0-9]{64}', image_id):
        raise ValueError('local_pinned_image_required')
    owned = []
    try:
        for scope, (_, database) in DATABASES.items():
            ownership = uuid.uuid4().hex
            name = 'proptech-restore-'+ownership
            container = run([*docker, 'create', '--pull=never', '--name', name,
                '--label', 'proptech.selfhost.disposable='+ownership, '--network=none',
                '--memory=768m', '--cpus=1', '--pids-limit=128',
                '--tmpfs', '/var/lib/postgresql/data:rw,size=512m',
                '-e', 'POSTGRES_HOST_AUTH_METHOD=trust', image_id], timeout=30).decode().strip()
            if not re.fullmatch(r'[a-f0-9]{64}', container):
                raise ValueError('invalid_disposable_container')
            owned.append((container, ownership))
            run([*docker, 'start', container], timeout=30)
            for _ in range(60):
                try:
                    run([*docker, 'exec', '--user', 'postgres', container, 'pg_isready', '-h', '127.0.0.1'], timeout=5)
                    break
                except RuntimeError:
                    time.sleep(0.5)
            else:
                raise RuntimeError('disposable_start_timeout')
            base = [*docker, 'exec', '-i', '--user', 'postgres', container]
            default_role = run([*base, 'psql', '-X', '-At', '-v', 'ON_ERROR_STOP=1', '-d', 'postgres'],
                data=b"SELECT rolsuper,rolinherit,rolcreaterole,rolcreatedb,rolcanlogin,rolreplication,rolbypassrls FROM pg_roles WHERE rolname='postgres';").decode().strip()
            if default_role != 't|t|t|t|t|t|t':
                raise ValueError('unexpected_default_postgres_attributes')
            roles = run(['age', '--decrypt', '--identity', str(identity), str(directory/f'{scope}.roles.age')], timeout=120)
            run([*base, 'psql', '-X', '-v', 'ON_ERROR_STOP=1', '-d', 'postgres'], data=prepare_roles(roles))
            pipeline(['age', '--decrypt', '--identity', str(identity), str(directory/f'{scope}.dump.age')],
                     [*base, 'pg_restore', '--exit-on-error', '--create', '--dbname=postgres'])
            if scope == 'usage':
                # Adapt the shared socket query boundary to plain docker exec.
                def sql(query):
                    return run([*base, 'psql', '-X', '-At', '-v', 'ON_ERROR_STOP=1', '-d', database], data=("SET statement_timeout='10s';\n"+query).encode())
                if hashlib.sha256(sql(SNAPSHOT)).hexdigest() != manifest['usage_catalog_sha256']:
                    raise ValueError('restored_usage_catalog_mismatch')
                if sql(USAGE_CHECK).decode().splitlines().count('t') != 2:
                    raise ValueError('restored_usage_security_failed')
                direct_runtime_probe(base)
    finally:
        for container, ownership in owned:
            # Never remove an identifier merely supplied by an operator.
            observed = run([*docker, 'inspect', '--format', '{{index .Config.Labels "proptech.selfhost.disposable"}}', container], timeout=10).decode().strip()
            if observed != ownership:
                raise ValueError('disposable_ownership_mismatch')
            run([*docker, 'rm', '--force', container], timeout=30)


def health(output, project, url, max_age_hours):
    output = safe_path(output, directory=True)
    if not 1 <= max_age_hours <= 8760:
        raise ValueError('invalid_backup_age_threshold')
    # HTTP checks deliberately target only the host's private loopback proxy.
    if not re.fullmatch(r'https?://127\.0\.0\.1:[0-9]{1,5}', url):
        raise ValueError('loopback_health_url_required')
    docker = local_docker()
    categories = {}
    identifiers = run([*compose(docker, project), 'ps', '-q'], timeout=15).decode().splitlines()
    states = []
    for container in identifiers:
        if not re.fullmatch(r'[a-f0-9]{12,64}', container):
            raise ValueError('invalid_container_id')
        # Only status and restart count; never full inspect or environment.
        states.append(run([*docker, 'inspect', '--format', '{{.State.Status}} {{.RestartCount}} {{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}', container], timeout=10).decode().strip().split())
    categories['CONTAINERS'] = 'PASS' if len(states) == 4 and all(s == ['running', '0', 'healthy'] for s in states) else 'WARN'
    for scope, (service, database) in DATABASES.items():
        try:
            run([*compose(docker, project), 'exec', '-T', '--user', 'postgres', service,
                 'pg_isready', '--timeout=3', '--dbname='+database], timeout=10)
            categories[scope.upper()+'_DATABASE'] = 'PASS'
        except Exception:
            categories[scope.upper()+'_DATABASE'] = 'FAIL'
    for endpoint in ('health', 'readiness'):
        try:
            # No proxy inheritance, redirects, credentials, or response logging.
            class NoRedirect(urllib.request.HTTPRedirectHandler):
                def redirect_request(self, *args, **kwargs):
                    return None
            client = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
            with client.open(url+'/'+endpoint, timeout=5) as response:
                payload = json.loads(response.read(65537))
                ready = (payload.get('readiness') == 'ready' and payload.get('mode') == 'preview'
                         if endpoint == 'health' else payload.get('runtime') == {'mode':'preview','ready':True})
                categories[endpoint.upper()] = 'PASS' if response.status == 200 and ready else 'FAIL'
        except Exception:
            categories[endpoint.upper()] = 'FAIL'
    categories['DISK'] = 'PASS' if shutil.disk_usage(output).free/shutil.disk_usage(output).total > 0.15 else 'WARN'
    categories['CPU'] = 'PASS' if hasattr(os, 'getloadavg') and os.getloadavg()[0] <= (os.cpu_count() or 1)*2 else 'WARN'
    try:
        memory = dict((line.split(':')[0], int(line.split()[1])) for line in Path('/proc/meminfo').read_text().splitlines())
        categories['MEMORY'] = 'PASS' if memory['MemAvailable']/memory['MemTotal'] > 0.1 else 'WARN'
    except (OSError, KeyError, ValueError):
        categories['MEMORY'] = 'UNKNOWN'
    freshest = None
    for directory in islice(output.iterdir(), 4096):
        if not directory.is_dir() or directory.is_symlink():
            continue
        try:
            # Archive hashes are verified by restore; this bounded host check
            # checks completeness and declared freshness, avoiding huge I/O.
            safe_path(directory/'manifest.json')
            safe_path(directory/'SUCCESS')
            if (directory/'SUCCESS').is_file() and (directory/'manifest.json').stat().st_size <= 65536:
                m = json.loads((directory/'manifest.json').read_text())
                age = (datetime.now(UTC)-datetime.fromisoformat(m['created_at'])).total_seconds()/3600
                complete = (set(m['files']) == ARCHIVES
                            and all(safe_path(directory/name).is_file()
                                    and (directory/name).stat().st_size == entry['bytes'] > 0
                                    for name, entry in m['files'].items()))
                if complete and 0 <= age:
                    freshest = age if freshest is None else min(age, freshest)
        except (OSError, ValueError, KeyError, TypeError):
            continue
    categories['BACKUP_AGE'] = 'PASS' if freshest is not None and freshest <= max_age_hours else 'WARN'
    try:
        probe = json.loads(run([*compose(docker, project), 'exec', '-T', 'api', 'python',
            'scripts/ops/selfhost_runtime.py', 'health'], timeout=15))
        categories['USAGE_GUARD'] = 'PASS' if probe == {'status':'pass','read_only':True,'usage_guard':'available','http_readiness':'ready'} else 'FAIL'
    except Exception:
        categories['USAGE_GUARD'] = 'FAIL'
    return categories


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='operation', required=True)
    b = sub.add_parser('backup')
    b.add_argument('--output-dir', type=Path, required=True)
    b.add_argument('--recipients-file', type=Path, required=True)
    b.add_argument('--project', default='proptech-selfhost')
    r = sub.add_parser('restore')
    r.add_argument('--backup-dir', type=Path, required=True)
    r.add_argument('--identity-file', type=Path, required=True)
    h = sub.add_parser('health')
    h.add_argument('--backup-dir', type=Path, required=True)
    h.add_argument('--project', default='proptech-selfhost')
    h.add_argument('--url', default='http://127.0.0.1:8080')
    h.add_argument('--max-age-hours', type=int, default=30)
    args = parser.parse_args()
    os.umask(0o077)
    try:
        if args.operation == 'backup':
            backup(args.output_dir, args.recipients_file, args.project)
            print('BACKUP=PASS')
        elif args.operation == 'restore':
            restore(args.backup_dir, args.identity_file)
            print('RESTORE=PASS; SCOPE=DISPOSABLE_LOCAL; PASSWORDS=NOT_RESTORED')
        else:
            categories = health(args.backup_dir, args.project, args.url, args.max_age_hours)
            print('; '.join(k+'='+v for k,v in categories.items()))
            return int(any(v in ('FAIL','WARN') for v in categories.values()))
        return 0
    except (Exception, KeyboardInterrupt):
        print(args.operation.upper()+'=FAIL; DETAILS=SUPPRESSED')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
