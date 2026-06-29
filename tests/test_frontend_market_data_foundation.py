"""Static checks for the Market Insight read model explorer UI."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAGE = (ROOT / "frontend_next/app/page.tsx").read_text(encoding="utf-8")
API = (ROOT / "frontend_next/lib/api.ts").read_text(encoding="utf-8")


def _market_insight_component() -> str:
    start = PAGE.index("function MarketInsight")
    end = PAGE.index("function LegacyMarketInsight", start)
    return PAGE[start:end]


def test_market_insight_loads_catalog_only_on_button_click() -> None:
    component = _market_insight_component()

    assert "api.marketCatalog()" in component
    assert "onClick={loadCatalog}" in component
    assert "useEffect" not in component
    assert "api.marketInsight(first.city" not in component
    assert "api.marketInsight(county,district)" in component


def test_market_insight_has_county_selector_district_search_and_manual_query() -> None:
    component = _market_insight_component()

    assert "available_counties" in component
    assert "changeCounty(e.target.value)" in component
    assert "api.marketRegions(value)" in component
    assert "搜尋行政區" in component
    assert "查詢行政區行情" in component


def test_market_insight_unavailable_state_hides_fake_metrics() -> None:
    component = _market_insight_component()

    assert 'catalog.read_model_status!=="ready"' in component
    assert "不會以展示數字、生活機能分數、ESG 分數或假趨勢替代" in component
    assert "livability_score" not in component
    assert "esg_lite_score" not in component
    assert "trend" not in component


def test_market_insight_adds_no_browser_storage_or_url_state() -> None:
    component = _market_insight_component()

    assert "localStorage" not in component
    assert "sessionStorage" not in component
    assert "document.cookie" not in component
    assert "URLSearchParams" not in component


def test_market_api_contract_has_read_model_endpoints_and_history() -> None:
    assert "marketCatalog" in API
    assert "/market-insights/catalog" in API
    assert "/market-insights/regions" in API
    assert "/market-insights/query" in API
    assert "read_model_status" in API
    assert "history:" in API
    assert "livability_score" not in API.split("export type MarketResult", 1)[1].split("export type MarketRegion", 1)[0]
    assert "esg_lite_score" not in API.split("export type MarketResult", 1)[1].split("export type MarketRegion", 1)[0]
