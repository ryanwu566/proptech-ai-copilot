"""Static frontend contracts for the commute livability card."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend_next"
API = (FRONTEND / "lib" / "api.ts").read_text(encoding="utf-8")
HELPER = (FRONTEND / "lib" / "commute-livability-ui.ts").read_text(encoding="utf-8")
CARD = (FRONTEND / "components" / "commute-livability-card.tsx").read_text(encoding="utf-8")
LOCATION = (FRONTEND / "components" / "location-insight.tsx").read_text(encoding="utf-8")
VIEWING_PANEL = (FRONTEND / "components" / "viewing-decision-panel.tsx").read_text(encoding="utf-8")
DECISION_REPORT = (FRONTEND / "components" / "decision-report.tsx").read_text(encoding="utf-8")


def test_commute_api_client_uses_address_lookup_only() -> None:
    assert "CommuteAddressLookupResult" in API
    assert "commuteAddressLookup" in API
    assert '"/commute/address-lookup"' in API
    assert '"/commute/refresh"' not in API


def test_card_is_integrated_into_location_insight() -> None:
    assert "CommuteLivabilityCard" in LOCATION
    assert '<CommuteLivabilityCard address={address} />' in LOCATION
    assert "查看通勤資訊" in CARD
    assert "api.commuteAddressLookup" in CARD


def test_blank_address_and_manual_click_contract() -> None:
    assert "請先輸入完整物件地址。" in CARD
    assert "isBlankAddress" in CARD
    assert "onClick={lookupCommute}" in CARD
    assert "api.commuteAddressLookup" not in CARD.split("useEffect", 1)[1].split("async function lookupCommute", 1)[0]


def test_loading_and_conservative_states_are_present() -> None:
    for text in (
        "正在查詢通勤資訊⋯",
        "目前無法從此地址取得可信的通勤參考結果。",
        "通勤資料目前無法使用，請稍後再試。",
        "尚未查詢通勤資訊。",
    ):
        assert text in CARD or text in HELPER
    assert 'disabled={status === "loading"}' in CARD


def test_resolved_card_only_renders_allowed_commute_fields() -> None:
    for text in ("最近捷運站", "路線", "步行前的直線距離（公尺）", "資料來源／資料更新時間"):
        assert text in CARD
    assert "僅供通勤與生活機能參考，不影響地勢災害、貸款、法律或看房結論。" in CARD + HELPER
    for forbidden in ("latitude", "longitude", "formatted_address", "station_uid", "StationUID", "raw_payload", "token", "secret"):
        assert forbidden not in CARD


def test_address_change_resets_previous_result_without_storage() -> None:
    assert "latestAddressRef.current = address" in CARD
    assert 'setStatus("idle")' in CARD
    assert "setResult(null)" in CARD
    combined = CARD + HELPER
    for forbidden in ("localStorage", "sessionStorage", "location.hash", "location.search", "document.cookie"):
        assert forbidden not in combined


def test_viewing_decision_files_are_not_part_of_commute_card() -> None:
    assert "commute" not in VIEWING_PANEL.lower()
    assert "commute" not in DECISION_REPORT.lower()
