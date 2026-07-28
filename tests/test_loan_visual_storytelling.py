from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend_next"
VISUAL_DIR = FRONTEND / "components" / "data-visualization"
HELPER = (FRONTEND / "lib" / "loan-visualization.ts").read_text(encoding="utf-8")
COMPONENT = (FRONTEND / "components" / "loan-calculator.tsx").read_text(encoding="utf-8")


def test_loan_model_is_pure_and_validates_financial_values() -> None:
    assert "buildLoanVisualModel" in HELPER
    assert "Number.isFinite" in HELPER
    assert "structureMatches" in HELPER
    assert "sensitivity.filter" in HELPER
    assert "differenceFromBase === 0" in (VISUAL_DIR / "loan-sensitivity-chart.tsx").read_text(encoding="utf-8")
    for forbidden in ("fetch(", "localStorage", "sessionStorage", "Date.now", "value || 0", "value ?? 0", ".sort("):
        assert forbidden not in HELPER


def test_loan_form_stays_visible_and_existing_manual_transfer_is_preserved() -> None:
    assert "貸款月付試算" in COMPONENT
    assert "計算貸款月付" in COMPONENT
    assert "LoanVisualPanel" in COMPONENT
    assert "onHoldingCost?.(loan)" in COMPONENT
    assert "api.loanCalculate" in COMPONENT
    assert "grace_period_monthly_payment ?? 0" not in COMPONENT
    assert "post_grace_monthly_payment ?? 0" not in COMPONENT


def test_loan_visual_hierarchy_and_safe_language_exist() -> None:
    panel = (VISUAL_DIR / "loan-visual-panel.tsx").read_text(encoding="utf-8")
    grace = (VISUAL_DIR / "loan-grace-period-chart.tsx").read_text(encoding="utf-8")
    structure = (VISUAL_DIR / "loan-financing-structure-chart.tsx").read_text(encoding="utf-8")
    evidence = (VISUAL_DIR / "calculation-evidence-details.tsx").read_text(encoding="utf-8")
    for text in ("貸款試算摘要", "頭期款", "貸款金額", "每月月付", "總利息", "LoanFinancingStructureChart", "LoanSensitivityChart", "CalculationEvidenceDetails"):
        assert text in panel
    assert "無法取得寬限期月付明細" in grace
    assert "寬限期內通常只繳利息" in grace
    assert "structureMatches" in HELPER
    assert "DetailDisclosure" in evidence
    for source in (grace, structure, (VISUAL_DIR / "loan-sensitivity-chart.tsx").read_text(encoding="utf-8")):
        assert 'role="img"' in source
        assert "aria-label" in source
        assert "<title>" in source or "aria-label" in source
        assert "max-w-full" in source
        assert "overflow-x-auto" not in source
    for forbidden in ("銀行一定會核貸", "安全貸款", "最佳貸款方案", "一定能買得起"):
        assert forbidden not in panel


def test_loan_affordability_and_income_states_are_explicit() -> None:
    status = (VISUAL_DIR / "affordability-status.tsx").read_text(encoding="utf-8")
    assert '"未評估"' in HELPER
    assert "尚未輸入收入" in HELPER
    assert 'role="status"' in status
    assert "value.message" in status


def test_loan_main_charts_do_not_require_horizontal_scroll_or_new_dependency() -> None:
    for name in ("loan-financing-structure-chart.tsx", "loan-sensitivity-chart.tsx", "loan-grace-period-chart.tsx"):
        source = (VISUAL_DIR / name).read_text(encoding="utf-8")
        assert "h-auto w-full" in source
        assert "min-w-[520px]" not in source
        assert "min-w-[620px]" not in source
        assert "overflow-x-auto" not in source
        assert "recharts" not in source.lower()
        assert "chart.js" not in source.lower()
