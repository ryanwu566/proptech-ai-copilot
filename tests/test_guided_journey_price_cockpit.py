"""Static contracts for the Guided Journey price decision cockpit."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAGE = (ROOT / "frontend_next/app/page.tsx").read_text(encoding="utf-8")
HELPER = (ROOT / "frontend_next/lib/guided-journey.ts").read_text(encoding="utf-8")
STAGE = (ROOT / "frontend_next/components/guided-journey/price-decision-stage.tsx").read_text(encoding="utf-8")


def test_price_step_has_the_product_question_and_conservative_description() -> None:
    assert 'question: "journey.price.question"' in HELPER
    assert 'description: "journey.price.description"' in HELPER


def test_price_step_uses_one_embedded_valuation_workspace_and_explicit_transfers() -> None:
    assert "<PriceDecisionStage" in PAGE
    assert "<ValuationPage embedded" in PAGE
    assert "onTransferToLoan" in STAGE
    assert "onTransferToHolding" in STAGE
    assert 't("trust.noPurchase")' in STAGE


def test_price_stage_reuses_selected_property_without_duplicate_search() -> None:
    price_stage = PAGE.split('if (step === "price")', 1)[1].split('if (step === "affordability")', 1)[0]
    assert "<ValuationPage embedded" in price_stage
    assert "<PropertyFinder" not in price_stage
    assert 'data-testid="price-decision-workspace"' in STAGE
    assert "JourneyMissingDataPanel" in STAGE
