"""Static contracts for the site-wide derived workflow experience."""

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STATUS = (ROOT / "frontend_next" / "lib" / "workflow-status.ts").read_text(encoding="utf-8")
CENTER = (ROOT / "frontend_next" / "components" / "workflow-command-center.tsx").read_text(encoding="utf-8")
WIZARD = (ROOT / "frontend_next" / "components" / "buying-wizard.tsx").read_text(encoding="utf-8")
WORKSPACE = (ROOT / "frontend_next" / "components" / "immersive-viewing-workspace.tsx").read_text(encoding="utf-8")
PAGE = (ROOT / "frontend_next" / "app" / "page.tsx").read_text(encoding="utf-8")
SHARE = (ROOT / "frontend_next" / "lib" / "valuation-share.ts").read_text(encoding="utf-8")
RUNTIME_COPY = (ROOT / "frontend_next" / "lib" / "runtime-copy.ts").read_text(encoding="utf-8")

STEP_IDS = ("property_search", "valuation", "affordability", "location", "risk", "report", "tax")


def test_workflow_status_derives_seven_step_progress_without_api_calls() -> None:
    # Workflow status type has all required semantic fields
    for field in ("currentStep", "completedSteps", "nextStep", "nextActionLabel", "nextActionTargetId", "missingItems", "overallProgress"):
        assert field in STATUS

    # (a) All 7 step IDs are defined in workflow-status.ts
    for step_id in STEP_IDS:
        assert f'"{step_id}"' in STATUS, f"Step ID {step_id} missing from workflow-status.ts"

    # (b) Each step has a targetId defined in WORKFLOW_STEPS
    assert "targetId" in STATUS
    # Verify each step definition includes a targetId string value
    target_count = STATUS.count("targetId:")
    assert target_count >= 7, f"Expected at least 7 targetId definitions, found {target_count}"

    # (c) No hardcoded Chinese display strings in business logic
    # The file should use semantic actionKey references, not inline Chinese labels
    assert "actionKey" in STATUS
    # Verify it references localization keys like wizardStep.* rather than Chinese strings
    assert "wizardStep." in STATUS
    # Confirm the old hardcoded Chinese step names are NOT in the file
    for old_chinese in ("找房雷達", "估價與趨勢", "貸款與持有成本", "區位分析", "風險總評", "看屋決策報告", "TaxOracle 稅務快篩"):
        assert old_chinese not in STATUS, f"Hardcoded Chinese '{old_chinese}' should not be in workflow-status.ts business logic"

    # No API calls in the status derivation logic
    assert "api." not in STATUS

    # Verify all 4 locales have non-empty copy for wizard step labels
    for step_id in STEP_IDS:
        parts = step_id.split("_")
        camel = parts[0] + "".join(p.capitalize() for p in parts[1:])
        key = f"wizardStep.{camel}"
        occurrences = RUNTIME_COPY.count(f'"{key}"')
        assert occurrences >= 4, f"Locale key {key} must appear in all 4 locales (found {occurrences})"


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
    assert "buildValuationShareUrl" in SHARE

def test_workspace_reduces_duplicate_information() -> None:
    assert "<details" in WORKSPACE
    assert "GuidedDemoRunner" in WORKSPACE
    assert "CaseManager" in WORKSPACE
    assert "WorkflowCommandCenter" in WORKSPACE
