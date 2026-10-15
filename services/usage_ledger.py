"""Optional PostgreSQL aggregate sink, outside request paths, with safe retries."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import os
import threading
import time
from urllib.parse import urlsplit
from uuid import UUID, uuid4

from services.api_usage import COUNTERS, UsageAggregator
from services.postgres_runtime import connect

RETENTION_SECONDS = 3600  # Never replay a batch beyond its two-hour marker TTL.
DIMENSIONS = ("bucket_start", "principal_class", "principal_id", "capability", "provider", "route_class", "status_class", "cache_state", "release_id")
_COLUMNS = (*DIMENSIONS, *COUNTERS)
_UPSERT = ("INSERT INTO api_usage.hourly (" + ",".join(_COLUMNS) + ") VALUES (" + ",".join(["%s"] * len(_COLUMNS)) + ") ON CONFLICT (" + ",".join(DIMENSIONS) + ") DO UPDATE SET " + ",".join(f"{name}=api_usage.hourly.{name}+EXCLUDED.{name}" for name in COUNTERS))


class _ProbeComplete(Exception):
    """Force rollback of a successful startup write probe."""


@dataclass(frozen=True)
class LedgerConfiguration:
    database_url: str
    required: bool
    flush_seconds: int


def ledger_configuration() -> LedgerConfiguration:
    raw = os.getenv("API_USAGE_LEDGER_REQUIRED", "false").strip().lower()
    if raw not in {"true", "false", "1", "0", "yes", "no", "on", "off", ""}:
        raise RuntimeError("Invalid API usage ledger configuration.")
    required = raw in {"true", "1", "yes", "on"}
    database_url = os.getenv("API_USAGE_DATABASE_URL", "").strip()
    try:
        interval = int(os.getenv("API_USAGE_FLUSH_SECONDS", "10"))
        parsed = urlsplit(database_url)
        if not 5 <= interval <= 60 or (required and not database_url):
            raise ValueError()
        if database_url and (parsed.scheme not in {"postgres", "postgresql"} or not parsed.hostname or not parsed.path.strip("/")):
            raise ValueError()
    except ValueError:
        raise RuntimeError("Invalid API usage ledger configuration.") from None
    return LedgerConfiguration(database_url, required, interval)


class PostgresUsageStore:
    def __init__(self, database_url, *, connection_factory=None):
        self.database_url = database_url
        self.connection_factory = connection_factory

    def _connect(self):
        return connect(self.database_url, connection_factory=self.connection_factory, connect_timeout=2)

    @staticmethod
    def _timeouts(connection):
        connection.execute("SET LOCAL TIME ZONE 'UTC'")
        connection.execute("SET LOCAL statement_timeout = '2000ms'")
        connection.execute("SET LOCAL lock_timeout = '500ms'")

    def check(self):
        with self._connect() as connection:
            try:
                with connection.transaction():
                    self._timeouts(connection)
                    connection.execute("SELECT bucket_start FROM api_usage.hourly LIMIT 1").fetchone()
                    # Exercise grants AND RLS for the real writer operations.
                    # Every change is rolled back, including an existing zero row.
                    bucket = datetime.fromtimestamp(int(time.time() // 3600) * 3600, UTC)
                    values = (bucket, "system", "", "metadata", "none", "internal", "other", "unknown", "unknown", *([0] * len(COUNTERS)))
                    connection.execute(_UPSERT, values)
                    connection.execute("DELETE FROM api_usage.hourly WHERE bucket_start=%s AND principal_class='system' AND principal_id='' AND capability='metadata' AND provider='none' AND route_class='internal' AND status_class='other' AND cache_state='unknown' AND release_id='unknown'", (bucket,))
                    token = uuid4()
                    connection.execute("INSERT INTO api_usage.flush_batches (batch_id) VALUES (%s) RETURNING batch_id", (token,)).fetchone()
                    connection.execute("DELETE FROM api_usage.flush_batches WHERE batch_id=%s", (token,))
                    raise _ProbeComplete()
            except _ProbeComplete:
                pass

    def write_batch(self, batch_id: UUID, rows):
        if len(rows) > 4096 or not isinstance(batch_id, UUID):
            raise ValueError("Invalid usage batch")
        with self._connect() as connection:
            with connection.transaction():
                self._timeouts(connection)
                marker = connection.execute("INSERT INTO api_usage.flush_batches (batch_id) VALUES (%s) ON CONFLICT (batch_id) DO NOTHING RETURNING batch_id", (batch_id,)).fetchone() if rows else None
                if marker is not None:
                    values = []
                    for row in rows:
                        values.append((datetime.fromtimestamp(row["bucket_start"], UTC), *(row[name] for name in _COLUMNS[1:])))
                    with connection.cursor() as cursor:
                        cursor.executemany(_UPSERT, values)
                # Bounded deletion work, including quiet periods. A maintenance
                # owner must catch up if expired rows exceed this per-flush pace.
                connection.execute("DELETE FROM api_usage.hourly WHERE ctid IN (SELECT ctid FROM api_usage.hourly WHERE bucket_start < CURRENT_TIMESTAMP - INTERVAL '30 days' LIMIT 5000)")
                connection.execute("DELETE FROM api_usage.flush_batches WHERE batch_id IN (SELECT batch_id FROM api_usage.flush_batches WHERE created_at < CURRENT_TIMESTAMP - INTERVAL '2 hours' LIMIT 5000)")
                connection.execute("SELECT api_usage.prune()")

    def summary(self, *, hours=24, principal_id=None):
        """Server-only durable aggregation; callers must authorize Admin access."""
        if isinstance(hours, bool) or not isinstance(hours, int) or not 1 <= hours <= 24:
            raise ValueError("Usage summary window must be 1..24 hours")
        parameters = [hours]
        predicate = ""
        if principal_id is not None:
            principal_id = str(UUID(str(principal_id)))
            predicate = " AND principal_class = 'authenticated' AND principal_id = %s"
            parameters.append(principal_id)
        query = ("SELECT principal_class,capability,provider," + ",".join(f"SUM({name})" for name in COUNTERS) + " FROM api_usage.hourly WHERE bucket_start >= date_trunc('hour', CURRENT_TIMESTAMP) - (%s - 1) * INTERVAL '1 hour'" + predicate + " GROUP BY principal_class,capability,provider ORDER BY principal_class,capability,provider LIMIT 1000")
        with self._connect() as connection:
            with connection.transaction():
                self._timeouts(connection)
                result = connection.execute(query, tuple(parameters)).fetchall()
        return {"scope": "durable_aggregates", "window_hours": hours,
                "rows": [dict(zip(("principal_class", "capability", "provider", *COUNTERS), row)) for row in result],
                "fleet_quota_enforced": False, "unflushed_usage_included": False}


class UsageFlusher:
    def __init__(self, usage: UsageAggregator, store, *, interval=10, wall_clock=time.time):
        self.usage, self.store = usage, store
        self.interval = max(5, min(60, interval))
        self.wall_clock = wall_clock
        self.pending_rows = []
        self._batch_id = None
        self._batch_created_at = None
        self._flush_lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = None

    def flush_once(self):
        with self._flush_lock:
            if not self.pending_rows:
                self.pending_rows = self.usage.take_pending()
                self._batch_id = uuid4()
                self._batch_created_at = self.wall_clock()
            if self.wall_clock() - self._batch_created_at > RETENTION_SECONDS:
                self.usage.record_expired(sum(row["observations"] for row in self.pending_rows))
                # Never change the payload of a retry token. Abandon an expired
                # batch as a whole; it can no longer be reliably replayed.
                self.pending_rows = []
                self._batch_id = None
                self._batch_created_at = None
                return True
            try:
                # Empty batches also run bounded retention maintenance.
                self.store.write_batch(self._batch_id, self.pending_rows)
            except Exception:
                self.usage.writer_status("unavailable")
                return False
            self.pending_rows = []
            self._batch_id = None
            self._batch_created_at = None
            self.usage.writer_status("available")
            return True

    def start(self):
        if self._thread is not None:
            raise RuntimeError("Usage writer already started")
        self.usage.writer_status("configured")
        self._thread = threading.Thread(target=self._run, name="api-usage-flush", daemon=True)
        self._thread.start()

    def _run(self):
        while not self._stop.wait(self.interval):
            self.flush_once()
        # Drain the retained batch and at most one newly aggregated batch.
        if self.flush_once():
            self.flush_once()

    def stop(self, *, timeout=5):
        self._stop.set()
        if self._thread is not None:
            self._thread.join(max(0, min(5, timeout)))
            stopped = not self._thread.is_alive()
            if stopped:
                self.usage.writer_status("stopped")
            return stopped
        return True


def start_usage_ledger(usage):
    config = ledger_configuration()
    if not config.database_url:
        usage.writer_status("not_configured")
        return None
    store = PostgresUsageStore(config.database_url)
    try:
        store.check()
    except Exception:
        usage.writer_status("unavailable")
        if config.required:
            raise RuntimeError("Required API usage ledger is unavailable.") from None
    writer = UsageFlusher(usage, store, interval=config.flush_seconds)
    writer.start()
    return writer
