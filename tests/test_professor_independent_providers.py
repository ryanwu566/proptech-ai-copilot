"""Independent provider operations use only synthetic credentials/temp files."""
import json
import os
import stat

import pytest

from tests.test_professor_required_providers import storage, values, mod


@pytest.mark.parametrize('provider,group', [('google','google'),('tgos','tgos'),('tdx','tdx'),
    ('r2','r2'),('openai','openai'),('earth-engine','earth_engine')])
def test_selected_storage_collects_and_writes_only_one_complete_provider(storage,provider,group):
    m,_,root,staged=storage
    s=m.Storage(root,staged,groups=m.provider_groups(provider))
    prompts=[]
    def hidden(name):prompts.append(name);return values()[name]
    selected=s.collect(hidden)
    assert set(selected)==set(m.GROUPS[group])
    assert set(prompts)==set(m.GROUPS[group])
    s.persist_and_stage(selected)
    assert set(p.name for p in root.iterdir())=={m.ALL[n]['file'] for n in selected if n in m.SECRETS}
    assert set(p.name for p in staged.iterdir())=={group}
    for name in selected:
        p=s.stored_path(name)
        assert stat.S_IMODE(p.stat().st_mode)==0o600
        assert stat.S_IMODE((staged/group/m.ALL[name]['file']).stat().st_mode)==0o440
    assert set(s.verify(selected))==set(selected)
    if group!='earth_engine':assert not (root/'earth_engine_adc_json').exists()


def test_tdx_pair_validates_before_any_write_and_never_accepts_cross_provider_values(storage):
    m,_,root,staged=storage;s=m.Storage(root,staged,groups=('tdx',))
    with pytest.raises(Exception):s.collect(lambda n:'' if n=='TDX_CLIENT_SECRET' else values()[n])
    assert not list(root.iterdir()) and not list(staged.iterdir())
    with pytest.raises(Exception,match='provider_population_incomplete'):s.persist_and_stage(values())
    assert not list(root.iterdir())


def test_independent_install_and_reboot_restore_preserve_other_provider_inodes(storage):
    m,_,root,staged=storage
    google=m.Storage(root,staged,groups=('google',));google.persist_and_stage(google.collect(lambda n:values()[n]))
    original=(root/'google_maps_api_key').stat().st_ino
    tdx=m.Storage(root,staged,groups=('tdx',));tdx.persist_and_stage(tdx.collect(lambda n:values()[n]))
    for name in m.GROUPS['tdx']:(staged/'tdx'/m.ALL[name]['file']).unlink()
    tdx.restore_staged_from_store()
    assert (root/'google_maps_api_key').stat().st_ino==original
    assert not (root/'earth_engine_adc_json').exists()
    assert tdx.verify({n:values()[n] for n in m.GROUPS['tdx']})


def test_scanner_accepts_partial_material_without_adc_and_still_scans_selected_key():
    from services.professor_activation_scan import SecretScanner,ScanRefused
    m=mod();selected={'GOOGLE_MAPS_API_KEY':values()['GOOGLE_MAPS_API_KEY']}
    scanner=SecretScanner(m.scanner_values(selected,['SYNTHETIC_CORE_MATERIAL']))
    with pytest.raises(ScanRefused,match='credential_detected'):scanner.check_bytes(selected['GOOGLE_MAPS_API_KEY'].encode())


@pytest.mark.parametrize('provider',['google','tgos','tdx','r2','openai'])
def test_cli_dispatches_independent_provider_without_earth_engine(provider,monkeypatch,tmp_path,capsys):
    from scripts.ops import professor_provider_credentials as cli
    m=mod();called=[]
    def migrate(provider,imports):called.append((provider,imports));return True,tmp_path/'acceptance.json'
    monkeypatch.setattr(m,'migrate_provider',migrate,raising=False)
    assert cli.main(['--provider',provider])==0
    assert called==[(provider,{})]
    report=json.loads(capsys.readouterr().out)
    assert report['status']=='PASS_MIGRATED_PROVIDER_DISABLED' and report['provider']==provider
    assert report['activation_performed'] is False


def test_cli_refuses_cross_provider_import_before_host_operations(monkeypatch,capsys):
    from scripts.ops import professor_provider_credentials as cli
    m=mod();monkeypatch.setattr(m,'migrate_provider',lambda *a:pytest.fail('host operation'),raising=False)
    assert cli.main(['--provider','google','--from-file','GOOGLE_APPLICATION_CREDENTIALS=/synthetic/path'])==1
    assert json.loads(capsys.readouterr().out)['reason_code']=='provider_import_name_invalid'


def test_cli_selection_errors_never_reflect_accidental_credential(capsys):
    from scripts.ops import professor_provider_credentials as cli
    assert cli.main(['--provider','SYNTHETIC_DO_NOT_ECHO'])==1
    assert 'SYNTHETIC_DO_NOT_ECHO' not in capsys.readouterr().out


def test_scoped_reboot_entrypoint_does_not_call_migration(monkeypatch,capsys):
    from scripts.ops import professor_provider_credentials as cli
    m=mod();called=[]
    def restore(provider=None):called.append(provider);return {'status':'PASS_STAGED_PROVIDERS_NOT_ACTIVE','activation_performed':False}
    monkeypatch.setattr(m,'stage_stored_providers',restore)
    assert cli.main(['--stage-provider','google'])==0
    assert called==['google'] and json.loads(capsys.readouterr().out)['activation_performed'] is False


@pytest.mark.parametrize('provider',['google','tgos','tdx','r2','openai'])
@pytest.mark.parametrize('failure',[None,'unselected_leak','unselected_changed','unselected_inserted'])
def test_end_to_end_selected_operator_flow_never_needs_adc(storage,monkeypatch,tmp_path,provider,failure):
    m,_,root,staged=storage
    monkeypatch.setattr(m.stage2,'STORE',root);monkeypatch.setattr(m,'STAGE',staged)
    monkeypatch.setattr(m,'BACKUPS',tmp_path/'reports');monkeypatch.setattr(m,'LOCK',tmp_path/'migration.lock')
    monkeypatch.setattr(m.os,'geteuid',lambda:0);monkeypatch.setenv('SUDO_UID',str(os.getuid()))
    monkeypatch.setattr(m,'core_values',lambda:['SYNTHETIC_CORE_MATERIAL'])
    monkeypatch.setattr(m,'core_metadata',lambda:{'core':'UNCHANGED'})
    monkeypatch.setattr(m,'scan_checkout',lambda scanner:{'status':'PASS'})
    probes=[];scans=[];prompts=[]
    group=m.provider_groups(provider)[0]
    other='tgos' if group=='google' else 'google'
    old=m.Storage(root,staged,groups=(other,))
    if failure in {'unselected_leak','unselected_changed'}:
        old.persist_and_stage(old.collect(lambda n:values()[n]))
    other_secret=next(n for n in m.GROUPS[other] if n in m.SECRETS)
    old_inodes={n:old.stored_path(n).stat().st_ino for n in m.GROUPS[other] if old.stored_path(n).exists()}
    class OfflineDocker:
        def __init__(self,folder):pass
        def preflight(self):return 'c'*64,'sha256:'+'a'*64
        def capture(self,args,*a,**kw):assert args[0]=='ps';return ('c'*64+'\n').encode()
        def stream(self,args,scanner,image=False):
            scans.append(args)
            if image and failure=='unselected_leak':scanner.check_bytes(values()[other_secret].encode())
            return {'status':'PASS'} if image else None
        def probe(self,image,actual,scanner,folder):
            probes.append(actual)
            assert actual==group
            if failure=='unselected_changed':
                p=old.stored_path(other_secret);p.write_text('SYNTHETIC_CONCURRENT_UNSELECTED_MATERIAL')
                q=staged/other/m.ALL[other_secret]['file'];q.chmod(0o600)
                q.write_text('SYNTHETIC_CONCURRENT_UNSELECTED_MATERIAL');q.chmod(0o440)
            if failure=='unselected_inserted':
                p=old.stored_path(other_secret);p.write_text(values()[other_secret]);p.chmod(0o600)
            return {'status':'PASS','group':actual,'readable_files':len(m.GROUPS[actual]),'values_returned':False}
    monkeypatch.setattr(m,'Docker',OfflineDocker)
    def hidden(prompt):
        for name in m.GROUPS[group]:
            if name in prompt:prompts.append(name);return values()[name]
        pytest.fail('prompted for an unrelated provider')
    monkeypatch.setattr(m.stage2,'hidden_input',hidden)
    ok,evidence=m.migrate_provider(provider,{})
    report=json.loads(evidence.read_text())
    assert ok is (failure is None)
    assert set(report['provider_classification'])==set(m.GROUPS[group])
    assert set(prompts)==set(m.GROUPS[group])
    if failure=='unselected_leak':
        assert report['reason_code']=='credential_detected' and not probes
        assert not any((root/m.ALL[n]['file']).exists() for n in m.GROUPS[group] if n in m.SECRETS)
    else:
        assert set(report['provider_file_metadata'])==set(m.GROUPS[group]) and probes==[group]
        if failure is None:
            assert report['status']=='PASS_MIGRATED_PROVIDER_DISABLED'
        else:
            assert report['status']=='REFUSED' and report['reason_code']=='provider_scan_population_changed'
    assert old_inodes=={n:old.stored_path(n).stat().st_ino for n in old_inodes}
    assert report['earth_engine_iam_status']=='PENDING_IAM'
    assert report['provider_functional_tests']=='NOT_RUN' and report['activation_performed'] is False
    assert report['paid_provider_calls']==0 and not (root/'earth_engine_adc_json').exists()
    if failure!='unselected_leak':assert {x[0] for x in scans}=={'image','inspect','logs'}
    assert all(values()[name] not in evidence.read_text() for name in m.GROUPS[group])
