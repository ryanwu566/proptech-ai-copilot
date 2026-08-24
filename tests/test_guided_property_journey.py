"""Static contracts for the Guided Property Decision Journey shell."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAGE = (ROOT / "frontend_next/app/page.tsx").read_text(encoding="utf-8")
JOURNEY = (ROOT / "frontend_next/components/guided-journey/guided-property-journey.tsx").read_text(encoding="utf-8")
HELPER = (ROOT / "frontend_next/lib/guided-journey.ts").read_text(encoding="utf-8")


def test_homepage_uses_one_guided_journey_and_starts_at_property() -> None:
    home = PAGE.split("export default function Home()", 1)[1].split("function Dashboard", 1)[0]
    assert "GuidedPropertyJourney" in home
    assert "DecisionWorkspaceSteps" not in home
    assert "WorkflowEntryCards" not in home
    assert 'useState<AppPage>("儀表板")' in home
    assert 'useState<JourneyStepId>("property")' in JOURNEY
    assert 'useState<JourneyStepId[]>(["property"])' in JOURNEY


def test_journey_has_exact_five_steps_in_fixed_order() -> None:
    expected = ["property", "location", "price", "affordability", "decision"]
    positions = [HELPER.index(f'id: "{step}"') for step in expected]
    assert positions == sorted(positions)
    assert HELPER.count('id: "') == 5
    assert "JOURNEY_STEPS.length" in JOURNEY


def test_property_finder_is_the_primary_first_step_entry() -> None:
    property_stage = PAGE.split('if (step === "property")', 1)[1].split('if (step === "location")', 1)[0]
    assert "<PropertyFinder embedded" in property_stage
    assert 'actions.goToTool("location-insight")' in property_stage
    assert 'actions.goToTool("valuation")' in property_stage
    assert 'actions.goToTool("loan")' in property_stage


def test_only_visited_steps_render_and_hidden_steps_are_not_focusable() -> None:
    assert "JOURNEY_STEPS.filter((step) => visitedSteps.includes(step.id))" in JOURNEY
    assert "hidden={!active}" in (ROOT / "frontend_next/components/guided-journey/journey-stage.tsx").read_text(encoding="utf-8")
    assert "aria-hidden={!active}" in (ROOT / "frontend_next/components/guided-journey/journey-stage.tsx").read_text(encoding="utf-8")
    assert "renderTools()" in (ROOT / "frontend_next/components/guided-journey/journey-expert-tools.tsx").read_text(encoding="utf-8")
    assert "{open &&" in (ROOT / "frontend_next/components/guided-journey/journey-expert-tools.tsx").read_text(encoding="utf-8")


def test_navigation_is_runtime_only_and_does_not_run_api_calls() -> None:
    sources = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (ROOT / "frontend_next/components/guided-journey").glob("*.tsx")
    )
    assert "api." not in sources
    assert "fetch(" not in sources
    assert "localStorage" not in sources
    assert "sessionStorage" not in sources
    assert "URLSearchParams" not in sources
