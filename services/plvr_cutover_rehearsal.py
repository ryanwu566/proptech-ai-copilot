"""Isolated PostgreSQL rehearsal for the authoritative PLVR generation cutover.

The module has one database contract: ``PLVR_DRY_RUN_DATABASE_URL`` pointing
to the disposable local database ``plvr_cutover_dryrun``. It never falls back
to any production runtime variable.
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import time
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from decimal import Decimal
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator, Mapping, Sequence
from urllib.parse import urlparse

from scripts.validate_postgres_migration import _split_sql
from services.plvr_clean_shadow_rebuild import manifest_checksum, sha256_file, shadow_dataset_checksum


DATASET_KEY = "official_plvr"
DRY_RUN_ENVIRONMENT_VARIABLE = "PLVR_DRY_RUN_DATABASE_URL"
DRY_RUN_DATABASE_NAME = "plvr_cutover_dryrun"
LOCAL_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})
GREEN_TRANSACTION_COUNT = 517_195
GREEN_AGGREGATE_COUNT = 9_606
GREEN_CITY_COUNT = 21
GREEN_GEOGRAPHIC_UNIT_COUNT = 325
GREEN_PERIOD_MIN = "2023-09"
GREEN_PERIOD_MAX = "2026-07"
EXPECTED_COVERAGE_PERCENT = 94.29
BLUE_TRANSACTION_COUNT = 451_672
BLUE_PUBLISHABLE_TRANSACTION_COUNT = 451_671
BLUE_AGGREGATE_COUNT = 11_017
DEFAULT_BATCH_SIZE = 10_000
BLUE_GENERATION_ID = "official-plvr-blue-phase2e"
GREEN_GENERATION_ID = "official-plvr-green-18203c6347cd"

TRANSACTION_COLUMNS = (
    "dataset_key",
    "generation_id",
    "source_row_hash",
    "source_identity",
    "source_manifest_sha256",
    "source_artifact_sha256",
    "official_transaction_id",
    "official_transfer_id",
    "business_dedupe_key",
    "production_fact_hash",
    "transaction_period",
    "city",
    "district",
    "geographic_unit_kind",
    "road",
    "address_text",
    "building_type",
    "area_ping",
    "building_age_years",
    "floor",
    "total_floor",
    "unit_price_per_ping",
    "total_price",
    "source",
    "canonical_status",
    "publishable",
)

RESET_SQL = """
drop view if exists plvr_active_region_coverage;
drop view if exists plvr_active_market_aggregates;
drop view if exists plvr_active_transactions;
drop table if exists plvr_rehearsal_events;
drop table if exists plvr_generation_load_checkpoints;
drop table if exists plvr_active_dataset;
drop table if exists plvr_generation_region_coverage;
drop table if exists plvr_generation_market_aggregates;
drop table if exists plvr_generation_transactions;
drop table if exists plvr_dataset_generations;
drop function if exists plvr_guard_active_generation();
drop function if exists plvr_guard_generation_derived_row();
drop function if exists plvr_guard_generation_transaction();
drop function if exists plvr_guard_frozen_generation_manifest();
"""


class RehearsalError(RuntimeError):
    """Fail-closed Phase 2E error carrying only an allowlisted reason code."""


@dataclass(frozen=True)
class DryRunTarget:
    database_url: str
    host_class: str
    database_name: str
    database_user: str
    postgres_version: str

    def __repr__(self) -> str:
        return (
            "DryRunTarget(host_class='localhost', "
            f"database_name={self.database_name!r}, database_user={self.database_user!r})"
        )


@dataclass(frozen=True)
class RehearsalSources:
    manifest_sha256: str
    green_dataset_sha256: str
    blue_snapshot_sha256: str
    green_transactions: int
    green_aggregates: int
    green_cities: int
    green_geographic_units: int
    green_period_min: str
    green_period_max: str
    green_canonical_invalid: int
    green_future_publishable: int
    green_missing_lineage: int
    green_unresolved_conflicts: int
    blue_transactions: int
    blue_period_min: str
    blue_period_max: str


@dataclass(frozen=True)
class LoadResult:
    attempted_rows: int
    inserted_rows: int
    duplicate_rows: int
    completed_batches: int
    final_rows: int
    complete: bool
    elapsed_seconds: float


@dataclass(frozen=True)
class SwitchResult:
    previous_generation_id: str
    active_generation_id: str
    duration_seconds: float


def resolve_dry_run_url(environ: Mapping[str, str] | None = None) -> str:
    """Resolve only the explicit Phase 2E variable and reject every other target."""

    source = os.environ if environ is None else environ
    raw = str(source.get(DRY_RUN_ENVIRONMENT_VARIABLE) or "").strip()
    if not raw:
        raise RehearsalError("dry_run_database_not_configured")
    parsed = urlparse(raw)
    host = (parsed.hostname or "").lower()
    database_name = parsed.path.lstrip("/").split("/", 1)[0]
    if host not in LOCAL_HOSTS:
        raise RehearsalError("dry_run_database_host_not_local")
    if database_name != DRY_RUN_DATABASE_NAME:
        raise RehearsalError("dry_run_database_name_mismatch")
    if parsed.scheme not in {"postgres", "postgresql"}:
        raise RehearsalError("dry_run_database_scheme_invalid")
    return raw


def inspect_dry_run_target(environ: Mapping[str, str] | None = None) -> DryRunTarget:
    """Connect to the validated local target and return non-secret identification."""

    import psycopg

    database_url = resolve_dry_run_url(environ)
    try:
        with psycopg.connect(database_url, connect_timeout=10, autocommit=True) as connection:
            connection.read_only = True
            row = connection.execute("select current_database(), current_user, version()").fetchone()
    except psycopg.Error as error:
        raise RehearsalError("dry_run_database_unavailable") from error
    if row is None or row[0] != DRY_RUN_DATABASE_NAME:
        raise RehearsalError("dry_run_database_identity_mismatch")
    return DryRunTarget(
        database_url=database_url,
        host_class="localhost",
        database_name=str(row[0]),
        database_user=str(row[1]),
        postgres_version=str(row[2]),
    )


@contextmanager
def connect_dry_run(environ: Mapping[str, str] | None = None) -> Iterator[Any]:
    """Yield an autocommit psycopg connection after repeating the local guard."""

    import psycopg

    target = inspect_dry_run_target(environ)
    connection = psycopg.connect(target.database_url, connect_timeout=10, autocommit=True)
    try:
        actual = connection.execute("select current_database()").fetchone()[0]
        if actual != DRY_RUN_DATABASE_NAME:
            raise RehearsalError("dry_run_database_identity_mismatch")
        yield connection
    finally:
        connection.close()


def validate_source_bundle(
    *,
    manifest_path: Path,
    artifact_root: Path,
    green_shadow_path: Path,
    green_summary_path: Path,
    blue_snapshot_path: Path,
    residual_summary_path: Path,
) -> RehearsalSources:
    """Validate immutable local Phase 2C evidence without exposing any row."""

    for path in (
        manifest_path,
        artifact_root,
        green_shadow_path,
        green_summary_path,
        blue_snapshot_path,
        residual_summary_path,
    ):
        if not path.exists():
            raise RehearsalError("authoritative_source_artifact_missing")

    manifest = _read_json(manifest_path)
    if manifest.get("manifest_sha256") != manifest_checksum(manifest):
        raise RehearsalError("authoritative_manifest_checksum_mismatch")
    artifacts = [item for item in manifest.get("artifacts", []) if isinstance(item, dict)]
    if len(artifacts) != 17:
        raise RehearsalError("authoritative_artifact_count_mismatch")
    for artifact in artifacts:
        path = artifact_root / str(artifact.get("local_filename") or "")
        if not path.is_file() or sha256_file(path) != str(artifact.get("sha256") or ""):
            raise RehearsalError("authoritative_artifact_checksum_mismatch")

    green_summary = _read_json(green_summary_path)
    if not bool(green_summary.get("invariants_satisfied")):
        raise RehearsalError("green_shadow_invariants_failed")
    if shadow_dataset_checksum(green_shadow_path) != green_summary.get("shadow_dataset_sha256"):
        raise RehearsalError("green_shadow_dataset_checksum_mismatch")
    green_canonical_invalid = int(
        (green_summary.get("invariants") or {}).get("canonical_invalid_geography", -1)
    )

    with _sqlite_read_only(green_shadow_path) as source:
        green_transactions = _sqlite_scalar(source, "select count(*) from shadow_transactions")
        green_aggregates = _sqlite_scalar(source, "select count(*) from shadow_market_aggregates")
        period_min, period_max = source.execute(
            "select min(transaction_period), max(transaction_period) from shadow_transactions"
        ).fetchone()
        cities = _sqlite_scalar(source, "select count(distinct city) from shadow_transactions")
        units = _sqlite_scalar(
            source,
            "select count(distinct city || '|' || district || '|' || geographic_unit_kind) "
            "from shadow_transactions",
        )
        future = _sqlite_scalar(
            source,
            "select count(*) from shadow_transactions where transaction_period > ?",
            (GREEN_PERIOD_MAX,),
        )
        missing_lineage = _sqlite_scalar(
            source,
            "select count(*) from shadow_transactions "
            "where artifact_sha256 = '' or source_row_hash = '' or source_identity = ''",
        )
        conflicts = _sqlite_scalar(
            source,
            "select count(*) from shadow_source_conflicts where resolution_status = 'UNRESOLVED'",
        )

    expected_green = (
        green_transactions == GREEN_TRANSACTION_COUNT,
        green_aggregates == GREEN_AGGREGATE_COUNT,
        cities == GREEN_CITY_COUNT,
        units == GREEN_GEOGRAPHIC_UNIT_COUNT,
        period_min == GREEN_PERIOD_MIN,
        period_max == GREEN_PERIOD_MAX,
        green_canonical_invalid == 0,
        future == 0,
        missing_lineage == 0,
        conflicts == 0,
    )
    if not all(expected_green):
        raise RehearsalError("green_shadow_baseline_mismatch")

    residual = _read_json(residual_summary_path)
    blue_expected_sha = str(residual.get("production_snapshot_sha256") or "")
    with _sqlite_read_only(blue_snapshot_path) as source:
        metadata = {
            str(key): _decode_snapshot_metadata(value)
            for key, value in source.execute("select key, value from snapshot_metadata")
        }
        blue_transactions = _sqlite_scalar(source, "select count(*) from snapshot_transactions")
        blue_period_min, blue_period_max = source.execute(
            "select min(transaction_period), max(transaction_period) from snapshot_transactions"
        ).fetchone()
        actual_blue_sha = _snapshot_checksum(source)
    if (
        blue_transactions != BLUE_TRANSACTION_COUNT
        or metadata.get("snapshot_sha256") != blue_expected_sha
        or actual_blue_sha != blue_expected_sha
    ):
        raise RehearsalError("blue_snapshot_baseline_mismatch")

    return RehearsalSources(
        manifest_sha256=str(manifest["manifest_sha256"]),
        green_dataset_sha256=str(green_summary["shadow_dataset_sha256"]),
        blue_snapshot_sha256=blue_expected_sha,
        green_transactions=green_transactions,
        green_aggregates=green_aggregates,
        green_cities=cities,
        green_geographic_units=units,
        green_period_min=str(period_min),
        green_period_max=str(period_max),
        green_canonical_invalid=green_canonical_invalid,
        green_future_publishable=future,
        green_missing_lineage=missing_lineage,
        green_unresolved_conflicts=conflicts,
        blue_transactions=blue_transactions,
        blue_period_min=str(blue_period_min),
        blue_period_max=str(blue_period_max),
    )


def reset_rehearsal_schema(connection: Any) -> None:
    """Remove only the named Phase 2E objects from the guarded disposable DB."""

    for statement in _split_sql(RESET_SQL):
        connection.execute(statement)


def initialize_rehearsal_schema(connection: Any, schema_path: Path) -> None:
    """Apply the rehearsal-only SQL file to the guarded disposable DB."""

    sql = schema_path.read_text(encoding="utf-8")
    if "ISOLATED DATABASE ONLY" not in sql or "plvr_dataset_generations" not in sql:
        raise RehearsalError("rehearsal_schema_contract_invalid")
    for statement in _split_sql(sql):
        connection.execute(statement)
    required = {
        "plvr_dataset_generations",
        "plvr_generation_transactions",
        "plvr_generation_market_aggregates",
        "plvr_generation_region_coverage",
        "plvr_active_dataset",
    }
    rows = connection.execute(
        "select table_name from information_schema.tables "
        "where table_schema = 'public' and table_name = any(%s)",
        (list(required),),
    ).fetchall()
    if {row[0] for row in rows} != required:
        raise RehearsalError("rehearsal_schema_creation_failed")


def register_generation(
    connection: Any,
    *,
    generation_id: str,
    generation_role: str,
    manifest_sha256: str,
    dataset_sha256: str,
    expected_transactions: int,
    expected_aggregates: int,
    period_min: str,
    period_max: str,
    expected_cities: int,
    expected_units: int,
    canonical_invalid: int = 0,
    future_publishable: int = 0,
    lineage_missing: int = 0,
    unresolved_conflicts: int = 0,
) -> None:
    connection.execute(
        """
        insert into plvr_dataset_generations (
            dataset_key, generation_id, generation_role, state,
            source_manifest_sha256, dataset_sha256, expected_transaction_count,
            expected_aggregate_count, expected_period_min, expected_period_max,
            expected_city_count, expected_geographic_unit_count,
            canonical_invalid_count, future_publishable_count,
            lineage_missing_count, unresolved_source_conflict_count,
            manifest_frozen
        ) values (%s, %s, %s, 'registered', %s, %s, %s, %s, %s, %s, %s, %s,
                  %s, %s, %s, %s, true)
        """,
        (
            DATASET_KEY,
            generation_id,
            generation_role,
            manifest_sha256,
            dataset_sha256,
            expected_transactions,
            expected_aggregates,
            period_min,
            period_max,
            expected_cities,
            expected_units,
            canonical_invalid,
            future_publishable,
            lineage_missing,
            unresolved_conflicts,
        ),
    )
    _record_event(connection, generation_id, "generation_registered", {"role": generation_role})


def set_generation_state(connection: Any, generation_id: str, state: str) -> None:
    result = connection.execute(
        "update plvr_dataset_generations set state = %s where dataset_key = %s and generation_id = %s",
        (state, DATASET_KEY, generation_id),
    )
    if result.rowcount != 1:
        raise RehearsalError("generation_not_found")
    _record_event(connection, generation_id, "generation_state_changed", {"state": state})


def load_generation(
    connection: Any,
    *,
    generation_id: str,
    source_kind: str,
    source_path: Path,
    manifest_sha256: str,
    snapshot_sha256: str = "",
    batch_size: int = DEFAULT_BATCH_SIZE,
    interrupt_after_batches: int | None = None,
    finalize_state: bool = True,
) -> LoadResult:
    """Load one generation in restartable batches using a durable checkpoint."""

    if source_kind not in {"green_shadow", "blue_snapshot"}:
        raise RehearsalError("unsupported_rehearsal_source_kind")
    if batch_size < 100 or batch_size > 50_000:
        raise RehearsalError("invalid_rehearsal_batch_size")
    state = _generation_state(connection, generation_id)
    if state == "registered":
        set_generation_state(connection, generation_id, "loading")
    elif state not in {"loading", "loaded"}:
        checkpoint = _checkpoint(connection, generation_id)
        if checkpoint and checkpoint["complete"]:
            return _load_result(connection, generation_id, 0.0)
        raise RehearsalError("generation_not_loadable")

    connection.execute(
        """
        insert into plvr_generation_load_checkpoints (
            dataset_key, generation_id, source_kind
        ) values (%s, %s, %s)
        on conflict (dataset_key, generation_id) do nothing
        """,
        (DATASET_KEY, generation_id, source_kind),
    )
    _ensure_stage_table(connection)
    started = time.perf_counter()

    while True:
        checkpoint = _checkpoint(connection, generation_id)
        if checkpoint is None:
            raise RehearsalError("generation_checkpoint_missing")
        if checkpoint["complete"]:
            break
        rows = _read_source_batch(
            source_kind=source_kind,
            source_path=source_path,
            after_key=checkpoint["last_source_key"],
            batch_size=batch_size,
            generation_id=generation_id,
            manifest_sha256=manifest_sha256,
            snapshot_sha256=snapshot_sha256,
        )
        if not rows:
            connection.execute(
                """
                update plvr_generation_load_checkpoints
                set complete = true, updated_at = clock_timestamp()
                where dataset_key = %s and generation_id = %s
                """,
                (DATASET_KEY, generation_id),
            )
            if finalize_state and _generation_state(connection, generation_id) == "loading":
                set_generation_state(connection, generation_id, "loaded")
            break

        source_key, values = rows[-1][0], [item[1] for item in rows]
        with connection.transaction():
            inserted = _insert_transaction_batch(connection, values)
            connection.execute(
                """
                update plvr_generation_load_checkpoints
                set last_source_key = %s,
                    attempted_rows = attempted_rows + %s,
                    inserted_rows = inserted_rows + %s,
                    duplicate_rows = duplicate_rows + %s,
                    completed_batches = completed_batches + 1,
                    updated_at = clock_timestamp()
                where dataset_key = %s and generation_id = %s
                """,
                (
                    source_key,
                    len(values),
                    inserted,
                    len(values) - inserted,
                    DATASET_KEY,
                    generation_id,
                ),
            )
        checkpoint = _checkpoint(connection, generation_id)
        if interrupt_after_batches and checkpoint["completed_batches"] >= interrupt_after_batches:
            _record_event(
                connection,
                generation_id,
                "load_interrupted",
                {"after_batches": checkpoint["completed_batches"]},
            )
            break

    return _load_result(connection, generation_id, time.perf_counter() - started)


def finalize_generation_load(connection: Any, generation_id: str) -> None:
    checkpoint = _checkpoint(connection, generation_id)
    if checkpoint is None or not checkpoint["complete"]:
        raise RehearsalError("generation_load_incomplete")
    actual = _transaction_count(connection, generation_id, include_unpublishable=True)
    expected = connection.execute(
        "select expected_transaction_count from plvr_dataset_generations "
        "where dataset_key = %s and generation_id = %s",
        (DATASET_KEY, generation_id),
    ).fetchone()[0]
    if actual != expected:
        raise RehearsalError("generation_transaction_count_mismatch")
    if _generation_state(connection, generation_id) == "loading":
        set_generation_state(connection, generation_id, "loaded")


def replay_first_green_batch(
    connection: Any,
    *,
    generation_id: str,
    green_shadow_path: Path,
    manifest_sha256: str,
    batch_size: int,
) -> int:
    """Replay one authoritative batch and return duplicate-safe row count."""

    rows = _read_source_batch(
        source_kind="green_shadow",
        source_path=green_shadow_path,
        after_key="",
        batch_size=batch_size,
        generation_id=generation_id,
        manifest_sha256=manifest_sha256,
        snapshot_sha256="",
    )
    inserted = _insert_transaction_batch(connection, [item[1] for item in rows])
    duplicates = len(rows) - inserted
    connection.execute(
        """
        update plvr_generation_load_checkpoints
        set attempted_rows = attempted_rows + %s,
            inserted_rows = inserted_rows + %s,
            duplicate_rows = duplicate_rows + %s,
            updated_at = clock_timestamp()
        where dataset_key = %s and generation_id = %s
        """,
        (len(rows), inserted, duplicates, DATASET_KEY, generation_id),
    )
    return duplicates


def prepare_generation_derivatives(connection: Any, generation_id: str) -> None:
    state = _generation_state(connection, generation_id)
    if state == "loaded":
        set_generation_state(connection, generation_id, "aggregating")
    elif state != "aggregating":
        raise RehearsalError("generation_not_ready_for_aggregation")


def load_generation_coverage(
    connection: Any,
    *,
    generation_id: str,
    green_shadow_path: Path,
) -> int:
    """Build generation-scoped coverage from the verified Phase 2C matrix."""

    if _generation_state(connection, generation_id) != "aggregating":
        raise RehearsalError("generation_not_aggregating")
    with _sqlite_read_only(green_shadow_path) as source:
        rows = source.execute(
            """
            select county, district, geographic_unit_kind, period,
                   coverage_status, reason_code
            from shadow_coverage_matrix
            order by county, district, period
            """
        ).fetchall()
    with connection.cursor() as cursor:
        cursor.executemany(
            """
            insert into plvr_generation_region_coverage (
                dataset_key, generation_id, county, district,
                geographic_unit_kind, period, coverage_status, reason_code
            ) values (%s, %s, %s, %s, %s, %s, %s, %s)
            on conflict (generation_id, county, district, period)
            do update set
                geographic_unit_kind = excluded.geographic_unit_kind,
                coverage_status = excluded.coverage_status,
                reason_code = excluded.reason_code,
                built_at = clock_timestamp()
            """,
            [
                (
                    DATASET_KEY,
                    generation_id,
                    row[0],
                    row[1],
                    row[2],
                    row[3],
                    row[4],
                    row[5],
                )
                for row in rows
            ],
        )
    return int(
        connection.execute(
            "select count(*) from plvr_generation_region_coverage where generation_id = %s",
            (generation_id,),
        ).fetchone()[0]
    )


AGGREGATE_INSERT_SQL = """
insert into plvr_generation_market_aggregates (
    dataset_key, generation_id, county, district, geographic_unit_kind,
    period, average_unit_price, transaction_count, record_count,
    source_name, coverage_status, data_status, aggregation_method
)
select %s, %s, transaction.city, transaction.district,
       transaction.geographic_unit_kind, transaction.transaction_period,
       round(avg(transaction.unit_price_per_ping)::numeric, 2),
       count(*), count(*), 'official_plvr_opendata',
       coalesce((
           select coverage.coverage_status
           from plvr_generation_region_coverage coverage
           where coverage.generation_id = transaction.generation_id
             and coverage.county = transaction.city
             and coverage.period = transaction.transaction_period
           order by case coverage.coverage_status
               when 'COMPLETE' then 1
               when 'PARTIAL' then 2
               when 'MISSING' then 3
               else 4
           end
           limit 1
       ), 'PARTIAL'),
       'available', 'avg_unit_price_per_ping_by_city_district_period'
from plvr_generation_transactions transaction
where transaction.dataset_key = %s
  and transaction.generation_id = %s
  and transaction.publishable
group by transaction.generation_id, transaction.city, transaction.district,
         transaction.geographic_unit_kind, transaction.transaction_period
"""


def build_generation_aggregates(connection: Any, generation_id: str) -> int:
    """Rebuild deterministic aggregates from only one generation's rows."""

    if _generation_state(connection, generation_id) != "aggregating":
        raise RehearsalError("generation_not_aggregating")
    with connection.transaction():
        connection.execute(
            "delete from plvr_generation_market_aggregates where generation_id = %s",
            (generation_id,),
        )
        connection.execute(
            AGGREGATE_INSERT_SQL,
            (DATASET_KEY, generation_id, DATASET_KEY, generation_id),
        )
    count = _aggregate_count(connection, generation_id)
    _record_event(connection, generation_id, "aggregates_built", {"aggregate_count": count})
    return count


def inject_aggregate_transaction_failure(connection: Any, generation_id: str) -> bool:
    """Prove an interrupted aggregate transaction leaves no partial rows."""

    before = _aggregate_count(connection, generation_id)
    try:
        with connection.transaction():
            connection.execute(
                "delete from plvr_generation_market_aggregates where generation_id = %s",
                (generation_id,),
            )
            connection.execute(
                AGGREGATE_INSERT_SQL,
                (DATASET_KEY, generation_id, DATASET_KEY, generation_id),
            )
            raise RehearsalError("injected_aggregate_failure")
    except RehearsalError as error:
        if str(error) != "injected_aggregate_failure":
            raise
    after = _aggregate_count(connection, generation_id)
    passed = before == after
    _record_event(connection, generation_id, "aggregate_failure_injected", {"rollback_passed": passed})
    return passed


def compare_green_aggregates(
    connection: Any,
    *,
    generation_id: str,
    green_shadow_path: Path,
) -> int:
    """Return count of aggregate fields that diverge from the clean shadow."""

    with _sqlite_read_only(green_shadow_path) as source:
        expected = {
            (str(row[0]), str(row[1]), str(row[2])): (round(float(row[3]), 2), int(row[4]), str(row[5]))
            for row in source.execute(
                """
                select county, district, period, average_unit_price,
                       transaction_count, coverage_status
                from shadow_market_aggregates
                """
            )
        }
    actual = {
        (str(row[0]), str(row[1]), str(row[2])): (round(float(row[3]), 2), int(row[4]), str(row[5]))
        for row in connection.execute(
            """
            select county, district, period, average_unit_price,
                   transaction_count, coverage_status
            from plvr_generation_market_aggregates
            where generation_id = %s
            """,
            (generation_id,),
        ).fetchall()
    }
    mismatches = len(set(expected) ^ set(actual))
    for key in set(expected) & set(actual):
        expected_value = expected[key]
        actual_value = actual[key]
        if (
            _aggregate_price_delta(expected_value[0], actual_value[0]) > Decimal("0.01")
            or expected_value[1:] != actual_value[1:]
        ):
            mismatches += 1
    return mismatches


def _aggregate_price_delta(expected: float, actual: float) -> Decimal:
    """Compare two-cent aggregates without binary-float boundary drift."""

    return abs(Decimal(str(expected)) - Decimal(str(actual)))


def coverage_result(connection: Any, generation_id: str) -> dict[str, Any]:
    rows = connection.execute(
        """
        select coverage_status, count(*)
        from plvr_generation_region_coverage
        where generation_id = %s
        group by coverage_status
        """,
        (generation_id,),
    ).fetchall()
    counts = {str(status): int(count) for status, count in rows}
    expected_scope = counts.get("COMPLETE", 0) + counts.get("PARTIAL", 0) + counts.get("MISSING", 0)
    percent = round(100 * counts.get("COMPLETE", 0) / expected_scope, 2) if expected_scope else 0.0
    return {
        "status_counts": counts,
        "expected_scope_count": expected_scope,
        "official_coverage_percent": percent,
        "missing_scope_count": counts.get("MISSING", 0),
        "passed": percent == EXPECTED_COVERAGE_PERCENT and counts.get("MISSING", 0) == 0,
    }


def validate_green_generation(
    connection: Any,
    *,
    generation_id: str,
    green_shadow_path: Path,
    gate_artifact_path: Path,
    aggregate_attribution_path: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    """Execute all 15 fail-closed Phase 2D hard gates."""

    gates_artifact = _read_json(gate_artifact_path)
    attribution = _read_json(aggregate_attribution_path)
    golden_source = attribution.get("golden_regions") or []
    if len(gates_artifact.get("gates") or []) != 15 or len(golden_source) != 7:
        raise RehearsalError("phase2d_gate_artifact_invalid")

    row = connection.execute(
        """
        select count(*),
               count(*) filter (where canonical_status <> 'canonical_valid'),
               count(*) filter (where publishable and transaction_period > %s),
               count(*) filter (
                   where source_manifest_sha256 = '' or source_artifact_sha256 = ''
                      or source_row_hash = '' or source_identity = ''
               ),
               min(transaction_period), max(transaction_period),
               count(distinct city),
               count(distinct city || '|' || district || '|' || geographic_unit_kind)
        from plvr_generation_transactions
        where dataset_key = %s and generation_id = %s
        """,
        (GREEN_PERIOD_MAX, DATASET_KEY, generation_id),
    ).fetchone()
    duplicate_identity_count = int(
        connection.execute(
            """
            select count(*) from (
                select source_identity
                from plvr_generation_transactions
                where generation_id = %s
                group by source_identity having count(*) > 1
            ) duplicate
            """,
            (generation_id,),
        ).fetchone()[0]
    )
    generation = connection.execute(
        """
        select unresolved_source_conflict_count, expected_transaction_count,
               expected_aggregate_count, expected_period_min, expected_period_max,
               expected_city_count, expected_geographic_unit_count
        from plvr_dataset_generations
        where dataset_key = %s and generation_id = %s
        """,
        (DATASET_KEY, generation_id),
    ).fetchone()
    aggregate_count = _aggregate_count(connection, generation_id)
    aggregate_mismatches = compare_green_aggregates(
        connection,
        generation_id=generation_id,
        green_shadow_path=green_shadow_path,
    )
    golden = _validate_golden_regions(connection, generation_id, golden_source)
    golden_passed = sum(int(item["passed"]) for item in golden)
    valuation_passed = all(item["valuation_read_passed"] for item in golden)
    market_passed = all(item["market_insight_read_passed"] for item in golden)

    checks = [
        ("transaction_row_count", int(row[0]) == int(generation[1]), {"actual": int(row[0]), "expected": int(generation[1])}),
        ("canonical_geography_invalid_count", int(row[1]) == 0, {"actual": int(row[1]), "expected": 0}),
        ("future_publishable_row_count", int(row[2]) == 0, {"actual": int(row[2]), "expected": 0}),
        ("lineage_missing_count", int(row[3]) == 0, {"actual": int(row[3]), "expected": 0}),
        ("source_conflict_count", int(generation[0]) == 0, {"actual": int(generation[0]), "expected": 0}),
        ("duplicate_authoritative_identity_count", duplicate_identity_count == 0, {"actual": duplicate_identity_count, "expected": 0}),
        ("period_range", row[4] == generation[3] and row[5] == generation[4], {"actual": [row[4], row[5]], "expected": [generation[3], generation[4]]}),
        ("city_coverage", int(row[6]) == int(generation[5]), {"actual": int(row[6]), "expected": int(generation[5])}),
        ("geographic_unit_coverage", int(row[7]) == int(generation[6]), {"actual": int(row[7]), "expected": int(generation[6])}),
        ("aggregate_scope_count", aggregate_count == int(generation[2]), {"actual": aggregate_count, "expected": int(generation[2])}),
        ("aggregate_unexplained_scope_count", aggregate_mismatches == 0, {"actual": aggregate_mismatches, "expected": 0}),
        ("golden_region_validation", golden_passed == 7, {"actual": golden_passed, "expected": 7}),
        ("valuation_smoke", valuation_passed, {"passed_regions": sum(int(item["valuation_read_passed"]) for item in golden), "expected": 7}),
        ("market_insight_smoke", market_passed, {"passed_regions": sum(int(item["market_insight_read_passed"]) for item in golden), "expected": 7}),
    ]
    results = [_gate_result(*check) for check in checks]
    if not all(item["result"] == "PASS" for item in results):
        return results, golden, {"aggregate_mismatches": aggregate_mismatches}

    connection.execute(
        """
        update plvr_dataset_generations
        set state = 'validated', validated_at = clock_timestamp()
        where dataset_key = %s and generation_id = %s and state = 'aggregating'
        """,
        (DATASET_KEY, generation_id),
    )
    pointer = connection.execute(
        "select active_generation_id from plvr_active_dataset where dataset_key = %s",
        (DATASET_KEY,),
    ).fetchone()
    status_passed = _generation_state(connection, generation_id) == "validated" and pointer is not None and pointer[0] != generation_id
    results.append(
        _gate_result(
            "read_model_status",
            status_passed,
            {
                "candidate_state": _generation_state(connection, generation_id),
                "candidate_active": bool(pointer and pointer[0] == generation_id),
                "expected_state": "validated_inactive",
            },
        )
    )
    if [item["gate_id"] for item in results] != [item["id"] for item in gates_artifact["gates"]]:
        raise RehearsalError("phase2d_gate_order_mismatch")
    _record_event(connection, generation_id, "hard_gates_executed", {"passed": 15, "total": 15})
    return results, golden, {
        "aggregate_mismatches": aggregate_mismatches,
        "transaction_count": int(row[0]),
        "aggregate_count": aggregate_count,
        "period_min": row[4],
        "period_max": row[5],
        "cities": int(row[6]),
        "geographic_units": int(row[7]),
    }


def activate_initial_generation(connection: Any, generation_id: str) -> None:
    if _generation_state(connection, generation_id) != "validated":
        raise RehearsalError("initial_generation_not_validated")
    with connection.transaction():
        connection.execute(
            "update plvr_dataset_generations set state = 'active' "
            "where dataset_key = %s and generation_id = %s",
            (DATASET_KEY, generation_id),
        )
        connection.execute(
            """
            insert into plvr_active_dataset (
                dataset_key, active_generation_id, previous_generation_id
            ) values (%s, %s, null)
            """,
            (DATASET_KEY, generation_id),
        )
    _record_event(connection, generation_id, "initial_generation_activated", {})


def switch_active_generation(
    connection: Any,
    target_generation_id: str,
    *,
    inject_failure_before_commit: bool = False,
) -> SwitchResult:
    """Atomically switch all readers by updating one locked pointer row."""

    started = time.perf_counter()
    previous = ""
    try:
        with connection.transaction():
            pointer = connection.execute(
                """
                select active_generation_id
                from plvr_active_dataset
                where dataset_key = %s
                for update
                """,
                (DATASET_KEY,),
            ).fetchone()
            if pointer is None:
                raise RehearsalError("active_generation_pointer_missing")
            previous = str(pointer[0])
            target = connection.execute(
                """
                select state from plvr_dataset_generations
                where dataset_key = %s and generation_id = %s
                for update
                """,
                (DATASET_KEY, target_generation_id),
            ).fetchone()
            if target is None or target[0] not in {"validated", "inactive"}:
                raise RehearsalError("target_generation_not_validated")
            connection.execute(
                "update plvr_dataset_generations set state = 'inactive' "
                "where dataset_key = %s and generation_id = %s",
                (DATASET_KEY, previous),
            )
            connection.execute(
                "update plvr_dataset_generations set state = 'active' "
                "where dataset_key = %s and generation_id = %s",
                (DATASET_KEY, target_generation_id),
            )
            connection.execute(
                """
                update plvr_active_dataset
                set previous_generation_id = %s,
                    active_generation_id = %s,
                    switch_sequence = switch_sequence + 1,
                    switched_at = clock_timestamp()
                where dataset_key = %s
                """,
                (previous, target_generation_id, DATASET_KEY),
            )
            if inject_failure_before_commit:
                raise RehearsalError("injected_pointer_transaction_failure")
    except RehearsalError:
        if inject_failure_before_commit:
            raise
        raise
    duration = time.perf_counter() - started
    _record_event(
        connection,
        target_generation_id,
        "active_generation_switched",
        {"previous_generation_id": previous, "duration_seconds": round(duration, 6)},
    )
    return SwitchResult(previous, target_generation_id, duration)


def activation_is_rejected(connection: Any, generation_id: str) -> bool:
    """Return true only when a nonvalidated generation cannot replace the pointer."""

    before = _active_generation_id(connection)
    try:
        switch_active_generation(connection, generation_id)
    except Exception:
        return _active_generation_id(connection) == before
    return False


def pointer_transaction_failure_rolls_back(connection: Any, generation_id: str) -> bool:
    before = _active_generation_id(connection)
    before_states = _generation_states(connection, [before, generation_id])
    try:
        switch_active_generation(connection, generation_id, inject_failure_before_commit=True)
    except RehearsalError as error:
        if str(error) != "injected_pointer_transaction_failure":
            raise
    return (
        _active_generation_id(connection) == before
        and _generation_states(connection, [before, generation_id]) == before_states
    )


def dual_read_rehearsal(
    connection: Any,
    *,
    blue_generation_id: str,
    green_generation_id: str,
    aggregate_attribution_path: Path,
) -> dict[str, Any]:
    """Compare explicit BLUE/GREEN reads against committed Phase 2C.7 evidence."""

    evidence = _read_json(aggregate_attribution_path)
    attribution = evidence["aggregate_attribution"]
    golden_evidence = evidence["golden_regions"]
    blue_transactions = _transaction_count(connection, blue_generation_id, include_unpublishable=True)
    green_transactions = _transaction_count(connection, green_generation_id, include_unpublishable=True)
    blue_aggregates = _aggregate_count(connection, blue_generation_id)
    green_aggregates = _aggregate_count(connection, green_generation_id)
    region_checks: list[dict[str, Any]] = []
    for region in golden_evidence:
        county = str(region["county"])
        district = str(region["district"])
        blue_count = _region_transaction_count(connection, blue_generation_id, county, district)
        green_count = _region_transaction_count(connection, green_generation_id, county, district)
        region_checks.append(
            {
                "county": county,
                "district": district,
                "blue_transaction_count": blue_count,
                "green_transaction_count": green_count,
                "expected_blue_transaction_count": int(region["production_transaction_count"]),
                "expected_green_transaction_count": int(region["shadow_transaction_count"]),
                "classification": (
                    "EXPECTED_CORRECTION"
                    if blue_count != green_count
                    else "EXPECTED_EXACT_MATCH"
                ),
                "passed": (
                    blue_count == int(region["production_transaction_count"])
                    and green_count == int(region["shadow_transaction_count"])
                ),
            }
        )
    passed = all(
        (
            _active_generation_id(connection) == blue_generation_id,
            blue_transactions == BLUE_TRANSACTION_COUNT,
            green_transactions == GREEN_TRANSACTION_COUNT,
            blue_aggregates == int(attribution["production_aggregate_scopes"]),
            green_aggregates == int(attribution["shadow_aggregate_scopes"]),
            int(attribution["unexplained_scopes"]) == 0,
            bool(attribution["status_conserved"]),
            all(item["passed"] for item in region_checks),
        )
    )
    return {
        "status": "PASS" if passed else "FAIL",
        "active_generation": _active_generation_id(connection),
        "blue_transaction_count": blue_transactions,
        "green_transaction_count": green_transactions,
        "blue_aggregate_count": blue_aggregates,
        "green_aggregate_count": green_aggregates,
        "unexpected_shadow_differences": 0 if passed else 1,
        "bounded_difference_evidence": "plvr-aggregate-delta-attribution-v1",
        "regions": region_checks,
    }


def active_reader_acceptance(
    connection: Any,
    *,
    expected_generation_id: str,
    expected_transactions: int,
    expected_aggregates: int,
    expected_latest_period: str,
    require_green_invariants: bool,
) -> dict[str, Any]:
    """Verify every active reader resolves one and the same generation."""

    transaction_row = connection.execute(
        """
        select count(*), count(distinct generation_id), min(generation_id),
               max(transaction_period),
               count(*) filter (where publishable and transaction_period > %s)
        from plvr_active_transactions
        """,
        (GREEN_PERIOD_MAX,),
    ).fetchone()
    aggregate_row = connection.execute(
        """
        select count(*), count(distinct generation_id), min(generation_id), max(period)
        from plvr_active_market_aggregates
        """
    ).fetchone()
    coverage_row = connection.execute(
        """
        select count(*), count(distinct generation_id), min(generation_id)
        from plvr_active_region_coverage
        """
    ).fetchone()
    same_generation = (
        transaction_row[2] == expected_generation_id
        and aggregate_row[2] == expected_generation_id
        and coverage_row[2] == expected_generation_id
        and int(transaction_row[1]) == 1
        and int(aggregate_row[1]) == 1
        and int(coverage_row[1]) == 1
    )
    passed = (
        _active_generation_id(connection) == expected_generation_id
        and int(transaction_row[0]) == expected_transactions
        and int(aggregate_row[0]) == expected_aggregates
        and same_generation
    )
    if require_green_invariants:
        passed = passed and transaction_row[3] == expected_latest_period and aggregate_row[3] == expected_latest_period
        passed = passed and int(transaction_row[4]) == 0
    return {
        "status": "PASS" if passed else "FAIL",
        "active_generation_id": _active_generation_id(connection),
        "transaction_generation_id": transaction_row[2],
        "aggregate_generation_id": aggregate_row[2],
        "coverage_generation_id": coverage_row[2],
        "transaction_count": int(transaction_row[0]),
        "aggregate_count": int(aggregate_row[0]),
        "coverage_count": int(coverage_row[0]),
        "latest_transaction_period": transaction_row[3],
        "latest_aggregate_period": aggregate_row[3],
        "future_publishable_count": int(transaction_row[4]),
        "mixed_generation_count": 0 if same_generation else 1,
    }


def run_phase2e_rehearsal(
    *,
    schema_path: Path,
    manifest_path: Path,
    artifact_root: Path,
    green_shadow_path: Path,
    green_summary_path: Path,
    blue_snapshot_path: Path,
    residual_summary_path: Path,
    gate_artifact_path: Path,
    aggregate_attribution_path: Path,
    output_dir: Path,
    batch_size: int = DEFAULT_BATCH_SIZE,
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Run the full cutover rehearsal and persist only privacy-bounded evidence."""

    target = inspect_dry_run_target(environ)
    sources = validate_source_bundle(
        manifest_path=manifest_path,
        artifact_root=artifact_root,
        green_shadow_path=green_shadow_path,
        green_summary_path=green_summary_path,
        blue_snapshot_path=blue_snapshot_path,
        residual_summary_path=residual_summary_path,
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    with connect_dry_run(environ) as connection:
        reset_rehearsal_schema(connection)
        initialize_rehearsal_schema(connection, schema_path)

        register_generation(
            connection,
            generation_id=BLUE_GENERATION_ID,
            generation_role="legacy",
            manifest_sha256=sources.blue_snapshot_sha256,
            dataset_sha256=sources.blue_snapshot_sha256,
            expected_transactions=sources.blue_transactions,
            expected_aggregates=BLUE_AGGREGATE_COUNT,
            period_min=sources.blue_period_min,
            period_max=GREEN_PERIOD_MAX,
            expected_cities=0,
            expected_units=0,
        )
        blue_load = load_generation(
            connection,
            generation_id=BLUE_GENERATION_ID,
            source_kind="blue_snapshot",
            source_path=blue_snapshot_path,
            manifest_sha256=sources.blue_snapshot_sha256,
            snapshot_sha256=sources.blue_snapshot_sha256,
            batch_size=batch_size,
        )
        finalize_generation_load(connection, BLUE_GENERATION_ID)
        prepare_generation_derivatives(connection, BLUE_GENERATION_ID)
        load_generation_coverage(
            connection,
            generation_id=BLUE_GENERATION_ID,
            green_shadow_path=green_shadow_path,
        )
        blue_aggregates = build_generation_aggregates(connection, BLUE_GENERATION_ID)
        if blue_aggregates != BLUE_AGGREGATE_COUNT:
            raise RehearsalError("blue_aggregate_count_mismatch")
        set_generation_state(connection, BLUE_GENERATION_ID, "validated")
        activate_initial_generation(connection, BLUE_GENERATION_ID)

        register_generation(
            connection,
            generation_id=GREEN_GENERATION_ID,
            generation_role="candidate",
            manifest_sha256=sources.manifest_sha256,
            dataset_sha256=sources.green_dataset_sha256,
            expected_transactions=sources.green_transactions,
            expected_aggregates=sources.green_aggregates,
            period_min=sources.green_period_min,
            period_max=sources.green_period_max,
            expected_cities=sources.green_cities,
            expected_units=sources.green_geographic_units,
            canonical_invalid=sources.green_canonical_invalid,
            future_publishable=sources.green_future_publishable,
            lineage_missing=sources.green_missing_lineage,
            unresolved_conflicts=sources.green_unresolved_conflicts,
        )
        registered_activation_rejected = activation_is_rejected(connection, GREEN_GENERATION_ID)
        partial = load_generation(
            connection,
            generation_id=GREEN_GENERATION_ID,
            source_kind="green_shadow",
            source_path=green_shadow_path,
            manifest_sha256=sources.manifest_sha256,
            batch_size=batch_size,
            interrupt_after_batches=3,
            finalize_state=False,
        )
        partial_activation_rejected = activation_is_rejected(connection, GREEN_GENERATION_ID)
        resumed = load_generation(
            connection,
            generation_id=GREEN_GENERATION_ID,
            source_kind="green_shadow",
            source_path=green_shadow_path,
            manifest_sha256=sources.manifest_sha256,
            batch_size=batch_size,
            finalize_state=False,
        )
        duplicate_replay = replay_first_green_batch(
            connection,
            generation_id=GREEN_GENERATION_ID,
            green_shadow_path=green_shadow_path,
            manifest_sha256=sources.manifest_sha256,
            batch_size=batch_size,
        )
        finalize_generation_load(connection, GREEN_GENERATION_ID)
        resumed = _load_result(connection, GREEN_GENERATION_ID, resumed.elapsed_seconds)
        loaded_activation_rejected = activation_is_rejected(connection, GREEN_GENERATION_ID)

        prepare_generation_derivatives(connection, GREEN_GENERATION_ID)
        green_coverage_count = load_generation_coverage(
            connection,
            generation_id=GREEN_GENERATION_ID,
            green_shadow_path=green_shadow_path,
        )
        aggregate_failure_rollback = inject_aggregate_transaction_failure(connection, GREEN_GENERATION_ID)
        green_aggregates = build_generation_aggregates(connection, GREEN_GENERATION_ID)
        first_aggregate_snapshot = _aggregate_fingerprint(connection, GREEN_GENERATION_ID)
        green_aggregates_repeat = build_generation_aggregates(connection, GREEN_GENERATION_ID)
        second_aggregate_snapshot = _aggregate_fingerprint(connection, GREEN_GENERATION_ID)
        coverage_repeat = load_generation_coverage(
            connection,
            generation_id=GREEN_GENERATION_ID,
            green_shadow_path=green_shadow_path,
        )
        manifest_immutable = _manifest_mutation_is_rejected(connection, GREEN_GENERATION_ID)

        gates, golden, green_metrics = validate_green_generation(
            connection,
            generation_id=GREEN_GENERATION_ID,
            green_shadow_path=green_shadow_path,
            gate_artifact_path=gate_artifact_path,
            aggregate_attribution_path=aggregate_attribution_path,
        )
        hard_gates_passed = sum(int(item["result"] == "PASS") for item in gates)
        if hard_gates_passed != 15:
            raise RehearsalError("hard_gate_failure_blocks_switch")
        coverage = coverage_result(connection, GREEN_GENERATION_ID)
        if not coverage["passed"]:
            raise RehearsalError("coverage_gate_failed")

        dual_read = dual_read_rehearsal(
            connection,
            blue_generation_id=BLUE_GENERATION_ID,
            green_generation_id=GREEN_GENERATION_ID,
            aggregate_attribution_path=aggregate_attribution_path,
        )
        if dual_read["status"] != "PASS":
            raise RehearsalError("dual_read_rehearsal_failed")

        register_generation(
            connection,
            generation_id="official-plvr-failure-fixture",
            generation_role="failure_fixture",
            manifest_sha256="f" * 64,
            dataset_sha256="f" * 64,
            expected_transactions=1,
            expected_aggregates=1,
            period_min=GREEN_PERIOD_MIN,
            period_max=GREEN_PERIOD_MAX,
            expected_cities=1,
            expected_units=1,
        )
        set_generation_state(connection, "official-plvr-failure-fixture", "failed")
        failed_generation_activation_rejected = activation_is_rejected(
            connection, "official-plvr-failure-fixture"
        )
        pre_switch_active = _active_generation_id(connection)
        pointer_failure_rollback = pointer_transaction_failure_rolls_back(connection, GREEN_GENERATION_ID)
        if _active_generation_id(connection) != pre_switch_active:
            raise RehearsalError("pre_switch_pointer_changed")

        cutover = switch_active_generation(connection, GREEN_GENERATION_ID)
        post_switch = active_reader_acceptance(
            connection,
            expected_generation_id=GREEN_GENERATION_ID,
            expected_transactions=GREEN_TRANSACTION_COUNT,
            expected_aggregates=GREEN_AGGREGATE_COUNT,
            expected_latest_period=GREEN_PERIOD_MAX,
            require_green_invariants=True,
        )
        if post_switch["status"] != "PASS":
            raise RehearsalError("post_switch_acceptance_failed")

        rollback = switch_active_generation(connection, BLUE_GENERATION_ID)
        rollback_acceptance = active_reader_acceptance(
            connection,
            expected_generation_id=BLUE_GENERATION_ID,
            expected_transactions=BLUE_PUBLISHABLE_TRANSACTION_COUNT,
            expected_aggregates=BLUE_AGGREGATE_COUNT,
            expected_latest_period=GREEN_PERIOD_MAX,
            require_green_invariants=False,
        )
        green_retained_after_rollback = (
            _transaction_count(connection, GREEN_GENERATION_ID, include_unpublishable=True)
            == GREEN_TRANSACTION_COUNT
            and _aggregate_count(connection, GREEN_GENERATION_ID) == GREEN_AGGREGATE_COUNT
        )
        if rollback_acceptance["status"] != "PASS" or not green_retained_after_rollback:
            raise RehearsalError("rollback_acceptance_failed")

        switch_forward = switch_active_generation(connection, GREEN_GENERATION_ID)
        switch_forward_acceptance = active_reader_acceptance(
            connection,
            expected_generation_id=GREEN_GENERATION_ID,
            expected_transactions=GREEN_TRANSACTION_COUNT,
            expected_aggregates=GREEN_AGGREGATE_COUNT,
            expected_latest_period=GREEN_PERIOD_MAX,
            require_green_invariants=True,
        )
        if switch_forward_acceptance["status"] != "PASS":
            raise RehearsalError("switch_forward_acceptance_failed")

        complete_noop = load_generation(
            connection,
            generation_id=GREEN_GENERATION_ID,
            source_kind="green_shadow",
            source_path=green_shadow_path,
            manifest_sha256=sources.manifest_sha256,
            batch_size=batch_size,
        )
        failure_checks = {
            "registered_before_load_activation_rejected": registered_activation_rejected,
            "partial_load_activation_rejected": partial_activation_rejected,
            "loaded_before_aggregate_activation_rejected": loaded_activation_rejected,
            "aggregate_transaction_rollback": aggregate_failure_rollback,
            "failed_generation_activation_rejected": failed_generation_activation_rejected,
            "pre_switch_pointer_unchanged": pre_switch_active == BLUE_GENERATION_ID,
            "pointer_transaction_rollback": pointer_failure_rollback,
            "manifest_immutable_after_freeze": manifest_immutable,
        }
        idempotency_checks = {
            "duplicate_batch_inserted_zero": duplicate_replay == batch_size,
            "aggregate_count_stable": green_aggregates == green_aggregates_repeat == GREEN_AGGREGATE_COUNT,
            "aggregate_fingerprint_stable": first_aggregate_snapshot == second_aggregate_snapshot,
            "coverage_count_stable": green_coverage_count == coverage_repeat,
            "completed_load_noop": complete_noop.final_rows == GREEN_TRANSACTION_COUNT,
            "single_active_pointer": _active_pointer_count(connection) == 1,
        }
        if not all(failure_checks.values()):
            raise RehearsalError("failure_injection_rehearsal_failed")
        if not all(idempotency_checks.values()):
            raise RehearsalError("idempotency_rehearsal_failed")

        summary = {
            "schema_version": "plvr-cutover-rehearsal-summary-v1",
            "mode": "isolated_dry_run",
            "database": {
                "host_class": target.host_class,
                "database_name": target.database_name,
                "database_user": target.database_user,
                "postgres_version": target.postgres_version,
            },
            "blue_simulation_mode": "FULL_BLUE_SIMULATION",
            "blue_generation_id": BLUE_GENERATION_ID,
            "green_generation_id": GREEN_GENERATION_ID,
            "sources": asdict(sources),
            "blue_load": asdict(blue_load),
            "green_partial_load": asdict(partial),
            "green_final_load": asdict(resumed),
            "green_metrics": green_metrics,
            "green_coverage": coverage,
            "hard_gates_passed": hard_gates_passed,
            "hard_gates_total": len(gates),
            "golden_regions_passed": sum(int(item["passed"]) for item in golden),
            "golden_regions_total": len(golden),
            "dual_read_status": dual_read["status"],
            "cutover_switch": asdict(cutover),
            "post_switch_acceptance": post_switch,
            "rollback": asdict(rollback),
            "rollback_acceptance": rollback_acceptance,
            "switch_forward": asdict(switch_forward),
            "switch_forward_acceptance": switch_forward_acceptance,
            "failure_injection_passed": all(failure_checks.values()),
            "resume_passed": resumed.complete and resumed.final_rows == GREEN_TRANSACTION_COUNT,
            "idempotency_passed": all(idempotency_checks.values()),
            "production_connection_attempts": 0,
            "production_ddl": 0,
            "production_dml": 0,
            "production_writes": 0,
            "production_pointer_switch": False,
            "production_approvals_executed": [],
        }
        _write_json(output_dir / "plvr_cutover_rehearsal_summary.json", summary)
        _write_json(
            output_dir / "plvr_cutover_rehearsal_gates.json",
            {
                "schema_version": "plvr-cutover-rehearsal-gates-v1",
                "gates": gates,
                "golden_regions": golden,
            },
        )
        _write_json(
            output_dir / "plvr_cutover_rehearsal_switch.json",
            {
                "schema_version": "plvr-cutover-rehearsal-switch-v1",
                "before": BLUE_GENERATION_ID,
                "after": GREEN_GENERATION_ID,
                "result": asdict(cutover),
                "acceptance": post_switch,
                "atomic": True,
            },
        )
        _write_json(
            output_dir / "plvr_cutover_rehearsal_rollback.json",
            {
                "schema_version": "plvr-cutover-rehearsal-rollback-v1",
                "from": GREEN_GENERATION_ID,
                "to": BLUE_GENERATION_ID,
                "result": asdict(rollback),
                "acceptance": rollback_acceptance,
                "green_retained": green_retained_after_rollback,
                "under_five_minutes": rollback.duration_seconds < 300,
                "switch_forward": asdict(switch_forward),
                "switch_forward_acceptance": switch_forward_acceptance,
            },
        )
        _write_json(
            output_dir / "plvr_cutover_rehearsal_failure_injection.json",
            {
                "schema_version": "plvr-cutover-rehearsal-failure-injection-v1",
                "failure_checks": failure_checks,
                "idempotency_checks": idempotency_checks,
                "duplicate_replay_rows": duplicate_replay,
            },
        )
        return summary


def _read_source_batch(
    *,
    source_kind: str,
    source_path: Path,
    after_key: str,
    batch_size: int,
    generation_id: str,
    manifest_sha256: str,
    snapshot_sha256: str,
) -> list[tuple[str, tuple[Any, ...]]]:
    with _sqlite_read_only(source_path) as source:
        source.row_factory = sqlite3.Row
        if source_kind == "green_shadow":
            rows = source.execute(
                """
                select source_row_hash, source_identity, artifact_sha256,
                       official_transaction_id, official_transfer_id,
                       business_dedupe_key, production_fact_hash,
                       transaction_period, city, district, geographic_unit_kind,
                       road, address_text, building_type, area_ping,
                       building_age_years, floor, total_floor,
                       unit_price_per_ping, total_price, source
                from shadow_transactions
                where source_row_hash > ?
                order by source_row_hash
                limit ?
                """,
                (after_key, batch_size),
            ).fetchall()
            return [
                (
                    str(row["source_row_hash"]),
                    (
                        DATASET_KEY,
                        generation_id,
                        row["source_row_hash"],
                        row["source_identity"],
                        manifest_sha256,
                        row["artifact_sha256"],
                        row["official_transaction_id"],
                        row["official_transfer_id"],
                        row["business_dedupe_key"],
                        row["production_fact_hash"],
                        row["transaction_period"],
                        row["city"],
                        row["district"],
                        row["geographic_unit_kind"],
                        row["road"] or "",
                        row["address_text"] or "",
                        row["building_type"] or "",
                        float(row["area_ping"] or 0),
                        float(row["building_age_years"] or 0),
                        int(row["floor"] or 0),
                        int(row["total_floor"]) if row["total_floor"] is not None else None,
                        float(row["unit_price_per_ping"] or 0),
                        float(row["total_price"] or 0),
                        row["source"],
                        "canonical_valid",
                        True,
                    ),
                )
                for row in rows
            ]

        last_id = int(after_key or 0)
        rows = source.execute(
            """
            select stable_id, transaction_period, city, district, road,
                   address_text, building_type, area_ping, building_age_years,
                   floor, total_floor, unit_price_per_ping, total_price,
                   source, dedupe_key, production_fact_hash
            from snapshot_transactions
            where stable_id > ?
            order by stable_id
            limit ?
            """,
            (last_id, batch_size),
        ).fetchall()
        transformed: list[tuple[str, tuple[Any, ...]]] = []
        for row in rows:
            stable_id = int(row["stable_id"])
            if not str(row["dedupe_key"] or "").strip():
                raise RehearsalError("blue_snapshot_dedupe_key_missing")
            source_hash = hashlib.sha256(
                f"{snapshot_sha256}:{stable_id}".encode("utf-8")
            ).hexdigest()
            transformed.append(
                (
                    str(stable_id),
                    (
                        DATASET_KEY,
                        generation_id,
                        source_hash,
                        f"legacy:{stable_id}",
                        snapshot_sha256,
                        snapshot_sha256,
                        "",
                        "",
                        row["dedupe_key"],
                        row["production_fact_hash"],
                        row["transaction_period"],
                        str(row["city"] or "").replace("台", "臺"),
                        row["district"],
                        "district" if str(row["district"] or "").strip() else "city_level",
                        row["road"] or "",
                        row["address_text"] or "",
                        row["building_type"] or "",
                        float(row["area_ping"] or 0),
                        float(row["building_age_years"] or 0),
                        int(row["floor"] or 0),
                        int(row["total_floor"]) if row["total_floor"] is not None else None,
                        float(row["unit_price_per_ping"] or 0),
                        float(row["total_price"] or 0),
                        row["source"],
                        "legacy_unverified",
                        str(row["transaction_period"]) <= GREEN_PERIOD_MAX,
                    ),
                )
            )
        return transformed


def _ensure_stage_table(connection: Any) -> None:
    connection.execute(
        """
        create temporary table if not exists plvr_rehearsal_transaction_stage
        (like plvr_generation_transactions including defaults)
        on commit preserve rows
        """
    )


def _insert_transaction_batch(connection: Any, rows: Sequence[tuple[Any, ...]]) -> int:
    if not rows:
        return 0
    columns = ", ".join(TRANSACTION_COLUMNS)
    with connection.cursor() as cursor:
        cursor.execute("truncate table plvr_rehearsal_transaction_stage")
        with cursor.copy(
            f"copy plvr_rehearsal_transaction_stage ({columns}) from stdin"
        ) as copy:
            for row in rows:
                copy.write_row(row)
        cursor.execute(
            f"""
            insert into plvr_generation_transactions ({columns})
            select {columns} from plvr_rehearsal_transaction_stage
            on conflict do nothing
            """
        )
        return int(cursor.rowcount)


def _checkpoint(connection: Any, generation_id: str) -> dict[str, Any] | None:
    row = connection.execute(
        """
        select source_kind, last_source_key, attempted_rows, inserted_rows,
               duplicate_rows, completed_batches, complete
        from plvr_generation_load_checkpoints
        where dataset_key = %s and generation_id = %s
        """,
        (DATASET_KEY, generation_id),
    ).fetchone()
    if row is None:
        return None
    return {
        "source_kind": str(row[0]),
        "last_source_key": str(row[1]),
        "attempted_rows": int(row[2]),
        "inserted_rows": int(row[3]),
        "duplicate_rows": int(row[4]),
        "completed_batches": int(row[5]),
        "complete": bool(row[6]),
    }


def _load_result(connection: Any, generation_id: str, elapsed: float) -> LoadResult:
    checkpoint = _checkpoint(connection, generation_id)
    if checkpoint is None:
        raise RehearsalError("generation_checkpoint_missing")
    return LoadResult(
        attempted_rows=checkpoint["attempted_rows"],
        inserted_rows=checkpoint["inserted_rows"],
        duplicate_rows=checkpoint["duplicate_rows"],
        completed_batches=checkpoint["completed_batches"],
        final_rows=_transaction_count(connection, generation_id, include_unpublishable=True),
        complete=checkpoint["complete"],
        elapsed_seconds=round(elapsed, 6),
    )


def _validate_golden_regions(
    connection: Any,
    generation_id: str,
    golden_source: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for expected in golden_source:
        county = str(expected["county"])
        district = str(expected["district"])
        transaction = connection.execute(
            """
            select count(*), avg(unit_price_per_ping),
                   count(*) filter (
                       where source_artifact_sha256 = '' or source_row_hash = ''
                   )
            from plvr_generation_transactions
            where generation_id = %s and city = %s and district = %s
            """,
            (generation_id, county, district),
        ).fetchone()
        market = connection.execute(
            """
            select count(*), max(period), coalesce(sum(transaction_count), 0),
                   count(*) filter (where source_name = '' or coverage_status = '')
            from plvr_generation_market_aggregates
            where generation_id = %s and county = %s and district = %s
            """,
            (generation_id, county, district),
        ).fetchone()
        transaction_count = int(transaction[0])
        history_length = int(market[0])
        valuation_passed = transaction_count > 0 and float(transaction[1] or 0) > 0
        market_passed = (
            history_length == int(expected["history_length"])
            and market[1] == expected["latest_publishable_period"]
            and int(market[2]) == transaction_count
            and int(market[3]) == 0
        )
        passed = (
            transaction_count == int(expected["shadow_transaction_count"])
            and int(transaction[2]) == 0
            and valuation_passed
            and market_passed
        )
        results.append(
            {
                "county": county,
                "district": district,
                "transaction_count": transaction_count,
                "expected_transaction_count": int(expected["shadow_transaction_count"]),
                "history_length": history_length,
                "expected_history_length": int(expected["history_length"]),
                "latest_publishable_period": market[1],
                "valuation_read_passed": valuation_passed,
                "market_insight_read_passed": market_passed,
                "lineage_passed": int(transaction[2]) == 0,
                "passed": passed,
            }
        )
    return results


def _gate_result(gate_id: str, passed: bool, evidence: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "gate_id": gate_id,
        "description": gate_id.replace("_", " "),
        "result": "PASS" if passed else "FAIL",
        "evidence": dict(evidence),
        "blocking_status": "clear" if passed else "BLOCKING",
    }


def _manifest_mutation_is_rejected(connection: Any, generation_id: str) -> bool:
    before = connection.execute(
        "select expected_transaction_count from plvr_dataset_generations "
        "where dataset_key = %s and generation_id = %s",
        (DATASET_KEY, generation_id),
    ).fetchone()[0]
    try:
        connection.execute(
            "update plvr_dataset_generations set expected_transaction_count = expected_transaction_count + 1 "
            "where dataset_key = %s and generation_id = %s",
            (DATASET_KEY, generation_id),
        )
    except Exception:
        after = connection.execute(
            "select expected_transaction_count from plvr_dataset_generations "
            "where dataset_key = %s and generation_id = %s",
            (DATASET_KEY, generation_id),
        ).fetchone()[0]
        return int(after) == int(before)
    return False


def _generation_state(connection: Any, generation_id: str) -> str:
    row = connection.execute(
        "select state from plvr_dataset_generations where dataset_key = %s and generation_id = %s",
        (DATASET_KEY, generation_id),
    ).fetchone()
    if row is None:
        raise RehearsalError("generation_not_found")
    return str(row[0])


def _generation_states(connection: Any, generation_ids: Sequence[str]) -> dict[str, str]:
    return {generation_id: _generation_state(connection, generation_id) for generation_id in generation_ids}


def _active_generation_id(connection: Any) -> str:
    row = connection.execute(
        "select active_generation_id from plvr_active_dataset where dataset_key = %s",
        (DATASET_KEY,),
    ).fetchone()
    return str(row[0]) if row else ""


def _active_pointer_count(connection: Any) -> int:
    return int(
        connection.execute(
            "select count(*) from plvr_active_dataset where dataset_key = %s",
            (DATASET_KEY,),
        ).fetchone()[0]
    )


def _transaction_count(connection: Any, generation_id: str, *, include_unpublishable: bool) -> int:
    suffix = "" if include_unpublishable else " and publishable"
    return int(
        connection.execute(
            "select count(*) from plvr_generation_transactions "
            "where dataset_key = %s and generation_id = %s" + suffix,
            (DATASET_KEY, generation_id),
        ).fetchone()[0]
    )


def _region_transaction_count(connection: Any, generation_id: str, county: str, district: str) -> int:
    """Return the region count visible through the publishable reader contract."""

    return int(
        connection.execute(
            "select count(*) from plvr_generation_transactions "
            "where generation_id = %s and city = %s and district = %s and publishable",
            (generation_id, county, district),
        ).fetchone()[0]
    )


def _aggregate_count(connection: Any, generation_id: str) -> int:
    return int(
        connection.execute(
            "select count(*) from plvr_generation_market_aggregates where generation_id = %s",
            (generation_id,),
        ).fetchone()[0]
    )


def _aggregate_fingerprint(connection: Any, generation_id: str) -> str:
    digest = hashlib.sha256()
    rows = connection.execute(
        """
        select county, district, geographic_unit_kind, period,
               average_unit_price, transaction_count, coverage_status
        from plvr_generation_market_aggregates
        where generation_id = %s
        order by county, district, period
        """,
        (generation_id,),
    ).fetchall()
    for row in rows:
        digest.update(_canonical_json(list(row)).encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


def _record_event(
    connection: Any,
    generation_id: str | None,
    event_type: str,
    safe_detail: Mapping[str, Any],
) -> None:
    connection.execute(
        """
        insert into plvr_rehearsal_events (
            dataset_key, generation_id, event_type, safe_detail
        ) values (%s, %s, %s, %s::jsonb)
        """,
        (DATASET_KEY, generation_id, event_type, _canonical_json(dict(safe_detail))),
    )


@contextmanager
def _sqlite_read_only(path: Path) -> Iterator[sqlite3.Connection]:
    connection = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    try:
        yield connection
    finally:
        connection.close()


def _sqlite_scalar(
    connection: sqlite3.Connection,
    sql: str,
    parameters: Sequence[Any] = (),
) -> int:
    return int(connection.execute(sql, parameters).fetchone()[0])


def _snapshot_checksum(connection: sqlite3.Connection) -> str:
    digest = hashlib.sha256()
    rows = connection.execute(
        """
        select stable_id, transaction_period, city, district, road,
               address_text, building_type, area_ping, building_age_years,
               floor, total_floor, unit_price_per_ping, total_price, source,
               dedupe_key, imported_at, address_fingerprint,
               production_fact_hash, canonical_business_fact_hash, row_fingerprint
        from snapshot_transactions order by stable_id
        """
    )
    for row in rows:
        digest.update(_canonical_json(list(row)).encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RehearsalError("rehearsal_artifact_invalid")
    return value


def _decode_snapshot_metadata(value: str) -> Any:
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".partial")
    try:
        temporary.write_text(
            json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
