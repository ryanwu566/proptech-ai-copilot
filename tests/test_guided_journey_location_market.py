"""Static contracts for the Phase 2 location and market journey workspace."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAGE = (ROOT / "frontend_next/app/page.tsx").read_text(encoding="utf-8")
HELPER = (ROOT / "frontend_next/lib/location-market-journey.ts").read_text(encoding="utf-8")
STAGE = (ROOT / "frontend_next/components/guided-journey/location-market-stage.tsx").read_text(encoding="utf-8")


def test_step_two_has_one_customer_question_and_unified_stage() -> None:
    journey = (ROOT / "frontend_next/lib/guided-journey.ts").read_text(encoding="utf-8")
    assert 'question: "journey.location.question"' in journey
    assert "LocationMarketStage" in PAGE
    for marker in ("JourneyPropertyContextHeader", "LocationMarketStatusStrip", "AmenityCategoryChart", "LocationMarketToolSelector", "LocationMarketSnapshot"):
        assert marker in STAGE


def test_property_context_is_presentation_only_and_runtime_safe() -> None:
    for field in ("city", "district", "road", "addressSummary", "buildingType", "areaPing", "askingPriceWan", "sourceLabel", "selectionStatus"):
        assert field in HELPER
    for forbidden in ("coordinates", "latitude", "longitude", "raw provider", "stack trace", "credentials", "token", "SQL"):
        assert forbidden not in HELPER
    assert '"not_selected" | "selected" | "partial"' in HELPER
    assert '"verified"' not in HELPER


def test_secondary_tools_are_explicit_and_lazy_mounted() -> None:
    assert 'useState<LocationMarketToolId[]>([])' in STAGE
    assert "addVisitedLocationMarketTool" in STAGE
    assert 'visitedTools.includes("commute")' in STAGE
    assert 'visitedTools.includes("terrain")' in STAGE
    assert 'visitedTools.includes("market")' in STAGE
    assert 'hidden={activeTool !== "commute"}' in STAGE
    assert 'hidden={activeTool !== "terrain"}' in STAGE
    assert 'hidden={activeTool !== "market"}' in STAGE
    assert "renderMarket" in STAGE


def test_next_step_only_navigates_without_running_valuation() -> None:
    assert 't("journey.price.next")' in STAGE
    assert "onContinueToPrice" in STAGE
    assert 't("trust.noPurchase")' in STAGE
    assert "api." not in STAGE
