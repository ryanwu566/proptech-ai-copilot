"""Static contracts for the viewing decision report v2."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT = (ROOT / "frontend_next" / "components" / "decision-report.tsx").read_text(encoding="utf-8")
SUMMARY = (ROOT / "frontend_next" / "lib" / "decision-summary.ts").read_text(encoding="utf-8")
HTML = (ROOT / "frontend_next" / "lib" / "valuation-share.ts").read_text(encoding="utf-8")


def test_decision_report_uses_rule_based_summary_and_checklist() -> None:
    assert "buildDecisionSummary" in REPORT
    for text in ("看屋決策摘要", "RULE-BASED DECISION SUMMARY", "主要理由", "主要風險", "資料信心", "決策 checklist"):
        assert text in REPORT
    for text in ("值得進一步看屋", "需謹慎評估", "暫不建議", "價格是否合理", "月付是否可承受", "持有成本是否可承受", "區位是否符合需求", "是否建議實地看屋"):
        assert text in SUMMARY
    assert "riskSummary" in REPORT
    assert "風險總評" in REPORT


def test_html_is_upgraded_to_viewing_decision_report_v2() -> None:
    for text in ("看屋決策報告 v2", "快速結論", "主要理由", "主要風險", "資料信心", "決策 checklist", "年持有成本", "市場趨勢摘要", "風險總評 / 開價合理性", "補查清單"):
        assert text in HTML
    for text in ("不代表銀行核貸", "不代表正式鑑價", "不代表正式稅務申報", "不代表即時待售物件", "實地確認"):
        assert text in HTML
