#!/usr/bin/env python3
"""Operator-only Stage 2 clean build and bounded activation. No credential arguments.

Default --plan is read-only except private sanitized evidence. --apply first prints
that exact plan and requires a terminal confirmation. Never run this as the agent.
All captured Docker output stays in memory, is scanned, and is never echoed.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import fcntl
import hashlib
import hmac
import json
import os
from pathlib import Path, PurePosixPath
import re
import resource
import select
import selectors
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time
import uuid

REPO = Path(__file__).resolve().parents[2]
sys.dont_write_bytecode = True
sys.path.insert(0, str(REPO))
from services.selfhost_secret_files import (CORE, DB_FILES, SecretRefused, inventory,
    open_directory, read_secret, sensitive_name, validate_local_guards, validate_nonsecret_env)

SOURCE_COMMIT = 'd8a93492eb900550ce490990fade7726766b18da'
FRONTEND_SHA256 = '0f70629890b72a0a82e91972cc032c04b658b26c265373cb711cf576bfbf8fcc'
DATA_ROOT = '/srv/proptech-data/DB'
ETC = Path('/etc/proptech-selfhost')
STAGED = Path('/run/proptech-selfhost/secrets')
STORE = ETC / 'secrets'
DESTINATION = ETC / 'stage2-secrets.override.yml'
EVIDENCE = Path('/var/backups/proptech-selfhost/stage2-activation')
SERVICES = ('postgres_app', 'postgres_usage', 'api', 'reverse_proxy')
RECREATE = ('postgres_app', 'postgres_usage', 'api')
FILES = (REPO / 'docker-compose.selfhost.yml', ETC / 'datasets.override.yml',
    ETC / 'valuation.override.yml', ETC / 'local-frontend.override.yml')
REQUIRED_ENV = {
    'APP_ENV': 'preview', 'RELEASE_COMMIT_SHA': SOURCE_COMMIT, 'POSTGRES_SSLMODE': 'verify-full', 'PGSSLROOTCERT': '/run/selfhost-ca/ca.crt',
    'PLVR_DATA_BACKEND': 'blue', 'VALUATION_DEMO_MODE': 'false', 'PLVR_SERVING_EXCLUSIONS_ENABLED': 'true',
    'WRA_FLOOD_LOCAL_ROOT': '/srv/proptech/datasets/wra/flood/v1',
    'EARTH_ENGINE_SATELLITE_REFERENCE_V1': 'false',
    **{'ANTI_ABUSE_' + k + '_DISABLED': 'true' for k in ('MARKET_OPS', 'GEOCODING', 'PLACES', 'ROUTES', 'SATELLITE', 'LOCATION', 'PARCEL', 'ARDSWC', 'LIQUEFACTION', 'NLSC', 'TGOS')},
    **{k: 'false' for k in ('FEATURE_IDENTITY_V1', 'FEATURE_LEGACY_CASE_IMPORT_V1', 'FEATURE_CASE_PARCEL_SET_V1', 'TAIPEI_PLANNING_READ_V1')},
}


class Refused(Exception):
    """Fixed reason codes only. Never include external output or exceptions."""


def require(value, reason):
    if not value: raise Refused(reason)


def allowed_source(name):
    p = PurePosixPath(name)
    if p.is_absolute() or '..' in p.parts or not p.parts: return False
    if any(c.startswith('.') or c in {'secrets', 'credentials', '__pycache__', 'node_modules', 'tests'} for c in p.parts): return False
    if p.suffix.lower() in {'.pem', '.key', '.p12', '.pfx', '.dump', '.backup', '.db', '.sqlite', '.sqlite3', '.pyc'}: return False
    if re.search(r'(?:service.account|application_default_credentials)', name, re.I): return False
    if name == 'backend/build-identity.json': return False
    if name in {'frontend_next/lib/taiwan-admin-areas.json', 'infra/selfhost/Dockerfile'}: return True
    return p.parts[0] in {'backend', 'services', 'config', 'database', 'models', 'rules', 'data', 'scripts'}


def secret_names(service):
    rows = service.get('secrets', [])
    result = []
    for row in rows:
        require(isinstance(row, dict), 'secret_model_invalid')
        name = row.get('source')
        require(row.get('target', name) in {name, '/run/secrets/'+str(name)}, 'secret_alias_forbidden')
        result.append(name)
    require(len(result) == len(set(result)), 'duplicate_secret_mount')
    return set(result)


def validate_models(before, after, image):
    """Reject any change outside the exact image/entrypoint/secret-list delta."""
    require(set(after) == set(before), 'compose_topology_changed')
    require({k: v for k, v in before.items() if k not in {'services','secrets'}} ==
            {k: v for k, v in after.items() if k not in {'services','secrets'}}, 'compose_global_changed')
    # Compose omits definitions that became unused after exact secret-list
    # replacement. Remaining sources must be identical; no new secret authority.
    require(set(after.get('secrets',{})) <= set(before.get('secrets',{})) and
            all(before['secrets'][k] == v for k,v in after.get('secrets',{}).items()),
            'compose_secret_definition_changed')
    services = after['services']
    require(set(services) == set(before['services']) and set(services) <= set(SERVICES) | {'usage_ops'}, 'service_set_changed')
    require(all(k in services for k in SERVICES), 'service_missing')
    for name in ('postgres_app', 'postgres_usage'):
        old, new = before['services'][name], services[name]
        require({k:v for k,v in old.items() if k != 'secrets'} == {k:v for k,v in new.items() if k != 'secrets'}, 'database_config_changed')
        require(not new.get('ports') and new.get('network_mode') != 'host', 'postgres_public')
        kind = name.removeprefix('postgres_')
        require(secret_names(new) == {kind + '_admin_password'}, 'database_secret_separation')
        require(set(new.get('networks', {})) == {kind + '_db'} and after['networks'][kind + '_db'].get('internal') is True, 'database_network_invalid')
        require(len([v for v in new['volumes'] if v['target'] == '/var/lib/postgresql/data' and v['type'] == 'volume']) == 1, 'database_volume_invalid')
    for name in set(services) - set(RECREATE):
        require(services[name] == before['services'][name], 'unintended_service_change')
    proxy = services['reverse_proxy']
    ports = proxy.get('ports', [])
    require(len(ports) == 1 and ports[0].get('host_ip') == '127.0.0.1' and str(ports[0].get('published')) == '8080' and ports[0].get('target') == 8080, 'proxy_not_loopback')
    old, new = before['services']['api'], services['api']
    mutable = {'image', 'pull_policy', 'entrypoint', 'command', 'environment', 'secrets', 'healthcheck'}
    require({k:v for k,v in old.items() if k not in mutable} == {k:v for k,v in new.items() if k not in mutable}, 'api_infrastructure_changed')
    require(new.get('image') == image and not new.get('ports') and new.get('network_mode') != 'host', 'api_image_or_ports_invalid')
    require(new.get('entrypoint') == ['python', 'scripts/ops/professor_runtime_entrypoint.py'] and new.get('command') == ['api'], 'entrypoint_invalid')
    require(new.get('healthcheck', {}).get('test') == ['CMD', 'python', 'scripts/ops/professor_runtime_entrypoint.py', 'health'], 'healthcheck_invalid')
    require(secret_names(new) == set(CORE), 'api_secret_separation')
    env = new.get('environment', {})
    require(all(env.get(k) == v for k, v in REQUIRED_ENV.items()), 'provider_or_local_guard_invalid')
    require(not any(sensitive_name(k) or k.startswith('NEXT_PUBLIC_') or k.startswith('PG') and k != 'PGSSLROOTCERT' for k in env), 'credential_environment_forbidden')
    require(all(env.get(k) == v for k, v in old.get('environment', {}).items() if k not in REQUIRED_ENV and k != 'RELEASE_COMMIT_SHA'), 'unreviewed_environment_delta')
    require(set(env) - set(old.get('environment', {})) <= set(REQUIRED_ENV) | {'RELEASE_COMMIT_SHA'}, 'unreviewed_environment_addition')
    mounts = new.get('volumes', [])
    for target in ('/srv/proptech/datasets/processed/nlsc/village-boundary/v1/features.json.gz', '/srv/proptech/datasets/wra/flood/v1'):
        found = [v for v in mounts if v.get('target') == target]
        require(len(found) == 1 and found[0].get('read_only') is True and found[0].get('source', '').startswith(DATA_ROOT + '/'), 'dataset_mount_invalid')
    require(not any('Crucial X9' in str(v) or str(v.get('source', '')).startswith('/dev/') for s in services.values() for v in s.get('volumes', [])), 'forbidden_runtime_mount')
    for name in CORE:
        require(after['secrets'][name].get('file') == str(STAGED / name), 'secret_source_invalid')


def recreate_command(prefix, service):
    require(service in RECREATE, 'unapproved_recreation')
    return [*prefix, 'up', '-d', '--no-deps', '--no-build', '--pull', 'never', '--force-recreate', service]


def artifact_probe_code(reference):
    expected = {r['scenario']: (r['artifact_sha256'], r['feature_count']) for r in reference['wra']}
    return '''import hashlib,json
from pathlib import Path
from services.wra_flood_runtime import WraFloodRuntime,CANONICAL_SCENARIOS
from services.nlsc_village_boundary_runtime import NlscVillageBoundaryRuntime
def deny():
    raise RuntimeError('network_forbidden')
expected = '''+repr(expected)+'''
assert set(expected)==set(CANONICAL_SCENARIOS)
rows=[]
for scenario in CANONICAL_SCENARIOS:
    runtime=WraFloodRuntime(client_factory=deny)
    loaded=runtime.load_scenario(scenario)
    assert loaded.storage_backend=='local'
    assert (loaded.artifact_sha256,loaded.feature_count)==expected[scenario]
    point=loaded.geometries[0].representative_point()
    assert runtime.query_point(scenario,point.x,point.y)['matched'] is True
    assert runtime.query_point(scenario,0,0)['matched'] is False
    rows.append({'scenario':scenario,'sha256':loaded.artifact_sha256,'features':loaded.feature_count})
path=Path('/srv/proptech/datasets/processed/nlsc/village-boundary/v1/features.json.gz')
assert hashlib.sha256(path.read_bytes()).hexdigest()=='1b1db799708e61ee337d1ac6ae0fa359eafd8c28b8cf297d80b0c83cb5a2b03d'
nlsc=NlscVillageBoundaryRuntime(artifact_path=path,expected_sha256='1b1db799708e61ee337d1ac6ae0fa359eafd8c28b8cf297d80b0c83cb5a2b03d')
assert nlsc.resolve(latitude=25.035570879000026,longitude=121.4525876531026)['district_code']=='65000050016'
print(json.dumps({'status':'PASS','wra':rows,'nlsc_sha256_verified':True,'network_calls':0}))
'''


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


MAX_CAPTURE_BYTES = 64 * 1024 * 1024


def bounded_capture(args, *, env, cwd, data=None, timeout=180):
    """Bounded in-memory stdout/stderr; no raw output files, no shell."""
    require(data is None or len(data)<=1024*1024,'command_input_limit')
    p=subprocess.Popen(args,stdin=subprocess.PIPE if data is not None else subprocess.DEVNULL,
        stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env,cwd=cwd)
    selector=selectors.DefaultSelector()
    buffers={'stdout':bytearray(),'stderr':bytearray()}
    pending=memoryview(data or b'')
    try:
        for name,stream in [('stdout',p.stdout),('stderr',p.stderr)]:
            os.set_blocking(stream.fileno(),False);selector.register(stream,selectors.EVENT_READ,name)
        if p.stdin:
            os.set_blocking(p.stdin.fileno(),False)
            if pending:selector.register(p.stdin,selectors.EVENT_WRITE,'stdin')
            else:p.stdin.close()
        deadline=time.monotonic()+timeout
        while selector.get_map():
            remaining=deadline-time.monotonic()
            require(remaining>0,'command_timeout')
            for key,_ in selector.select(min(remaining,0.25)):
                if key.data=='stdin':
                    try:written=os.write(key.fd,pending[:65536]);pending=pending[written:]
                    except BrokenPipeError:pending=memoryview(b'')
                    if not pending:selector.unregister(key.fileobj);key.fileobj.close()
                else:
                    chunk=os.read(key.fd,65536)
                    if not chunk:selector.unregister(key.fileobj)
                    else:
                        require(len(buffers[key.data])+len(chunk)<=MAX_CAPTURE_BYTES,'command_output_limit')
                        buffers[key.data].extend(chunk)
        require(deadline-time.monotonic()>0,'command_timeout')
        code=p.wait(timeout=max(0.01,deadline-time.monotonic()))
        return code,bytes(buffers['stdout']),bytes(buffers['stderr'])
    finally:
        selector.close()
        if p.poll() is None:p.kill()
        p.wait(timeout=10)
        for stream in (p.stdin,p.stdout,p.stderr):
            if stream and not stream.closed:stream.close()


class DeadlineReader:
    def __init__(self,stream,timeout):
        self.fd=stream.fileno();self.deadline=time.monotonic()+timeout
        os.set_blocking(self.fd,False)

    def read(self,size=65536):
        while True:
            remaining=self.deadline-time.monotonic()
            require(remaining>0,'image_export_timeout')
            ready,_,_=select.select([self.fd],[],[],min(remaining,1))
            if ready:return os.read(self.fd,min(max(size,1),65536))


def installed_values():
    """Current protected values and installer replacement backups, internally."""
    result={}
    fd=open_directory(STORE,private=True)
    try:names=os.listdir(fd)
    finally:os.close(fd)
    for name in names:
        if name=='backups':
            folder=STORE/name
            fd=open_directory(folder,private=True)
            try:backups=os.listdir(fd)
            finally:os.close(fd)
            for backup in backups:
                result[str(folder/backup)]=read_secret(folder,backup,gid=0,mode=0o600,limit=1024*1024,multiline=True)
        else:
            result[str(STORE/name)]=read_secret(STORE,name,gid=0,mode=0o600,limit=1024*1024,multiline=True)
    return result


def file_metadata(path):
    s = path.lstat()
    require(stat.S_ISREG(s.st_mode) and s.st_nlink == 1, 'regular_file_required')
    return {'uid': s.st_uid, 'gid': s.st_gid, 'mode': oct(stat.S_IMODE(s.st_mode)), 'device': s.st_dev, 'inode': s.st_ino, 'size': s.st_size}


def stable_database_snapshot(value):
    # Container IP and TLS negotiation may change; serving facts never may.
    return json.loads(json.dumps(value), object_hook=lambda d:{k:v for k,v in d.items()
        if k not in {'server_ip','tls_version','tls_cipher','checked_at'}})


class Activation:
    def __init__(self):
        self.run_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:12]
        self.image = 'proptech-professor-api:stage2-' + self.run_id.lower()
        self.backend = 'proptech-professor-backend:stage2-' + self.run_id.lower()
        self.report = {'schema': 'professor-stage2-activation-v1', 'run_id': self.run_id, 'status': 'PARTIAL', 'source_commit': SOURCE_COMMIT, 'stage2_complete': False, 'production_ready': False, 'provider_activation': False, 'database_schema_or_source_mutations': False, 'normal_application_telemetry_may_write': True}
        self.maintenance = False
        self.override_installed = False
        self.transients = set()
        self.scanner = None
        self.env = {'PATH': os.defpath, 'HOME': '/root', 'LANG': 'C.UTF-8', 'DOCKER_HOST': 'unix:///var/run/docker.sock', 'DOCKER_BUILDKIT': '1', 'COMPOSE_PROFILES': ''}
        self.root = None
        self.original_hashes = {}

    def run(self, args, *, data=None, timeout=180, scan=True):
        if args[0] == 'git': args = ['git', '-c', 'safe.directory='+str(REPO), *args[1:]]
        code,stdout,stderr=bounded_capture(args,env=self.env,cwd=REPO,data=data,timeout=timeout)
        if scan and self.scanner:
            self.scanner.check_bytes(stdout); self.scanner.check_bytes(stderr)
        require(code == 0, 'command_failed_output_suppressed')
        return stdout

    def docker(self, *args, **kwargs):
        return self.run(['docker', *args], **kwargs)

    def json_command(self, args):
        try: return json.loads(self.run(args))
        except (ValueError, UnicodeError): raise Refused('invalid_json_output') from None

    def save(self, name, value):
        raw = (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()
        if self.scanner: self.scanner.check_bytes(raw)
        path = self.root / name
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'wb') as f: f.write(raw)

    def checkpoint(self, phase):
        self.report['phase'] = phase
        print(json.dumps({'phase': phase, 'status': 'running'}), flush=True)

    def prefix(self, extra=None):
        cmd = ['docker', 'compose', '--project-name', 'proptech-selfhost', '--project-directory', str(REPO), '--env-file', str(ETC/'compose.env')]
        for path in (*FILES, *((extra,) if extra else ())): cmd.extend(['-f', str(path)])
        return cmd

    def inspect(self, service):
        ids = self.service_ids(service)
        require(len(ids) == 1, 'container_identity_ambiguous')
        result = json.loads(self.docker('inspect', ids[0]))[0]
        require(result['Config']['Labels']['com.docker.compose.project'] == 'proptech-selfhost' and result['Config']['Labels']['com.docker.compose.service'] == service, 'container_label_invalid')
        return result

    def service_ids(self, service):
        require(service in SERVICES,'unapproved_service_discovery')
        ids = self.docker('ps', '-aq', '--no-trunc', '--filter', 'label=com.docker.compose.project=proptech-selfhost',
                         '--filter', 'label=com.docker.compose.service='+service).decode().split()
        require(all(re.fullmatch(r'[0-9a-f]{64}',s) for s in ids),'container_id_invalid')
        return ids

    def halt_consumers(self):
        """Stop every owned API/proxy match, even if recreation left zero/many.

        Never assert stopped without re-inspection. This path does not inspect
        Config.Env, so a credential-scan refusal cannot prevent emergency stop.
        """
        result={'status':'CONFIRMED_STOPPED','services':{}}
        for service in ('reverse_proxy','api'):
            try:
                ids=self.service_ids(service)
                failures=0
                for ident in ids:
                    try:self.docker('stop','--time','20',ident,timeout=45)
                    except BaseException: failures+=1
                current=self.service_ids(service)
                running=[]
                for ident in current:
                    state=self.docker('inspect','--format','{{.State.Running}}',ident).decode().strip()
                    require(state in {'true','false'},'invalid_container_state')
                    if state=='true':running.append(ident)
                if running:result['status']='UNCERTAIN'
                result['services'][service]={'matches':len(current),'running':len(running),'stop_errors':failures}
            except BaseException:
                result['status']='UNCERTAIN'
                result['services'][service]={'state':'UNVERIFIED'}
        return result

    def config_hashes(self, extra=None):
        lines=self.run([*self.prefix(extra),'config','--hash','*']).decode().splitlines()
        hashes={}
        for line in lines:
            fields=line.split()
            require(len(fields)==2 and fields[0] in set(SERVICES)|{'usage_ops'} and re.fullmatch(r'[a-f0-9]{64}',fields[1]),'compose_hash_output_invalid')
            require(fields[0] not in hashes,'duplicate_compose_hash')
            hashes[fields[0]]=fields[1]
        require(set(SERVICES)<=set(hashes),'compose_hash_missing')
        return hashes

    def snapshot(self):
        return {s: self.inspect(s) for s in SERVICES}

    def assert_live(self, objects, *, after=False, proxy_stopped=False):
        for name, item in objects.items():
            if name=='reverse_proxy' and proxy_stopped:
                require(item['State']['Running'] is False,'proxy_started_before_acceptance')
            else:
                require(item['State']['Running'] and item['State'].get('Health', {}).get('Status') == 'healthy', 'container_not_healthy')
            require(item['HostConfig'].get('NetworkMode') != 'host', 'host_network_forbidden')
            if name.startswith('postgres_') or name == 'api': require(not item['HostConfig'].get('PortBindings'), 'public_container_port')
            if name == 'reverse_proxy':
                require(item['HostConfig'].get('PortBindings') == {'8080/tcp': [{'HostIp': '127.0.0.1', 'HostPort': '8080'}]}, 'proxy_not_loopback')
            for mount in item['Mounts']:
                require('Crucial X9' not in mount['Source'] and not mount['Source'].startswith('/dev/'), 'forbidden_active_mount')
            if name.startswith('postgres_'):
                data = [m for m in item['Mounts'] if m['Destination'] == '/var/lib/postgresql/data']
                require(len(data) == 1 and data[0]['Type'] == 'volume', 'existing_volume_required')
                if after: require(data == self.data_mounts[name], 'database_volume_identity_changed')
                for network in item['NetworkSettings']['Networks']:
                    config = json.loads(self.docker('network', 'inspect', network))[0]
                    require(config.get('Internal') is True, 'postgres_network_not_internal')
        listeners = self.run(['ss', '-H', '-lnt']).decode().splitlines()
        for line in listeners:
            fields = line.split()
            if len(fields) < 4: continue
            local = fields[3]
            require(not local.endswith(':5432'), 'postgres_host_listener')
            if local.endswith(':8080'): require(local == '127.0.0.1:8080', 'public_8080_listener')

    def sanitized_containers(self, objects):
        return {s: {'id': x['Id'], 'image_id': x['Image'], 'health': x['State'].get('Health', {}).get('Status'),
            'data_mount': [m for m in x['Mounts'] if m['Destination'] == '/var/lib/postgresql/data'],
            'mounts': [{k:m.get(k) for k in ('Type', 'Source', 'Destination', 'RW')} for m in x['Mounts']],
            'ports': x['HostConfig'].get('PortBindings')} for s,x in objects.items()}

    def probe(self, mode, api=None):
        code = self.probe_source
        self.scanner.check_bytes(code)
        target = api or self.inspect('api')['Id']
        if mode == '--api-host':
            raw = self.run([sys.executable, '-B', '-', '--api'], data=code, timeout=180)
        else:
            raw = self.docker('exec', '-i', target, 'python', '-B', '-', mode, data=code, timeout=180)
        result = json.loads(raw)
        require(result.get('status') == 'PASS', 'focused_probe_failed')
        return result

    def preflight(self):
        from scripts.ops.professor_server_secrets import check_backing_storage, validate_host
        from services.professor_activation_scan import SecretScanner
        require(os.geteuid() == 0, 'operator_root_required')
        require(REPO == Path('/home/andy/proptech-ai-copilot') and digest(REPO/'frontend_next/next-env.d.ts') == FRONTEND_SHA256, 'checkout_or_frontend_changed')
        head = self.run(['git', 'rev-parse', 'HEAD']).decode().strip()
        require(head == SOURCE_COMMIT, 'preactivation_commit_changed')
        require(not DESTINATION.exists(), 'stage2_override_already_exists')
        for path in (REPO, ETC, STAGED, EVIDENCE): check_backing_storage(path)
        host_validation = validate_host()  # Existing install validation; never installation/staging.
        values = installed_values()
        self.scanner = SecretScanner(values.values())
        self.probe_source = (REPO/'scripts/ops/professor_stage2_probe.py').read_bytes()
        self.scanner.check_bytes(self.probe_source)
        self.secret_values = values
        # No real value leaves this operator process; no value/hash is persisted.
        self.host_secrets = {n: file_metadata(STAGED/n) for n in (*CORE, *DB_FILES)}
        EVIDENCE.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.close(open_directory(EVIDENCE, private=True))
        self.root = EVIDENCE / self.run_id
        self.root.mkdir(mode=0o700)
        configdir = self.root/'docker-config'; configdir.mkdir(mode=0o700)
        self.env['DOCKER_CONFIG'] = str(configdir)
        info = json.loads(self.docker('info', '--format', '{{json .}}'))
        check_backing_storage(Path(info['DockerRootDir']))
        for path in (Path('/var/lib/containerd'),Path('/run/containerd')):
            if path.exists():check_backing_storage(path)
        require('rootless' not in str(info.get('SecurityOptions', [])), 'unexpected_docker_daemon')
        self.before = self.snapshot(); self.assert_live(self.before)
        self.run(['git','diff','--exit-code',SOURCE_COMMIT,'--','backend','services','config','database','models','rules','data','infra/selfhost','scripts/ops/professor_runtime_entrypoint.py','scripts/ops/selfhost_runtime.py','scripts/ops/professor_server_secrets.py'])
        self.data_mounts = {s: [m for m in self.before[s]['Mounts'] if m['Destination']=='/var/lib/postgresql/data'] for s in ('postgres_app','postgres_usage')}
        for s in self.data_mounts:
            for m in self.before[s]['Mounts']:
                if m.get('RW') and m.get('Source'):check_backing_storage(Path(m['Source']))
            self.docker('exec', self.before[s]['Id'], 'test', '-s', '/var/lib/postgresql/data/PG_VERSION')
        actual_files = self.before['api']['Config']['Labels'].get('com.docker.compose.project.config_files', '').split(',')
        require(actual_files == [str(p) for p in FILES], 'unexpected_compose_file_set')
        self.before_model = self.json_command([*self.prefix(), 'config', '--format', 'json'])
        self.original_service_hashes=self.config_hashes()
        require(all(self.before[s]['Config']['Labels'].get('com.docker.compose.config-hash')==self.original_service_hashes[s]
                    for s in SERVICES),'running_compose_config_drift')
        require(all(self.before_model['services'][s]['image'] == self.before[s]['Config']['Image']
                    for s in SERVICES), 'running_compose_image_drift')
        for service, mounts in self.data_mounts.items():
            declared = [v for v in self.before_model['services'][service]['volumes']
                        if v['target']=='/var/lib/postgresql/data']
            require(len(declared)==1 and declared[0]['type']=='volume','declared_volume_invalid')
            name = self.before_model['volumes'][declared[0]['source']]['name']
            require(mounts[0]['Name']==name,'running_declared_volume_drift')
            volume = json.loads(self.docker('volume','inspect',name))[0]
            require(volume['Name']==name and volume['Mountpoint']==mounts[0]['Source']
                    and volume['Driver']=='local' and not volume.get('Options'),
                    'existing_volume_authority_invalid')
        for path in (*FILES, ETC/'compose.env', ETC/'runtime.env'):
            require(not path.is_symlink() and path.is_file(), 'configuration_path_unsafe')
            if path.is_relative_to(ETC):
                m = file_metadata(path)
                require(m['uid'] == 0 and int(m['mode'],8) in (0o600,0o640), 'configuration_permissions_unsafe')
            raw = path.read_bytes(); self.scanner.check_bytes(raw)
            self.original_hashes[str(path)] = hashlib.sha256(raw).hexdigest()
        original = (REPO/'infra/selfhost/professor-secrets.override.yml').read_text()
        require(original.count('${PROFESSOR_SERVER_API_IMAGE:?reviewed Stage 2 API image required}') == 1, 'override_template_changed')
        self.override_bytes = original.replace(
            '${PROFESSOR_SERVER_API_IMAGE:?reviewed Stage 2 API image required}', self.image
        ).replace('    environment:\n', '    environment:\n      RELEASE_COMMIT_SHA: "'+SOURCE_COMMIT+'"\n').encode()
        self.candidate_override = self.root/'stage2-secrets.override.yml'
        self.scanner.check_bytes(self.override_bytes)
        self.candidate_override.write_bytes(self.override_bytes)
        # Pin public release identity only; this file contains no credential values.
        self.env['PROFESSOR_SERVER_API_IMAGE'] = self.image
        self.env['RELEASE_COMMIT_SHA'] = SOURCE_COMMIT
        self.after_model = self.json_command([*self.prefix(self.candidate_override), 'config', '--format', 'json'])
        validate_models(self.before_model, self.after_model, self.image)
        self.save('host-validation.json', host_validation)
        self.save('containers-before.json', self.sanitized_containers(self.before))
        self.save('secret-host-metadata.json', self.host_secrets)
        self.save('configuration-sha256.json', self.original_hashes)
        self.save('compose-before.json', self.before_model)
        self.save('compose-after.json', self.after_model)
        self.save('change-plan.json', {'recreate': list(RECREATE), 'restart_only': ['reverse_proxy'],
            'containers': {s:self.before[s]['Id'] for s in SERVICES}, 'unchanged_database_volumes': self.data_mounts,
            'compose_files_after': [str(p) for p in (*FILES,DESTINATION)],
            'recreate_commands': [recreate_command(self.prefix(DESTINATION),s) for s in RECREATE],
            'stop_commands': [['docker','stop','--time','30',self.before[s]['Id']] for s in ('reverse_proxy','api')],
            'proxy_restart_command': ['docker','start',self.before['reverse_proxy']['Id']],
            'secret_mounts_after': {s:sorted(secret_names(self.after_model['services'][s])) for s in RECREATE},
            'api_image_after': self.image, 'source_commit': SOURCE_COMMIT,
            'changes': ['Build from pinned official Python base, exact existing package versions, committed public source',
                        'Add one final /etc override; preserve existing four configs and all databases',
                        'Renew API five secret inodes; PostgreSQL admin-only mounts',
                        'Stop proxy during maintenance; restart only after focused acceptance'],
            'no_database_sql_mutation': True, 'optional_providers_disabled': True, 'market_ops_disabled': True,
            'rollback': 'Original four-file compose, pinned old image IDs, same named volumes; proxy last after acceptance',
            'evidence': str(self.root)})
        self.write_rollback()
        print((self.root/'change-plan.json').read_text(), flush=True)

    def write_rollback(self):
        rollback = {'original_compose_prefix': self.prefix(), 'old_images': {s:self.before[s]['Image'] for s in RECREATE},
            'old_image_tags': {s:self.before[s]['Config']['Image'] for s in RECREATE}, 'volumes': self.data_mounts,
            'files_unchanged': self.original_hashes, 'proxy_stays_stopped_until_api_ready': True,
            'no_database_restore_or_migration': True}
        self.save('rollback.json', rollback)
        backup = self.root/'etc-before'; backup.mkdir(mode=0o700)
        for p in (*FILES[1:], ETC/'compose.env', ETC/'runtime.env'):
            shutil.copyfile(p, backup/p.name); os.chmod(backup/p.name, 0o600)
        text = ('# Stage 2 rollback\n\nThe runner automatically attempts bounded rollback after a runtime failure. '
            'It stops proxy/API, recreates only the same three containers from the original four-file model, '
            'verifies the same volume identities, TLS and serving filters, then starts the existing proxy last. '
            'No key is rotated; no database backup restore, migration or data deletion occurs.\n\n'
            'rollback.json records exact original command, old immutable image IDs, and unchanged volume mounts. '
            'etc-before/ holds the pre-change nonsecret configuration. Do not source credential files. '
            'If rollback is refused or fails, leave API and proxy stopped. Do not improvise a volume replacement. '
            'Repair the reported invariant before restarting. The four original /etc files remain untouched.\n')
        (self.root/'ROLLBACK.md').write_text(text)

    def stable(self):
        require(all(digest(Path(p)) == h for p,h in self.original_hashes.items()), 'configuration_changed_concurrently')
        require(digest(REPO/'frontend_next/next-env.d.ts') == FRONTEND_SHA256, 'frontend_changed')
        require({n:file_metadata(STAGED/n) for n in (*CORE,*DB_FILES)} == self.host_secrets, 'staged_secret_changed')
        from scripts.ops.professor_server_secrets import validate_host
        validate_host()
        values=installed_values()
        require(set(values)==set(self.secret_values),'persistent_secret_set_changed')
        require(all(hmac.compare_digest(values[n].encode(),v.encode()) for n,v in self.secret_values.items()), 'persistent_secret_changed')

    def original_live_unchanged(self):
        environment=self.env
        try:
            self.env={k:v for k,v in environment.items() if k not in {'RELEASE_COMMIT_SHA','PROFESSOR_SERVER_API_IMAGE'}}
            require(self.config_hashes()==self.original_service_hashes,'original_compose_model_changed')
        finally:self.env=environment
        for service in SERVICES:
            current=self.inspect(service)
            require(current['Id']==self.before[service]['Id'] and
                    current['Config']['Labels'].get('com.docker.compose.config-hash')==self.original_service_hashes[service],
                    'containers_changed_concurrently')

    def start_transient(self, args):
        name = 'proptech-stage2-' + uuid.uuid4().hex[:16]
        self.transients.add(name)
        return self.docker('run', '--name', name, '--label', 'proptech.stage2.run='+self.run_id, *args, timeout=1200)

    def build(self, *, source_commit=SOURCE_COMMIT):
        # Shared by later operator activations; the Stage 2 default stays frozen.
        require(re.fullmatch(r'[0-9a-f]{40}', source_commit), 'build_commit_invalid')
        self.checkpoint('clean-build')
        context = self.root/'context'; context.mkdir(mode=0o700)
        listing = self.run(['git','ls-tree','-rz','--full-tree',source_commit]).split(b'\0')
        for entry in listing:
            if not entry: continue
            meta, name_raw = entry.split(b'\t',1); mode, kind, blob = meta.decode().split()
            name = name_raw.decode('utf-8')
            if not allowed_source(name): continue
            require(kind == 'blob' and mode in ('100644','100755'), 'nonregular_build_source')
            raw = self.run(['git','cat-file','blob',blob]); self.scanner.check_bytes(raw)
            path = context/name; path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            path.write_bytes(raw)
        require((context/'backend/api_main.py').is_file(), 'build_source_incomplete')
        version = self.docker('exec', self.before['api']['Id'], 'python', '-c', 'import sys;print(str(sys.version_info.major)+"."+str(sys.version_info.minor))').decode().strip()
        require(version == '3.12', 'working_python_abi_unexpected')
        packages = json.loads(self.docker('exec', self.before['api']['Id'], 'python', '-c',
            'import importlib.metadata,json;print(json.dumps(sorted((d.metadata["Name"],d.version) for d in importlib.metadata.distributions())))'))
        require(packages and len(packages) <= 400, 'package_inventory_invalid')
        lock = []
        for name, version in packages:
            require(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,100}',name) and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9.+!_-]{0,100}',version), 'package_identifier_invalid')
            lock.append(name+'=='+version)
        require(len(lock) == len(set(s.lower().replace('_','-') for s in lock)), 'duplicate_package')
        self.packages = packages
        (context/'_stage2.lock').write_text('\n'.join(lock)+'\n')
        self.save('package-lock.json', {'packages': packages, 'source': 'working API distribution metadata; no URLs or environment'})
        self.docker('pull','python:3.12-slim',timeout=600)
        base = json.loads(self.docker('image','inspect','python:3.12-slim'))[0]
        pins = [p for p in base.get('RepoDigests',[]) if re.fullmatch(r'(?:docker.io/library/)?python@sha256:[a-f0-9]{64}',p)]
        require(len(pins) == 1, 'base_digest_unresolved')
        base_pin = pins[0]
        wheels = context/'_stage2_wheels'; wheels.mkdir(mode=0o755)
        self.start_transient(['--network','bridge','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges',
            '--pids-limit','128','--memory','1g','--tmpfs','/tmp:rw,noexec,nosuid,size=256m',
            '--mount','type=bind,src='+str(wheels)+',dst=/wheels',
            '--mount','type=bind,src='+str(context/'_stage2.lock')+',dst=/requirements.lock,readonly',
            base_pin,'python','-I','-m','pip','--isolated','download','--disable-pip-version-check','--no-cache-dir',
            '--only-binary=:all:','--no-deps','--index-url','https://pypi.org/simple','--dest','/wheels','-r','/requirements.lock'])
        hashes = {}
        for wheel in wheels.iterdir():
            require(wheel.is_file() and not wheel.is_symlink() and wheel.suffix == '.whl', 'unexpected_wheel_file')
            with wheel.open('rb') as f: self.scanner.check_stream(f)
            hashes[wheel.name] = digest(wheel)
        require(len(hashes) == len(packages), 'wheel_set_incomplete')
        self.save('wheel-sha256.json', hashes)
        dockerfile = ('FROM '+base_pin+'\nWORKDIR /app\n'
            'RUN --mount=type=bind,source=_stage2_wheels,target=/wheels,readonly '
            '--mount=type=bind,source=_stage2.lock,target=/requirements.lock,readonly '
            'python -I -m pip --isolated install --disable-pip-version-check --no-cache-dir --no-index --no-deps --find-links=/wheels -r /requirements.lock\n'
            'COPY backend backend\nCOPY services services\nCOPY config config\nCOPY database database\n'
            'COPY models models\nCOPY rules rules\nCOPY data data\nCOPY scripts scripts\nCOPY frontend_next/lib/taiwan-admin-areas.json frontend_next/lib/taiwan-admin-areas.json\n'
            'RUN python scripts/write_backend_build_identity.py --commit '+source_commit+'\n')
        # Root Python modules used by the app are copied individually, never COPY . .
        for p in context.glob('*.py'): dockerfile += 'COPY '+p.name+' '+p.name+'\n'
        (context/'_stage2.Dockerfile').write_text(dockerfile)
        for p in context.rglob('*'):
            if p.is_file() and p.suffix != '.whl': self.scanner.check_bytes(p.read_bytes())
        self.save('context-sha256.json', {p.relative_to(context).as_posix():digest(p)
            for p in context.rglob('*') if p.is_file()})
        # COPY preserves context modes; the non-root API must read public source.
        for path in context.rglob('*'):
            os.chmod(path, 0o755 if path.is_dir() else 0o644)
        self.docker('build','--no-cache','--network','none','--pull=false','-t',self.backend,'-f',str(context/'_stage2.Dockerfile'),str(context),timeout=1800)
        backend_info=json.loads(self.docker('image','inspect',self.backend))[0]
        backend_id=backend_info['Id']
        self.docker('build','--no-cache','--network','none','--pull=false','--build-arg','SELFHOST_BACKEND_IMAGE='+self.backend,
            '-t',self.image,'-f',str(context/'infra/selfhost/Dockerfile'),str(context),timeout=900)
        api_info=json.loads(self.docker('image','inspect',self.image))[0]
        self.image_id=api_info['Id']
        require(json.loads(self.docker('image','inspect',self.backend))[0]['Id']==backend_id and
                api_info['RootFS']['Layers'][:len(backend_info['RootFS']['Layers'])]==backend_info['RootFS']['Layers'],
                'clean_backend_ancestry_changed')
        self.scan_image()
        self.save('build.json', {'base_digest': base_pin, 'backend_image':backend_id,'api_image':self.image_id,
            'source_commit':source_commit,'clean_committed_context':True,'offline_install_build':True,'private_registry_credentials_used':False})

    def scan_image(self):
        self.checkpoint('image-layer-scan')
        # Never save an unverified export to disk. The scanner consumes all layers.
        p = subprocess.Popen(['docker','image','save',self.image_id], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, env=self.env)
        try:
            result = self.scanner.scan_image_archive(DeadlineReader(p.stdout,1800))
            require(p.wait(timeout=30) == 0, 'image_export_failed')
        except BaseException:
            p.kill(); p.wait(); raise
        finally:
            p.stdout.close()
        self.docker('image','history','--no-trunc','--format','{{json .}}',self.image_id)
        self.docker('image','inspect',self.image_id)
        self.save('image-scan.json', {'status':'PASS','scan':result,'full_history_and_config_scanned':True,
            'build_context_scanned':True,'build_output_scanned_in_memory':True,
            'coverage':'Known installed credential values, supported encodings/password variants and private-key signatures; not a proof against arbitrary unknown encodings',
            'image_id':self.image_id})

    def candidate(self):
        self.checkpoint('clean-image-validation')
        api = self.after_model['services']['api']
        flags = ['--network','none','--read-only','--user','10001:10001','--cap-drop','ALL','--security-opt','no-new-privileges',
            '--pids-limit','128','--memory','2g','--tmpfs','/tmp:rw,noexec,nosuid,size=128m,uid=10001,gid=10001']
        for name in CORE:
            flags += ['--mount','type=bind,src='+str(STAGED/name)+',dst=/run/secrets/'+name+',readonly']
        for mount in api.get('volumes',[]):
            require(mount.get('read_only') is True, 'candidate_writable_mount')
            flags += ['--mount','type=bind,src='+mount['source']+',dst='+mount['target']+',readonly']
        for key,value in api['environment'].items(): flags += ['--env',key+'='+value]
        output = self.start_transient([*flags,'--entrypoint','python',self.image_id,'scripts/ops/professor_runtime_entrypoint.py','validate'])
        data = json.loads(output)
        require(data.get('status') == 'pass' and data.get('core_files') == 5 and data.get('values_returned') is False, 'candidate_configuration_failed')
        packages = json.loads(self.start_transient([*flags,'--entrypoint','python',self.image_id,'-c',
            'import importlib.metadata,json;print(json.dumps(sorted((d.metadata["Name"],d.version) for d in importlib.metadata.distributions())))']))
        require(packages == self.packages, 'candidate_package_versions_changed')
        self.start_transient([*flags,'--entrypoint','python',self.image_id,'-I','-m','pip','check'])
        smoke = ('import os,json;from pathlib import Path;from services.selfhost_secret_files import runtime_environment;'
            'os.environ.update(runtime_environment(Path("/run/secrets"),dict(os.environ)));'
            'import backend.api_main;from services.production_identity import backend_identity;'
            'x=backend_identity();assert x["commit_sha"]=="'+SOURCE_COMMIT+'";print(json.dumps({"status":"PASS","app_import":True,"build_commit":x["commit_sha"]}))')
        smoke_result = json.loads(self.start_transient([*flags,'--entrypoint','python',self.image_id,'-B','-c',smoke]))
        require(smoke_result.get('status') == 'PASS', 'candidate_import_failed')
        reference = json.loads(self.run(['git', 'show', SOURCE_COMMIT+':reports/professor-final-integration/reference-artifact-validation.json']))
        artifacts = json.loads(self.start_transient([*flags,'--entrypoint','python',self.image_id,'-B','-c',artifact_probe_code(reference)]))
        require(artifacts.get('status') == 'PASS', 'candidate_artifact_failed')
        self.save('candidate-artifacts.json',artifacts)
        self.save('candidate-validation.json', {'configuration':data,'import_smoke':smoke_result,'network':'none'})

    def wait_healthy(self, service):
        deadline = time.monotonic()+240
        while time.monotonic() < deadline:
            item = self.inspect(service)
            require(item['State'].get('Status') not in ('dead','exited'), 'container_exited')
            if item['State'].get('Health',{}).get('Status') == 'healthy': return
            time.sleep(2)
        raise Refused('container_health_timeout')

    def check_mounts(self, objects):
        result = {}
        for service,names,gid in [('api',list(CORE),10001),('postgres_app',['app_admin_password'],70),('postgres_usage',['usage_admin_password'],70)]:
            item = objects[service]
            secret_mounts = [m for m in item['Mounts'] if m['Destination'].startswith('/run/secrets/')]
            require({m['Destination'].split('/')[-1] for m in secret_mounts} == set(names), 'active_secret_list_invalid')
            for m in secret_mounts:
                name=m['Destination'].split('/')[-1]
                require(m['Source'] == str(STAGED/name) and m['RW'] is False, 'active_secret_source_invalid')
            code = 'import os,stat,json;print(json.dumps({n:{"uid":(s:=os.stat("/run/secrets/"+n,follow_symlinks=False)).st_uid,"gid":s.st_gid,"mode":oct(stat.S_IMODE(s.st_mode)),"device":s.st_dev,"inode":s.st_ino,"size":s.st_size} for n in '+repr(names)+'}))'
            if service == 'api': raw=self.docker('exec',item['Id'],'python','-B','-c',code)
            else:
                # PostgreSQL image has no Python. Busybox stat prints metadata only.
                raw=self.docker('exec',item['Id'],'stat','-c','%n %u %g %a %d %i %s',*['/run/secrets/'+n for n in names])
                rows={}
                for line in raw.decode().splitlines():
                    name,uid,group,mode,device,inode,size=line.split()
                    rows[name.split('/')[-1]]={'uid':int(uid),'gid':int(group),'mode':oct(int(mode,8)),'device':int(device),'inode':int(inode),'size':int(size)}
                raw=json.dumps(rows).encode()
            metadata=json.loads(raw)
            for n in names:
                require(metadata[n] == self.host_secrets[n] and metadata[n]['uid']==0 and metadata[n]['gid']==gid and metadata[n]['mode']=='0o440', 'active_secret_inode_or_permission_invalid')
            require(not any(sensitive_name(v.partition('=')[0]) or v.startswith('NEXT_PUBLIC_') for v in item['Config'].get('Env',[]) if v.partition('=')[0] != 'POSTGRES_PASSWORD_FILE'), 'active_credential_environment')
            result[service]=metadata
        return result

    def activate(self):
        self.before_db = self.probe('--database')
        self.save('database-before.json', self.before_db)
        self.save('api-before.json', self.probe('--api'))
        self.build(); self.candidate(); self.stable()
        self.original_live_unchanged()
        for s in RECREATE:
            old_tag = self.before[s]['Config']['Image']
            require(json.loads(self.docker('image','inspect',old_tag))[0]['Id'] == self.before[s]['Image'], 'rollback_image_tag_changed')
        self.checkpoint('controlled-recreation')
        self.maintenance=True
        self.docker('stop','--time','30',self.before['reverse_proxy']['Id'],timeout=60)
        self.docker('stop','--time','30',self.before['api']['Id'],timeout=60)
        self.install_override()
        for service in RECREATE:
            self.run(recreate_command(self.prefix(DESTINATION),service),timeout=180)
            self.wait_healthy(service)
            if service.startswith('postgres_'):
                current = self.inspect(service)
                require([m for m in current['Mounts'] if m['Destination']=='/var/lib/postgresql/data'] == self.data_mounts[service], 'database_volume_identity_changed')
        self.checkpoint('post-activation-acceptance')
        objects={s:self.inspect(s) for s in SERVICES}
        require(objects['api']['Image']==self.image_id, 'running_image_not_candidate')
        self.assert_live(objects,after=True,proxy_stopped=True)
        expected_hashes=self.config_hashes(DESTINATION)
        require(all(objects[s]['Config']['Labels'].get('com.docker.compose.config-hash')==expected_hashes[s]
                    for s in SERVICES),'activated_compose_config_drift')
        mounts=self.check_mounts(objects); self.save('secret-mounts-after.json',mounts)
        after_db=self.probe('--database'); self.save('database-after.json',after_db)
        require(stable_database_snapshot(after_db)==stable_database_snapshot(self.before_db), 'database_readonly_snapshot_changed')
        # Direct API checks while public proxy remains stopped.
        direct=self.probe('--api'); self.save('api-direct-after.json',direct)
        self.docker('start',self.before['reverse_proxy']['Id']);self.wait_healthy('reverse_proxy')
        self.save('api-loopback-after.json', self.probe('--api-host'))
        objects=self.snapshot();self.assert_live(objects,after=True)
        expected_hashes=self.config_hashes(DESTINATION)
        require(all(objects[s]['Config']['Labels'].get('com.docker.compose.config-hash')==expected_hashes[s]
                    for s in SERVICES),'activated_compose_config_drift')
        self.stable()
        for item in objects.values(): self.docker('logs',item['Id'],timeout=120)
        self.save('containers-after.json',self.sanitized_containers(objects))
        require(self.inspect('reverse_proxy')['Id']==self.before['reverse_proxy']['Id'], 'proxy_recreated_unexpectedly')
        self.report.update(status='PASS',phase='complete',stage2_complete=True,api_image_id=self.image_id,
            original_compose_files_preserved=True,configuration_override=str(DESTINATION),
            health_readiness=True,core_secret_mounts=5,postgresql_secret_mounts_each=1,postgresql_private=True,loopback_8080=True,
            market_ops_disabled=True,paid_providers_disabled=True,source_frontend_preserved=True,
            completed_at=datetime.now(timezone.utc).isoformat())
        self.maintenance=False

    def install_override(self):
        # Link an fsynced file exclusively; never overwrite an operator config.
        temporary = ETC / ('.stage2-secrets-'+self.run_id+'.tmp')
        fd=os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o640)
        try:
            with os.fdopen(fd,'wb') as f: f.write(self.override_bytes);f.flush();os.fsync(f.fileno())
            mask=signal.pthread_sigmask(signal.SIG_BLOCK,{signal.SIGINT,signal.SIGTERM})
            try:
                os.link(temporary,DESTINATION,follow_symlinks=False)
                self.override_installed=True
                directory=os.open(ETC,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
                try:os.fsync(directory)
                finally:os.close(directory)
            finally:signal.pthread_sigmask(signal.SIG_SETMASK,mask)
        finally:
            temporary.unlink(missing_ok=True)

    def rollback(self):
        self.checkpoint('rollback')
        # Prevent a second signal interrupting the bounded fail-closed recovery.
        signal.signal(signal.SIGINT,signal.SIG_IGN); signal.signal(signal.SIGTERM,signal.SIG_IGN)
        stopped=self.halt_consumers()
        self.report['rollback_stop']=stopped
        require(stopped['status']=='CONFIRMED_STOPPED','rollback_consumers_not_stopped')
        require(all(stopped['services'][s].get('matches',0)<=1 for s in ('api','reverse_proxy')),'rollback_ambiguous_containers')
        self.stable()
        self.env.pop('RELEASE_COMMIT_SHA',None)
        self.env.pop('PROFESSOR_SERVER_API_IMAGE',None)
        if self.override_installed:
            require(file_metadata(DESTINATION)['uid']==0 and DESTINATION.read_bytes()==self.override_bytes,'rollback_override_changed')
            DESTINATION.unlink()
            self.override_installed=False
            directory=os.open(ETC,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
            try:os.fsync(directory)
            finally:os.close(directory)
        for s in RECREATE:
            require(json.loads(self.docker('image','inspect',self.before[s]['Config']['Image']))[0]['Id']==self.before[s]['Image'], 'rollback_image_changed')
            self.run(recreate_command(self.prefix(),s),timeout=180);self.wait_healthy(s)
        result=self.probe('--database');require(result.get('status')=='PASS','rollback_database_failed')
        require(stable_database_snapshot(result)==stable_database_snapshot(self.before_db),'rollback_database_snapshot_changed')
        for s in self.data_mounts:
            require([m for m in self.inspect(s)['Mounts'] if m['Destination']=='/var/lib/postgresql/data']==self.data_mounts[s],'rollback_volume_changed')
        require(self.probe('--api').get('status')=='PASS','rollback_api_failed')
        self.assert_live(self.snapshot(),after=True,proxy_stopped=True)
        hashes=self.config_hashes()
        require(all(self.inspect(s)['Config']['Labels'].get('com.docker.compose.config-hash')==hashes[s]
                    for s in SERVICES),'rollback_compose_drift')
        require(self.inspect('reverse_proxy')['Id']==self.before['reverse_proxy']['Id'],'rollback_proxy_identity_changed')
        self.docker('start',self.before['reverse_proxy']['Id']);self.wait_healthy('reverse_proxy')
        self.save('api-rollback-loopback.json',self.probe('--api-host'))
        self.assert_live(self.snapshot(),after=True)
        self.report['rollback']='PASS_original_four_file_profile'

    def cleanup(self):
        for name in self.transients:
            try:
                info=json.loads(self.docker('inspect',name))[0]
                if info['Config'].get('Labels',{}).get('proptech.stage2.run')==self.run_id:
                    self.docker('rm','-f',name)
            except Exception: self.report['transient_cleanup']='PARTIAL'
        if self.root:
            context=self.root/'context'
            if context.exists(): shutil.rmtree(context)  # Generated, scanned public context only; never datasets/secrets.

    def publish(self):
        self.save('acceptance.json',self.report)
        public=Path('/tmp')/('professor-stage2-activation-'+uuid.uuid4().hex)
        public.mkdir(mode=0o755);os.chmod(public,0o755)
        self.public_receipt=public
        names=['acceptance.json','change-plan.json','containers-before.json','containers-after.json','host-validation.json',
            'secret-host-metadata.json','secret-mounts-after.json','database-before.json','database-after.json','image-scan.json',
            'candidate-validation.json','candidate-artifacts.json','build.json','api-before.json','api-direct-after.json','api-loopback-after.json']
        for name in names:
            p=self.root/name
            if not p.exists(): continue
            raw=p.read_bytes();self.scanner.check_bytes(raw)
            fd=os.open(public/name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o644)
            with os.fdopen(fd,'wb') as f:f.write(raw)
            os.chmod(public/name,0o644)
        print(json.dumps({'status':self.report['status'],'evidence':str(self.root),'sanitized_receipt':str(public)}),flush=True)

    def invalidate_receipt(self):
        """Preserve an unpublished attempt; canonical receipts must say FAILED."""
        for folder,mode in [(self.root,0o600),(getattr(self,'public_receipt',None),0o644)]:
            if folder is None:continue
            target=folder/'acceptance.json'
            if target.exists():
                require(file_metadata(target)['uid']==0,'receipt_owner_changed')
                os.link(target,folder/'acceptance-unpublished.json',follow_symlinks=False)
                target.unlink()
            raw=(json.dumps(self.report,sort_keys=True)+'\n').encode()
            self.scanner.check_bytes(raw)
            fd=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,mode)
            with os.fdopen(fd,'wb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
            os.chmod(target,mode)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    group=parser.add_mutually_exclusive_group()
    group.add_argument('--plan',action='store_true');group.add_argument('--apply',action='store_true')
    # Do not reflect unknown arguments, which might be accidental credentials.
    if sys.argv[1:] not in ([],['--plan'],['--apply']):
        print('{"status":"REFUSED","reason_code":"invalid_arguments"}');return 1
    args=parser.parse_args()
    if os.geteuid()!=0:
        print('{"status":"REFUSED","reason_code":"operator_root_required"}');return 1
    os.umask(0o077);resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    runner=Activation()
    lock=None
    try:
        # Pin a root-owned no-follow lock; operator tickets are never inherited.
        from scripts.ops.professor_server_secrets import check_backing_storage
        check_backing_storage(Path('/run'))
        lock=os.open('/run/proptech-stage2-activation.lock',os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600)
        meta=os.fstat(lock);require(meta.st_uid==0 and stat.S_ISREG(meta.st_mode) and meta.st_nlink==1 and stat.S_IMODE(meta.st_mode)==0o600,'lock_unsafe')
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        runner.preflight()
        if args.apply:
            require(sys.stdin.isatty() and sys.stdout.isatty(),'interactive_terminal_required')
            print('Review the exact plan above. Type ACTIVATE to build, verify, and apply this bounded change:',flush=True)
            require(sys.stdin.readline().strip()=='ACTIVATE','operator_confirmation_missing')
            def interrupted(signum,frame): raise Refused('operator_interrupted')
            signal.signal(signal.SIGINT,interrupted);signal.signal(signal.SIGTERM,interrupted)
            runner.activate()
        else:
            runner.report.update(status='PLAN_ONLY',phase='preflight',stage2_complete=False)
    except BaseException as exc:
        reason=str(exc) if isinstance(exc,(Refused,SecretRefused)) else getattr(exc,'reason_code','operation_failed_details_suppressed')
        if not isinstance(reason,str) or not re.fullmatch(r'[a-z0-9_]+',reason): reason='operation_failed_details_suppressed'
        runner.report.update(status='FAILED',reason_code=reason,stage2_complete=False)
        if runner.maintenance:
            try: runner.rollback()
            except BaseException:
                runner.report['rollback']='FAILED'
                runner.report['emergency_stop']=runner.halt_consumers()
    finally:
        try: runner.cleanup()
        except BaseException:
            runner.report.update(status='PARTIAL',stage2_complete=False,cleanup='FAILED')
        if runner.root and runner.scanner:
            try:runner.publish()
            except BaseException:
                runner.report.update(status='FAILED',stage2_complete=False,reason_code='receipt_unavailable')
                try:runner.invalidate_receipt()
                except BaseException:pass  # Failure exit remains authoritative if evidence storage itself failed.
                print('{"status":"FAILED","reason_code":"receipt_unavailable"}',flush=True)
        else: print(json.dumps({'status':'REFUSED','reason_code':runner.report.get('reason_code','preflight_failed')}),flush=True)
        if lock is not None: os.close(lock)
    return 0 if runner.report['status'] in ('PASS','PLAN_ONLY') else 1


if __name__=='__main__':
    raise SystemExit(main())
