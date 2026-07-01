"""Audit safe Market Insight region coverage from an operator manifest."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.taiwan_admin_registry import audit_region_coverage


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit Taiwan market coverage metadata without querying providers.")
    parser.add_argument("--coverage-manifest", type=Path, help="Local manifest with covered_regions and optional unknown_regions.")
    args = parser.parse_args()

    if not args.coverage_manifest or not args.coverage_manifest.exists():
        result = audit_region_coverage([], unknown_regions=[])
        result = {**result, "status": "UNKNOWN", "unknown_region_count": result["expected_region_count"]}
    else:
        payload = _read_manifest(args.coverage_manifest)
        result = audit_region_coverage(
            _region_pairs(payload.get("covered_regions", [])),
            unknown_regions=_region_pairs(payload.get("unknown_regions", [])),
        )

    print(f"MARKET_COVERAGE={result['status']}")
    print(f"EXPECTED_REGION_COUNT={result['expected_region_count']}")
    print(f"COVERED_REGION_COUNT={result['covered_region_count']}")
    print(f"MISSING_REGION_COUNT={result['missing_region_count']}")
    print(f"UNKNOWN_REGION_COUNT={result['unknown_region_count']}")
    print(f"MISSING_REGIONS={','.join(result['missing_regions'])}")
    print(f"UNKNOWN_REGIONS={','.join(result['unknown_regions'])}")
    return 0 if result["status"] == "FULL" else 1


def _read_manifest(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Coverage manifest must be a JSON object.")
    return payload


def _region_pairs(rows: Any) -> list[tuple[str, str]]:
    if not isinstance(rows, list):
        return []
    pairs: list[tuple[str, str]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        county = str(row.get("county") or "").strip()
        district = str(row.get("district") or "").strip()
        if county and district:
            pairs.append((county, district))
    return pairs


if __name__ == "__main__":
    raise SystemExit(main())
