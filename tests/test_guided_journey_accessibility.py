"""Accessibility and responsive contracts for the journey shell."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
JOURNEY_DIR = ROOT / "frontend_next/components/guided-journey"


def read(name: str) -> str:
    return (JOURNEY_DIR / name).read_text(encoding="utf-8")


def test_journey_navigation_has_native_step_semantics() -> None:
    stepper = read("journey-stepper.tsx")
    stage = read("journey-stage.tsx")
    navigation = read("journey-navigation.tsx")
    assert '<nav aria-label="購屋判斷流程"' in stepper
    assert 'aria-current={active ? "step" : undefined}' in stepper
    assert 'type="button"' in stepper
    assert 'type="button"' in navigation
    assert 'aria-labelledby={headingId}' in stage
    assert 'className="cursor-pointer' in stepper


def test_mobile_steps_use_collapsed_native_disclosure() -> None:
    stepper = read("journey-stepper.tsx")
    assert "<details" in stepper
    assert "<summary" in stepper
    assert "查看全部步驟" in stepper
    assert "space-y-2" in stepper
    assert "overflow-x-auto" not in stepper
    assert "min-w-[" not in stepper


def test_hidden_stages_and_controls_keep_visible_focus() -> None:
    stage = read("journey-stage.tsx")
    navigation = read("journey-navigation.tsx")
    tools = read("journey-tool-card.tsx")
    assert "hidden={!active}" in stage
    assert "aria-hidden={!active}" in stage
    for source in (navigation, tools):
        assert "focus:ring-2" in source
        assert 'type="button"' in source
    combined = "\n".join((read(name) for name in (
        "guided-property-journey.tsx",
        "journey-stepper.tsx",
        "journey-stage.tsx",
        "journey-navigation.tsx",
        "journey-tool-card.tsx",
    )))
    assert "autoFocus" not in combined
    assert "keyboard trap" not in combined.lower()
    assert "hover-only" not in combined.lower()


def test_desktop_rail_is_bounded_and_progress_is_not_completion() -> None:
    shell = read("guided-property-journey.tsx")
    progress = read("journey-progress-summary.tsx")
    assert "lg:grid-cols-[240px_minmax(0,1fr)]" in shell
    assert "lg:sticky" in shell
    assert "流程瀏覽進度" in progress
    assert "已瀏覽" in progress
    assert "瀏覽進度不代表資料完整度或決策完成度" in progress
    assert "已完成" not in progress
