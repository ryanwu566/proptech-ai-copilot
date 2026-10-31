import ast
from pathlib import Path

import pytest

ROOT=Path(__file__).resolve().parents[1]


def test_stage4a_url_never_accepts_legacy_admin_or_remote():
    from services.professor_userdb import validate_url
    expected='postgresql://professor_user_runtime:synthetic@postgres_app/proptech_app'
    assert validate_url(expected)==expected
    for value in [expected.replace('professor_user_runtime','postgres'),expected.replace('postgres_app','example.invalid'),expected+'?sslmode=disable',expected.replace('proptech_app','proptech_valuation')]:
        with pytest.raises(ValueError): validate_url(value)


def test_provisioning_is_separate_and_default_plan_is_nonprivileged():
    from scripts.ops.professor_stage4a_provision import plan
    result=plan()
    assert result['container_recreation'] is False
    assert result['existing_auth_users_modified'] is False
    assert result['database']=='proptech_app'
    assert result['schema']=='professor_user'


def test_new_scripts_parse_and_no_destructive_database_verbs():
    for name in ['professor_stage4a_provision.py','professor_stage4a_entrypoint.py']:
        source=(ROOT/'scripts/ops'/name).read_text()
        ast.parse(source)
        assert 'sudo' not in source
        assert 'down -v' not in source
        assert 'TRUNCATE' not in source
        assert 'DROP DATABASE' not in source
    migration=(ROOT/'database/userdb/001_professor_users.sql').read_text()
    assert 'real_price_transactions' not in migration
    assert 'auth.users' in migration.splitlines()[1]  # comment explicitly forbids dependency
    assert 'SECURITY DEFINER' not in migration


def test_entrypoint_separate_mount_keeps_stage2_core_exact(tmp_path):
    import os
    from scripts.ops.professor_stage4a_entrypoint import environment
    from services.selfhost_secret_files import SecretRefused
    from tests.test_professor_secrets import synthetic_mount,guards
    core,_=synthetic_mount(tmp_path)
    user=tmp_path/'user';user.mkdir(mode=0o700)
    secret=user/'professor_user_database_url'
    secret.write_text('postgresql://professor_user_runtime:synthetic@postgres_app/proptech_app')
    secret.chmod(0o440)
    env={**guards(),'PROFESSOR_USERDB_ENABLED':'true'}
    loaded=environment(core,user,env,owner=os.getuid(),gid=os.getgid())
    assert 'PROFESSOR_USER_DATABASE_URL' in loaded
    assert len(list(core.iterdir()))==5
    for bad in [
        {**env,'PROFESSOR_USER_DATABASE_URL':'synthetic'},
        {**env,'PROFESSOR_USER_DATABASE_URL_FILE':'/tmp/alias'},
        {**env,'VNEXT_DATABASE_URL':'synthetic'},
        {**env,'ANTI_ABUSE_MARKET_OPS_DISABLED':'false'},
    ]:
        with pytest.raises(SecretRefused):environment(core,user,bad,owner=os.getuid(),gid=os.getgid())
    secret.chmod(0o644)
    with pytest.raises(SecretRefused):environment(core,user,env,owner=os.getuid(),gid=os.getgid())


def test_compose_profile_merge_keeps_databases_and_mounts_and_ports(tmp_path):
    import json
    import os
    import subprocess
    runtime=tmp_path/'runtime.env';runtime.write_text('API_ALLOWED_HOSTS=localhost\n')
    env={'PATH':os.defpath,'SELFHOST_SECRETS_DIR':str(tmp_path),
         'SELFHOST_TLS_DIR':str(tmp_path),'SELFHOST_RUNTIME_ENV_FILE':str(runtime),
         'SELFHOST_BACKEND_IMAGE':'backend@sha256:'+'a'*64,
         'SELFHOST_PROXY_IMAGE':'nginx@sha256:'+'b'*64,
         'PROFESSOR_SERVER_API_IMAGE':'professor-stage2@sha256:'+'c'*64,
         'PROFESSOR_STAGE4A_API_IMAGE':'professor-stage4a@sha256:'+'d'*64}
    drift=tmp_path/'drift.json'
    drift.write_text(json.dumps({'services':{'api':{'secrets':['old_credential_alias'],
        'volumes':['/srv/proptech-data/DB/local-fixture:/srv/proptech/datasets/fixture:ro']}},
        'secrets':{'old_credential_alias':{'file':str(tmp_path/'not-a-real-secret')}}}))
    args=['docker','compose','-p','proptech-selfhost','-f','docker-compose.selfhost.yml',
          '-f',str(drift),'-f','infra/selfhost/professor-secrets.override.yml']
    def model(extra):
        p=subprocess.run(args+extra+['config','--format','json'],cwd=ROOT,env=env,capture_output=True,text=True,timeout=20)
        assert p.returncode==0,'synthetic_compose_merge_failed'
        return json.loads(p.stdout)
    before=model([]);after=model(['-f','infra/selfhost/professor-userdb.override.yml'])
    for name in before['services']:
        if name!='api':assert before['services'][name]==after['services'][name]
    api=after['services']['api']
    assert api['volumes']==before['services']['api']['volumes']
    assert api['networks']==before['services']['api']['networks']
    assert {s['source'] for s in api['secrets']}=={'app_database_url','usage_database_url','valuation_database_url','usage_peer_hmac_key','pilot_session_signing_key','professor_user_database_url'}
    assert next(s for s in api['secrets'] if s['source']=='professor_user_database_url')['target']=='/run/professor-userdb/professor_user_database_url'
    assert not api.get('ports')
    assert not after['services']['postgres_app'].get('ports')
    assert after['services']['reverse_proxy']['ports'][0]['host_ip']=='127.0.0.1'
    assert api['environment']['ANTI_ABUSE_MARKET_OPS_DISABLED']=='true'


def test_production_pool_pins_tls_and_dedicated_role(monkeypatch):
    import psycopg_pool
    from services import professor_userdb as module
    seen={}
    class FakePool:
        def __init__(self,**kwargs):seen.update(kwargs)
        def close(self):pass
    monkeypatch.setenv('PROFESSOR_USERDB_ENABLED','true')
    monkeypatch.setenv('PROFESSOR_USER_DATABASE_URL','postgresql://professor_user_runtime:synthetic@postgres_app/proptech_app')
    monkeypatch.setattr(psycopg_pool,'ConnectionPool',FakePool)
    module.get_repository.cache_clear()
    try:
        module.get_repository()
        assert seen['kwargs']['sslmode']=='verify-full'
        assert seen['kwargs']['sslrootcert']=='/run/selfhost-ca/ca.crt'
        assert seen['max_size']==3
    finally:module.close_pool()


def test_scram_uses_random_salt_and_no_plaintext():
    from scripts.ops.professor_stage4a_provision import scram
    one=scram('synthetic-password');two=scram('synthetic-password')
    assert one!=two and one.startswith('SCRAM-SHA-256$32768:')
    assert 'synthetic-password' not in one


def test_restaging_after_reboot_preserves_store_and_uses_no_sql(tmp_path,monkeypatch):
    import os
    from scripts.ops import professor_stage4a_provision as module
    from services.selfhost_secret_files import SecretRefused
    store=tmp_path/'store';stage=tmp_path/'stage'
    store.mkdir(mode=0o700);stage.mkdir(mode=0o700)
    source=store/'professor_user_database_url'
    value='postgresql://professor_user_runtime:synthetic-long-password-1234567890@postgres_app/proptech_app'
    source.write_text(value);source.chmod(0o600)
    before=source.stat().st_ino
    monkeypatch.setattr(module,'run',lambda *a,**kw:pytest.fail('restaging must not invoke commands/SQL'))
    kwargs={'owner':os.getuid(),'gid':os.getgid(),'store_gid':os.getgid()}
    assert module.stage_existing(store,stage,**kwargs)['status']=='STAGED'
    target=stage/source.name;inode=target.stat().st_ino
    assert target.stat().st_mode & 0o777==0o440
    assert source.stat().st_ino==before
    assert module.stage_existing(store,stage,**kwargs)['status']=='UNCHANGED'
    assert target.stat().st_ino==inode
    target.unlink()  # only disposable fixture: simulate volatile /run loss
    assert module.stage_existing(store,stage,**kwargs)['status']=='STAGED'
    target.chmod(0o640)
    with pytest.raises(SecretRefused):module.stage_existing(store,stage,**kwargs)
    assert source.read_text()==value


@pytest.mark.parametrize('failure',['backup','sql','stage'])
def test_operator_partial_failures_preserve_recovery_material(tmp_path,monkeypatch,capsys,failure):
    """Simulated root/daemon boundaries; every file is a disposable fixture."""
    import json
    import os
    import subprocess
    from scripts.ops import professor_stage4a_provision as module
    from services.selfhost_secret_files import SecretRefused
    store=tmp_path/'store';store.mkdir(mode=0o700)
    staged=tmp_path/'staged';staged.mkdir(mode=0o700)
    evidence=tmp_path/'evidence'
    monkeypatch.setattr(module,'STORE',store);monkeypatch.setattr(module,'STAGED',staged);monkeypatch.setattr(module,'EVIDENCE',evidence)
    monkeypatch.setattr(module.os,'geteuid',lambda:0)
    monkeypatch.setattr(module,'check_backing_storage',lambda _:None)
    monkeypatch.setattr(module,'ensure_private',lambda p:p.mkdir(mode=0o700,exist_ok=True))
    real_open=os.open
    def opened(path,flags,*a,**kw):
        if path=='/run/proptech-stage4a-provision.lock':path=tmp_path/'lock'
        return real_open(path,flags,*a,**kw)
    monkeypatch.setattr(module.os,'open',opened)
    monkeypatch.setattr(module,'open_directory',lambda p,**k:real_open(p,os.O_RDONLY))
    actual_write=module.atomic_secret_write
    def write(folder,name,value,**kwargs):
        actual_write(folder,name,value,owner=os.getuid(),gid=os.getgid(),**kwargs)
    monkeypatch.setattr(module,'atomic_secret_write',write)
    monkeypatch.setattr(module.secrets,'token_urlsafe',lambda _: 'synthetic-test-password-with-over-32-characters')
    attempted=[]
    def command(args,data=None,timeout=60):
        if args[:2]==['docker','info']:return json.dumps(str(tmp_path)).encode()
        if args[:2]==['docker','ps']:return b'fixture-container\n'
        if args[:2]==['docker','inspect']:return json.dumps([{'HostConfig':{'PortBindings':{}},'Mounts':[]}]).encode()
        if data and b'SELECT current_database()' in data:return b'proptech_app|postgres|t|t\n'
        if data and b'CREATE ROLE' in data:
            attempted.append('sql')
            if failure=='sql':raise SecretRefused('synthetic_sql_failure')
            return b''
        pytest.fail('unexpected operator command')
    monkeypatch.setattr(module,'run',command)
    def subrun(args,**kwargs):
        if 'pg_dump' in args:
            attempted.append('backup')
            if failure=='backup':return subprocess.CompletedProcess(args,1,stderr=b'fixture')
            kwargs['stdout'].write(b'PGDMPfixture')
            return subprocess.CompletedProcess(args,0)
        if 'pg_restore' in args:return subprocess.CompletedProcess(args,0)
        pytest.fail('unexpected subprocess')
    monkeypatch.setattr(module.subprocess,'run',subrun)
    monkeypatch.setattr(module,'stage_existing',lambda *a,**kw:(_ for _ in ()).throw(SecretRefused('synthetic_stage_failure')))
    original_umask=os.umask(0o077)
    try:
        with pytest.raises(SecretRefused):module.provision()
    finally:os.umask(original_umask)
    report=json.loads(next(evidence.glob('*/apply-report.json')).read_text())
    assert report['status']=='REFUSED' and report['container_recreation'] is False
    assert (store/'professor_user_database_url').exists()==(failure!='backup')
    assert not (staged/'professor_user_database_url').exists()
    assert ('sql' in attempted)==(failure!='backup')
    if failure=='stage':assert report['schema_applied'] is True
    public=capsys.readouterr().out
    assert 'synthetic-test-password' not in public and 'SCRAM' not in public


def test_existing_postgres_tmpfs_mounts_are_supported_without_storage_paths(monkeypatch):
    from scripts.ops import professor_stage4a_provision as module
    from services.selfhost_secret_files import SecretRefused
    seen=[]
    monkeypatch.setattr(module,'check_backing_storage',lambda p:seen.append(str(p)))
    module.validate_mounts([
        {'Type':'volume','Source':'/var/lib/docker/volumes/fixture/_data','Destination':'/var/lib/postgresql/data'},
        {'Type':'tmpfs','Source':'','Destination':'/tmp'},
        {'Type':'tmpfs','Source':'','Destination':'/var/run/postgresql'},
    ])
    assert seen==['/var/lib/docker/volumes/fixture/_data']
    with pytest.raises(SecretRefused):module.validate_mounts([{'Type':'tmpfs','Source':'','Destination':'/unknown'}])
