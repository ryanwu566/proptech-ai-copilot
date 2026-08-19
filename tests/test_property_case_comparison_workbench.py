"""Static contracts for explicit, non-ranking case comparison."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HELPER = (ROOT / "frontend_next/lib/property-case-comparison.ts").read_text(encoding="utf-8")
WORKBENCH = (ROOT / "frontend_next/components/data-visualization/property-case-comparison-workbench.tsx").read_text(encoding="utf-8")


def test_comparison_requires_two_and_caps_at_three_selected_cases() -> None:
    assert "selectedIds" in HELPER
    assert ".slice(0, 3)" in HELPER
    assert "rows.length >= 2" in HELPER
    assert "rows.length <= 3" in HELPER
    assert "selectedIds.length >= 3" in WORKBENCH


def test_comparison_selection_is_explicit_and_local_only() -> None:
    assert "type=\"checkbox\"" in WORKBENCH
    assert "selectedIds" in WORKBENCH
    assert "useState" in WORKBENCH
    for forbidden in ("localStorage", "sessionStorage", "URLSearchParams", "location.hash", "JSON.stringify"):
        assert forbidden not in WORKBENCH


def test_comparison_uses_saved_case_helper_without_new_storage_schema() -> None:
    assert "readSavedCases" in WORKBENCH
    assert "SavedCase" in HELPER
    assert "buildPropertyCaseComparisonModel" in HELPER
    assert "new storage" not in HELPER.lower()


def test_comparison_shows_known_fields_and_missing_data() -> None:
    for field in (
        "caseName",
        "addressSummary",
        "decisionStatus",
        "listingPrice",
        "userEstimatedValue",
        "initialCashNeeded",
        "monthlyPayment",
        "monthlyHoldingCost",
        "financialStatus",
        "dueDiligenceReadiness",
        "viewingOfferReadiness",
        "timelineReadiness",
        "missingDataCount",
    ):
        assert field in HELPER or field in WORKBENCH
    assert "未提供" in WORKBENCH or "viz.caseComparisonNotProvided" in WORKBENCH


def test_comparison_does_not_add_rank_score_winner_or_recommendation() -> None:
    for forbidden in ("ranking", "rank", "score", "winner", "bestCase", "推薦購買", "最佳物件", "第一名"):
        assert forbidden not in HELPER
        assert forbidden not in WORKBENCH


def test_comparison_is_vertical_on_mobile_and_has_no_main_table_scroll() -> None:
    assert "md:grid-cols-2 xl:grid-cols-3" in WORKBENCH
    assert "min-w-0" in WORKBENCH
    assert "overflow-x-auto" not in WORKBENCH
    assert "min-w-[" not in WORKBENCH


def test_comparison_keeps_market_commute_and_terrain_out_of_decision_fields() -> None:
    for forbidden in ("marketScore", "commuteScore", "terrainScore", "locationRank", "riskScore"):
        assert forbidden not in HELPER
        assert forbidden not in WORKBENCH


def test_comparison_notice_is_conservative() -> None:
    assert "資料不足，僅比較已知欄位" in HELPER
    assert "不產生排名或購買建議" in HELPER
    assert "資料不足" in WORKBENCH or "viz.caseComparisonPartialNote" in WORKBENCH
