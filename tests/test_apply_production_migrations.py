from __future__ import annotations

from contextlib import contextmanager
import json
from pathlib import Path
import shutil

import pytest

from scripts import apply_production_migrations as migration_runner
from scripts import validate_postgres_migration as migration_validator
from scripts.migration_registry import (
    MIGRATION_DIRECTORY,
    REGISTRY_PATH,
    MigrationRegistryError,
    checksum,
    load_registry,
    next_safe_sequence,
)


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
            if "constraint_schema in" in normalized:
                return _Result(
                    [(name,) for name in migration_runner.REQUIRED_VNEXT_FOREIGN_KEYS]
                )
            return _Result([("schema_migration_ledger_pkey",)])
        if normalized.startswith("insert into schema_migration_ledger"):
            assert params is not None
            self.schema_versions[str(params[0])] = str(params[1])
            self.ledger[str(params[0])] = str(params[3])
            return _Result([])
        if normalized.startswith("select table_name"):
            return _Result([(table,) for table in migration_runner.REQUIRED_TABLES])
        if normalized.startswith("select table_schema, table_name"):
            return _Result(
                [tuple(table.split(".", 1)) for table in migration_runner.REQUIRED_VNEXT_TABLES]
            )
        if normalized.startswith("select indexname"):
            return _Result([(index,) for index in migration_runner.REQUIRED_INDEXES])
        if normalized.startswith("select schemaname, indexname"):
            return _Result(
                [tuple(index.split(".", 1)) for index in migration_runner.REQUIRED_VNEXT_INDEXES]
            )
        if normalized.startswith("select count(*) from information_schema.table_constraints"):
                return _Result([(69 if "constraint_schema in" in normalized else 4,)])
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


def test_registry_freezes_every_historical_migration_exactly_once() -> None:
    registrations = load_registry()
    actual_files = {path.name for path in MIGRATION_DIRECTORY.glob("*.sql")}

    assert len(registrations) == len(actual_files) == 18
    assert {item.filename for item in registrations} == actual_files
    assert len({item.logical_id for item in registrations}) == len(registrations)
    assert [item.registry_order for item in registrations] == list(range(1, 19))
    assert [item.filename for item in registrations][1:3] == [
        "002_add_market_direct_query_indexes.sql",
        "002_expand_valuation_import_runs.sql",
    ]


def test_registry_preserves_historical_checksums_and_migration_012() -> None:
    frozen = {item.filename: item.sha256 for item in load_registry()}

    assert frozen["001_add_dedupe_key_to_real_price_transactions.sql"] == (
        "2eb4a3e8652d3f18cac9c200d38b3bf350e77bd36aa103f8b76ecf4004143223"
    )
    assert frozen["011_add_plvr_compact_green_schema.sql"] == (
        "107ba18c7db124a40183dc048581f821c853499feca203f874152c5b0dab2af2"
    )
    assert frozen["012_security_rls_deny_by_default.sql"] == (
        "bb1551d4e7fda1d3c7df99e3fd64a53f7fb05a8dcfb7ec0049c18ae6c2dfa056"
    )
    assert all(checksum(item.path) == item.sha256 for item in load_registry())


def test_registry_detects_duplicate_logical_registration(tmp_path: Path) -> None:
    payload = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    payload["migrations"][1]["logical_id"] = payload["migrations"][0]["logical_id"]
    registry_path = tmp_path / "registry.json"
    registry_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(MigrationRegistryError) as error:
        load_registry(registry_path, MIGRATION_DIRECTORY, verify_files=False)

    assert error.value.reason == "migration_logical_registration_duplicate"


def test_registry_detects_checksum_drift(tmp_path: Path) -> None:
    migration_directory = tmp_path / "migrations"
    migration_directory.mkdir()
    for source in MIGRATION_DIRECTORY.glob("*.sql"):
        shutil.copyfile(source, migration_directory / source.name)
    drifted = migration_directory / "012_security_rls_deny_by_default.sql"
    drifted.write_text(drifted.read_text(encoding="utf-8") + "\n-- drift\n", encoding="utf-8")

    with pytest.raises(MigrationRegistryError) as error:
        load_registry(REGISTRY_PATH, migration_directory)

    assert error.value.reason == "migration_checksum_drift"


def test_registry_checksum_is_stable_across_checkout_line_endings(tmp_path: Path) -> None:
    lf = tmp_path / "lf.sql"
    crlf = tmp_path / "crlf.sql"
    lf.write_bytes(b"select 1;\nselect 2;\n")
    crlf.write_bytes(b"select 1;\r\nselect 2;\r\n")

    assert checksum(lf) == checksum(crlf)


def test_registry_allocates_next_slice_sequence_after_stage_1_slice_7() -> None:
    registrations = load_registry()

    assert next_safe_sequence(registrations) == 18
    assert sum(item.filename.startswith("013_") for item in registrations) == 1
    assert sum(item.filename.startswith("014_") for item in registrations) == 1
    assert sum(item.filename.startswith("015_") for item in registrations) == 1
    assert "011_add_plvr_compact_green_schema.sql" not in {
        path.name for path in migration_runner.MIGRATIONS
    }


def test_dry_run_reports_frozen_registry_and_next_allocation() -> None:
    result = migration_runner.apply(None, dry_run=True)

    assert result == {
        "status": "ready",
        "migration_count": 13,
        "registry_count": 18,
        "next_migration_sequence": "018",
        "mode": "dry_run",
    }


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
    assert connection.schema_versions["010_add_plvr_generation_schema"] == "schema-010"
    assert connection.schema_versions["013_vnext_workspace_case_foundation"] == "schema-013"
    assert connection.schema_versions["014_vnext_property_graph_evidence_foundation"] == "schema-014"
    assert connection.schema_versions["015_vnext_identity_resolution_candidates"] == "schema-015"
    assert connection.schema_versions["016_vnext_identity_confirmation_case_links"] == "schema-016"
    assert connection.schema_versions["017_vnext_legacy_saved_case_import"] == "schema-017"


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
    assert migration_runner.MIGRATIONS[-1].name == "017_vnext_legacy_saved_case_import.sql"
    assert any(path.name == "010_add_plvr_generation_schema.sql" for path in migration_runner.MIGRATIONS)
    assert "official_market_region_coverage" in migration_runner.REQUIRED_TABLES
    assert "plvr_dataset_generations" in migration_runner.REQUIRED_TABLES


def _statements(tmp_path: Path, sql: str) -> list[str]:
    path = tmp_path / "synthetic.sql"
    path.write_text(sql, encoding="utf-8")
    return migration_validator._statements(path)


def test_statement_splitter_keeps_untagged_dollar_quoted_block(tmp_path: Path) -> None:
    statements = _statements(
        tmp_path,
        """DO $$
BEGIN
    PERFORM 1;
    PERFORM 2;
END
$$;
CREATE TABLE example_table (id integer);
""",
    )

    assert len(statements) == 2
    assert "PERFORM 2;" in statements[0]
    assert statements[1].startswith("CREATE TABLE example_table")


def test_statement_splitter_keeps_tagged_dollar_quoted_block(tmp_path: Path) -> None:
    statements = _statements(
        tmp_path,
        """DO $migration$
BEGIN
    PERFORM 1;
END
$migration$;
""",
    )

    assert len(statements) == 1
    assert statements[0].startswith("DO $migration$")
    assert statements[0].endswith("$migration$")


def test_statement_splitter_ignores_semicolons_in_strings_and_escaped_quotes(tmp_path: Path) -> None:
    statements = _statements(
        tmp_path,
        "INSERT INTO examples (value) VALUES ('a;b'), ('it''s;valid');",
    )

    assert len(statements) == 1
    assert "it''s;valid" in statements[0]


def test_statement_splitter_ignores_semicolons_in_comments(tmp_path: Path) -> None:
    statements = _statements(
        tmp_path,
        """-- comment with a semicolon ;
CREATE TABLE comment_table (id integer);
/* block comment with a semicolon ; */
CREATE INDEX comment_index ON comment_table (id);
""",
    )

    assert len(statements) == 2
    assert statements[0].startswith("CREATE TABLE comment_table")
    assert statements[1].startswith("CREATE INDEX comment_index")


def test_migration_009_keeps_do_block_and_rename_as_one_statement() -> None:
    path = ROOT / "database/migrations/009_separate_official_market_region_coverage.sql"
    statements = migration_validator._statements(path)

    assert len(statements) == 3
    assert "alter table public.market_region_coverage rename to official_market_region_coverage" in statements[0].lower()
    assert not any(statement.strip().lower().startswith("alter table") for statement in statements[1:])


def test_all_registered_migrations_split_into_non_empty_statements() -> None:
    for path in migration_validator.MIGRATIONS:
        statements = migration_validator._statements(path)
        assert statements, path.name
        assert all(statement.strip() for statement in statements)
