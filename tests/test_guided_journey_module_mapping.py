"""Static module-to-journey mapping contracts."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HELPER = (ROOT / "frontend_next/lib/guided-journey.ts").read_text(encoding="utf-8")
PAGE = (ROOT / "frontend_next/app/page.tsx").read_text(encoding="utf-8")


def test_module_mapping_is_explicit_and_static() -> None:
    expected = {
        '"property-finder": "property"',
        '"property-search": "property"',
        '"location-insight": "location"',
        "commute: \"location\"",
        '"terrain-risk": "location"',
        '"market-insight": "location"',
        "valuation: \"price\"",
        "loan: \"affordability\"",
        '"holding-cost": "affordability"',
        "taxoracle: \"affordability\"",
        '"property-case": "decision"',
        'comparison: "decision"',
    }
    for marker in expected:
        assert marker in HELPER


def test_mapping_does_not_turn_reference_tools_into_decision_scores() -> None:
    assert 'getJourneyStepForTool("market-insight")' not in HELPER
    assert '"market-insight": "price"' not in HELPER
    assert '"terrain-risk": "investment"' not in HELPER
    assert '"commute": "price"' not in HELPER
    journey_section = PAGE.split("function renderJourneyStep", 1)[1].split("function Dashboard", 1)[0]
    assert "市場資料僅供研究參考" in (ROOT / "frontend_next/lib/location-market-journey.ts").read_text(encoding="utf-8")
    selector = (ROOT / "frontend_next/components/guided-journey/location-market-tool-selector.tsx").read_text(encoding="utf-8")
    assert 't("journey.location.description")' in selector
    assert 'aria-pressed={activeTool === tool.id}' in selector


def test_all_five_customer_questions_and_tools_are_visible() -> None:
    for key in ("journey.property.question", "journey.location.question", "journey.price.question", "journey.affordability.question", "journey.decision.question"):
        assert key in HELPER
    for tool in ("PropertyFinder", "LocationInsight", "MarketInsight", "ValuationPage", "LoanCalculator", "HoldingCostCalculator", "TaxOracle", "PropertyCaseCommandCenter", "CaseManager"):
        assert tool in PAGE
