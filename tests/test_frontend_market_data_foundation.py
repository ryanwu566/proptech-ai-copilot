"""Static checks for the Market Insight direct query UI."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAGE = (ROOT / "frontend_next/app/page.tsx").read_text(encoding="utf-8")
API = (ROOT / "frontend_next/lib/api.ts").read_text(encoding="utf-8")


def _market_insight_component() -> str:
    start = PAGE.index("function MarketInsight")
    end = PAGE.index("function ReadModelMarketInsight", start)
    return PAGE[start:end]


def test_market_insight_queries_only_on_button_click_without_catalog_scan() -> None:
    component = _market_insight_component()

    assert "api.marketCatalog()" not in component
    assert "api.marketRegions" not in component
    assert "api.marketStatus" not in component
    assert "onClick={query}" in component
    assert "useEffect" not in component
    assert "api.marketInsight(first.city" not in component
    assert "api.marketInsight(county.trim(),district.trim()||undefined)" in component


def test_market_insight_has_county_required_and_optional_district_inputs() -> None:
    component = _market_insight_component()

    assert "縣市為必填" in component
    assert "行政區可留空" in component
    assert 'setError("請先輸入縣市。")' in component
    assert "查詢市場資料" in component


def test_market_insight_unavailable_state_hides_fake_metrics() -> None:
    component = _market_insight_component()

    assert "目前沒有可安全呈現的行情" in component
    assert "不會以 mock 平均單價、交易量、生活機能或 ESG 分數替代" in component
    assert "livability_score" not in component
    assert "esg_lite_score" not in component
    assert "trend" not in component


def test_market_insight_adds_no_browser_storage_or_url_state() -> None:
    component = _market_insight_component()

    assert "localStorage" not in component
    assert "sessionStorage" not in component
    assert "document.cookie" not in component
    assert "URLSearchParams" not in component


def test_market_api_contract_has_direct_query_endpoint_and_history() -> None:
    assert "/market-insights/query" in API
    assert "marketInsight: (county: string, district?: string" in API
    assert "history:" in API
    assert "livability_score" not in API.split("export type MarketResult", 1)[1].split("export type MarketRegion", 1)[0]
    assert "esg_lite_score" not in API.split("export type MarketResult", 1)[1].split("export type MarketRegion", 1)[0]
