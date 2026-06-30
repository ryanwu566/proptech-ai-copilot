"""Static checks for the Market Insight direct query UI."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAGE = (ROOT / "frontend_next/app/page.tsx").read_text(encoding="utf-8")
API = (ROOT / "frontend_next/lib/api.ts").read_text(encoding="utf-8")
ADMIN_AREAS = (ROOT / "frontend_next/lib/taiwan-admin-areas.ts").read_text(encoding="utf-8")
SIDEBAR = (ROOT / "frontend_next/components/sidebar.tsx").read_text(encoding="utf-8")


def _market_insight_component() -> str:
    start = PAGE.index("function MarketInsight")
    end = PAGE.index("function LegacyTextMarketInsight", start)
    return PAGE[start:end]


def test_market_insight_queries_only_on_button_click_without_catalog_scan() -> None:
    component = _market_insight_component()

    assert "api.marketCatalog()" not in component
    assert "api.marketRegions" not in component
    assert "api.marketStatus" not in component
    assert "onClick={query}" in component
    assert "useEffect" not in component
    assert "api.marketInsight(first.city" not in component
    assert "api.marketInsight(canonicalCounty, canonicalDistrict || undefined)" in component


def test_market_insight_has_canonical_county_and_dependent_district_selectors() -> None:
    component = _market_insight_component()

    assert "縣市（必填）" in component
    assert "行政區（可留空）" in component
    assert "請先選擇縣市" in component
    assert "<select value={canonicalCounty}" in component
    assert "<select value={canonicalDistrict}" in component
    assert "disabled={!canonicalCounty}" in component
    assert "setDistrict(\"\")" in component
    assert 'setError("請先選擇縣市，再查詢市場資料。")' in component


def test_market_insight_unavailable_state_hides_fake_metrics() -> None:
    component = _market_insight_component()

    assert 'result?.data_status === "no_data"' in component
    assert "目前此區域尚無市場資料" in component
    assert "目前尚未找到足夠的官方 PLVR 市場資料。" in component
    assert "不會顯示 0 元、低風險或展示成功狀態" in component
    assert "!availableResult && !noDataResult" in component
    assert "livability_score" not in component
    assert "esg_lite_score" not in component
    assert "trend" not in component


def test_market_insight_adds_no_browser_storage_or_url_state() -> None:
    component = _market_insight_component()

    assert "localStorage" not in component
    assert "sessionStorage" not in component
    assert "document.cookie" not in component
    assert "URLSearchParams" not in component
    assert "location.search" not in component
    assert "location.hash" not in component


def test_market_api_contract_has_direct_query_endpoint_and_history() -> None:
    assert "/market-insights/query" in API
    assert "marketInsight: (county: string, district?: string" in API
    assert "history:" in API
    assert "livability_score" not in API.split("export type MarketResult", 1)[1].split("export type MarketRegion", 1)[0]
    assert "esg_lite_score" not in API.split("export type MarketResult", 1)[1].split("export type MarketRegion", 1)[0]


def test_taiwan_admin_area_helper_provides_canonical_aliases() -> None:
    assert "TAIWAN_ADMIN_AREAS" in ADMIN_AREAS
    assert "TAIWAN_COUNTIES" in ADMIN_AREAS
    assert "normalizeTaiwanCounty" in ADMIN_AREAS
    assert "normalizeTaiwanDistrict" in ADMIN_AREAS
    assert "getDistrictsForCounty" in ADMIN_AREAS
    assert "臺北市" in ADMIN_AREAS
    assert "信義區" in ADMIN_AREAS
    assert "[normalizeKey(county.replace(\"臺\", \"台\")), county]" in ADMIN_AREAS


def test_production_sidebar_no_longer_displays_market_mock_badge() -> None:
    assert "<span>Mock</span>" not in SIDEBAR
    assert "正式資料模式" in SIDEBAR
