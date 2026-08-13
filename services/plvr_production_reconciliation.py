"""Bounded, read-only PLVR production-to-shadow reconciliation.

The production connection executes only a count and stable-key SELECT pages in
one repeatable-read, read-only transaction. Raw facts remain in an ignored local
SQLite snapshot; public summaries contain only counts and aggregate evidence.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC
from enum import StrEnum
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping, Protocol, Sequence

from services.plvr_coverage_closure import CoverageState
from services.plvr_data_integrity import normalized_storage_key
from services.plvr_import_service import OFFICIAL_SOURCE, build_dedupe_key
from services.taiwan_admin_registry import iter_taiwan_regions, normalize_market_region


SNAPSHOT_SCHEMA_VERSION = "plvr-production-readonly-snapshot-v1"
RECONCILIATION_SCHEMA_VERSION = "plvr-shadow-production-reconciliation-v1"
DEFAULT_PAGE_SIZE = 2_000
MAX_PAGE_SIZE = 10_000
FORBIDDEN_PRODUCTION_SQL = re.compile(
    r"\b(insert|update|delete|upsert|merge|truncate|drop|alter|create|grant|revoke|copy)\b",
    re.IGNORECASE,
)


class ProductionBucket(StrEnum):
    AUTHORITATIVE_MATCH = "PROD_AUTHORITATIVE_MATCH"
    GEOGRAPHY_CORRUPT_MATCH = "PROD_GEOGRAPHY_CORRUPT_MATCH"
    PROVABLE_DUPLICATE = "PROD_PROVABLE_DUPLICATE"
    PROBABLE_DUPLICATE = "PROD_PROBABLE_DUPLICATE"
    NOT_IN_CLEAN_SOURCE = "PROD_NOT_IN_CLEAN_SOURCE"
    FUTURE_ANOMALY = "PROD_FUTURE_ANOMALY"
    CONFLICTING = "PROD_CONFLICTING"
    UNCLASSIFIED = "PROD_UNCLASSIFIED"


class CleanBucket(StrEnum):
    PRESENT_CORRECTLY = "CLEAN_PRESENT_CORRECTLY"
    PRESENT_BUT_PROD_CORRUPT = "CLEAN_PRESENT_BUT_PROD_CORRUPT"
    MISSING_FROM_PROD = "CLEAN_MISSING_FROM_PROD"
    DUPLICATED_IN_PROD = "CLEAN_DUPLICATED_IN_PROD"
    SOURCE_CONFLICT = "CLEAN_SOURCE_CONFLICT"
    UNCLASSIFIED = "CLEAN_UNCLASSIFIED"


class ReconciliationError(RuntimeError):
    """Raised when the read-only or deterministic reconciliation contract fails."""


class SnapshotStream(Protocol):
    snapshot_at: str
    expected_count: int
    transaction_isolation: str
    transaction_read_only: str
    database_identified: bool
    user_identified: bool

    def __iter__(self) -> Iterator[Sequence[Mapping[str, Any]]]: ...

    def validate_stationary(self) -> int: ...

    def close(self) -> None: ...


class ProductionSource(Protocol):
    def open_snapshot(self, *, page_size: int) -> SnapshotStream: ...


@dataclass(frozen=True)
class SnapshotMetadata:
    snapshot_at: str
    production_total_count: int
    source_filter: str
    pagination_method: str
    first_stable_key: int | None
    last_stable_key: int | None
    page_count: int
    snapshot_sha256: str
    main_sha: str
    clean_manifest_sha256: str
    clean_shadow_sha256: str
    closing_production_count: int
    snapshot_stationary: bool
    transaction_isolation: str
    transaction_read_only: str
    database_identified: bool
    user_identified: bool


class _PostgresSnapshotStream:
    COUNT_SQL = """
    select count(*)::bigint as count, transaction_timestamp() as transaction_timestamp
    from real_price_transactions where source = %s
    """
    FINAL_COUNT_SQL = """
    select count(*)::bigint as count
    from real_price_transactions where source = %s
    """
    IDENTITY_SQL = """
    select current_database() is not null as database_identified,
           current_user is not null as user_identified
    """
    PAGE_SQL = """
    select id, transaction_period, city, district, road, address_text,
           building_type, area_ping, building_age_years, floor, total_floor,
           unit_price_per_ping, total_price, source, dedupe_key, imported_at
    from real_price_transactions
    where source = %s and id > %s
    order by id
    limit %s
    """

    def __init__(self, database_url: str, *, page_size: int) -> None:
        _assert_production_select(self.COUNT_SQL)
        _assert_production_select(self.FINAL_COUNT_SQL)
        _assert_production_select(self.IDENTITY_SQL)
        _assert_production_select(self.PAGE_SQL)
        import psycopg
        from psycopg.rows import dict_row

        self._connection = None
        self._cursor = None
        try:
            self._connection = psycopg.connect(
                database_url,
                connect_timeout=20,
                prepare_threshold=None,
                row_factory=dict_row,
                options="-c default_transaction_read_only=on -c statement_timeout=120000",
            )
            self._connection.read_only = True
            self._cursor = self._connection.cursor()
            self._cursor.execute("set transaction isolation level repeatable read, read only")
            self._cursor.execute("show transaction_read_only")
            self.transaction_read_only = str(
                self._cursor.fetchone()["transaction_read_only"]
            ).lower()
            if self.transaction_read_only != "on":
                raise ReconciliationError("production_transaction_not_read_only")
            self._cursor.execute("show transaction_isolation")
            self.transaction_isolation = str(
                self._cursor.fetchone()["transaction_isolation"]
            ).lower()
            if self.transaction_isolation != "repeatable read":
                raise ReconciliationError("production_transaction_not_repeatable_read")
            self._cursor.execute(self.IDENTITY_SQL)
            identity = self._cursor.fetchone()
            self.database_identified = bool(identity["database_identified"])
            self.user_identified = bool(identity["user_identified"])
            self._cursor.execute(self.COUNT_SQL, [OFFICIAL_SOURCE])
            row = self._cursor.fetchone()
            self.expected_count = int(row["count"])
            self.snapshot_at = row["transaction_timestamp"].astimezone(UTC).isoformat()
        except Exception:
            if self._cursor is not None:
                self._cursor.close()
            if self._connection is not None:
                self._connection.close()
            raise
        self._page_size = page_size
        self._last_id = 0
        self._closed = False

    def __iter__(self) -> Iterator[Sequence[Mapping[str, Any]]]:
        while True:
            page_cursor = self._connection.cursor(
                name=f"plvr_reconciliation_page_{self._last_id}"
            )
            try:
                page_cursor.execute(
                    self.PAGE_SQL, [OFFICIAL_SOURCE, self._last_id, self._page_size]
                )
                rows = page_cursor.fetchall()
            finally:
                page_cursor.close()
            if not rows:
                return
            first_id = int(rows[0]["id"])
            if first_id <= self._last_id:
                raise ReconciliationError("production_keyset_not_monotonic")
            previous = self._last_id
            for row in rows:
                stable_id = int(row["id"])
                if stable_id <= previous:
                    raise ReconciliationError("production_keyset_duplicate_or_unsorted")
                previous = stable_id
            self._last_id = previous
            yield rows

    def validate_stationary(self) -> int:
        self._cursor.execute(self.FINAL_COUNT_SQL, [OFFICIAL_SOURCE])
        return int(self._cursor.fetchone()["count"])

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            if self._cursor is not None:
                self._cursor.close()
        finally:
            if self._connection is not None:
                self._connection.close()


class ReadOnlyPostgresProductionSource:
    """Open a stable PostgreSQL snapshot with explicit fail-closed read-only mode."""

    def __init__(self, database_url: str) -> None:
        if not str(database_url or "").strip():
            raise ReconciliationError("production_read_runtime_not_configured")
        self._database_url = database_url

    def open_snapshot(self, *, page_size: int) -> SnapshotStream:
        _validate_page_size(page_size)
        return _PostgresSnapshotStream(self._database_url, page_size=page_size)


def capture_production_snapshot(
    source: ProductionSource,
    snapshot_path: Path,
    *,
    allowed_root: Path,
    main_sha: str,
    clean_manifest_sha256: str,
    clean_shadow_sha256: str = "",
    page_size: int = DEFAULT_PAGE_SIZE,
    max_attempts: int = 2,
) -> SnapshotMetadata:
    """Atomically capture one local snapshot, restarting after transient failure."""

    _validate_page_size(page_size)
    _assert_local_target(snapshot_path, allowed_root)
    if max_attempts < 1 or max_attempts > 3:
        raise ReconciliationError("invalid_snapshot_retry_limit")
    last_error: Exception | None = None
    for _attempt in range(max_attempts):
        temporary = snapshot_path.with_name(f"{snapshot_path.name}.building-{uuid.uuid4().hex}")
        stream: SnapshotStream | None = None
        try:
            temporary.parent.mkdir(parents=True, exist_ok=True)
            connection = sqlite3.connect(temporary)
            try:
                _create_snapshot_schema(connection)
                stream = source.open_snapshot(page_size=page_size)
                digest = hashlib.sha256()
                count = 0
                page_count = 0
                first_key: int | None = None
                last_key: int | None = None
                for page in stream:
                    if not page:
                        raise ReconciliationError("production_empty_page")
                    rows = [_snapshot_row(row) for row in page]
                    keys = [int(row[0]) for row in rows]
                    if first_key is None:
                        first_key = keys[0]
                    if last_key is not None and keys[0] <= last_key:
                        raise ReconciliationError("production_keyset_duplicate_or_unsorted")
                    if any(right <= left for left, right in zip(keys, keys[1:])):
                        raise ReconciliationError("production_keyset_duplicate_or_unsorted")
                    connection.executemany(
                        """
                        insert into snapshot_transactions values (
                            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                        )
                        """,
                        rows,
                    )
                    for row in rows:
                        digest.update(_canonical_json(list(row)).encode("utf-8"))
                        digest.update(b"\n")
                    count += len(rows)
                    page_count += 1
                    last_key = keys[-1]
                    connection.commit()
                if count != int(stream.expected_count):
                    raise ReconciliationError("production_snapshot_count_mismatch")
                closing_count = int(stream.validate_stationary())
                if closing_count != int(stream.expected_count):
                    raise ReconciliationError("SNAPSHOT_NON_STATIONARY")
                checksum = digest.hexdigest()
                metadata = SnapshotMetadata(
                    snapshot_at=stream.snapshot_at,
                    production_total_count=count,
                    source_filter=OFFICIAL_SOURCE,
                    pagination_method="stable_key_id_gt_last_id",
                    first_stable_key=first_key,
                    last_stable_key=last_key,
                    page_count=page_count,
                    snapshot_sha256=checksum,
                    main_sha=main_sha,
                    clean_manifest_sha256=clean_manifest_sha256,
                    clean_shadow_sha256=clean_shadow_sha256,
                    closing_production_count=closing_count,
                    snapshot_stationary=True,
                    transaction_isolation=stream.transaction_isolation,
                    transaction_read_only=stream.transaction_read_only,
                    database_identified=stream.database_identified,
                    user_identified=stream.user_identified,
                )
                connection.execute(
                    "insert into snapshot_metadata values (?, ?)",
                    ("schema_version", SNAPSHOT_SCHEMA_VERSION),
                )
                for key, value in asdict_without_none(metadata).items():
                    connection.execute(
                        "insert into snapshot_metadata values (?, ?)",
                        (key, _canonical_json(value)),
                    )
                connection.commit()
            finally:
                if stream is not None:
                    stream.close()
                connection.close()
            os.replace(temporary, snapshot_path)
            return metadata
        except Exception as error:
            last_error = error
            temporary.unlink(missing_ok=True)
            if isinstance(error, ReconciliationError) and str(error) in {
                "SNAPSHOT_NON_STATIONARY",
                "production_transaction_not_read_only",
                "production_transaction_not_repeatable_read",
            }:
                raise
    raise ReconciliationError("production_snapshot_unavailable") from last_error


def reconcile_snapshots(
    shadow_path: Path,
    snapshot_path: Path,
    reconciliation_path: Path,
    *,
    allowed_root: Path,
    coverage_report: Mapping[str, Any],
    since: str,
    expected_release_ceiling: str,
    main_sha: str,
    clean_manifest_sha256: str,
) -> dict[str, Any]:
    """Classify every local production and clean row without database writes."""

    _assert_local_target(reconciliation_path, allowed_root)
    if not shadow_path.is_file() or not snapshot_path.is_file():
        raise ReconciliationError("local_reconciliation_input_missing")
    temporary = reconciliation_path.with_name(
        f"{reconciliation_path.name}.building-{uuid.uuid4().hex}"
    )
    temporary.parent.mkdir(parents=True, exist_ok=True)
    try:
        output = sqlite3.connect(temporary)
        output.row_factory = sqlite3.Row
        shadow = _open_sqlite_readonly(shadow_path)
        production = _open_sqlite_readonly(snapshot_path)
        try:
            _create_reconciliation_schema(output)
            _index_clean_rows(shadow, output)
            output.commit()
            _classify_production_rows(
                production,
                output,
                coverage_report=coverage_report,
                since=since,
                expected_release_ceiling=expected_release_ceiling,
            )
            _mark_duplicate_topology(output)
            _classify_clean_rows(output)
            output.commit()
            report = _build_reconciliation_report(
                shadow,
                production,
                output,
                coverage_report=coverage_report,
                expected_release_ceiling=expected_release_ceiling,
                main_sha=main_sha,
                clean_manifest_sha256=clean_manifest_sha256,
            )
        finally:
            shadow.close()
            production.close()
            output.close()
        os.replace(temporary, reconciliation_path)
        return report
    finally:
        temporary.unlink(missing_ok=True)


def safe_reconciliation_artifacts(
    report: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    """Return commit-safe summaries without production row payloads."""

    summary = json.loads(_canonical_json(report))
    if "production_runtime" in summary:
        summary["production_runtime"] = {
            "database_status": (summary.get("production_runtime") or {}).get(
                "database_status"
            )
        }
    buckets = {
        "schema_version": "plvr-production-reconciliation-buckets-v1",
        "main_sha": report.get("main_sha"),
        "production_snapshot_sha256": (
            report.get("production_snapshot") or {}
        ).get("snapshot_sha256"),
        "matching_tiers": report.get("matching_tiers"),
        "production": report.get("production"),
        "production_bucket_evidence": report.get("production_bucket_evidence"),
        "clean": report.get("clean"),
        "conservation": report.get("conservation"),
        "invalid_geography_cohort": report.get("invalid_geography_cohort"),
        "legacy_geography_cohort": report.get("legacy_geography_cohort"),
        "legacy_duplicate_cohort": report.get("legacy_duplicate_cohort"),
        "duplicate_topology": report.get("duplicate_topology"),
        "production_only_analysis": report.get("production_only_analysis"),
        "clean_only_analysis": report.get("clean_only_analysis"),
        "future_row": report.get("future_row"),
    }
    aggregates = {
        "schema_version": "plvr-production-aggregate-reconciliation-v1",
        "main_sha": report.get("main_sha"),
        "production_snapshot_sha256": (
            report.get("production_snapshot") or {}
        ).get("snapshot_sha256"),
        "aggregate_reconciliation": report.get("aggregate_reconciliation"),
        "aggregate_delta_context": report.get("aggregate_delta_context"),
    }
    payloads = {
        "plvr_production_reconciliation_summary.json": summary,
        "plvr_production_reconciliation_buckets.json": buckets,
        "plvr_production_aggregate_reconciliation.json": aggregates,
    }
    serialized = _canonical_json(payloads).lower()
    for forbidden in (
        "database_url",
        "password",
        "raw production",
        "address_text",
        "full_address",
        "postgresql://",
    ):
        if forbidden in serialized:
            raise ReconciliationError("unsafe_reconciliation_artifact")
    return payloads


def reconciliation_gate(
    shadow_report: Mapping[str, Any],
    reconciliation: Mapping[str, Any],
) -> tuple[str, list[str]]:
    blockers: list[str] = []
    coverage = shadow_report.get("coverage") or {}
    snapshot = reconciliation.get("production_snapshot") or {}
    conservation = reconciliation.get("conservation") or {}
    production = reconciliation.get("production") or {}
    clean = reconciliation.get("clean") or {}
    safety = reconciliation.get("production_safety") or {}
    topology = reconciliation.get("duplicate_topology") or {}
    aggregates = reconciliation.get("aggregate_reconciliation") or {}
    future = reconciliation.get("future_row") or {}
    if not bool(snapshot.get("snapshot_stationary")):
        blockers.append("production_snapshot_not_stationary")
    if str(snapshot.get("transaction_read_only") or "").lower() != "on":
        blockers.append("production_transaction_not_read_only")
    if int(safety.get("writes") or 0) or int(safety.get("rows_changed") or 0):
        blockers.append("production_mutation_detected")
    if not bool(conservation.get("production_rows_conserved")):
        blockers.append("production_bucket_conservation_failed")
    if not bool(conservation.get("clean_rows_conserved")):
        blockers.append("clean_bucket_conservation_failed")
    if int(coverage.get("missing") or 0) > 0:
        blockers.append("expected_authoritative_coverage_incomplete")
    if int(shadow_report.get("source_identity_conflicts") or 0):
        blockers.append("source_identity_conflicts_unresolved")
    if int(production.get(ProductionBucket.CONFLICTING.value) or 0):
        blockers.append("production_conflicts_unresolved")
    if int(production.get(ProductionBucket.UNCLASSIFIED.value) or 0):
        blockers.append("production_rows_unclassified")
    if int((reconciliation.get("production_only_analysis") or {}).get("UNRESOLVED") or 0):
        blockers.append("production_only_rows_unresolved")
    if int((reconciliation.get("clean_only_analysis") or {}).get("UNRESOLVED") or 0):
        blockers.append("clean_only_rows_unresolved")
    if int(clean.get(CleanBucket.SOURCE_CONFLICT.value) or 0):
        blockers.append("clean_source_conflicts_unresolved")
    if int(clean.get(CleanBucket.UNCLASSIFIED.value) or 0):
        blockers.append("clean_rows_unclassified")
    if int(topology.get("duplicate_rows") or 0) > int(
        production.get(ProductionBucket.PROVABLE_DUPLICATE.value) or 0
    ):
        blockers.append("probable_duplicate_candidates_unresolved")
    if str(future.get("classification") or "") != "PROD_FUTURE_SOURCE_CONFIRMED":
        blockers.append("future_anomaly_identity_unresolved")
    if any(
        int(aggregates.get(key) or 0)
        for key in (
            "materially_changed_scopes",
            "production_only_scopes",
            "shadow_only_scopes",
        )
    ):
        blockers.append("aggregate_deltas_require_explanation")
    if int(
        (reconciliation.get("legacy_geography_cohort") or {}).get(
            "baseline_difference"
        )
        or 0
    ):
        blockers.append("historical_supporting_cohort_membership_not_reproducible")
    if int(
        (reconciliation.get("legacy_duplicate_cohort") or {}).get(
            "baseline_difference"
        )
        or 0
    ):
        blockers.append("historical_duplicate_cohort_membership_not_reproducible")
    if int((shadow_report.get("lineage") or {}).get("rows_missing_identity") or 0):
        blockers.append("shadow_lineage_incomplete")
    return (
        "NOT_READY_FOR_SHADOW_CUTOVER_DESIGN" if blockers else "READY_FOR_SHADOW_CUTOVER_DESIGN",
        blockers,
    )


def _create_snapshot_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        pragma journal_mode = delete;
        pragma synchronous = full;
        create table snapshot_transactions (
            stable_id integer primary key,
            transaction_period text not null,
            city text not null,
            district text not null,
            road text not null,
            address_text text not null,
            building_type text not null,
            area_ping real not null,
            building_age_years real not null,
            floor integer not null,
            total_floor integer,
            unit_price_per_ping real not null,
            total_price real not null,
            source text not null,
            dedupe_key text not null,
            imported_at text not null,
            address_fingerprint text not null,
            production_fact_hash text not null,
            canonical_business_fact_hash text not null,
            row_fingerprint text not null
        );
        create index idx_snapshot_dedupe_key on snapshot_transactions(dedupe_key);
        create index idx_snapshot_production_fact on snapshot_transactions(production_fact_hash);
        create index idx_snapshot_canonical_fact on snapshot_transactions(canonical_business_fact_hash);
        create index idx_snapshot_region_period on snapshot_transactions(city, district, transaction_period);
        create table snapshot_metadata (key text primary key, value text not null);
        """
    )


def _create_reconciliation_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        pragma journal_mode = delete;
        pragma synchronous = full;
        create table clean_index (
            clean_id text primary key,
            source_identity text not null,
            source_row_hash text not null,
            official_transaction_id text not null,
            official_transfer_id text not null,
            business_dedupe_key text not null,
            production_fact_hash text not null,
            canonical_business_fact_hash text not null,
            city text not null,
            district text not null,
            geographic_unit_kind text not null,
            transaction_period text not null,
            artifact_id text not null,
            artifact_sequence integer not null,
            source_conflict integer not null default 0,
            forensic_reason text not null default ''
        );
        create index idx_clean_business_key on clean_index(business_dedupe_key);
        create index idx_clean_production_fact on clean_index(production_fact_hash);
        create index idx_clean_canonical_fact on clean_index(canonical_business_fact_hash);
        create index idx_clean_source_identity on clean_index(source_identity);
        create table production_classification (
            stable_id integer primary key,
            bucket text not null,
            detail text not null,
            clean_id text,
            evidence_tier text not null,
            geography_matches integer not null,
            canonical_invalid integer not null,
            legacy_supporting integer not null,
            legacy_duplicate_candidate integer not null,
            production_only_reason text not null default ''
        );
        create index idx_prod_class_clean on production_classification(clean_id);
        create index idx_prod_class_bucket on production_classification(bucket);
        create table clean_classification (
            clean_id text primary key,
            bucket text not null,
            detail text not null
        );
        """
    )


def _index_clean_rows(shadow: sqlite3.Connection, output: sqlite3.Connection) -> None:
    rows = shadow.execute(
        """
        select source_identity, source_row_hash, official_transaction_id,
               official_transfer_id, business_dedupe_key, production_fact_hash,
               business_fact_hash,
               city, district, geographic_unit_kind, transaction_period,
               artifact_id, artifact_sequence
        from shadow_transactions
        order by source_identity, source_row_hash
        """
    )
    batch: list[tuple[Any, ...]] = []
    for row in rows:
        clean_id = _clean_id(str(row[0]), str(row[1]))
        batch.append((clean_id, *row, 0, ""))
        if len(batch) >= 2_000:
            _insert_clean_batch(output, batch)
            batch.clear()
    _insert_clean_batch(output, batch)

    conflict_rows = shadow.execute(
        """
        select candidate.source_identity, candidate.source_row_hash,
               candidate.official_transaction_id, candidate.official_transfer_id,
               candidate.business_dedupe_key, candidate.production_fact_hash,
               candidate.business_fact_hash,
               candidate.city, candidate.district, candidate.geographic_unit_kind,
               candidate.transaction_period, candidate.artifact_id,
               candidate.artifact_sequence
        from shadow_candidate_transactions candidate
        join shadow_source_conflicts conflict
          on conflict.source_identity = candidate.source_identity
        where conflict.resolution_status = 'UNRESOLVED'
        order by candidate.source_identity, candidate.source_row_hash
        """
    )
    batch = []
    for row in conflict_rows:
        clean_id = _clean_id(str(row[0]), str(row[1]))
        batch.append((clean_id, *row, 1, ""))
    _insert_clean_batch(output, batch)

    forensic_rows = shadow.execute(
        """
        select source_identity, source_row_hash, official_transaction_id,
               official_transfer_id, business_dedupe_key, production_fact_hash,
               business_fact_hash,
               city, district, geographic_unit_kind, transaction_period,
               artifact_id, artifact_sequence, forensic_reason
        from shadow_forensic_transactions
        order by source_identity, source_row_hash
        """
    )
    batch = []
    for row in forensic_rows:
        clean_id = _clean_id(str(row[0]), str(row[1]))
        batch.append((clean_id, *row[:13], 0, str(row[13])))
    _insert_clean_batch(output, batch)


def _insert_clean_batch(connection: sqlite3.Connection, rows: Sequence[tuple[Any, ...]]) -> None:
    if rows:
        connection.executemany(
            "insert or ignore into clean_index values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            rows,
        )


def _classify_production_rows(
    production: sqlite3.Connection,
    output: sqlite3.Connection,
    *,
    coverage_report: Mapping[str, Any],
    since: str,
    expected_release_ceiling: str,
) -> None:
    coverage = {
        (_city_key(item.get("city")), str(item.get("period") or "")): str(
            item.get("coverage_state") or ""
        )
        for item in coverage_report.get("matrix", ())
        if isinstance(item, Mapping)
    }
    district_owners = _district_owners()
    county_names = tuple(sorted({_city_key(region.county) for region in iter_taiwan_regions()}, key=len, reverse=True))
    rows = production.execute("select * from snapshot_transactions order by stable_id")
    batch: list[tuple[Any, ...]] = []
    for row in rows:
        item = dict(row)
        region = normalize_market_region(str(item["city"]), str(item["district"]))
        canonical_invalid = int(not region.valid or not region.district)
        proposed_city = _address_city(str(item["address_text"]), county_names)
        owners = district_owners.get(normalized_storage_key(item["district"]), ())
        legacy_supporting = int(bool(proposed_city and len(owners) == 1 and _city_key(owners[0]) == _city_key(proposed_city)))
        legacy_duplicate = 0
        if legacy_supporting:
            proposed_hash = _canonical_business_fact_hash(item, proposed_city, str(item["district"]))
            legacy_duplicate = int(
                production.execute(
                    "select 1 from snapshot_transactions where canonical_business_fact_hash = ? and stable_id <> ? limit 1",
                    (proposed_hash, item["stable_id"]),
                ).fetchone()
                is not None
            )
        classification = _match_production_row(output, item)
        period = str(item["transaction_period"])
        if period > expected_release_ceiling:
            bucket = ProductionBucket.FUTURE_ANOMALY.value
            detail = (
                "PROD_FUTURE_SOURCE_CONFIRMED"
                if classification[2] in {"A", "B"}
                else "PROD_FUTURE_UNRESOLVED"
            )
        else:
            bucket, detail = classification[0], classification[1]
        production_only_reason = ""
        if bucket == ProductionBucket.NOT_IN_CLEAN_SOURCE.value:
            state = coverage.get((_city_key(item["city"]), period), "")
            if period < since:
                production_only_reason = "OUTSIDE_REBUILD_WINDOW"
            elif state in {CoverageState.PARTIAL.value, CoverageState.MISSING.value}:
                production_only_reason = "SOURCE_COVERAGE_GAP"
            elif canonical_invalid:
                production_only_reason = "PROBABLE_BAD_IMPORT"
            else:
                production_only_reason = "UNRESOLVED"
        batch.append(
            (
                item["stable_id"],
                bucket,
                detail,
                classification[3],
                classification[2],
                classification[4],
                canonical_invalid,
                legacy_supporting,
                legacy_duplicate,
                production_only_reason,
            )
        )
        if len(batch) >= 2_000:
            output.executemany("insert into production_classification values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", batch)
            output.commit()
            batch.clear()
    if batch:
        output.executemany("insert into production_classification values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", batch)


def _match_production_row(
    output: sqlite3.Connection,
    production: Mapping[str, Any],
) -> tuple[str, str, str, str | None, int]:
    direct = output.execute(
        "select * from clean_index where business_dedupe_key = ?",
        (str(production.get("dedupe_key") or ""),),
    ).fetchall()
    if len(direct) == 1:
        clean = dict(direct[0])
        if clean["source_conflict"]:
            return ProductionBucket.CONFLICTING.value, "authoritative_identity_source_conflict", "A", clean["clean_id"], 0
        matches = int(_same_geography(production, clean))
        bucket = ProductionBucket.AUTHORITATIVE_MATCH.value if matches else ProductionBucket.GEOGRAPHY_CORRUPT_MATCH.value
        return bucket, "official_dedupe_identity", "A", clean["clean_id"], matches
    if len(direct) > 1:
        return ProductionBucket.CONFLICTING.value, "duplicate_clean_business_identity", "A", None, 0

    candidates = output.execute(
        "select * from clean_index where production_fact_hash = ?",
        (str(production.get("production_fact_hash") or ""),),
    ).fetchall()
    proven = [dict(row) for row in candidates if _dedupe_proves_official_identity(production, dict(row))]
    if len(proven) == 1:
        clean = proven[0]
        if clean["source_conflict"]:
            return ProductionBucket.CONFLICTING.value, "reconstructed_identity_source_conflict", "B", clean["clean_id"], 0
        matches = int(_same_geography(production, clean))
        bucket = ProductionBucket.AUTHORITATIVE_MATCH.value if matches else ProductionBucket.GEOGRAPHY_CORRUPT_MATCH.value
        return bucket, "official_identity_reconstructed", "B", clean["clean_id"], matches
    if len(proven) > 1:
        return ProductionBucket.CONFLICTING.value, "multiple_authoritative_candidates", "B", None, 0
    exact = output.execute(
        "select * from clean_index where canonical_business_fact_hash = ?",
        (str(production.get("canonical_business_fact_hash") or ""),),
    ).fetchall()
    if len(exact) == 1:
        clean = dict(exact[0])
        return ProductionBucket.PROBABLE_DUPLICATE.value, "exact_business_facts_only", "C", clean["clean_id"], int(_same_geography(production, clean))
    if len(exact) > 1:
        return ProductionBucket.CONFLICTING.value, "multiple_fact_candidates", "C", None, 0
    return ProductionBucket.NOT_IN_CLEAN_SOURCE.value, "no_clean_match", "NONE", None, 0


def _mark_duplicate_topology(connection: sqlite3.Connection) -> None:
    rows = connection.execute(
        """
        select stable_id, clean_id,
               row_number() over (
                   partition by clean_id
                   order by geography_matches desc, stable_id
               ) as match_rank,
               count(*) over (partition by clean_id) as match_count
        from production_classification
        where clean_id is not null and evidence_tier in ('A', 'B')
        """
    ).fetchall()
    duplicate_ids = [int(row[0]) for row in rows if int(row[2]) > 1]
    for start in range(0, len(duplicate_ids), 1_000):
        chunk = duplicate_ids[start : start + 1_000]
        placeholders = ",".join("?" for _ in chunk)
        connection.execute(
            f"update production_classification set bucket = ?, detail = ? where stable_id in ({placeholders})",
            [ProductionBucket.PROVABLE_DUPLICATE.value, "authoritative_clean_multiplicity", *chunk],
        )


def _classify_clean_rows(connection: sqlite3.Connection) -> None:
    rows = connection.execute(
        """
        select clean.clean_id, clean.source_conflict, clean.forensic_reason,
               count(prod.stable_id) as matched,
               count(prod.stable_id) filter (where prod.evidence_tier in ('A','B')) as authoritative,
               count(prod.stable_id) filter (
                   where prod.evidence_tier in ('A','B') and prod.geography_matches = 1
               ) as authoritative_correct,
               count(prod.stable_id) filter (
                   where prod.bucket in ('PROD_PROVABLE_DUPLICATE','PROD_PROBABLE_DUPLICATE')
               ) as duplicates
        from clean_index clean
        left join production_classification prod on prod.clean_id = clean.clean_id
        where clean.source_conflict = 0 and clean.forensic_reason = ''
        group by clean.clean_id, clean.source_conflict, clean.forensic_reason
        order by clean.clean_id
        """
    )
    batch: list[tuple[str, str, str]] = []
    for row in rows:
        clean_id = str(row[0])
        if int(row[1]):
            bucket, detail = CleanBucket.SOURCE_CONFLICT.value, "unresolved_official_source_conflict"
        elif str(row[2]):
            bucket, detail = CleanBucket.UNCLASSIFIED.value, "forensic_non_publishable_row"
        elif int(row[3]) > 1:
            bucket, detail = CleanBucket.DUPLICATED_IN_PROD.value, "production_multiplicity"
        elif int(row[4]) and int(row[5]):
            bucket, detail = CleanBucket.PRESENT_CORRECTLY.value, "authoritative_geography_match"
        elif int(row[4]):
            bucket, detail = CleanBucket.PRESENT_BUT_PROD_CORRUPT.value, "authoritative_geography_mismatch"
        elif int(row[3]):
            bucket, detail = CleanBucket.UNCLASSIFIED.value, "probable_only_match"
        else:
            bucket, detail = CleanBucket.MISSING_FROM_PROD.value, "no_production_match"
        batch.append((clean_id, bucket, detail))
    connection.executemany("insert into clean_classification values (?, ?, ?)", batch)


def _build_reconciliation_report(
    shadow: sqlite3.Connection,
    production: sqlite3.Connection,
    output: sqlite3.Connection,
    *,
    coverage_report: Mapping[str, Any],
    expected_release_ceiling: str,
    main_sha: str,
    clean_manifest_sha256: str,
) -> dict[str, Any]:
    production_counts = _count_by(output, "production_classification", "bucket")
    clean_counts = _count_by(output, "clean_classification", "bucket")
    production_total = sum(production_counts.values())
    clean_publishable = int(shadow.execute("select count(*) from shadow_transactions").fetchone()[0])
    clean_total = sum(clean_counts.values())
    invalid = _invalid_cohort(output)
    legacy_geography = _legacy_geography_cohort(output)
    legacy_duplicates = _legacy_duplicate_cohort(output)
    production_only = _count_by(
        output,
        "production_classification",
        "production_only_reason",
        where="bucket = 'PROD_NOT_IN_CLEAN_SOURCE'",
    )
    for key in (
        "SOURCE_COVERAGE_GAP",
        "OUTSIDE_REBUILD_WINDOW",
        "PROBABLE_BAD_IMPORT",
        "UNSUPPORTED_TRANSACTION_TYPE",
        "FUTURE",
        "UNRESOLVED",
    ):
        production_only.setdefault(key, 0)
    clean_only = _clean_only_analysis(output)
    topology = _duplicate_topology(output)
    aggregates = _aggregate_reconciliation(shadow, production, expected_release_ceiling)
    snapshot = _snapshot_metadata(production)
    expected_production = int(snapshot["production_total_count"])
    production_only_total = sum(production_only.values())
    clean_only_total = sum(clean_only.values())
    expected_production_only = production_counts.get(
        ProductionBucket.NOT_IN_CLEAN_SOURCE.value, 0
    )
    expected_clean_only = clean_counts.get(CleanBucket.MISSING_FROM_PROD.value, 0)
    if production_total != expected_production:
        raise ReconciliationError("production_bucket_conservation_failed")
    if clean_total != clean_publishable:
        raise ReconciliationError("clean_bucket_conservation_failed")
    if production_only_total != expected_production_only:
        raise ReconciliationError("production_only_subtype_conservation_failed")
    if clean_only_total != expected_clean_only:
        raise ReconciliationError("clean_only_subtype_conservation_failed")
    evidence = _production_bucket_evidence(output, production_total)
    report: dict[str, Any] = {
        "schema_version": RECONCILIATION_SCHEMA_VERSION,
        "main_sha": main_sha,
        "clean_manifest_sha256": clean_manifest_sha256,
        "production_snapshot": snapshot,
        "production": {bucket.value: production_counts.get(bucket.value, 0) for bucket in ProductionBucket},
        "clean": {bucket.value: clean_counts.get(bucket.value, 0) for bucket in CleanBucket},
        "production_bucket_evidence": evidence,
        "matching_tiers": {
            "A": {
                "classification": "AUTHORITATIVE",
                "fields": ["persisted_official_identity_key", "clean_official_transaction_identity"],
            },
            "B": {
                "classification": "AUTHORITATIVE",
                "fields": ["production_fact_hash", "reconstructed_official_transaction_identity"],
            },
            "C": {
                "classification": "STRONG_FACT_MATCH",
                "fields": [
                    "canonical_geography", "transaction_period", "address_fingerprint",
                    "road", "building_type", "area", "total_price", "unit_price",
                    "floor", "total_floor",
                ],
            },
            "D": {
                "classification": "PROBABLE_ONLY",
                "fields": ["legacy_natural_key"],
                "used_for_authoritative_classification": False,
            },
        },
        "conservation": {
            "production_expected": expected_production,
            "production_bucket_sum": production_total,
            "production_rows_conserved": production_total == expected_production,
            "clean_expected": clean_publishable,
            "clean_bucket_sum": clean_total,
            "clean_rows_conserved": clean_total == clean_publishable,
            "production_only_expected": expected_production_only,
            "production_only_subtype_sum": production_only_total,
            "production_only_conserved": production_only_total == expected_production_only,
            "clean_only_expected": expected_clean_only,
            "clean_only_subtype_sum": clean_only_total,
            "clean_only_conserved": clean_only_total == expected_clean_only,
        },
        "quality": {
            "classified_rows": production_total,
            "classification_percent": _percent(production_total, expected_production),
            "authoritative_matched_percent": _percent(
                production_counts.get(ProductionBucket.AUTHORITATIVE_MATCH.value, 0)
                + production_counts.get(ProductionBucket.GEOGRAPHY_CORRUPT_MATCH.value, 0)
                + production_counts.get(ProductionBucket.PROVABLE_DUPLICATE.value, 0),
                production_total,
            ),
            "invalid_geography_authoritative_resolved_percent": _percent(
                invalid["GEOGRAPHY_CORRUPT_MATCH"], invalid["current_observed_baseline"]
            ),
            "legacy_duplicate_provably_resolved_percent": _percent(
                legacy_duplicates["PROVABLE_DUPLICATE"],
                legacy_duplicates["current_observed_baseline"],
            ),
            "production_only_unresolved_percent": _percent(
                production_only.get("UNRESOLVED", 0),
                production_counts.get(ProductionBucket.NOT_IN_CLEAN_SOURCE.value, 0),
            ),
            "clean_only_unresolved_percent": _percent(
                clean_only.get("UNRESOLVED", 0),
                clean_counts.get(CleanBucket.MISSING_FROM_PROD.value, 0),
            ),
        },
        "invalid_geography_cohort": invalid,
        "legacy_geography_cohort": legacy_geography,
        "legacy_duplicate_cohort": legacy_duplicates,
        "duplicate_topology": topology,
        "production_only_analysis": production_only,
        "clean_only_analysis": clean_only,
        "future_row": _future_analysis(output),
        "aggregate_reconciliation": aggregates,
        "aggregate_delta_context": {
            "attribution_status": "MATERIAL_DELTAS_REQUIRE_FURTHER_EXPLANATION",
            "geography_corrupt_rows": production_counts.get(
                ProductionBucket.GEOGRAPHY_CORRUPT_MATCH.value, 0
            ),
            "probable_duplicate_candidates": production_counts.get(
                ProductionBucket.PROBABLE_DUPLICATE.value, 0
            ),
            "provable_duplicate_rows": production_counts.get(
                ProductionBucket.PROVABLE_DUPLICATE.value, 0
            ),
            "production_only_rows": production_counts.get(
                ProductionBucket.NOT_IN_CLEAN_SOURCE.value, 0
            ),
            "clean_missing_from_production": clean_counts.get(
                CleanBucket.MISSING_FROM_PROD.value, 0
            ),
            "future_excluded_rows": production_counts.get(
                ProductionBucket.FUTURE_ANOMALY.value, 0
            ),
        },
        "coverage": {
            "raw_calendar_coverage_percent": coverage_report.get("raw_calendar_coverage_percent"),
            "expected_official_coverage_percent": coverage_report.get("expected_official_coverage_percent"),
            "expected_release_ceiling": coverage_report.get("expected_release_ceiling"),
        },
        "production_safety": {
            "mode": "SELECT_ONLY",
            "writes": 0,
            "migrations": 0,
            "rows_changed": 0,
        },
    }
    return report


def _snapshot_row(row: Mapping[str, Any]) -> tuple[Any, ...]:
    item = dict(row)
    address = str(item.get("address_text") or "")
    address_fingerprint = hashlib.sha256(_compact(address).encode("utf-8")).hexdigest()
    production_hash = _production_fact_hash(item)
    canonical_hash = _canonical_business_fact_hash(item, str(item.get("city") or ""), str(item.get("district") or ""))
    safe_row = {
        "stable_id": int(item["id"]),
        "period": str(item.get("transaction_period") or ""),
        "city": str(item.get("city") or ""),
        "district": str(item.get("district") or ""),
        "address_fingerprint": address_fingerprint,
        "building_type": str(item.get("building_type") or ""),
        "area": _number(item.get("area_ping")),
        "total_price": _number(item.get("total_price")),
        "unit_price": _number(item.get("unit_price_per_ping")),
        "dedupe_key": str(item.get("dedupe_key") or ""),
    }
    return (
        int(item["id"]), str(item.get("transaction_period") or ""),
        str(item.get("city") or ""), str(item.get("district") or ""),
        str(item.get("road") or ""), address, str(item.get("building_type") or ""),
        _number(item.get("area_ping")), _number(item.get("building_age_years")),
        int(item.get("floor") or 0), int(item["total_floor"]) if item.get("total_floor") is not None else None,
        _number(item.get("unit_price_per_ping")), _number(item.get("total_price")),
        str(item.get("source") or ""), str(item.get("dedupe_key") or ""),
        _date_text(item.get("imported_at")), address_fingerprint, production_hash,
        canonical_hash, _hash_payload(safe_row),
    )


def _production_fact_hash(row: Mapping[str, Any]) -> str:
    return _hash_payload(
        {
            "source": str(row.get("source") or OFFICIAL_SOURCE),
            "transaction_period": str(row.get("transaction_period") or "").strip(),
            "address_text": _compact(row.get("address_text")),
            "road": _compact(row.get("road")),
            "building_type": _compact(row.get("building_type")),
            "area_ping": f"{_number(row.get('area_ping')):.2f}",
            "total_price": f"{_number(row.get('total_price')):.2f}",
            "unit_price_per_ping": f"{_number(row.get('unit_price_per_ping')):.2f}",
            "floor": int(row.get("floor") or 0),
            "total_floor": int(row.get("total_floor") or 0),
        }
    )


def _canonical_business_fact_hash(row: Mapping[str, Any], city: str, district: str) -> str:
    return _hash_payload(
        {
            "source": str(row.get("source") or OFFICIAL_SOURCE),
            "city": _city_key(city),
            "district": _compact(district),
            "transaction_period": str(row.get("transaction_period") or "").strip(),
            "address_text": _compact(row.get("address_text")),
            "road": _compact(row.get("road")),
            "building_type": _compact(row.get("building_type")),
            "area_ping": f"{_number(row.get('area_ping')):.2f}",
            "total_price": f"{_number(row.get('total_price')):.2f}",
            "unit_price_per_ping": f"{_number(row.get('unit_price_per_ping')):.2f}",
            "floor": int(row.get("floor") or 0),
            "total_floor": int(row.get("total_floor") or 0),
        }
    )


def _dedupe_proves_official_identity(
    production: Mapping[str, Any], clean: Mapping[str, Any]
) -> bool:
    official_id = str(clean.get("official_transaction_id") or clean.get("official_transfer_id") or "")
    persisted = str(production.get("dedupe_key") or "")
    return bool(official_id and persisted and build_dedupe_key(dict(production), official_id) == persisted)


def _same_geography(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    if str(right.get("geographic_unit_kind") or "") == "city_level":
        left_county = normalize_market_region(str(left.get("city") or ""))
        return (
            left_county.valid
            and left_county.county == str(right.get("city") or "")
            and _city_key(left.get("district")) in {"", _city_key(left_county.county)}
        )
    left_region = normalize_market_region(str(left.get("city") or ""), str(left.get("district") or ""))
    right_region = normalize_market_region(str(right.get("city") or ""), str(right.get("district") or ""))
    return (
        left_region.valid
        and right_region.valid
        and left_region.county == right_region.county
        and left_region.district == right_region.district
    )


def _invalid_cohort(connection: sqlite3.Connection) -> dict[str, Any]:
    rows = connection.execute(
        "select bucket, count(*) from production_classification where canonical_invalid = 1 group by bucket"
    ).fetchall()
    counts = {str(row[0]): int(row[1]) for row in rows}
    unclassified = counts.get(ProductionBucket.UNCLASSIFIED.value, 0) + counts.get(
        ProductionBucket.AUTHORITATIVE_MATCH.value, 0
    )
    historical_baseline = 126_087
    current_observed_baseline = sum(counts.values())
    return {
        "historical_baseline": historical_baseline,
        "current_observed_baseline": current_observed_baseline,
        "baseline_difference": current_observed_baseline - historical_baseline,
        "baseline_difference_reason": "CURRENT_PREDICATE_MATCHES_HISTORICAL_BASELINE",
        "GEOGRAPHY_CORRUPT_MATCH": counts.get(ProductionBucket.GEOGRAPHY_CORRUPT_MATCH.value, 0),
        "PROVABLE_DUPLICATE": counts.get(ProductionBucket.PROVABLE_DUPLICATE.value, 0),
        "PROBABLE_DUPLICATE": counts.get(ProductionBucket.PROBABLE_DUPLICATE.value, 0),
        "NOT_IN_CLEAN_SOURCE": counts.get(ProductionBucket.NOT_IN_CLEAN_SOURCE.value, 0),
        "FUTURE_ANOMALY": counts.get(ProductionBucket.FUTURE_ANOMALY.value, 0),
        "CONFLICTING": counts.get(ProductionBucket.CONFLICTING.value, 0),
        "UNCLASSIFIED": unclassified,
    }


def _legacy_geography_cohort(connection: sqlite3.Connection) -> dict[str, Any]:
    rows = connection.execute(
        "select bucket, count(*) from production_classification where legacy_supporting = 1 group by bucket"
    ).fetchall()
    counts = {str(row[0]): int(row[1]) for row in rows}
    historical_baseline = 109_236
    current_observed_baseline = sum(counts.values())
    return {
        "historical_baseline": historical_baseline,
        "current_observed_baseline": current_observed_baseline,
        "baseline_difference": current_observed_baseline - historical_baseline,
        "baseline_difference_reason": (
            "CURRENT_FULL_SNAPSHOT_PREDICATE_DIFFERS_FROM_HISTORICAL_EXTRACTION"
        ),
        "AUTHORITATIVE_CONFIRMED": (
            counts.get(ProductionBucket.AUTHORITATIVE_MATCH.value, 0)
            + counts.get(ProductionBucket.GEOGRAPHY_CORRUPT_MATCH.value, 0)
            + counts.get(ProductionBucket.PROVABLE_DUPLICATE.value, 0)
        ),
        "PROBABLE_ONLY": counts.get(ProductionBucket.PROBABLE_DUPLICATE.value, 0),
        "NO_SOURCE_MATCH": counts.get(ProductionBucket.NOT_IN_CLEAN_SOURCE.value, 0),
        "CONFLICTING": counts.get(ProductionBucket.CONFLICTING.value, 0),
        "UNCLASSIFIED": counts.get(ProductionBucket.UNCLASSIFIED.value, 0)
        + counts.get(ProductionBucket.FUTURE_ANOMALY.value, 0),
    }


def _legacy_duplicate_cohort(connection: sqlite3.Connection) -> dict[str, Any]:
    rows = connection.execute(
        "select bucket, count(*) from production_classification where legacy_duplicate_candidate = 1 group by bucket"
    ).fetchall()
    counts = {str(row[0]): int(row[1]) for row in rows}
    historical_baseline = 57_350
    current_observed_baseline = sum(counts.values())
    return {
        "historical_baseline": historical_baseline,
        "current_observed_baseline": current_observed_baseline,
        "baseline_difference": current_observed_baseline - historical_baseline,
        "baseline_difference_reason": (
            "CURRENT_FULL_SNAPSHOT_RECOMPUTATION_DIFFERS_FROM_HISTORICAL_FROZEN_COUNT"
        ),
        "PROVABLE_DUPLICATE": counts.get(ProductionBucket.PROVABLE_DUPLICATE.value, 0),
        "PROBABLE_DUPLICATE": counts.get(ProductionBucket.PROBABLE_DUPLICATE.value, 0),
        "NOT_ACTUALLY_DUPLICATE": counts.get(ProductionBucket.AUTHORITATIVE_MATCH.value, 0)
        + counts.get(ProductionBucket.GEOGRAPHY_CORRUPT_MATCH.value, 0),
        "NO_CLEAN_MATCH": counts.get(ProductionBucket.NOT_IN_CLEAN_SOURCE.value, 0),
        "CONFLICTING": counts.get(ProductionBucket.CONFLICTING.value, 0),
        "UNRESOLVED": counts.get(ProductionBucket.UNCLASSIFIED.value, 0)
        + counts.get(ProductionBucket.FUTURE_ANOMALY.value, 0),
    }


def _duplicate_topology(connection: sqlite3.Connection) -> dict[str, Any]:
    authoritative_multiplicities = [
        int(row[0])
        for row in connection.execute(
            """
            select count(*) from production_classification
            where clean_id is not null and evidence_tier in ('A','B')
            group by clean_id
            """
        )
    ]
    probable_multiplicities = [
        int(row[0])
        for row in connection.execute(
            """
            select count(*) from production_classification
            where clean_id is not null and evidence_tier = 'C'
            group by clean_id
            """
        )
    ]
    duplicate_rows = int(
        connection.execute(
            """
            select count(*)
            from production_classification
            where bucket in ('PROD_PROVABLE_DUPLICATE', 'PROD_PROBABLE_DUPLICATE')
            """
        ).fetchone()[0]
    )
    duplicate_rows_with_invalid_geography = int(
        connection.execute(
            """
            select count(*)
            from production_classification
            where bucket in ('PROD_PROVABLE_DUPLICATE', 'PROD_PROBABLE_DUPLICATE')
              and canonical_invalid = 1
            """
        ).fetchone()[0]
    )
    return {
        "authoritative_one_clean_to_one_prod": sum(
            value == 1 for value in authoritative_multiplicities
        ),
        "authoritative_one_clean_to_two_prod": sum(
            value == 2 for value in authoritative_multiplicities
        ),
        "authoritative_one_clean_to_three_plus_prod": sum(
            value >= 3 for value in authoritative_multiplicities
        ),
        "provable_duplicate_groups": sum(
            value > 1 for value in authoritative_multiplicities
        ),
        "provable_duplicate_excess_rows": sum(
            max(0, value - 1) for value in authoritative_multiplicities
        ),
        "probable_one_clean_to_one_prod": sum(
            value == 1 for value in probable_multiplicities
        ),
        "probable_one_clean_to_two_prod": sum(
            value == 2 for value in probable_multiplicities
        ),
        "probable_one_clean_to_three_plus_prod": sum(
            value >= 3 for value in probable_multiplicities
        ),
        "probable_duplicate_groups": sum(
            value > 1 for value in probable_multiplicities
        ),
        "probable_duplicate_excess_rows": sum(
            max(0, value - 1) for value in probable_multiplicities
        ),
        "provable_evidence_tiers": ["A", "B"],
        "probable_evidence_tiers": ["C"],
        "duplicate_rows": duplicate_rows,
        "duplicate_rows_with_invalid_geography": duplicate_rows_with_invalid_geography,
    }


def _clean_only_analysis(connection: sqlite3.Connection) -> dict[str, int]:
    counts = Counter()
    rows = connection.execute(
        """
        select clean.artifact_id, clean.forensic_reason
        from clean_index clean
        join clean_classification classified on classified.clean_id = clean.clean_id
        where classified.bucket = 'CLEAN_MISSING_FROM_PROD'
        """
    )
    for artifact_id, forensic_reason in rows:
        if forensic_reason:
            counts["UNRESOLVED"] += 1
        elif "history-" in str(artifact_id) or "current-" in str(artifact_id):
            counts["SOURCE_NEWER_THAN_PROD"] += 1
        else:
            counts["PREVIOUS_IMPORT_SCOPE_GAP"] += 1
    for key in ("LEGITIMATE_PROD_MISSING", "DIFFERENT_DEDUPE", "PREVIOUS_IMPORT_SCOPE_GAP", "SOURCE_NEWER_THAN_PROD", "UNRESOLVED"):
        counts.setdefault(key, 0)
    return dict(counts)


def _future_analysis(connection: sqlite3.Connection) -> dict[str, Any]:
    rows = connection.execute(
        """
        select detail, evidence_tier, count(*)
        from production_classification
        where bucket = 'PROD_FUTURE_ANOMALY'
        group by detail, evidence_tier
        """
    ).fetchall()
    confirmed = sum(int(row[2]) for row in rows if str(row[0]) == "PROD_FUTURE_SOURCE_CONFIRMED")
    total = sum(int(row[2]) for row in rows)
    evidence_tiers = sorted({str(row[1]) for row in rows if str(row[1]) not in {"", "NONE"}})
    artifacts = [
        str(row[0])
        for row in connection.execute(
            """
            select distinct clean.artifact_id
            from production_classification production
            join clean_index clean on clean.clean_id = production.clean_id
            where production.bucket = 'PROD_FUTURE_ANOMALY'
              and clean.forensic_reason <> ''
            order by clean.artifact_id
            """
        )
    ]
    source_periods = [
        str(row[0])
        for row in connection.execute(
            """
            select distinct clean.transaction_period
            from production_classification production
            join clean_index clean on clean.clean_id = production.clean_id
            where production.bucket = 'PROD_FUTURE_ANOMALY'
              and clean.forensic_reason <> ''
            order by clean.transaction_period
            """
        )
    ]
    return {
        "classification": "PROD_FUTURE_SOURCE_CONFIRMED" if confirmed == total and total else "PROD_FUTURE_UNRESOLVED",
        "production_match_count": total,
        "clean_source_evidence_count": confirmed,
        "identity_match": bool(confirmed and confirmed == total),
        "identity_tiers": evidence_tiers,
        "source_artifact_ids": artifacts,
        "raw_source_periods": source_periods,
        "publishable_status": "excluded",
    }


def _production_bucket_evidence(
    connection: sqlite3.Connection, production_total: int
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for bucket in ProductionBucket:
        rows = connection.execute(
            """
            select evidence_tier, detail, count(*)
            from production_classification
            where bucket = ?
            group by evidence_tier, detail
            order by count(*) desc, evidence_tier, detail
            """,
            (bucket.value,),
        ).fetchall()
        count = sum(int(row[2]) for row in rows)
        tiers: Counter[str] = Counter()
        reasons: dict[str, int] = {}
        for tier, detail, row_count in rows:
            tiers[str(tier)] += int(row_count)
            reasons[str(detail)] = int(row_count)
        result[bucket.value] = {
            "row_count": count,
            "percentage": _percent(count, production_total),
            "evidence_tiers": dict(sorted(tiers.items())),
            "representative_reason_codes": dict(list(reasons.items())[:5]),
        }
    return result


def _aggregate_reconciliation(
    shadow: sqlite3.Connection,
    production: sqlite3.Connection,
    ceiling: str,
) -> dict[str, Any]:
    shadow_rows = {
        (str(row[0]), str(row[1]), str(row[2])): tuple(row[3:])
        for row in shadow.execute(
            """
            select city, district, transaction_period, count(*),
                   round(avg(unit_price_per_ping), 2), round(avg(total_price), 2),
                   round(avg(area_ping), 2), round(sum(total_price), 2)
            from shadow_transactions
            group by city, district, transaction_period
            """
        )
    }
    production_rows = {
        (str(row[0]), str(row[1]), str(row[2])): tuple(row[3:])
        for row in production.execute(
            """
            select city, district, transaction_period, count(*),
                   round(avg(unit_price_per_ping), 2), round(avg(total_price), 2),
                   round(avg(area_ping), 2), round(sum(total_price), 2)
            from snapshot_transactions
            where transaction_period <= ?
            group by city, district, transaction_period
            """,
            (ceiling,),
        )
    }
    unchanged = changed = production_only = shadow_only = 0
    count_abs_delta = 0
    unit_price_abs_deltas: list[float] = []
    total_value_abs_delta = 0.0
    for key in set(shadow_rows) | set(production_rows):
        left, right = production_rows.get(key), shadow_rows.get(key)
        if left is None:
            shadow_only += 1
        elif right is None:
            production_only += 1
        elif left == right:
            unchanged += 1
        else:
            changed += 1
            count_abs_delta += abs(int(left[0]) - int(right[0]))
            unit_price_abs_deltas.append(abs(float(left[1] or 0) - float(right[1] or 0)))
            total_value_abs_delta += abs(float(left[4] or 0) - float(right[4] or 0))
    golden = []
    for county, district in (
        ("臺北市", "中正區"), ("臺北市", "南港區"), ("臺中市", "北屯區"),
        ("桃園市", "平鎮區"), ("桃園市", "中壢區"), ("高雄市", "小港區"),
        ("高雄市", "三民區"),
    ):
        row = shadow.execute(
            """
            select count(*), max(period) from shadow_market_aggregates
            where county = ? and district = ?
            """,
            (county, district),
        ).fetchone()
        golden.append({"county": county, "district": district, "history_length": int(row[0]), "latest_period": row[1]})
    return {
        "production_aggregate_rows": len(production_rows),
        "shadow_aggregate_rows": len(shadow_rows),
        "unchanged_scopes": unchanged,
        "materially_changed_scopes": changed,
        "production_only_scopes": production_only,
        "shadow_only_scopes": shadow_only,
        "materiality_threshold": None,
        "changed_scope_delta_summary": {
            "transaction_count_absolute_delta_sum": count_abs_delta,
            "average_unit_price_mean_absolute_delta": round(
                sum(unit_price_abs_deltas) / len(unit_price_abs_deltas), 2
            )
            if unit_price_abs_deltas
            else 0.0,
            "average_unit_price_max_absolute_delta": round(
                max(unit_price_abs_deltas), 2
            )
            if unit_price_abs_deltas
            else 0.0,
            "total_transaction_value_absolute_delta_sum": round(total_value_abs_delta, 2),
        },
        "golden_regions": golden,
    }


def _snapshot_metadata(connection: sqlite3.Connection) -> dict[str, Any]:
    values = {
        str(row[0]): _json_value(str(row[1]))
        for row in connection.execute("select key, value from snapshot_metadata")
    }
    return values


def _count_by(
    connection: sqlite3.Connection,
    table: str,
    column: str,
    *,
    where: str = "1 = 1",
) -> dict[str, int]:
    allowed = {
        ("production_classification", "bucket"),
        ("production_classification", "production_only_reason"),
        ("clean_classification", "bucket"),
    }
    if (table, column) not in allowed:
        raise ReconciliationError("unsafe_local_summary_query")
    return {
        str(row[0]): int(row[1])
        for row in connection.execute(
            f"select {column}, count(*) from {table} where {where} group by {column}"
        )
        if str(row[0])
    }


def _district_owners() -> dict[str, tuple[str, ...]]:
    owners: dict[str, list[str]] = defaultdict(list)
    for region in iter_taiwan_regions():
        owners[normalized_storage_key(region.district)].append(region.county)
    return {key: tuple(dict.fromkeys(values)) for key, values in owners.items()}


def _address_city(address: str, counties: Iterable[str]) -> str:
    normalized = normalized_storage_key(address)
    for county in counties:
        if normalized.startswith(county):
            result = normalize_market_region(county)
            return result.county if result.valid else ""
    return ""


def _clean_id(source_identity: str, source_row_hash: str) -> str:
    return _hash_payload({"source_identity": source_identity, "source_row_hash": source_row_hash})


def _open_sqlite_readonly(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def _assert_local_target(path: Path, allowed_root: Path) -> None:
    root = allowed_root.resolve()
    target = path.resolve()
    if target == root or root not in target.parents:
        raise ReconciliationError("local_output_outside_allowed_root")


def _assert_production_select(sql: str) -> None:
    compact = re.sub(r"\s+", " ", sql).strip()
    if not compact.lower().startswith("select ") or FORBIDDEN_PRODUCTION_SQL.search(compact):
        raise ReconciliationError("production_query_not_select_only")


def _validate_page_size(page_size: int) -> None:
    if page_size < 1 or page_size > MAX_PAGE_SIZE:
        raise ReconciliationError("invalid_production_page_size")


def _compact(value: Any) -> str:
    return re.sub(r"\s+", "", str(value or ""))


def _city_key(value: Any) -> str:
    return _compact(value).replace("臺", "台")


def _number(value: Any) -> float:
    return round(float(value or 0), 2)


def _date_text(value: Any) -> str:
    return value.isoformat() if hasattr(value, "isoformat") else str(value or "")


def _hash_payload(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def _percent(numerator: int, denominator: int) -> float:
    return round(numerator / denominator * 100, 2) if denominator else 0.0


def _json_value(value: str) -> Any:
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def asdict_without_none(value: SnapshotMetadata) -> dict[str, Any]:
    return {
        key: item
        for key, item in {
            "snapshot_at": value.snapshot_at,
            "production_total_count": value.production_total_count,
            "source_filter": value.source_filter,
            "pagination_method": value.pagination_method,
            "first_stable_key": value.first_stable_key,
            "last_stable_key": value.last_stable_key,
            "page_count": value.page_count,
            "snapshot_sha256": value.snapshot_sha256,
            "main_sha": value.main_sha,
            "clean_manifest_sha256": value.clean_manifest_sha256,
            "clean_shadow_sha256": value.clean_shadow_sha256,
            "closing_production_count": value.closing_production_count,
            "snapshot_stationary": value.snapshot_stationary,
            "transaction_isolation": value.transaction_isolation,
            "transaction_read_only": value.transaction_read_only,
            "database_identified": value.database_identified,
            "user_identified": value.user_identified,
        }.items()
        if item is not None
    }
