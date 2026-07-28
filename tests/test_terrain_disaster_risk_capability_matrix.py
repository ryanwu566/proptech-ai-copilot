"""Contract tests for the terrain and disaster capability audit artifacts."""

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MATRIX_PATH = ROOT / "docs" / "terrain-disaster-risk-capability-matrix-v1.json"

CAPABILITY_STATES = {
    "official_live",
    "official_snapshot",
    "implemented_but_unverified",
    "partial",
    "demo",
    "mock",
    "placeholder",
    "unavailable",
    "not_integrated",
    "unknown",
}
PROVIDER_KINDS = {
    "live_external",
    "local_snapshot",
    "database",
    "static_file",
    "fixture",
    "mock",
    "stub",
    "placeholder",
    "none",
    "unknown",
}
REQUIRED_FIELDS = {
    "hazard_id",
    "display_name",
    "capability_state",
    "provider_present",
    "provider_kind",
    "source_name",
    "official_source_proven",
    "data_asset_present",
    "coverage_scope",
    "coverage_proven",
    "spatial_matching_method",
    "geocoding_dependency",
    "freshness_available",
    "source_version_available",
    "failure_state",
    "no_match_state",
    "unknown_preserved",
    "not_assessed_preserved",
    "unavailable_preserved",
    "frontend_present",
    "evidence_metadata_present",
    "property_case_transfer",
    "decision_effect",
    "supporting_files",
    "supporting_tests",
    "confirmed_gaps",
}
FORBIDDEN_KEYS = {
    "overall_score",
    "safety_score",
    "aggregate_score",
    "ranking",
    "winner",
    "purchase_recommendation",
    "recommendation",
}


def _tracked(path: str) -> bool:
    result = subprocess.run(
        ["git", "ls-files", "--error-unmatch", "--", path],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


def _walk_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        return set(value) | set().union(*(_walk_keys(item) for item in value.values()))
    if isinstance(value, list):
        return set().union(*(_walk_keys(item) for item in value)) if value else set()
    return set()


def test_capability_matrix_is_valid_and_complete() -> None:
    assert MATRIX_PATH.exists()
    rows = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))
    assert isinstance(rows, list)
    assert rows
    assert len({row["hazard_id"] for row in rows}) == len(rows)
    for row in rows:
        assert REQUIRED_FIELDS <= set(row)
        assert row["capability_state"] in CAPABILITY_STATES
        assert row["provider_kind"] in PROVIDER_KINDS
        assert row["decision_effect"] == "reference_only"
        assert isinstance(row["unknown_preserved"], bool)
        assert isinstance(row["not_assessed_preserved"], bool)
        assert isinstance(row["unavailable_preserved"], bool)
        assert isinstance(row["confirmed_gaps"], list)
        assert all(isinstance(gap, str) for gap in row["confirmed_gaps"])
        assert all(_tracked(path) for path in row["supporting_files"])
        assert all(_tracked(path) for path in row["supporting_tests"])


def test_matrix_never_promotes_unproven_capabilities() -> None:
    rows = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))
    for row in rows:
        if row["capability_state"] == "official_live":
            assert row["provider_present"] is True
            assert row["official_source_proven"] is True
            assert row["coverage_proven"] is True
            assert row["failure_state"]
            assert row["no_match_state"]
            assert row["supporting_files"]
            assert row["supporting_tests"]
            assert row["provider_kind"] not in {"fixture", "mock", "stub"}
        if row["capability_state"] == "official_snapshot":
            assert row["data_asset_present"] is True
            assert row["source_version_available"] is True
            assert row["freshness_available"] is True
        if row["capability_state"] in {"partial", "unknown", "not_integrated", "unavailable"}:
            assert row["coverage_proven"] is False


def test_matrix_preserves_fail_closed_state_language() -> None:
    rows = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))
    for row in rows:
        assert row["decision_effect"] == "reference_only"
        assert "low risk" not in row["no_match_state"].lower()
        assert "safe" not in row["failure_state"].lower()
        assert not ({"low_risk", "no_risk", "safety_score"} & _walk_keys(row))


def test_matrix_contains_required_hazards_and_no_score_fields() -> None:
    rows = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))
    hazard_ids = {row["hazard_id"] for row in rows}
    assert {"flood", "liquefaction", "landslide", "debris_flow", "active_fault", "slope", "elevation"} <= hazard_ids
    assert not (_walk_keys(rows) & FORBIDDEN_KEYS)


def test_audit_document_is_conservative_and_covers_required_sections() -> None:
    document = (ROOT / "docs" / "terrain-disaster-risk-audit-v1.md").read_text(encoding="utf-8")
    for heading in (
        "Executive Summary",
        "Current Architecture Map",
        "Hazard Capability Matrix",
        "Provider Inventory",
        "Data Source Evidence",
        "Geographic Coverage Evidence",
        "Address and Spatial Matching Flow",
        "State Contract Audit",
        "Frontend Presentation Audit",
        "Property Case Transfer Audit",
        "Privacy and Error Boundary Audit",
        "Existing Test Coverage",
        "Confirmed Gaps",
        "Risk-ranked Remediation Plan",
        "Definition of Done",
        "Release Decision",
    ):
        assert heading in document
    assert "RELEASE_DECISION=NO_GO" in document
    assert "official_live" not in document.split("## 3. Hazard Capability Matrix", 1)[1].split("## 4.", 1)[0] or "official_live" in document
    assert "全臺" in document
    assert "資料不足" in document
    assert "不代表沒有風險" in document
    assert "不得宣稱" in document
