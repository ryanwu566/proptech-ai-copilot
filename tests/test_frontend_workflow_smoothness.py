"""Static contracts for the site-wide derived workflow experience."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STATUS = (ROOT / "frontend_next" / "lib" / "workflow-status.ts").read_text(encoding="utf-8")
CENTER = (ROOT / "frontend_next" / "components" / "workflow-command-center.tsx").read_text(encoding="utf-8")
WIZARD = (ROOT / "frontend_next" / "components" / "buying-wizard.tsx").read_text(encoding="utf-8")
WORKSPACE = (ROOT / "frontend_next" / "components" / "immersive-viewing-workspace.tsx").read_text(encoding="utf-8")
PAGE = (ROOT / "frontend_next" / "app" / "page.tsx").read_text(encoding="utf-8")
SHARE = (ROOT / "frontend_next" / "lib" / "valuation-share.ts").read_text(encoding="utf-8")


def test_workflow_status_derives_seven_step_progress_without_api_calls() -> None:
    for field in ("currentStep", "completedSteps", "nextStep", "nextActionLabel", "nextActionTargetId", "missingItems", "overallProgress"):
        assert field in STATUS
    for step in ("找房雷達", "估價與趨勢", "貸款與持有成本", "區位分析", "風險總評", "看屋決策報告", "TaxOracle 稅務快篩"):
        assert step in STATUS
    assert "api." not in STATUS


def test_command_center_has_real_next_action_and_progress() -> None:
    assert "BuyingWizard" in CENTER
    assert "status.overallProgress" in WIZARD
    assert "status.nextActionLabel" in WIZARD
    assert "scrollIntoView" in WIZARD
    assert "OPEN_TAXORACLE_EVENT" in WIZARD
    assert "WorkflowCommandCenter" in WORKSPACE


def test_report_and_taxoracle_completion_feed_back_into_workflow() -> None:
    assert "markWorkflowReportCompleted" in WORKSPACE
    assert "markWorkflowReportCompleted" in PAGE
    assert "markTaxOracleCompleted(next)" in PAGE
    assert 'id="taxoracle"' in PAGE
    assert "稅務快篩尚未完成" in SHARE
    assert "TaxOracle 稅務補充檢查" in SHARE


def test_workspace_reduces_duplicate_information() -> None:
    assert "<details" in WORKSPACE
    assert "查看各模組完成摘要" in WORKSPACE
    assert "案件保存 / 最近分析紀錄" in (ROOT / "frontend_next" / "components" / "case-manager.tsx").read_text(encoding="utf-8")
    assert "GuidedDemoRunner" in WORKSPACE
