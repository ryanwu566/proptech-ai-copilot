"""Required storage is distinct from activation; all values are synthetic."""
import importlib
import json
import os
import stat

import pytest


def mod():
    try:
        return importlib.import_module('scripts.ops.professor_provider_storage')
    except ImportError:
        pytest.fail('required provider migration is missing')


def values():
    from tests.test_earth_engine_keyless_adc import adc_info
    adc = json.dumps(adc_info())
    return {'GOOGLE_MAPS_API_KEY':'SYNTHETIC_MAPS_MATERIAL_0123456789',
            'GOOGLE_APPLICATION_CREDENTIALS':adc,'TGOS_APP_ID':'SYNTHETIC_TGOS_ID_0123456789',
            'TGOS_API_KEY':'SYNTHETIC_TGOS_MATERIAL_0123456789',
            'TDX_CLIENT_ID':'SYNTHETIC_TDX_ID_0123456789','TDX_CLIENT_SECRET':'SYNTHETIC_TDX_MATERIAL_0123456789',
            'R2_ACCESS_KEY_ID':'SYNTHETIC_R2_ID_0123456789','R2_SECRET_ACCESS_KEY':'SYNTHETIC_R2_MATERIAL_0123456789',
            'OPENAI_API_KEY':'SYNTHETIC_OPENAI_MATERIAL_0123456789',
            'EARTH_ENGINE_PROJECT':'synthetic-project','R2_ENDPOINT':'https://synthetic.r2.cloudflarestorage.com',
            'R2_BUCKET':'synthetic-bucket','R2_REGION':'auto'}


@pytest.fixture
def storage(tmp_path, monkeypatch):
    m=mod(); owner=os.getuid(); group=os.getgid()
    monkeypatch.setattr(m,'OWNER',owner);monkeypatch.setattr(m,'GID',group)
    monkeypatch.setattr(m,'STORE_GID',group)
    monkeypatch.setattr(m.stage2,'check_backing_storage',lambda path:None)
    root=tmp_path/'persistent';root.mkdir(mode=0o700)
    staged=tmp_path/'staged';staged.mkdir(mode=0o700)
    return m,m.Storage(root,staged),root,staged


def test_required_set_includes_disabled_providers_and_shared_google_contract():
    m=mod()
    assert len(m.SECRETS)==9
    assert {'GOOGLE_MAPS_API_KEY','GOOGLE_APPLICATION_CREDENTIALS','TGOS_APP_ID','TGOS_API_KEY',
            'TDX_CLIENT_ID','TDX_CLIENT_SECRET','R2_ACCESS_KEY_ID','R2_SECRET_ACCESS_KEY','OPENAI_API_KEY'}==set(m.SECRETS)
    assert {'EARTH_ENGINE_PROJECT','R2_ENDPOINT','R2_BUCKET','R2_REGION'}==set(m.CONFIG)
    assert m.GROUPS['google']==('GOOGLE_MAPS_API_KEY',)


def test_collect_does_not_write_before_every_value_validates(storage):
    m,s,root,staged=storage; supplied=values(); supplied['R2_REGION']=''
    with pytest.raises(Exception):s.collect(lambda name: supplied[name])
    assert list(root.iterdir())==[] and list(staged.iterdir())==[]


def test_storage_and_provider_staging_are_private_and_idempotent(storage):
    m,s,root,staged=storage
    collected=s.collect(lambda name:values()[name]);s.persist_and_stage(collected)
    ids={p.name:p.stat().st_ino for p in root.iterdir()}
    def no_prompt(name):pytest.fail('existing material prompted for replacement')
    s.persist_and_stage(s.collect(no_prompt))
    assert ids=={p.name:p.stat().st_ino for p in root.iterdir()}
    for name,spec in m.ALL.items():
        p=s.stored_path(name);q=staged/spec['group']/spec['file']
        assert p.read_text()==values()[name] and q.read_text()==values()[name]
        assert stat.S_IMODE(p.stat().st_mode)==0o600
        assert stat.S_IMODE(q.stat().st_mode)==0o440
        assert stat.S_IMODE(q.parent.stat().st_mode)==0o700


def test_public_provider_settings_do_not_pollute_stage2_secret_scanner_inventory(storage):
    m,s,root,staged=storage;s.persist_and_stage(s.collect(lambda name:values()[name]))
    assert {p.name for p in root.iterdir()}=={item['file'] for item in m.SECRETS.values()}


def test_conflicting_stage_or_unsafe_store_is_never_overwritten(storage):
    m,s,root,staged=storage;s.persist_and_stage(s.collect(lambda name:values()[name]))
    target=staged/'google'/'google_maps_api_key';target.chmod(0o600);target.write_text('SYNTHETIC_CONFLICT');target.chmod(0o440)
    with pytest.raises(Exception):s.collect(lambda name:pytest.fail('conflict prompted'))
    assert target.read_text()=='SYNTHETIC_CONFLICT'


def test_existing_staged_values_adopt_without_input(storage):
    m,s,root,staged=storage
    for name,spec in m.ALL.items():
        folder=staged/spec['group'];folder.mkdir(mode=0o700,exist_ok=True)
        p=folder/spec['file'];p.write_text(values()[name]);p.chmod(0o440)
    got=s.collect(lambda name:pytest.fail('staged value prompted'))
    s.persist_and_stage(got)
    assert len(list(root.iterdir()))==9 and len(list(s.config.iterdir()))==4


def test_reboot_restoration_uses_only_persistent_material_and_preserves_store_inodes(storage):
    m,s,root,staged=storage
    s.persist_and_stage(s.collect(lambda name:values()[name]))
    inodes={name:s.stored_path(name).stat().st_ino for name in m.ALL}
    for name,item in m.ALL.items(): (staged/item['group']/item['file']).unlink()
    s.restore_staged_from_store()
    assert inodes=={name:s.stored_path(name).stat().st_ino for name in m.ALL}
    assert s.verify(values())


def test_reboot_restoration_requires_complete_persistent_set_before_any_write(storage):
    m,s,root,staged=storage
    with pytest.raises(Exception,match='provider_persistent_population_incomplete'):
        s.restore_staged_from_store()
    assert list(root.iterdir())==[] and list(staged.iterdir())==[]


def test_reboot_restoration_never_adopts_a_missing_store_from_volatile_stage(storage):
    m,s,root,staged=storage
    s.persist_and_stage(s.collect(lambda name:values()[name]))
    (root/'earth_engine_adc_json').unlink()
    with pytest.raises(Exception,match='provider_persistent_population_incomplete'):
        s.restore_staged_from_store()
    assert not (root/'earth_engine_adc_json').exists()


def test_concurrent_stage2_insertion_is_preserved_and_refused(storage,monkeypatch):
    m,s,root,staged=storage;original=m.stage2.atomic_secret_write;inserted=False
    def insert_between_phases(directory,name,value,**kwargs):
        nonlocal inserted
        original(directory,name,value,**kwargs)
        if not inserted and directory==root and name=='google_maps_api_key':
            inserted=True
            original(root,'tgos_app_id','SYNTHETIC_CONCURRENT_ID',owner=m.OWNER,gid=m.STORE_GID,mode=0o600)
    monkeypatch.setattr(m.stage2,'atomic_secret_write',insert_between_phases)
    with pytest.raises(Exception) as error:s.persist_and_stage(s.collect(lambda name:values()[name]))
    assert str(error.value)=='provider_credential_conflict'
    assert (root/'tgos_app_id').read_text()=='SYNTHETIC_CONCURRENT_ID'


def test_visibility_probe_has_one_group_no_network_env_logs_or_app_entrypoint():
    m=mod();args=m.probe_command('sha256:'+'a'*64,'google','/run/proptech-selfhost/secrets/providers')
    assert '--network=none' in args and '--read-only' in args and '--pull=never' in args
    assert '--log-driver=none' in args and '--cap-drop=ALL' in args and '--user=10001:10001' in args
    assert '--security-opt=no-new-privileges' in args
    assert not any(x in args for x in ['--publish','-p','--env','-e','--privileged'])
    assert len([x for x in args if x.startswith('type=bind,')])==1
    assert any('google_maps_api_key' in x and 'readonly' in x for x in args if x.startswith('type=bind,'))
    assert 'python' in args and 'uvicorn' not in args


def test_secret_scanner_excludes_public_settings_and_includes_adc_refresh_scalars():
    m=mod();material=m.scanner_values(values(),[])
    assert values()['R2_REGION'] not in material and values()['R2_BUCKET'] not in material
    source=json.loads(values()['GOOGLE_APPLICATION_CREDENTIALS'])['source_credentials']
    assert source['refresh_token'] in material and source['client_secret'] in material


def test_capture_reads_complete_multichunk_metadata():
    import sys
    m=mod();d=m.Docker.__new__(m.Docker)
    d.prefix=[sys.executable,'-c',"import sys;sys.stdout.write('x'*150000)"]
    d.env={'PATH':os.defpath}
    assert len(d.capture([],limit=200000))==150000


def test_project_stderr_logs_are_scanned():
    import sys
    from services.professor_activation_scan import SecretScanner
    m=mod();d=m.Docker.__new__(m.Docker)
    d.prefix=[sys.executable,'-c',"import sys;sys.stderr.write('SYNTHETIC_PRIVATE_LOG_MATERIAL')"]
    d.env={'PATH':os.defpath}
    with pytest.raises(Exception):d.stream(['logs'],SecretScanner(['SYNTHETIC_PRIVATE_LOG_MATERIAL']))


def test_arbitrary_lowercase_secret_is_never_a_reason_code():
    m=mod();material='a'*64
    assert m.safe_reason(RuntimeError(material))=='provider_migration_failed_details_suppressed'
    assert m.safe_reason(ValueError(material))=='provider_migration_failed_details_suppressed'


@pytest.mark.parametrize('source', ['/','/run','/run/proptech-selfhost','/run/proptech-selfhost/secrets',
                                  '/run/proptech-selfhost/secrets/providers','/etc','/etc/proptech-selfhost/secrets'])
def test_live_api_ancestor_mount_cannot_expose_provider_storage(source):
    assert mod().covers_provider_storage(source)


def test_current_core_and_dataset_mounts_do_not_cover_provider_storage():
    m=mod()
    assert not m.covers_provider_storage('/run/proptech-selfhost/secrets/app_database_url')
    assert not m.covers_provider_storage('/srv/proptech-data/DB')


@pytest.mark.parametrize('source', ['/run/proptech-selfhost/secrets/google_maps_api_key',
                                  '/run/proptech-selfhost/secrets/earth_engine_adc_json',
                                  '/run/proptech-selfhost/secrets/r2_endpoint'])
def test_legacy_flat_provider_mounts_are_not_live_api_consumers(source):
    assert mod().covers_provider_storage(source)


@pytest.mark.parametrize('source', ['/run/proptech-selfhost/secrets',
                                  '/etc/proptech-selfhost',
                                  '/run/proptech-selfhost/secrets/google_maps_api_key'])
def test_actual_preflight_rejects_covering_mount_from_inspection(monkeypatch,source):
    m=mod();d=m.Docker.__new__(m.Docker)
    def capture(args,*a,**k):
        if args[0]=='ps':return ('c'*64+'\n').encode()
        if args[0]=='image':return b'null'
        template=args[2]
        if template=='{{.Image}}':return ('sha256:'+'a'*64).encode()
        if '.Config.Volumes' in template:return b'null'
        if '.Mounts' in template:return json.dumps([{'Source':source}]).encode()
        if 'println (index' in template:return b'APP_ENV\n'
        for name,value in {**m.DISABLED,**m.AUTH}.items():
            if '"'+name+'"' in template:return (name+'='+value+'\n').encode()
        raise AssertionError('Unexpected metadata query')
    monkeypatch.setattr(d,'capture',capture)
    with pytest.raises(Exception) as error:d.preflight()
    assert str(error.value)=='provider_already_mounted_in_live_api'


@pytest.mark.parametrize('change', ['accepted_issuer_only','matching_url','conflicting_url',
                                   'missing_issuer','missing_audience','missing_paid_guard'])
def test_preflight_matches_accepted_explicit_issuer_profile(monkeypatch,change):
    from pathlib import Path
    import re
    m=mod();d=m.Docker.__new__(m.Docker)
    # Accepted Stage4A uses issuer/audience; SUPABASE_URL is an optional legacy alias.
    override=(Path(__file__).resolve().parents[1]/'infra/selfhost/professor-userdb.override.yml').read_text()
    assert re.search(r'^\s+SUPABASE_JWT_ISSUER:',override,re.M)
    assert re.search(r'^\s+SUPABASE_JWT_AUDIENCE:',override,re.M)
    assert not re.search(r'^\s+SUPABASE_URL:',override,re.M)
    env={**m.DISABLED,**{k:v for k,v in m.AUTH.items() if k!='SUPABASE_URL'}}
    if change=='matching_url':env['SUPABASE_URL']=m.AUTH['SUPABASE_URL']
    if change=='conflicting_url':env['SUPABASE_URL']='https://foreign-project.supabase.co'
    if change=='missing_issuer':env.pop('SUPABASE_JWT_ISSUER')
    if change=='missing_audience':env.pop('SUPABASE_JWT_AUDIENCE')
    if change=='missing_paid_guard':env.pop('ANTI_ABUSE_GEOCODING_DISABLED')
    def capture(args,*a,**k):
        if args[0]=='ps':return ('c'*64+'\n').encode()
        if args[0]=='image':return b'null'
        template=args[2]
        if template=='{{.Image}}':return ('sha256:'+'a'*64).encode()
        if '.Mounts' in template:return b'[]'
        if 'println (index' in template:return ('\n'.join(env)+'\n').encode()
        for name in {**m.DISABLED,**m.AUTH}:
            if '"'+name+'"' in template:
                return (name+'='+env[name]+'\n').encode() if name in env else b''
        raise AssertionError('Unexpected metadata query')
    monkeypatch.setattr(d,'capture',capture)
    if change in {'accepted_issuer_only','matching_url'}:
        assert d.preflight()==('c'*64,'sha256:'+'a'*64)
    else:
        with pytest.raises(Exception) as error:d.preflight()
        assert str(error.value)==('provider_auth_authority_changed' if change=='conflicting_url' else 'provider_guard_unavailable')


@pytest.mark.parametrize('failure', [None,'image','probe','changed_after_probe'])
def test_complete_operator_flow_synthetic_only(storage, monkeypatch, tmp_path, failure):
    from services.professor_activation_scan import ScanRefused
    m,s,root,staged=storage
    monkeypatch.setattr(m.stage2,'STORE',root);monkeypatch.setattr(m,'STAGE',staged)
    monkeypatch.setattr(m,'BACKUPS',tmp_path/'reports');monkeypatch.setattr(m,'LOCK',tmp_path/'migration.lock')
    monkeypatch.setattr(m.os,'geteuid',lambda:0);monkeypatch.setenv('SUDO_UID',str(os.getuid()))
    monkeypatch.setattr(m,'core_values',lambda:['SYNTHETIC_CORE_MATERIAL'])
    monkeypatch.setattr(m,'core_metadata',lambda:{'synthetic_core_metadata':'UNCHANGED'})
    monkeypatch.setattr(m,'scan_checkout',lambda scanner:{'status':'PASS','files':1,'bytes':1})
    calls=[]
    class OfflineDocker:
        def __init__(self,folder):pass
        def preflight(self):return 'c'*64,'sha256:'+'a'*64
        def capture(self,args,*a,**k):
            assert args[0]=='ps';return ('c'*64+'\n').encode()
        def stream(self,args,scanner,image=False):
            calls.append(args)
            if image and failure=='image':raise ScanRefused('credential_detected')
            return {'status':'PASS'} if image else None
        def probe(self,image,group,scanner,folder):
            if failure=='probe':raise RuntimeError('private_secret_material'*3)
            for name in m.GROUPS[group]:assert (staged/group/m.ALL[name]['file']).read_text()==values()[name]
            if failure=='changed_after_probe' and group==list(m.GROUPS)[-1]:
                (root/'google_maps_api_key').write_text('SYNTHETIC_CONCURRENT_MATERIAL')
                path=staged/'google'/'google_maps_api_key';path.chmod(0o600)
                path.write_text('SYNTHETIC_CONCURRENT_MATERIAL');path.chmod(0o440)
            return {'status':'PASS','group':group,'readable_files':len(m.GROUPS[group]),'values_returned':False}
    monkeypatch.setattr(m,'Docker',OfflineDocker)
    imports={}
    for name,value in values().items():
        path=tmp_path/('input-'+name);path.write_text(value);path.chmod(0o600);imports[name]=path
    ok,evidence=m.migrate_all(imports);report=json.loads(evidence.read_text())
    assert ok is (failure is None)
    assert 'SYNTHETIC_CORE_MATERIAL' not in evidence.read_text()
    assert values()['GOOGLE_MAPS_API_KEY'] not in evidence.read_text()
    assert 'private_secret_material'*3 not in evidence.read_text()
    assert report['activation_performed'] is False and report['paid_provider_calls']==0
    if failure=='image':assert list(root.iterdir())==[]
    elif failure in {'probe','changed_after_probe'}:
        reason='provider_migration_failed_details_suppressed' if failure=='probe' else 'provider_credential_conflict'
        assert len(list(root.iterdir()))==9 and report['reason_code']==reason
        assert set(report['provider_classification'].values())=={'PRESENT_NOT_VALIDATED'}
    else:
        assert set(report['provider_classification'].values())=={'PRESENT_AND_VALIDATED'}
        assert report['provider_functional_tests']=='NOT_RUN'
        assert report['core_database_hmac_session_material_preserved'] is True
    assert all(c[0] not in {'build','compose','exec','restart'} for c in calls)
