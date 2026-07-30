"""Static contracts for the Experience Architecture v3 Phase 1 audit."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "experience-architecture-v3-audit.md"
MATRIX = ROOT / "docs" / "experience-architecture-v3-capability-matrix.json"


def load_matrix() -> dict:
    return json.loads(MATRIX.read_text(encoding="utf-8"))


def test_audit_artifacts_exist_and_identify_the_verified_base() -> None:
    assert DOC.is_file()
    assert MATRIX.is_file()
    matrix = load_matrix()
    assert matrix["audit_version"] == "experience-architecture-v3-phase-1"
    assert matrix["base_sha"] == "24f24733ea21cfc2f3992a8ef5768c91beb32dcf"
    assert matrix["generated_from_repository"]["static_inventory_only"] is True


def test_route_and_journey_map_cover_the_existing_decision_spine() -> None:
    matrix = load_matrix()
    assert {page["route"] for page in matrix["pages"]} == {"/", "/cases/[caseId]"}
    assert [step["id"] for step in matrix["journey_steps"]] == [
        "property",
        "location",
        "price",
        "affordability",
        "decision",
    ]
    assert "PropertyFinder" in matrix["journey_steps"][0]["components"]
    assert "CommuteLivabilityCard" in matrix["journey_steps"][1]["components"]
    assert "ViewingDecisionPanel" in matrix["journey_steps"][-1]["components"]


def test_multilingual_matrix_has_target_locales_without_translating_contract_enums() -> None:
    matrix = load_matrix()["multilingual"]
    assert set(matrix["target_locales"]) == {"zh-TW", "en", "ja", "ko"}
    assert {row["locale"] for row in matrix["matrix"]} == set(matrix["target_locales"])
    assert "enum values remain stable" in matrix["stable_enum_policy"]
    assert matrix["new_dependency_added"] is False


def test_voice_read_aloud_is_explicit_safe_and_not_autoplayed() -> None:
    voice = load_matrix()["voice_read_aloud"]
    assert voice["explicit_play_required"] is True
    assert voice["autoplay"] is False
    assert voice["background_audio"] is False
    assert voice["visible_summary_only"] is True
    for field in ("raw_json_allowed", "coordinates_allowed", "provider_payload_allowed", "url_allowed", "hidden_state_allowed"):
        assert voice[field] is False
    assert set(voice["states"]) == {
        "supported",
        "unavailable",
        "permission_not_required",
        "voice_missing",
        "stopped",
        "speaking",
        "paused",
        "error",
    }


def test_voice_input_has_no_background_listening_or_persistence() -> None:
    voice = load_matrix()["voice_input"]
    assert voice["explicit_microphone_action"] is True
    assert voice["recording_status_visible"] is True
    assert voice["stop_action_required"] is True
    assert voice["background_listening"] is False
    assert voice["transcript_persisted"] is False
    assert voice["raw_audio_persisted"] is False
    assert voice["dangerous_action_confirmation_required"] is True
    assert {"save_case", "delete_case", "export_report", "place_bid"}.issubset(set(voice["blocked_actions"]))
    assert voice["voice_dependency_added"] is False


def test_privacy_contract_does_not_add_storage_or_sensitive_spoken_output() -> None:
    matrix = load_matrix()
    privacy = matrix["privacy"]
    assert privacy["audit_added_storage"] is False
    assert privacy["new_storage_key"] is False
    assert privacy["url_query_or_hash_added"] is False
    assert privacy["raw_audio_storage"] is False
    assert privacy["transcript_storage"] is False
    assert "address" in privacy["spoken_sensitive_fields"]
    assert "coordinates" in privacy["spoken_sensitive_fields"]
    assert "provider_payload" in privacy["spoken_sensitive_fields"]


def test_experience_contract_preserves_domain_boundaries_and_missing_data_safety() -> None:
    text = DOC.read_text(encoding="utf-8") + "\n" + MATRIX.read_text(encoding="utf-8")
    assert "Terrain is a risk-reference surface, not a security score." in text
    assert "not a security score" in text
    assert "winner" in text
    assert "No API, database schema, PLVR, valuation, loan, tax, terrain, commute or" in text
    assert "hide empty visuals" in text
    assert "NO_GO" in text
    assert "business-logic change" in text or "business logic" in text


def test_release_gate_records_pending_browser_and_production_acceptance() -> None:
    release = load_matrix()["release_decision"]
    assert release["decision"] == "NO_GO"
    assert release["browser_validation_completed"] is False
    assert release["production_validation_completed"] is False
    assert release["skipped_tests"] == 0
    assert release["xfail_tests"] == 0


def test_report_contains_required_audit_sections_and_phase_plan() -> None:
    text = DOC.read_text(encoding="utf-8")
    for heading in (
        "## 1. Executive Summary",
        "## 2. Current Route and Page Map",
        "## 3. Current Journey Map",
        "## 4. Interface Density Findings",
        "## 5. Primary Action Findings",
        "## 6. Copy Density Findings",
        "## 7. Visual and Chart Findings",
        "## 8. Responsive Risks",
        "## 9. Accessibility Risks",
        "## 10. Multilingual Capability",
        "## 11. Voice Read-Aloud Capability",
        "## 12. Voice Input Safety",
        "## 13. Privacy Findings",
        "## 14. Proposed Experience Architecture v3",
        "## 15. Recommended Implementation Phases",
        "## 16. Acceptance Criteria",
        "## 17. Confirmed Non-Goals",
        "## 18. Release Decision",
    ):
        assert heading in text
    for phase in range(2, 9):
        assert f"| {phase} |" in text
