"""Static contracts for the Guided Journey price decision cockpit."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAGE = (ROOT / "frontend_next/app/page.tsx").read_text(encoding="utf-8")
HELPER = (ROOT / "frontend_next/lib/guided-journey.ts").read_text(encoding="utf-8")
STAGE = (ROOT / "frontend_next/components/guided-journey/price-decision-stage.tsx").read_text(encoding="utf-8")


def test_price_step_has_the_product_question_and_conservative_description() -> None:
    assert "這間房的價格有沒有官方成交依據？" in HELPER
    assert "先確認資料狀態、官方可比成交與估價區間。只有正式且可採取行動的估價，才能手動帶入後續工具。" in HELPER


def test_price_step_uses_one_embedded_valuation_workspace_and_explicit_transfers() -> None:
    assert "<PriceDecisionStage" in PAGE
    assert "<ValuationPage embedded" in PAGE
    assert "onTransferToLoan" in STAGE
    assert "onTransferToHolding" in STAGE
    assert "不會自動計算或儲存" in STAGE


def test_property_search_is_progressively_disclosed_in_price_stage() -> None:
    assert "<details" in STAGE
    assert "重新查看官方成交條件" in STAGE
    assert "<PropertyFinder embedded" in PAGE
