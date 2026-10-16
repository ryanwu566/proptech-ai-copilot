"""Two real PG17 databases: durable acceptance, remote audit, and recovery."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import time
from uuid import uuid4

import pytest

from scripts.disposable_postgres_auth import bootstrap_disposable_supabase_auth
from scripts.validate_postgres_migration import _statements
from services.admin.commands import QuotaCommand
from services.admin.store import AdminStore
from services.vnext.errors import VNextError
from tests.test_admin_postgres import A, B, C, command, database, principal


@pytest.fixture(scope='module')
def split(database):
    import psycopg
    from psycopg import sql
    from psycopg.conninfo import make_conninfo
    names = ('admin_control_test_accounts', 'admin_control_test_usage')
    urls = [make_conninfo(database[0], dbname=n) for n in names]
    with psycopg.connect(database[0], autocommit=True) as conn:
        for name in names:
            conn.execute(sql.SQL('DROP DATABASE IF EXISTS {} WITH (FORCE)').format(sql.Identifier(name)))
            conn.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(name)))
        if not conn.execute("SELECT 1 FROM pg_roles WHERE rolname='admin_migration_test'").fetchone():
            conn.execute('CREATE ROLE admin_migration_test NOLOGIN CREATEROLE NOINHERIT NOSUPERUSER NOBYPASSRLS NOCREATEDB')
        conn.execute('GRANT proptech_admin_executor TO admin_migration_test WITH ADMIN TRUE, INHERIT FALSE, SET FALSE')
        conn.execute('GRANT proptech_admin_operator TO admin_migration_test WITH ADMIN TRUE, INHERIT FALSE, SET FALSE')
        for name in names:
            conn.execute(sql.SQL('GRANT CREATE ON DATABASE {} TO admin_migration_test').format(sql.Identifier(name)))
    for index, url in enumerate(urls):
        with psycopg.connect(url) as conn:
            if index == 0:
                bootstrap_disposable_supabase_auth(conn)
                foundations = ('013_vnext_workspace_case_foundation.sql', '020_consumer_account_foundation.sql')
            else:
                foundations = ('021_api_usage_quota_ledger.sql',)
            for name in foundations:
                conn.execute(Path('database/migrations', name).read_text(encoding='utf-8'))
            # Ordinary CREATEROLE source-table owner, never a runtime credential.
            schemas = ('vnext_private',) if index == 0 else ('api_usage',)
            for schema in schemas:
                rows = conn.execute('SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname=%s AND c.relkind=\'r\'', (schema,)).fetchall()
                for (table,) in rows:
                    conn.execute(sql.SQL('ALTER TABLE {}.{} OWNER TO admin_migration_test').format(sql.Identifier(schema),sql.Identifier(table)))
                conn.execute(sql.SQL('ALTER SCHEMA {} OWNER TO admin_migration_test').format(sql.Identifier(schema)))
            conn.execute('SET LOCAL ROLE admin_migration_test')
            for statement in _statements(Path('database/migrations/022_admin_control_plane.sql')):
                conn.execute(statement)
            assert not conn.execute("SELECT pg_has_role(current_user,'proptech_admin_executor','SET')").fetchone()[0]
            assert not conn.execute("SELECT has_schema_privilege('proptech_admin_executor','admin_plane','CREATE')").fetchone()[0]
        with psycopg.connect(url) as conn:
            if index == 0:
                conn.execute('INSERT INTO auth.users(id) VALUES(%s),(%s),(%s)', (A,B,C))
                conn.execute("INSERT INTO vnext_private.consumer_accounts(user_id,platform_role) VALUES(%s,'platform_admin'),(%s,'platform_admin'),(%s,'consumer')", (A,B,C))
            else:
                assert conn.execute("SELECT to_regnamespace('auth'),to_regnamespace('vnext_private')").fetchone() == (None,None)
                if not conn.execute("SELECT 1 FROM pg_roles WHERE rolname='admin_usage_guard_test'").fetchone():
                    conn.execute('CREATE ROLE admin_usage_guard_test LOGIN INHERIT NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE')
                conn.execute('GRANT proptech_usage_guard TO admin_usage_guard_test')
    runtime = [make_conninfo(url, user='admin_test_login') for url in urls]
    return urls, runtime


def quota(key=None, reason='Dedicated usage policy review'):
    return QuotaCommand(command_id=key or uuid4(),reason=reason,principal_class='authenticated',request_hour=17,operation_hour=9,operation_day=23)


def test_effective_libpq_targets_include_query_overrides():
    assert AdminStore.target('postgresql://a@host/db?dbname=other&port=5555') == ('host','','5555','other')
    assert AdminStore.target('postgresql://a@host/db') == AdminStore.target('postgresql://b@host/db')
    assert AdminStore.target('postgresql://a@host/db?host=elsewhere') != AdminStore.target('postgresql://a@host/db')


def test_libpq_environment_defaults_are_bound_or_refused(monkeypatch):
    monkeypatch.setenv('PGPORT','5555')
    monkeypatch.setenv('PGHOSTADDR','127.0.0.2')
    assert AdminStore.target('postgresql://a@host/db') == ('host','127.0.0.2','5555','db')
    for query in ('port=', 'hostaddr=', 'port=&hostaddr='):
        with pytest.raises(VNextError): AdminStore.target('postgresql://a@host/db?'+query)
    monkeypatch.setenv('PGSERVICE','implicit-service')
    with pytest.raises(VNextError): AdminStore.target('postgresql://a@host/db')


def test_split_authority_policy_and_atomic_usage_audit(split):
    import psycopg
    store = AdminStore(*split[1]); cmd = quota()
    result = store.command(principal(), cmd)
    assert store.command(principal(), cmd) == result
    assert store.policies(principal())[1]['request_hour'] == 17
    for index, url in enumerate(split[0]):
        with psycopg.connect(url) as conn:
            assert conn.execute('SELECT count(*) FROM admin_plane.claims WHERE command_id=%s',(cmd.command_id,)).fetchone()[0] == (1 if index == 0 else 0)
            assert conn.execute('SELECT count(*) FROM admin_plane.audit WHERE command_id=%s',(cmd.command_id,)).fetchone()[0] == (0 if index == 0 else 1)
    with pytest.raises(VNextError) as failure:
        store.command(principal(),command(value='active',key=cmd.command_id),C)
    assert failure.value.status_code == 409
    # Unchanged Wave 1B guard reads the owning policy, not a shadow account copy.
    from psycopg.conninfo import make_conninfo
    from services.usage_guard import PostgresQuotaGuard
    from services.usage_principal import UsagePrincipal
    from services.usage_quota import QuotaExceeded
    guard=PostgresQuotaGuard(make_conninfo(split[0][1],user='admin_usage_guard_test'))
    guard.check()
    subject=UsagePrincipal('user:'+str(uuid4()),'authenticated')
    for _ in range(17):
        assert guard.consume(subject,'places','request',uuid4()) == 'admitted'
    with pytest.raises(QuotaExceeded): guard.consume(subject,'places','request',uuid4())


def test_usage_failure_retains_claim_without_policy_or_audit_change(split):
    import psycopg
    store=AdminStore(*split[1]); cmd=quota(reason='Injected audit failure').model_copy(update={'request_hour':19})
    with psycopg.connect(split[0][1]) as conn:
        conn.execute("CREATE FUNCTION admin_plane.test_fail() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'audit failed'; END $$")
        conn.execute('CREATE TRIGGER test_fail BEFORE INSERT ON admin_plane.audit FOR EACH ROW EXECUTE FUNCTION admin_plane.test_fail()')
        before=conn.execute('SELECT request_hour FROM api_usage.quota_policy WHERE principal_class=\'authenticated\'').fetchone()
    try:
        with pytest.raises(VNextError) as failure: store.command(principal(),cmd)
        assert failure.value.status_code == 503
        with psycopg.connect(split[0][1]) as conn:
            assert conn.execute('SELECT request_hour FROM api_usage.quota_policy WHERE principal_class=\'authenticated\'').fetchone() == before
            assert conn.execute('SELECT count(*) FROM admin_plane.commands WHERE command_id=%s',(cmd.command_id,)).fetchone()[0] == 0
    finally:
        with psycopg.connect(split[0][1]) as conn:
            conn.execute('DROP TRIGGER test_fail ON admin_plane.audit')
            conn.execute('DROP FUNCTION admin_plane.test_fail()')
    assert store.command(principal(),cmd)['command_id'] == str(cmd.command_id)


def test_lost_acceptance_commit_ack_never_dispatches_until_retry_confirms_claim(split):
    from contextlib import contextmanager
    import psycopg
    class LostAckStore(AdminStore):
        calls=0
        @contextmanager
        def transaction(self, actor):
            self.calls+=1
            count=self.calls
            with super().transaction(actor) as conn:
                yield conn
            if count==2:
                raise VNextError.provider_unavailable()
    store=LostAckStore(*split[1]); cmd=quota(reason='Lost durable acceptance acknowledgement')
    with pytest.raises(VNextError): store.command(principal(),cmd)
    for index,url in enumerate(split[0]):
        with psycopg.connect(url) as conn:
            table='claims' if index==0 else 'commands'
            assert conn.execute(f'SELECT count(*) FROM admin_plane.{table} WHERE command_id=%s',(cmd.command_id,)).fetchone()[0] == (1 if index==0 else 0)
    assert store.command(principal(),cmd)['command_id'] == str(cmd.command_id)


def test_durable_acceptance_survives_connection_termination_and_revocation(split):
    import psycopg
    store=AdminStore(*split[1]); cmd=quota(reason='Accepted work survives coordinator loss')
    with store.usage_transaction(principal()) as usage:
        owner=store.owner(store.usage_url(),usage)
    args=(cmd.principal_class,cmd.request_hour,cmd.operation_hour,cmd.operation_day,cmd.reason,cmd.command_id)
    # Keep the accepting connection open after commit, then terminate it while
    # an independent remote mutation is proven waiting on a database lock.
    accepting=psycopg.connect(split[1][0])
    accepting.execute("SELECT set_config('request.jwt.claim.sub',%s,false)",(str(A),))
    accepting.execute('SELECT admin_plane.accept_quota(%s,%s,%s,%s,%s,%s,%s)',(owner,*args))
    accepting.commit()
    try:
        with psycopg.connect(split[0][1]) as blocker, psycopg.connect(split[1][1]) as remote:
            blocker.execute('SELECT pg_advisory_xact_lock(832,1)')
            remote.execute("SET LOCAL statement_timeout='30000ms'")
            remote.execute("SELECT set_config('request.jwt.claim.sub',%s,true)",(str(A),))
            with ThreadPoolExecutor(max_workers=1) as pool:
                future=pool.submit(remote.execute,'SELECT admin_plane.mutate_quota(%s,%s,%s,%s,%s,%s)',args)
                deadline=time.monotonic()+15
                while not blocker.execute("SELECT EXISTS(SELECT 1 FROM pg_locks WHERE pid=%s AND locktype='advisory' AND NOT granted)",(remote.info.backend_pid,)).fetchone()[0]:
                    assert time.monotonic()<deadline
                    time.sleep(.01)
                with psycopg.connect(split[0][0]) as killer:
                    assert killer.execute('SELECT pg_terminate_backend(%s)',(accepting.info.backend_pid,)).fetchone()[0]
                with pytest.raises(VNextError) as failure: store.command(principal(),command(value='active',key=cmd.command_id),C)
                assert failure.value.status_code == 409
                store.command(principal(B),command(),A)
                blocker.commit()
                assert future.result(timeout=30).fetchone()[0]['command_id'] == str(cmd.command_id)
            remote.commit()
        with pytest.raises(VNextError) as failure: store.command(principal(),cmd)
        assert failure.value.status_code == 403
    finally:
        accepting.close()
        with psycopg.connect(split[0][0]) as conn:
            conn.execute("UPDATE vnext_private.consumer_accounts SET status='active' WHERE user_id=%s",(A,))


def test_owning_instance_change_cannot_replay_a_reserved_command(split):
    store=AdminStore(*split[1]); cmd=quota()
    store.command(principal(),cmd)
    # Same physical DB via another hostname is deliberately a different target.
    changed=AdminStore(split[1][0], split[1][1].replace('127.0.0.1','localhost'))
    with pytest.raises(VNextError) as failure: changed.command(principal(),cmd)
    assert failure.value.status_code == 409


def test_split_audit_tie_order_and_unavailable_store_are_explicit(split):
    import psycopg
    from psycopg.conninfo import make_conninfo
    store=AdminStore(*split[1]); tie=uuid4(); keys=[uuid4(),uuid4()]
    # Deliberately equal timestamp AND event UUID in the two independent stores.
    for index,url in enumerate(split[0]):
        with psycopg.connect(url) as conn:
            conn.execute("INSERT INTO admin_plane.commands(actor,command_id,payload,result) VALUES(%s,%s,'{}','{}')",(A,keys[index]))
            conn.execute("INSERT INTO admin_plane.audit(event_id,actor,command_id,timestamp,event_type,target_type,target,reason,before_state,after_state) VALUES(%s,%s,%s,'2100-01-01','policy_changed','policy','authenticated','tie fixture','{}','{}')",(tie,A,keys[index]))
    rows,_=store.audit_page(principal(),None)
    assert [r[6] for r in rows[:2]] == keys[::-1]
    rows,_=store.audit_page(principal(),'u_'+str(tie))
    assert rows[0][6] == keys[0]
    rows,_=store.audit_page(principal(),'a_'+str(tie))
    assert not any(r[9]==tie for r in rows)
    missing=AdminStore(split[1][0],make_conninfo(split[1][1],dbname='admin_control_test_missing'))
    with pytest.raises(VNextError) as failure: missing.audit_page(principal(),None)
    assert failure.value.status_code == 503
