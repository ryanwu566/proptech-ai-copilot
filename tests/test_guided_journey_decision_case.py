"""Static contracts for the Guided Journey Decision Case Stage."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAGE = (ROOT / "frontend_next/app/page.tsx").read_text(encoding="utf-8")
STAGE = (ROOT / "frontend_next/components/guided-journey/decision-case-stage.tsx").read_text(encoding="utf-8")
CONTEXT = (ROOT / "frontend_next/components/guided-journey/journey-decision-context-header.tsx").read_text(encoding="utf-8")
ATTENTION = (ROOT / "frontend_next/components/guided-journey/decision-attention-panel.tsx").read_text(encoding="utf-8")


def test_step_five_is_a_decision_case_stage_not_three_entry_cards() -> None:
    assert "<DecisionCaseStage" in PAGE
    decision_section = PAGE.split("<DecisionCaseStage", 1)[1].split("const handleTourAction", 1)[0]
    assert "<JourneyToolCard" not in decision_section
    assert 't("journey.decision.question")' in STAGE
    assert 't("journey.decision.description")' in STAGE


def test_decision_stage_orders_context_status_readiness_and_attention() -> None:
    order = [
        "JourneyDecisionContextHeader",
        "DecisionCaseStatusStrip",
        "DecisionReadinessSummary",
        "DecisionAttentionPanel",
        "DecisionCaseActionSelector",
    ]
    render_body = STAGE.split("return <div", 1)[1]
    positions = [render_body.index(name) for name in order]
    assert positions == sorted(positions)
    assert "ATTENTION FIRST" in ATTENTION
    assert "前往處理" in ATTENTION


def test_case_creation_and_saved_case_opening_are_explicit() -> None:
    assert 'activeAction === "new"' in STAGE
    assert 'activeAction === "saved"' in STAGE
    assert "不會自動建立或選取案件" in (ROOT / "frontend_next/components/guided-journey/decision-case-action-selector.tsx").read_text(encoding="utf-8")
    assert 'renderSavedCases={() => <CaseManager listOnly />}' in PAGE
    assert 'renderCommandCenter={() => <PropertyCaseCommandCenter embedded' in PAGE
