"""Static contracts for the Guided Journey affordability cockpit."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAGE = (ROOT / "frontend_next/app/page.tsx").read_text(encoding="utf-8")
HELPER = (ROOT / "frontend_next/lib/guided-journey.ts").read_text(encoding="utf-8")
STAGE = (ROOT / "frontend_next/components/guided-journey/affordability-decision-stage.tsx").read_text(encoding="utf-8")


def test_affordability_step_has_the_product_question_and_boundary() -> None:
    assert 'question: "journey.affordability.question"' in HELPER
    assert 't("trust.noPurchase")' in STAGE


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
    assert 't("trust.noPurchase")' in STAGE
