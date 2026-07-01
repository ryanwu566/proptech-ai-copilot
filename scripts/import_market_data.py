"""Build a traceable Market Insight aggregate from a local CSV file.

The importer is offline-only by design. It never downloads data and defaults to
dry-run mode so raw transaction inputs are not accidentally committed or
overwritten.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


REQUIRED_COLUMNS = {
    "county",
    "district",
    "period",
    "unit_price_per_ping",
}
DEFAULT_OUTPUT = Path("data/market/market_insight_aggregate.json")
VALID_COVERAGE_STATUSES = {"covered", "not_covered", "coverage_unknown", "partial", "nationwide", "unknown"}


def build_market_aggregate(
    input_path: Path,
    *,
    source_name: str,
    source_updated_at: str,
    coverage_status: str,
    coverage_manifest: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Aggregate local transaction rows into the Market Insight contract."""

    if coverage_status not in VALID_COVERAGE_STATUSES:
        raise ValueError("Invalid coverage_status.")
    rows = _read_rows(input_path)
    grouped: dict[tuple[str, str, str], list[float]] = defaultdict(list)
    for row in rows:
        county = _required_text(row, "county")
        district = _required_text(row, "district")
        period = _required_text(row, "period")
        unit_price = float(_required_text(row, "unit_price_per_ping"))
        if unit_price <= 0:
            continue
        grouped[(county, district, period)].append(unit_price)

    regions = []
    for (county, district, period), prices in sorted(grouped.items()):
        if not prices:
            continue
        regions.append(
            {
                "county": county,
                "district": district,
                "period": period,
                "average_unit_price": round(sum(prices) / len(prices), 2),
                "transaction_count": len(prices),
                "source_name": source_name,
                "source_updated_at": source_updated_at,
                "coverage_status": coverage_status,
                "data_status": "available",
                "caveat": "市場資料為行政區聚合結果，僅供行情背景參考；樣本不足時不代表價格較低或風險較低。",
                "source_file_hash": _sha256(input_path),
                "aggregation_method": "mean_unit_price_per_ping_by_county_district_period",
                "record_count": len(prices),
            }
        )

    data_status = "available" if regions else "unavailable"
    return {
        "schema_version": "market-data-foundation-v1",
        "source_name": source_name,
        "source_updated_at": source_updated_at,
        "coverage_status": coverage_status,
        "data_status": data_status,
        "source_file_hash": _sha256(input_path),
        "aggregation_method": "mean_unit_price_per_ping_by_county_district_period",
        "record_count": len(rows),
        "generated_at": datetime.now(UTC).isoformat(),
        "coverage_manifest": _safe_coverage_manifest(coverage_manifest),
        "regions": regions,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a local Market Insight aggregate artifact.")
    parser.add_argument("--input", required=True, type=Path, help="Local CSV prepared outside this repository.")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, type=Path)
    parser.add_argument("--source-name", required=True)
    parser.add_argument("--source-updated-at", required=True)
    parser.add_argument("--coverage-status", choices=sorted(VALID_COVERAGE_STATUSES), default="coverage_unknown")
    parser.add_argument("--coverage-manifest", type=Path)
    parser.add_argument("--write", action="store_true", help="Write the aggregate artifact. Omit for dry-run.")
    args = parser.parse_args()

    coverage_manifest = _read_coverage_manifest(args.coverage_manifest) if args.coverage_manifest else None
    aggregate = build_market_aggregate(
        args.input,
        source_name=args.source_name,
        source_updated_at=args.source_updated_at,
        coverage_status=args.coverage_status,
        coverage_manifest=coverage_manifest,
    )
    result = "success" if aggregate["regions"] else "failed"
    print(f"IMPORT_RESULT={result}")
    print(f"AGGREGATE_REGION_COUNT={len(aggregate['regions'])}")
    print(f"COVERAGE_STATUS={aggregate['coverage_status']}")
    print(f"DATA_STATUS={aggregate['data_status']}")
    if args.write:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(aggregate, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0 if aggregate["regions"] else 1


def _read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError("Input CSV does not exist.")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = REQUIRED_COLUMNS.difference(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Input CSV missing required columns: {', '.join(sorted(missing))}")
        return [dict(row) for row in reader]


def _required_text(row: dict[str, str], field: str) -> str:
    value = (row.get(field) or "").strip()
    if not value:
        raise ValueError(f"Input CSV has blank required value: {field}")
    return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_coverage_manifest(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Coverage manifest must be a JSON object.")
    return payload


def _safe_coverage_manifest(payload: dict[str, Any] | None) -> dict[str, int | str] | None:
    if not payload:
        return None
    status = str(payload.get("coverage_status") or payload.get("status") or "coverage_unknown").strip()
    if status not in VALID_COVERAGE_STATUSES:
        status = "coverage_unknown"
    covered = payload.get("covered_regions")
    unknown = payload.get("unknown_regions")
    return {
        "coverage_status": status,
        "covered_region_count": len(covered) if isinstance(covered, list) else 0,
        "unknown_region_count": len(unknown) if isinstance(unknown, list) else 0,
    }


if __name__ == "__main__":
    raise SystemExit(main())
