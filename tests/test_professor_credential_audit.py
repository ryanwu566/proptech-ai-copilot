"""Names and synthetic file metadata only; no provider activation or real secrets."""
import copy
import importlib
from pathlib import Path

import pytest


def audit():
    try:return importlib.import_module('services.professor_credential_audit')
    except ImportError:pytest.fail('expanded dependency audit is missing')


def snapshot():
    from services.professor_credentials import ACTIVE
    row={'device':1,'gid':10001,'inode':20,'mode':'0o440','size':64,'uid':0}
    host={n:dict(row,inode=20+i) for i,n in enumerate(ACTIVE.values())}
    receipt={'status':'PASS','api_image_id':'sha256:'+'a'*64,'identity_provider':'supabase',
        'application_data_authority':'professor_postgresql','profile_installed':True,'secret_values_returned':False,
        'loopback_8080':True,'postgresql_private':True,'market_ops_disabled':True,'paid_providers_disabled':True}
    return receipt,host,copy.deepcopy(host)


def test_exact_accepted_six_are_proven_without_values():
    r,h,m=snapshot();v=audit().validate_accepted_credentials(r,h,m,'sha256:'+'a'*64)
    assert v['status']=='PASS_ACCEPTED_RECEIPT'
    assert len(v['verified_secret_files'])==6 and v['fresh_host_inspection'] is False


def test_db_only_mount_evidence_rejects_admin_credentials_in_api():
    m=audit();assert hasattr(m,'validate_database_mounts')
    services={'api':{'mounts':[]}}
    for kind in ('app','usage'):
        services['postgres_'+kind]={'ports':None,'mounts':[
            {'Source':'/run/proptech-selfhost/secrets/'+kind+'_admin_password',
             'Destination':'/run/secrets/'+kind+'_admin_password','RW':False,'Type':'bind'},
            {'Source':'/run/proptech-selfhost/tls/'+kind,'Destination':'/run/postgres-tls','RW':False,'Type':'bind'}]}
    assert m.validate_database_mounts(services)['db_admin_files']==['app_admin_password','usage_admin_password']
    services['api']['mounts'].append(copy.deepcopy(services['postgres_app']['mounts'][0]))
    with pytest.raises(ValueError):m.validate_database_mounts(services)


@pytest.mark.parametrize('service,source',[('reverse_proxy','/run/proptech-selfhost/secrets/app_admin_password'),
    ('api','/run/proptech-selfhost/secrets'),('api','/etc/proptech-selfhost/secrets'),
    ('api','/run/proptech-selfhost/tls'),('reverse_proxy','/run/proptech-selfhost/tls/app/server.key')])
def test_db_secret_and_tls_ancestor_binds_are_never_non_db_consumers(service,source):
    services={'api':{'mounts':[]},'reverse_proxy':{'mounts':[]}}
    for kind in ('app','usage'):
        services['postgres_'+kind]={'ports':None,'mounts':[
            {'Source':'/run/proptech-selfhost/secrets/'+kind+'_admin_password','Destination':'/run/secrets/'+kind+'_admin_password','RW':False,'Type':'bind'},
            {'Source':'/run/proptech-selfhost/tls/'+kind,'Destination':'/run/postgres-tls','RW':False,'Type':'bind'}]}
    services[service]['mounts'].append({'Source':source,'Destination':'/unexpected','RW':False,'Type':'bind'})
    with pytest.raises(ValueError):audit().validate_database_mounts(services)


@pytest.mark.parametrize('kind',['wrong_image','unsafe_mode','foreign_owner','changed_inode','extra','missing','failed','wrong_authority'])
def test_accepted_evidence_mismatch_fails_closed(kind):
    r,h,m=snapshot();name=next(iter(h))
    if kind=='wrong_image':r['api_image_id']='sha256:'+'b'*64
    if kind=='unsafe_mode':h[name]['mode']='0o644'
    if kind=='foreign_owner':h[name]['uid']=1000
    if kind=='changed_inode':m[name]['inode']+=1
    if kind=='extra':h['unknown']=dict(h[name])
    if kind=='missing':h.pop(name)
    if kind=='failed':r['status']='FAIL'
    if kind=='wrong_authority':r['identity_provider']='custom'
    with pytest.raises(ValueError):audit().validate_accepted_credentials(r,h,m,'sha256:'+'a'*64)


def test_missing_permission_and_accepted_presence_are_distinct():
    m=audit()
    assert m.credential_state(True,{'state':'UNKNOWN'})=='PRESENT_ACCEPTED_RECEIPT'
    assert m.credential_state(False,{'state':'UNKNOWN'})=='UNKNOWN'
    assert m.credential_state(True,{'state':'MISSING'},required=True)=='MISSING_REQUIRED'
    assert m.credential_state(False,{'state':'PRESENT_SAFE'})=='PRESENT_METADATA_ONLY'
    assert m.credential_state(True,{'state':'PRESENT_UNSAFE'})=='UNSAFE_METADATA'


def test_requiredness_does_not_depend_on_old_receipt_availability(monkeypatch):
    m=audit();root=Path(__file__).resolve().parents[1]
    monkeypatch.setattr(m,'accepted_credential_evidence',lambda root:{'status':'UNAVAILABLE_ACCEPTED_RECEIPT','verified_secret_files':[]})
    monkeypatch.setattr(m,'file_metadata',lambda path:{'state':'MISSING'})
    r=m.build_dependency_matrix(root)
    assert set(r['missing_required_credentials'])==set(m.ACTIVE)


@pytest.mark.parametrize('gid,mode',[(0,0o600),(0,0o440),(10001,0o640)])
def test_staged_file_permissions_require_exact_api_read_access(monkeypatch,gid,mode):
    from types import SimpleNamespace
    import stat
    m=audit();row=SimpleNamespace(st_mode=stat.S_IFREG|mode,st_uid=0,st_gid=gid,st_nlink=1,st_size=64)
    monkeypatch.setattr(Path,'lstat',lambda path:row)
    assert m.file_metadata(Path('/run/proptech-selfhost/secrets/app_database_url'))['state']=='PRESENT_UNSAFE'


def test_required_configuration_comes_from_manifest_and_accepted_profile(monkeypatch):
    m=audit();root=Path(__file__).resolve().parents[1]
    monkeypatch.setattr(m,'file_metadata',lambda path:{'state':'UNKNOWN'})
    rows={r['name']:r for r in m.build_dependency_matrix(root)['dependencies']}
    for name in ('APP_ENV','API_USAGE_GUARD_MODE','API_USAGE_LEDGER_REQUIRED','POSTGRES_SSLMODE','ANTI_ABUSE_MARKET_OPS_DISABLED'):
        assert rows[name]['required_for_production']=='YES'
        assert rows[name]['classification']=='PROFESSOR_SERVER_ACTIVE'
    assert rows['GOOGLE_MAPS_API_KEY']['required_for_production']=='NO'


def test_complete_dependency_rows_include_configuration_and_migration_fields(monkeypatch):
    m=audit();root=Path(__file__).resolve().parents[1]
    monkeypatch.setattr(m,'file_metadata',lambda path:{'state':'UNKNOWN'})
    r=m.build_dependency_matrix(root)
    rows={row['name']:row for row in r['dependencies']}
    for name in ('GOOGLE_MAPS_API_KEY','TDX_CLIENT_SECRET','SUPABASE_JWT_ISSUER','CORS_ALLOWED_ORIGINS',
                 'PROFESSOR_USER_DATABASE_URL','VALUATION_ML_MANIFEST_SHA256','R2_ACCESS_KEY_ID'):
        assert name in rows
        assert {'provider','consumer','current_location','target_location','required_for_production',
            'migration_state','retirement_state','classification'}<=set(rows[name])
        assert rows[name]['required_for_production'] in {'YES','NO'}
    assert rows['GOOGLE_MAPS_API_KEY']['required_for_production']=='NO'
    assert rows['DATABASE_URL']['required_for_production']=='YES'
    assert rows['PROFESSOR_USER_DATABASE_URL']['installer_support'] is False
    assert rows['RENDER_API_BASE_URL']['classification']=='LEGACY_CLOUD_ONLY'
    assert rows['RENDER_GIT_COMMIT']['classification']=='LEGACY_CLOUD_ONLY'
    assert r['all_requested_audit_scopes_complete'] is False
    assert r['missing_required_credentials']==[]
    assert r['ready_to_retire_credentials']==[]
    assert r['live_cloud_scopes']['github_actions']=='UNKNOWN_NAMES_INVENTORY_NOT_SUPPLIED'


def test_missing_required_known_secret_never_becomes_optional(monkeypatch):
    m=audit();root=Path(__file__).resolve().parents[1]
    monkeypatch.setattr(m,'file_metadata',lambda path:{'state':'MISSING'} if path.name=='app_database_url' else {'state':'UNKNOWN'})
    r=m.build_dependency_matrix(root)
    row=next(x for x in r['dependencies'] if x['name']=='DATABASE_URL')
    assert row['classification']=='MISSING_REQUIRED'
    assert 'DATABASE_URL' in r['missing_required_credentials']


def test_extended_reference_forms_only_return_identifiers():
    m=audit()
    assert m.reference_names('x.ts','process.env["NEXT_PUBLIC_API_BASE_URL"]')=={'NEXT_PUBLIC_API_BASE_URL'}
    assert m.reference_names('x.yml','x: ${API_ALLOWED_HOSTS:?missing}\nenv:\n  CUSTOM_PROVIDER_API_KEY: hidden\nx: ${{ vars.GCP_PROJECT_ID }}')>={'API_ALLOWED_HOSTS','CUSTOM_PROVIDER_API_KEY','GCP_PROJECT_ID'}
    assert 'hidden' not in m.reference_names('x.yml','env:\n  TGOS_API_KEY: hidden')


def test_javascript_constants_and_yaml_heredoc_are_not_environment_dependencies():
    m=audit()
    assert m.reference_names('client.ts','const API_BASE="url"; const TOKEN_SECRET="fixture"; const url=`${API_BASE}/v1`;')==set()
    assert m.reference_names('ci.yml','run: |\n  python - <<PY\n  PY\n')==set()


def test_git_env_example_projection_returns_names_never_assignment_values(tmp_path,monkeypatch):
    import subprocess
    m=audit();assert hasattr(m,'template_identifier_evidence')
    subprocess.run(['git','init','-q',str(tmp_path)],check=True)
    (tmp_path/'.env.example').write_text('GOOGLE_MAPS_API_KEY=SYNTHETIC_VALUE_DO_NOT_RETURN\n# TDX_CLIENT_SECRET=HIDDEN_EXAMPLE\nexport APP_ENV=preview\n')
    (tmp_path/'.env').write_text('PRIVATE_SHOULD_NOT_BE_READ=PRIVATE_SYNTHETIC_VALUE\n')
    subprocess.run(['git','-C',str(tmp_path),'add','.env.example','.env'],check=True)
    original=Path.read_text
    def reject(path,*args,**kwargs):
        assert path.name not in {'.env','.env.example'},'envfile content entered Python auditor'
        return original(path,*args,**kwargs)
    monkeypatch.setattr(Path,'read_text',reject)
    result=m.template_identifier_evidence(tmp_path)
    rows=result['templates']['.env.example']
    assert set(rows)=={'GOOGLE_MAPS_API_KEY','TDX_CLIENT_SECRET','APP_ENV'}
    assert result['template_values_materialized'] is False
    assert result['host_envfiles_opened'] is False
    assert 'PRIVATE_SHOULD' not in str(result) and 'SYNTHETIC_VALUE' not in str(result)


def test_git_env_projection_refuses_unreviewed_or_credential_shaped_output(tmp_path,monkeypatch):
    import subprocess
    m=audit();assert hasattr(m,'template_identifier_evidence')
    subprocess.run(['git','init','-q',str(tmp_path)],check=True)
    (tmp_path/'.env.example').write_text('APP_ENV=example\n')
    subprocess.run(['git','-C',str(tmp_path),'add','.env.example'],check=True)
    real=subprocess.run
    def injected(args,**kwargs):
        if 'grep' in args:
            return subprocess.CompletedProcess(args,0,stdout=('.env.example:AKIA'+'Z'*16+'=\n').encode(),stderr=b'')
        return real(args,**kwargs)
    monkeypatch.setattr(m.subprocess,'run',injected)
    with pytest.raises(ValueError) as exc:m.template_identifier_evidence(tmp_path)
    assert str(exc.value)=='template_identifier_credential_literal_forbidden'


@pytest.mark.parametrize('name',['UNMAPPED_PROVIDER_API_KEY','UNMAPPED_CLIENT_SECRET','UNMAPPED_SECRET_KEY','PASSWORD','TOKEN'])
def test_unmapped_example_secret_is_never_nonsecret_runtime_configuration(monkeypatch,name):
    m=audit();root=Path(__file__).resolve().parents[1]
    monkeypatch.setattr(m,'file_metadata',lambda path:{'state':'UNKNOWN'})
    monkeypatch.setattr(m,'template_identifier_evidence',lambda root:{'templates':{'.env.example':[name]}})
    rows={r['name']:r for r in m.build_dependency_matrix(root)['dependencies']}
    assert rows[name]['classification']=='UNKNOWN'
    assert rows[name]['target_location']=='NOT_ADMITTED_FILE_ONLY_SECRET_REVIEW_REQUIRED'
    assert rows[name]['identifier_kind']=='credential'
