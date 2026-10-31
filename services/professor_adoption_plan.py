"""Pure replacement/retirement plan. Never installs, schedules or runs a job."""
from __future__ import annotations

import json

from services.professor_credentials import ACTIVE,require
from services.professor_activation_scan import SecretScanner,ScanRefused

PRESENCE={'UNKNOWN','PRESENT_ACCEPTED_RECEIPT','PRESENT_METADATA_ONLY','MISSING_REQUIRED','UNSAFE_METADATA','ABSENT_METADATA_ONLY'}


def adoption_retirement_plan(dependencies,local_checks):
    require(dependencies.get('schema')=='professor-stage5-provider-dependencies-v2' and dependencies.get('values_included') is False,'adoption_input_scope_invalid')
    items=dependencies.get('dependencies',[])
    require(len(items)<=2000 and len({r['name'] for r in items})==len(items),'adoption_identifier_set_invalid')
    rows={r['name']:r for r in items}
    def presence(name):
        value=rows.get(name,{}).get('professor_secret_presence','UNKNOWN')
        require(value in PRESENCE,'adoption_presence_state_invalid')
        return value
    missing=dependencies.get('missing_required_credentials',[])
    unverified=dependencies.get('unverified_current_profile_credentials',[])
    for values in (missing,unverified):
        require(isinstance(values,list) and all(isinstance(n,str) and n in ACTIVE for n in values),'adoption_missing_set_invalid')
    proof=dependencies.get('accepted_required_credential_evidence',{})
    core=(dependencies.get('known_current_profile_credentials_on_server') is True
          and proof.get('status')=='PASS_ACCEPTED_RECEIPT'
          and set(proof.get('verified_secret_files',[]))==set(ACTIVE.values())
          and all(presence(name)=='PRESENT_ACCEPTED_RECEIPT' for name in ACTIVE)
          and not missing and not unverified)
    checks=local_checks.get('checks',[])
    local=(local_checks.get('status')=='PASS' and isinstance(checks,list) and checks
           and all(r.get('status')=='PASS' for r in checks)
           and {'health','readiness'}<={r.get('name') for r in checks})
    local=bool(local and core)
    passed_names={r.get('name') for r in checks if r.get('status')=='PASS'}
    gis=local and {'demographics_village','demographics_location','wra_matched','wra_no_match'}<=passed_names
    ml=local and {'ml_companion_health','ml_pinned_status','ml_estimate_honest_support'}<=passed_names
    ml=bool(ml and local_checks.get('model_version_matches_stage3') is True
            and local_checks.get('expected_model_version')=='plvr-gross-v1-bccf2ec1bc-dcc6587c76b3-6493b5f7')
    credential_tested=local and proof.get('database_security_probe')=='PASS_ACCEPTED_RECEIPT_NOT_FRESH'

    def provider(name,credentials,consumer,service,data,capability,required=False,migrated=False):
        states={n:presence(n) for n in credentials}
        for n in credentials:
            if n.startswith('NEXT_PUBLIC_'):states[n]='FRONTEND_ONLY_NOT_A_SERVER_SECRET'
            elif n in {'SUPABASE_URL','SUPABASE_JWT_ISSUER','SUPABASE_JWT_AUDIENCE'}:states[n]='PUBLIC_METADATA_ACCEPTED_STAGE4A' if core else 'PUBLIC_METADATA_UNVERIFIED'
            elif n=='EARTH_ENGINE_PROJECT':states[n]='NONSECRET_PROJECT_METADATA_NOT_REVALIDATED'
        return {'provider':name,'credential_names':credentials,'professor_secret_files':[
            '/etc/proptech-selfhost/secrets/'+ACTIVE[n] for n in credentials if n in ACTIVE],
            'professor_presence':states,'target_consumer':consumer,
            'local_service_or_job':service,'local_data_path_or_schema':data,'local_api_capability':capability,
            'required_current_profile':required,'migrated':'YES' if migrated else 'NO',
            'tested':'YES' if migrated and local else 'NO','test_scope':'accepted local profile only; no new provider calls',
            'automatic_activation':False,'timer_or_cron':'NONE_UNLESS_SEPARATELY_ADMITTED'}
    providers=[
        provider('Professor runtime credentials',list(ACTIVE),'API six-file profile; admin/init secrets excluded','existing api/postgres services',
                 'proptech_app / proptech_api_usage / proptech_valuation','existing application and serving APIs',True,core),
        provider('Google Maps / Places / Routes',['GOOGLE_MAPS_API_KEY'],'separately admitted backend provider only','existing bounded adapters',
                 'no local credential-bearing dataset','geocoding / places / routes'),
        provider('Google browser maps',['NEXT_PUBLIC_GOOGLE_MAPS_BROWSER_KEY'],'Vercel frontend only','existing browser integration',
                 'frontend public configuration only','Maps JavaScript / Street View'),
        provider('Earth Engine',['GOOGLE_APPLICATION_CREDENTIALS','EARTH_ENGINE_PROJECT'],'separately admitted satellite worker','existing bounded Earth Engine worker pool',
                 'protected ADC file; no image-layer copy','optional satellite reference'),
        provider('TGOS',['TGOS_APP_ID','TGOS_API_KEY'],'separately admitted backend geocoder','existing canonical TGOS adapter',
                 'no transformed source archive','optional address resolution'),
        provider('TDX',['TDX_CLIENT_ID','TDX_CLIENT_SECRET'],'future restricted snapshot producer, never current API profile','commute persistence adapter required',
                 '/srv/proptech-runtime/commute (PROPOSED, not created)','optional commute snapshot consumer'),
        provider('Cloudflare R2',['R2_ACCESS_KEY_ID','R2_SECRET_ACCESS_KEY'],'optional archive/upload or remote-artifact consumer','separately admitted operations only',
                 '/srv/proptech-data/DB local NLSC/WRA remain sufficient','no R2 dependency for active local NLSC/WRA'),
        provider('Supabase browser configuration',['NEXT_PUBLIC_SUPABASE_URL','NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY'],'Vercel frontend only','existing Supabase identity SDK',
                 'identities retained in accepted Supabase project','register/login/refresh'),
        provider('Supabase server verification',['SUPABASE_URL','SUPABASE_JWT_ISSUER','SUPABASE_JWT_AUDIENCE'],'FastAPI public JWKS verifier','existing Stage4A identity adapter',
                 'Professor application-user schema; no Supabase signing/service-role secret','session/profile/saved cases',True,core),
        provider('Government local/open-data and archives',[],'existing supported GIS/RIS consumers','read-only local artifacts or existing admitted open-data contract',
                 '/srv/proptech-data/DB; RIS in proptech_app','NLSC/RIS/WRA active; unsupported archives stay explicit'),
        provider('Other optional / restricted provider credentials',['OPENAI_API_KEY','NLSC_GATEWAY_CLIENT_TOKEN'],'separately reviewed consumer only','no new provider activation',
                 'protected Stage2 file contract if admitted','no current-profile requirement'),
    ]
    optional_files={'GOOGLE_MAPS_API_KEY':'google_maps_api_key','GOOGLE_APPLICATION_CREDENTIALS':'earth_engine_adc_json',
        'TGOS_APP_ID':'tgos_app_id','TGOS_API_KEY':'tgos_api_key','TDX_CLIENT_ID':'tdx_client_id','TDX_CLIENT_SECRET':'tdx_client_secret',
        'R2_ACCESS_KEY_ID':'r2_access_key_id','R2_SECRET_ACCESS_KEY':'r2_secret_access_key','OPENAI_API_KEY':'openai_api_key','NLSC_GATEWAY_CLIENT_TOKEN':'nlsc_gateway_client_token'}
    for item in providers:
        item['professor_secret_files'] += ['/etc/proptech-selfhost/secrets/'+optional_files[n] for n in item['credential_names'] if n in optional_files]
        item['optional_presence_or_admission_proven']=False if not item['required_current_profile'] else core
        if item['provider']=='Professor runtime credentials':
            item['tested']='YES' if credential_tested else 'NO'
            item['test_scope']='accepted private DB TLS/privilege probe plus configuration metadata; not public cutover'
        if item['provider']=='Supabase server verification':
            item['tested']='NO'
            item['test_scope']='verification configuration adopted; this local receipt does not exercise authorized provider session/profile/saved-case persistence'

    jobs=[]
    for kind,workflow in [('commute','refresh-commute-snapshot.yml'),('market','refresh-market-read-model.yml'),('coverage','reconcile-market-coverage.yml')]:
        job={'kind':kind,'workflow':'.github/workflows/'+workflow,'target_decision':'A_MOVE_TO_PROFESSOR',
            'interim_decision':'C_KEEP_EXISTING_EXTERNAL_DEFINITION_UNCHANGED','preserve_prior_activity_state':True,
            'external_execution_requested':False,'target_selection_scope':'self-hosted design; no execution/installation approval',
            'whole_workflow_retirement_selected':False,'migrated':'NO','tested':'NO','retirement_ready':'NO','activated':False,
            'public_api_retarget_allowed':False,'timer':'NONE_MANUAL_CADENCE_PRESERVED',
            'target_service':'proposed local manual one-shot; not installed','implementation_required':'reviewed local operations adapter and scoped role',
            'proposed_systemd_unit':{'commute':'proptech-commute-snapshot.service','market':'proptech-market-reconcile.service','coverage':'proptech-coverage-audit.service'}[kind],
            'credentials':'new restricted maintenance-role file contract requires separate review; never reuse serving/admin URL',
            'data':'proptech_valuation derived Market read models only','api_capability':'Market/Trend/Finder/Valuation read consistency',
            'reuse_serving_runtime_write_privilege_allowed':False,'new_restricted_operations_role_required':True,
            'safety':['market_ops stays disabled','no public maintenance endpoint','no raw transaction deletion or TRUNCATE',
                'preserve row38652 storage and serving exclusion','ambiguous evidence remains protected','bounded single-writer execution and transactional rollback']}
        if kind=='commute':
            job.update(current_snapshot_storage='API_PROCESS_MEMORY_ONLY',separate_oneshot_is_runtime_compatible=False,
                implementation_required='persistent snapshot producer plus API loader/reload contract; separate CLI cannot update API process memory',
                credentials='TDX_CLIENT_ID / TDX_CLIENT_SECRET files for admitted producer only; no new API mounts',
                data='/srv/proptech-runtime/commute (PROPOSED, not created)',api_capability='/commute/status and /commute/nearest',
                new_restricted_operations_role_required=False)
        if kind=='market':job['legacy_refresh_copy_allowed']=False
        if kind=='coverage':job['legacy_bootstrap_step']='B_NOT_CARRIED_FORWARD_ALREADY_PROVISIONED'
        jobs.append(job)

    def matrix_row(dependency,replacement,migrated=False,tested=False,proof_needed='actual deployed dependency evidence and approved public cutover',capability=None):
        return {'dependency':dependency,'replacement':replacement,'migrated':'YES' if migrated else 'NO',
            'tested':'YES' if tested else 'NO','retirement_ready':'NO','evidence_scope':'accepted local replacement only; not production caller cutover',
            'remaining_proof':proof_needed,'capability':capability}
    shared=[matrix_row('Private API baseline availability','accepted Professor API',local,local),
        matrix_row('Local NLSC/RIS/WRA replacement','verified local datasets and existing APIs',gis,gis,capability='gis'),
        matrix_row('Local ML replacement','accepted pinned ML companion',ml,ml,capability='ml'),
        matrix_row('Supabase-backed authorized user flows','accepted Stage4 backend; real provider/caller migration acceptance pending',False,False,
            'real authorized session/profile/saved-case persistence and cross-user public E2E',capability='authenticated_user_flows'),
        matrix_row('Application/usage/valuation/user runtime credentials','existing six-file Stage2/4 profile',core,credential_tested),
        matrix_row('Public deployed callers','direct NGINX HTTPS plus Vercel Preview/Production'),
        matrix_row('Unique remote mutable data and background users','verified Professor data authority and scoped local jobs'),
        matrix_row('Reboot / trusted TLS renewal / rollback','reviewed persistent restoration and service ordering')]
    cloud=[*shared,matrix_row('Provider keys and ADC/service identity/IAM','protected optional provider files and individually approved IAM'),
        matrix_row('Current/retained revision and rollback inventory','verified cloud metadata plus retained Professor release artifacts')]
    render=[*shared,matrix_row('Render provider/env-group/file inventory','verified names-only inventory and Stage2 adoption'),
        *[matrix_row(j['kind']+' maintenance workflow',j['target_service']+'; '+j['implementation_required']) for j in jobs]]
    result={'schema':'professor-stage5-adoption-retirement-plan-v1','values_included':False,'plan_only':True,
        'provider_adoption':providers,'workflow_decisions':jobs,
        'cloud_run':{'fully_inventoried':False,'retirement_matrix':cloud,'retirement_allowed':False},
        'render':{'fully_inventoried':False,'retirement_matrix':render,'retirement_allowed':False},
        'provider_credentials_audited':False,
        'credential_name_scopes_complete':dependencies.get('all_requested_audit_scopes_complete') is True,
        'audit_scope_note':'Names alone do not prove deployed ADC/IAM or all required production credentials on Professor; this planning input cannot certify that closure.',
        'production_critical_credentials_on_server':'NO' if missing else 'PARTIAL',
        'missing_required_credentials':missing,'ready_to_retire_credentials':[],
        'known_local_profile_evidence':core,'local_functional_evidence':local,
        'privileged_installation_required_now':bool(missing),'operator_installation_command':None,
        'installation_note':('Required runtime files are missing: recover the same protected credentials through reviewed restore procedures; never generate replacement DB passwords/signing keys.' if missing else
            'No missing current-profile credential confirmed; optional jobs/providers require separate admission, so no speculative privileged installer is released.'),
        'cloud_run_metadata_required':['actual env/secret-reference names','attached service-account identity and ADC source','effective IAM roles/API restrictions','deployed callers and scheduled/background consumers','retained revisions and rollback identity'],
        'render_metadata_required':['actual env/group/file names','deployed callers and current service identity','three workflow activity/disposition and validation','unique mutable state and rollback'],
        'retirement_gates':['outside-LAN trusted Professor HTTPS','Vercel Preview and Production authenticated E2E','profile/saved-case ownership and persistence',
            'ML/GIS/Market/Valuation accepted behavior','all required credential dependencies adopted','reboot and renewal acceptance','no unique remote state/caller remains','explicit retirement approval'],
        'waiting_only_for_router_wan':False,'ready_for_operator_ingress_apply':False,'retirement_allowed':False,'actions_executed':[]}
    try:SecretScanner(()).check_bytes(json.dumps(result).encode())
    except ScanRefused:raise ValueError('adoption_identifier_credential_literal_forbidden') from None
    return result
