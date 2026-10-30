"""Retirement inventory is evidence, never a cloud or maintenance action."""
import importlib
from pathlib import Path
import pytest
import subprocess


def module():
    try:return importlib.import_module('services.professor_retirement_inventory')
    except ImportError:pytest.fail('retirement dependency inventory missing')


def test_exact_render_jobs_remain_blocked_on_separate_local_maintenance():
    report=module().retirement_inventory(Path(__file__).resolve().parents[1])
    jobs=report['render']['protected_maintenance_workflows']
    assert {j['workflow'] for j in jobs}=={'.github/workflows/refresh-commute-snapshot.yml',
        '.github/workflows/refresh-market-read-model.yml','.github/workflows/reconcile-market-coverage.yml'}
    assert all(j['public_professor_retarget_allowed'] is False for j in jobs)
    assert all('RENDER_API_BASE_URL' in j['secret_names'] for j in jobs)
    assert report['render']['retirement_allowed'] is False
    assert report['cloud_run']['retirement_allowed'] is False
    assert report['ready_to_retire_credentials']==[]


def test_inventory_records_source_declarations_without_live_presence_claims():
    report=module().retirement_inventory(Path(__file__).resolve().parents[1])
    assert report['live_cloud_configuration_proven'] is False
    assert report['cloud_run']['service']=='proptech-earth-engine-api'
    assert 'GOOGLE_MAPS_API_KEY' in report['render']['declared_environment_names']
    assert report['values_included'] is False and report['actions_executed']==[]
    assert report['waiting_only_for_router_wan'] is False
    assert report['public_maintenance_routes_enabled'] is False


@pytest.mark.parametrize('kind',['untracked_workflow','tracked_workflow_symlink','render_symlink'])
def test_inventory_never_opens_untracked_or_symlinked_private_sources(tmp_path,kind):
    subprocess.run(['git','init','-q',str(tmp_path)],check=True)
    workflows=tmp_path/'.github/workflows';workflows.mkdir(parents=True)
    (tmp_path/'render.yaml').write_text('services: []\n')
    (workflows/'normal.yml').write_text('name: harmless\n')
    private=tmp_path/'private.env';private.write_text('PRIVATE_TOKEN=SYNTHETIC_DO_NOT_OPEN\n')
    if kind=='render_symlink':
        (tmp_path/'render.yaml').unlink();(tmp_path/'render.yaml').symlink_to(private)
    else:(workflows/'private.yml').symlink_to(private)
    paths=['render.yaml','.github/workflows/normal.yml']
    if kind=='tracked_workflow_symlink':paths.append('.github/workflows/private.yml')
    subprocess.run(['git','-C',str(tmp_path),'add',*paths],check=True)
    if kind=='untracked_workflow':
        result=module().retirement_inventory(tmp_path)
        assert len(result['github_ci_workflows'])==1
        assert 'PRIVATE_TOKEN' not in str(result)
    else:
        with pytest.raises(ValueError):module().retirement_inventory(tmp_path)


@pytest.mark.parametrize('field',['secret','environment'])
def test_inventory_refuses_credential_shaped_identifiers_without_echo(tmp_path,field):
    subprocess.run(['git','init','-q',str(tmp_path)],check=True)
    workflows=tmp_path/'.github/workflows';workflows.mkdir(parents=True)
    (tmp_path/'render.yaml').write_text('services: []\n')
    text='x: ${{ secrets.'+'AKIA'+'Z'*16+' }}\n' if field=='secret' else '  environment: sk-proj-'+'z'*40+'\n'
    (workflows/'normal.yml').write_text(text)
    subprocess.run(['git','-C',str(tmp_path),'add','render.yaml','.github/workflows/normal.yml'],check=True)
    with pytest.raises(ValueError) as exc:module().retirement_inventory(tmp_path)
    assert str(exc.value)=='retirement_identifier_credential_literal_forbidden'
