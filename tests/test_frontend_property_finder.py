"""Static frontend contracts for Property Finder and compact data status."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAGE = (ROOT / "frontend_next" / "app" / "page.tsx").read_text(encoding="utf-8")
COMPONENT = (ROOT / "frontend_next" / "components" / "property-finder.tsx").read_text(encoding="utf-8")
API = (ROOT / "frontend_next" / "lib" / "api.ts").read_text(encoding="utf-8")
SHARE = (ROOT / "frontend_next" / "lib" / "valuation-share.ts").read_text(encoding="utf-8")


def test_property_finder_api_and_form_contracts() -> None:
    assert '"/valuation/property-search"' in API
    assert "找房雷達" in COMPONENT
    assert "搜尋看屋方向" in COMPONENT
    assert "推薦行政區" in COMPONENT
    assert "推薦路段" in COMPONENT
    assert "符合條件的成交樣本" in COMPONENT


def test_property_finder_can_fill_valuation_without_auto_estimate() -> None:
    assert "帶入估價" in COMPONENT
    handler = PAGE.split("async function usePropertyFinderSelection", 1)[1].split("async function estimate", 1)[0]
    assert "setCity(selection.city)" in handler
    assert "setRoad(selection.road)" in handler
    assert "api.valuation(" not in handler
    assert "已帶入估價條件，可按下估價重新查詢" in handler


def test_property_finder_mobile_tables_are_scoped_scroll_areas() -> None:
    assert "overflow-x-auto" in COMPONENT
    assert "min-w-[820px]" in COMPONENT
    assert "min-w-[980px]" in COMPONENT
    assert "w-full sm:w-auto" in COMPONENT


def test_data_status_does_not_render_long_coverage_note() -> None:
    card = PAGE.split("function ValuationDataStatusCard", 1)[1].split("function SwipeHint", 1)[0]
    assert "status.coverage_summary" in card
    assert "status.coverage_note_short" in card
    assert "status.official_coverage_note" not in card


def test_existing_share_and_html_export_remain_available() -> None:
    assert "複製分享連結" in PAGE
    assert "下載 HTML 摘要" in PAGE
    assert "找房雷達摘要" in SHARE
    assert "propertySearch?.road_suggestions.slice(0, 5)" in SHARE
