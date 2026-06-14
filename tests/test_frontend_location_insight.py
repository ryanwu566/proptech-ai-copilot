"""Static frontend contracts for the decision-oriented location insight."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAGE = (ROOT / "frontend_next" / "app" / "page.tsx").read_text(encoding="utf-8")
COMPONENT = (ROOT / "frontend_next" / "components" / "location-insight.tsx").read_text(encoding="utf-8")
FINDER = (ROOT / "frontend_next" / "components" / "property-finder.tsx").read_text(encoding="utf-8")
API = (ROOT / "frontend_next" / "lib" / "api.ts").read_text(encoding="utf-8")
SHARE = (ROOT / "frontend_next" / "lib" / "valuation-share.ts").read_text(encoding="utf-8")


def test_location_insight_form_and_api_client_exist() -> None:
    assert '"/location/insight"' in API
    assert "locationInsight" in API
    for text in ("區位分析", "縣市", "行政區", "路段", "完整地址（可選）", "分析半徑（公尺）"):
        assert text in COMPONENT


def test_location_results_and_unavailable_state_are_visible() -> None:
    for text in ("區位總分", '"交通"', '"生活機能"', "區位優點", "區位缺點", "最近 POI", "資料品質"):
        assert text in COMPONENT
    assert "目前資料不足，建議改用完整地址或手動查詢" in COMPONENT
    assert "overflow-x-auto" in COMPONENT
    assert "min-w-[560px]" in COMPONENT


def test_property_finder_and_valuation_can_prefill_location() -> None:
    assert "分析區位" in FINDER
    assert "onUseForLocationInsight" in FINDER
    assert "item.median_total_price" in FINDER
    assert "item.total_price" in FINDER
    assert "prefillLocationInsight({city,district,road" in PAGE
    assert "result?.price_range.mid" in PAGE


def test_html_summary_contains_location_insight() -> None:
    for text in ("locationInsight?: LocationInsightResult", "區位分析", "區位總分", "區位優點", "區位缺點", "POI 摘要", "資料品質"):
        assert text in SHARE
    assert "location.disclaimer" in SHARE
