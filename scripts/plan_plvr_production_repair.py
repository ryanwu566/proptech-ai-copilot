"""Create a strictly read-only PLVR production repair dry-run plan."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.plvr_data_integrity import current_transaction_period, normalized_storage_key
from services.plvr_import_service import OFFICIAL_SOURCE, build_dedupe_key
from services.plvr_production_repair_planner import (
    CollisionClassification,
    CollisionEvidence,
    FutureClassification,
    FutureEvidence,
    GeographyEvidence,
    ReconciliationInput,
    RepairClassification,
    build_manifest_entry,
    classify_collision,
    classify_future_evidence,
    classify_geography_evidence,
    future_aggregate_lineage_matches,
    manifest_checksum,
    simulate_reconciliation,
    summary_checksum,
)
from services.taiwan_admin_registry import TaiwanRegion, iter_taiwan_regions, normalize_market_region


TRANSACTION_SCAN_SQL = """
select id, transaction_period, city, district, road, address_text, building_type,
       area_ping, building_age_years, floor, total_floor, unit_price_per_ping,
       total_price, source, raw_note, dedupe_key, imported_at
from real_price_transactions
where source = %s
order by id
"""

AGGREGATE_STATS_SQL = """
select count(*) as aggregate_rows,
       count(*) filter (where period > %s) as future_aggregate_rows
from market_district_period_aggregates
"""

FUTURE_AGGREGATE_SQL = """
select county, district, period, transaction_count, record_count
from market_district_period_aggregates
where period > %s
order by county, district, period
"""

EXECUTABLE_QUERIES = (TRANSACTION_SCAN_SQL, AGGREGATE_STATS_SQL, FUTURE_AGGREGATE_SQL)


class ReadOnlyPostgresRepository:
    """Minimal repository that opens PostgreSQL in default read-only mode."""

    def __init__(self, database_url: str, *, batch_size: int = 2_000) -> None:
        self.database_url = database_url
        self.batch_size = batch_size

    def iter_transactions(self) -> Iterator[Mapping[str, Any]]:
        connection = self._connect()
        cursor = None
        try:
            connection.read_only = True
            cursor = connection.cursor(name="plvr_repair_plan_scan")
            cursor.execute(TRANSACTION_SCAN_SQL, [OFFICIAL_SOURCE])
            while rows := cursor.fetchmany(self.batch_size):
                yield from rows
        finally:
            if cursor is not None:
                cursor.close()
            connection.close()

    def aggregate_stats(self, as_of_period: str) -> dict[str, int]:
        with self._read_cursor() as cursor:
            cursor.execute(AGGREGATE_STATS_SQL, [as_of_period])
            row = cursor.fetchone() or {}
            return {
                "aggregate_rows": int(_row_value(row, "aggregate_rows", 0) or 0),
                "future_aggregate_rows": int(_row_value(row, "future_aggregate_rows", 1) or 0),
            }

    def future_aggregates(self, as_of_period: str) -> list[Mapping[str, Any]]:
        with self._read_cursor() as cursor:
            cursor.execute(FUTURE_AGGREGATE_SQL, [as_of_period])
            return list(cursor.fetchall())

    def _read_cursor(self):
        return _ReadCursor(self._connect())

    def _connect(self):
        import psycopg
        from psycopg.rows import dict_row

        return psycopg.connect(
            self.database_url,
            connect_timeout=20,
            prepare_threshold=None,
            row_factory=dict_row,
            options="-c default_transaction_read_only=on -c statement_timeout=120000",
        )


class _ReadCursor:
    def __init__(self, connection: Any) -> None:
        self.connection = connection
        self.cursor: Any = None

    def __enter__(self):
        self.connection.read_only = True
        self.cursor = self.connection.cursor()
        return self.cursor

    def __exit__(self, _exc_type: Any, _exc: Any, _traceback: Any) -> None:
        if self.cursor is not None:
            self.cursor.close()
        self.connection.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Plan PLVR reconciliation using SELECT-only database access.")
    parser.add_argument("--database-url-env", default="VALUATION_DATABASE_URL")
    parser.add_argument("--as-of-date", type=date.fromisoformat)
    parser.add_argument("--summary-output", type=Path)
    parser.add_argument("--manifest-output", type=Path)
    parser.add_argument("--batch-size", type=int, default=2_000)
    parser.add_argument("--top", type=int, default=20)
    return parser


def build_production_repair_plan(
    repository: Any,
    *,
    as_of_period: str,
    regions: Iterable[TaiwanRegion] | None = None,
    top: int = 20,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Build an in-memory dry run without changing source or derived tables."""

    canonical_regions = list(regions or iter_taiwan_regions())
    district_owners = _district_owners(canonical_regions)
    canonical_districts = {
        normalized_storage_key(region.district): region.district for region in canonical_regions
    }
    counties = tuple(dict.fromkeys(region.county for region in canonical_regions))
    valid_natural: Counter[tuple[Any, ...]] = Counter()
    valid_exact: Counter[tuple[Any, ...]] = Counter()
    valid_dedupe_keys: set[str] = set()
    valid_scopes: set[tuple[str, str, str]] = set()
    invalid_rows: list[dict[str, Any]] = []
    future_rows: list[dict[str, Any]] = []
    total_rows = 0
    valid_rows = 0

    for source_row in repository.iter_transactions():
        row = dict(source_row)
        total_rows += 1
        period = str(row.get("transaction_period") or "").strip()
        if period > as_of_period:
            future_rows.append(row)
        region = normalize_market_region(str(row.get("city") or ""), str(row.get("district") or ""))
        if region.valid and region.district:
            valid_rows += 1
            valid_scopes.add((region.county, region.district, period))
            valid_natural[_natural_key(row, region.county, region.district)] += 1
            valid_exact[_exact_key(row, region.county, region.district)] += 1
            if row.get("dedupe_key"):
                valid_dedupe_keys.add(str(row["dedupe_key"]))
            continue
        invalid_rows.append(row)

    classifications: Counter[str] = Counter()
    collisions: Counter[str] = Counter()
    current_groups: Counter[tuple[str, str, str]] = Counter()
    target_groups: Counter[tuple[str, str, str]] = Counter()
    mapping_groups: Counter[tuple[str, str, str, str, str]] = Counter()
    source_groups: Counter[tuple[str, str]] = Counter()
    import_groups: Counter[tuple[str, str]] = Counter()
    period_groups: Counter[tuple[str, str]] = Counter()
    affected_scopes: set[tuple[str, str, str]] = set()
    manifest: list[dict[str, Any]] = []

    for row in invalid_rows:
        district = str(row.get("district") or "").strip()
        evidence = GeographyEvidence(
            row_id=row.get("id", ""),
            source=str(row.get("source") or ""),
            dedupe_key=str(row.get("dedupe_key") or ""),
            current_city=str(row.get("city") or ""),
            current_district=district,
            period=str(row.get("transaction_period") or ""),
            district_owner_counties=district_owners.get(normalized_storage_key(district), ()),
            canonical_district=canonical_districts.get(normalized_storage_key(district), ""),
            address_city=_address_city(str(row.get("address_text") or ""), counties),
            row_fingerprint=_row_fingerprint(row),
            source_transaction_identifier_preserved=False,
        )
        decision = classify_geography_evidence(evidence)
        classifications[decision.classification.value] += 1
        current_groups[(evidence.current_city, evidence.current_district, decision.classification.value)] += 1
        source_groups[(evidence.source, decision.classification.value)] += 1
        import_groups[(_date_text(row.get("imported_at")), decision.classification.value)] += 1
        period_groups[(evidence.period, decision.classification.value)] += 1

        collision = CollisionClassification.NO_COLLISION
        if decision.classification in {
            RepairClassification.SAFE_AUTOMATIC_REPAIR,
            RepairClassification.REPAIR_WITH_SUPPORTING_EVIDENCE,
        }:
            proposed_key = build_dedupe_key({**row, "city": decision.proposed_city, "district": decision.proposed_district})
            collision = classify_collision(
                CollisionEvidence(
                    exact_match_count=valid_exact[_exact_key(row, decision.proposed_city, decision.proposed_district)],
                    natural_key_match_count=valid_natural[
                        _natural_key(row, decision.proposed_city, decision.proposed_district)
                    ],
                    proposed_dedupe_key_match_count=int(proposed_key in valid_dedupe_keys),
                )
            )
            target_groups[(decision.proposed_city, decision.proposed_district, decision.classification.value)] += 1
            mapping_groups[
                (
                    evidence.current_city,
                    evidence.current_district,
                    decision.proposed_city,
                    decision.proposed_district,
                    decision.classification.value,
                )
            ] += 1
            scope = (decision.proposed_city, decision.proposed_district, evidence.period)
            affected_scopes.add(scope)
            valid_scopes.add(scope)
            collisions[collision.value] += 1
        manifest.append(build_manifest_entry(evidence, decision, collision))

    aggregate_stats = repository.aggregate_stats(as_of_period)
    future_aggregates = repository.future_aggregates(as_of_period)
    future_evidence = _future_evidence(future_rows, future_aggregates)
    future_classification = classify_future_evidence(future_evidence)
    reconciliation = simulate_reconciliation(
        ReconciliationInput(
            baseline_rows=total_rows,
            baseline_valid_rows=valid_rows,
            baseline_invalid_rows=len(invalid_rows),
            safe_automatic=classifications[RepairClassification.SAFE_AUTOMATIC_REPAIR.value],
            supporting_evidence=classifications[RepairClassification.REPAIR_WITH_SUPPORTING_EVIDENCE.value],
            ambiguous=classifications[RepairClassification.AMBIGUOUS.value],
            unresolved=classifications[RepairClassification.SOURCE_CORRUPT_OR_UNRESOLVED.value],
            future_rows=len(future_rows),
            affected_scopes=len(affected_scopes),
            aggregate_rows_before=aggregate_stats["aggregate_rows"],
            aggregate_rows_after_without_deduplication=len(valid_scopes),
        )
    )
    summary: dict[str, Any] = {
        "schema_version": "plvr-production-repair-plan-v1",
        "planner_mode": "select_only_dry_run",
        "as_of_period": as_of_period,
        "baseline": {
            "official_rows": total_rows,
            "canonical_valid_rows": valid_rows,
            "canonical_invalid_rows": len(invalid_rows),
            "future_rows": len(future_rows),
            "aggregate_rows": aggregate_stats["aggregate_rows"],
            "future_aggregate_rows": aggregate_stats["future_aggregate_rows"],
        },
        "geography_classification": dict(sorted(classifications.items())),
        "collision_classification": dict(sorted(collisions.items())),
        "groups": {
            "by_current_invalid_pair": _counter_rows(current_groups, ("current_city", "current_district", "classification"), top),
            "by_proposed_target": _counter_rows(target_groups, ("proposed_city", "proposed_district", "classification"), top),
            "by_mapping": _counter_rows(
                mapping_groups,
                ("current_city", "current_district", "proposed_city", "proposed_district", "classification"),
                top,
            ),
            "by_source": _counter_rows(source_groups, ("source", "classification"), top),
            "by_import_date": _counter_rows(import_groups, ("imported_date", "classification"), top),
            "by_import_run": {"status": "unavailable_no_row_level_link"},
            "by_period": _counter_rows(period_groups, ("period", "classification"), top),
        },
        "future": {
            "classification": future_classification.value,
            "aggregate_lineage_matches": future_aggregate_lineage_matches(future_evidence),
            "recommended_action": "quarantine_pending_authoritative_source_verification",
        },
        "reconciliation": reconciliation,
        "manifest": {
            "row_count": len(manifest),
            "checksum": manifest_checksum(manifest),
            "contains_raw_address": False,
            "contains_credentials": False,
        },
        "dedupe_dependency": {
            "geography_in_key": True,
            "source_transaction_identifier_persisted": False,
            "foreign_key_references_found": False,
            "regeneration_status": "blocked_without_authoritative_source_identifier",
        },
        "decision_gate": {
            "status": "NOT_READY_FOR_PHASE_2B2",
            "blockers": [
                "row_level_source_artifact_or_import_run_lineage_is_not_persisted",
                "collision_disposition_requires_operator_approval",
                "future_source_semantics_are_unresolved",
            ],
        },
    }
    summary["summary_checksum"] = summary_checksum(summary)
    return summary, manifest


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    database_url = os.getenv(args.database_url_env, "").strip()
    if not database_url:
        print(json.dumps({"status": "unavailable", "reason_code": "database_runtime_not_configured"}))
        return 2
    as_of_period = current_transaction_period(args.as_of_date)
    try:
        summary, manifest = build_production_repair_plan(
            ReadOnlyPostgresRepository(database_url, batch_size=max(1, args.batch_size)),
            as_of_period=as_of_period,
            top=max(1, args.top),
        )
    except Exception:
        print(json.dumps({"status": "unavailable", "reason_code": "read_only_planning_failed"}))
        return 2

    if args.summary_output:
        _write_json(args.summary_output, summary)
    if args.manifest_output:
        _write_json(args.manifest_output, {"entries": manifest, "checksum": manifest_checksum(manifest)})
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


def _district_owners(regions: Iterable[TaiwanRegion]) -> dict[str, tuple[str, ...]]:
    owners: dict[str, list[str]] = {}
    for region in regions:
        owners.setdefault(normalized_storage_key(region.district), []).append(region.county)
    return {district: tuple(dict.fromkeys(counties)) for district, counties in owners.items()}


def _address_city(address: str, counties: Iterable[str]) -> str:
    normalized_address = normalized_storage_key(address)
    for county in sorted(counties, key=len, reverse=True):
        if normalized_address.startswith(normalized_storage_key(county)):
            return county
    return ""


def _natural_key(row: Mapping[str, Any], city: str, district: str) -> tuple[Any, ...]:
    return (
        str(row.get("source") or ""),
        normalized_storage_key(city),
        normalized_storage_key(district),
        str(row.get("transaction_period") or ""),
        normalized_storage_key(row.get("address_text")),
        normalized_storage_key(row.get("road")),
        normalized_storage_key(row.get("building_type")),
        _rounded(row.get("area_ping")),
        _rounded(row.get("total_price")),
        _rounded(row.get("unit_price_per_ping")),
    )


def _exact_key(row: Mapping[str, Any], city: str, district: str) -> tuple[Any, ...]:
    return _natural_key(row, city, district) + (
        int(row.get("building_age_years") or 0),
        int(row.get("floor") or 0),
        int(row.get("total_floor") or 0),
    )


def _row_fingerprint(row: Mapping[str, Any]) -> str:
    safe_facts = {
        "source": row.get("source"),
        "dedupe_key": row.get("dedupe_key"),
        "period": row.get("transaction_period"),
        "address_hash": hashlib.sha256(str(row.get("address_text") or "").encode("utf-8")).hexdigest(),
        "road_hash": hashlib.sha256(str(row.get("road") or "").encode("utf-8")).hexdigest(),
        "building_type": row.get("building_type"),
        "area": _rounded(row.get("area_ping")),
        "total_price": _rounded(row.get("total_price")),
        "unit_price": _rounded(row.get("unit_price_per_ping")),
    }
    return hashlib.sha256(
        json.dumps(safe_facts, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _future_evidence(
    future_rows: list[dict[str, Any]],
    future_aggregates: list[Mapping[str, Any]],
) -> FutureEvidence:
    if not future_rows:
        return FutureEvidence()
    aggregate_source_count = len(future_rows)
    aggregate_record_count = sum(int(_row_value(row, "record_count", 4) or 0) for row in future_aggregates)
    return FutureEvidence(
        normalized_period=str(future_rows[0].get("transaction_period") or ""),
        aggregate_source_transaction_count=aggregate_source_count,
        aggregate_record_count=aggregate_record_count,
    )


def _counter_rows(counter: Counter[tuple[Any, ...]], names: tuple[str, ...], limit: int) -> list[dict[str, Any]]:
    rows = [dict(zip(names, key), count=count) for key, count in counter.items()]
    return sorted(rows, key=lambda row: (-int(row["count"]), *(str(row[name]) for name in names)))[:limit]


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _row_value(row: Any, name: str, index: int) -> Any:
    if isinstance(row, Mapping):
        return row.get(name)
    return row[index]


def _date_text(value: Any) -> str:
    return value.isoformat()[:10] if hasattr(value, "isoformat") else str(value or "")[:10]


def _rounded(value: Any) -> float:
    return round(float(value or 0), 2)


if __name__ == "__main__":
    raise SystemExit(main())
