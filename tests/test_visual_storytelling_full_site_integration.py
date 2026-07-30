"""Static full-site integration contracts for Phase 5A."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend_next"


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_primary_routes_keep_all_decision_modules_reachable() -> None:
    page = read("frontend_next/app/page.tsx")
    case_route = read("frontend_next/app/cases/[caseId]/page.tsx")
    for marker in (
        "PropertyFinder",
        "MarketInsight",
        "ValuationVisualPanel",
        "TaxDecisionVisualPanel",
        "LoanCalculator",
        "HoldingCostCalculator",
        "ViewingDecisionPanel",
    ):
        assert marker in page
    assert "PropertyCaseCommandCenter" in case_route
    assert "if (result && getValuationDisplayState(result).kind !== \"available\")" not in page


def test_visual_result_does_not_duplicate_page_chrome() -> None:
    page = read("frontend_next/app/page.tsx")
    result_section = page.split("function MarketInsightVisualResult", 1)[1].split("function AegisCredit", 1)[0]
    assert "<PageHeader" not in result_section
    assert "<HelpCallout" not in result_section
    assert "evidenceDisclosure" in result_section
    assert "<EvidenceSummary" in page.split("function MarketInsight(", 1)[1].split("function LegacyMarketInsightOriginal", 1)[0]


def test_dense_tables_are_disclosure_scoped_and_charts_are_mobile_safe() -> None:
    finder = read("frontend_next/components/property-finder.tsx")
    visual_dir = FRONTEND / "components" / "data-visualization"
    assert "return <DetailDisclosure" in finder
    assert 'copy("finder.transactions")' in finder
    for path in visual_dir.glob("*.tsx"):
        source = path.read_text(encoding="utf-8")
        if path.name in {"trend-line-chart.tsx", "volume-bar-chart.tsx"}:
            assert "overflow-x-auto" not in source
            assert "min-w-[560px]" not in source

def test_visual_integration_has_no_new_persistence_or_network_boundary() -> None:
    sources = [
        read("frontend_next/lib/visual-storytelling-copy.ts"),
        read("frontend_next/components/data-visualization/data-status-badge.tsx"),
        read("frontend_next/components/data-visualization/evidence-summary.tsx"),
        read("frontend_next/components/data-visualization/evidence-details.tsx"),
        read("frontend_next/components/data-visualization/visual-data-unavailable-state.tsx"),
    ]
    combined = "\n".join(sources)
    for forbidden in ("localStorage", "sessionStorage", "document.cookie", "URLSearchParams", "fetch(", "Date.now"):
        assert forbidden not in combined
