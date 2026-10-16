"""Real PG17 proofs; only an explicitly opted-in loopback disposable cluster."""
from pathlib import Path
import hashlib
import os
from uuid import uuid4

import pytest

ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / 'database/migrations/021_api_usage_quota_ledger.sql'
CHECKSUM = '00ed7d4b78de6d92c285ab8cd87241d1477bee2ce6e97caef6bbf6e2f43b98af'
RELEASE = '59631992e03c05ff01e67fb691710c738fcc6d1b'
ACTOR = 'usage_migration'
RUNTIME = 'proptech_usage_runtime_v1'
GRANT_ROLES = tuple('proptech_usage_' + name for name in ('executor', 'guard', 'reader', 'writer'))
BROWSER_ROLES = ('anon', 'authenticated', 'service_role', 'vnext_api', 'usage_public_probe')


@pytest.fixture
def target():
    if os.getenv('USAGE_BOOTSTRAP_DISPOSABLE') != '1':
        pytest.skip('Explicit loopback disposable usage bootstrap cluster is not configured')
    port = int(os.environ['USAGE_BOOTSTRAP_TEST_PORT'])
    assert 1024 < port < 65536
    import psycopg
    from psycopg import sql
    control = f'postgresql://postgres@127.0.0.1:{port}/usage_bootstrap_control'
    name = 'api_usage_test_bootstrap_' + uuid4().hex[:12]
    with psycopg.connect(control, autocommit=True) as setup:
        assert setup.execute("SELECT current_setting('server_version_num')::int / 10000").fetchone()[0] == 17
        setup.execute('CREATE ROLE usage_migration LOGIN CREATEROLE NOCREATEDB NOSUPERUSER NOBYPASSRLS NOREPLICATION NOINHERIT')
        for role in BROWSER_ROLES:
            setup.execute(sql.SQL('CREATE ROLE {} NOLOGIN').format(sql.Identifier(role)))
        setup.execute(sql.SQL('CREATE DATABASE {} OWNER usage_migration').format(sql.Identifier(name)))
    class Target:
        database = name
        def connect(self, role=ACTOR, **kwargs):
            return psycopg.connect(f'postgresql://{role}@127.0.0.1:{port}/{name}', **kwargs)
        @property
        def runtime_url(self):
            return f'postgresql://{RUNTIME}@127.0.0.1:{port}/{name}'
    try:
        yield Target()
    finally:
        with psycopg.connect(control, autocommit=True) as setup:
            setup.execute(sql.SQL('DROP DATABASE {} WITH (FORCE)').format(sql.Identifier(name)))
            for role in (RUNTIME, *GRANT_ROLES, *BROWSER_ROLES, ACTOR, 'usage_unsafe_parent'):
                setup.execute(sql.SQL('DROP ROLE IF EXISTS {}').format(sql.Identifier(role)))


def install(target, *, runtime=False):
    from scripts.bootstrap_usage_database import bootstrap, provision_runtime
    with target.connect() as conn:
        result = bootstrap(conn, expected_database=target.database, release_version=RELEASE)
    if runtime:
        with target.connect() as conn:
            provision_runtime(conn, expected_database=target.database)
    return result


def assert_empty(target):
    with target.connect('postgres') as conn:
        assert conn.execute("SELECT nspname FROM pg_namespace WHERE nspname IN ('api_usage','api_usage_bootstrap')").fetchall() == []
        assert conn.execute("SELECT rolname FROM pg_roles WHERE rolname LIKE 'proptech_usage_%'").fetchall() == []


def test_raw_021_fails_at_owner_transfer_and_rolls_back(target):
    import psycopg
    with pytest.raises(psycopg.errors.InsufficientPrivilege, match='must be able to SET ROLE'):
        with target.connect() as conn:
            assert conn.execute('SELECT rolsuper,rolbypassrls,rolcreatedb FROM pg_roles WHERE rolname=current_user').fetchone() == (False, False, False)
            conn.execute(MIGRATION.read_text(encoding='utf-8'))
    assert_empty(target)


def test_raw_021_with_set_membership_still_fails_missing_schema_create(target):
    import psycopg
    with pytest.raises(psycopg.errors.InsufficientPrivilege, match='permission denied for schema api_usage'):
        with target.connect() as conn:
            conn.execute("SET LOCAL createrole_self_grant = 'set'")
            conn.execute(MIGRATION.read_text(encoding='utf-8'))
    assert_empty(target)


def test_bootstrap_keeps_exact_021_and_cleans_both_transfer_seams(target):
    result = install(target)
    assert result['status'] == 'bootstrapped'
    assert result['checksum'] == CHECKSUM
    assert hashlib.sha256(MIGRATION.read_bytes().replace(b'\r\n', b'\n')).hexdigest() == CHECKSUM
    with target.connect() as conn:
        assert conn.execute("SELECT proname,pg_get_userbyid(proowner),prosecdef,proconfig FROM pg_proc WHERE pronamespace='api_usage'::regnamespace ORDER BY proname").fetchall() == [
            ('consume', 'proptech_usage_executor', True, ['search_path=""']),
            ('prune', 'proptech_usage_executor', True, ['search_path=""'])]
        assert conn.execute("SELECT rolsuper,rolbypassrls,rolcanlogin,rolcreaterole,rolcreatedb,rolreplication,rolinherit FROM pg_roles WHERE rolname='proptech_usage_executor'").fetchone() == (False,) * 7
        assert conn.execute("SELECT has_schema_privilege('proptech_usage_executor','api_usage','CREATE'),pg_has_role(current_user,'proptech_usage_executor','SET'),pg_has_role(current_user,'proptech_usage_executor','USAGE')").fetchone() == (False,) * 3
        assert conn.execute("SELECT migration_id,checksum FROM api_usage_bootstrap.history").fetchall() == [('021_api_usage_quota_ledger', CHECKSUM)]
        assert conn.execute("SELECT to_regclass('public.schema_migration_ledger')").fetchone() == (None,)
        assert conn.execute("SELECT count(*) FROM pg_class WHERE relnamespace='api_usage'::regnamespace AND relkind='r' AND relrowsecurity AND relforcerowsecurity").fetchone()[0] == 6
    with pytest.raises(__import__('psycopg').errors.InsufficientPrivilege):
        with target.connect() as conn:
            conn.execute('SET ROLE proptech_usage_executor')


def test_runtime_login_uses_only_guard_writer_without_set_role(target):
    from services.usage_guard import PostgresQuotaGuard
    from services.usage_ledger import PostgresUsageStore
    install(target, runtime=True)
    with target.connect(RUNTIME) as conn:
        assert conn.execute('SELECT current_user,session_user').fetchone() == (RUNTIME, RUNTIME)
        assert conn.execute('SELECT rolsuper,rolbypassrls,rolcreatedb,rolcreaterole,rolreplication,rolcanlogin,rolinherit FROM pg_roles WHERE rolname=current_user').fetchone() == (False,False,False,False,False,True,True)
        assert conn.execute('SELECT r.rolname,a.admin_option,a.inherit_option,a.set_option FROM pg_auth_members a JOIN pg_roles r ON r.oid=a.roleid WHERE a.member=(SELECT oid FROM pg_roles WHERE rolname=current_user) ORDER BY r.rolname').fetchall() == [
            ('proptech_usage_guard', False, True, False), ('proptech_usage_writer', False, True, False)]
        assert conn.execute("SELECT pg_has_role(current_user,'proptech_usage_reader','MEMBER'),pg_has_role(current_user,'proptech_usage_executor','MEMBER'),has_schema_privilege(current_user,'api_usage','CREATE'),has_database_privilege(current_user,current_database(),'CREATE')").fetchone() == (False,) * 4
    PostgresQuotaGuard(target.runtime_url).check()
    PostgresUsageStore(target.runtime_url).check()


def test_real_guard_and_writer_work_and_batch_replay_is_idempotent(target):
    from services.usage_guard import PostgresQuotaGuard
    from services.usage_ledger import PostgresUsageStore
    from services.usage_principal import UsagePrincipal
    from services.api_usage import UsageAggregator
    install(target, runtime=True)
    principal = UsagePrincipal('anon:' + 'a' * 64, 'anonymous', 'a' * 64)
    guard = PostgresQuotaGuard(target.runtime_url)
    marker = uuid4()
    assert guard.consume(principal, 'places', 'request', marker) == 'admitted'
    assert guard.consume(principal, 'places', 'request', marker) == 'duplicate'
    assert guard.consume(principal, 'places', 'operation', uuid4()) == 'admitted'
    usage = UsageAggregator()
    usage.observe(capability='places', provider='google_places', event='physical_calls', count=2)
    store = PostgresUsageStore(target.runtime_url)
    rows, batch = usage.take_pending(), uuid4()
    store.write_batch(batch, rows)
    store.write_batch(batch, rows)
    assert store.summary()['rows'][0]['provider_attempt_count'] == 2
    store.write_batch(uuid4(), [])  # Runs real bounded retention and executor prune.
    with target.connect('postgres') as conn:
        assert conn.execute('SELECT requests,operations,daily_operations FROM api_usage.quota_subjects WHERE subject=%s', (principal.key,)).fetchone() == (1, 1, 1)
        assert conn.execute('SELECT sum(admitted),sum(reservations) FROM api_usage.quota_hourly').fetchone() == (1, 1)
        assert conn.execute('SELECT count(*) FROM api_usage.flush_batches').fetchone()[0] == 1


@pytest.mark.parametrize('role', ['proptech_usage_guard','proptech_usage_writer',*BROWSER_ROLES])
def test_roles_cannot_cross_telemetry_quota_or_browser_boundaries(target, role):
    import psycopg
    from psycopg import sql
    install(target)
    denied = ['UPDATE api_usage.quota_policy SET request_hour=99999', 'UPDATE api_usage.quota_subjects SET requests=0', 'DELETE FROM api_usage.quota_hourly', 'TRUNCATE api_usage.quota_hourly']
    if role != 'proptech_usage_writer':
        denied += ['INSERT INTO api_usage.flush_batches(batch_id) VALUES(gen_random_uuid())', 'DELETE FROM api_usage.hourly']
    if role != 'proptech_usage_guard':
        denied += ['SELECT api_usage.consume(NULL,NULL,NULL,NULL,NULL)']
    if role not in ('proptech_usage_guard','proptech_usage_writer'):
        denied += ['SELECT api_usage.prune()', 'SELECT * FROM api_usage.hourly']
    for statement in denied:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            with target.connect('postgres') as conn:
                conn.execute(sql.SQL('SET LOCAL ROLE {}').format(sql.Identifier(role)))
                conn.execute(statement)


def test_public_has_no_table_or_function_acl_and_force_rls_binds_owner(target):
    install(target, runtime=True)
    from services.usage_guard import PostgresQuotaGuard
    from services.usage_principal import UsagePrincipal
    PostgresQuotaGuard(target.runtime_url).consume(UsagePrincipal('anon:'+'b'*64, 'anonymous'), 'places', 'request', uuid4())
    with target.connect() as conn:
        assert conn.execute('SELECT count(*) FROM api_usage.quota_subjects').fetchone()[0] == 0
        with pytest.raises(__import__('psycopg').errors.InsufficientPrivilege):
            with conn.transaction():
                conn.execute("INSERT INTO api_usage.quota_subjects(subject,principal_class,hour_bucket,day_bucket) VALUES('anon:'||repeat('c',64),'anonymous',now(),now())")
        assert conn.execute("SELECT count(*) FROM pg_class c CROSS JOIN LATERAL aclexplode(coalesce(c.relacl,acldefault('r',c.relowner))) a WHERE c.relnamespace='api_usage'::regnamespace AND a.grantee=0").fetchone()[0] == 0
        assert conn.execute("SELECT count(*) FROM pg_proc p CROSS JOIN LATERAL aclexplode(coalesce(p.proacl,acldefault('f',p.proowner))) a WHERE p.pronamespace='api_usage'::regnamespace AND a.grantee=0").fetchone()[0] == 0


@pytest.mark.parametrize('state', ['schema','table','function','type','default_acl','extension','partial_schema','partial_role','wrong_database','actor_superuser','actor_bypassrls'])
def test_fresh_target_refuses_unrelated_or_partial_state(target, state):
    from scripts.bootstrap_usage_database import bootstrap, BootstrapRefused
    statements = {
        'schema':'CREATE SCHEMA unrelated', 'table':'CREATE TABLE public.unrelated(id int)',
        'function':"CREATE FUNCTION public.unrelated() RETURNS int LANGUAGE sql AS 'SELECT 1'",
        'type':"CREATE TYPE public.unrelated AS ENUM ('one')",
        'default_acl':'ALTER DEFAULT PRIVILEGES GRANT SELECT ON TABLES TO anon',
        'extension':'CREATE EXTENSION hstore',
        'partial_schema':'CREATE SCHEMA api_usage',
        'partial_role':'CREATE ROLE proptech_usage_guard NOLOGIN',
    }
    if state in statements:
        with target.connect('postgres') as conn:
            conn.execute(statements[state])
    if state=='actor_bypassrls':
        with target.connect('postgres') as conn:
            conn.execute('ALTER ROLE usage_migration BYPASSRLS')
    with target.connect('postgres' if state=='actor_superuser' else ACTOR) as conn:
        with pytest.raises(BootstrapRefused):
            bootstrap(conn, expected_database='wrong_database' if state=='wrong_database' else target.database, release_version=RELEASE)
    with target.connect('postgres') as conn:
        assert conn.execute("SELECT to_regnamespace('api_usage_bootstrap')").fetchone() == (None,)


def test_repeated_bootstrap_and_runtime_provisioning_are_bounded_refusals(target):
    from scripts.bootstrap_usage_database import bootstrap, provision_runtime, BootstrapRefused
    install(target, runtime=True)
    with target.connect() as conn:
        with pytest.raises(BootstrapRefused, match='already_provisioned'):
            bootstrap(conn, expected_database=target.database, release_version=RELEASE)
    with target.connect() as conn:
        with pytest.raises(BootstrapRefused, match='runtime_already_exists'):
            provision_runtime(conn, expected_database=target.database)
    with target.connect('postgres') as conn:
        assert conn.execute('SELECT count(*) FROM api_usage_bootstrap.history').fetchone()[0] == 1


@pytest.mark.parametrize('failure', ['cleanup','verification'])
def test_failure_rolls_back_schema_roles_privileges_and_history(target, monkeypatch, failure):
    import scripts.bootstrap_usage_database as module
    def reject(*args, **kwargs):
        raise RuntimeError('injected verification failure')
    if failure == 'verification':
        monkeypatch.setattr(module, 'verify_security', reject)
    class Connection:
        def __init__(self, real): self.real = real
        def __getattr__(self, name): return getattr(self.real, name)
        def execute(self, query, *args, **kwargs):
            if failure == 'cleanup' and isinstance(query, str) and query.startswith('REVOKE CREATE ON SCHEMA api_usage'):
                raise RuntimeError('injected cleanup failure')
            return self.real.execute(query, *args, **kwargs)
    with target.connect() as conn:
        with pytest.raises(RuntimeError, match='injected'):
            module.bootstrap(Connection(conn), expected_database=target.database, release_version=RELEASE)
    assert_empty(target)


@pytest.mark.parametrize('unsafe', ['CREATEDB','CREATEROLE','BYPASSRLS','SUPERUSER','REPLICATION','database_owner','schema_owner','function_owner','inherited_owner','inherited_createdb','inherited_schema_create','inherited_database_create','executor','schema_create','database_create','admin_option','disguised_session','pg_execute_server_program','pg_read_server_files','pg_write_server_files'])
def test_runtime_guard_rejects_unsafe_direct_inherited_and_session_authority(target, unsafe):
    from services.usage_guard import PostgresQuotaGuard
    from psycopg import sql
    install(target, runtime=True)
    with target.connect('postgres') as conn:
        if unsafe in ('CREATEDB','CREATEROLE','BYPASSRLS','SUPERUSER','REPLICATION'):
            conn.execute(sql.SQL('ALTER ROLE {} {}').format(sql.Identifier(RUNTIME),sql.SQL(unsafe)))
        elif unsafe == 'database_owner':
            conn.execute(sql.SQL('ALTER DATABASE {} OWNER TO {}').format(sql.Identifier(target.database),sql.Identifier(RUNTIME)))
        elif unsafe == 'schema_owner':
            conn.execute(sql.SQL('ALTER SCHEMA api_usage OWNER TO {}').format(sql.Identifier(RUNTIME)))
        elif unsafe == 'function_owner':
            conn.execute(sql.SQL('ALTER FUNCTION api_usage.prune() OWNER TO {}').format(sql.Identifier(RUNTIME)))
        elif unsafe in ('inherited_owner','inherited_createdb','inherited_schema_create','inherited_database_create'):
            conn.execute('CREATE ROLE usage_unsafe_parent NOLOGIN' + (' CREATEDB' if unsafe=='inherited_createdb' else ''))
            conn.execute(sql.SQL('GRANT usage_unsafe_parent TO {} WITH SET TRUE, INHERIT FALSE').format(sql.Identifier(RUNTIME)))
            if unsafe == 'inherited_owner':
                conn.execute('ALTER SCHEMA api_usage OWNER TO usage_unsafe_parent')
            elif unsafe == 'inherited_schema_create':
                conn.execute('GRANT CREATE ON SCHEMA api_usage TO usage_unsafe_parent')
            elif unsafe == 'inherited_database_create':
                conn.execute(sql.SQL('GRANT CREATE ON DATABASE {} TO usage_unsafe_parent').format(sql.Identifier(target.database)))
        elif unsafe == 'executor':
            conn.execute(sql.SQL('GRANT proptech_usage_executor TO {}').format(sql.Identifier(RUNTIME)))
        elif unsafe == 'schema_create':
            conn.execute(sql.SQL('GRANT CREATE ON SCHEMA api_usage TO {}').format(sql.Identifier(RUNTIME)))
        elif unsafe == 'database_create':
            conn.execute(sql.SQL('GRANT CREATE ON DATABASE {} TO {}').format(sql.Identifier(target.database),sql.Identifier(RUNTIME)))
        elif unsafe == 'admin_option':
            conn.execute(sql.SQL('GRANT proptech_usage_guard TO {} WITH ADMIN TRUE').format(sql.Identifier(RUNTIME)))
        elif unsafe.startswith('pg_'):
            conn.execute(sql.SQL('GRANT {} TO {} WITH INHERIT TRUE, SET TRUE, ADMIN FALSE').format(sql.Identifier(unsafe),sql.Identifier(RUNTIME)))
    guard = PostgresQuotaGuard(target.runtime_url)
    if unsafe == 'disguised_session':
        def disguised(_):
            c = target.connect('postgres')
            c.execute('SET ROLE proptech_usage_guard')
            c.commit()
            return c
        guard = PostgresQuotaGuard('unused', connection_factory=disguised)
    with pytest.raises(RuntimeError, match='Unsafe API usage database principal'):
        guard.check()


@pytest.mark.parametrize('drift', ['executor_create','column_acl','function_body','rls','public_execute','request_execute','trigger','rule'])
def test_provisioner_refuses_installed_security_drift(target, drift):
    from scripts.bootstrap_usage_database import provision_runtime, BootstrapRefused
    install(target)
    with target.connect('postgres') as conn:
        conn.execute({
            'executor_create':'GRANT CREATE ON SCHEMA api_usage TO proptech_usage_executor',
            'column_acl':'GRANT SELECT(requests) ON api_usage.quota_subjects TO proptech_usage_guard',
            'function_body':"CREATE OR REPLACE FUNCTION api_usage.prune() RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path='' AS $$BEGIN RETURN; END$$",
            'rls':'ALTER TABLE api_usage.hourly NO FORCE ROW LEVEL SECURITY',
            'public_execute':'GRANT EXECUTE ON FUNCTION api_usage.consume(text,text,text,text,uuid) TO PUBLIC',
            'request_execute':'GRANT EXECUTE ON FUNCTION api_usage.consume(text,text,text,text,uuid) TO authenticated',
            'trigger':"CREATE FUNCTION public.zero_counters() RETURNS trigger LANGUAGE plpgsql AS $$BEGIN NEW.requests=0; NEW.operations=0; NEW.daily_operations=0; RETURN NEW; END$$; CREATE TRIGGER bypass_quota BEFORE INSERT OR UPDATE ON api_usage.quota_subjects FOR EACH ROW EXECUTE FUNCTION public.zero_counters()",
            'rule':'CREATE RULE bypass_quota AS ON UPDATE TO api_usage.quota_subjects DO INSTEAD NOTHING',
        }[drift])
    with target.connect() as conn:
        with pytest.raises(BootstrapRefused):
            provision_runtime(conn, expected_database=target.database)
    with target.connect() as conn:
        assert conn.execute('SELECT 1 FROM pg_roles WHERE rolname=%s', (RUNTIME,)).fetchall() == []


def test_runtime_provisioner_rolls_back_role_and_membership_after_failed_final_audit(target, monkeypatch):
    from scripts import bootstrap_usage_database as module
    install(target)
    real = module.verify_security
    def verify(*args, **kwargs):
        real(*args, **kwargs)
        if kwargs.get('runtime'):
            raise RuntimeError('injected runtime audit failure')
    monkeypatch.setattr(module,'verify_security',verify)
    with target.connect() as conn:
        with pytest.raises(RuntimeError, match='injected runtime audit'):
            module.provision_runtime(conn,expected_database=target.database)
    with target.connect() as conn:
        assert conn.execute('SELECT 1 FROM pg_roles WHERE rolname=%s',(RUNTIME,)).fetchall()==[]
        module.verify_security(conn,actor=ACTOR,migration_text=MIGRATION.read_text(encoding='utf-8'))


def test_migration_source_rehashes_the_bytes_it_actually_consumes(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from scripts import bootstrap_usage_database as module
    path = tmp_path / '021.sql'
    path.write_bytes(MIGRATION.read_bytes()+b'\n-- unregistered change\n')
    monkeypatch.setattr(module, 'load_registry', lambda: [SimpleNamespace(path=path,sha256=CHECKSUM)])
    # Give the fake registration the real stem so this test targets the second
    # read/checksum boundary, independently of registry file verification.
    renamed = tmp_path / (MIGRATION.stem + '.sql')
    path.rename(renamed)
    monkeypatch.setattr(module, 'load_registry', lambda: [SimpleNamespace(path=renamed,sha256=CHECKSUM)])
    with pytest.raises(module.BootstrapRefused, match='migration_checksum_mismatch'):
        module.migration_source()


def test_cli_plan_never_connects_and_execution_suppresses_connection_secrets(monkeypatch, capsys):
    from scripts import bootstrap_usage_database as module
    def forbidden(*args, **kwargs):
        raise RuntimeError('synthetic-private-connection-detail')
    monkeypatch.setattr('services.postgres_runtime.connect', forbidden)
    monkeypatch.setenv('PRODUCTION_MIGRATION_DATABASE_URL','synthetic-private-production-value')
    assert module.main([])==0
    assert '"database_contacted": false' in capsys.readouterr().out
    assert module.main(['--execute'])==1
    assert 'explicit_dedicated_target_required' in capsys.readouterr().out
    monkeypatch.delenv('API_USAGE_BOOTSTRAP_DATABASE_URL',raising=False)
    args = ['--execute','--acknowledge-fresh-dedicated','--expected-database','synthetic_db','--release-version',RELEASE]
    assert module.main(args)==1
    assert 'bootstrap_url_required' in capsys.readouterr().out
    monkeypatch.setenv('API_USAGE_BOOTSTRAP_DATABASE_URL','synthetic-private-bootstrap-value')
    assert module.main(args)==1
    assert capsys.readouterr().out.strip()=='{"status": "failed", "reason": "details_suppressed"}'


@pytest.mark.parametrize('endpoint', ['tcp://remote.example.invalid:2375','ssh://remote.example.invalid','npipe:////remote/pipe/docker_engine','unix://remote/docker.sock'])
def test_rehearsal_refuses_remote_docker_before_daemon_commands(monkeypatch, endpoint):
    from scripts import rehearse_usage_database as module
    monkeypatch.setenv('DOCKER_HOST', endpoint)
    def forbidden(*args, **kwargs):
        pytest.fail('Docker must not be called with a remote endpoint')
    monkeypatch.setattr(module.subprocess,'run',forbidden)
    with pytest.raises(RuntimeError, match='local_docker_endpoint_required'):
        module.local_docker_prefix(module.clean_environment())


def test_rehearsal_excludes_inherited_usage_and_docker_secrets(monkeypatch):
    from scripts.rehearse_usage_database import clean_environment
    for name in ('API_USAGE_PEER_HMAC_KEY','DOCKER_HOST','DOCKER_CONTEXT','DOCKER_CONFIG','PRODUCTION_MIGRATION_DATABASE_URL','API_USAGE_BOOTSTRAP_DATABASE_URL','PGSERVICE','PGPASSFILE'):
        monkeypatch.setenv(name,'synthetic-private-value')
    environment = clean_environment()
    assert not any(name in environment for name in ('API_USAGE_PEER_HMAC_KEY','DOCKER_HOST','DOCKER_CONTEXT','DOCKER_CONFIG','PRODUCTION_MIGRATION_DATABASE_URL','API_USAGE_BOOTSTRAP_DATABASE_URL','PGSERVICE','PGPASSFILE'))
