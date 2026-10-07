"""Static contracts for valuation share links and HTML summary export."""

from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
HELPER = (ROOT / "frontend_next" / "lib" / "valuation-share.ts").read_text(encoding="utf-8")
PAGE = (ROOT / "frontend_next" / "app" / "page.tsx").read_text(encoding="utf-8")


def _share_initialization_effect(source: str) -> str:
    start = source.index("const shared=!embedded?parseValuationShareParams(window.location.search):undefined;")
    end = source.index("useEffect(()=>{api.valuationDataStatus()", start)
    return source[start:end]


def _assert_share_initialization_does_not_auto_estimate(source: str) -> None:
    assert "api.valuation(" not in _share_initialization_effect(source)


def test_share_link_whitelists_all_valuation_inputs() -> None:
    for field in ("city", "district", "road", "building_type", "area_ping", "building_age_years", "floor"):
        assert f'"{field}"' in HELPER
    assert "value !== undefined && value !== null" in HELPER


def test_share_query_loads_inputs_without_auto_estimate() -> None:
    assert "parseValuationShareParams(window.location.search)" in PAGE
    assert "已載入分享條件，可按下估價重新查詢" in PAGE
    shared_block = _share_initialization_effect(PAGE)
    for assignment in (
        "setCity(shared.city)",
        "setDistrict(shared.district)",
        "setRoad(shared.road)",
        "setType(shared.building_type)",
        "setArea(shared.area_ping)",
        "setAge(shared.building_age_years)",
        "setFloor(shared.floor)",
    ):
        assert assignment in shared_block
    _assert_share_initialization_does_not_auto_estimate(PAGE)

    estimate_start = PAGE.index("async function estimate()")
    estimate_end = PAGE.index("const shareInputs:", estimate_start)
    assert "api.valuation(" in PAGE[estimate_start:estimate_end]


def test_share_no_auto_estimate_contract_rejects_an_inserted_call() -> None:
    injected = PAGE.replace("if(shared){", "if(shared){void api.valuation({});", 1)
    with pytest.raises(AssertionError):
        _assert_share_initialization_does_not_auto_estimate(injected)


def test_share_and_html_download_buttons_exist_and_are_mobile_safe() -> None:
    assert 'copy("valuation.copyShare")' in PAGE
    assert 'copy("valuation.download")' in PAGE
    assert 'className="w-full sm:w-auto"' in PAGE
    assert "break-all" in PAGE


def test_html_summary_contains_required_sections_and_disclaimer() -> None:
    for text in (
        "PropTech AI Copilot 估價摘要",
        "查詢條件",
        "估價區間",
        "信心分數",
        "估價資料組成",
        "官方／樣本資料數量",
        "可比成交前 5 筆",
        "市場趨勢情境",
        "非正式鑑價、非銀行估價、非投資保證",
    ):
        assert text in HELPER
    assert "result.comparables.slice(0, 5)" in HELPER


def test_html_summary_allows_missing_trend() -> None:
    assert "trend?: ValuationTrendResult" in HELPER
    assert "const safeTrend = trend && getValuationTrendDisplayState(trend).kind === \"available\" ? trend : undefined" in HELPER
    assert "safeTrend ? `" in HELPER
    assert ": \"\"" in HELPER


def test_html_filename_format_is_timestamped() -> None:
    assert "valuation_summary_" in HELPER
    assert ".html`" in HELPER
