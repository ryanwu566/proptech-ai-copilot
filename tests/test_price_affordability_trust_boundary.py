"""Trust-boundary contracts for price and affordability handoff."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HELPER = (ROOT / "frontend_next/lib/price-affordability-journey.ts").read_text(encoding="utf-8")
PRICE_STAGE = (ROOT / "frontend_next/components/guided-journey/price-decision-stage.tsx").read_text(encoding="utf-8")
PAGE = (ROOT / "frontend_next/app/page.tsx").read_text(encoding="utf-8")


def test_price_trust_reuses_the_existing_valuation_display_state() -> None:
    assert 'from "@/lib/valuation-result-state"' in HELPER
    assert "getValuationDisplayState" in HELPER
    assert "actionable" in HELPER
    assert "officialEstimateWan" in HELPER


def test_only_explicit_price_actions_transfer_to_followup_tools() -> None:
    assert "onTransferToLoan" in PRICE_STAGE
    assert "onTransferToHolding" in PRICE_STAGE
    assert "actionsAvailable" in PRICE_STAGE
    price_stage = PAGE.split('if (step === "price")', 1)[1].split('if (step === "affordability")', 1)[0]
    assert 'onTransferToLoan={(priceWan) =>' in price_stage
    assert 'onTransferToHolding={(priceWan, areaPing) =>' in price_stage
    assert 'selectJourneyPrice(current, "valuation", priceWan)' in price_stage
    assert "actions.goToNextStep()" in price_stage
    assert "useEffect" not in price_stage
    assert 't("trust.noPurchase")' in PRICE_STAGE


def test_phase3_copy_does_not_claim_purchase_or_approval_outcomes() -> None:
    source = "\n".join((HELPER, PRICE_STAGE, PAGE.split("function renderJourneyStep", 1)[1].split("return <AppShell", 1)[0]))
    for forbidden in ("值得買", "值得看房", "保證核貸", "投資評分", "最佳價格", "最佳貸款", "推薦購入"):
        assert forbidden not in source
