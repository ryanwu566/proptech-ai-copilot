from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend_next"
VISUAL_DIR = FRONTEND / "components" / "data-visualization"
HELPER = (FRONTEND / "lib" / "holding-cost-visualization.ts").read_text(encoding="utf-8")
COMPONENT = (FRONTEND / "components" / "holding-cost-calculator.tsx").read_text(encoding="utf-8")


def test_holding_model_preserves_order_and_explicit_zero_without_persistence() -> None:
    assert "buildHoldingCostVisualModel" in HELPER
    assert "cost_breakdown.filter" in HELPER
    assert "nonNegative" in HELPER
    assert "breakdown," in HELPER
    assert ".sort(" not in HELPER
    for forbidden in ("fetch(", "localStorage", "sessionStorage", "Date.now", "value || 0", "value ?? 0"):
        assert forbidden not in HELPER
    assert "HOLDING_COST_SESSION_KEY" in COMPONENT
    assert "HOLDING_COST_PREFILL_EVENT" in COMPONENT
    assert "HOLDING_COST_RESULT_EVENT" in COMPONENT


def test_holding_form_and_visual_hierarchy_are_present() -> None:
    panel = (VISUAL_DIR / "holding-cost-visual-panel.tsx").read_text(encoding="utf-8")
    chart = (VISUAL_DIR / "holding-cost-breakdown-chart.tsx").read_text(encoding="utf-8")
    for text in ("每月持有成本", "每月總持有成本", "年持有成本", "月收入負擔率", "每年簡化稅費估算", "HoldingCostBreakdownChart"):
        assert text in panel or text in COMPONENT
    assert "DetailDisclosure" in panel
    assert "另有" in chart
    assert "簡化估算" in panel
    assert "正式稅務或財務意見" in panel
    assert "autoCase" not in panel
    assert "setCase" not in panel


def test_holding_invalid_total_does_not_create_fake_percentage() -> None:
    assert "monthly_total_holding_cost ?" not in COMPONENT
    assert "0%" not in COMPONENT
    assert "無法計算占比" in (VISUAL_DIR / "holding-cost-breakdown-chart.tsx").read_text(encoding="utf-8")
    assert "incomeBurden === null ? \"未輸入收入\"" in (VISUAL_DIR / "holding-cost-visual-panel.tsx").read_text(encoding="utf-8")


def test_holding_breakdown_chart_is_accessible_and_mobile_safe() -> None:
    source = (VISUAL_DIR / "holding-cost-breakdown-chart.tsx").read_text(encoding="utf-8")
    assert 'role="img"' in source
    assert "aria-label" in source
    assert "<title>" in source
    assert "<desc>" in source
    assert "h-auto w-full" in source
    assert "max-w-full" in source
    assert "overflow-x-auto" not in source
    assert "min-w-[520px]" not in source
