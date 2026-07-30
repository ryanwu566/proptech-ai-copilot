"""Static trust-boundary contracts for Phase 2."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STAGE = (ROOT / "frontend_next/components/guided-journey/location-market-stage.tsx").read_text(encoding="utf-8")
HELPER = (ROOT / "frontend_next/lib/location-market-journey.ts").read_text(encoding="utf-8")
MARKET = (ROOT / "frontend_next/app/page.tsx").read_text(encoding="utf-8")


def test_location_market_copy_keeps_reference_only_boundary() -> None:
    selector = (ROOT / "frontend_next/components/guided-journey/location-market-tool-selector.tsx").read_text(encoding="utf-8")
    for key in ("trust.referenceOnly", "trust.noPurchase", "journey.location.next"):
        assert f't("{key}")' in STAGE
    assert 'aria-pressed={activeTool === tool.id}' in selector
    assert "market:" in HELPER and "summary" in HELPER


def test_terrain_unknown_and_missing_data_are_not_safe_claims() -> None:
    assert 't("trust.referenceOnly")' in STAGE
    assert "unknown" in HELPER
    assert "not_started" in HELPER
    assert "低風險" not in STAGE


def test_market_reuses_existing_visual_result_and_does_not_create_decision_logic() -> None:
    assert "buildMarketInsightVisualModel" in MARKET
    assert "MarketInsightVisualResult" in MARKET
    for forbidden in ("location_score", "livability_score", "ranking", "winner", "推薦購買"):
        assert forbidden not in STAGE
