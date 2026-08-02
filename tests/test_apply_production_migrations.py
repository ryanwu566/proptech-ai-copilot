from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path

from scripts import apply_production_migrations as migration_runner


ROOT = Path(__file__).resolve().parents[1]


class _Result:
    def __init__(self, rows: list[tuple[object, ...]]) -> None:
        self._rows = rows

    def fetchone(self) -> tuple[object, ...] | None:
        return self._rows[0] if self._rows else None

    def fetchall(self) -> list[tuple[object, ...]]:
        return self._rows


class _FakeConnection:
    def __init__(self, *, ledger: dict[str, str] | None = None, fail_on: str | None = None) -> None:
        self.ledger = dict(ledger or {})
        self.fail_on = fail_on
        self.sql: list[str] = []
        self.schema_versions: dict[str, str] = {}
        self.transaction_committed = False
        self.transaction_rolled_back = False
        self._ledger_snapshot: dict[str, str] | None = None

    def __enter__(self) -> "_FakeConnection":
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> bool:
        return False

    @contextmanager
    def transaction(self):
        self._ledger_snapshot = dict(self.ledger)
        try:
            yield
        except Exception:
            self.ledger = self._ledger_snapshot
            self.transaction_rolled_back = True
            raise
        else:
            self.transaction_committed = True

    def execute(self, statement: str, params: tuple[object, ...] | None = None) -> _Result:
        normalized = " ".join(statement.lower().split())
        self.sql.append(normalized)
        if self.fail_on and self.fail_on in normalized:
            raise RuntimeError("synthetic database failure")
        if normalized.startswith("select checksum from schema_migration_ledger"):
            migration_id = str(params[0])
            checksum = self.ledger.get(migration_id)
            return _Result([] if checksum is None else [(checksum,)])
        if normalized.startswith("select column_name from information_schema.columns"):
            return _Result([(column,) for column in {"migration_id", "schema_version", "applied_at", "release_version", "checksum"}])
        if normalized.startswith("select constraint_name from information_schema.table_constraints"):
            return _Result([("schema_migration_ledger_pkey",)])
        if normalized.startswith("insert into schema_migration_ledger"):
            assert params is not None
            self.schema_versions[str(params[0])] = str(params[1])
            self.ledger[str(params[0])] = str(params[3])
            return _Result([])
        if normalized.startswith("select table_name"):
            return _Result([(table,) for table in migration_runner.REQUIRED_TABLES])
        if normalized.startswith("select indexname"):
            return _Result([(index,) for index in migration_runner.REQUIRED_INDEXES])
        if normalized.startswith("select count(*) from information_schema.table_constraints"):
            return _Result([(4,)])
        return _Result([])


def _run(monkeypatch, connection: _FakeConnection) -> dict[str, object]:
    monkeypatch.setattr(migration_runner, "connect", lambda database_url: connection)
    return migration_runner.apply("postgresql://synthetic", release_version="test-release")


def test_empty_database_bootstraps_ledger_before_recording_migrations(monkeypatch) -> None:
    connection = _FakeConnection()

    result = _run(monkeypatch, connection)

    assert result["status"] == "pass"
    assert set(connection.ledger) == {path.stem for path in migration_runner.MIGRATIONS}
    first_insert = next(index for index, sql in enumerate(connection.sql) if sql.startswith("insert into schema_migration_ledger"))
    assert any(
        index < first_insert and "create table if not exists schema_migration_ledger" in sql
        for index, sql in enumerate(connection.sql)
    )
    assert not any(sql == "begin" for sql in connection.sql)
    assert connection.transaction_committed is True


def test_rerunning_migrations_is_idempotent_and_preserves_checksums(monkeypatch) -> None:
    connection = _FakeConnection()

    first = _run(monkeypatch, connection)
    statement_count = len(connection.sql)
    second = _run(monkeypatch, connection)

    assert first["status"] == "pass"
    assert second["status"] == "pass"
    assert len(connection.sql) < statement_count * 2
    assert set(connection.ledger) == {path.stem for path in migration_runner.MIGRATIONS}


def test_migration_schema_versions_follow_file_numbers(monkeypatch) -> None:
    connection = _FakeConnection()

    result = _run(monkeypatch, connection)

    assert result["status"] == "pass"
    assert connection.schema_versions["008_add_official_market_pipeline"] == "schema-008"
    assert connection.schema_versions["009_separate_official_market_region_coverage"] == "schema-009"


def test_checksum_drift_fails_without_applying_other_migrations(monkeypatch) -> None:
    first_migration = migration_runner.MIGRATIONS[0].stem
    connection = _FakeConnection(ledger={first_migration: "unexpected-checksum"})

    result = _run(monkeypatch, connection)

    assert result == {"status": "unavailable", "reason": "migration_checksum_drift"}
    assert connection.transaction_rolled_back is True
    assert set(connection.ledger) == {first_migration}


def test_failed_migration_rolls_back_ledger_records(monkeypatch) -> None:
    connection = _FakeConnection(fail_on="create table if not exists official_market_releases")

    result = _run(monkeypatch, connection)

    assert result == {"status": "unavailable", "reason": "database_migration_unavailable"}
    assert connection.transaction_rolled_back is True
    assert connection.ledger == {}


def test_legacy_and_official_market_coverage_schemas_are_distinct() -> None:
    legacy = (ROOT / "database/migrations/003_add_market_region_coverage.sql").read_text(encoding="utf-8")
    published = (ROOT / "database/migrations/008_add_official_market_pipeline.sql").read_text(encoding="utf-8")
    forward = (ROOT / "database/migrations/009_separate_official_market_region_coverage.sql").read_text(encoding="utf-8")

    assert "create table if not exists market_region_coverage (" in legacy
    assert "valid_market_candidate_count" in legacy
    assert "create table if not exists market_region_coverage (" in published
    assert "create table if not exists official_market_region_coverage (" in forward
    assert "release_id text not null references official_market_releases" in forward
    assert "create table if not exists market_region_coverage (" not in forward
    assert "idx_official_market_region_coverage_region_period" in forward
    assert migration_runner.MIGRATIONS[-1].name == "009_separate_official_market_region_coverage.sql"
    assert "official_market_region_coverage" in migration_runner.REQUIRED_TABLES
