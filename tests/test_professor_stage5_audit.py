"""No remote configuration or real credentials are read by these tests."""
import importlib
import json
from pathlib import Path

import pytest


def api():
    try:return importlib.import_module('services.professor_credentials')
    except ImportError:pytest.fail('Stage5 sanitized credential auditor is not implemented')


def test_env_reference_extraction_returns_names_not_values():
    source='''import os
NAME='GOOGLE_MAPS_API_KEY'
os.getenv(NAME)
os.environ.get('TDX_CLIENT_SECRET')
'''
    assert api().environment_names('source.py',source)=={'GOOGLE_MAPS_API_KEY','TDX_CLIENT_SECRET'}
    assert api().environment_names('client.ts','process.env.NEXT_PUBLIC_SUPABASE_URL')=={'NEXT_PUBLIC_SUPABASE_URL'}
    assert api().environment_names('deploy.yml','${{ secrets.GOOGLE_MAPS_API_KEY }}')=={'GOOGLE_MAPS_API_KEY'}


def test_cloud_inventory_accepts_names_only_and_keeps_scope():
    value={'platform':'cloud_run','source':'operator_control_plane_metadata','environment_names':['GOOGLE_MAPS_API_KEY'],
           'secret_reference_names':['provider-maps-key'],'values_exported':False}
    result=api().validate_cloud_metadata(value)
    assert result['environment_names']==['GOOGLE_MAPS_API_KEY'] and result['platform']=='cloud_run'


@pytest.mark.parametrize('mutation',['value','name_with_value','secret_json','false_attestation'])
def test_value_bearing_cloud_exports_are_refused_without_echo(mutation):
    value={'platform':'render','source':'operator_control_plane_metadata','environment_names':[],
           'secret_reference_names':[],'values_exported':False}
    if mutation=='value':value['values']={'GOOGLE_MAPS_API_KEY':'SYNTHETIC_CANARY'}
    if mutation=='name_with_value':value['environment_names']=['GOOGLE_MAPS_API_KEY=SYNTHETIC_CANARY']
    if mutation=='secret_json':value['secret_reference_names']=[{'name':'x','value':'SYNTHETIC_CANARY'}]
    if mutation=='false_attestation':value['values_exported']=True
    with pytest.raises(ValueError) as exc:api().validate_cloud_metadata(value)
    assert 'SYNTHETIC' not in str(exc.value)


def test_active_six_are_distinct_from_optional_and_cloud_only():
    root=Path(__file__).resolve().parents[1];report=api().build_matrix(root)
    rows={r['name']:r for r in report['credentials']}
    for n in ['DATABASE_URL','API_USAGE_DATABASE_URL','API_USAGE_PEER_HMAC_KEY','PILOT_SESSION_SIGNING_KEY','VALUATION_DATABASE_URL','PROFESSOR_USER_DATABASE_URL']:
        assert rows[n]['classification']=='PROFESSOR_SERVER_ACTIVE'
        assert rows[n]['active_api_secret_mount'] is True
    assert rows['GOOGLE_MAPS_API_KEY']['classification']=='PROFESSOR_SERVER_OPTIONAL'
    assert rows['NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY']['classification']=='VERCEL_BROWSER_PUBLIC'
    assert rows['VERCEL_TOKEN']['classification']=='LEGACY_CLOUD_ONLY'
    assert report['remote_inventory_complete'] is False
    assert not any(r['classification']=='READY_TO_RETIRE' for r in rows.values())


def test_supported_optional_tdx_storage_never_claims_runtime_admission():
    report=api().build_matrix(Path(__file__).resolve().parents[1])
    rows={r['name']:r for r in report['credentials']}
    assert 'TDX_CLIENT_SECRET' in rows
    assert rows['TDX_CLIENT_SECRET']['installer_support'] is True
    assert rows['TDX_CLIENT_SECRET']['classification']=='PROFESSOR_SERVER_OPTIONAL'
    assert rows['TDX_CLIENT_SECRET']['active_api_secret_mount'] is False
    assert rows['TDX_CLIENT_SECRET']['automatic_activation'] is False


def test_root_auditor_has_no_mutation_or_secret_read_commands():
    p=Path(__file__).resolve().parents[1]/'scripts/ops/professor_stage5.py'
    assert p.is_file(),'Stage5 operator audit tool missing'
    text=p.read_text()
    assert 'sudo' not in text and 'compose down' not in text and 'systemctl restart' not in text
    assert 'configuration_values_returned' in text
    assert 'read_secret(' not in text and 'installed_values(' not in text


def test_evidence_outputs_cannot_target_sources_or_runtime_configuration(tmp_path):
    from scripts.ops import professor_stage5 as ops
    assert hasattr(ops,'validate_evidence_destination'),'safe evidence path guard missing'
    for path in ['/dev/sda','/run/media/andy/Crucial X9/DB/evidence.json','/srv/proptech-data/DB/evidence.json','/etc/proptech-selfhost/runtime.env','/run/proptech-selfhost/secrets/new.json']:
        with pytest.raises(ValueError):ops.validate_evidence_destination(Path(path))
    expected=Path(ops.ROOT)/'reports/professor-stage5-ingress/test.json'
    assert ops.validate_evidence_destination(expected)==expected.resolve()


def test_blocked_plan_returns_nonzero_without_mutations(capsys):
    from scripts.ops import professor_stage5 as ops
    path=ops.ROOT/'config/professor-direct-ingress.plan.example.json'
    result=ops.main(['--plan',str(path)])
    assert result==2
    output=json.loads(capsys.readouterr().out)
    assert output['ready_for_operator_apply'] is False
    assert output['operator_command'] is None


def test_audit_commands_use_fixed_path_with_administrative_binaries(monkeypatch):
    from scripts.ops import professor_stage5 as ops
    import subprocess
    seen=[]
    def capture(args,**kwargs):
        seen.append(kwargs['env'])
        return subprocess.CompletedProcess(args,1,stdout=b'',stderr=b'')
    monkeypatch.setattr(ops.subprocess,'run',capture)
    assert ops.run(['ufw','status','verbose'])==(1,b'')
    assert '/usr/sbin' in seen[0]['PATH'].split(':')
    assert set(seen[0])=={'PATH','LANG','DOCKER_HOST','DOCKER_CONFIG'}


def test_source_audit_skips_env_and_credential_files_before_open(tmp_path,monkeypatch):
    m=api();root=Path(__file__).resolve().parents[1]
    (tmp_path/'config').mkdir()
    (tmp_path/'config/professor-server-credentials.json').write_text((root/'config/professor-server-credentials.json').read_text())
    protected=['infra/selfhost/professor-secrets.env.example','runtime.env','compose.env.example',
        'credentials/service-account.json','config/adc.json','config/private-key.json']
    for name in protected:
        target=tmp_path/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_text('DO_NOT_READ')
    monkeypatch.setattr(m.subprocess,'check_output',lambda *a,**kw:'\0'.join(protected).encode())
    original=Path.read_text
    def read(path,*a,**kw):
        assert path not in [tmp_path/name for name in protected],'protected source was opened'
        return original(path,*a,**kw)
    monkeypatch.setattr(Path,'read_text',read)
    report=m.build_matrix(tmp_path)
    assert set(report['protected_source_files_not_opened'])==set(protected)


@pytest.mark.parametrize('field',['environment_names','secret_reference_names'])
def test_literal_token_shaped_metadata_rejected_before_output(field):
    value={'platform':'render','source':'operator_control_plane_metadata','environment_names':[],
           'secret_reference_names':[],'values_exported':False}
    value[field]=['AKIA'+'Z'*16]
    with pytest.raises(ValueError) as exc:api().validate_cloud_metadata(value)
    assert 'AKIA' not in str(exc.value)


def test_documentation_prefixes_and_constants_are_not_environment_names():
    report=api().build_matrix(Path(__file__).resolve().parents[1])
    names={r['name'] for r in report['credentials']}
    assert not names.intersection({'NEXT_PUBLIC_','NEXT_PUBLIC_SUPABASE','TGOS_MAP_API','TGOS_MIN_REMAINING_SECONDS','R2_REMOTE'})
