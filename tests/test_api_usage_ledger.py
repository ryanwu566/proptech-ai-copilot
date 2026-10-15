"""Bounded asynchronous ledger writes, idempotency and privacy boundaries."""
from contextlib import contextmanager
from datetime import UTC, datetime
import threading
import time

import pytest

from services.api_usage import UsageAggregator


class Store:
    def __init__(self):
        self.rows = []
        self.ids = set()
        self.fail = False
        self.ambiguous = False
    def write_batch(self, batch_id, rows):
        if self.fail:
            raise RuntimeError("secret-dsn-and-password")
        if batch_id not in self.ids:
            self.ids.add(batch_id)
            self.rows.extend(rows)
        if self.ambiguous:
            self.ambiguous = False
            raise RuntimeError("commit-response-lost")


def test_bounded_batch_retries_same_id_after_ambiguous_commit():
    from services.usage_ledger import UsageFlusher
    usage, store = UsageAggregator(max_rows=4), Store()
    writer = UsageFlusher(usage, store)
    usage.observe(capability="places", event="physical_calls", provider="google_places")
    store.ambiguous = True
    assert writer.flush_once() is False
    assert usage.summary()["accounting"]["writer_status"] == "unavailable"
    usage.observe(capability="places", event="physical_calls", provider="google_places")
    assert writer.flush_once() is True
    assert sum(row["provider_attempt_count"] for row in store.rows) == 1
    assert writer.flush_once() is True
    assert sum(row["provider_attempt_count"] for row in store.rows) == 2
    assert len(store.ids) == 2


def test_outage_does_not_write_on_request_path_or_grow_buffer():
    from services.usage_ledger import UsageFlusher
    usage, store = UsageAggregator(max_rows=4), Store()
    writer = UsageFlusher(usage, store)
    store.fail = True
    for _ in range(1000):
        usage.observe(capability="places", event="physical_calls", provider="google_places")
    assert not store.rows
    assert writer.flush_once() is False
    assert usage.summary()["accounting"]["writer_status"] == "unavailable"
    assert len(writer.pending_rows) == 1
    assert "secret" not in str(usage.summary())
    store.fail = False
    assert writer.flush_once() is True
    assert store.rows[0]["provider_attempt_count"] == 1000


def test_expired_pending_records_are_counted_as_loss_not_replayed():
    from services.usage_ledger import UsageFlusher
    now = [0.0]
    usage, store = UsageAggregator(wall_clock=lambda: now[0]), Store()
    writer = UsageFlusher(usage, store, wall_clock=lambda: now[0])
    usage.observe(capability="places", event="physical_calls")
    store.fail = True
    writer.flush_once()
    now[0] = 32 * 86400
    store.fail = False
    assert writer.flush_once() is True
    assert not store.rows
    assert usage.summary()["accounting"]["complete"] is False
    assert usage.summary()["accounting"]["expired_observations"] > 0


def test_postgres_writer_uses_transaction_marker_and_parameterized_aggregates():
    from services.usage_ledger import PostgresUsageStore
    from uuid import UUID
    operations = []
    class Result:
        def fetchone(self):
            return (1,)
    class Connection:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        @contextmanager
        def transaction(self):
            operations.append("begin")
            yield
            operations.append("commit")
        def execute(self, query, params=None):
            operations.append((query, params))
            return Result()
        def cursor(self): return self
        def executemany(self, query, values):
            operations.append((query, list(values)))
    usage = UsageAggregator(wall_clock=lambda: 1760000000)
    usage.observe(capability="places", provider="google_places", event="physical_calls")
    store = PostgresUsageStore("postgresql://local.test/disposable", connection_factory=lambda _: Connection())
    store.write_batch(UUID(int=1), usage.take_pending())
    assert operations[0] == "begin" and operations[-1] == "commit"
    statements = [op for op in operations if isinstance(op, tuple)]
    marker = next(op for op in statements if "flush_batches" in op[0] and "INSERT" in op[0])
    assert "ON CONFLICT" in marker[0] and marker[1][0] == UUID(int=1)
    aggregate = next(op for op in statements if "INSERT INTO api_usage.hourly" in op[0])
    assert "%s" in aggregate[0] and "provider_attempt_count" in aggregate[0]
    assert any(isinstance(value, datetime) and value.tzinfo == UTC for value in aggregate[1][0])


def test_ledger_runtime_configuration_fails_safely(monkeypatch):
    from services.usage_ledger import ledger_configuration
    monkeypatch.setenv("API_USAGE_LEDGER_REQUIRED", "true")
    monkeypatch.delenv("API_USAGE_DATABASE_URL", raising=False)
    with pytest.raises(RuntimeError, match="API usage ledger configuration"):
        ledger_configuration()
    monkeypatch.setenv("API_USAGE_LEDGER_REQUIRED", "malformed")
    with pytest.raises(RuntimeError):
        ledger_configuration()


def test_background_flush_and_shutdown_are_bounded():
    from services.usage_ledger import UsageFlusher
    usage, store = UsageAggregator(), Store()
    usage.observe(capability="places", event="physical_calls")
    writer = UsageFlusher(usage, store)
    writer.start()
    assert writer.stop(timeout=2) is True
    assert sum(row["provider_attempt_count"] for row in store.rows) == 1


def test_protected_usage_summary_has_no_public_identity_endpoint(monkeypatch):
    from backend.api_main import app
    from fastapi.testclient import TestClient
    monkeypatch.setenv("METRICS_SCRAPE_TOKEN", "a" * 32)
    client = TestClient(app)
    assert client.get("/provider-status").status_code == 404
    assert client.get("/metrics").status_code == 404
    response = client.get("/provider-status", headers={"X-Metrics-Scrape-Token": "a" * 32})
    assert response.status_code == 200
    assert response.json()["controls"]["fleet_quota_enforced"] is False
    assert response.json()["usage"]["rows"] == []


def test_accounting_path_is_fast_and_never_calls_store():
    usage = UsageAggregator()
    started = time.perf_counter()
    for _ in range(10000):
        usage.observe(capability="places", event="physical_calls", provider="google_places")
    elapsed = time.perf_counter() - started
    assert usage.summary()["totals"]["provider_attempt_count"] == 10000
    assert elapsed < 2.0


def test_required_startup_checks_write_permissions_not_only_reads():
    from services.usage_ledger import PostgresUsageStore
    class Connection:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        @contextmanager
        def transaction(self): yield
        def execute(self, query, params=None):
            if query.startswith("INSERT"):
                raise PermissionError("denied")
            return self
        def fetchone(self): return None
    store = PostgresUsageStore("postgresql://local.test/disposable", connection_factory=lambda _: Connection())
    with pytest.raises(PermissionError):
        store.check()


def test_expired_retry_batch_counts_newer_rows_abandoned_with_it():
    from services.usage_ledger import UsageFlusher
    now = [3600.0]
    usage, store = UsageAggregator(wall_clock=lambda: now[0]), Store()
    usage.observe(capability="places", event="physical_calls")
    now[0] = 86400.0
    usage.observe(capability="routes", event="physical_calls", count=10)
    writer = UsageFlusher(usage, store, wall_clock=lambda: now[0])
    store.fail = True
    writer.flush_once()
    now[0] = 30 * 86400 + 7200
    assert writer.flush_once() is True
    assert usage.summary()["accounting"]["expired_observations"] == 11
    assert not writer.pending_rows


def test_new_batch_near_hour_boundary_is_not_immediately_expired():
    from services.usage_ledger import UsageFlusher
    now = [3599.0]
    usage, store = UsageAggregator(wall_clock=lambda: now[0]), Store()
    usage.observe(capability="places", event="physical_calls")
    now[0] = 3601.0
    writer = UsageFlusher(usage, store, wall_clock=lambda: now[0])
    assert writer.flush_once() is True
    assert sum(row["provider_attempt_count"] for row in store.rows) == 1


def test_saturated_cardinality_accounting_does_not_scan_every_row_per_event():
    from uuid import UUID
    usage = UsageAggregator(wall_clock=lambda: 0)
    for i in range(4096):
        usage.observe(capability="places", event="physical_calls", principal_class="authenticated", principal_id=str(UUID(int=i)))
    started = time.perf_counter()
    for _ in range(10000):
        usage.observe(capability="places", event="physical_calls", principal_class="authenticated", principal_id="00000000-0000-0000-0000-000000000000")
    assert time.perf_counter() - started < 2.0
    assert usage.summary()["totals"]["provider_attempt_count"] == 14096


@pytest.mark.external_database
def test_disposable_postgres_ledger_idempotency_retention_and_denied_clients():
    import os
    from pathlib import Path
    from urllib.parse import urlsplit
    from uuid import UUID
    from services.usage_ledger import PostgresUsageStore
    target = os.getenv("API_USAGE_TEST_POSTGRES_URL", "")
    if not target or os.getenv("API_USAGE_TEST_DISPOSABLE") != "1":
        pytest.skip("Dedicated disposable usage PostgreSQL is not configured")
    parsed = urlsplit(target)
    if parsed.hostname not in {"127.0.0.1", "localhost"} or not parsed.path.lstrip("/").startswith("api_usage_test"):
        pytest.fail("Unsafe usage PostgreSQL test target")
    import psycopg
    with psycopg.connect(target) as connection:
        for role in ("anon", "authenticated", "service_role"):
            if not connection.execute("SELECT 1 FROM pg_roles WHERE rolname=%s", (role,)).fetchone():
                connection.execute(f"CREATE ROLE {role} NOLOGIN")
        if not connection.execute("SELECT 1 FROM pg_namespace WHERE nspname='api_usage'").fetchone():
            connection.execute(Path("database/migrations/021_api_usage_quota_ledger.sql").read_text(encoding="utf-8"))
        if not connection.execute("SELECT 1 FROM pg_roles WHERE rolname='usage_test_read_only'").fetchone():
            connection.execute("CREATE ROLE usage_test_read_only NOLOGIN")
        connection.execute("GRANT USAGE ON SCHEMA api_usage TO usage_test_read_only")
        connection.execute("GRANT SELECT ON api_usage.hourly,api_usage.flush_batches TO usage_test_read_only")
    def writer_connection(_):
        connection = psycopg.connect(target)
        connection.execute("SET ROLE proptech_usage_writer")
        connection.execute("SET TIME ZONE 'Asia/Kolkata'")
        connection.commit()
        return connection
    store = PostgresUsageStore(target, connection_factory=writer_connection)
    store.check()
    def read_only_connection(_):
        connection = psycopg.connect(target)
        connection.execute("SET ROLE usage_test_read_only")
        connection.commit()
        return connection
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        PostgresUsageStore(target, connection_factory=read_only_connection).check()
    usage = UsageAggregator()
    usage.observe(capability="places", provider="google_places", event="physical_calls", count=2, principal_class="authenticated", principal_id=str(UUID(int=1)))
    rows = usage.take_pending()
    store.write_batch(UUID(int=1), rows)
    store.write_batch(UUID(int=1), rows)
    summary = store.summary(principal_id=UUID(int=1))
    assert summary["rows"][0]["provider_attempt_count"] == 2
    assert not store.summary(principal_id=UUID(int=2))["rows"]
    with psycopg.connect(target) as connection:
        connection.execute("INSERT INTO api_usage.flush_batches (batch_id,created_at) VALUES (%s,CURRENT_TIMESTAMP - INTERVAL '32 days')", (UUID(int=9),))
    store.write_batch(UUID(int=2), [])
    with psycopg.connect(target) as connection:
        assert connection.execute("SELECT COUNT(*) FROM api_usage.flush_batches WHERE batch_id=%s", (UUID(int=9),)).fetchone()[0] == 0
        assert connection.execute("SELECT relrowsecurity,relforcerowsecurity FROM pg_class WHERE oid='api_usage.hourly'::regclass").fetchone() == (True, True)
        for role in ("anon", "authenticated", "service_role"):
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                with connection.transaction():
                    connection.execute(f"SET LOCAL ROLE {role}")
                    connection.execute("SELECT * FROM api_usage.hourly")
        with connection.transaction():
            connection.execute("SET LOCAL ROLE proptech_usage_reader")
            assert connection.execute("SELECT SUM(provider_attempt_count) FROM api_usage.hourly WHERE principal_class='authenticated' AND principal_id=%s", (str(UUID(int=1)),)).fetchone()[0] == 2
        with pytest.raises(psycopg.errors.CheckViolation):
            with connection.transaction():
                connection.execute("SET LOCAL ROLE proptech_usage_writer")
                connection.execute("UPDATE api_usage.hourly SET route_class='PRIVATE_ADDRESS?jwt=secret'")
        with connection.transaction():
            connection.execute("SET LOCAL ROLE proptech_usage_writer")
            connection.execute("SET LOCAL TIME ZONE 'Asia/Kolkata'")
            connection.execute("UPDATE api_usage.hourly SET requests=requests")
