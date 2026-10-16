"""Rehearse the selfhost bundle using NEW UUID local Docker resources only.

Requires preloaded immutable backend/proxy image IDs in SELFHOST_BACKEND_IMAGE /
SELFHOST_PROXY_IMAGE; never pulls, contacts remote databases or accepts a target.
All provider egress is blocked by internal Docker networks during this rehearsal.
Generated dummy secrets live outside the checkout and are destroyed on cleanup.
The application database is deliberately EMPTY: this certifies connectivity and
actual FastAPI lifespan only, not application migration/auth readiness.
"""
from __future__ import annotations

import argparse
from datetime import UTC, datetime, timedelta
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys
import tempfile
import time
from urllib.request import build_opener, ProxyHandler, HTTPRedirectHandler
from urllib.parse import urlsplit
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
PG = 'postgres@sha256:742f40ea20b9ff2ff31db5458d127452988a2164df9e17441e191f3b72252193'
RELEASE = '0ac46365f35b01d5f13aed978a4eb3ddf00db670'
_DUMMY_REDACTIONS: list[str] = []
_LOCAL_DOCKER: list[str] = []


def run(command, *, env, data=None, timeout=120, check=True):
    if command[0] == 'docker':
        if not _LOCAL_DOCKER:
            raise ValueError('local_docker_socket_required')
        command = [*_LOCAL_DOCKER, *command[1:]]
    result = subprocess.run(command, cwd=ROOT, env=env, input=data,
                            text=True, encoding='utf-8', errors='replace',
                            capture_output=True, timeout=timeout)
    if check and result.returncode:
        # Keep all subprocess exception/log detail suppressed: may include SQL.
        category = ''
        try:
            safe = json.loads(result.stdout)
            # Only wrapper-emitted fixed categories are retained.
            category = ':' + str({key: safe[key] for key in ('status', 'reason', 'error_type') if key in safe})
        except (ValueError, TypeError):
            detail = result.stderr
            for value in _DUMMY_REDACTIONS:
                detail = detail.replace(value, '[redacted]')
            category = ':docker_diagnostic=' + detail[-500:]
        raise RuntimeError('local_operation_failed:' + command[0] + ':' + command[1] + category)
    return result


def certificates(folder: Path):
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID
    now = datetime.now(UTC)
    ca_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    ca_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'Disposable rehearsal CA')])
    ca = (x509.CertificateBuilder().subject_name(ca_name).issuer_name(ca_name)
          .public_key(ca_key.public_key()).serial_number(x509.random_serial_number())
          .not_valid_before(now-timedelta(minutes=1)).not_valid_after(now+timedelta(days=1))
          .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
          .sign(ca_key, hashes.SHA256()))
    (folder/'ca').mkdir()
    (folder/'ca/ca.crt').write_bytes(ca.public_bytes(serialization.Encoding.PEM))
    for kind in ('app', 'usage'):
        target = folder/kind
        target.mkdir()
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'postgres_'+kind)])
        cert = (x509.CertificateBuilder().subject_name(name).issuer_name(ca_name)
                .public_key(key.public_key()).serial_number(x509.random_serial_number())
                .not_valid_before(now-timedelta(minutes=1)).not_valid_after(now+timedelta(days=1))
                .add_extension(x509.SubjectAlternativeName([x509.DNSName('postgres_'+kind)]), critical=False)
                .sign(ca_key, hashes.SHA256()))
        (target/'server.crt').write_bytes(cert.public_bytes(serialization.Encoding.PEM))
        (target/'server.key').write_bytes(key.private_bytes(serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL, serialization.NoEncryption()))


def local_http_json(url: str) -> dict:
    parsed = urlsplit(url)
    if (parsed.scheme != 'http' or parsed.hostname != '127.0.0.1' or not parsed.port
            or parsed.username or parsed.password or parsed.path not in ('/health', '/readiness')
            or parsed.query or parsed.fragment):
        raise ValueError('local_health_url_required')
    class RefuseRedirect(HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None
    with build_opener(ProxyHandler({}), RefuseRedirect()).open(url, timeout=5) as response:
        body = response.read(65537)
        if response.status != 200 or len(body) > 65536:
            raise ValueError('invalid_local_health_response')
        return json.loads(body)


def rehearsal_override(project: str) -> str:
    if not re.fullmatch(r'selfhost_rehearsal_[a-f0-9]{12}', project):
        raise ValueError('invalid_rehearsal_project')
    return '''services:
  postgres_app:
    secrets: !reset []
    volumes:
      - tls_app:/run/postgres-tls:ro
      - dbsecrets:/run/secrets:ro
  postgres_usage:
    secrets: !reset []
    volumes:
      - tls_usage:/run/postgres-tls:ro
      - dbsecrets:/run/secrets:ro
  api:
    image: __REHEARSAL_IMAGE__
    secrets: !reset []
    volumes: !override
      - runtime:/run/secrets:ro
      - ca:/run/selfhost-ca:ro
  usage_ops:
    image: __REHEARSAL_IMAGE__
    secrets: !reset []
    volumes: !override
      - ops:/run/secrets:ro
      - ca:/run/selfhost-ca:ro
  reverse_proxy:
    ports: !override ["127.0.0.1::8080"]
    networks: !override [api_egress, proxy_loopback]
networks:
  api_egress: {internal: true}
  proxy_loopback: {}
volumes:
  tls_app: {}
  tls_usage: {}
  ca: {}
  runtime: {}
  ops: {}
  dbsecrets: {}
'''.replace('__REHEARSAL_IMAGE__', project + '-api:local')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--hold-seconds', type=int, default=0, choices=range(0, 301), metavar='0..300')
    args = parser.parse_args(argv)
    project = 'selfhost_rehearsal_' + uuid4().hex[:12]
    report_dir = ROOT/'.local/selfhost-preparation'
    report_dir.mkdir(parents=True, exist_ok=True)
    evidence = {'project': project, 'status': 'running', 'application_schema': 'empty_connectivity_fixture',
                'external_egress': 'api_all_networks_internal_proxy_only_loopback_bridge'}
    evidence_path = report_dir/'compose-rehearsal.json'
    system_keys = {'PATH', 'HOME', 'USERPROFILE', 'APPDATA', 'LOCALAPPDATA', 'SYSTEMROOT',
                   'WINDIR', 'COMSPEC', 'PATHEXT', 'TEMP', 'TMP', 'PROGRAMDATA', 'LANG', 'LC_ALL', 'TZ'}
    environment = {key: value for key, value in os.environ.items()
                   if key.upper() in system_keys or key in {'SELFHOST_BACKEND_IMAGE', 'SELFHOST_PROXY_IMAGE'}}
    # Inspect only local context metadata before pinning every daemon operation.
    endpoint = os.environ.get('DOCKER_HOST', '').strip()
    if endpoint and not re.fullmatch(r'(unix://[^\r\n\x00]+|npipe:////\./pipe/[A-Za-z0-9_.-]+)', endpoint):
        raise ValueError('local_docker_socket_required')
    from scripts.rehearse_usage_database import local_docker_prefix
    try:
        prefix = local_docker_prefix(environment)
    except RuntimeError:
        raise ValueError('local_docker_socket_required') from None
    if not re.fullmatch(r'(unix:///[^\r\n\x00]+|npipe:////\./pipe/[A-Za-z0-9_.-]+)', prefix[-1]):
        raise ValueError('local_docker_socket_required')
    _LOCAL_DOCKER[:] = prefix
    for name in ('SELFHOST_BACKEND_IMAGE', 'SELFHOST_PROXY_IMAGE'):
        if not re.fullmatch(r'[\w./:-]+@sha256:[a-f0-9]{64}', environment.get(name, '')):
            raise RuntimeError('immutable_local_image_required:' + name)
    for reference in (PG, environment['SELFHOST_BACKEND_IMAGE'], environment['SELFHOST_PROXY_IMAGE']):
        run(['docker','image','inspect',reference,'--format','{{.Id}}'],env=environment,timeout=15)
    evidence['images'] = {'postgres': PG, 'backend': environment['SELFHOST_BACKEND_IMAGE'],
                          'proxy': environment['SELFHOST_PROXY_IMAGE']}
    volumes = [project+'_'+name for name in ('tls_app', 'tls_usage', 'ca', 'runtime', 'ops', 'dbsecrets')]
    with tempfile.TemporaryDirectory(prefix='proptech-selfhost-rehearsal-') as temporary:
        temp = Path(temporary)
        certificates(temp)
        for directory in ('runtime', 'ops', 'dbsecrets'):
            (temp/directory).mkdir()
        passwords = {name: secrets.token_urlsafe(36) for name in ('app_admin_password', 'app_runtime_password',
                     'usage_admin_password', 'usage_migration_password', 'usage_runtime_password')}
        for name, value in passwords.items():
            directory = 'ops' if name == 'usage_runtime_password' else 'dbsecrets'
            (temp/directory/name).write_text(value, encoding='utf-8')
        runtime = {
            'app_database_url': 'postgresql://app_runtime:'+passwords['app_runtime_password']+'@postgres_app/proptech_app',
            'usage_database_url': 'postgresql://proptech_usage_runtime_v1:'+passwords['usage_runtime_password']+'@postgres_usage/proptech_api_usage',
            'usage_peer_hmac_key': secrets.token_hex(32), 'pilot_session_signing_key': secrets.token_hex(32),
        }
        _DUMMY_REDACTIONS.extend([*passwords.values(), *runtime.values()])
        for name, value in runtime.items():
            (temp/'runtime'/name).write_text(value, encoding='utf-8')
        (temp/'ops/usage_bootstrap_database_url').write_text('postgresql://usage_migration:'+passwords['usage_migration_password']+'@postgres_usage/proptech_api_usage', encoding='utf-8')
        (temp/'runtime.env').write_text('CORS_ALLOWED_ORIGINS=https://staging.example.invalid\nPUBLIC_APP_BASE_URL=https://staging.example.invalid\nAPI_ALLOWED_HOSTS=localhost,127.0.0.1\n', encoding='utf-8')
        environment.update(SELFHOST_SECRETS_DIR=str(temp/'dbsecrets'), SELFHOST_TLS_DIR=str(temp),
                           SELFHOST_RUNTIME_ENV_FILE=str(temp/'runtime.env'))
        # Windows bind mounts cannot enforce Unix private-key ownership. The
        # rehearsal seeds exclusively owned Docker volumes with exact Unix modes.
        override = rehearsal_override(project)
        override_path = temp/'rehearsal.yml'
        override_path.write_text(override, encoding='utf-8')
        compose = ['docker', 'compose', '-p', project, '-f', str(ROOT/'docker-compose.selfhost.yml'), '-f', str(override_path)]
        def dc(*command, **kwargs):
            return run([*compose, *command], env=environment, **kwargs)
        try:
            for name in volumes:
                run(['docker','volume','create','--label','proptech.selfhost.rehearsal='+project,name], env=environment)
            mounts = []
            for name in ('tls_app','tls_usage','ca','runtime','ops','dbsecrets'):
                mounts += ['--mount', 'type=volume,src='+project+'_'+name+',dst=/seed/'+name]
            seed = '''set -eu
cp /input/app/* /seed/tls_app/
cp /input/usage/* /seed/tls_usage/
cp /input/ca/* /seed/ca/
cp /input/runtime/* /seed/runtime/
cp /input/ops/* /seed/ops/
cp /input/dbsecrets/* /seed/dbsecrets/
chown -R 70:70 /seed/tls_app /seed/tls_usage /seed/dbsecrets
chown -R 10001:10001 /seed/runtime /seed/ops
chmod 700 /seed/runtime /seed/ops /seed/dbsecrets
chmod 600 /seed/runtime/* /seed/ops/* /seed/dbsecrets/* /seed/tls_app/server.key /seed/tls_usage/server.key
chmod 755 /seed/ca
chmod 444 /seed/ca/ca.crt /seed/tls_app/server.crt /seed/tls_usage/server.crt
'''
            run(['docker','run','--rm','--pull=never','--network=none','--user=0',
                 '--read-only','--cap-drop=ALL','--cap-add=CHOWN','--cap-add=FOWNER','--cap-add=DAC_OVERRIDE',
                 '--security-opt=no-new-privileges:true','--memory=128m','--cpus=0.5','--pids-limit=64',
                 '--mount','type=bind,src='+str(temp)+',dst=/input,readonly', *mounts,
                 '--entrypoint','sh',PG,'-c',seed],env=environment)
            config = json.loads(dc('config','--format','json').stdout)
            for service in ('postgres_app','postgres_usage','api'):
                assert not config['services'][service].get('ports')
            assert all(config['networks'][name]['internal'] for name in ('app_db','usage_db','api_egress'))
            assert config['services']['api']['image'] == project + '-api:local'
            # Profile services appear only when explicitly included in config.
            ops_config = json.loads(dc('--profile','usage_ops','config','--format','json').stdout)
            assert ops_config['services']['usage_ops']['image'] == project + '-api:local'
            evidence['compose_config'] = 'pass'
            evidence['rehearsal_image'] = project + '-api:local'
            dc('build','--pull=false','api', timeout=180)
            dc('up','-d','--no-build','--pull','never','--wait','--wait-timeout','90','postgres_app','postgres_usage', timeout=120)
            ops = ['--profile','usage_ops','run','--rm','--no-deps','usage_ops']
            evidence['freshness'] = json.loads(dc(*ops,'preflight').stdout)
            dc(*ops,'bootstrap','--execute','--acknowledge-fresh-dedicated','--expected-database','proptech_api_usage','--release-version',RELEASE)
            duplicate = dc(*ops,'preflight',check=False)
            assert duplicate.returncode != 0
            evidence['repeat_preflight'] = 'refused'
            dc(*ops,'bootstrap','--operation','provision-runtime','--execute','--acknowledge-fresh-dedicated','--expected-database','proptech_api_usage')
            evidence['activation'] = json.loads(dc(*ops,'activate-runtime').stdout)
            dc('up','-d','--no-build','--pull','never','--wait','--wait-timeout','90','api','reverse_proxy',timeout=120)
            evidence['runtime_probe'] = json.loads(dc('exec','-T','api','python','scripts/ops/selfhost_runtime.py','runtime-probe').stdout)
            evidence['readonly_health'] = json.loads(dc('exec','-T','api','python','scripts/ops/selfhost_runtime.py','health').stdout)
            # Negative proof on this new disposable fixture only. Restore the
            # exact grant before backup capture or any subsequent checks.
            admin = ['exec','-T','--user','postgres','postgres_usage','psql','-X','-q',
                     '-v','ON_ERROR_STOP=1','-d','proptech_api_usage']
            dc(*admin, data='REVOKE DELETE ON api_usage.flush_batches FROM proptech_usage_writer;\n')
            try:
                unhealthy = dc('exec','-T','api','python','scripts/ops/selfhost_runtime.py','health',check=False)
                assert unhealthy.returncode != 0
                assert json.loads(unhealthy.stdout)['reason'] == 'usage_writer_grant_unavailable'
            finally:
                dc(*admin, data='GRANT DELETE ON api_usage.flush_batches TO proptech_usage_writer;\n')
            evidence['health_missing_writer_grant'] = 'refused_then_exact_grant_restored'
            direct = dc('exec','-T','api','python','-c',
                "from pathlib import Path; import os,psycopg; from scripts.ops.selfhost_runtime import runtime_environment; os.environ.update(runtime_environment(Path('/run/secrets')));\nfor name in ('DATABASE_URL','API_USAGE_DATABASE_URL'):\n with psycopg.connect(os.environ[name],sslmode='verify-full',connect_timeout=3) as c:\n  assert c.execute('SELECT ssl FROM pg_stat_ssl WHERE pid=pg_backend_pid()').fetchone()==(True,)\n try:\n  psycopg.connect(os.environ[name],sslmode='disable',connect_timeout=3)\n except psycopg.OperationalError: pass\n else: raise SystemExit(1)\nfrom services.usage_guard import PostgresQuotaGuard; from services.usage_principal import UsagePrincipal; from uuid import uuid4; assert PostgresQuotaGuard(os.environ['API_USAGE_DATABASE_URL']).consume(UsagePrincipal('anon:'+'a'*64,'anonymous','a'*64),'places','request',uuid4())=='admitted'; print('tls_required_direct_runtime_quota_passed')")
            assert 'tls_required_direct_runtime_quota_passed' in direct.stdout
            evidence['tls_and_quota'] = 'verify_full_both_clusters_cleartext_refused_real_runtime_consume'
            address = dc('port','reverse_proxy','8080').stdout.strip()
            evidence['proxy_binding'] = address
            assert address.startswith('127.0.0.1:')
            for path in ('health','readiness'):
                payload = local_http_json('http://'+address+'/'+path)
                if path=='health':
                    assert payload['mode']=='preview' and payload['readiness']=='ready'
                else:
                    assert payload['runtime']=={'mode':'preview','ready':True}
                evidence[path] = payload
            # Actual lifespan refusal: remove only usage URL in a NEW one-shot
            # disposable API container's tmpfs, keeping every other file valid.
            missing = dc('run','--rm','--no-deps','--entrypoint','python','api','-c',
                "import os,shutil,subprocess; from pathlib import Path; p=Path('/tmp/missing'); p.mkdir(); [shutil.copy(x,p/x.name) for x in Path('/run/secrets').iterdir() if x.name!='usage_database_url']; r=subprocess.run(['python','scripts/ops/selfhost_runtime.py','validate-secrets','--secrets-dir',str(p)],capture_output=True,text=True); assert r.returncode==1; from scripts.ops.selfhost_runtime import runtime_environment; e=runtime_environment(Path('/run/secrets')); e.pop('API_USAGE_DATABASE_URL'); os.environ.clear();os.environ.update(e); from fastapi.testclient import TestClient; from backend.api_main import app;\ntry:\n with TestClient(app): pass\nexcept RuntimeError:\n print('missing_usage_url_refused');raise SystemExit(0)\nraise SystemExit(1)")
            assert 'missing_usage_url_refused' in missing.stdout
            evidence['missing_usage_url'] = 'real_lifespan_refused_no_fallback'
            evidence['containers'] = {service: dc('ps','-q',service).stdout.strip() for service in ('postgres_app','postgres_usage','api','reverse_proxy')}
            evidence['status']='pass'
            evidence_path.write_text(json.dumps(evidence,indent=2)+'\n',encoding='utf-8')
            print(json.dumps({'status':'pass','evidence':str(evidence_path),'project':project}),flush=True)
            if args.hold_seconds:
                time.sleep(args.hold_seconds)
        except BaseException:
            evidence['status'] = 'failed'
            raise
        finally:
            dc('down','--volumes','--remove-orphans',timeout=90,check=False)
            # Remove only exact locally generated UUID-scoped volume names.
            for name in volumes:
                run(['docker','volume','rm',name],env=environment,check=False)
            remaining = []
            for command in (
                ['ps','-aq','--filter','label=com.docker.compose.project='+project],
                ['network','ls','-q','--filter','label=com.docker.compose.project='+project],
                ['volume','ls','-q','--filter','label=com.docker.compose.project='+project],
                ['volume','ls','-q','--filter','label=proptech.selfhost.rehearsal='+project],
            ):
                remaining.extend(run(['docker',*command],env=environment).stdout.split())
            run(['docker','image','rm',project + '-api:local'],env=environment,check=False)
            evidence['cleanup']='verified_no_project_resources' if not remaining else 'failed_resources_remain'
            evidence_path.write_text(json.dumps(evidence,indent=2)+'\n',encoding='utf-8')
            if remaining:
                raise RuntimeError('local_rehearsal_cleanup_incomplete')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
