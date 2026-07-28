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
    assert "官方市場資料只作研究與背景參考" in journey_section
    assert "不影響其他決策" in journey_section


def test_all_five_customer_questions_and_tools_are_visible() -> None:
    for text in (
        "我現在看的是哪一間房？",
        "住在這裡方便嗎？區域行情與環境如何？",
        "這間房的開價有沒有官方成交依據？",
        "頭期、月付、持有成本與稅務條件如何？",
        "資料是否足夠，我接下來要做什麼？",
        "Property Finder",
        "Location Insight",
        "Market Insight",
        "Valuation",
        "Loan",
        "Holding Cost",
        "TaxOracle",
        "Property Case",
        "Comparison",
    ):
        assert text in PAGE or text in HELPER
