"""Static contracts for the Guided Journey affordability cockpit."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAGE = (ROOT / "frontend_next/app/page.tsx").read_text(encoding="utf-8")
HELPER = (ROOT / "frontend_next/lib/guided-journey.ts").read_text(encoding="utf-8")
STAGE = (ROOT / "frontend_next/components/guided-journey/affordability-decision-stage.tsx").read_text(encoding="utf-8")


def test_affordability_step_has_the_product_question_and_boundary() -> None:
    assert "頭期、月付、持有成本與稅務條件如何？" in HELPER
    assert "這些結果不是銀行、會計師或主管機關的正式認定。" in HELPER


def test_affordability_step_embeds_loan_and_keeps_secondary_tools_explicit() -> None:
    assert "<AffordabilityDecisionStage" in PAGE
    assert "<LoanCalculator embedded" in PAGE
    assert "<AffordabilityToolSelector" in STAGE
    assert "initialSecondaryTool" in STAGE
    assert "visitedTools.includes" in STAGE
    assert "hidden={activeSecondaryTool !== \"holding\"}" in STAGE
    assert "hidden={activeSecondaryTool !== \"tax\"}" in STAGE


def test_affordability_stage_does_not_create_scores_or_automatic_decisions() -> None:
    for forbidden in ("purchaseScore", "affordabilityScore", "recommendBuy", "bestPrice", "bestLoan", "autoDecision"):
        assert forbidden not in STAGE
    assert "不會自動建立案件、保存結果、列印或產生推薦" in STAGE
