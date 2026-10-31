"""Stage 4A real PostgreSQL proof; private disposable Unix socket, never live DB."""
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from uuid import UUID, uuid4

import pytest

ROOT = Path(__file__).resolve().parents[1]
ISSUER = 'https://fixture-project.supabase.co/auth/v1'
USER = UUID('11111111-1111-4111-8111-111111111111')
OTHER = UUID('22222222-2222-4222-8222-222222222222')


@pytest.fixture(scope='session')
def pg(tmp_path_factory):
    import psycopg
    binary = Path('/tmp/proptech-pg18-package/usr/lib/postgresql/18/bin')
    if not (binary/'initdb').is_file():
        pytest.skip('requires local PostgreSQL test binaries')
    parent = Path.home()/'.cache/proptech-stage4a-tests'
    parent.mkdir(mode=0o700,parents=True,exist_ok=True)
    generated = tempfile.TemporaryDirectory(prefix='pg-',dir=parent)
    root = Path(generated.name)
    root.chmod(0o700)
    data = root/'data'
    sock = root/'socket'; sock.mkdir(mode=0o700)
    def run(args):
        result = subprocess.run(args, capture_output=True, text=True, timeout=45,
            env={**os.environ, 'LD_LIBRARY_PATH':str(binary.parents[3]/'lib/x86_64-linux-gnu')})
        assert result.returncode == 0, result.stderr[-2500:]
    run([str(binary/'initdb'), '-D', str(data), '-A', 'trust', '--no-locale', '-E', 'UTF8'])
    run([str(binary/'pg_ctl'), '-D', str(data), '-l', str(root/'server.log'), '-o',
         f"-k {sock} -c listen_addresses='' -c shared_buffers=16MB -c max_connections=12", '-w', 'start'])
    try:
        with psycopg.connect(host=str(sock), dbname='postgres', autocommit=True) as c:
            c.execute('CREATE DATABASE stage4a_userdb_test')
        with psycopg.connect(host=str(sock), dbname='stage4a_userdb_test', autocommit=True) as c:
            c.execute('REVOKE CREATE ON SCHEMA public FROM PUBLIC')
            c.execute('CREATE ROLE professor_user_runtime LOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE NOREPLICATION')
            c.execute((ROOT/'database/userdb/001_professor_users.sql').read_text())
            c.execute('INSERT INTO professor_user.configuration(issuer,authority_reviewed) VALUES (%s,true)', (ISSUER,))
        yield str(sock)
    finally:
        run([str(binary/'pg_ctl'), '-D', str(data), '-m', 'fast', '-w', 'stop'])
        generated.cleanup()


@pytest.fixture
def repo(pg):
    import psycopg
    from services.professor_userdb import UserRepository
    from services.vnext.db_principal import DatabasePrincipalContext
    class Pool:
        @contextmanager
        def connection(self):
            with psycopg.connect(host=pg, dbname='stage4a_userdb_test', user='professor_user_runtime') as c:
                yield c
    return UserRepository(DatabasePrincipalContext(Pool(), expected_role='professor_user_runtime'))


def principal(user=USER, session=None):
    from services.vnext.auth import AuthenticatedPrincipal
    return AuthenticatedPrincipal(user, str(user), ISSUER, datetime.now(timezone.utc),
                                  session_id=session or uuid4(), token_expires_at=datetime.now(timezone.utc)+timedelta(minutes=5))


def test_schema_exists_and_forces_rls(pg):
    import psycopg
    with psycopg.connect(host=pg, dbname='stage4a_userdb_test') as c:
        rows = c.execute("SELECT relname, relrowsecurity, relforcerowsecurity FROM pg_class JOIN pg_namespace n ON n.oid=relnamespace WHERE n.nspname='professor_user' AND relkind='r' AND relname<>'configuration'").fetchall()
        assert len(rows) == 8
        assert all(a and b for _,a,b in rows)
        assert c.execute("SELECT count(*) FROM pg_class WHERE relname='real_price_transactions'").fetchone()[0] == 0


def test_accounts_profiles_preferences_and_cross_user_rls(repo):
    p = principal(); other = principal(OTHER)
    repo.admit(p); repo.admit(other)
    assert repo.get_account(principal=p).user_id == USER
    profile = repo.profile(p)
    assert profile['user_id'] == USER
    changed = repo.update_profile(p, profile['revision'], {'display_name': 'Professor'})
    assert changed['revision'] == profile['revision']+1
    from services.vnext.errors import VNextError
    with pytest.raises(VNextError) as e:
        repo.update_profile(p, profile['revision'], {'display_name': 'stale'})
    assert e.value.code.value == 'version_conflict'
    assert repo.profile(other)['display_name'] == ''
    with repo.context.transaction(p) as c:
        assert c.execute('SELECT id FROM professor_user.users WHERE id=%s', (OTHER,)).fetchall() == []
        assert c.execute('UPDATE professor_user.profiles SET display_name=%s WHERE user_id=%s', ('steal', OTHER)).rowcount == 0
        with pytest.raises(Exception):
            with c.transaction():
                c.execute("UPDATE professor_user.users SET platform_role='platform_admin'")
    prefs = repo.preferences(p)
    assert repo.update_preferences(p, prefs['revision'], {'version':1, 'compare_ids':[]})['data']['version'] == 1


def test_session_revocation_refresh_and_wrong_issuer_fail_closed(repo):
    from dataclasses import replace
    from services.vnext.errors import VNextError
    p = principal(); repo.admit(p)
    repo.logout(p)
    with pytest.raises(VNextError) as e:
        repo.admit(replace(p, token_issued_at=datetime.now(timezone.utc)))
    assert e.value.code.value == 'authentication_required'
    with pytest.raises(VNextError):
        repo.admit(replace(principal(), issuer='https://other.supabase.co/auth/v1'))
    with pytest.raises(VNextError):
        repo.admit(replace(principal(), session_id=None))
    repo.admit(principal())  # another device/session remains valid


def test_cases_survive_new_repository_and_deny_other_user(repo):
    from services.professor_userdb import PrivateCaseService, PostgresCaseRepository
    from services.vnext.durable_cases import CreateCase, MetadataUpdate, MembershipUpdate
    from services.vnext.errors import VNextError
    from tests.durable_case_fixtures import snapshot
    p = principal(); other = principal(OTHER); repo.admit(p); repo.admit(other)
    service = PrivateCaseService(PostgresCaseRepository(repo))
    body = CreateCase(snapshot=snapshot(), import_key=uuid4().hex, explicit_consent=True)
    key = uuid4().hex
    row = service.create(p, body, idempotency_key=key)
    assert service.create(p, body, idempotency_key=key).id == row.id
    assert service.create(p, body, idempotency_key=uuid4().hex).id == row.id
    fresh = PrivateCaseService(PostgresCaseRepository(repo))
    assert fresh.open(p, row.id).snapshot == body.snapshot
    assert service.list(other, scope='owned', offset=0, limit=100) == []
    for call in [lambda:service.open(other,row.id), lambda:service.metadata(other,row.id,MetadataUpdate(expected_revision=1,title='steal'),idempotency_key=uuid4().hex), lambda:service.delete(other,row.id,1)]:
        with pytest.raises(VNextError) as e: call()
        assert e.value.status_code == 404
    with pytest.raises(VNextError) as e:
        service.membership(p,row.id,MembershipUpdate(expected_revision=1,member_id=OTHER,role='viewer'),idempotency_key=uuid4().hex)
    assert e.value.code.value == 'unsupported_input'
    updated = service.metadata(p,row.id,MetadataUpdate(expected_revision=1,title='saved'),idempotency_key=uuid4().hex)
    assert updated.revision == 2
    with pytest.raises(VNextError): service.delete(p,row.id,1)
    report = repo.create_report(p,row.id,'Report',{'unknown':None})
    assert repo.report(p,report['id'])['payload'] == {'unknown':None}
    with pytest.raises(VNextError): repo.report(other,report['id'])
    with pytest.raises(VNextError): repo.create_report(other,row.id,'steal',{})
    service.delete(p,row.id,2)
    for call in [lambda:service.open(p,row.id),lambda:service.create(p,body,idempotency_key=key),lambda:service.create(p,body,idempotency_key=uuid4().hex),lambda:repo.report(p,report['id'])]:
        with pytest.raises(VNextError):call()


def test_suspension_blocks_sql_and_cannot_be_reset(repo, pg):
    import psycopg
    from services.vnext.errors import VNextError
    p = principal(uuid4()); repo.admit(p)
    with psycopg.connect(host=pg, dbname='stage4a_userdb_test') as c:
        c.execute("UPDATE professor_user.users SET status='suspended' WHERE id=%s", (p.user_id,))
    assert repo.get_account(principal=p).status == 'suspended'
    with pytest.raises(VNextError): repo.profile(p)
    with repo.context.transaction(p) as c:
        assert c.execute('SELECT * FROM professor_user.profiles').fetchall() == []
        with pytest.raises(Exception):
            with c.transaction():
                c.execute('INSERT INTO professor_user.profiles(user_id) VALUES (%s)',(p.user_id,))


def test_foreign_owner_insert_reassignment_and_role_escalation_denied(repo):
    import psycopg
    p=principal(uuid4()); other=principal(uuid4());repo.admit(p);repo.admit(other)
    repo.profile(p)
    with repo.context.transaction(p) as c:
        for query,values in [
            ('INSERT INTO professor_user.profiles(user_id) VALUES (%s)',(other.user_id,)),
            ('UPDATE professor_user.profiles SET user_id=%s WHERE user_id=%s',(other.user_id,p.user_id)),
            ("INSERT INTO professor_user.users(id,issuer,status) VALUES (%s,%s,'active')",(uuid4(),ISSUER)),
            ("UPDATE professor_user.configuration SET authority_reviewed=true",()),
            ('DELETE FROM professor_user.users WHERE id=%s',(p.user_id,)),
        ]:
            with pytest.raises(psycopg.Error):
                with c.transaction():c.execute(query,values)


def test_concurrent_retry_and_compare_and_swap_commit_once(repo):
    from concurrent.futures import ThreadPoolExecutor
    from services.professor_userdb import PrivateCaseService,PostgresCaseRepository
    from services.vnext.durable_cases import CreateCase,MetadataUpdate
    from services.vnext.errors import VNextError
    from tests.durable_case_fixtures import snapshot
    p=principal(uuid4());repo.admit(p)
    service=PrivateCaseService(PostgresCaseRepository(repo))
    body=CreateCase(snapshot=snapshot(),import_key=uuid4().hex,explicit_consent=True)
    key=uuid4().hex
    with ThreadPoolExecutor(max_workers=2) as pool:
        rows=list(pool.map(lambda _:service.create(p,body,idempotency_key=key),range(2)))
    assert rows[0].id==rows[1].id
    def update(_):
        try:
            return service.metadata(p,rows[0].id,MetadataUpdate(expected_revision=1,title='CAS'),idempotency_key=uuid4().hex).revision
        except VNextError as error:return error.code.value
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(update,range(2)))
    assert sorted(map(str,results))==['2','version_conflict']
    assert len(service.activity(p,rows[0].id,offset=0,limit=20))==2


def test_revoke_after_admission_stops_existing_request_and_expiry(repo):
    from dataclasses import replace
    from services.vnext.errors import VNextError
    p=principal(uuid4());repo.admit(p)
    repo.logout(p)
    with pytest.raises(VNextError) as e:repo.profile(p)
    assert e.value.status_code==401
    fresh=principal(uuid4());repo.admit(fresh)
    with pytest.raises(VNextError):repo.profile(replace(fresh,token_expires_at=datetime.now(timezone.utc)-timedelta(seconds=1)))


def test_startup_requires_pinned_issuer_review_and_rls(repo,monkeypatch,pg):
    import psycopg
    from services.professor_userdb import validate_configuration
    from services.vnext.errors import VNextError
    class Verifier: issuer=ISSUER
    monkeypatch.setattr('services.professor_userdb.get_repository',lambda:repo)
    monkeypatch.setattr('services.vnext.auth.get_supabase_jwt_verifier',lambda:Verifier())
    validate_configuration()
    with psycopg.connect(host=pg,dbname='stage4a_userdb_test') as c:
        c.execute('UPDATE professor_user.configuration SET authority_reviewed=false')
    try:
        with pytest.raises(VNextError):validate_configuration()
    finally:
        with psycopg.connect(host=pg,dbname='stage4a_userdb_test') as c:
            c.execute('UPDATE professor_user.configuration SET authority_reviewed=true')


def test_startup_rejects_runtime_extra_write_privilege(repo,monkeypatch,pg):
    import psycopg
    from services.professor_userdb import validate_configuration
    from services.vnext.errors import VNextError
    class Verifier: issuer=ISSUER
    monkeypatch.setattr('services.professor_userdb.get_repository',lambda:repo)
    monkeypatch.setattr('services.vnext.auth.get_supabase_jwt_verifier',lambda:Verifier())
    with psycopg.connect(host=pg,dbname='stage4a_userdb_test') as c:
        c.execute('GRANT UPDATE(status) ON professor_user.users TO professor_user_runtime')
    try:
        with pytest.raises(VNextError):validate_configuration()
    finally:
        with psycopg.connect(host=pg,dbname='stage4a_userdb_test') as c:
            c.execute('REVOKE UPDATE(status) ON professor_user.users FROM professor_user_runtime')


@pytest.mark.parametrize('grant,revoke',[
 ('GRANT DELETE ON professor_user.revoked_sessions TO professor_user_runtime','REVOKE DELETE ON professor_user.revoked_sessions FROM professor_user_runtime'),
 ('GRANT UPDATE ON professor_user.revoked_sessions TO professor_user_runtime','REVOKE UPDATE ON professor_user.revoked_sessions FROM professor_user_runtime'),
 ('GRANT DELETE ON professor_user.saved_cases TO professor_user_runtime','REVOKE DELETE ON professor_user.saved_cases FROM professor_user_runtime'),
 ('GRANT UPDATE(expires_at) ON professor_user.case_commands TO professor_user_runtime','REVOKE UPDATE(expires_at) ON professor_user.case_commands FROM professor_user_runtime'),
 ('GRANT TRUNCATE ON professor_user.saved_cases TO professor_user_runtime','REVOKE TRUNCATE ON professor_user.saved_cases FROM professor_user_runtime'),
])
def test_startup_rejects_token_tombstone_receipt_grant_drift(repo,pg,monkeypatch,grant,revoke):
    import psycopg
    from services.professor_userdb import validate_configuration
    from services.vnext.errors import VNextError
    class Verifier: issuer=ISSUER
    monkeypatch.setattr('services.professor_userdb.get_repository',lambda:repo)
    monkeypatch.setattr('services.vnext.auth.get_supabase_jwt_verifier',lambda:Verifier())
    with psycopg.connect(host=pg,dbname='stage4a_userdb_test') as c:c.execute(grant)
    try:
        with pytest.raises(VNextError):validate_configuration()
    finally:
        with psycopg.connect(host=pg,dbname='stage4a_userdb_test') as c:c.execute(revoke)


def test_startup_rejects_foreign_column_grants_and_callable_definer(repo,pg,monkeypatch):
    import psycopg
    from services.professor_userdb import validate_configuration
    from services.vnext.errors import VNextError
    class Verifier: issuer=ISSUER
    monkeypatch.setattr('services.professor_userdb.get_repository',lambda:repo)
    monkeypatch.setattr('services.vnext.auth.get_supabase_jwt_verifier',lambda:Verifier())
    with psycopg.connect(host=pg,dbname='stage4a_userdb_test') as c:
        c.execute('CREATE TABLE public.stage4a_other_authority(status text)')
        c.execute('GRANT UPDATE(status) ON public.stage4a_other_authority TO professor_user_runtime')
    try:
        with pytest.raises(VNextError):validate_configuration()
    finally:
        with psycopg.connect(host=pg,dbname='stage4a_userdb_test') as c:
            c.execute('REVOKE UPDATE(status) ON public.stage4a_other_authority FROM professor_user_runtime')
    validate_configuration()
    with psycopg.connect(host=pg,dbname='stage4a_userdb_test') as c:
        c.execute("CREATE FUNCTION public.stage4a_definer_fixture() RETURNS int LANGUAGE sql SECURITY DEFINER SET search_path='' AS 'SELECT 1'")
    try:
        with pytest.raises(VNextError):validate_configuration()
    finally:
        with psycopg.connect(host=pg,dbname='stage4a_userdb_test') as c:
            c.execute('REVOKE EXECUTE ON FUNCTION public.stage4a_definer_fixture() FROM PUBLIC')
    validate_configuration()


def test_saved_data_survives_logout_new_session_and_fresh_connections(repo):
    from services.professor_userdb import PrivateCaseService,PostgresCaseRepository
    from services.vnext.durable_cases import CreateCase
    from tests.durable_case_fixtures import snapshot
    p=principal(uuid4());other=principal(uuid4());repo.admit(p);repo.admit(other)
    service=PrivateCaseService(PostgresCaseRepository(repo))
    body=CreateCase(snapshot=snapshot(),import_key=uuid4().hex,explicit_consent=True)
    case=service.create(p,body,idempotency_key=uuid4().hex)
    report=repo.create_report(p,case.id,'retained',{'unknown':None})
    prefs=repo.preferences(p);repo.update_preferences(p,prefs['revision'],{'saved':True})
    repo.logout(p)
    login=principal(p.user_id);repo.admit(login)
    assert PrivateCaseService(PostgresCaseRepository(repo)).open(login,case.id).snapshot==body.snapshot
    assert repo.preferences(login)['data']=={'saved':True}
    assert repo.report(login,report['id'])['case_id']==case.id
    with repo.context.transaction(other) as c:
        assert c.execute('SELECT id FROM professor_user.saved_cases WHERE id=%s',(case.id,)).fetchall()==[]
        assert c.execute('UPDATE professor_user.saved_cases SET notes=%s WHERE id=%s',('steal',case.id)).rowcount==0
        assert c.execute('SELECT id FROM professor_user.reports WHERE id=%s',(report['id'],)).fetchall()==[]
