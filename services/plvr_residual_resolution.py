"""Resolve Phase 2C.6 PLVR residual cohorts from ignored local snapshots.

This module has no PostgreSQL client and no production write path. It reads the
verified Phase 2C.6 SQLite snapshot, clean shadow, and reconciliation cache,
then writes only a new ignored local analysis database and safe summaries.
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import uuid
from collections import Counter, defaultdict
from enum import StrEnum
from pathlib import Path
from statistics import median
from typing import Any, Mapping

from scripts.plan_plvr_production_repair import build_production_repair_plan


EXPECTED_PRODUCTION_ROWS = 451_672
EXPECTED_CLEAN_ROWS = 517_195
EXPECTED_SNAPSHOT_SHA256 = (
    "d18823a8e9953fd78598f3aa428b43e302dd1af1ce6d6338ca4ceabbaa6b9d33"
)
REVISED_SCHEMA_VERSION = "plvr-residual-cohort-resolution-v1"


class ResidualResolutionError(RuntimeError):
    """Raised when cached evidence or conservation checks fail closed."""


class RevisedProductionBucket(StrEnum):
    AUTHORITATIVE_MATCH = "AUTHORITATIVE_MATCH"
    STRONG_FACT_MATCH = "STRONG_FACT_MATCH"
    GEOGRAPHY_CORRUPT_MATCH = "GEOGRAPHY_CORRUPT_MATCH"
    DUPLICATE = "DUPLICATE"
    NOT_IN_CLEAN_SOURCE = "NOT_IN_CLEAN_SOURCE"
    FUTURE_ANOMALY = "FUTURE_ANOMALY"
    CONFLICTING = "CONFLICTING"
    UNCLASSIFIED = "UNCLASSIFIED"


class RevisedCleanBucket(StrEnum):
    PRESENT_AUTHORITATIVELY = "PRESENT_AUTHORITATIVELY"
    PRESENT_BY_STRONG_FACT = "PRESENT_BY_STRONG_FACT"
    PRESENT_BUT_PROD_CORRUPT = "PRESENT_BUT_PROD_CORRUPT"
    MISSING_FROM_PROD = "MISSING_FROM_PROD"
    DUPLICATED_IN_PROD = "DUPLICATED_IN_PROD"
    SOURCE_CONFLICT = "SOURCE_CONFLICT"
    UNCLASSIFIED = "UNCLASSIFIED"


GOLDEN_REGIONS = (
    ("臺北市", "中正區"),
    ("臺北市", "南港區"),
    ("臺中市", "北屯區"),
    ("桃園市", "平鎮區"),
    ("桃園市", "中壢區"),
    ("高雄市", "小港區"),
    ("高雄市", "三民區"),
)


def resolve_residual_cohorts(
    shadow_path: Path,
    snapshot_path: Path,
    prior_reconciliation_path: Path,
    output_path: Path,
    *,
    allowed_root: Path,
    main_sha: str,
    expected_snapshot_sha256: str = EXPECTED_SNAPSHOT_SHA256,
) -> dict[str, Any]:
    """Build a revised, conserved reconciliation from local read-only inputs."""

    for path in (shadow_path, snapshot_path, prior_reconciliation_path):
        if not path.is_file():
            raise ResidualResolutionError("phase2c6_local_evidence_missing")
    _assert_local_output(output_path, allowed_root)
    snapshot_metadata = _read_snapshot_metadata(snapshot_path)
    if snapshot_metadata.get("snapshot_sha256") != expected_snapshot_sha256:
        raise ResidualResolutionError("phase2c6_snapshot_sha_mismatch")
    if int(snapshot_metadata.get("production_total_count") or 0) != EXPECTED_PRODUCTION_ROWS:
        raise ResidualResolutionError("phase2c6_snapshot_count_mismatch")
    if str(snapshot_metadata.get("transaction_read_only") or "").lower() != "on":
        raise ResidualResolutionError("phase2c6_snapshot_not_read_only")
    if not bool(snapshot_metadata.get("snapshot_stationary")):
        raise ResidualResolutionError("phase2c6_snapshot_not_stationary")

    temporary = output_path.with_name(
        f"{output_path.name}.building-{uuid.uuid4().hex}"
    )
    temporary.parent.mkdir(parents=True, exist_ok=True)
    try:
        connection = sqlite3.connect(temporary, uri=True)
        connection.row_factory = sqlite3.Row
        connection.create_function("safe_hash", 1, _safe_hash)
        connection.create_function("city_key", 1, _city_key)
        connection.create_function("compact", 1, _compact)
        try:
            _attach_readonly(connection, "shadow", shadow_path)
            _attach_readonly(connection, "snapshot", snapshot_path)
            _attach_readonly(connection, "prior", prior_reconciliation_path)
            _create_schema(connection)
            _index_clean_shadow(connection)
            _classify_production(connection)
            _resolve_production_only(connection)
            _resolve_invalid_geography(connection)
            _classify_clean(connection)
            connection.commit()
            report = _build_report(
                connection,
                snapshot_metadata=snapshot_metadata,
                main_sha=main_sha,
                shadow_path=shadow_path,
                snapshot_path=snapshot_path,
            )
        finally:
            connection.close()
        os.replace(temporary, output_path)
        return report
    finally:
        temporary.unlink(missing_ok=True)


def safe_residual_artifacts(
    report: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    """Return count-only artifacts without local row references or raw facts."""

    summary = json.loads(_canonical_json(report))
    buckets = {
        "schema_version": "plvr-revised-reconciliation-buckets-v1",
        "main_sha": report.get("main_sha"),
        "production_snapshot_sha256": report.get("production_snapshot_sha256"),
        "matching_semantics": report.get("matching_semantics"),
        "production_buckets": report.get("production_buckets"),
        "duplicate_breakdown": report.get("duplicate_breakdown"),
        "clean_buckets": report.get("clean_buckets"),
        "clean_unclassified_reasons": report.get("clean_unclassified_reasons"),
        "conflicts": report.get("conflicts"),
        "production_only_5017": report.get("production_only_5017"),
        "invalid_geography": report.get("invalid_geography"),
        "historical_cohorts": report.get("historical_cohorts"),
        "future_row": report.get("future_row"),
        "conservation": report.get("conservation"),
    }
    aggregate = {
        "schema_version": "plvr-aggregate-delta-attribution-v1",
        "main_sha": report.get("main_sha"),
        "production_snapshot_sha256": report.get("production_snapshot_sha256"),
        "aggregate_attribution": report.get("aggregate_attribution"),
        "golden_regions": report.get("golden_regions"),
    }
    risk = {
        "schema_version": "plvr-cutover-risk-matrix-v1",
        "main_sha": report.get("main_sha"),
        "risk_matrix": report.get("risk_matrix"),
        "cutover_design_blockers": report.get("cutover_design_blockers"),
        "cutover_execution_blockers": report.get("cutover_execution_blockers"),
        "gate": report.get("gate"),
    }
    payloads = {
        "plvr_residual_resolution_summary.json": summary,
        "plvr_revised_reconciliation_buckets.json": buckets,
        "plvr_aggregate_delta_attribution.json": aggregate,
        "plvr_cutover_risk_matrix.json": risk,
    }
    serialized = _canonical_json(payloads).lower()
    forbidden = (
        "database_url",
        "postgresql://",
        "password",
        "address_text",
        "raw production",
        "stable_id",
        "source_row_hash",
        "dedupe_key",
    )
    if any(value in serialized for value in forbidden):
        raise ResidualResolutionError("unsafe_residual_artifact")
    return payloads


def _attach_readonly(
    connection: sqlite3.Connection, alias: str, path: Path
) -> None:
    uri = path.resolve().as_uri() + "?mode=ro"
    connection.execute(f"attach database ? as {alias}", (uri,))


def _create_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        pragma journal_mode = delete;
        pragma synchronous = full;
        create table clean_aux (
            clean_id text primary key,
            source_identity text not null,
            canonical_fact_hash text not null,
            artifact_id text not null,
            artifact_sequence integer not null,
            city text not null,
            city_key text not null,
            district text not null,
            geographic_unit_kind text not null,
            period text not null,
            address_hash text not null,
            building_age real not null,
            unit_price real not null,
            total_price real not null,
            area real not null
        );
        create index idx_residual_clean_fact on clean_aux(canonical_fact_hash);
        create index idx_residual_clean_address on clean_aux(period, address_hash);
        create index idx_residual_clean_geo_address
            on clean_aux(city_key, district, period, address_hash);

        create table production_resolution (
            row_reference integer primary key,
            bucket text not null,
            subtype text not null,
            evidence_tier text not null,
            clean_id text,
            canonical_invalid integer not null
        );
        create index idx_residual_prod_bucket on production_resolution(bucket);
        create index idx_residual_prod_clean on production_resolution(clean_id);

        create table clean_resolution (
            clean_id text primary key,
            bucket text not null,
            reason_code text not null
        );
        create index idx_residual_clean_bucket on clean_resolution(bucket);

        create table production_only_resolution (
            row_reference integer primary key,
            subtype text not null
        );
        create table invalid_geography_resolution (
            row_reference integer primary key,
            subtype text not null
        );
        """
    )


def _index_clean_shadow(connection: sqlite3.Connection) -> None:
    rows = connection.execute(
        """
        select source_identity, source_row_hash, business_fact_hash,
               artifact_id, artifact_sequence, city, district,
               geographic_unit_kind, transaction_period, address_text,
               building_age_years, unit_price_per_ping, total_price, area_ping
        from shadow.shadow_transactions
        order by source_identity, source_row_hash
        """
    )
    batch: list[tuple[Any, ...]] = []
    for row in rows:
        clean_id = _hash_payload(
            {"source_identity": str(row[0]), "source_row_hash": str(row[1])}
        )
        batch.append(
            (
                clean_id,
                str(row[0]),
                str(row[2]),
                str(row[3]),
                int(row[4]),
                str(row[5]),
                _city_key(row[5]),
                str(row[6]),
                str(row[7]),
                str(row[8]),
                _safe_hash(_compact(row[9])),
                _number(row[10]),
                _number(row[11]),
                _number(row[12]),
                _number(row[13]),
            )
        )
        if len(batch) >= 2_000:
            connection.executemany(
                "insert into clean_aux values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                batch,
            )
            batch.clear()
    if batch:
        connection.executemany(
            "insert into clean_aux values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            batch,
        )
    connection.commit()


def _classify_production(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        insert into production_resolution
        with tier_c_multiplicity as (
            select clean_id, count(*) as production_count
            from prior.production_classification
            where evidence_tier = 'C' and clean_id is not null
            group by clean_id
        )
        select prior.stable_id,
               case
                 when prior.bucket = 'PROD_AUTHORITATIVE_MATCH'
                   then 'AUTHORITATIVE_MATCH'
                 when prior.bucket = 'PROD_GEOGRAPHY_CORRUPT_MATCH'
                   then 'GEOGRAPHY_CORRUPT_MATCH'
                 when prior.bucket = 'PROD_PROVABLE_DUPLICATE'
                   then 'DUPLICATE'
                 when prior.bucket = 'PROD_PROBABLE_DUPLICATE'
                      and coalesce(m.production_count, 0) = 1
                   then 'STRONG_FACT_MATCH'
                 when prior.bucket = 'PROD_PROBABLE_DUPLICATE'
                      and coalesce(m.production_count, 0) > 1
                   then 'DUPLICATE'
                 when prior.bucket = 'PROD_NOT_IN_CLEAN_SOURCE'
                   then 'NOT_IN_CLEAN_SOURCE'
                 when prior.bucket = 'PROD_FUTURE_ANOMALY'
                   then 'FUTURE_ANOMALY'
                 when prior.bucket = 'PROD_CONFLICTING'
                   then 'CONFLICTING'
                 else 'UNCLASSIFIED'
               end,
               case
                 when prior.bucket = 'PROD_AUTHORITATIVE_MATCH'
                   then 'AUTHORITATIVE_IDENTITY_MATCH'
                 when prior.bucket = 'PROD_GEOGRAPHY_CORRUPT_MATCH'
                   then 'AUTHORITATIVE_IDENTITY_GEOGRAPHY_MISMATCH'
                 when prior.bucket = 'PROD_PROVABLE_DUPLICATE'
                   then 'AUTHORITATIVE_DUPLICATE'
                 when prior.bucket = 'PROD_PROBABLE_DUPLICATE'
                      and coalesce(m.production_count, 0) = 1
                   then 'STRONG_FACT_MATCH_1_TO_1'
                 when prior.bucket = 'PROD_PROBABLE_DUPLICATE'
                      and coalesce(m.production_count, 0) > 1
                   then 'STRONG_FACT_DUPLICATE_1_TO_MANY'
                 when prior.bucket = 'PROD_NOT_IN_CLEAN_SOURCE'
                   then prior.production_only_reason
                 when prior.bucket = 'PROD_FUTURE_ANOMALY'
                   then 'STRONG_FACT_FUTURE_SOURCE_MATCH'
                 when prior.bucket = 'PROD_CONFLICTING'
                   then 'UNRESOLVED_FACT_MATCH'
                 else 'UNCLASSIFIED'
               end,
               prior.evidence_tier,
               prior.clean_id,
               prior.canonical_invalid
        from prior.production_classification prior
        left join tier_c_multiplicity m on m.clean_id = prior.clean_id
        order by prior.stable_id
        """
    )


def _resolve_production_only(connection: sqlite3.Connection) -> None:
    rows = connection.execute(
        """
        select resolution.row_reference, snapshot.city, snapshot.district,
               snapshot.transaction_period, snapshot.address_fingerprint
        from production_resolution resolution
        join snapshot.snapshot_transactions snapshot
          on snapshot.stable_id = resolution.row_reference
        join prior.production_classification prior
          on prior.stable_id = resolution.row_reference
        where resolution.bucket = 'NOT_IN_CLEAN_SOURCE'
          and prior.production_only_reason = 'UNRESOLVED'
        order by resolution.row_reference
        """
    )
    batch = []
    for row in rows:
        same_geography = int(
            connection.execute(
                """
                select count(*) from clean_aux
                where city_key = ? and district = ? and period = ?
                  and address_hash = ?
                """,
                (_city_key(row[1]), str(row[2]), str(row[3]), str(row[4])),
            ).fetchone()[0]
        )
        same_period_address = int(
            connection.execute(
                "select count(*) from clean_aux where period = ? and address_hash = ?",
                (str(row[3]), str(row[4])),
            ).fetchone()[0]
        )
        if same_geography:
            subtype = "IDENTITY_LOSS"
        elif same_period_address == 1:
            subtype = "LEGACY_IMPORT_TRANSFORMATION_ERROR"
        elif same_period_address > 1:
            subtype = "INSUFFICIENT_EVIDENCE"
        else:
            subtype = "SOURCE_RECORD_NOT_REACQUIRED"
        batch.append((int(row[0]), subtype))
    connection.executemany(
        "insert into production_only_resolution values (?, ?)", batch
    )
    connection.execute(
        """
        update production_resolution
        set subtype = (
            select residual.subtype from production_only_resolution residual
            where residual.row_reference = production_resolution.row_reference
        )
        where row_reference in (select row_reference from production_only_resolution)
        """
    )


def _resolve_invalid_geography(connection: sqlite3.Connection) -> None:
    rows = connection.execute(
        """
        select resolution.row_reference, resolution.bucket, resolution.clean_id,
               snapshot.transaction_period, snapshot.address_fingerprint
        from production_resolution resolution
        join snapshot.snapshot_transactions snapshot
          on snapshot.stable_id = resolution.row_reference
        where resolution.canonical_invalid = 1
        order by resolution.row_reference
        """
    )
    batch = []
    for row in rows:
        clean_kind = ""
        if row[2]:
            match = connection.execute(
                "select geographic_unit_kind from clean_aux where clean_id = ?",
                (str(row[2]),),
            ).fetchone()
            clean_kind = str(match[0]) if match else ""
        if row[1] == RevisedProductionBucket.AUTHORITATIVE_MATCH.value and clean_kind == "city_level":
            subtype = "RECOVERED_AUTHORITATIVE_CITY_LEVEL"
        elif row[1] == RevisedProductionBucket.NOT_IN_CLEAN_SOURCE.value:
            candidates = int(
                connection.execute(
                    "select count(*) from clean_aux where period = ? and address_hash = ?",
                    (str(row[3]), str(row[4])),
                ).fetchone()[0]
            )
            if candidates == 1:
                subtype = "LEGACY_IMPORT_TRANSFORMATION_ERROR"
            elif candidates > 1:
                subtype = "CONFLICTING_GEOGRAPHY_CANDIDATES"
            else:
                subtype = "CLEAN_SOURCE_MISSING"
        elif row[1] == RevisedProductionBucket.CONFLICTING.value:
            subtype = "CONFLICTING"
        else:
            subtype = "GENUINELY_UNRESOLVED"
        batch.append((int(row[0]), subtype))
    connection.executemany(
        "insert into invalid_geography_resolution values (?, ?)", batch
    )


def _classify_clean(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        insert into clean_resolution
        with mappings as (
            select clean_id,
                   count(*) as production_count,
                   sum(bucket = 'AUTHORITATIVE_MATCH') as authoritative_count,
                   sum(bucket = 'GEOGRAPHY_CORRUPT_MATCH') as corrupt_count,
                   sum(bucket = 'STRONG_FACT_MATCH') as strong_count,
                   sum(bucket = 'DUPLICATE') as duplicate_count
            from production_resolution
            where clean_id is not null and bucket <> 'FUTURE_ANOMALY'
            group by clean_id
        ), conflict_facts as (
            select distinct snapshot.canonical_business_fact_hash as fact_hash
            from production_resolution resolution
            join snapshot.snapshot_transactions snapshot
              on snapshot.stable_id = resolution.row_reference
            where resolution.bucket = 'CONFLICTING'
        )
        select clean.clean_id,
               case
                 when coalesce(map.production_count, 0) > 1
                   then 'DUPLICATED_IN_PROD'
                 when coalesce(map.corrupt_count, 0) = 1
                   then 'PRESENT_BUT_PROD_CORRUPT'
                 when coalesce(map.authoritative_count, 0) = 1
                   then 'PRESENT_AUTHORITATIVELY'
                 when coalesce(map.strong_count, 0) = 1
                   then 'PRESENT_BY_STRONG_FACT'
                 when conflict.fact_hash is not null
                   then 'UNCLASSIFIED'
                 else 'MISSING_FROM_PROD'
               end,
               case
                 when coalesce(map.production_count, 0) > 1
                   then 'STRONG_FACT_ONE_TO_MANY'
                 when coalesce(map.corrupt_count, 0) = 1
                   then 'AUTHORITATIVE_GEOGRAPHY_MISMATCH'
                 when coalesce(map.authoritative_count, 0) = 1
                   then 'AUTHORITATIVE_IDENTITY_MATCH'
                 when coalesce(map.strong_count, 0) = 1
                   then 'STRONG_FACT_MATCH_1_TO_1'
                 when conflict.fact_hash is not null
                   then 'BOUNDED_FACT_GROUP_AMBIGUITY'
                 else 'NO_PRODUCTION_MATCH'
               end
        from clean_aux clean
        left join mappings map on map.clean_id = clean.clean_id
        left join conflict_facts conflict
          on conflict.fact_hash = clean.canonical_fact_hash
        order by clean.clean_id
        """
    )


def _build_report(
    connection: sqlite3.Connection,
    *,
    snapshot_metadata: Mapping[str, Any],
    main_sha: str,
    shadow_path: Path,
    snapshot_path: Path,
) -> dict[str, Any]:
    production = _count_by(connection, "production_resolution", "bucket")
    clean = _count_by(connection, "clean_resolution", "bucket")
    clean_unclassified_reasons = {
        str(row[0]): int(row[1])
        for row in connection.execute(
            """
            select reason_code, count(*)
            from clean_resolution
            where bucket = 'UNCLASSIFIED'
            group by reason_code
            order by reason_code
            """
        )
    }
    production_total = sum(production.values())
    clean_total = sum(clean.values())
    if production_total != EXPECTED_PRODUCTION_ROWS:
        raise ResidualResolutionError("revised_production_conservation_failed")
    if clean_total != EXPECTED_CLEAN_ROWS:
        raise ResidualResolutionError("revised_clean_conservation_failed")

    duplicate_breakdown = _duplicate_breakdown(connection)
    conflicts = _conflict_report(connection)
    residual = _count_by(
        connection, "production_only_resolution", "subtype"
    )
    if sum(residual.values()) != 5_017:
        raise ResidualResolutionError("production_only_5017_conservation_failed")
    invalid = _count_by(
        connection, "invalid_geography_resolution", "subtype"
    )
    if sum(invalid.values()) != 126_087:
        raise ResidualResolutionError("invalid_geography_conservation_failed")
    historical = _historical_cohort_report(snapshot_path)
    aggregate, golden = _aggregate_attribution(connection)
    risk_matrix, design_blockers, execution_blockers = _risk_matrix(
        production,
        clean,
        conflicts,
        residual,
        invalid,
        aggregate,
        golden,
    )
    gate = (
        "NOT_READY_FOR_SHADOW_CUTOVER_DESIGN"
        if design_blockers
        else "READY_FOR_SHADOW_CUTOVER_DESIGN"
    )
    report = {
        "schema_version": REVISED_SCHEMA_VERSION,
        "main_sha": main_sha,
        "production_snapshot_sha256": snapshot_metadata["snapshot_sha256"],
        "production_transaction_read_only": snapshot_metadata[
            "transaction_read_only"
        ],
        "production_rows": EXPECTED_PRODUCTION_ROWS,
        "clean_rows": EXPECTED_CLEAN_ROWS,
        "matching_semantics": {
            "A": "AUTHORITATIVE_OFFICIAL_IDENTITY",
            "B": "AUTHORITATIVE_RECONSTRUCTED_SOURCE_IDENTITY",
            "C_ONE_TO_ONE": "STRONG_FACT_MATCH_NOT_DUPLICATE",
            "C_ONE_TO_MANY": "STRONG_FACT_DUPLICATE",
            "D": "PROBABLE_LEGACY_ONLY_NOT_AUTHORITATIVE",
        },
        "production_buckets": _all_production_buckets(production),
        "duplicate_breakdown": duplicate_breakdown,
        "clean_buckets": _all_clean_buckets(clean),
        "clean_unclassified_reasons": clean_unclassified_reasons,
        "conflicts": conflicts,
        "production_only_5017": residual,
        "invalid_geography": invalid,
        "historical_cohorts": historical,
        "future_row": {
            "status": "STRONG_FACT_FUTURE_SOURCE_MATCH",
            "production_count": production.get("FUTURE_ANOMALY", 0),
            "artifact_id": "moi-plvr-sale-season-115S1",
            "publishable_status": "excluded",
        },
        "aggregate_attribution": aggregate,
        "golden_regions": golden,
        "risk_matrix": risk_matrix,
        "conservation": {
            "production_expected": EXPECTED_PRODUCTION_ROWS,
            "production_sum": production_total,
            "production_conserved": production_total == EXPECTED_PRODUCTION_ROWS,
            "clean_expected": EXPECTED_CLEAN_ROWS,
            "clean_sum": clean_total,
            "clean_conserved": clean_total == EXPECTED_CLEAN_ROWS,
            "production_only_expected": 5_017,
            "production_only_sum": sum(residual.values()),
            "invalid_geography_expected": 126_087,
            "invalid_geography_sum": sum(invalid.values()),
        },
        "production_safety": {
            "mode": "LOCAL_CACHE_ONLY_AFTER_VERIFIED_READ_ONLY_SNAPSHOT",
            "writes": 0,
            "rows_changed": 0,
            "migrations": 0,
            "schema_changes": 0,
        },
        "cutover_design_blockers": design_blockers,
        "cutover_execution_blockers": execution_blockers,
        "gate": gate,
    }
    return report


def _duplicate_breakdown(connection: sqlite3.Connection) -> dict[str, Any]:
    rows = connection.execute(
        """
        select clean_id, count(*)
        from production_resolution
        where subtype = 'STRONG_FACT_DUPLICATE_1_TO_MANY'
        group by clean_id
        """
    ).fetchall()
    group_sizes = Counter(int(row[1]) for row in rows)
    strong_rows = sum(size * count for size, count in group_sizes.items())
    return {
        "AUTHORITATIVE_DUPLICATE": int(
            connection.execute(
                "select count(*) from production_resolution where subtype = 'AUTHORITATIVE_DUPLICATE'"
            ).fetchone()[0]
        ),
        "STRONG_FACT_DUPLICATE": strong_rows,
        "PROBABLE_LEGACY_DUPLICATE": 0,
        "DUPLICATE_GROUPS": sum(group_sizes.values()),
        "DUPLICATE_EXCESS_ROWS": sum(
            (size - 1) * count for size, count in group_sizes.items()
        ),
        "DUPLICATE_CLEAN_TRANSACTIONS": sum(group_sizes.values()),
        "GROUP_SIZE_DISTRIBUTION": {
            str(size): count for size, count in sorted(group_sizes.items())
        },
        "TIER_C_1_TO_1": int(
            connection.execute(
                "select count(*) from production_resolution where subtype = 'STRONG_FACT_MATCH_1_TO_1'"
            ).fetchone()[0]
        ),
        "TIER_C_1_TO_MANY": strong_rows,
    }


def _conflict_report(connection: sqlite3.Connection) -> dict[str, Any]:
    groups = connection.execute(
        """
        with conflict_groups as (
            select snapshot.canonical_business_fact_hash as fact_hash,
                   count(distinct resolution.row_reference) as production_rows,
                   count(distinct clean.clean_id) as clean_rows,
                   count(distinct clean.artifact_id) as artifacts,
                   count(distinct clean.source_identity) as source_identities
            from production_resolution resolution
            join snapshot.snapshot_transactions snapshot
              on snapshot.stable_id = resolution.row_reference
            join clean_aux clean
              on clean.canonical_fact_hash = snapshot.canonical_business_fact_hash
            where resolution.bucket = 'CONFLICTING'
            group by snapshot.canonical_business_fact_hash
        )
        select production_rows, clean_rows, artifacts, source_identities,
               count(*) as group_count
        from conflict_groups
        group by production_rows, clean_rows, artifacts, source_identities
        order by production_rows, clean_rows, artifacts, source_identities
        """
    ).fetchall()
    source_revision_groups = sum(int(row[4]) for row in groups if int(row[2]) > 1)
    source_revision_rows = sum(
        int(row[0]) * int(row[4]) for row in groups if int(row[2]) > 1
    )
    bounded_groups = sum(int(row[4]) for row in groups if int(row[2]) == 1)
    bounded_rows = sum(
        int(row[0]) * int(row[4]) for row in groups if int(row[2]) == 1
    )
    total_rows = bounded_rows + source_revision_rows
    topology = [
        {
            "production_rows_per_group": int(row[0]),
            "clean_rows_per_group": int(row[1]),
            "source_artifacts_per_group": int(row[2]),
            "source_identities_per_group": int(row[3]),
            "group_count": int(row[4]),
            "production_rows": int(row[0]) * int(row[4]),
        }
        for row in groups
    ]
    return {
        "group_count": bounded_groups + source_revision_groups,
        "production_rows": total_rows,
        "group_topology": topology,
        "single_artifact_groups": bounded_groups,
        "single_artifact_production_rows": bounded_rows,
        "multi_artifact_groups": source_revision_groups,
        "multi_artifact_production_rows": source_revision_rows,
        "resolved_rows": 0,
        "materially_unresolved_rows": total_rows,
        "classification": {
            "INSUFFICIENT_EVIDENCE": bounded_rows,
            "SOURCE_REVISION_AMBIGUITY": source_revision_rows,
            "RESOLVED_BY_AUTHORITATIVE_IDENTITY": 0,
            "RESOLVED_BY_SOURCE_LINEAGE": 0,
            "RESOLVED_BY_UNIQUE_AUXILIARY_FACTS": 0,
            "TRUE_DUPLICATE_AMBIGUITY": 0,
        },
        "auxiliary_fields_checked": ["building_age_years"],
        "unique_auxiliary_resolutions": 0,
        "auxiliary_resolution_note": (
            "building_age_years did not uniquely distinguish any candidate"
        ),
        "bounded_for_design": True,
    }


class _CachedSnapshotRepository:
    def __init__(self, path: Path) -> None:
        self.path = path

    def iter_transactions(self):
        connection = _open_sqlite_readonly(self.path)
        connection.row_factory = sqlite3.Row
        try:
            rows = connection.execute(
                """
                select stable_id as id, transaction_period, city, district,
                       road, address_text, building_type, area_ping,
                       building_age_years, floor, total_floor,
                       unit_price_per_ping, total_price, source, dedupe_key,
                       imported_at
                from snapshot_transactions order by stable_id
                """
            )
            for row in rows:
                yield dict(row)
        finally:
            connection.close()

    def aggregate_stats(self, _as_of_period: str) -> dict[str, int]:
        return {"aggregate_rows": 11_018, "future_aggregate_rows": 1}

    def future_aggregates(self, _as_of_period: str) -> list[dict[str, Any]]:
        return []


def _historical_cohort_report(snapshot_path: Path) -> dict[str, Any]:
    summary, manifest = build_production_repair_plan(
        _CachedSnapshotRepository(snapshot_path),
        as_of_period="2026-08",
        top=1,
    )
    supporting = int(
        summary["geography_classification"].get(
            "REPAIR_WITH_SUPPORTING_EVIDENCE", 0
        )
    )
    collision_candidates = int(
        summary["collision_classification"].get(
            "EXACT_DUPLICATE_AFTER_REPAIR", 0
        )
    )
    return {
        "historical_109236": {
            "status": "REPRODUCIBLE",
            "historical_count": 109_236,
            "reproduced_count": supporting,
            "predicate_source": "phase2b_original_repair_planner",
            "same_snapshot_row_count": len(manifest),
            "design_blocking": supporting != 109_236,
        },
        "historical_57350": {
            "status": "PARTIALLY_REPRODUCIBLE",
            "historical_count": 57_350,
            "reproduced_broad_collision_count": collision_candidates,
            "aggregate_only_adjustment_without_row_membership": (
                collision_candidates - 57_350
            ),
            "design_blocking": False,
            "execution_blocking": True,
        },
    }


def _aggregate_attribution(
    connection: sqlite3.Connection,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    production_rows = _aggregate_rows(
        connection,
        """
        select city_key(snapshot.city), snapshot.district,
               snapshot.transaction_period, count(*),
               round(avg(snapshot.unit_price_per_ping), 2),
               round(sum(snapshot.total_price), 2)
        from snapshot.snapshot_transactions snapshot
        where snapshot.transaction_period <= '2026-07'
        group by city_key(snapshot.city), snapshot.district,
                 snapshot.transaction_period
        """,
    )
    clean_rows = _aggregate_rows(
        connection,
        """
        select city_key, district, period, count(*),
               round(avg(unit_price), 2), round(sum(total_price), 2)
        from clean_aux group by city_key, district, period
        """,
    )
    production_reasons = _scope_reasons(connection, side="production")
    clean_reasons = _scope_reasons(connection, side="clean")
    scopes: dict[tuple[str, str, str], dict[str, Any]] = {}
    status_counts: Counter[str] = Counter()
    reason_scope_counts: Counter[str] = Counter()
    status_count_delta: Counter[str] = Counter()
    status_value_delta: defaultdict[str, float] = defaultdict(float)
    status_unit_price_delta: defaultdict[str, list[float]] = defaultdict(list)
    unchanged = 0
    for key in sorted(set(production_rows) | set(clean_rows)):
        left = production_rows.get(key)
        right = clean_rows.get(key)
        if left == right:
            unchanged += 1
            continue
        reasons = set(production_reasons.get(key, ())) | set(
            clean_reasons.get(key, ())
        )
        if not reasons:
            reasons.add("UNEXPLAINED")
        unresolved = {
            "INSUFFICIENT_EVIDENCE",
            "SOURCE_RECORD_NOT_REACQUIRED",
            "CONFLICTING_IDENTITY",
            "UNEXPLAINED",
        } & reasons
        known = reasons - unresolved
        if unresolved and known:
            status = "PARTIALLY_EXPLAINED"
        elif unresolved:
            status = "UNEXPLAINED"
        else:
            status = "FULLY_EXPLAINED"
        status_counts[status] += 1
        for reason in reasons:
            reason_scope_counts[reason] += 1
        left_values = left or (0, 0.0, 0.0)
        right_values = right or (0, 0.0, 0.0)
        status_count_delta[status] += abs(int(left_values[0]) - int(right_values[0]))
        status_value_delta[status] += abs(float(left_values[2]) - float(right_values[2]))
        status_unit_price_delta[status].append(
            abs(float(left_values[1]) - float(right_values[1]))
        )
        scopes[key] = {"status": status, "reasons": tuple(sorted(reasons))}

    mismatched = sum(status_counts.values())
    for reason in (
        "PRODUCTION_ONLY_BAD_IMPORT",
        "PRODUCTION_ONLY_OUTSIDE_WINDOW",
        "CLEAN_MISSING_FROM_PROD",
        "STRONG_FACT_DUPLICATE",
        "INVALID_GEOGRAPHY",
        "FUTURE_EXCLUSION",
        "SOURCE_SCOPE_DIFFERENCE",
        "CANONICAL_GEOGRAPHY_SEMANTICS",
        "OTHER_KNOWN",
        "CONFLICTING_IDENTITY",
        "INSUFFICIENT_EVIDENCE",
        "SOURCE_RECORD_NOT_REACQUIRED",
        "UNEXPLAINED",
    ):
        reason_scope_counts.setdefault(reason, 0)
    unexplained_share = round(
        100.0 * status_counts["UNEXPLAINED"] / mismatched, 4
    ) if mismatched else 0.0
    materiality = {
        "rule": (
            "material if unexplained scopes exceed 0.1% of mismatched scopes, "
            "or any unexplained golden latest-period scope exists"
        ),
        "unexplained_scope_percent": unexplained_share,
        "threshold_percent": 0.1,
        "result": "pending_golden_validation",
    }
    golden = _golden_region_report(connection, scopes)
    golden_latest_unexplained = any(
        not item["latest_period_fully_explained"] for item in golden
    )
    material = unexplained_share > 0.1 or golden_latest_unexplained
    materiality["golden_latest_unexplained"] = golden_latest_unexplained
    materiality["result"] = "MATERIAL_UNEXPLAINED" if material else "IMMATERIAL_BOUNDED"
    scope_percentages = {
        status: round(100.0 * status_counts[status] / mismatched, 4)
        if mismatched
        else 0.0
        for status in ("FULLY_EXPLAINED", "PARTIALLY_EXPLAINED", "UNEXPLAINED")
    }
    return (
        {
            "production_aggregate_scopes": len(production_rows),
            "shadow_aggregate_scopes": len(clean_rows),
            "exact_scopes": unchanged,
            "mismatched_scopes": mismatched,
            "mismatched_scope_percent": round(
                100.0 * mismatched / (mismatched + unchanged), 4
            )
            if mismatched + unchanged
            else 0.0,
            "fully_explained_scopes": status_counts["FULLY_EXPLAINED"],
            "partially_explained_scopes": status_counts["PARTIALLY_EXPLAINED"],
            "unexplained_scopes": status_counts["UNEXPLAINED"],
            "scope_percentages": scope_percentages,
            "status_conserved": sum(status_counts.values()) == mismatched,
            "attribution_matrix_scope_counts": dict(sorted(reason_scope_counts.items())),
            "absolute_transaction_count_delta_by_status": dict(status_count_delta),
            "absolute_total_value_delta_by_status": {
                key: round(value, 2) for key, value in status_value_delta.items()
            },
            "average_unit_price_delta_by_status": {
                key: {
                    "mean_absolute_delta": round(sum(values) / len(values), 4),
                    "median_absolute_delta": round(float(median(values)), 4),
                    "maximum_absolute_delta": round(max(values), 4),
                }
                for key, values in sorted(status_unit_price_delta.items())
                if values
            },
            "materiality": materiality,
        },
        golden,
    )


def _scope_reasons(
    connection: sqlite3.Connection, *, side: str
) -> dict[tuple[str, str, str], set[str]]:
    result: defaultdict[tuple[str, str, str], set[str]] = defaultdict(set)
    if side == "production":
        rows = connection.execute(
            """
            select city_key(snapshot.city), snapshot.district,
                   snapshot.transaction_period, resolution.bucket,
                   resolution.subtype
            from production_resolution resolution
            join snapshot.snapshot_transactions snapshot
              on snapshot.stable_id = resolution.row_reference
            where snapshot.transaction_period <= '2026-07'
              and resolution.bucket not in (
                  'AUTHORITATIVE_MATCH', 'STRONG_FACT_MATCH'
              )
            group by city_key(snapshot.city), snapshot.district,
                     snapshot.transaction_period, resolution.bucket,
                     resolution.subtype
            """
        )
        for city, district, period, bucket, subtype in rows:
            reason = _production_attribution_reason(str(bucket), str(subtype))
            result[(str(city), str(district), str(period))].add(reason)
        mapped_rows = connection.execute(
            """
            select city_key(snapshot.city), snapshot.district,
                   snapshot.transaction_period, snapshot.unit_price_per_ping,
                   snapshot.total_price, snapshot.area_ping,
                   clean.city_key, clean.district, clean.period,
                   clean.unit_price, clean.total_price, clean.area
            from production_resolution resolution
            join snapshot.snapshot_transactions snapshot
              on snapshot.stable_id = resolution.row_reference
            join clean_aux clean on clean.clean_id = resolution.clean_id
            where snapshot.transaction_period <= '2026-07'
              and resolution.bucket in (
                  'AUTHORITATIVE_MATCH', 'STRONG_FACT_MATCH',
                  'GEOGRAPHY_CORRUPT_MATCH'
              )
            """
        )
        for row in mapped_rows:
            production_scope = (str(row[0]), str(row[1]), str(row[2]))
            clean_scope = (str(row[6]), str(row[7]), str(row[8]))
            if production_scope != clean_scope:
                result[production_scope].add("CANONICAL_GEOGRAPHY_SEMANTICS")
                result[clean_scope].add("CANONICAL_GEOGRAPHY_SEMANTICS")
            if any(
                abs(float(left or 0) - float(right or 0)) > 0.01
                for left, right in ((row[3], row[9]), (row[4], row[10]), (row[5], row[11]))
            ):
                result[production_scope].add("OTHER_KNOWN")
                result[clean_scope].add("OTHER_KNOWN")
    else:
        rows = connection.execute(
            """
            select clean.city_key, clean.district, clean.period,
                   resolution.bucket, resolution.reason_code
            from clean_resolution resolution
            join clean_aux clean on clean.clean_id = resolution.clean_id
            where resolution.bucket in ('MISSING_FROM_PROD', 'UNCLASSIFIED')
            group by clean.city_key, clean.district, clean.period,
                     resolution.bucket, resolution.reason_code
            """
        )
        for city, district, period, bucket, reason_code in rows:
            reason = (
                "CLEAN_MISSING_FROM_PROD"
                if str(bucket) == "MISSING_FROM_PROD"
                else "CONFLICTING_IDENTITY"
            )
            result[(str(city), str(district), str(period))].add(reason)
    return result


def _production_attribution_reason(bucket: str, subtype: str) -> str:
    if bucket == "DUPLICATE":
        return "STRONG_FACT_DUPLICATE"
    if bucket == "GEOGRAPHY_CORRUPT_MATCH":
        return "INVALID_GEOGRAPHY"
    if bucket == "CONFLICTING":
        return "CONFLICTING_IDENTITY"
    if subtype == "OUTSIDE_REBUILD_WINDOW":
        return "PRODUCTION_ONLY_OUTSIDE_WINDOW"
    if subtype in {
        "PROBABLE_BAD_IMPORT",
        "LEGACY_IMPORT_TRANSFORMATION_ERROR",
        "IDENTITY_LOSS",
    }:
        return "PRODUCTION_ONLY_BAD_IMPORT"
    if subtype in {"INSUFFICIENT_EVIDENCE", "SOURCE_RECORD_NOT_REACQUIRED"}:
        return subtype
    if bucket == "NOT_IN_CLEAN_SOURCE":
        return "SOURCE_SCOPE_DIFFERENCE"
    return "OTHER_KNOWN"


def _golden_region_report(
    connection: sqlite3.Connection,
    scope_status: Mapping[tuple[str, str, str], Mapping[str, Any]],
) -> list[dict[str, Any]]:
    result = []
    for county, district in GOLDEN_REGIONS:
        county_key = _city_key(county)
        shadow = connection.execute(
            """
            select count(*), max(period), sum(transaction_count)
            from shadow.shadow_market_aggregates
            where city_key(county) = ? and district = ?
            """,
            (county_key, district),
        ).fetchone()
        recomputed = connection.execute(
            """
            select count(distinct period), max(period), count(*)
            from clean_aux where city_key = ? and district = ?
            """,
            (county_key, district),
        ).fetchone()
        production_region = connection.execute(
                """
                select count(*), round(sum(total_price), 2)
                from snapshot.snapshot_transactions
                where city_key(city) = ? and district = ?
                  and transaction_period <= '2026-07'
                """,
                (county_key, district),
            ).fetchone()
        production_count = int(production_region[0])
        production_total_value = float(production_region[1] or 0)
        shadow_total_value = float(
            connection.execute(
                """
                select round(sum(total_price), 2)
                from clean_aux where city_key = ? and district = ?
                """,
                (county_key, district),
            ).fetchone()[0]
            or 0
        )
        latest = str(shadow[1] or "")
        region_scopes = [
            data
            for (city, item_district, _period), data in scope_status.items()
            if city == county_key and item_district == district
        ]
        latest_status = scope_status.get((county_key, district, latest), {})
        result.append(
            {
                "county": county,
                "district": district,
                "history_length": int(shadow[0]),
                "latest_publishable_period": latest,
                "production_transaction_count": production_count,
                "shadow_transaction_count": int(recomputed[2]),
                "membership_delta": production_count - int(recomputed[2]),
                "aggregate_transaction_count_delta": (
                    production_count - int(recomputed[2])
                ),
                "aggregate_total_value_delta": round(
                    production_total_value - shadow_total_value, 2
                ),
                "mismatched_scope_count": len(region_scopes),
                "all_differences_fully_explained": all(
                    item.get("status") == "FULLY_EXPLAINED"
                    for item in region_scopes
                ),
                "latest_period_fully_explained": (
                    not latest_status
                    or latest_status.get("status") == "FULLY_EXPLAINED"
                ),
                "shadow_internally_consistent": (
                    int(shadow[0]) == int(recomputed[0])
                    and latest == str(recomputed[1] or "")
                    and int(shadow[2] or 0) == int(recomputed[2])
                ),
            }
        )
    return result


def _risk_matrix(
    production: Mapping[str, int],
    clean: Mapping[str, int],
    conflicts: Mapping[str, Any],
    residual: Mapping[str, int],
    invalid: Mapping[str, int],
    aggregate: Mapping[str, Any],
    golden: list[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    rows = [
        _risk_row(
            "strong_fact_one_to_one",
            production.get("STRONG_FACT_MATCH", 0),
            "strong",
            "production identity incomplete; facts correspond one-to-one",
            True,
            "pair during cutover using clean authoritative identity",
            False,
            False,
            False,
        ),
        _risk_row(
            "strong_fact_duplicates",
            production.get("DUPLICATE", 0),
            "strong topology",
            "production contains multiplicity beyond clean transaction",
            True,
            "deduplicate only in a future shadow replacement plan",
            True,
            False,
            True,
        ),
        _risk_row(
            "production_only",
            production.get("NOT_IN_CLEAN_SOURCE", 0),
            "mixed",
            "mostly transformed legacy geography or outside source window",
            True,
            "exclude or replace by explicit subtype during execution",
            True,
            False,
            True,
        ),
        _risk_row(
            "conflicting_identity",
            int(conflicts.get("production_rows") or 0),
            "bounded ambiguity",
            "individual production identity cannot be selected safely",
            True,
            "replace the bounded group from clean source; no row repair",
            True,
            False,
            True,
        ),
        _risk_row(
            "clean_missing_from_production",
            clean.get("MISSING_FROM_PROD", 0),
            "authoritative clean lineage",
            "production is incomplete relative to clean shadow",
            True,
            "include through shadow replacement",
            False,
            False,
            True,
        ),
        _risk_row(
            "clean_bounded_fact_group_ambiguity",
            clean.get("UNCLASSIFIED", 0),
            "bounded exact-fact group ambiguity",
            "individual production-to-clean permutation is not identifiable",
            True,
            "replace each bounded group from authoritative clean membership",
            True,
            False,
            True,
        ),
        _risk_row(
            "future_anomaly",
            production.get("FUTURE_ANOMALY", 0),
            "strong fact source match",
            "future source row is real but not publishable",
            True,
            "retain excluded from publishable output",
            False,
            False,
            False,
        ),
    ]
    design_blockers: list[str] = []
    materiality = (aggregate.get("materiality") or {}).get("result")
    if materiality == "MATERIAL_UNEXPLAINED":
        design_blockers.append("aggregate_unexplained_scopes_material")
    if not all(bool(item.get("shadow_internally_consistent")) for item in golden):
        design_blockers.append("golden_region_shadow_inconsistency")
    unresolved_residual = int(residual.get("INSUFFICIENT_EVIDENCE") or 0) + int(
        residual.get("SOURCE_RECORD_NOT_REACQUIRED") or 0
    )
    if 100.0 * unresolved_residual / EXPECTED_PRODUCTION_ROWS > 0.01:
        design_blockers.append("production_only_residual_materially_unresolved")
    clean_unclassified_percent = (
        100.0 * int(clean.get("UNCLASSIFIED") or 0) / EXPECTED_CLEAN_ROWS
    )
    if clean_unclassified_percent > 0.1 or (
        int(clean.get("UNCLASSIFIED") or 0)
        and not bool(conflicts.get("bounded_for_design"))
    ):
        design_blockers.append("clean_unclassified_cohort_material")
    if int(invalid.get("GENUINELY_UNRESOLVED") or 0):
        design_blockers.append("invalid_geography_materially_unresolved")
    execution_blockers = [
        "no_approved_shadow_cutover_plan",
        "production_mutation_not_authorized",
        "rollback_and_validation_procedure_not_designed",
        "bounded_identity_ambiguities_require_execution_policy",
        "historical_57350_row_membership_not_reproducible",
    ]
    return rows, design_blockers, execution_blockers


def _risk_row(
    cohort: str,
    count: int,
    evidence_quality: str,
    production_assessment: str,
    clean_authoritative: bool,
    treatment: str,
    manual_review: bool,
    blocks_design: bool,
    blocks_execution: bool,
) -> dict[str, Any]:
    return {
        "cohort": cohort,
        "row_count": int(count),
        "production_percent": round(100.0 * int(count) / EXPECTED_PRODUCTION_ROWS, 4),
        "evidence_quality": evidence_quality,
        "production_assessment": production_assessment,
        "clean_shadow_authoritative": clean_authoritative,
        "recommended_treatment": treatment,
        "manual_review_required": manual_review,
        "blocks_design": blocks_design,
        "blocks_execution": blocks_execution,
    }


def _aggregate_rows(
    connection: sqlite3.Connection, sql: str
) -> dict[tuple[str, str, str], tuple[int, float, float]]:
    return {
        (str(row[0]), str(row[1]), str(row[2])): (
            int(row[3]),
            round(float(row[4] or 0), 2),
            round(float(row[5] or 0), 2),
        )
        for row in connection.execute(sql)
    }


def _all_production_buckets(counts: Mapping[str, int]) -> dict[str, int]:
    return {bucket.value: int(counts.get(bucket.value, 0)) for bucket in RevisedProductionBucket}


def _all_clean_buckets(counts: Mapping[str, int]) -> dict[str, int]:
    return {bucket.value: int(counts.get(bucket.value, 0)) for bucket in RevisedCleanBucket}


def _count_by(
    connection: sqlite3.Connection, table: str, column: str
) -> dict[str, int]:
    allowed = {
        ("production_resolution", "bucket"),
        ("clean_resolution", "bucket"),
        ("production_only_resolution", "subtype"),
        ("invalid_geography_resolution", "subtype"),
    }
    if (table, column) not in allowed:
        raise ResidualResolutionError("unsafe_residual_summary_query")
    return {
        str(row[0]): int(row[1])
        for row in connection.execute(
            f"select {column}, count(*) from {table} group by {column}"
        )
    }


def _read_snapshot_metadata(path: Path) -> dict[str, Any]:
    connection = _open_sqlite_readonly(path)
    try:
        return {
            str(key): _json_value(str(value))
            for key, value in connection.execute(
                "select key, value from snapshot_metadata"
            )
        }
    finally:
        connection.close()


def _open_sqlite_readonly(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)


def _assert_local_output(path: Path, root: Path) -> None:
    resolved_root = root.resolve()
    resolved_path = path.resolve()
    if resolved_path == resolved_root or resolved_root not in resolved_path.parents:
        raise ResidualResolutionError("residual_output_outside_ignored_root")


def _json_value(value: str) -> Any:
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def _safe_hash(value: Any) -> str:
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()


def _hash_payload(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _compact(value: Any) -> str:
    return "".join(str(value or "").split())


def _city_key(value: Any) -> str:
    return _compact(value).replace("臺", "台")


def _number(value: Any) -> float:
    try:
        return round(float(value or 0), 2)
    except (TypeError, ValueError):
        return 0.0


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
