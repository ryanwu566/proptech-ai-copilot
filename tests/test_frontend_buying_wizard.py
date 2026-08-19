"""Static contracts for the guided buying wizard UX."""

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAGE = (ROOT / "frontend_next" / "app" / "page.tsx").read_text(encoding="utf-8")
ENTRIES = (ROOT / "frontend_next" / "components" / "workflow-entry-cards.tsx").read_text(encoding="utf-8")
WIZARD = (ROOT / "frontend_next" / "components" / "buying-wizard.tsx").read_text(encoding="utf-8")
STATUS = (ROOT / "frontend_next" / "lib" / "buying-wizard-status.ts").read_text(encoding="utf-8")
WORKFLOW = (ROOT / "frontend_next" / "lib" / "workflow-status.ts").read_text(encoding="utf-8")
WORKSPACE = (ROOT / "frontend_next" / "components" / "immersive-viewing-workspace.tsx").read_text(encoding="utf-8")
DEMO = (ROOT / "frontend_next" / "components" / "guided-demo-runner.tsx").read_text(encoding="utf-8")
RUNTIME_COPY = (ROOT / "frontend_next" / "lib" / "runtime-copy.ts").read_text(encoding="utf-8")

STEP_IDS = ("property_search", "valuation", "affordability", "location", "risk", "report", "tax")


def test_home_has_three_task_oriented_entry_cards() -> None:
    for key in ("workflow.entryBuyingTitle", "workflow.entryDemoTitle", "workflow.entryCompareTitle"):
        assert f'copy("{key}")' in ENTRIES
    for handler in ("onStartBuying", "onGuidedDemo", "onOpenCompare", "onOpenTax", "onOpenAdvanced"):
        assert handler in ENTRIES
        assert handler in PAGE
    assert 'id="advanced-tools"' in PAGE


def test_buying_wizard_has_seven_plain_language_steps() -> None:
    # (a) All 7 step IDs are defined in workflow-status.ts which is the source of truth
    for step_id in STEP_IDS:
        assert f'"{step_id}"' in WORKFLOW, f"Step ID {step_id} missing from workflow-status.ts"

    # (b) Buying wizard component uses localized step label/title/guide functions
    assert "localizeWizardStepLabel" in WIZARD
    assert "localizeWizardStepTitle" in WIZARD
    assert "localizeWizardStepGuide" in WIZARD

    # (c) runtime-copy.ts has wizardStep.* keys for all 7 steps in all 4 locales
    for step_id in STEP_IDS:
        # Convert step_id (snake_case) to camelCase key suffix
        parts = step_id.split("_")
        camel = parts[0] + "".join(p.capitalize() for p in parts[1:])
        base_key = f"wizardStep.{camel}"
        title_key = f"wizardStep.{camel}Title"
        guide_key = f"wizardStep.{camel}Guide"
        for key in (base_key, title_key, guide_key):
            # Must appear at least 4 times (once per locale dictionary)
            occurrences = RUNTIME_COPY.count(f'"{key}"')
            assert occurrences >= 4, f"Key {key} appears only {occurrences} times, expected at least 4 (one per locale)"

    # Verify wizard still uses disabled={!enabled} for step progression
    assert "disabled={!enabled}" in WIZARD
    # Verify wizard uses copy() for intro text (not hardcoded Chinese)
    assert 'wizard.introNote' in WIZARD


def test_completed_steps_and_advanced_tools_are_retained() -> None:
    assert "summaries" in WIZARD
    assert "isWizardStepCompleted" in WIZARD
    assert "wizardSummaries" in WORKSPACE
    assert "Map Insight / GeoMap" in PAGE or 'copy("dashboard.mapModule")' in PAGE
    assert 'setPage("Map Insight Lite")' in PAGE
    assert "GuidedDemoRunner" in WORKSPACE
    assert "一鍵 Demo 流程" in DEMO
