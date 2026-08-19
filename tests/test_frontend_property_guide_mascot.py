"""Static contracts for the original yellow viewing assistant."""

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MASCOT = (ROOT / "frontend_next" / "components" / "property-guide-mascot.tsx").read_text(encoding="utf-8")
WORKSPACE = (ROOT / "frontend_next" / "components" / "immersive-viewing-workspace.tsx").read_text(encoding="utf-8")
WIZARD_STATUS = (ROOT / "frontend_next" / "lib" / "buying-wizard-status.ts").read_text(encoding="utf-8")
WORKFLOW_STATUS = (ROOT / "frontend_next" / "lib" / "workflow-status.ts").read_text(encoding="utf-8")
GUIDED_DEMO = (ROOT / "frontend_next" / "components" / "guided-demo-runner.tsx").read_text(encoding="utf-8")
RUNTIME_COPY = (ROOT / "frontend_next" / "lib" / "runtime-copy.ts").read_text(encoding="utf-8")


def test_original_yellow_assistant_is_present_and_uses_plain_language() -> None:
    # Mascot component is rendered in the workspace
    assert "PropertyGuideMascot" in WORKSPACE

    # (a) Mascot uses copy() for display strings instead of hardcoded Chinese
    assert "copy(" in MASCOT, "Mascot must use copy() for localized strings"
    # Uses mascot.name key for the assistant's displayed name
    assert 'copy("mascot.name")' in MASCOT
    # Uses copy("intro.scene1") for the start/welcome message
    assert 'copy("intro.scene1")' in MASCOT
    # Uses localizeWizardStepGuide for step-specific guidance messages
    assert "localizeWizardStepGuide" in MASCOT

    # (b) Workflow-status uses semantic step IDs, not hardcoded Chinese display strings
    # The 7 steps are defined by id (semantic), not by Chinese display name
    for step_id in ("property_search", "valuation", "affordability", "location", "risk", "report", "tax"):
        assert f'id: "{step_id}"' in WORKFLOW_STATUS
    # Workflow-status uses actionKey references to localization keys, not raw Chinese
    assert "actionKey" in WORKFLOW_STATUS
    assert "wizardStep." in WORKFLOW_STATUS

    # (c) All four locales have non-empty wizardStep Guide keys used by mascot
    guide_keys = [
        "wizardStep.propertySearchGuide", "wizardStep.valuationGuide",
        "wizardStep.affordabilityGuide", "wizardStep.locationGuide",
        "wizardStep.riskGuide", "wizardStep.reportGuide", "wizardStep.taxGuide",
    ]
    for key in guide_keys:
        occurrences = RUNTIME_COPY.count(f'"{key}"')
        assert occurrences >= 4, f"Guide key {key} not present in all 4 locales (found {occurrences})"

    # Mascot still has accessibility role and case message support
    assert 'role="status"' in MASCOT
    assert "caseMessage" in MASCOT


def test_assistant_receives_guided_demo_messages() -> None:
    for message in ("先確認後端服務是否醒著", "Demo 正在跑", "目前卡在這一步", "Demo 已完成"):
        assert message in GUIDED_DEMO
    assert "onMessage={setCaseMessage}" in WORKSPACE


def test_assistant_uses_only_local_css_shapes() -> None:
    lowered = MASCOT.lower()
    assert all(term not in lowered for term in ("minion", "小黃人", "http://", "https://", "<img"))
    assert "bg-yellow-300" in MASCOT
