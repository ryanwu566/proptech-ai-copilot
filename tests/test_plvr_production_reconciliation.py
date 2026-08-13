"""Read-only snapshot and row-level reconciliation contracts."""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator, Mapping, Sequence

import psycopg
import pytest

from services.plvr_clean_shadow_rebuild import _create_shadow_schema
from services.plvr_import_service import OFFICIAL_SOURCE, build_dedupe_key
from services.plvr_production_reconciliation import (
    CleanBucket,
    ProductionBucket,
    ReadOnlyPostgresProductionSource,
    ReconciliationError,
    _PostgresSnapshotStream,
    _assert_production_select,
    _canonical_business_fact_hash,
    _production_fact_hash,
    capture_production_snapshot,
    reconcile_snapshots,
)
from scripts.reconcile_plvr_shadow_with_production import main as reconciliation_main


class FakeStream:
    snapshot_at = "2026-08-13T00:00:00+00:00"

    def __init__(
        self,
        pages: Sequence[Sequence[Mapping[str, Any]]],
        *,
        expected_count: int | None = None,
        fail_after_pages: int | None = None,
    ) -> None:
        self.pages = pages
        self.expected_count = (
            sum(len(page) for page in pages) if expected_count is None else expected_count
        )
        self.fail_after_pages = fail_after_pages
        self.closed = False

    def __iter__(self) -> Iterator[Sequence[Mapping[str, Any]]]:
        for index, page in enumerate(self.pages):
            if self.fail_after_pages is not None and index >= self.fail_after_pages:
                raise OSError("simulated snapshot interruption")
            yield page

    def close(self) -> None:
        self.closed = True


class FakeSource:
    def __init__(self, streams: Sequence[FakeStream]) -> None:
        self.streams = list(streams)
        self.open_count = 0

    def open_snapshot(self, *, page_size: int) -> FakeStream:
        assert 1 <= page_size <= 10_000
        stream = self.streams[self.open_count]
        self.open_count += 1
        return stream


def _production_row(stable_id: int, **overrides: Any) -> dict[str, Any]:
    row: dict[str, Any] = {
        "id": stable_id,
        "transaction_period": "2025-01",
        "city": "臺北市",
        "district": "中正區",
        "road": "忠孝東路",
        "address_text": "臺北市中正區忠孝東路1號",
        "building_type": "住宅大樓",
        "area_ping": 30.0,
        "building_age_years": 10.0,
        "floor": 8,
        "total_floor": 15,
        "unit_price_per_ping": 80.0,
        "total_price": 2400.0,
        "source": OFFICIAL_SOURCE,
        "dedupe_key": f"unmatched-{stable_id}",
        "imported_at": "2026-08-11T00:00:00+00:00",
    }
    row.update(overrides)
    return row


def _clean_row(serial: str, **overrides: Any) -> dict[str, Any]:
    facts = _production_row(0, dedupe_key="")
    facts.update(overrides)
    official_id = str(overrides.get("official_transaction_id") or serial)
    return {
        "artifact_id": str(overrides.get("artifact_id") or "moi-plvr-sale-season-114S4"),
        "artifact_sequence": int(overrides.get("artifact_sequence") or 1),
        "artifact_sha256": "a" * 64,
        "artifact_filename": "season-114S4.zip",
        "source_filename": "a_lvr_land_a.csv",
        "source_row_number": 3,
        "source_identity": f"source-{serial}",
        "source_row_hash": f"row-{serial}",
        "source_agency": "Ministry of the Interior",
        "official_transaction_id": official_id,
        "official_transfer_id": "",
        "raw_transaction_date": "1140105",
        "transaction_period": facts["transaction_period"],
        "city": facts["city"],
        "district": facts["district"],
        "geographic_unit_kind": "district",
        "road": facts["road"],
        "address_text": facts["address_text"],
        "building_type": facts["building_type"],
        "area_ping": facts["area_ping"],
        "building_age_years": facts["building_age_years"],
        "floor": facts["floor"],
        "total_floor": facts["total_floor"],
        "unit_price_per_ping": facts["unit_price_per_ping"],
        "total_price": facts["total_price"],
        "source": OFFICIAL_SOURCE,
        "business_dedupe_key": build_dedupe_key(facts, official_id),
        "business_fact_hash": _canonical_business_fact_hash(
            facts, str(facts["city"]), str(facts["district"])
        ),
        "production_fact_hash": _production_fact_hash(facts),
        "revision_anchor_hash": f"anchor-{serial}",
        "normalizer_version": "test-normalizer",
        "dedupe_algorithm_version": "test-dedupe",
        "normalized_at": "2026-08-13T00:00:00+00:00",
    }


def _insert_mapping(
    connection: sqlite3.Connection, table: str, values: Mapping[str, Any]
) -> None:
    columns = tuple(values)
    placeholders = ", ".join("?" for _ in columns)
    connection.execute(
        f"insert into {table} ({', '.join(columns)}) values ({placeholders})",
        tuple(values[column] for column in columns),
    )


def _shadow(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    connection = sqlite3.connect(path)
    try:
        _create_shadow_schema(connection)
        for row in rows:
            _insert_mapping(connection, "shadow_transactions", row)
        connection.commit()
    finally:
        connection.close()


def _snapshot(tmp_path: Path, rows: Sequence[Mapping[str, Any]]) -> Path:
    target = tmp_path / "production-snapshot.sqlite3"
    pages = [rows[index : index + 2] for index in range(0, len(rows), 2)]
    capture_production_snapshot(
        FakeSource([FakeStream(pages)]),
        target,
        allowed_root=tmp_path,
        main_sha="main-sha",
        clean_manifest_sha256="manifest-sha",
        page_size=2,
    )
    return target


def test_snapshot_uses_stable_key_pages_without_duplicates_or_skips(tmp_path: Path) -> None:
    rows = [_production_row(index) for index in (3, 8, 11, 20, 21)]
    stream = FakeStream((rows[:2], rows[2:4], rows[4:]))
    target = tmp_path / "snapshot.sqlite3"

    metadata = capture_production_snapshot(
        FakeSource([stream]),
        target,
        allowed_root=tmp_path,
        main_sha="main-sha",
        clean_manifest_sha256="manifest-sha",
        page_size=2,
    )

    connection = sqlite3.connect(target)
    try:
        keys = [row[0] for row in connection.execute("select stable_id from snapshot_transactions order by stable_id")]
    finally:
        connection.close()
    assert keys == [3, 8, 11, 20, 21]
    assert metadata.production_total_count == 5
    assert metadata.first_stable_key == 3
    assert metadata.last_stable_key == 21
    assert metadata.page_count == 3
    assert stream.closed is True


def test_snapshot_rejects_unsorted_or_count_mismatched_pages(tmp_path: Path) -> None:
    duplicate = FakeStream(([_production_row(1), _production_row(1)],))
    with pytest.raises(ReconciliationError, match="production_snapshot_unavailable"):
        capture_production_snapshot(
            FakeSource([duplicate]),
            tmp_path / "duplicate.sqlite3",
            allowed_root=tmp_path,
            main_sha="main-sha",
            clean_manifest_sha256="manifest-sha",
            max_attempts=1,
        )

    mismatch = FakeStream(([_production_row(1)],), expected_count=2)
    with pytest.raises(ReconciliationError, match="production_snapshot_unavailable"):
        capture_production_snapshot(
            FakeSource([mismatch]),
            tmp_path / "mismatch.sqlite3",
            allowed_root=tmp_path,
            main_sha="main-sha",
            clean_manifest_sha256="manifest-sha",
            max_attempts=1,
        )


def test_snapshot_retry_restarts_and_preserves_deterministic_hash(tmp_path: Path) -> None:
    rows = [_production_row(index) for index in (1, 2, 3)]
    interrupted = FakeStream((rows[:1], rows[1:]), fail_after_pages=1)
    recovered = FakeStream((rows[:1], rows[1:]))
    source = FakeSource([interrupted, recovered])

    retried = capture_production_snapshot(
        source,
        tmp_path / "retried.sqlite3",
        allowed_root=tmp_path,
        main_sha="main-sha",
        clean_manifest_sha256="manifest-sha",
    )
    direct = capture_production_snapshot(
        FakeSource([FakeStream((rows[:1], rows[1:]))]),
        tmp_path / "direct.sqlite3",
        allowed_root=tmp_path,
        main_sha="main-sha",
        clean_manifest_sha256="manifest-sha",
    )

    assert source.open_count == 2
    assert interrupted.closed is True
    assert recovered.closed is True
    assert retried.snapshot_sha256 == direct.snapshot_sha256


def test_postgres_stream_enforces_read_only_transaction_and_closes_resources(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    page = [_production_row(1)]

    class Cursor:
        def __init__(self) -> None:
            self.sql: list[str] = []
            self.current: list[dict[str, Any]] = []
            self.closed = False

        def execute(self, sql: str, params: Sequence[Any] | None = None) -> None:
            self.sql.append(" ".join(sql.split()).lower())
            if "from real_price_transactions" in sql and "count(*)" not in sql:
                self.current = page if int(params[1]) < 1 else []

        def fetchone(self) -> dict[str, Any]:
            return {
                "count": 1,
                "transaction_timestamp": datetime(2026, 8, 13, tzinfo=UTC),
            }

        def fetchall(self) -> list[dict[str, Any]]:
            return self.current

        def close(self) -> None:
            self.closed = True

    class Connection:
        def __init__(self) -> None:
            self.read_only = False
            self.closed = False
            self.cursors: list[Cursor] = []

        def cursor(self, **_kwargs: Any) -> Cursor:
            cursor = Cursor()
            self.cursors.append(cursor)
            return cursor

        def close(self) -> None:
            self.closed = True

    connection = Connection()
    connect_options: dict[str, Any] = {}

    def connect(_url: str, **kwargs: Any) -> Connection:
        connect_options.update(kwargs)
        return connection

    monkeypatch.setattr(psycopg, "connect", connect)
    stream = _PostgresSnapshotStream("not-output", page_size=10)

    assert [row["id"] for rows in stream for row in rows] == [1]
    stream.close()
    assert connection.read_only is True
    assert "default_transaction_read_only=on" in connect_options["options"]
    assert connection.cursors[0].sql[0] == "set transaction isolation level repeatable read, read only"
    assert all(cursor.closed for cursor in connection.cursors)
    assert len(connection.cursors) == 3
    assert connection.closed is True


def test_postgres_stream_closes_connection_when_initialization_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Cursor:
        closed = False

        def execute(self, _sql: str, _params: Sequence[Any] | None = None) -> None:
            raise RuntimeError("simulated read-only setup failure")

        def close(self) -> None:
            self.closed = True

    class Connection:
        read_only = False
        closed = False
        cursor_instance = Cursor()

        def cursor(self, **_kwargs: Any) -> Cursor:
            return self.cursor_instance

        def close(self) -> None:
            self.closed = True

    connection = Connection()
    monkeypatch.setattr(psycopg, "connect", lambda *_args, **_kwargs: connection)

    with pytest.raises(RuntimeError, match="simulated read-only setup failure"):
        _PostgresSnapshotStream("not-output", page_size=10)

    assert connection.cursor_instance.closed is True
    assert connection.closed is True


def test_production_sql_guard_rejects_every_write_class() -> None:
    _assert_production_select("select id from real_price_transactions")
    for statement in (
        "update real_price_transactions set city = 'x'",
        "delete from real_price_transactions",
        "insert into real_price_transactions default values",
        "create table replacement(id integer)",
        "alter table real_price_transactions add column x integer",
        "drop table real_price_transactions",
    ):
        with pytest.raises(ReconciliationError, match="production_query_not_select_only"):
            _assert_production_select(statement)


def test_row_level_reconciliation_classifies_strict_evidence_and_keeps_summary_safe(
    tmp_path: Path,
) -> None:
    clean_match = _clean_row("MATCH")
    clean_corrupt = _clean_row("CORRUPT", road="仁愛路", address_text="臺北市中正區仁愛路1號")
    clean_probable = _clean_row("PROBABLE", road="信義路", address_text="臺北市中正區信義路1號")
    clean_conflict_a = _clean_row("CONFLICT-A", road="重慶南路", address_text="臺北市中正區重慶南路1號")
    clean_conflict_b = {
        **_clean_row("CONFLICT-B", road="重慶南路", address_text="臺北市中正區重慶南路1號"),
        "source_identity": clean_conflict_a["source_identity"],
        "business_dedupe_key": clean_conflict_a["business_dedupe_key"],
    }
    clean_missing = _clean_row("MISSING", road="杭州南路", address_text="臺北市中正區杭州南路1號")
    clean_cross_region = _clean_row(
        "CROSS-REGION",
        city="新北市",
        district="板橋區",
        road="共同路",
        address_text="共同路1號",
    )
    clean_future = _clean_row(
        "FUTURE",
        transaction_period="2026-10",
        road="青島東路",
        address_text="臺北市中正區青島東路1號",
        artifact_id="moi-plvr-sale-season-115S1",
    )
    clean_source_conflict = _clean_row(
        "SOURCE-CONFLICT", road="館前路", address_text="臺北市中正區館前路1號"
    )
    shadow_path = tmp_path / "shadow.sqlite3"
    _shadow(
        shadow_path,
        (
            clean_match,
            clean_corrupt,
            clean_probable,
            clean_missing,
            clean_cross_region,
        ),
    )
    shadow_connection = sqlite3.connect(shadow_path)
    try:
        _insert_mapping(
            shadow_connection,
            "shadow_forensic_transactions",
            {**clean_future, "forensic_reason": "future_transaction_period"},
        )
        _insert_mapping(
            shadow_connection, "shadow_candidate_transactions", clean_source_conflict
        )
        _insert_mapping(
            shadow_connection, "shadow_candidate_transactions", clean_conflict_a
        )
        _insert_mapping(
            shadow_connection, "shadow_candidate_transactions", clean_conflict_b
        )
        _insert_mapping(
            shadow_connection,
            "shadow_source_conflicts",
            {
                "source_identity": clean_source_conflict["source_identity"],
                "conflicting_fact_count": 2,
                "candidate_row_count": 2,
                "revision_anchor_count": 2,
                "resolution_status": "UNRESOLVED",
            },
        )
        _insert_mapping(
            shadow_connection,
            "shadow_source_conflicts",
            {
                "source_identity": clean_conflict_a["source_identity"],
                "conflicting_fact_count": 2,
                "candidate_row_count": 2,
                "revision_anchor_count": 2,
                "resolution_status": "UNRESOLVED",
            },
        )
        shadow_connection.commit()
    finally:
        shadow_connection.close()

    exact = _production_row(1)
    exact["dedupe_key"] = clean_match["business_dedupe_key"]
    exact_duplicate = {**exact, "id": 2}
    corrupt = _production_row(
        3,
        city="錯誤縣市",
        district="中正區",
        road="仁愛路",
        address_text="臺北市中正區仁愛路1號",
    )
    corrupt["dedupe_key"] = build_dedupe_key(corrupt, "CORRUPT")
    probable = _production_row(
        4, road="信義路", address_text="臺北市中正區信義路1號"
    )
    conflict = _production_row(
        5, road="重慶南路", address_text="臺北市中正區重慶南路1號"
    )
    conflict["dedupe_key"] = clean_conflict_a["business_dedupe_key"]
    production_only = _production_row(
        6, road="羅斯福路", address_text="臺北市中正區羅斯福路1號"
    )
    future = _production_row(
        7,
        transaction_period="2026-10",
        road="青島東路",
        address_text="臺北市中正區青島東路1號",
    )
    future["dedupe_key"] = clean_future["business_dedupe_key"]
    source_conflict = _production_row(
        8, road="館前路", address_text="臺北市中正區館前路1號"
    )
    source_conflict["dedupe_key"] = clean_source_conflict["business_dedupe_key"]
    cross_region = _production_row(9, road="共同路", address_text="共同路1號")
    snapshot_path = _snapshot(
        tmp_path,
        (
            exact,
            exact_duplicate,
            corrupt,
            probable,
            conflict,
            production_only,
            future,
            source_conflict,
            cross_region,
        ),
    )
    reconciliation_path = tmp_path / "reconciliation.sqlite3"
    report = reconcile_snapshots(
        shadow_path,
        snapshot_path,
        reconciliation_path,
        allowed_root=tmp_path,
        coverage_report={
            "raw_calendar_coverage_percent": 91.67,
            "expected_official_coverage_percent": 94.29,
            "expected_release_ceiling": "2026-07",
            "matrix": [
                {"city": "臺北市", "period": "2025-01", "coverage_state": "COMPLETE"}
            ],
        },
        since="2023-09",
        expected_release_ceiling="2026-07",
        main_sha="main-sha",
        clean_manifest_sha256="manifest-sha",
    )

    assert report["production"] == {
        ProductionBucket.AUTHORITATIVE_MATCH.value: 1,
        ProductionBucket.GEOGRAPHY_CORRUPT_MATCH.value: 1,
        ProductionBucket.PROVABLE_DUPLICATE.value: 1,
        ProductionBucket.PROBABLE_DUPLICATE.value: 1,
        ProductionBucket.NOT_IN_CLEAN_SOURCE.value: 2,
        ProductionBucket.FUTURE_ANOMALY.value: 1,
        ProductionBucket.CONFLICTING.value: 2,
        ProductionBucket.UNCLASSIFIED.value: 0,
    }
    assert report["clean"][CleanBucket.DUPLICATED_IN_PROD.value] == 1
    assert report["clean"][CleanBucket.PRESENT_BUT_PROD_CORRUPT.value] == 1
    assert report["clean"][CleanBucket.MISSING_FROM_PROD.value] == 2
    assert report["clean"][CleanBucket.SOURCE_CONFLICT.value] == 3
    assert report["future_row"] == {
        "classification": "PROD_FUTURE_SOURCE_CONFIRMED",
        "production_match_count": 1,
        "clean_source_evidence_count": 1,
        "publishable_status": "excluded",
    }
    serialized = json.dumps(report, ensure_ascii=False)
    assert "忠孝東路" not in serialized
    assert "臺北市中正區" not in serialized
    assert "dedupe_key" not in serialized
    assert report["production_safety"] == {
        "mode": "SELECT_ONLY",
        "writes": 0,
        "migrations": 0,
        "rows_changed": 0,
    }
    connection = sqlite3.connect(reconciliation_path)
    try:
        evidence = {
            int(row[0]): (str(row[1]), str(row[2]), str(row[3]))
            for row in connection.execute(
                "select stable_id, bucket, detail, evidence_tier from production_classification"
            )
        }
    finally:
        connection.close()
    assert evidence[1] == (
        ProductionBucket.AUTHORITATIVE_MATCH.value,
        "official_dedupe_identity",
        "A",
    )
    assert evidence[2][0] == ProductionBucket.PROVABLE_DUPLICATE.value
    assert evidence[3] == (
        ProductionBucket.GEOGRAPHY_CORRUPT_MATCH.value,
        "official_identity_reconstructed",
        "B",
    )
    assert evidence[4] == (
        ProductionBucket.PROBABLE_DUPLICATE.value,
        "exact_business_facts_only",
        "C",
    )
    assert evidence[9] == (
        ProductionBucket.NOT_IN_CLEAN_SOURCE.value,
        "no_clean_match",
        "NONE",
    )


def test_production_source_requires_runtime_and_never_offers_write_mode() -> None:
    with pytest.raises(ReconciliationError, match="production_read_runtime_not_configured"):
        ReadOnlyPostgresProductionSource("")


def test_reconciliation_cli_rejects_write_mode_before_opening_inputs(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert reconciliation_main(["--production-access", "write"]) == 2
    assert capsys.readouterr().out.splitlines() == [
        "PLVR_RECONCILIATION_STATUS=blocked",
        "REASON_CODE=production_access_must_be_select_only",
    ]
