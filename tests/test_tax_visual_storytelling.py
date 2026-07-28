from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend_next"
VISUAL_DIR = FRONTEND / "components" / "data-visualization"
HELPER = (FRONTEND / "lib" / "tax-visualization.ts").read_text(encoding="utf-8")
PAGE = (FRONTEND / "app" / "page.tsx").read_text(encoding="utf-8")


def test_tax_model_uses_existing_outcomes_without_reclassification() -> None:
    assert "buildTaxVisualModel" in HELPER
    assert "row.outcome" in HELPER
    assert "risk_points" not in HELPER
    assert "Math.max" not in HELPER
    assert "riskScore: validScore" in HELPER
    assert "unknown" in HELPER
    assert "hard_fail" in HELPER
    assert ".sort(" not in HELPER
    for forbidden in ("fetch(", "localStorage", "sessionStorage", "Date.now", "value || 0", "value ?? 0"):
        assert forbidden not in HELPER


def test_tax_decision_and_rule_visuals_preserve_status_and_safe_conclusions() -> None:
    panel = (VISUAL_DIR / "tax-decision-visual-panel.tsx").read_text(encoding="utf-8")
    gauge = (VISUAL_DIR / "tax-risk-gauge.tsx").read_text(encoding="utf-8")
    chart = (VISUAL_DIR / "tax-rule-outcome-chart.tsx").read_text(encoding="utf-8")
    reminders = (VISUAL_DIR / "tax-reminder-timeline.tsx").read_text(encoding="utf-8")
    for text in ("資格／複核結論", "未通過規則", "需複核規則", "通過規則", "缺少文件", "TaxRuleOutcomeChart", "TaxReminderTimeline"):
        assert text in panel
    assert 'role="img"' in gauge
    assert "aria-label" in gauge
    assert "風險分數目前無法顯示" in gauge
    assert 'role="img"' in chart
    assert "其他／未辨識" in HELPER
    assert "目前沒有回傳補件項目" in reminders
    assert "不得" not in panel
    for forbidden in ("保證可退稅", "法律上一定符合", "一定不能退稅", "零風險"):
        assert forbidden not in panel


def test_tax_rules_reminders_and_report_remain_manual_and_disclosed() -> None:
    section = PAGE.split("function TaxOracle", 1)[1].split("function MapInsight", 1)[0]
    panel = (VISUAL_DIR / "tax-decision-visual-panel.tsx").read_text(encoding="utf-8")
    assert 'api.runTaxOracleCase(taxCase)' in section
    assert "downloadTaxReport" in section
    assert "setTab(\"原因\")" in section
    assert 'title="查看 AI 客戶溝通內容與完整使用限制"' in panel
    assert "reminder_timeline" in HELPER
    assert "case_input.enters_five_year_monitoring" in HELPER
    assert "TX001–TX009" in section
    assert 'open={false}' in section


def test_tax_chart_is_mobile_safe_and_has_non_color_text() -> None:
    for name in ("tax-rule-outcome-chart.tsx", "tax-risk-gauge.tsx"):
        source = (VISUAL_DIR / name).read_text(encoding="utf-8")
        assert "aria-label" in source
        assert "text" in source.lower()
        assert "overflow-x-auto" not in source
        assert "min-w-[520px]" not in source
        assert "min-w-[620px]" not in source
