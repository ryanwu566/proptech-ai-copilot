"""Static checks for Market Insight unavailable-first UI."""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAGE = (ROOT / "frontend_next/app/page.tsx").read_text(encoding="utf-8")
API = (ROOT / "frontend_next/lib/api.ts").read_text(encoding="utf-8")


def _market_insight_component() -> str:
    start = PAGE.index("function MarketInsight")
    end = PAGE.index("function AegisCredit", start)
    return PAGE[start:end]


def test_market_insight_does_not_auto_query_first_region() -> None:
    component = _market_insight_component()

    assert "api.marketRegions()" in component
    assert "api.marketInsight(first.city" not in component
    assert "查詢區域行情" in component


def test_market_insight_unavailable_state_hides_fake_metrics() -> None:
    component = _market_insight_component()

    assert 'catalog.data_status !== "available"' in component
    assert "目前尚未接上可追溯的全台市場資料" in component
    assert "不顯示平均單價、交易量、趨勢、生活機能或 ESG" in component


def test_market_insight_adds_no_browser_storage() -> None:
    component = _market_insight_component()

    assert "localStorage" not in component
    assert "sessionStorage" not in component
    assert "document.cookie" not in component
    assert "URLSearchParams" not in component


def test_market_api_contract_has_foundation_metadata() -> None:
    assert "data_status" in API
    assert "coverage_status" in API
    assert "source_updated_at" in API
    assert "MarketRegionCatalog" in API
