"""Authority is proven by public frontend binding, never by secrets or DB name alone."""
from copy import deepcopy
from uuid import uuid4
import json

import pytest

from scripts.ops import professor_stage4a_authority as audit


def observation(origin='https://flyhsjcynreuofbcdxod.supabase.co'):
    return {'schema':'professor-public-auth-authority-observation-v1','frontend_origin':'https://proptech-ai-copilot.vercel.app',
        'release_commit':'9cc40d645757af4513d9afdf0c008939cc489a77','release_stable':True,
        'credential_values_returned':False,'credential_values_compared':False,'auth_requests_performed':False,'frontend_modified':False,'read_only':True,
        'assets':[{'path':audit.REVIEWED_ASSET,'sha256':audit.REVIEWED_SHA256,'binding_proof':'manually_reviewed_immutable_asset_sha256','authenticated_audience_marker':True,'issuer_suffix_marker':True,'password_signin_marker':True,
          'configuration_bindings':[{'public_origin':origin,'url_constructor_returns_origin':True,'client_uses_same_configuration_url_and_key':True,'persist_session':True,'auto_refresh':True,'detect_session_in_url':False}]}]}


def provider():
    return {'project_ref':'flyhsjcynreuofbcdxod','auth_users':1,'confirmed_users':1,'prior_signin_users':1,'authenticated_audience_users':1,'authenticated_role_users':1,'banned_users':0,
        'deleted_users':0,'anonymous_users':0,'subject_storage_type':'uuid','legacy_account_authority_present':False,'legacy_workspace_cases_present':False}


def test_public_frontend_provider_backend_agree_without_key_comparison():
    result=audit.evaluate(observation(),provider())
    assert result['status']=='PASS' and result['issuer_conflict'] is False
    assert result['issuer']=='https://flyhsjcynreuofbcdxod.supabase.co/auth/v1'
    assert result['audience']=='authenticated' and result['password_migration_required'] is False
    assert result['subject_mapping']=='verified_supabase_sub_uuid_unchanged'
    assert len(result['authority_sha256'])==64


def test_database_project_or_doc_reference_alone_never_proves_frontend_authority():
    o=observation();o['assets']=[]
    assert audit.evaluate(o,provider())['status']=='PENDING'
    o=observation();o['assets'][0]['configuration_bindings'][0]['client_uses_same_configuration_url_and_key']=False
    assert audit.evaluate(o,provider())['status']=='PENDING'


@pytest.mark.parametrize('change',['backend','audience','provider','multiple'])
def test_conflicting_authority_fails_without_silently_selecting_one(change):
    o=observation();p=provider();args={}
    alternate='https://osypacuurzkqerfhcqty.supabase.co'
    if change=='backend':args['backend_issuer']=alternate+'/auth/v1'
    elif change=='audience':args['audience']='other'
    elif change=='provider':p['project_ref']='osypacuurzkqerfhcqty'
    else:o['assets'].append(observation(alternate)['assets'][0])
    result=audit.evaluate(o,p,**args)
    assert result['status']=='FAIL' and result['issuer_conflict'] is True


@pytest.mark.parametrize('field,value',[('legacy_account_authority_present',True),('banned_users',1),('subject_storage_type','text'),('authenticated_audience_users',0),('authenticated_role_users',0)])
def test_unreconciled_account_metadata_stays_pending(field,value):
    p=provider();p[field]=value
    assert audit.evaluate(observation(),p)['status']=='PENDING'


def test_malformed_origin_or_changed_release_cannot_pass_or_echo_values():
    o=observation('https://user:SYNTHETIC_SECRET@flyhsjcynreuofbcdxod.supabase.co')
    result=audit.evaluate(o,provider())
    assert result['status']=='FAIL' and 'SYNTHETIC_SECRET' not in json.dumps(result)
    o=observation();o['release_stable']=False
    assert audit.evaluate(o,provider())['status']=='PENDING'


def test_verified_uuid_is_preserved_and_other_issuer_is_rejected(monkeypatch):
    from tests.test_vnext_auth_api import PUBLIC_KEY, _token
    from services.vnext.auth import SupabaseJWTVerifier
    from services.vnext.errors import VNextError
    monkeypatch.setenv('PROFESSOR_USERDB_ENABLED','true')
    authority=audit.evaluate(observation(),provider())
    verifier=SupabaseJWTVerifier(issuer=authority['issuer'],audience=authority['audience'],signing_key_resolver=lambda _:PUBLIC_KEY)
    id=uuid4();session=uuid4()
    token=_token(subject=str(id),issuer=authority['issuer'],role='authenticated',session_id=str(session))
    principal=verifier.verify(token)
    assert principal.user_id==id and principal.token_subject==str(id) and principal.issuer==authority['issuer']
    with pytest.raises(VNextError):verifier.verify(_token(subject=str(id),issuer='https://osypacuurzkqerfhcqty.supabase.co/auth/v1',role='authenticated',session_id=str(session)))


@pytest.mark.parametrize('field,value',[('sha256','b'*64),('path','/_next/static/unknown.js'),('binding_proof','heuristic')])
def test_unreviewed_assets_never_become_automatic_authority(field,value):
    o=observation();o['assets'][0][field]=value
    assert audit.evaluate(o,provider())['status']=='PENDING'


def test_impossible_account_aggregates_stay_pending():
    p=provider();p['prior_signin_users']=2
    assert audit.evaluate(observation(),p)['status']=='PENDING'


def test_recorded_deployment_metadata_matches_backend_profile_and_fingerprint():
    from pathlib import Path
    import re
    root=Path(__file__).resolve().parents[1];folder=root/'reports/professor-stage4a-auth-userdb'
    o=json.loads((folder/'frontend-authority-observation.json').read_text())
    p=json.loads((folder/'provider-authority-metadata.json').read_text())
    profile=(root/'infra/selfhost/professor-userdb.override.yml').read_text()
    issuer=re.search(r'^      SUPABASE_JWT_ISSUER: (https://[a-z0-9-]+\.supabase\.co/auth/v1)$',profile,re.M).group(1)
    audience=re.search(r'^      SUPABASE_JWT_AUDIENCE: ([a-z]+)$',profile,re.M).group(1)
    result=audit.evaluate(o,p,backend_issuer=issuer,audience=audience)
    assert result['status']=='PASS'
    assert result['authority_sha256']=='ffd784ac6e456727b17ad7daf4db013351e76b43599c27ec4f4aa830958b588e'
    reviewed=json.loads((folder/'reviewed-frontend-authority.json').read_text())
    assert reviewed['asset_sha256']==audit.REVIEWED_SHA256
    assert reviewed['release_commit']==audit.REVIEWED_RELEASE
    assert reviewed['public_origin']==audit.REVIEWED_ORIGIN


def test_conflicting_legacy_backend_project_url_is_not_silently_ignored():
    result=audit.evaluate(observation(),provider(),backend_project_url='https://osypacuurzkqerfhcqty.supabase.co')
    assert result['status']=='FAIL' and result['issuer_conflict'] is True
