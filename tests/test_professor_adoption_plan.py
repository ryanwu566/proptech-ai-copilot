"""Pure adoption/retirement decisions. No credentials, DB, providers or host IO."""
import importlib
import pytest


def module():
    try:return importlib.import_module('services.professor_adoption_plan')
    except ImportError:pytest.fail('final adoption and retirement matrix missing')


def inputs():
    from services.professor_credentials import ACTIVE
    dependencies={'schema':'professor-stage5-provider-dependencies-v2','values_included':False,
        'known_current_profile_credentials_on_server':True,'missing_required_credentials':[],'unverified_current_profile_credentials':[],
        'accepted_required_credential_evidence':{'status':'PASS_ACCEPTED_RECEIPT','verified_secret_files':list(ACTIVE.values()),'database_security_probe':'PASS_ACCEPTED_RECEIPT_NOT_FRESH'},
        'all_requested_audit_scopes_complete':False,
        'dependencies':[{'name':n,'professor_secret_presence':'PRESENT_ACCEPTED_RECEIPT'} for n in ACTIVE]}
    baseline={'status':'PASS','checks':[{'name':'health','status':'PASS'},{'name':'readiness','status':'PASS'}]}
    return dependencies,baseline


def test_local_replacements_do_not_imply_cloud_migration_or_retirement():
    deps,local=inputs();r=module().adoption_retirement_plan(deps,local)
    for platform in ('cloud_run','render'):
        assert r[platform]['fully_inventoried'] is False
        assert all(row['retirement_ready']=='NO' for row in r[platform]['retirement_matrix'])
        assert all(set(row)>={'dependency','replacement','migrated','tested','retirement_ready','evidence_scope','remaining_proof'} for row in r[platform]['retirement_matrix'])
        assert any(row['migrated']=='YES' and row['tested']=='YES' for row in r[platform]['retirement_matrix'])
    assert r['production_critical_credentials_on_server']=='PARTIAL'
    assert r['ready_for_operator_ingress_apply'] is False and r['retirement_allowed'] is False


def test_missing_or_unproven_core_credentials_are_never_marked_migrated():
    deps,local=inputs();deps['known_current_profile_credentials_on_server']=False;deps['missing_required_credentials']=['DATABASE_URL']
    r=module().adoption_retirement_plan(deps,local)
    assert r['missing_required_credentials']==['DATABASE_URL']
    assert next(x for x in r['provider_adoption'] if x['provider']=='Professor runtime credentials')['migrated']=='NO'


def test_three_jobs_have_definitive_targets_without_activation():
    r=module().adoption_retirement_plan(*inputs());jobs=r['workflow_decisions']
    assert len(jobs)==3
    assert all(j['target_decision']=='A_MOVE_TO_PROFESSOR' for j in jobs)
    assert all(j['interim_decision']=='C_KEEP_EXISTING_EXTERNAL_DEFINITION_UNCHANGED' for j in jobs)
    assert all(j['timer']=='NONE_MANUAL_CADENCE_PRESERVED' and not j['activated'] for j in jobs)
    assert all(j['public_api_retarget_allowed'] is False for j in jobs)
    assert all(j['migrated']=='NO' and j['tested']=='NO' for j in jobs)


def test_commute_process_memory_and_market_writer_gaps_are_explicit():
    jobs=module().adoption_retirement_plan(*inputs())['workflow_decisions']
    commute=next(j for j in jobs if j['kind']=='commute')
    assert commute['current_snapshot_storage']=='API_PROCESS_MEMORY_ONLY'
    assert commute['separate_oneshot_is_runtime_compatible'] is False
    assert 'persistent snapshot' in commute['implementation_required']
    for job in jobs:
        if job['kind']!='commute':
            assert job['reuse_serving_runtime_write_privilege_allowed'] is False
            assert job['new_restricted_operations_role_required'] is True
    coverage=next(j for j in jobs if j['kind']=='coverage')
    assert coverage['legacy_bootstrap_step']=='B_NOT_CARRIED_FORWARD_ALREADY_PROVISIONED'


def test_values_or_unknown_presence_states_cannot_enter_plan_output():
    deps,local=inputs();deps['values_included']=True
    with pytest.raises(ValueError):module().adoption_retirement_plan(deps,local)
    deps,local=inputs();deps['dependencies'][0]['professor_secret_presence']='SYNTHETIC_DO_NOT_ECHO'
    with pytest.raises(ValueError) as exc:module().adoption_retirement_plan(deps,local)
    assert 'SYNTHETIC' not in str(exc.value)


def test_credential_mapping_never_installs_optional_keys_or_changes_frontend():
    r=module().adoption_retirement_plan(*inputs())
    assert all(x['automatic_activation'] is False for x in r['provider_adoption'])
    assert r['privileged_installation_required_now'] is False
    assert r['operator_installation_command'] is None
    browser=next(x for x in r['provider_adoption'] if x['provider']=='Google browser maps')
    assert browser['target_consumer']=='Vercel frontend only'


def test_health_only_cannot_mark_gis_ml_or_authenticated_flows_tested():
    deps,local=inputs();r=module().adoption_retirement_plan(deps,local)
    for platform in ('cloud_run','render'):
        for row in r[platform]['retirement_matrix']:
            if row.get('capability') in {'gis','ml','authenticated_user_flows'}:assert row['tested']=='NO'
    auth=next(x for x in r['provider_adoption'] if x['provider']=='Supabase server verification')
    assert auth['tested']=='NO'


@pytest.mark.parametrize('field',['missing_required_credentials','unverified_current_profile_credentials'])
def test_conflicting_positive_flags_do_not_override_missing_or_unverified(field):
    deps,local=inputs();deps[field]=['DATABASE_URL']
    r=module().adoption_retirement_plan(deps,local)
    row=next(x for x in r['provider_adoption'] if x['provider']=='Professor runtime credentials')
    assert row['migrated']=='NO' and row['tested']=='NO'
    if field=='missing_required_credentials':assert 'recover' in r['installation_note'].lower()


def test_ml_gis_require_named_checks_and_model_identity():
    deps,local=inputs()
    local['checks'] += [{'name':n,'status':'PASS'} for n in ('demographics_village','demographics_location','wra_matched','wra_no_match',
        'ml_companion_health','ml_pinned_status','ml_estimate_honest_support')]
    r=module().adoption_retirement_plan(deps,local)
    ml=next(x for x in r['cloud_run']['retirement_matrix'] if x.get('capability')=='ml')
    assert ml['tested']=='NO'
    local['model_version_matches_stage3']=True
    local['expected_model_version']='plvr-gross-v1-bccf2ec1bc-dcc6587c76b3-6493b5f7'
    r=module().adoption_retirement_plan(deps,local)
    assert next(x for x in r['cloud_run']['retirement_matrix'] if x.get('capability')=='ml')['tested']=='YES'
    assert next(x for x in r['cloud_run']['retirement_matrix'] if x.get('capability')=='gis')['tested']=='YES'


def test_complete_name_lists_do_not_prove_adc_iam_or_critical_profile_adoption():
    deps,local=inputs();deps['all_requested_audit_scopes_complete']=True
    r=module().adoption_retirement_plan(deps,local)
    assert r['provider_credentials_audited'] is False
    assert r['credential_name_scopes_complete'] is True
    assert r['production_critical_credentials_on_server']=='PARTIAL'
