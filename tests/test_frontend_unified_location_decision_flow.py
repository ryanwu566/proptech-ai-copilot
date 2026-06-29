"""Static contracts for Unified Location Decision Flow v1."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend_next"
LOCATION = (FRONTEND / "components" / "location-insight.tsx").read_text(encoding="utf-8")
TERRAIN = (FRONTEND / "components" / "terrain-risk-analysis.tsx").read_text(encoding="utf-8")
COMMUTE = (FRONTEND / "components" / "commute-livability-card.tsx").read_text(encoding="utf-8")
LOAN = (FRONTEND / "components" / "loan-calculator.tsx").read_text(encoding="utf-8")
PAGE = (FRONTEND / "app" / "page.tsx").read_text(encoding="utf-8")
VIEWING_DECISION = (FRONTEND / "components" / "viewing-decision-panel.tsx").read_text(encoding="utf-8")
CASE_COMPARISON = (FRONTEND / "lib" / "case-comparison.ts").read_text(encoding="utf-8")


def test_location_flow_has_single_clear_sequence() -> None:
    for text in ("位置洞察", "地勢／災害風險", "通勤與生活機能", "在地圖查看"):
        assert text in LOCATION
    assert "用同一個物件地址" in LOCATION
    assert "開始位置分析" in LOCATION
    assert "onLocationMap" in LOAN
    assert "onMap={() => setPage(\"Map Insight Lite\")}" in PAGE


def test_location_flow_has_one_primary_address_input() -> None:
    assert LOCATION.count("物件地址<input") == 1
    assert "完整地址（可選）" not in LOCATION
    assert "縣市<input" not in LOCATION
    assert "行政區<input" not in LOCATION
    assert "路段<input" not in LOCATION
    assert "setAddress(detail.address ?? `${detail.city ?? \"\"}${detail.district ?? \"\"}${detail.road ?? \"\"}`)" in LOCATION


def test_blank_address_blocks_location_api_and_shows_message() -> None:
    assert 'if (!address.trim())' in LOCATION
    assert "請先輸入完整物件地址。" in LOCATION
    assert 'disabled={loading || !address.trim()}' in LOCATION
    before_analyze = LOCATION.split("async function analyze", 1)[0]
    assert "api.locationInsight" not in before_analyze
    assert "api.terrainRiskAnalyze" not in before_analyze
    assert "api.commuteAddressLookup" not in before_analyze


def test_address_change_invalidates_old_location_terrain_and_commute_results() -> None:
    assert "function invalidateLocationFlow()" in LOCATION
    assert "setResult(undefined)" in LOCATION
    assert "window.sessionStorage.removeItem(LOCATION_INSIGHT_SESSION_KEY)" in LOCATION
    assert "window.sessionStorage.removeItem(TERRAIN_RISK_SESSION_KEY)" in LOCATION
    assert "invalidateLocationFlow();" in LOCATION
    assert "resetKey={address}" in LOCATION
    assert "latestAddressRef.current = address" in COMMUTE
    assert "setResult(null)" in COMMUTE.split("useEffect", 1)[1].split("async function lookupCommute", 1)[0]


def test_terrain_uses_location_context_without_duplicate_address_inputs() -> None:
    assert "compactFromLocation" in TERRAIN
    assert "查看地勢與災害" in TERRAIN
    compact_branch = TERRAIN.split("compactFromLocation &&", 1)[1]
    assert "使用上方位置洞察的可信位置脈絡" in compact_branch
    assert "location?.resolved_location" in TERRAIN
    assert "請先完成位置洞察" in TERRAIN


def test_commute_remains_manual_and_non_decisional() -> None:
    assert "查看通勤資訊" in COMMUTE
    assert "api.commuteAddressLookup" in COMMUTE
    assert "api.commuteAddressLookup" not in COMMUTE.split("useEffect", 1)[1].split("async function lookupCommute", 1)[0]
    for target in ("地勢風險", "估價", "貸款", "稅費", "法律", "看房決策"):
        assert target not in COMMUTE.split("api.commuteAddressLookup", 1)[1]
    assert "commute" not in VIEWING_DECISION.lower()
    assert "commute" not in CASE_COMPARISON.lower()


def test_unavailable_unknown_are_not_presented_as_safe() -> None:
    for text in ("unavailable", "not_assessed", "unknown"):
        assert text in TERRAIN
    for forbidden in ("安全", "無風險"):
        assert forbidden not in LOCATION
        assert forbidden not in TERRAIN


def test_no_new_location_flow_persistence_or_page_load_calls() -> None:
    new_location_section = LOCATION.split("function LocationInsight", 1)[1].split("function LocationResults", 1)[0]
    assert "localStorage" not in new_location_section
    assert "document.cookie" not in new_location_section
    assert "location.search" not in new_location_section
    assert "location.hash" not in new_location_section
    assert "api.locationInsight" not in new_location_section.split("async function analyze", 1)[0]
