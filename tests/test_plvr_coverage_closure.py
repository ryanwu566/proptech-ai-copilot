"""Coverage and geography contracts for PLVR Phase 2C.5."""

from __future__ import annotations

import copy
import json
from datetime import date
from pathlib import Path

from services.plvr_coverage_closure import build_coverage_report
from services.plvr_clean_shadow_rebuild import manifest_checksum
from services.plvr_data_integrity import (
    INVALID_CITY_DISTRICT_PAIR,
    normalized_row_integrity_reason,
)
from services.plvr_import_service import normalize_row


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "artifacts" / "plvr_source_manifest.json"
COVERAGE_MATRIX = ROOT / "artifacts" / "plvr_coverage_matrix.json"
SUMMARY = ROOT / "docs" / "plvr-coverage-reconciliation-summary-v1.json"


def _manifest() -> dict[str, object]:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def _source_row(city: str, district: str) -> dict[str, str]:
    return {
        "縣市": city,
        "鄉鎮市區": district,
        "交易標的": "房地(土地+建物)",
        "土地位置建物門牌": f"{city}中央路1號",
        "交易年月日": "1140105",
        "建物移轉總面積平方公尺": "99.17",
        "總價元": "24000000",
        "單價元平方公尺": "242008",
        "建物型態": "住宅大樓",
        "編號": f"ID-{city}",
    }


def _state(report: dict[str, object], city: str, period: str) -> str:
    matrix = report["matrix"]
    assert isinstance(matrix, list)
    return next(
        str(item["coverage_state"])
        for item in matrix
        if item["city"].replace("臺", "台") == city.replace("臺", "台")
        and item["period"] == period
    )


def test_official_release_metadata_defines_expected_coverage_ceiling() -> None:
    report = build_coverage_report(_manifest(), since="2023-09", until="2026-08")

    assert report["expected_release_ceiling"] == "2026-07"
    assert report["complete_through"] == "2026-05"
    assert report["counts"] == {
        "COMPLETE": 726,
        "PARTIAL": 44,
        "MISSING": 0,
        "NOT_YET_EXPECTED": 22,
        "NOT_APPLICABLE": 0,
    }
    assert report["raw_calendar_coverage_percent"] == 91.67
    assert report["expected_official_coverage_percent"] == 94.29


def test_committed_manifest_and_coverage_matrix_are_deterministic() -> None:
    manifest = _manifest()
    committed = json.loads(COVERAGE_MATRIX.read_text(encoding="utf-8"))
    rebuilt = build_coverage_report(manifest, since="2023-09", until="2026-08")

    assert manifest["manifest_sha256"] == manifest_checksum(manifest)
    assert committed["manifest_sha256"] == manifest["manifest_sha256"]
    assert committed["counts"] == rebuilt["counts"]
    assert committed["matrix"] == rebuilt["matrix"]
    assert len(committed["matrix"]) == 22 * 36
    assert "date.today" not in COVERAGE_MATRIX.read_text(encoding="utf-8")


def test_committed_summary_contains_no_row_level_claim_without_runtime() -> None:
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    reconciliation = summary["production_row_level_reconciliation"]

    assert reconciliation["status"] == "UNAVAILABLE_ROW_LEVEL_RUNTIME"
    assert reconciliation["reason_code"] == "production_read_runtime_not_configured"
    assert reconciliation["classified_rows"] is None
    assert summary["production_safety"] == {
        "select_only": True,
        "writes": 0,
        "migrations": 0,
        "rows_changed": 0,
        "cutover_performed": False,
    }
    serialized = json.dumps(summary, ensure_ascii=False).lower()
    for forbidden in ("address_text", "database_url", "password", "api_key", "token"):
        assert forbidden not in serialized


def test_recent_period_states_are_not_inferred_from_calendar_date() -> None:
    report = build_coverage_report(_manifest(), since="2023-09", until="2026-08")

    for city in ("新竹市", "嘉義市", "連江縣"):
        assert _state(report, city, "2026-05") == "COMPLETE"
        assert _state(report, city, "2026-06") == "PARTIAL"
        assert _state(report, city, "2026-07") == "PARTIAL"
        assert _state(report, city, "2026-08") == "NOT_YET_EXPECTED"


def test_partial_history_artifacts_are_official_release_scope_not_download_failure() -> None:
    report = build_coverage_report(_manifest(), since="2026-06", until="2026-08")
    audits = report["artifact_scope_audit"]
    partial = [item for item in audits if item["classification"] == "PARTIAL_BY_OFFICIAL_RELEASE"]

    assert [item["release"] for item in partial] == ["20260701", "20260711", "20260721"]
    assert all(item["omitted_city_members"] == ("連江縣",) for item in partial)
    assert all(item["can_reacquire_full_artifact"] is False for item in partial)


def test_missing_verified_artifact_is_a_failure_but_zero_transactions_are_not() -> None:
    manifest = copy.deepcopy(_manifest())
    manifest["artifacts"][0]["verification_status"] = "REJECTED"

    report = build_coverage_report(manifest, since="2023-09", until="2023-09")

    assert report["counts"]["MISSING"] == 22
    assert report["counts"]["COMPLETE"] == 0


def test_hsinchu_and_chiayi_city_level_source_geography_is_explicitly_opt_in() -> None:
    for city in ("新竹市", "嘉義市"):
        rejected, reason = normalize_row(
            _source_row(city, city), city_hint=city, as_of=date(2026, 8, 11)
        )
        accepted, accepted_reason = normalize_row(
            _source_row(city, city),
            city_hint=city,
            as_of=date(2026, 8, 11),
            allow_official_city_level=True,
        )

        assert rejected is None
        assert reason == INVALID_CITY_DISTRICT_PAIR
        assert accepted_reason is None
        assert accepted is not None
        assert accepted["city"] == city
        assert accepted["district"] == ""
        assert accepted["geographic_unit_kind"] == "city_level"
        assert normalized_row_integrity_reason(
            accepted, as_of=date(2026, 8, 11), allow_official_city_level=True
        ) is None
        assert normalized_row_integrity_reason(accepted, as_of=date(2026, 8, 11)) == INVALID_CITY_DISTRICT_PAIR


def test_regular_district_geography_remains_unchanged() -> None:
    accepted, reason = normalize_row(
        _source_row("臺北市", "中正區"),
        city_hint="臺北市",
        as_of=date(2026, 8, 11),
        allow_official_city_level=True,
    )

    assert reason is None
    assert accepted is not None
    assert accepted["city"] == "臺北市"
    assert accepted["district"] == "中正區"
    assert accepted["geographic_unit_kind"] == "district"
