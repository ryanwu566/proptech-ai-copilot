"""Static frontend contracts for the loan calculator workflow."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAGE = (ROOT / "frontend_next" / "app" / "page.tsx").read_text(encoding="utf-8")
COMPONENT = (ROOT / "frontend_next" / "components" / "loan-calculator.tsx").read_text(encoding="utf-8")
FINDER = (ROOT / "frontend_next" / "components" / "property-finder.tsx").read_text(encoding="utf-8")
API = (ROOT / "frontend_next" / "lib" / "api.ts").read_text(encoding="utf-8")
SHARE = (ROOT / "frontend_next" / "lib" / "valuation-share.ts").read_text(encoding="utf-8")


def test_loan_calculator_form_and_api_client_exist() -> None:
    assert '"/loan/calculate"' in API
    assert "loanCalculate" in API
    for text in ("貸款月付試算", "房屋總價（萬元）", "頭期款比例", "年利率（%）", "貸款年限（年）", "寬限期年數", "月收入（萬元，可選）"):
        assert text in COMPONENT


def test_loan_results_and_sensitivity_are_visible() -> None:
    for text in ("頭期款", "貸款金額", "每月月付", "總還款", "總利息", "月收入負擔率", "利率敏感度"):
        assert text in COMPONENT
    assert "overflow-x-auto" in COMPONENT
    assert "min-w-[620px]" in COMPONENT
    assert "grid gap-3 sm:grid-cols-2 xl:grid-cols-3" in COMPONENT


def test_valuation_and_property_finder_can_fill_loan_without_auto_submit() -> None:
    assert PAGE.count("<LoanCalculator") >= 2
    assert "用估價中位總價試算" in PAGE
    assert "result.price_range.mid" in PAGE
    assert "帶入貸款" in FINDER
    assert "item.median_total_price" in FINDER
    assert "item.total_price" in FINDER
    handler = PAGE.split("function useLoanPrice", 1)[1].split("async function estimate", 1)[0]
    assert "setLoanPriceWan(priceWan)" in handler
    assert "api.loanCalculate" not in handler


def test_html_summary_contains_optional_loan_result() -> None:
    for text in ("loan?: LoanCalculationResult", "貸款月付試算", "房屋總價", "貸款金額", "月付", "總利息", "負擔率", "負擔等級", "利率敏感度"):
        assert text in SHARE
    assert "loan.disclaimer" in SHARE
