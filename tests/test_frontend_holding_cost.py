"""Static frontend contracts for the holding-cost workflow."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAGE = (ROOT / "frontend_next" / "app" / "page.tsx").read_text(encoding="utf-8")
COMPONENT = (ROOT / "frontend_next" / "components" / "holding-cost-calculator.tsx").read_text(encoding="utf-8")
LOAN = (ROOT / "frontend_next" / "components" / "loan-calculator.tsx").read_text(encoding="utf-8")
FINDER = (ROOT / "frontend_next" / "components" / "property-finder.tsx").read_text(encoding="utf-8")
API = (ROOT / "frontend_next" / "lib" / "api.ts").read_text(encoding="utf-8")
SHARE = (ROOT / "frontend_next" / "lib" / "valuation-share.ts").read_text(encoding="utf-8")


def test_holding_cost_form_and_api_client_exist() -> None:
    assert '"/holding-cost/calculate"' in API
    assert "holdingCostCalculate" in API
    for text in ("每月持有成本", "房屋總價（萬元）", "房貸月付（元／月）", "管理費（元／坪／月）", "修繕預備金", "房屋稅簡化估算率", "地價稅簡化估算率", "年保險費"):
        assert text in COMPONENT


def test_holding_cost_results_and_mobile_breakdown_exist() -> None:
    for text in ("每月總持有成本", "年持有成本", "月收入負擔率", "每月成本 breakdown", "管理費", "修繕預備金", "稅費", "保險"):
        assert text in COMPONENT
    assert "overflow-x-auto" in COMPONENT
    assert "min-w-[520px]" in COMPONENT
    assert "grid gap-3 sm:grid-cols-2 xl:grid-cols-3" in COMPONENT


def test_loan_valuation_and_property_finder_can_prefill_holding_cost() -> None:
    assert "帶入持有成本" in LOAN
    assert "loan.monthly_payment" in LOAN
    assert "propertyPriceWan" in LOAN
    assert "帶入持有成本" in FINDER
    assert "item.median_total_price, item.median_area_ping" in FINDER
    assert "item.total_price, item.area_ping" in FINDER
    assert "result.price_range.mid" in PAGE


def test_html_summary_contains_completed_holding_cost_result() -> None:
    for text in ("holdingCost?: HoldingCostResult", "每月持有成本", "每月總持有成本", "房貸月付", "管理費", "修繕預備金", "每月稅費簡化估算", "每月保險", "負擔率"):
        assert text in SHARE
    assert "holding.disclaimer" in SHARE
    assert "sessionStorage" in SHARE
