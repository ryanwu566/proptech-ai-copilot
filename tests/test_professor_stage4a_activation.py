"""No host mutations: exact Compose boundaries and fail-closed activation order."""
import ast
import copy
import json
from pathlib import Path
import subprocess

import pytest

from scripts.ops import professor_stage4a_activation as a


def models():
    from tests.test_professor_stage2_activation import models as stage2
    _, before = stage2()
    before['name'] = 'proptech-selfhost'
    after = copy.deepcopy(before)
    after['secrets'][a.USER_SECRET] = {'file': str(a.STAGED/a.USER_SECRET)}
    after['services']['api'].update(image='sha256:'+'b'*64,pull_policy='never',
        entrypoint=['python', a.ENTRYPOINT], command=['api'])
    after['services']['api']['healthcheck']['test'] = ['CMD','python',a.ENTRYPOINT,'health']
    after['services']['api']['secrets'].append({'source':a.USER_SECRET,'target':a.USER_TARGET})
    after['services']['api']['environment'].update(a.ENV_DELTA, RELEASE_COMMIT_SHA='c'*40)
    return before, after


def test_exact_api_only_merge():
    before, after = models()
    a.validate_models(before, after, 'sha256:'+'b'*64, 'c'*40)
    assert a.recreate_command(['docker','compose'])[-1] == 'api'
    assert '--no-deps' in a.recreate_command([])


@pytest.mark.parametrize('kind', ['db_volume','db_image','proxy','extra_secret','wrong_target',
    'wrong_issuer','different_audience','paid','market_ops','x9','writable','alias','extra_env','global'])
def test_unreviewed_changes_fail_closed(kind):
    before, after = models()
    api = after['services']['api']
    if kind == 'db_volume': after['services']['postgres_app']['volumes'][0]['source']='new'
    if kind == 'db_image': after['services']['postgres_app']['image']='postgres:latest'
    if kind == 'proxy': after['services']['reverse_proxy']['ports'][0]['host_ip']='0.0.0.0'
    if kind == 'extra_secret': api['secrets'].append({'source':'app_admin_password'})
    if kind == 'wrong_target': api['secrets'][-1]['target']='/run/secrets/'+a.USER_SECRET
    if kind == 'wrong_issuer': api['environment']['SUPABASE_JWT_ISSUER']='https://other.supabase.co/auth/v1'
    if kind == 'different_audience': api['environment']['SUPABASE_JWT_AUDIENCE']='service_role'
    if kind == 'paid': api['environment']['ANTI_ABUSE_PLACES_DISABLED']='false'
    if kind == 'market_ops': api['environment']['ANTI_ABUSE_MARKET_OPS_DISABLED']='false'
    if kind == 'x9': api['volumes'][0]['source']='/run/media/andy/Crucial X9/DB/x'
    if kind == 'writable': api['volumes'][0]['read_only']=False
    if kind == 'alias': api['environment']['PROFESSOR_USER_DATABASE_URL']='synthetic'
    if kind == 'extra_env': api['environment']['UNREVIEWED_FLAG']='true'
    if kind == 'global': after['networks']['app_db']['internal']=False
    with pytest.raises(a.Refused): a.validate_models(before,after,'sha256:'+'b'*64,'c'*40)


def test_unsafe_existing_state_is_rejected():
    before, after = models()
    for m in (before, after): m['services']['postgres_usage']['ports']=[{'published':'5432'}]
    with pytest.raises(a.Refused): a.validate_models(before,after,'sha256:'+'b'*64,'c'*40)


def test_actual_compose_cli_merge(tmp_path):
    before, _ = models()
    existing=tmp_path/'existing.json'; existing.write_text(json.dumps(before))
    override=tmp_path/'override.yml'
    override.write_bytes(a.override_bytes('sha256:'+'b'*64,'c'*40))
    command=['docker','compose','--project-name','proptech-selfhost','--project-directory',str(tmp_path),
        '--env-file','/dev/null','-f',str(existing),'-f',str(override),'config','--format','json']
    result=subprocess.run(command,capture_output=True,timeout=20)
    assert result.returncode == 0, 'Compose merge failed (details suppressed)'
    merged=json.loads(result.stdout)
    # Normalize the synthetic baseline with this installed Compose too.
    old=subprocess.run(command[:command.index('-f')+2]+['config','--format','json'],capture_output=True,timeout=20)
    assert old.returncode == 0
    a.validate_models(json.loads(old.stdout),merged,'sha256:'+'b'*64,'c'*40)


def test_generated_candidate_checks_are_valid_python_and_read_only():
    for approved in (False,True):
        source=a.candidate_probe_code('c'*40,approved)
        ast.parse(source)
        assert 'default_transaction_read_only' in source
        assert 'pg_stat_ssl' in source and 'validate_grants' in source
        assert 'validate_configuration()' in source if approved else 'validate_configuration()' not in source
        assert 'INSERT ' not in source and 'UPDATE ' not in source
    ast.parse(a.proxy_recovery_code('a'*64))


def test_proxy_reload_recovers_stale_unhealthy_and_transient_502():
    states=iter(['unhealthy','healthy','healthy'])
    calls=[];ticks=[0]
    def state():return {'Running':True,'Health':{'Status':next(states)}}
    def fetch(path):
        calls.append(path)
        if len(calls)==1:raise RuntimeError('synthetic upstream 502')
        return {'status':'ok','readiness':'ready'} if path=='/health' else {'status':'ready'}
    result=a.wait_proxy_recovery('a'*64,state=state,fetch=fetch,clock=lambda:ticks[0],
        sleep=lambda seconds:ticks.__setitem__(0,ticks[0]+seconds),timeout=5)
    assert result['status']=='PASS' and ticks[0]==2
    assert calls==['/health','/health','/readiness']


def test_proxy_readiness_failure_remains_fail_closed():
    ticks=[0]
    with pytest.raises(RuntimeError,match='proxy_recovery_timeout'):
        a.wait_proxy_recovery('a'*64,state=lambda:{'Running':True,'Health':{'Status':'healthy'}},
            fetch=lambda path:{'status':'unavailable'},clock=lambda:ticks[0],
            sleep=lambda seconds:ticks.__setitem__(0,ticks[0]+seconds),timeout=2)


def test_exact_template_pin_and_native_live_catalog(monkeypatch):
    raw=a.override_bytes('sha256:'+'b'*64,'c'*40)
    assert b'${' not in raw
    runner=a.Activation()
    baseline=json.loads((a.ROOT/'reports/professor-stage4a-auth-userdb/expected-catalog.json').read_text())
    role={k:True for k in ('database_connect','role_safe','no_external_reads','no_external_writes',
        'no_callable_definer','issuer_matches','database_matches')}
    role.update(configuration_rows=1,authority_reviewed=False,server_version_num='170010')
    def peer(sql,write=False):
        assert not write
        if sql==a.CATALOG_SQL:return json.dumps(a.catalog_for_server(baseline['catalog'],'170010')).encode()
        return json.dumps(role).encode()
    monkeypatch.setattr(runner,'peer',peer)
    assert runner.schema()==role


def test_docker_writes_are_preceded_by_backing_and_credential_isolation():
    source=Path(a.__file__).read_text()
    assert "self.env['DOCKER_CONFIG']" in source
    assert "check_backing_storage(Path(info['DockerRootDir']))" in source
    assert "Path('/var/lib/containerd')" in source
    assert source.index("self.env['DOCKER_CONFIG']") < source.index("self.docker('info'")


def test_shared_clean_builder_accepts_only_immutable_commits():
    runner=a.Activation()
    with pytest.raises(a.Refused,match='build_commit_invalid'):
        a.shared.Activation.build(runner,source_commit='HEAD; unsafe')


def test_private_secret_consistency_and_same_length_drift_never_echo_values():
    original={n:'synthetic-original-'+n for n in (*a.CORE,a.USER_SECRET)}
    a.validate_secret_snapshot(original,dict(original),dict(original))
    changed=dict(original);changed[a.USER_SECRET]=changed[a.USER_SECRET].replace('original','tampered')
    assert len(changed[a.USER_SECRET])==len(original[a.USER_SECRET])
    for stored,staged,baseline in [(original,changed,None),(changed,changed,original)]:
        with pytest.raises(a.Refused) as exc:a.validate_secret_snapshot(stored,staged,baseline)
        assert 'synthetic' not in str(exc.value)


def test_approval_sql_updates_only_reviewed_configuration():
    sql=a.approval_sql(False)
    assert 'UPDATE professor_user.configuration' in sql
    assert a.ISSUER in sql and 'migration_version=1' in sql
    assert 'configuration' in sql and 'ROW_COUNT' in sql
    assert 'users SET' not in sql and 'real_price_transactions' not in sql
    assert 'UPDATE ' not in a.approval_sql(True)


def test_approval_is_transactional_and_issuer_scoped(pg):
    import psycopg
    from tests.test_professor_userdb import ISSUER as fixture_issuer
    with psycopg.connect(host=pg,dbname='stage4a_userdb_test') as c:
        with c.transaction(force_rollback=True):
            c.execute('UPDATE professor_user.configuration SET issuer=%s,authority_reviewed=false',(a.ISSUER,))
            c.execute(a.approval_sql(False))
            assert c.execute('SELECT authority_reviewed FROM professor_user.configuration').fetchone()==(True,)
        assert c.execute('SELECT issuer FROM professor_user.configuration').fetchone()==(fixture_issuer,)
        with pytest.raises(psycopg.Error):
            with c.transaction(): c.execute(a.approval_sql(False))


def fake_runner(monkeypatch, fail=None):
    runner=a.Activation()
    events=[]
    for name in ('stable','assert_unchanged','approve_authority','install_override','recreate_api',
                 'wait_api','reload_proxy','verify_active','verify_regressions'):
        def op(n=name):
            events.append(n)
            if n==fail: raise a.Refused('synthetic_failure')
        monkeypatch.setattr(runner,name,op)
    monkeypatch.setattr(runner,'candidate',lambda approved:events.append(('candidate',approved)))
    monkeypatch.setattr(runner,'save',lambda *args:None)
    return runner,events


def test_approval_then_candidate_before_any_runtime_change(monkeypatch):
    runner,events=fake_runner(monkeypatch)
    runner.activate()
    assert events.index('approve_authority') < events.index(('candidate',True)) < events.index('install_override')
    assert events.index('install_override') < events.index('recreate_api') < events.index('verify_regressions')
    assert events.index('wait_api') < events.index('reload_proxy') < events.index('verify_regressions')
    assert runner.report['status']=='PASS'
    assert runner.report['api_recreation_outcome']=='COMPLETED' and runner.report['activation_performed'] is True


def test_candidate_rejection_leaves_runtime_untouched(monkeypatch):
    runner,events=fake_runner(monkeypatch)
    monkeypatch.setattr(runner,'candidate',lambda approved:(_ for _ in ()).throw(a.Refused('candidate_failed')))
    with pytest.raises(a.Refused): runner.activate()
    assert 'install_override' not in events and 'recreate_api' not in events
    assert runner.maintenance is False


def test_recreation_failure_is_marked_for_rollback(monkeypatch):
    runner,events=fake_runner(monkeypatch,fail='recreate_api')
    with pytest.raises(a.Refused): runner.activate()
    assert runner.maintenance is True
    assert runner.report['api_recreation_attempted'] is True
    assert runner.report['api_recreation_outcome']=='UNVERIFIED'
    assert runner.report['phase']=='recreate-api-only'


def test_durable_authority_receipt_is_truthful_even_if_next_receipt_write_fails(tmp_path,monkeypatch):
    runner=a.Activation();runner.approved=False
    runner.before_schema={'authority_reviewed':False,'user_count':0}
    states=iter([runner.before_schema,{**runner.before_schema,'authority_reviewed':True}])
    monkeypatch.setattr(a,'APPROVAL',tmp_path/'approval.json')
    monkeypatch.setattr(runner,'checkpoint',lambda *args:None)
    monkeypatch.setattr(runner,'install_file',lambda *args:None)
    monkeypatch.setattr(runner,'schema',lambda:next(states))
    monkeypatch.setattr(runner,'peer',lambda sql,write=False:b'')
    monkeypatch.setattr(runner,'save',lambda *args:(_ for _ in ()).throw(a.Refused('receipt_write_failed')))
    with pytest.raises(a.Refused):runner.approve_authority()
    assert runner.report['database_authority_approval']=='RECORDED_AND_APPLIED'
    assert runner.report['authority_reviewed'] is True
    assert runner.maintenance is False


def test_rollback_shell_is_valid_and_api_only(tmp_path):
    raw=a.rollback_script(['docker','compose','-f','/safe path/original.yml'],
        tmp_path,'sha256:'+'a'*64,'f'*64,'a'*64)
    target=tmp_path/'ROLLBACK.sh'; target.write_text(raw)
    assert subprocess.run(['bash','-n',str(target)],capture_output=True).returncode==0
    assert '--no-deps' in raw and '--force-recreate api' in raw
    assert 'down ' not in raw and 'postgres_app up' not in raw
    assert 'nginx -s reload' in raw and 'wait_proxy_recovery' in raw
    assert 'exec /usr/bin/env -i ' in raw and 'DOCKER_CONFIG=' in raw and 'COMPOSE_PROFILES=' in raw
    assert 'authority_reviewed' not in raw  # preserve the separate reviewed approval


def test_rollback_outer_budget_covers_every_phase_and_command_overhead():
    assert a.ROLLBACK_TIMEOUT >= a.RECREATE_TIMEOUT+a.API_PHASE_TIMEOUT+a.PROXY_PHASE_TIMEOUT+120
    source=Path(a.__file__).read_text()
    assert "timeout=ROLLBACK_TIMEOUT" in source
    raw=a.rollback_script(['docker','compose'],Path('/separate/backups/run'),'sha256:'+'a'*64,'f'*64,'b'*64)
    assert str(a.RECREATE_TIMEOUT)+'s docker compose' in raw
    assert str(a.API_PHASE_TIMEOUT)+'s python3' in raw
    assert str(a.PROXY_PHASE_TIMEOUT)+'s python3' in raw


def test_rollback_move_stays_on_etc_filesystem_and_is_repeatable(tmp_path,monkeypatch):
    import hashlib,shlex,sys
    etc=tmp_path/'etc';etc.mkdir()
    backup=tmp_path/'separate-backup-filesystem';backup.mkdir()
    destination=etc/'stage4a-auth.override.yml';destination.write_bytes(b'reviewed synthetic override')
    monkeypatch.setattr(a,'ETC',etc);monkeypatch.setattr(a,'DESTINATION',destination)
    raw=a.rollback_script(['docker','compose'],backup,'sha256:'+'a'*64,hashlib.sha256(destination.read_bytes()).hexdigest(),'a'*64)
    # A Python literal multiline command is quoted by shlex; parse the entire shell.
    words=shlex.split(raw)
    index=words.index('python3')
    move=words[index+4]
    ast.parse(move)
    assert str(backup/'inactive-stage4a.override.yml') not in move
    for _ in range(2):
        result=subprocess.run([sys.executable,'-I','-B','-c',move],capture_output=True,timeout=5)
        assert result.returncode==0
    assert not destination.exists()
    assert (etc/('.stage4a-inactive-'+backup.name+'.yml')).read_bytes()==b'reviewed synthetic override'


def test_no_provisioning_or_frontend_mutation_or_dynamic_code():
    text=Path(a.__file__).read_text()
    ast.parse(text)
    assert 'professor_stage4a_provision' not in text
    assert 'down -v' not in text and 'DROP ' not in text and 'TRUNCATE ' not in text
    assert 'frontend_next/next-env.d.ts' in text  # hash guard only
    tree=ast.parse(text)
    assert not any(isinstance(n,ast.Call) and isinstance(n.func,ast.Name)
                   and n.func.id in {'eval','exec'} for n in ast.walk(tree))


# Reuse only the private disposable Unix-socket fixture, never a live database.
from tests.test_professor_userdb import pg  # noqa: E402,F401
