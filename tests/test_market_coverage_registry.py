"""Tests for canonical Taiwan market coverage registry."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from services.taiwan_admin_registry import (
    DEFAULT_REGISTRY_PATH,
    audit_region_coverage,
    expected_region_count,
    iter_taiwan_regions,
    load_taiwan_admin_areas,
    normalize_market_region,
)


ROOT = Path(__file__).resolve().parents[1]
SHARED_REGISTRY_PATH = ROOT / "frontend_next" / "lib" / "taiwan-admin-areas.json"


def test_backend_default_registry_uses_shared_frontend_json() -> None:
    assert DEFAULT_REGISTRY_PATH == SHARED_REGISTRY_PATH
    assert DEFAULT_REGISTRY_PATH.exists()


def test_shared_registry_loads_for_python_and_frontend() -> None:
    registry = json.loads(SHARED_REGISTRY_PATH.read_text(encoding="utf-8"))
    areas = load_taiwan_admin_areas()

    assert registry["schema_version"] == "taiwan-admin-areas-v1"
    assert areas == registry["areas"]
    assert len(areas) == 22
    assert len(iter_taiwan_regions()) == 368


def test_registry_normalizes_county_alias_and_rejects_cross_county_district() -> None:
    normalized = normalize_market_region(" 台北市 ", "信義區")
    assert normalized.valid is True
    assert normalized.county == "臺北市"
    assert normalized.district == "信義區"

    invalid = normalize_market_region("臺北市", "板橋區")
    assert invalid.valid is False
    assert invalid.reason == "unknown_district"


def test_registry_has_nationwide_county_district_pairs_without_metrics() -> None:
    registry = json.loads(SHARED_REGISTRY_PATH.read_text(encoding="utf-8"))
    serialized = json.dumps(registry, ensure_ascii=False)

    assert registry["schema_version"] == "taiwan-admin-areas-v1"
    assert len(registry["areas"]) == 22
    assert expected_region_count() == 368
    assert "average_unit_price" not in serialized
    assert "transaction_count" not in serialized
    assert "token" not in serialized.lower()


def test_coverage_audit_reports_full_partial_and_unknown() -> None:
    full_regions = [("臺北市", "信義區")]
    partial = audit_region_coverage(full_regions)
    assert partial["status"] == "PARTIAL"
    assert partial["covered_region_count"] == 1
    assert partial["missing_region_count"] > 0

    unknown = audit_region_coverage([], unknown_regions=[("臺北市", "信義區")])
    assert unknown["status"] == "UNKNOWN"
    assert unknown["unknown_region_count"] == 1


def test_coverage_audit_script_outputs_safe_lines(tmp_path: Path) -> None:
    manifest = tmp_path / "coverage.json"
    manifest.write_text(
        json.dumps({"covered_regions": [{"county": "臺北市", "district": "信義區"}]}),
        encoding="utf-8",
    )

    result = subprocess.run(
        [sys.executable, "scripts/audit_market_coverage.py", "--coverage-manifest", str(manifest)],
        cwd=ROOT,
        check=False,
        text=True,
        capture_output=True,
    )

    assert result.returncode != 0
    assert "MARKET_COVERAGE=PARTIAL" in result.stdout
    assert "EXPECTED_REGION_COUNT=368" in result.stdout
    forbidden = {"token", "database", "url", "raw_payload"}
    assert forbidden.isdisjoint(result.stdout.lower().split())
