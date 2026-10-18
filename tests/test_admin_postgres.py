"""Real PostgreSQL 17 proofs using an explicitly disposable loopback database."""
import os
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from urllib.parse import urlsplit
from uuid import UUID, uuid4

import pytest

from scripts.disposable_postgres_auth import bootstrap_disposable_supabase_auth
from scripts.validate_postgres_migration import _statements
from services.admin.commands import AccountCommand, QuotaCommand
from services.admin.store import AdminStore
from services.vnext.auth import AuthenticatedPrincipal
from services.vnext.errors import VNextError

A, B, C = (
    UUID('11111111-1111-4111-8111-111111111111'),
    UUID('22222222-2222-4222-8222-222222222222'),
    UUID('33333333-3333-4333-8333-333333333333'))


@pytest.fixture(scope='module')
def database():
    url = os.getenv('ADMIN_TEST_POSTGRES_URL', '')
    if not url or os.getenv('ADMIN_TEST_DISPOSABLE') != '1':
        pytest.skip('Explicit disposable Admin PostgreSQL not configured')
    parsed = urlsplit(url)
    assert parsed.hostname in {'127.0.0.1','localhost'}
    assert parsed.path.lstrip('/').startswith('admin_control_test')
    import psycopg
    with psycopg.connect(url) as conn:
        assert conn.execute('SHOW server_version_num').fetchone()[0].startswith('17')
        for schema in ('admin_plane','api_usage','vnext_private','vnext_core','auth'):
            conn.execute(f'DROP SCHEMA IF EXISTS {schema} CASCADE')
        bootstrap_disposable_supabase_auth(conn)
        for name in ('013_vnext_workspace_case_foundation.sql','020_consumer_account_foundation.sql',
                     '021_api_usage_quota_ledger.sql','022_admin_control_plane.sql'):
            path=Path('database/migrations',name)
            for statement in _statements(path):
                conn.execute(statement)
        if not conn.execute("SELECT 1 FROM pg_roles WHERE rolname='admin_test_login'").fetchone():
            conn.execute('CREATE ROLE admin_test_login LOGIN INHERIT NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE')
        conn.execute('GRANT proptech_admin_operator TO admin_test_login')
        conn.execute('INSERT INTO auth.users(id) VALUES (%s),(%s),(%s)', (A,B,C))
        conn.execute('INSERT INTO vnext_private.consumer_accounts(user_id) SELECT id FROM auth.users')
    runtime = parsed._replace(netloc=f'admin_test_login@{parsed.hostname}:{parsed.port}').geturl()
    return url, runtime


@pytest.fixture(autouse=True)
def accounts(database):
    import psycopg
    with psycopg.connect(database[0]) as conn:
        conn.execute("UPDATE vnext_private.consumer_accounts SET status='active',platform_role=CASE WHEN user_id=%s THEN 'consumer' ELSE 'platform_admin' END", (C,))


def principal(actor=A):
    return AuthenticatedPrincipal(actor, str(actor), 'fixture')


def command(field='status', value='suspended', key=None, reason='Security investigation'):
    return AccountCommand(command_id=key or uuid4(),reason=reason,field=field,value=value)


@pytest.mark.parametrize('drift', [
    'inherited_admin_executor', 'set_only_admin_executor', 'hidden_owner_session',
    'request_createrole', 'request_database_owner', 'request_schema_create', 'request_schema_owner',
])
def test_consumer_context_rejects_admin_authority_drift(database, drift):
    """022's stronger SQL grants must never leak through the consumer credential."""
    import psycopg
    from psycopg import sql
    from psycopg.conninfo import make_conninfo
    from services.vnext.db_principal import DatabasePrincipalContext, DatabasePrincipalContextError

    with psycopg.connect(database[0]) as setup:
        if drift.endswith('admin_executor'):
            inherit = 'TRUE' if drift.startswith('inherited') else 'FALSE'
            setup.execute('GRANT proptech_admin_executor TO vnext_api WITH INHERIT ' + inherit + ', SET TRUE')
        elif drift == 'request_createrole':
            setup.execute('ALTER ROLE vnext_api CREATEROLE')
        elif drift == 'request_database_owner':
            setup.execute(sql.SQL('ALTER DATABASE {} OWNER TO vnext_api').format(sql.Identifier(setup.info.dbname)))
        elif drift.startswith('request_schema_'):
            setup.execute('CREATE SCHEMA pgx')
            if drift.endswith('owner'):
                setup.execute('ALTER SCHEMA pgx OWNER TO vnext_api')
            else:
                setup.execute('GRANT CREATE ON SCHEMA pgx TO vnext_api')
    try:
        target = database[0] if drift == 'hidden_owner_session' else make_conninfo(database[0], user='vnext_api')
        with psycopg.connect(target) as connection:
            if drift == 'hidden_owner_session':
                connection.execute('SET ROLE vnext_api')
                connection.commit()
            # Demonstrate that inherited 022 authority really permits the forbidden
            # account write, then roll it back; this is not a mocked catalog check.
            if drift == 'inherited_admin_executor':
                connection.execute("UPDATE vnext_private.consumer_accounts SET platform_role='platform_admin' WHERE user_id=%s", (C,))
                assert connection.execute('SELECT platform_role FROM vnext_private.consumer_accounts WHERE user_id=%s', (C,)).fetchone() == ('platform_admin',)
                connection.rollback()
            class Pool:
                @contextmanager
                def connection(self):
                    yield connection
            with pytest.raises(DatabasePrincipalContextError, match='database_request_role_unsafe'):
                with DatabasePrincipalContext(Pool()).transaction(principal(C)):
                    pytest.fail('Privileged consumer credential entered a request transaction')
            assert connection.execute("SELECT nullif(current_setting('request.jwt.claim.sub',true),'')").fetchone() == (None,)
    finally:
        with psycopg.connect(database[0]) as setup:
            if drift.endswith('admin_executor'):
                setup.execute('REVOKE proptech_admin_executor FROM vnext_api')
            elif drift == 'request_createrole':
                setup.execute('ALTER ROLE vnext_api NOCREATEROLE')
            elif drift == 'request_database_owner':
                setup.execute(sql.SQL('ALTER DATABASE {} OWNER TO postgres').format(sql.Identifier(setup.info.dbname)))
            elif drift.startswith('request_schema_'):
                setup.execute('DROP SCHEMA pgx')


def test_platform_admin_account_does_not_bypass_workspace_tenancy(database):
    import psycopg
    from psycopg.conninfo import make_conninfo
    from services.vnext.accounts import AccountAuthorizer, PostgresAccountRepository
    from services.vnext.authorization import PostgresWorkspaceMembershipRepository, WorkspaceAuthorizer
    from services.vnext.db_principal import DatabasePrincipalContext

    workspace = uuid4()
    with psycopg.connect(database[0]) as setup:
        setup.execute("INSERT INTO vnext_core.workspaces(workspace_id,workspace_type,display_name,created_by_user_id,personal_owner_user_id) VALUES(%s,'personal','Foreign workspace',%s,%s)", (workspace,B,B))
        setup.execute("INSERT INTO vnext_core.workspace_members(workspace_id,user_id,role,status,joined_at) VALUES(%s,%s,'owner','active',clock_timestamp())", (workspace,B))
    class Pool:
        @contextmanager
        def connection(self):
            with psycopg.connect(make_conninfo(database[0],user='vnext_api')) as connection:
                yield connection
    context = DatabasePrincipalContext(Pool())
    actor = principal()
    assert AccountAuthorizer(PostgresAccountRepository(lambda: context)).require_platform_admin(actor).platform_role == 'platform_admin'
    tenancy = WorkspaceAuthorizer(PostgresWorkspaceMembershipRepository(lambda: context))
    with pytest.raises(VNextError) as failure:
        tenancy.require_workspace_access(actor,workspace)
    assert failure.value.status_code == 403
    with context.transaction(actor) as connection:
        assert connection.execute('SELECT workspace_id FROM vnext_core.workspaces WHERE workspace_id=%s',(workspace,)).fetchall() == []
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            with connection.transaction():
                connection.execute("INSERT INTO vnext_core.cases(workspace_id,purpose,title,created_by_user_id) VALUES(%s,'buy_due_diligence','Forbidden',%s)",(workspace,A))


def test_dedicated_runtime_and_direct_dml_denials(database):
    import psycopg
    with psycopg.connect(database[1]) as conn:
        AdminStore.verify_role(conn)
        for sql in (
            "UPDATE vnext_private.consumer_accounts SET platform_role='platform_admin'",
            'DELETE FROM admin_plane.audit', 'TRUNCATE admin_plane.audit',
            "UPDATE api_usage.quota_policy SET request_hour=100000",
            "INSERT INTO admin_plane.commands VALUES (gen_random_uuid(),gen_random_uuid(),'{}','{}',now())",
            'SET ROLE proptech_admin_executor', 'SET ROLE vnext_api'):
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                with conn.transaction():
                    conn.execute(sql)
    with psycopg.connect(database[0]) as conn:
        with pytest.raises(RuntimeError):
            AdminStore.verify_role(conn)
        for role in ('vnext_api','anon','authenticated','service_role'):
            if not conn.execute('SELECT 1 FROM pg_roles WHERE rolname=%s',(role,)).fetchone():
                conn.execute(f'CREATE ROLE {role} NOLOGIN')
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                with conn.transaction():
                    conn.execute(f'SET LOCAL ROLE {role}')
                    conn.execute('SELECT admin_plane.mutate_account(%s,\'status\',\'suspended\',\'reason\',%s)', (C,uuid4()))


@pytest.mark.parametrize('role', ['pg_execute_server_program','pg_read_server_files','pg_write_server_files','pg_signal_backend'])
@pytest.mark.parametrize('grantee', ['admin_test_login','proptech_admin_executor'])
def test_predefined_powerful_memberships_are_rejected(database, role, grantee):
    import psycopg
    with psycopg.connect(database[0]) as conn:
        conn.execute(f'GRANT {role} TO {grantee}')
    try:
        with psycopg.connect(database[1]) as conn:
            with pytest.raises(RuntimeError, match='Unsafe Admin database principal'):
                AdminStore.verify_role(conn)
    finally:
        with psycopg.connect(database[0]) as conn:
            conn.execute(f'REVOKE {role} FROM {grantee}')


@pytest.mark.parametrize('field,value', [('status','suspended'),('platform_role','consumer')])
def test_self_and_final_admin_are_protected(database, field, value):
    import psycopg
    with psycopg.connect(database[0]) as conn:
        conn.execute("UPDATE vnext_private.consumer_accounts SET platform_role='consumer' WHERE user_id=%s", (B,))
    store = AdminStore(database[1])
    with pytest.raises(VNextError) as failure:
        store.command(principal(), command(field,value), A)
    assert failure.value.status_code == 403


@pytest.mark.parametrize('field,value', [('status','suspended'),('platform_role','consumer')])
def test_cross_admin_concurrency_cannot_reach_zero(database, field, value):
    import psycopg
    barrier = Barrier(2)
    def run(pair):
        actor,target=pair
        barrier.wait(timeout=5)
        try:
            AdminStore(database[1]).command(principal(actor),command(field,value),target)
            return 'ok'
        except VNextError as exc:
            return exc.status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(run,[(A,B),(B,A)]))
    assert sorted(map(str,results)) == ['403','ok']
    with psycopg.connect(database[0]) as conn:
        assert conn.execute("SELECT count(*) FROM vnext_private.consumer_accounts WHERE status='active' AND platform_role='platform_admin'").fetchone()[0] == 1


def test_concurrent_retry_is_exactly_one_audit_and_changed_payload_conflicts(database):
    import psycopg
    key=uuid4()
    cmd=command(key=key)
    with ThreadPoolExecutor(max_workers=8) as pool:
        results=list(pool.map(lambda _: AdminStore(database[1]).command(principal(),cmd,C),range(8)))
    assert all(r==results[0] for r in results)
    with pytest.raises(VNextError) as failure:
        AdminStore(database[1]).command(principal(),command(value='active',key=key),C)
    assert failure.value.code.value=='idempotency_conflict'
    with psycopg.connect(database[0]) as conn:
        assert conn.execute('SELECT count(*) FROM admin_plane.audit WHERE command_id=%s',(key,)).fetchone()[0]==1


def test_audit_insert_failure_rolls_back_mutation_and_command(database):
    import psycopg
    key=uuid4()
    with psycopg.connect(database[0]) as conn:
        conn.execute("CREATE FUNCTION admin_plane.test_fail() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'injected audit failure'; END $$")
        conn.execute('CREATE TRIGGER test_audit_failure BEFORE INSERT ON admin_plane.audit FOR EACH ROW EXECUTE FUNCTION admin_plane.test_fail()')
    try:
        with pytest.raises(VNextError) as failure:
            AdminStore(database[1]).command(principal(),command(key=key),C)
        assert failure.value.status_code == 503
        with psycopg.connect(database[0]) as conn:
            assert conn.execute('SELECT status FROM vnext_private.consumer_accounts WHERE user_id=%s',(C,)).fetchone()[0]=='active'
            assert conn.execute('SELECT count(*) FROM admin_plane.commands WHERE command_id=%s',(key,)).fetchone()[0]==0
    finally:
        with psycopg.connect(database[0]) as conn:
            conn.execute('DROP TRIGGER test_audit_failure ON admin_plane.audit')
            conn.execute('DROP FUNCTION admin_plane.test_fail()')


def test_history_immutable_even_with_accidental_dml_grants(database):
    import psycopg
    with psycopg.connect(database[0]) as conn:
        for table in ('audit','commands'):
            for verb in ('UPDATE','DELETE','TRUNCATE'):
                sql = f'{verb} admin_plane.{table} CASCADE' if verb=='TRUNCATE' else f'{verb} FROM admin_plane.{table}' if verb=='DELETE' else f'UPDATE admin_plane.{table} SET actor=actor'
                with pytest.raises(psycopg.errors.InsufficientPrivilege):
                    with conn.transaction():
                        conn.execute(sql)


def test_revoked_actor_cannot_replay_or_read_and_quota_update_is_audited(database):
    import psycopg
    store=AdminStore(database[1]); key=uuid4()
    cmd=QuotaCommand(command_id=key,reason='Adjust abuse envelope',principal_class='authenticated',request_hour=5,operation_hour=3,operation_day=9)
    first=store.command(principal(),cmd)
    assert store.command(principal(),cmd)==first
    assert next(p for p in store.policies(principal()) if p['principal_class']=='authenticated')['request_hour']==5
    with psycopg.connect(database[0]) as conn:
        assert conn.execute('SELECT count(*) FROM admin_plane.audit WHERE command_id=%s',(key,)).fetchone()[0]==1
        conn.execute("UPDATE vnext_private.consumer_accounts SET status='suspended' WHERE user_id=%s", (A,))
    with pytest.raises(VNextError): store.command(principal(),cmd)
    with pytest.raises(VNextError): store.account(principal(),C)


def test_directory_exact_lookup_and_audit_cursor(database):
    from services.admin.durable import DurableAdminSummarySource
    from services.admin.summaries import LocalAdminSummarySource
    store=AdminStore(database[1])
    assert store.account(principal(),C)['platform_role']=='consumer'
    source=DurableAdminSummarySource(principal(),store,LocalAdminSummarySource())
    assert len(source.read('users').users)==3
    assert source.read('usage').state=='partial'
    with pytest.raises(VNextError): source.read('users','invalid')
    with store.transaction(principal()) as conn:
        for _ in range(52):
            conn.execute("SELECT admin_plane.mutate_account(%s,'status','active','pagination fixture',%s)", (C,uuid4()))
    first=source.read('audit'); second=source.read('audit',first.next_cursor)
    assert len(first.audit)==50 and second.audit
    assert not {r.command_id for r in first.audit} & {r.command_id for r in second.audit}


def test_populated_usage_and_quota_are_renderable_strict_counts(database):
    import psycopg
    from services.api_usage import UsageAggregator
    from services.usage_ledger import PostgresUsageStore
    from services.admin.durable import DurableAdminSummarySource
    from services.admin.summaries import LocalAdminSummarySource
    usage=UsageAggregator()
    usage.observe(capability='places',provider='google_places',event='physical_calls',count=2)
    PostgresUsageStore(database[0]).write_batch(uuid4(),usage.take_pending())
    with psycopg.connect(database[0]) as conn:
        conn.execute("INSERT INTO api_usage.quota_hourly(bucket_start,subject,capability,admitted,rejected,reservations) VALUES(date_trunc('hour',now()),%s,'places',2,1,3)", ('user:'+str(C),))
    result=DurableAdminSummarySource(principal(),AdminStore(database[1]),LocalAdminSummarySource()).read('usage')
    row=next(r for r in result.usage if r.capability=='places')
    assert (row.provider_attempts,row.admitted,row.rejected,row.quota_consumed)==(2,2,1,3)
    assert row.cost.state=='unknown'
    with psycopg.connect(database[0]) as conn:
        conn.execute("UPDATE api_usage.hourly SET provider_accounting_unknown=1 WHERE capability='places'")
        conn.execute("INSERT INTO api_usage.quota_hourly(bucket_start,subject,capability,admitted,rejected,reservations) VALUES(date_trunc('hour',now()),%s,'routes',4,0,1)", ('user:'+str(C),))
    result=DurableAdminSummarySource(principal(),AdminStore(database[1]),LocalAdminSummarySource()).read('usage')
    assert next(r for r in result.usage if r.capability=='places').provider_attempts is None
    quota_only=next(r for r in result.usage if r.capability=='routes')
    assert quota_only.requests is None and quota_only.admitted==4
    from fastapi.testclient import TestClient
    from backend.api_main import app
    from services.admin.store import get_admin_store
    from services.vnext.auth import require_authenticated_principal
    from tests.test_admin_commands import authority
    read_errors=[]
    class CapturingStore(AdminStore):
        @contextmanager
        def transaction(self, value):
            try:
                with super().transaction(value) as connection:
                    yield connection
            except VNextError as exc:
                context=exc.__context__
                read_errors.append((type(context).__name__,getattr(context,'sqlstate',None)))
                raise
    app.dependency_overrides[require_authenticated_principal]=lambda: principal()
    app.dependency_overrides[get_admin_store]=lambda: CapturingStore(database[1])
    authority(role='platform_admin')
    try:
        with TestClient(app) as client:
            response=client.get('/v1/admin/usage')
        assert response.status_code==200, read_errors
        assert response.json()['state']=='partial'
    finally:
        app.dependency_overrides.clear()


def test_revocation_is_rechecked_after_a_proven_advisory_lock_wait(database):
    import time
    import psycopg
    key=uuid4()
    with psycopg.connect(database[0]) as owner, psycopg.connect(database[1]) as runtime:
        AdminStore.verify_role(runtime)
        runtime.execute("SET LOCAL statement_timeout='15000ms'")
        runtime.execute("SELECT set_config('request.jwt.claim.sub',%s,true)",(str(A),))
        assert runtime.execute('SELECT admin_plane.is_admin()').fetchone()[0] is True
        owner.execute('SELECT pg_advisory_xact_lock(832,1)')
        with ThreadPoolExecutor(max_workers=1) as pool:
            future=pool.submit(runtime.execute,"SELECT admin_plane.mutate_account(%s,'status','suspended','revocation test',%s)",(C,key))
            deadline=time.monotonic()+10
            while not owner.execute("SELECT EXISTS(SELECT 1 FROM pg_locks WHERE pid=%s AND locktype='advisory' AND NOT granted)",(runtime.info.backend_pid,)).fetchone()[0]:
                assert time.monotonic()<deadline, 'Command never reached the lock wait'
                time.sleep(.01)
            owner.execute("UPDATE vnext_private.consumer_accounts SET platform_role='consumer' WHERE user_id=%s",(A,))
            owner.commit()
            with pytest.raises(psycopg.errors.InsufficientPrivilege): future.result(timeout=15)
        runtime.rollback()
        assert owner.execute('SELECT status FROM vnext_private.consumer_accounts WHERE user_id=%s',(C,)).fetchone()[0]=='active'
        assert owner.execute('SELECT count(*) FROM admin_plane.commands WHERE command_id=%s',(key,)).fetchone()[0]==0


def test_idempotency_namespace_is_shared_across_account_and_quota_commands(database):
    store=AdminStore(database[1])
    def quota(key):
        return QuotaCommand(command_id=key,reason='Policy review',principal_class='anonymous',request_hour=100,operation_hour=30,operation_day=80)
    account_key,quota_key=uuid4(),uuid4()
    store.command(principal(),command(value='active',key=account_key),C)
    store.command(principal(),quota(quota_key))
    for cmd,target in ((quota(account_key),None),(command(value='active',key=quota_key),C)):
        with pytest.raises(VNextError) as failure: store.command(principal(),cmd,target)
        assert failure.value.status_code==409


def test_configured_dedicated_usage_never_silently_reads_a_shadow_policy(database, monkeypatch):
    from psycopg.conninfo import make_conninfo
    usage_url = make_conninfo(database[0], dbname='api_usage_test_admin')
    assert AdminStore.target(usage_url) != AdminStore.target(database[0])
    monkeypatch.setenv('API_USAGE_DATABASE_URL', usage_url)
    monkeypatch.delenv('ADMIN_USAGE_DATABASE_URL',raising=False)
    with pytest.raises(VNextError) as failure:
        AdminStore(database[1]).policies(principal())
    assert failure.value.status_code==503


@pytest.mark.parametrize('drift',['runtime_function','executor_function','runtime_create','executor_create',
                                 'runtime_pgx_create','executor_pgx_create',
                                 'runtime_pgx_owner','executor_pgx_owner'])
def test_function_ownership_and_schema_create_drift_are_rejected(database, drift):
    import psycopg
    with psycopg.connect(database[0]) as conn:
        if drift.endswith('function'):
            conn.execute('CREATE FUNCTION admin_plane.test_drift() RETURNS integer LANGUAGE sql AS $$ SELECT 1 $$')
            owner='admin_test_login' if drift.startswith('runtime') else 'proptech_admin_executor'
            conn.execute(f'ALTER FUNCTION admin_plane.test_drift() OWNER TO {owner}')
        else:
            owner='admin_test_login' if drift.startswith('runtime') else 'proptech_admin_executor'
            schema='pgx' if '_pgx_' in drift else 'public'
            if schema == 'pgx':
                conn.execute('CREATE SCHEMA pgx')
            if drift.endswith('_owner'):
                conn.execute(f'ALTER SCHEMA {schema} OWNER TO {owner}')
            else:
                conn.execute(f'GRANT CREATE ON SCHEMA {schema} TO {owner}')
    try:
        with psycopg.connect(database[1]) as conn:
            with pytest.raises(RuntimeError,match='Unsafe Admin database principal'):
                AdminStore.verify_role(conn)
    finally:
        with psycopg.connect(database[0]) as conn:
            if drift.endswith('function'):
                conn.execute('DROP FUNCTION admin_plane.test_drift()')
            else:
                conn.execute(f'REVOKE CREATE ON SCHEMA {schema} FROM {owner}')
                if schema == 'pgx':
                    conn.execute('DROP SCHEMA pgx')
