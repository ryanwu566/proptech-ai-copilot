"""Privacy and runtime-only contracts for Phase 4 decision state."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HELPER = (ROOT / "frontend_next/lib/decision-case-journey.ts").read_text(encoding="utf-8")
STAGE = (ROOT / "frontend_next/components/guided-journey/decision-case-stage.tsx").read_text(encoding="utf-8")
CONTEXT = (ROOT / "frontend_next/components/guided-journey/journey-decision-context-header.tsx").read_text(encoding="utf-8")
PAGE = (ROOT / "frontend_next/app/page.tsx").read_text(encoding="utf-8")


def test_decision_context_is_presentation_only() -> None:
    assert "JourneyDecisionContext" in HELPER
    assert "raw case" not in HELPER.lower()
    for forbidden in ("fetch(", "api.", "localStorage", "sessionStorage", "document.cookie", "URLSearchParams", "coordinates", "latitude", "longitude", "sql", "token", "credential", "exception"):
        assert forbidden not in HELPER.lower()
    assert "selectedSavedCaseIds" in HELPER
    assert "missingDataLabels" in HELPER


def test_decision_selection_is_not_persisted_or_automatically_created() -> None:
    for source in (STAGE, CONTEXT):
        for forbidden in ("localStorage", "sessionStorage", "URLSearchParams", "saveCase(", "writeCases(", "window.location.search"):
            assert forbidden not in source
    decision_section = PAGE.split("<DecisionCaseStage", 1)[1].split("const handleTourAction", 1)[0]
    assert "renderCommandCenter" in decision_section
    assert "renderSavedCases" in decision_section
