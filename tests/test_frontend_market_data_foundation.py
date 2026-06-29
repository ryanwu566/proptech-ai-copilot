"""Static checks for Market Insight PLVR bridge UI."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAGE = (ROOT / "frontend_next/app/page.tsx").read_text(encoding="utf-8")
API = (ROOT / "frontend_next/lib/api.ts").read_text(encoding="utf-8")


def _market_insight_component() -> str:
    start = PAGE.index("function MarketInsight")
    end = PAGE.index("function AegisCredit", start)
    return PAGE[start:end]


def test_market_insight_uses_manual_load_only() -> None:
    component = _market_insight_component()

    assert "api.marketStatus()" in component
    assert "api.marketRegions(selectedCounty)" in component
    assert "載入可用市場資料" in component
    assert "useEffect" not in component
    assert "api.marketInsight(first.city" not in component


def test_market_insight_has_county_selector_and_district_search() -> None:
    component = _market_insight_component()

    assert "選擇縣市" in component
    assert "搜尋行政區" in component
    assert "選擇行政區" in component
    assert "查詢市場資料" in component


def test_market_insight_unavailable_state_hides_fake_metrics() -> None:
    component = _market_insight_component()

    assert 'catalog.data_status!=="available"' in component
    assert "目前尚未取得可用的官方 PLVR 行政區聚合資料" in component
    assert "不會顯示 mock 平均單價、交易量、趨勢、生活機能或 ESG" in component


def test_market_insight_adds_no_browser_storage() -> None:
    component = _market_insight_component()

    assert "localStorage" not in component
    assert "sessionStorage" not in component
    assert "document.cookie" not in component
    assert "URLSearchParams" not in component


def test_market_api_contract_has_bridge_endpoints() -> None:
    assert "marketStatus" in API
    assert "/market-insights/status" in API
    assert "/market-insights/regions" in API
    assert "coverage_status" in API
    assert "source_updated_at" in API
