"""Synthetic activation boundary tests. Never use Docker or protected host paths."""
import copy
import importlib.util
from pathlib import Path
import pytest

PATH = Path(__file__).parents[1] / 'scripts/ops/professor_stage2_activation.py'
spec = importlib.util.spec_from_file_location('stage2_activation', PATH)
a = importlib.util.module_from_spec(spec)
spec.loader.exec_module(a)


def models():
    before = {'services': {}, 'networks': {'app_db': {'internal': True}, 'usage_db': {'internal': True}, 'api_egress': {}}, 'volumes': {'app_data': {}, 'usage_data': {}}, 'secrets': {n: {'file': '/run/proptech-selfhost/secrets/' + n} for n in [*a.CORE, *a.DB_FILES]}}
    for kind in ('app', 'usage'):
        before['services']['postgres_' + kind] = {'image': 'postgres@sha256:' + 'a'*64, 'volumes': [{'type': 'volume', 'source': kind + '_data', 'target': '/var/lib/postgresql/data'}], 'networks': {kind + '_db': {}}, 'environment': {'POSTGRES_PASSWORD_FILE': '/run/secrets/' + kind + '_admin_password'}, 'secrets': [{'source': kind + '_admin_password', 'target': kind + '_admin_password'}, {'source': 'app_runtime_password' if kind == 'app' else 'usage_migration_password'}]}
    env = dict(a.REQUIRED_ENV)
    before['services']['api'] = {'image': 'old:local', 'networks': {'app_db': {}, 'usage_db': {}, 'api_egress': {}}, 'secrets': [{'source': n, 'target': n} for n in a.CORE], 'environment': env, 'volumes': [{'type': 'bind', 'source': a.DATA_ROOT + '/nlsc.json.gz', 'target': '/srv/proptech/datasets/processed/nlsc/village-boundary/v1/features.json.gz', 'read_only': True}, {'type': 'bind', 'source': a.DATA_ROOT + '/wra', 'target': '/srv/proptech/datasets/wra/flood/v1', 'read_only': True}, {'type': 'bind', 'source': '/run/proptech-selfhost/tls/ca.crt', 'target': '/run/selfhost-ca/ca.crt', 'read_only': True}]}
    before['services']['reverse_proxy'] = {'image': 'nginx@sha256:' + 'b'*64, 'ports': [{'host_ip': '127.0.0.1', 'published': '8080', 'target': 8080}], 'networks': {'api_egress': {}}}
    after = copy.deepcopy(before)
    for kind in ('app', 'usage'): after['services']['postgres_' + kind]['secrets'] = [{'source': kind + '_admin_password', 'target': kind + '_admin_password'}]
    after['services']['api'].update(image='new:local', entrypoint=['python', 'scripts/ops/professor_runtime_entrypoint.py'], command=['api'], healthcheck={'test': ['CMD', 'python', 'scripts/ops/professor_runtime_entrypoint.py', 'health']})
    return before, after


def test_exact_safe_delta_is_accepted():
    before, after = models()
    a.validate_models(before, after, 'new:local')


@pytest.mark.parametrize('mutation', ['volume', 'network', 'pg_image', 'proxy_port', 'secret_alias', 'secret_target', 'alias_env', 'paid', 'x9', 'writable_dataset', 'unknown_service'])
def test_unsafe_compose_delta_is_refused(mutation):
    before, after = models()
    svc = after['services']
    if mutation == 'volume': svc['postgres_app']['volumes'][0]['source'] = 'fresh_volume'
    if mutation == 'network': after['networks']['app_db']['internal'] = False
    if mutation == 'pg_image': svc['postgres_app']['image'] = 'postgres:latest'
    if mutation == 'proxy_port': svc['reverse_proxy']['ports'][0]['host_ip'] = '0.0.0.0'
    if mutation == 'secret_alias': svc['api']['secrets'].append({'source': 'app_admin_password'})
    if mutation == 'secret_target': svc['api']['secrets'][0]['target'] = '/run/secrets/other_name'
    if mutation == 'alias_env': svc['api']['environment']['GOOGLE_MAPS_API_KEY'] = 'synthetic-only'
    if mutation == 'paid': svc['api']['environment']['ANTI_ABUSE_PLACES_DISABLED'] = 'false'
    if mutation == 'x9': svc['api']['volumes'][0]['source'] = '/run/media/andy/Crucial X9/DB/a'
    if mutation == 'writable_dataset': svc['api']['volumes'][0]['read_only'] = False
    if mutation == 'unknown_service': svc['extra'] = {}
    with pytest.raises(a.Refused): a.validate_models(before, after, 'new:local')


def test_unsafe_existing_pg_mount_is_refused_even_without_delta():
    before, after = models()
    for model in (before, after): model['services']['postgres_app']['ports'] = [{'published': '5432'}]
    with pytest.raises(a.Refused): a.validate_models(before, after, 'new:local')


@pytest.mark.parametrize('name', ['frontend_next/.env.local', '.git/config', 'secrets/api.txt', 'data/proptech.db', 'frontend_next/next-env.d.ts', 'a/../backend/a.py'])
def test_build_context_forbids_private_or_unrelated_names(name):
    assert not a.allowed_source(name)


@pytest.mark.parametrize('name', ['backend/api_main.py', 'services/selfhost_secret_files.py', 'config/professor-server-credentials.json', 'frontend_next/lib/taiwan-admin-areas.json', 'scripts/ops/professor_runtime_entrypoint.py'])
def test_build_context_keeps_required_public_source(name):
    assert a.allowed_source(name)


def test_recreation_commands_are_bounded_and_volume_preserving():
    cmd = a.recreate_command(['docker', 'compose'], 'postgres_app')
    assert cmd == ['docker', 'compose', 'up', '-d', '--no-deps', '--no-build', '--pull', 'never', '--force-recreate', 'postgres_app']
    with pytest.raises(a.Refused): a.recreate_command(['docker', 'compose'], 'reverse_proxy')


def test_source_has_no_privileged_execution_at_import_or_volume_destruction():
    import ast
    tree = ast.parse(PATH.read_text())
    assert not any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in {'eval', 'exec'} for n in ast.walk(tree))
    assert 'down -v' not in PATH.read_text()


def test_real_compose_merge_obeys_bounded_delta_with_synthetic_config(tmp_path):
    import json
    import os
    import subprocess
    runtime = tmp_path/'runtime.env'
    runtime.write_text('\n'.join(k+'='+v for k,v in a.REQUIRED_ENV.items())+'\n'
        'ANTI_ABUSE_ENFORCEMENT_MODE=local_only\nTAIPEI_PLANNING_SOURCE_MODE=manual_evidence\n')
    # Exact existing Stage 1 nonsecret mode names failed before any Compose call.
    # Project identity stays explicitly pinned, independent of the checkout name.
    a.validate_nonsecret_env(runtime.read_text())
    dotenv = tmp_path/'compose.env'; dotenv.write_text('')
    original = tmp_path/'existing.json'
    source = a.DATA_ROOT+'/Cloudflare R2/proptech-government-data/processed/'
    original.write_text(json.dumps({'services': {'api': {'image':'old:local', 'secrets':['valuation_database_url'], 'volumes':[
        source+'nlsc/village-boundary/v1/features.json.gz:/srv/proptech/datasets/processed/nlsc/village-boundary/v1/features.json.gz:ro',
        source+'wra/flood/v1:/srv/proptech/datasets/wra/flood/v1:ro']}},
        'secrets':{'valuation_database_url': {'file':str(a.STAGED/'valuation_database_url')}}}))
    override = tmp_path/'candidate.yml'
    template = (PATH.parents[2]/'infra/selfhost/professor-secrets.override.yml').read_text()
    override.write_text(template.replace('${PROFESSOR_SERVER_API_IMAGE:?reviewed Stage 2 API image required}','new:local')
        .replace('    environment:\n','    environment:\n      RELEASE_COMMIT_SHA: "'+a.SOURCE_COMMIT+'"\n'))
    env = {'PATH':os.defpath,'SELFHOST_RUNTIME_ENV_FILE':str(runtime),'SELFHOST_SECRETS_DIR':str(a.STAGED),
        'SELFHOST_TLS_DIR':'/run/proptech-selfhost/tls','SELFHOST_BACKEND_IMAGE':'backend@sha256:'+'a'*64,
        'SELFHOST_PROXY_IMAGE':'nginx@sha256:'+'b'*64}
    base = ['docker','compose','--project-name','proptech-selfhost','--env-file',str(dotenv),'-f',str(PATH.parents[2]/'docker-compose.selfhost.yml'),'-f',str(original)]
    def parse(extra):
        result = subprocess.run([*base,*extra,'config','--format','json'],env=env,capture_output=True,text=True,timeout=15)
        assert result.returncode == 0
        return json.loads(result.stdout)
    before,after=parse([]),parse(['-f',str(override)])
    a.validate_models(before,after,'new:local')
    assert before['name']==after['name']=='proptech-selfhost'
    assert before['volumes']['app_data']['name']==after['volumes']['app_data']['name']=='proptech-selfhost_app_data'
    assert before['volumes']['usage_data']['name']==after['volumes']['usage_data']['name']=='proptech-selfhost_usage_data'
    hashes=subprocess.run([*base,'config','--hash','*'],env=env,capture_output=True,text=True,timeout=15)
    assert hashes.returncode==0
    fields=[line.split() for line in hashes.stdout.splitlines()]
    assert all(len(row)==2 and len(row[1])==64 for row in fields)
    assert set(a.SERVICES)<={row[0] for row in fields}


def test_generated_artifact_probe_is_valid_python_and_has_no_network_fallback():
    import ast
    reference={'wra':[{'scenario':'6h-150mm','artifact_sha256':'a'*64,'feature_count':1}]}
    code=a.artifact_probe_code(reference)
    ast.parse(code)
    assert 'client_factory=deny' in code
    assert "['matched'] is False" in code


def fake_activation(monkeypatch, *, candidate_failure=False):
    import json
    events=[]
    runner=a.Activation()
    runner.before={s:{'Id':s+'-old','Image':'sha256:'+s,'Config':{'Image':s+':old','Labels':{'com.docker.compose.config-hash':'hash'}},'Mounts':[],'State':{'Health':{'Status':'healthy'}},'HostConfig':{'PortBindings':{}}} for s in a.SERVICES}
    runner.image_id='sha256:new'
    runner.before_db={'status':'PASS'}
    runner.data_mounts={s:[] for s in ('postgres_app','postgres_usage')}
    runner.candidate_override=Path('/synthetic/override.yml')
    recreated=set()
    def inspect(service):
        result=copy.deepcopy(runner.before[service])
        if service in recreated:
            result['Id']=service+'-new'
            if service=='api': result['Image']=runner.image_id
        return result
    def docker(*args,**kwargs):
        events.append(tuple(args[:3]))
        if args[:2]==('image','inspect'):
            service=args[2].split(':')[0]
            return json.dumps([{'Id':runner.before[service]['Image']}]).encode()
        return b''
    def run(args,**kwargs):
        service=args[-1]
        assert service in a.RECREATE
        recreated.add(service);events.append(('recreate',service));return b''
    monkeypatch.setattr(runner,'docker',docker)
    monkeypatch.setattr(runner,'run',run)
    monkeypatch.setattr(runner,'inspect',inspect)
    monkeypatch.setattr(runner,'snapshot',lambda:{s:inspect(s) for s in a.SERVICES})
    monkeypatch.setattr(runner,'save',lambda *args:None)
    monkeypatch.setattr(runner,'checkpoint',lambda phase:events.append(('phase',phase)))
    monkeypatch.setattr(runner,'stable',lambda:None)
    monkeypatch.setattr(runner,'original_live_unchanged',lambda:None)
    monkeypatch.setattr(runner,'config_hashes',lambda *args:{s:'hash' for s in a.SERVICES})
    monkeypatch.setattr(runner,'build',lambda:events.append(('build',)))
    def candidate():
        events.append(('candidate',))
        if candidate_failure: raise a.Refused('candidate_rejected')
    monkeypatch.setattr(runner,'candidate',candidate)
    monkeypatch.setattr(runner,'probe',lambda mode:events.append(('probe',mode)) or {'status':'PASS'})
    monkeypatch.setattr(runner,'wait_healthy',lambda s:events.append(('healthy',s)))
    monkeypatch.setattr(runner,'check_mounts',lambda _:events.append(('mounts',)) or {})
    monkeypatch.setattr(runner,'assert_live',lambda *args,**kwargs:events.append(('boundary',)))
    monkeypatch.setattr(runner,'install_override',lambda:events.append(('install_override',)))
    return runner,events


def test_candidate_failure_never_stops_a_running_service(monkeypatch):
    runner,events=fake_activation(monkeypatch,candidate_failure=True)
    with pytest.raises(a.Refused):runner.activate()
    assert not runner.maintenance
    assert not any(e[0] in {'stop','recreate','install_override'} for e in events)


def test_only_reviewed_services_recreated_and_proxy_starts_after_direct_acceptance(monkeypatch):
    runner,events=fake_activation(monkeypatch)
    runner.activate()
    assert [e[1] for e in events if e[0]=='recreate']==list(a.RECREATE)
    start=events.index(('start','reverse_proxy-old'))
    assert events.index(('mounts',))<start
    assert events.index(('probe','--api'),events.index(('mounts',)))<start
    assert events.index(('probe','--api-host'))>start
    assert runner.report['status']=='PASS'


def test_candidate_uses_the_committed_fastapi_module():
    import subprocess
    expected='backend/api_main.py'
    # The publication branch is a squash and CI checks it out shallowly. The
    # archived operator release pin is deliberately not part of that history.
    # Verify the committed module in this checkout, without repinning activation.
    result=subprocess.run(['git','cat-file','-e','HEAD:'+expected],cwd=PATH.parents[2],capture_output=True)
    assert result.returncode==0
    source=PATH.read_text()
    assert "context/'"+expected+"'" in source
    assert 'import backend.api_main;' in source
    assert 'import backend.main;' not in source


def test_bounded_capture_limits_output_without_returning_partial_bytes(monkeypatch,tmp_path):
    import os,sys
    monkeypatch.setattr(a,'MAX_CAPTURE_BYTES',1024)
    with pytest.raises(a.Refused,match='command_output_limit'):
        a.bounded_capture([sys.executable,'-c','import sys;sys.stdout.write("x"*4096)'],env={'PATH':os.defpath},cwd=tmp_path)


def test_bounded_capture_has_deadline(tmp_path):
    import os,sys
    with pytest.raises(a.Refused,match='command_timeout'):
        a.bounded_capture([sys.executable,'-c','import time;time.sleep(30)'],env={'PATH':os.defpath},cwd=tmp_path,timeout=0.05)


def test_bounded_capture_transmits_input_and_both_streams(tmp_path):
    import os,sys
    code,out,err=a.bounded_capture([sys.executable,'-c','import sys;x=sys.stdin.buffer.read();sys.stdout.buffer.write(x);sys.stderr.write("diagnostic")'],env={'PATH':os.defpath},cwd=tmp_path,data=b'synthetic input')
    assert (code,out,err)==(0,b'synthetic input',b'diagnostic')


def test_image_export_deadline_does_not_wait_for_eof():
    import os
    reader,writer=os.pipe()
    try:
        with os.fdopen(reader,'rb') as stream:
            timed=a.DeadlineReader(stream,0.01)
            with pytest.raises(a.Refused,match='image_export_timeout'):timed.read()
    finally:os.close(writer)


def test_halt_handles_zero_api_and_confirms_proxy_stopped(monkeypatch):
    runner=a.Activation()
    monkeypatch.setattr(runner,'service_ids',lambda s:['a'*64] if s=='reverse_proxy' else [])
    monkeypatch.setattr(runner,'docker',lambda *args,**kwargs:b'false\n' if args[0]=='inspect' else b'')
    result=runner.halt_consumers()
    assert result['status']=='CONFIRMED_STOPPED'
    assert result['services']['api']['matches']==0


def test_halt_reports_uncertain_when_stop_cannot_be_confirmed(monkeypatch):
    runner=a.Activation()
    monkeypatch.setattr(runner,'service_ids',lambda s:['a'*64])
    monkeypatch.setattr(runner,'docker',lambda *args,**kwargs:b'true\n' if args[0]=='inspect' else b'')
    assert runner.halt_consumers()['status']=='UNCERTAIN'


def test_rollback_recreates_api_even_if_failed_recreation_removed_it(monkeypatch):
    runner,events=fake_activation(monkeypatch)
    monkeypatch.setattr(a.signal,'signal',lambda *args:None)
    monkeypatch.setattr(runner,'halt_consumers',lambda:{'status':'CONFIRMED_STOPPED','services':{'api':{'matches':0},'reverse_proxy':{'matches':1}}})
    runner.rollback()
    assert [e[1] for e in events if e[0]=='recreate']==list(a.RECREATE)
    assert runner.report['rollback']=='PASS_original_four_file_profile'


def test_override_install_bookkeeping_survives_pending_signal(monkeypatch,tmp_path):
    import os,signal
    runner=a.Activation();runner.override_bytes=b'public config\n'
    destination=tmp_path/'stage2.yml'
    monkeypatch.setattr(a,'ETC',tmp_path);monkeypatch.setattr(a,'DESTINATION',destination)
    original_link=a.os.link
    def interrupted_link(*args,**kwargs):
        original_link(*args,**kwargs)
        os.kill(os.getpid(),signal.SIGTERM)
    monkeypatch.setattr(a.os,'link',interrupted_link)
    previous=signal.getsignal(signal.SIGTERM)
    def interrupt(*args):raise a.Refused('synthetic_interrupt')
    signal.signal(signal.SIGTERM,interrupt)
    try:
        with pytest.raises(a.Refused,match='synthetic_interrupt'):runner.install_override()
        assert destination.read_bytes()==runner.override_bytes
        assert runner.override_installed
        assert not list(tmp_path.glob('*.tmp'))
    finally:signal.signal(signal.SIGTERM,previous)


def test_installed_values_supports_protected_installer_backups(monkeypatch,tmp_path):
    import os
    (tmp_path/'current').write_text('synthetic current')
    (tmp_path/'backups').mkdir()
    (tmp_path/'backups/previous').write_text('synthetic previous')
    monkeypatch.setattr(a,'STORE',tmp_path)
    monkeypatch.setattr(a,'open_directory',lambda p,**kw:os.open(p,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW))
    calls=[]
    def read(folder,name,**policy):
        calls.append(policy)
        return (folder/name).read_text()
    monkeypatch.setattr(a,'read_secret',read)
    values=a.installed_values()
    assert len(values)==2
    assert set(values)=={str(tmp_path/'current'),str(tmp_path/'backups/previous')}
    assert all(p['gid']==0 and p['mode']==0o600 for p in calls)


def test_receipt_publication_failure_is_nonzero_and_incomplete(monkeypatch,tmp_path,capsys):
    import os,stat,sys
    from types import SimpleNamespace
    import scripts.ops.professor_server_secrets as installer
    class Runner:
        def __init__(self):
            self.report={'status':'PARTIAL'};self.root=tmp_path;self.scanner=True;self.maintenance=False
        def preflight(self):pass
        def cleanup(self):pass
        def publish(self):raise OSError('synthetic private detail must stay suppressed')
        def invalidate_receipt(self):self.invalidated=True
    runner=Runner()
    monkeypatch.setattr(a,'Activation',lambda:runner)
    monkeypatch.setattr(a.os,'geteuid',lambda:0)
    original_open,original_fstat=os.open,os.fstat
    lock_fd=[]
    def opened(path,*args,**kw):
        if str(path)=='/run/proptech-stage2-activation.lock':
            fd=original_open(tmp_path/'lock',*args,**kw);lock_fd.append(fd);return fd
        return original_open(path,*args,**kw)
    monkeypatch.setattr(a.os,'open',opened)
    monkeypatch.setattr(a.os,'fstat',lambda fd:SimpleNamespace(st_uid=0,st_mode=stat.S_IFREG|0o600,st_nlink=1) if lock_fd and fd==lock_fd[-1] else original_fstat(fd))
    monkeypatch.setattr(a.resource,'setrlimit',lambda *args:None)
    monkeypatch.setattr(a.os,'umask',lambda *args:None)
    monkeypatch.setattr(installer,'check_backing_storage',lambda *args:None)
    monkeypatch.setattr(sys,'argv',['activation','--plan'])
    assert a.main()==1
    assert runner.report['status']=='FAILED' and not runner.report['stage2_complete']
    assert runner.invalidated
    out=capsys.readouterr().out
    assert 'receipt_unavailable' in out and 'synthetic private' not in out


def test_missing_operator_source_pin_never_falls_back_to_checkout_head(monkeypatch,tmp_path):
    import os
    import subprocess
    repo=tmp_path/'repo';repo.mkdir()
    env={'PATH':os.defpath,'HOME':str(tmp_path)}
    def git(*args):
        return subprocess.run(['git',*args],cwd=repo,env=env,capture_output=True,check=True)
    git('init','-q')
    (repo/'backend').mkdir()
    (repo/'backend/api_main.py').write_text('# Synthetic current checkout module\n')
    git('add','backend/api_main.py')
    git('-c','user.name=Synthetic Test','-c','user.email=fixture@users.noreply.github.com',
        'commit','-q','-m','synthetic checkout')
    assert git('cat-file','-e','HEAD:backend/api_main.py').returncode==0
    monkeypatch.setattr(a,'REPO',repo)
    runner=a.Activation();runner.root=tmp_path/'evidence';runner.root.mkdir()
    monkeypatch.setattr(runner,'checkpoint',lambda phase:None)
    calls=[]
    original_run=runner.run
    def run(args,**kwargs):
        calls.append(args)
        return original_run(args,**kwargs)
    monkeypatch.setattr(runner,'run',run)
    monkeypatch.setattr(runner,'docker',lambda *args,**kwargs:pytest.fail('Docker must never run without the pinned source'))
    with pytest.raises(a.Refused,match='command_failed_output_suppressed'):
        runner.build()
    assert calls==[['git','ls-tree','-rz','--full-tree',a.SOURCE_COMMIT]]
    assert not (runner.root/'context/backend/api_main.py').exists()
