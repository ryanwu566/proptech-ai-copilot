"""Static trust-boundary contracts for Phase 2."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STAGE = (ROOT / "frontend_next/components/guided-journey/location-market-stage.tsx").read_text(encoding="utf-8")
HELPER = (ROOT / "frontend_next/lib/location-market-journey.ts").read_text(encoding="utf-8")
MARKET = (ROOT / "frontend_next/app/page.tsx").read_text(encoding="utf-8")


def test_location_market_copy_keeps_reference_only_boundary() -> None:
    selector = (ROOT / "frontend_next/components/guided-journey/location-market-tool-selector.tsx").read_text(encoding="utf-8")
    for marker in ("通勤資訊只供生活安排參考", "研究參考，不會自動影響估價或案件決策", "不會影響估價、風險或案件排名"):
        assert marker in STAGE
    assert "不會合成分數" in selector
    assert "市場資料僅供研究參考" in HELPER


def test_terrain_unknown_and_missing_data_are_not_safe_claims() -> None:
    assert "不代表沒有風險" in STAGE
    assert "unknown" in HELPER
    assert "not_started" in HELPER
    assert "低風險" not in STAGE


def test_market_reuses_existing_visual_result_and_does_not_create_decision_logic() -> None:
    assert "buildMarketInsightVisualModel" in MARKET
    assert "MarketInsightVisualResult" in MARKET
    for forbidden in ("location_score", "livability_score", "ranking", "winner", "推薦購買"):
        assert forbidden not in STAGE
