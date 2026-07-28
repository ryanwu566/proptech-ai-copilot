"""Accessibility and responsive contracts for the Phase 4 decision stage."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STAGE_DIR = ROOT / "frontend_next/components/guided-journey"


def read(name: str) -> str:
    return (STAGE_DIR / name).read_text(encoding="utf-8")


def test_decision_stage_controls_have_native_semantics() -> None:
    stage = read("decision-case-stage.tsx")
    context = read("journey-decision-context-header.tsx")
    action = read("decision-case-action-selector.tsx")
    for source in (stage, context, action):
        assert 'type="button"' in source
        assert "min-w-0" in source
        assert "focus" in source or "aria" in source
    assert 'aria-label="案件流程返回"' in stage
    assert "aria-labelledby" in context
    assert "aria-pressed" in action


def test_attention_and_saved_case_sections_are_textual_and_mobile_safe() -> None:
    attention = read("decision-attention-panel.tsx")
    stage = read("decision-case-stage.tsx")
    saved = (ROOT / "frontend_next/components/case-manager.tsx").read_text(encoding="utf-8")
    assert "DecisionAttentionCategory" in attention or "attentionCategoryLabel" in attention
    assert "blocked" in attention
    assert "missing" in attention
    assert "unknown" in attention
    assert "grid gap-2 md:grid-cols-2" in attention
    assert "aria-label={\"選擇比較 \" + saved.title}" in saved
    assert "disabled" in stage
