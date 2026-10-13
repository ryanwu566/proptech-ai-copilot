"""Atomic quota and least-privilege proofs against loopback disposable PostgreSQL."""
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlsplit
from uuid import UUID, uuid4

import pytest

from services.usage_quota import QuotaExceeded


@pytest.fixture(scope="module")
def database():
    target = os.getenv("API_USAGE_TEST_POSTGRES_URL", "")
    if not target or os.getenv("API_USAGE_TEST_DISPOSABLE") != "1":
        pytest.skip("Explicit disposable usage PostgreSQL is not configured")
    parsed = urlsplit(target)
    assert parsed.scheme in {"postgres", "postgresql"}
    assert parsed.hostname in {"127.0.0.1", "localhost"}
    assert parsed.path.lstrip("/").startswith("api_usage_test")
    import psycopg
    with psycopg.connect(target) as conn:
        # Dedicated confirmed loopback test database only; each run is repeatable.
        conn.execute("DROP SCHEMA IF EXISTS api_usage CASCADE")
        conn.execute(Path("database/migrations/021_api_usage_quota_ledger.sql").read_text(encoding="utf-8"))
        conn.execute("UPDATE api_usage.quota_policy SET request_hour=5,operation_hour=3,operation_day=4")
    return target


def guard(database):
    import psycopg
    from services.usage_guard import PostgresQuotaGuard
    def connection(_):
        conn = psycopg.connect(database)
        conn.execute("SET ROLE proptech_usage_guard")
        conn.commit()
        return conn
    return PostgresQuotaGuard(database, connection_factory=connection)


def subject(number):
    from services.usage_principal import verified_principal
    from services.vnext.auth import AuthenticatedPrincipal
    uid = UUID(int=number)
    return verified_principal(AuthenticatedPrincipal(uid, str(uid), "fixture"))


@pytest.mark.external_database
def test_atomic_shared_budget_instances_restart_duplicate_and_independent_user(database):
    identity = subject(700)
    def run(_):
        try:
            # Independent adapter/connection, as on different API instances.
            return guard(database).consume(identity, "places", "request", uuid4())
        except QuotaExceeded:
            return "quota"
    with ThreadPoolExecutor(max_workers=12) as pool:
        results = list(pool.map(run, range(24)))
    assert results.count("admitted") == 5
    assert results.count("quota") == 19
    with pytest.raises(QuotaExceeded):
        guard(database).consume(identity, "places", "request", uuid4())
    assert guard(database).consume(subject(701), "places", "request", uuid4()) == "admitted"
    token = uuid4()
    for _ in range(10):
        guard(database).consume(subject(702), "routes", "operation", token)
    import psycopg
    with psycopg.connect(database) as conn:
        assert conn.execute("SELECT operations,daily_operations FROM api_usage.quota_subjects WHERE subject=%s", (subject(702).key,)).fetchone() == (1, 1)
        assert conn.execute("SELECT sum(admitted),sum(rejected) FROM api_usage.quota_hourly WHERE subject=%s", (identity.key,)).fetchone() == (5, 20)


@pytest.mark.external_database
def test_operation_atomicity_failure_consumes_reservation_and_marker_mismatch_denies(database):
    identity = subject(703)
    store = guard(database)
    token = uuid4()
    assert store.consume(identity, "places", "operation", token) == "admitted"
    assert store.consume(identity, "places", "operation", token) == "duplicate"
    with pytest.raises(RuntimeError):
        store.consume(identity, "routes", "operation", token)
    for _ in range(2):
        store.consume(identity, "places", "operation", uuid4())
    with pytest.raises(QuotaExceeded):
        store.consume(identity, "places", "operation", uuid4())
    import psycopg
    with psycopg.connect(database) as conn:
        conn.execute("UPDATE api_usage.quota_subjects SET hour_bucket=hour_bucket-interval '1 hour' WHERE subject=%s", (identity.key,))
    store.consume(identity, "places", "operation", uuid4())
    with pytest.raises(QuotaExceeded):
        store.consume(identity, "places", "operation", uuid4())


@pytest.mark.external_database
def test_private_roles_cannot_mutate_policy_counters_or_forge_account_authority(database):
    import psycopg
    with psycopg.connect(database) as conn:
        for role in ("anon", "authenticated", "service_role", "vnext_api", "usage_test_owner", "usage_test_bypass"):
            if not conn.execute("SELECT 1 FROM pg_roles WHERE rolname=%s", (role,)).fetchone():
                conn.execute(f"CREATE ROLE {role} NOLOGIN")
        for role in ("anon", "authenticated", "service_role", "vnext_api", "proptech_usage_guard"):
            for sql in ("SELECT * FROM api_usage.quota_subjects", "UPDATE api_usage.quota_policy SET request_hour=99999", "DELETE FROM api_usage.quota_subjects"):
                with pytest.raises(psycopg.errors.InsufficientPrivilege):
                    with conn.transaction():
                        conn.execute(f"SET LOCAL ROLE {role}")
                        conn.execute("SELECT set_config('request.jwt.claims', '{\"platform_role\":\"platform_admin\",\"workspace_role\":\"owner\"}', true)")
                        conn.execute(sql)
            if role != "proptech_usage_guard":
                with pytest.raises(psycopg.errors.InsufficientPrivilege):
                    with conn.transaction():
                        conn.execute(f"SET LOCAL ROLE {role}")
                        conn.execute("SELECT * FROM api_usage.consume('user:00000000-0000-0000-0000-000000000001','authenticated','places','request',gen_random_uuid())")
        # FORCE RLS binds an ordinary table owner; owner has no applicable policy.
        with conn.transaction(force_rollback=True):
            conn.execute("GRANT USAGE ON SCHEMA api_usage TO usage_test_owner")
            conn.execute("ALTER TABLE api_usage.quota_subjects OWNER TO usage_test_owner")
            conn.execute("SET LOCAL ROLE usage_test_owner")
            assert conn.execute("SELECT count(*) FROM api_usage.quota_subjects").fetchone()[0] == 0
        # BYPASSRLS really bypasses policies when granted access: deployment must reject it.
        with conn.transaction(force_rollback=True):
            conn.execute("ALTER ROLE usage_test_bypass BYPASSRLS")
            conn.execute("GRANT USAGE ON SCHEMA api_usage TO usage_test_bypass")
            conn.execute("GRANT SELECT ON api_usage.quota_subjects TO usage_test_bypass")
            conn.execute("SET LOCAL ROLE usage_test_bypass")
            assert conn.execute("SELECT count(*) FROM api_usage.quota_subjects").fetchone()[0] > 0


@pytest.mark.external_database
def test_retention_expired_markers_and_anonymous_private_subject(database):
    import psycopg
    from services.usage_principal import principal_from_scope
    identity = principal_from_scope({"client": ("192.0.2.90", 1)})
    store = guard(database)
    token = uuid4()
    store.consume(identity, "places", "request", token)
    with psycopg.connect(database) as conn:
        conn.execute("UPDATE api_usage.reservation_markers SET created_at=clock_timestamp()-interval '11 minutes' WHERE subject=%s", (identity.key,))
    assert store.consume(identity, "places", "request", token) == "admitted"
    with psycopg.connect(database) as conn:
        assert "192.0.2.90" not in str(conn.execute("SELECT * FROM api_usage.quota_subjects WHERE subject=%s", (identity.key,)).fetchone())
        conn.execute("UPDATE api_usage.quota_subjects SET updated_at=clock_timestamp()-interval '3 days' WHERE subject=%s", (identity.key,))
        conn.execute("UPDATE api_usage.reservation_markers SET created_at=clock_timestamp()-interval '11 minutes' WHERE subject=%s", (identity.key,))
        with conn.transaction():
            conn.execute("SET LOCAL ROLE proptech_usage_writer")
            conn.execute("SELECT api_usage.prune()")
        conn.execute("RESET ROLE")
        assert conn.execute("SELECT count(*) FROM api_usage.quota_subjects WHERE subject=%s", (identity.key,)).fetchone()[0] == 0


@pytest.mark.external_database
def test_pruning_skips_subject_locked_by_inflight_admission(database):
    import psycopg
    identity = subject(704)
    guard(database).consume(identity, "places", "request", uuid4())
    with psycopg.connect(database) as conn:
        conn.execute("UPDATE api_usage.quota_subjects SET updated_at=clock_timestamp()-interval '3 days' WHERE subject=%s", (identity.key,))
    with psycopg.connect(database) as locked:
        locked.execute("SELECT subject FROM api_usage.quota_subjects WHERE subject=%s FOR UPDATE", (identity.key,))
        def prune():
            with psycopg.connect(database) as conn:
                conn.execute("SET LOCAL statement_timeout='500ms'")
                conn.execute("SET LOCAL ROLE proptech_usage_writer")
                conn.execute("SELECT api_usage.prune()")
        with ThreadPoolExecutor(max_workers=1) as pool:
            pool.submit(prune).result(timeout=3)
        locked.execute("UPDATE api_usage.quota_subjects SET updated_at=clock_timestamp() WHERE subject=%s", (identity.key,))
    with psycopg.connect(database) as conn:
        assert conn.execute("SELECT requests FROM api_usage.quota_subjects WHERE subject=%s", (identity.key,)).fetchone()[0] == 1


@pytest.mark.external_database
def test_runtime_principal_probe_rejects_owner_superuser_and_accepts_guard_login(database):
    import psycopg
    from services.usage_guard import PostgresQuotaGuard
    with pytest.raises(RuntimeError, match="Unsafe API usage database principal"):
        PostgresQuotaGuard(database).check()
    with psycopg.connect(database) as conn:
        if not conn.execute("SELECT 1 FROM pg_roles WHERE rolname='usage_guard_login'").fetchone():
            conn.execute("CREATE ROLE usage_guard_login LOGIN INHERIT NOBYPASSRLS")
        conn.execute("GRANT proptech_usage_guard TO usage_guard_login")
    url = database.replace("postgres@", "usage_guard_login@")
    PostgresQuotaGuard(url).check()
    def disguised(_):
        conn = psycopg.connect(database)
        conn.execute("SET ROLE proptech_usage_guard")
        conn.commit()
        return conn
    with pytest.raises(RuntimeError, match="Unsafe API usage database principal"):
        PostgresQuotaGuard(database, connection_factory=disguised).check()


@pytest.mark.external_database
def test_per_subject_retry_namespace_is_bounded_and_not_client_selected(database):
    import psycopg
    identity = subject(705)
    store = guard(database)
    store.consume(identity, "places", "request", uuid4())
    with psycopg.connect(database) as conn:
        with conn.cursor() as cursor:
            cursor.executemany("INSERT INTO api_usage.reservation_markers(subject,marker,capability,kind) VALUES (%s,%s,'places','request')", [(identity.key, uuid4()) for _ in range(2047)])
    with pytest.raises(RuntimeError):
        store.consume(identity, "places", "request", uuid4())
    with psycopg.connect(database) as conn:
        assert conn.execute("SELECT requests FROM api_usage.quota_subjects WHERE subject=%s", (identity.key,)).fetchone()[0] == 1
        assert conn.execute("SELECT count(*) FROM api_usage.reservation_markers WHERE subject=%s", (identity.key,)).fetchone()[0] == 2048


@pytest.mark.external_database
def test_budget_timestamp_is_selected_after_waiting_for_subject_lock(database):
    import time
    import psycopg
    identity = subject(706)
    with psycopg.connect(database) as locker:
        locker.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s,831))", (identity.key,))
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(guard(database).consume, identity, "places", "request", uuid4())
            try:
                deadline = time.monotonic() + 2
                while True:
                    locker.execute("SELECT pg_stat_clear_snapshot()")
                    waiting = locker.execute("SELECT count(*) FROM pg_stat_activity WHERE wait_event='advisory' AND datname=current_database() AND pid<>pg_backend_pid()").fetchone()[0]
                    if waiting:
                        break
                    assert time.monotonic() < deadline
                    time.sleep(0.005)
                released = locker.execute("SELECT clock_timestamp()").fetchone()[0]
                locker.commit()
            finally:
                locker.commit()
            assert future.result(timeout=3) == "admitted"
    with psycopg.connect(database) as conn:
        stamp = conn.execute("SELECT updated_at FROM api_usage.quota_subjects WHERE subject=%s", (identity.key,)).fetchone()[0]
        assert stamp >= released


@pytest.mark.external_database
def test_real_http_instances_cache_failure_accounting_and_no_work_after_rejection(database, monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from services import anti_abuse, api_usage
    from backend.api.abuse_middleware import AbuseMiddleware
    from services.provider_cost_metrics import PROVIDER_COST_METRICS
    from services.provider_request_cache import BoundedRequestCache
    from services.usage_ledger import PostgresUsageStore
    import psycopg
    monkeypatch.setenv("API_USAGE_PEER_HMAC_KEY", "ab" * 32)
    calls = []
    def application(fail=False):
        controls = anti_abuse.AbuseControls({"places": anti_abuse.Policy(100,60,8,100)})
        controls.durable_guard = guard(database)
        app = FastAPI()
        cache = BoundedRequestCache("places",60,8)
        def provider():
            with controls.operation("places"):
                calls.append(1)
                PROVIDER_COST_METRICS.record("places","physical_calls")
                if fail:
                    PROVIDER_COST_METRICS.record("places","provider_failure")
                    raise RuntimeError("private-provider-credential")
                return {"ok": True}
        @app.post("/map/nearby")
        def endpoint():
            return cache.run("one-server-owned-key",provider)
        app.add_middleware(AbuseMiddleware,controls=controls)
        return app
    first = TestClient(application(),client=("192.0.2.233",1))
    restarted = TestClient(application(),client=("192.0.2.233",2))
    for client in (first,first,restarted,first,restarted):
        assert client.post("/map/nearby").status_code == 200
    rejected = restarted.post("/map/nearby",headers={"X-Forwarded-For":"192.0.2.250"})
    assert rejected.status_code == 429
    assert rejected.json()["detail"]["reason_code"] == "anonymous_quota"
    assert len(calls) == 2  # Two process owners; three completed-cache hits.
    failing = TestClient(application(fail=True),client=("192.0.2.234",1),raise_server_exceptions=False)
    for _ in range(3):
        response = failing.post("/map/nearby")
        assert response.status_code == 500
        assert "credential" not in response.text
    assert failing.post("/map/nearby").status_code == 429
    assert len(calls) == 5
    totals = api_usage.USAGE.summary()["totals"]
    assert totals["provider_attempt_count"] == 5
    assert totals["provider_failures"] == 3
    assert totals["cache_hits"] == 3
    def writer(_):
        conn = psycopg.connect(database)
        conn.execute("SET ROLE proptech_usage_writer")
        conn.commit()
        return conn
    store = PostgresUsageStore(database,connection_factory=writer)
    store.write_batch(uuid4(),api_usage.USAGE.take_pending())
    with psycopg.connect(database) as conn:
        assert conn.execute("SELECT sum(provider_attempt_count),sum(provider_failures) FROM api_usage.hourly").fetchone() == (5,3)


@pytest.mark.external_database
def test_verified_public_users_share_durable_budget_and_spoofing_cannot_select_victim(database, monkeypatch):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from backend.api.abuse_middleware import AbuseMiddleware
    from services import anti_abuse
    from services.vnext.auth import SupabaseJWTVerifier
    from tests.test_vnext_auth_api import _token, PUBLIC_KEY, ISSUER
    from tests.account_fixtures import active_account_authorizer
    monkeypatch.setenv("API_USAGE_PEER_HMAC_KEY", "ab" * 32)
    monkeypatch.setattr("services.vnext.auth.get_supabase_jwt_verifier", lambda: SupabaseJWTVerifier(issuer=ISSUER,signing_key_resolver=lambda _: PUBLIC_KEY))
    monkeypatch.setattr("services.vnext.accounts.get_account_authorizer", active_account_authorizer)
    calls = []
    def application():
        controls = anti_abuse.AbuseControls({"places": anti_abuse.Policy(100,60,8,100)})
        controls.durable_guard = guard(database)
        app = FastAPI()
        @app.post("/map/nearby")
        def endpoint():
            calls.append(1)
            return {"ok":True}
        app.add_middleware(AbuseMiddleware,controls=controls)
        return TestClient(app)
    a,b = str(UUID(int=900)),str(UUID(int=901))
    headers = {"Authorization":"Bearer "+_token(subject=a,user_metadata={"user_id":b,"role":"platform_admin"}),
               "X-User-ID":b,"X-Role":"platform_admin","X-Workspace-Role":"owner","X-Real-IP":"192.0.2.2","Forwarded":"for=192.0.2.2"}
    clients = [application(),application()]
    for i in range(5):
        assert clients[i%2].post("/map/nearby?user_id="+b,headers=headers).status_code == 200
    response = application().post("/map/nearby?user_id="+b,headers=headers)
    assert response.status_code == 429
    assert response.json()["detail"]["reason_code"] == "authenticated_quota"
    assert 1<=int(response.headers["Retry-After"])<=3600
    assert clients[0].post("/map/nearby",headers={"Authorization":"Bearer "+_token(subject=b)}).status_code == 200
    assert len(calls) == 6


@pytest.mark.external_database
def test_pruning_uses_age_index_conditions_in_actual_nested_plans(database):
    import json
    import psycopg
    messages = []
    with psycopg.connect(database) as conn:
        conn.add_notice_handler(lambda diagnostic:messages.append(diagnostic.message_primary))
        for statement in ("LOAD 'auto_explain'","SET client_min_messages='log'",
                          "SET auto_explain.log_min_duration=0","SET auto_explain.log_nested_statements=on",
                          "SET auto_explain.log_format='json'","SET enable_seqscan=off",
                          "SELECT api_usage.prune()"):
            conn.execute(statement)
    conditions = []
    def collect(node):
        if isinstance(node,dict):
            if "Index Cond" in node: conditions.append(node["Index Cond"])
            for value in node.values(): collect(value)
        elif isinstance(node,list):
            for value in node: collect(value)
    for message in messages:
        if "DELETE FROM api_usage" in message:
            collect(json.loads(message[message.index("{"):]))
    for column in ("created_at","updated_at","bucket_start"):
        assert any(column+" <" in condition for condition in conditions), (column,conditions)
