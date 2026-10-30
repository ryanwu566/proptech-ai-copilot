"""Migration classes and operator-only storage; synthetic credentials only."""
import copy
import importlib
import json
from pathlib import Path

import pytest


def module():
    try:
        return importlib.import_module('scripts.ops.professor_provider_credentials')
    except ImportError:
        pytest.fail('provider credential workflow missing')


def empty_plan():
    return {'schema': 'professor-provider-install-plan-v1', 'values_included': False,
            'operation': 'store_only', 'required': []}


def entry(name='GOOGLE_MAPS_API_KEY', mode='hidden'):
    return {'name': name, 'classification': 'MISSING_REQUIRED',
            'required_consumer_approved': True, 'absence_confirmed': True,
            'input_mode': mode}


def test_empty_required_set_needs_no_root_secret_access_or_service_action(tmp_path, monkeypatch, capsys):
    m = module(); plan = tmp_path/'plan.json'; plan.write_text(json.dumps(empty_plan()))
    monkeypatch.setattr(m, 'PLAN', plan)
    monkeypatch.setattr(m.os, 'geteuid', lambda: 1000)
    assert m.main(['--install-required']) == 0
    result = json.loads(capsys.readouterr().out)
    assert result['status'] == 'NO_INSTALLATION_REQUIRED'
    assert result['stored_names'] == [] and result['activation_performed'] is False


def test_plan_accepts_only_confirmed_required_canonical_credentials():
    m = module(); p = empty_plan(); p['required'] = [entry()]
    assert m.validate_plan(p)[0]['name'] == 'GOOGLE_MAPS_API_KEY'


@pytest.mark.parametrize('change', ['optional', 'unapproved', 'unknown_absence', 'browser',
                                  'legacy', 'value', 'duplicate', 'core_hidden', 'userdb'])
def test_plan_refuses_unsafe_or_unreviewed_population_without_reflection(change):
    m = module(); p = empty_plan(); p['required'] = [entry()]
    row = p['required'][0]
    if change == 'optional': row['classification'] = 'OPTIONAL_NOT_ENABLED'
    if change == 'unapproved': row['required_consumer_approved'] = False
    if change == 'unknown_absence': row['absence_confirmed'] = False
    if change == 'browser': row['name'] = 'NEXT_PUBLIC_GOOGLE_MAPS_BROWSER_KEY'
    if change == 'legacy': row['name'] = 'RENDER_API_KEY'
    if change == 'value': row['value'] = 'SYNTHETIC_DO_NOT_ECHO'
    if change == 'duplicate': p['required'].append(copy.deepcopy(row))
    if change == 'core_hidden': row['name'] = 'DATABASE_URL'
    if change == 'userdb': row['name'] = 'PROFESSOR_USER_DATABASE_URL'
    with pytest.raises(Exception) as error:
        m.validate_plan(p)
    assert 'SYNTHETIC' not in str(error.value)


def test_parser_never_reflects_accidental_secret_argument(capsys):
    m = module()
    assert m.main(['--unexpected', 'SYNTHETIC_DO_NOT_ECHO']) == 1
    assert 'SYNTHETIC' not in capsys.readouterr().out


def test_nonempty_install_requires_operator_root(tmp_path, monkeypatch, capsys):
    m = module(); p = empty_plan(); p['required'] = [entry()]
    plan = tmp_path/'plan.json'; plan.write_text(json.dumps(p))
    monkeypatch.setattr(m, 'PLAN', plan); monkeypatch.setattr(m.os, 'geteuid', lambda: 1000)
    assert m.main(['--install-required']) == 1
    assert json.loads(capsys.readouterr().out)['reason_code'] == 'operator_root_required'


def test_stored_provider_restoration_requires_root_and_never_accepts_input(monkeypatch,capsys):
    m=module();monkeypatch.setattr(m.os,'geteuid',lambda:1000)
    assert m.main(['--stage-stored-providers'])==1
    assert json.loads(capsys.readouterr().out)['reason_code']=='operator_root_required'
    assert m.main(['--stage-stored-providers','--from-file','GOOGLE_APPLICATION_CREDENTIALS=/synthetic/path'])==1
    assert json.loads(capsys.readouterr().out)['reason_code']=='restore_does_not_accept_imports'


def test_migration_classes_keep_unknown_optional_and_browser_distinct():
    m = module()
    from services.professor_credentials import ACTIVE
    source = {'schema':'professor-stage5-provider-dependencies-v2', 'values_included':False, 'dependencies': [
        {'name':'DATABASE_URL','classification':'PROFESSOR_SERVER_ACTIVE','professor_secret_presence':'PRESENT_ACCEPTED_RECEIPT'},
        {'name':'NEXT_PUBLIC_SUPABASE_URL','classification':'VERCEL_BROWSER_PUBLIC'},
        {'name':'GOOGLE_MAPS_API_KEY','classification':'PROFESSOR_SERVER_OPTIONAL','professor_secret_presence':'UNKNOWN'},
        {'name':'RENDER_API_KEY','classification':'LEGACY_CLOUD_ONLY'},
        {'name':'UNRESOLVED_KEY','classification':'UNKNOWN'},
    ], 'accepted_required_credential_evidence':{'status':'PASS_ACCEPTED_RECEIPT','verified_secret_files':list(ACTIVE.values())}}
    rows = {r['name']:r for r in m.migration_rows(source)}
    assert rows['DATABASE_URL']['migration_class'] == 'ALREADY_ON_PROFESSOR_SERVER'
    assert rows['NEXT_PUBLIC_SUPABASE_URL']['migration_class'] == 'BROWSER_PUBLIC_ON_VERCEL'
    assert rows['GOOGLE_MAPS_API_KEY']['migration_class'] == 'OPTIONAL_NOT_ENABLED'
    assert rows['RENDER_API_KEY']['migration_class'] == 'LEGACY_CLOUD_ONLY'
    assert rows['UNRESOLVED_KEY']['migration_class'] == 'UNKNOWN_LIVE_METADATA'
    assert not any(r['migration_class'] in {'READY_TO_RETIRE','MISSING_REQUIRED'} for r in rows.values())


def test_browser_or_optional_presence_does_not_prove_professor_admission():
    source = {'schema':'professor-stage5-provider-dependencies-v2', 'values_included':False,
              'dependencies':[{'name':'NEXT_PUBLIC_SUPABASE_URL','classification':'VERCEL_BROWSER_PUBLIC',
                               'professor_secret_presence':'PRESENT_ACCEPTED_RECEIPT'}]}
    assert module().migration_rows(source)[0]['migration_class'] == 'BROWSER_PUBLIC_ON_VERCEL'


def test_migration_refuses_values_and_credential_shaped_identifiers():
    m = module()
    with pytest.raises(Exception):
        m.migration_rows({'schema':'professor-stage5-provider-dependencies-v2','values_included':True,'dependencies':[]})
    with pytest.raises(Exception):
        m.migration_rows({'schema':'professor-stage5-provider-dependencies-v2','values_included':False,
                          'dependencies':[{'name':'AKIA'+'Z'*16,'classification':'UNKNOWN'}]})


@pytest.mark.parametrize('proof', [None, {'status':'FAIL'}, {'status':'UNAVAILABLE_ACCEPTED_RECEIPT'},
                                  {'status':'PASS_ACCEPTED_RECEIPT','verified_secret_files':[]},
                                  {'status':'PASS_ACCEPTED_RECEIPT','verified_secret_files':['foreign_file']}])
def test_unproven_receipt_cannot_certify_server_presence(proof):
    source = {'schema':'professor-stage5-provider-dependencies-v2','values_included':False,
              'dependencies':[{'name':'DATABASE_URL','classification':'PROFESSOR_SERVER_ACTIVE',
                               'professor_secret_presence':'PRESENT_ACCEPTED_RECEIPT'}]}
    if proof is not None: source['accepted_required_credential_evidence'] = proof
    assert module().migration_rows(source)[0]['migration_class'] == 'UNKNOWN_LIVE_METADATA'


@pytest.mark.parametrize('field', ['missing_required_credentials', 'unverified_current_profile_credentials'])
def test_conflicting_core_presence_fails_closed(field):
    source = {'schema':'professor-stage5-provider-dependencies-v2', 'values_included':False,
              field:['DATABASE_URL'], 'dependencies':[{'name':'DATABASE_URL',
              'classification':'PROFESSOR_SERVER_ACTIVE','professor_secret_presence':'PRESENT_ACCEPTED_RECEIPT'}]}
    with pytest.raises(Exception) as error:
        module().migration_rows(source)
    assert str(error.value) == 'migration_evidence_contradiction'


@pytest.fixture
def synthetic_store(tmp_path, monkeypatch):
    """Adapt only root/storage boundaries; exercise real validation and writes."""
    import os
    from services import selfhost_secret_files as secrets
    m = module(); base = m.stage2
    store = tmp_path/'store'; store.mkdir(mode=0o700)
    uid, gid = os.getuid(), os.getgid()
    real_write, real_open = secrets.atomic_secret_write, secrets.open_directory
    monkeypatch.setattr(base, 'STORE', store)
    monkeypatch.setattr(base, 'storage_boundary', lambda: None)
    monkeypatch.setattr(base, 'check_backing_storage', lambda path: None)
    monkeypatch.setattr(base, 'open_directory', lambda path, **kw: real_open(path, owner=uid, **kw))
    monkeypatch.setattr(base, 'atomic_secret_write', lambda path, name, value, **kw:
                        real_write(path, name, value, owner=uid, gid=gid, **kw))
    monkeypatch.setattr(m.os, 'geteuid', lambda: 0)
    monkeypatch.setenv('SUDO_UID', str(uid))
    return m, base, store


def test_nonempty_install_validates_every_value_then_writes_private_files(synthetic_store, monkeypatch):
    import os, stat
    m, base, store = synthetic_store
    monkeypatch.setattr(base, 'hidden_input', lambda prompt: 'SYNTHETIC_PROVIDER_MATERIAL')
    p = empty_plan(); p['required'] = [entry()]
    stored = []; m.install(m.validate_plan(p), {}, stored)
    path = store/'google_maps_api_key'
    assert stored == ['GOOGLE_MAPS_API_KEY']
    assert path.read_text() == 'SYNTHETIC_PROVIDER_MATERIAL'
    assert path.stat().st_uid == os.getuid() and stat.S_IMODE(path.stat().st_mode) == 0o600
    assert path.stat().st_nlink == 1 and sorted(x.name for x in store.iterdir()) == ['google_maps_api_key']


def test_bad_second_value_creates_no_secret_files(synthetic_store, monkeypatch):
    m, base, store = synthetic_store
    values = iter(['SYNTHETIC_PROVIDER_MATERIAL', ''])
    monkeypatch.setattr(base, 'hidden_input', lambda prompt: next(values))
    p = empty_plan(); p['required'] = [entry(), entry('TGOS_APP_ID')]
    with pytest.raises(Exception): m.install(m.validate_plan(p), {}, [])
    assert list(store.iterdir()) == []


@pytest.mark.parametrize('symlink', [False, True])
def test_existing_targets_refused_before_any_input(synthetic_store, monkeypatch, tmp_path, symlink):
    m, base, store = synthetic_store
    target = store/'google_maps_api_key'
    original = tmp_path/'preserved'; original.write_text('SYNTHETIC_PRESERVED')
    if symlink: target.symlink_to(original)
    else: target.write_text('SYNTHETIC_PRESERVED')
    monkeypatch.setattr(base, 'hidden_input', lambda prompt: pytest.fail('existing target prompted for value'))
    p = empty_plan(); p['required'] = [entry()]
    with pytest.raises(Exception) as error: m.install(m.validate_plan(p), {}, [])
    assert str(error.value) == 'existing_credential_will_not_be_replaced'
    assert original.read_text() == 'SYNTHETIC_PRESERVED'
    assert target.read_text() == 'SYNTHETIC_PRESERVED'


def test_core_restore_uses_protected_existing_file_only(synthetic_store, tmp_path):
    m, base, store = synthetic_store
    source = tmp_path/'protected-recovery'
    value = 'postgresql://app_runtime:synthetic_password_0123456789@postgres_app/proptech_app'
    source.write_text(value); source.chmod(0o600)
    p = empty_plan(); p['required'] = [entry('DATABASE_URL', 'protected_file')]
    stored = []; m.install(m.validate_plan(p), {'DATABASE_URL':source}, stored)
    assert (store/'app_database_url').read_text() == value
    assert source.read_text() == value and stored == ['DATABASE_URL']
