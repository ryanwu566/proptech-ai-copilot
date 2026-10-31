from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from backend.api_main import app
from services.professor_userdb import get_repository, PrivateCaseService, PostgresCaseRepository
from services.vnext.auth import get_supabase_jwt_verifier
from tests.test_vnext_auth_api import verifier, _token, USER_ID  # noqa:F401
from tests.test_professor_userdb import pg, repo, principal, OTHER  # noqa:F401
from tests.durable_case_fixtures import snapshot


@pytest.fixture
def client(monkeypatch,repo,verifier):
    monkeypatch.setenv('PROFESSOR_USERDB_ENABLED','true')
    monkeypatch.setattr('services.professor_userdb.validate_configuration',lambda:None)
    monkeypatch.setattr('services.professor_userdb.close_pool',lambda:None)
    app.dependency_overrides[get_supabase_jwt_verifier]=lambda:verifier
    # The verifier dependency calls the configured getter directly, not Depends.
    monkeypatch.setattr('services.professor_userdb.get_repository',lambda:repo)
    app.dependency_overrides[get_repository]=lambda:repo
    with TestClient(app) as c: yield c
    app.dependency_overrides.clear()


def auth(user=USER_ID,session=None,**claims):
    return {'Authorization':'Bearer '+_token(subject=str(user),role='authenticated',session_id=str(session or uuid4()),**claims),
            'Idempotency-Key':uuid4().hex}


def test_profile_and_preference_routes_no_identity_override(client):
    response=client.get('/v1/profile',headers=auth())
    assert response.status_code==200,response.text
    assert response.headers['cache-control']=='no-store'
    p=response.json()
    r=client.patch('/v1/profile',headers=auth(),json={'expected_revision':p['revision'],'display_name':'New'})
    assert r.status_code==200
    assert client.get('/v1/profile',headers=auth(OTHER)).json()['display_name']==''
    assert client.patch('/v1/profile',headers=auth(),json={'expected_revision':p['revision'],'display_name':'stale'}).status_code==409
    assert client.get('/v1/profile?user_id='+str(OTHER),headers=auth()).status_code==422
    assert client.patch('/v1/profile',headers=auth(),json={'expected_revision':1,'user_id':str(OTHER)}).status_code==422
    pref=client.get('/v1/preferences',headers=auth()).json()
    assert client.put('/v1/preferences',headers=auth(),json={'expected_revision':pref['revision'],'data':{'version':1}}).status_code==200


def test_revoked_refreshed_expired_malformed_and_anonymous_sessions(client,caplog):
    session=uuid4(); headers=auth(session=session)
    assert client.get('/v1/session',headers=headers).status_code==200
    assert client.post('/v1/session/logout',headers=headers).json()=={'status':'revoked'}
    assert client.get('/v1/account',headers=auth(session=session)).status_code==401
    assert client.get('/v1/profile',headers=headers).status_code==401
    assert client.get('/v1/profile',headers=auth()).status_code==200
    for h in [None,{'Authorization':'Bearer malformed'},auth(expires_at=datetime.now(timezone.utc)-timedelta(seconds=1)),auth(is_anonymous=True),{'Authorization':'Bearer '+_token(role='authenticated',session_id='not-a-uuid')}]:
        assert client.get('/v1/profile',headers=h).status_code==401
    assert headers['Authorization'].split(' ',1)[1] not in caplog.text
    response=client.patch('/v1/profile',headers=auth(),json={'expected_revision':1,'display_name':'Bearer SYNTHETIC_CANARY'})
    assert response.status_code==422 and 'SYNTHETIC_CANARY' not in response.text


def test_saved_case_report_delete_and_cross_user_denial(client):
    response=client.post('/v1/saved-cases',headers=auth(),json={'snapshot':snapshot(),'explicit_consent':True,'import_key':uuid4().hex})
    assert response.status_code==201,response.text
    case=response.json(); id=case['id']
    report=client.post('/v1/reports',headers=auth(),json={'case_id':id,'title':'saved','payload':{'unknown':None}})
    assert report.status_code==201,report.text
    rid=report.json()['id']
    for method,path,body in [('GET','/v1/reports/'+rid,None),('DELETE','/v1/reports/'+rid,None),('DELETE',f'/v1/saved-cases/{id}?expected_revision=1',None),('POST','/v1/reports',{'case_id':id,'title':'steal','payload':{}})]:
        assert client.request(method,path,headers=auth(OTHER),json=body).status_code==404
    assert client.delete(f'/v1/saved-cases/{id}?expected_revision=1',headers=auth()).status_code==204
    assert client.get('/v1/reports/'+rid,headers=auth()).status_code==404


def test_provider_password_endpoints_are_not_added(client):
    # Existing Supabase signup/login paths stay in the official SDK.
    for path in ['/v1/register','/v1/login']:
        assert client.post(path,json={'email':'test@example.invalid','password':'SYNTHETIC'}).status_code in {404,405}


def test_disabled_profile_never_uses_db(monkeypatch,verifier):
    monkeypatch.delenv('PROFESSOR_USERDB_ENABLED',raising=False)
    app.dependency_overrides[get_supabase_jwt_verifier]=lambda:verifier
    with TestClient(app) as c:
        assert c.get('/v1/profile',headers=auth()).status_code==503
    app.dependency_overrides.clear()


def test_user_data_reuses_existing_abuse_controls_only_when_enabled(monkeypatch):
    from backend.api.abuse_middleware import capability
    scope={'path':'/v1/profile','method':'PATCH'}
    assert capability(scope) is None
    monkeypatch.setenv('PROFESSOR_USERDB_ENABLED','true')
    assert capability(scope)=='metadata'


@pytest.mark.parametrize('claims',[
    {'role':'service_role'},{'role':'anon'},{'session_id':None},{'iat':True},
    {'exp':True},{'exp':10**100},{'is_anonymous':True},{'iss':'https://other.supabase.co/auth/v1'},
])
def test_stage4a_claims_fail_closed(client,claims):
    token=_token(role='authenticated',session_id=str(uuid4())) if not claims else _token(**{'role':'authenticated','session_id':str(uuid4()),**claims})
    assert client.get('/v1/profile',headers={'Authorization':'Bearer '+token}).status_code==401


def test_existing_write_origin_and_request_budget_apply(client):
    response=client.patch('/v1/profile',headers={**auth(),'Origin':'https://untrusted.invalid'},json={'expected_revision':1,'display_name':'deny'})
    assert response.status_code==403
    # Existing controls are server-selected before JWKS/database work.
    from services import anti_abuse
    from services.anti_abuse import Policy
    controls=anti_abuse.AbuseControls({'metadata':Policy(1,60,1,10)})
    original=anti_abuse.CONTROLS
    anti_abuse.CONTROLS=controls
    try:
        assert client.get('/v1/profile',headers=auth()).status_code==200
        assert client.get('/v1/profile',headers=auth()).status_code==429
    finally:anti_abuse.CONTROLS=original
