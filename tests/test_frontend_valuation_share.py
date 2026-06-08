"""Static contracts for valuation share links and HTML summary export."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HELPER = (ROOT / "frontend_next" / "lib" / "valuation-share.ts").read_text(encoding="utf-8")
PAGE = (ROOT / "frontend_next" / "app" / "page.tsx").read_text(encoding="utf-8")


def test_share_link_whitelists_all_valuation_inputs() -> None:
    for field in ("city", "district", "road", "building_type", "area_ping", "building_age_years", "floor"):
        assert f'"{field}"' in HELPER
    assert "value !== undefined && value !== null" in HELPER


def test_share_query_loads_inputs_without_auto_estimate() -> None:
    assert "parseValuationShareParams(window.location.search)" in PAGE
    assert "已載入分享條件，可按下估價重新查詢" in PAGE
    shared_block = PAGE.split("if(shared){", maxsplit=1)[1].split("}},[]);", maxsplit=1)[0]
    assert "api.valuation(" not in shared_block


def test_share_and_html_download_buttons_exist_and_are_mobile_safe() -> None:
    assert "複製分享連結" in PAGE
    assert "下載 HTML 摘要" in PAGE
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
    assert "trend ? `" in HELPER
    assert ": \"\"" in HELPER


def test_html_filename_format_is_timestamped() -> None:
    assert "valuation_summary_" in HELPER
    assert ".html`" in HELPER
