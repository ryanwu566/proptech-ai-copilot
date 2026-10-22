"""Static contracts for the lightweight user-oriented landing hero."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HERO = (ROOT / "frontend_next" / "components" / "hero-intro.tsx").read_text(encoding="utf-8")
PAGE = (ROOT / "frontend_next" / "app" / "page.tsx").read_text(encoding="utf-8")
HOME = (ROOT / "frontend_next" / "components" / "commercial-home.tsx").read_text(encoding="utf-8")
CSS = (ROOT / "frontend_next" / "app" / "home.css").read_text(encoding="utf-8")
WALKTHROUGH = (ROOT / "frontend_next" / "components" / "friendly-intro-walkthrough.tsx").read_text(encoding="utf-8")


def test_hero_intro_explains_the_buying_decision_task() -> None:
    assert "HeroIntro" in HERO
    for key in ("hero.title", "hero.description", "hero.primary", "hero.secondaryCta", "hero.capabilityLabel", "hero.disclaimer"):
        assert f't("{key}")' in HERO
    assert "capabilities" in HERO
    assert "trustItems" in HERO
    assert "FriendlyIntroWalkthrough" in HERO


def test_hero_ctas_keep_real_navigation_handlers() -> None:
    for handler in ("onStart", "onWorkspace"):
        assert f"onClick={{{handler}}}" in HERO
    assert "onReport" in HERO
    assert "continueWorkflow" in PAGE
    assert "workflowStatus.nextActionTargetId" in PAGE
    assert 'openViewingFlow("immersive-workspace")' in PAGE
    assert 'openViewingFlow("decision-report")' in PAGE
    assert 'data-action-kind="primary"' in HERO
    assert 'data-action-kind="secondary"' in HERO
    active_home = PAGE.split("export default function Home()", 1)[1].split("function buildJourneySaveCase", 1)[0]
    # Home address Start opens the modern case workspace; only the finder opens the legacy journey.
    assert '<CommercialHome onFinder={() => openJourneyStep("property")} />' in active_home
    assert "onStart" not in active_home.split("<CommercialHome", 1)[1].split("/>", 1)[0]
    assert "createClosedLoopJourneyState({ addressSummary: address" not in active_home
    assert "export function CommercialHome({ onFinder }: { onFinder: () => void })" in HOME
    assert "onStart=" not in HOME
    assert "openJourneyStep" not in HOME
    start = HOME.split("async function start(", 1)[1].split("const recent", 1)[0]
    assert "createAddressDraftCase(address)" in start
    assert 'router.push(caseDestination(result.caseId, "location"))' in start
    assert "useRouter()" in HOME
    assert 'from "next/navigation"' in HOME
    # The explicit Start owns one location lookup for a newly created case, never automatic analysis.
    assert 'result.status === "created" && query' in start
    assert "locationStartHandoff.begin" in start
    assert start.count("api.locationResolve(") == 1
    assert all(term not in start for term in ("fetch(", "locationInsight", "mapNearby", "commuteRoute", "terrainRisk", "workflow=property"))
    assert 'href={`/cases/${encodeURIComponent(workspace.caseId)}/overview`}' in HOME


def test_active_homepage_renders_one_address_entry_before_the_optional_guided_journey() -> None:
    home = PAGE.split("export default function Home()", 1)[1].split("function renderPage", 1)[0]
    assert home.count("<CommercialHome ") == 1
    assert "<HeroIntro " not in home
    assert home.index("<CommercialHome ") < home.index("<GuidedPropertyJourney ")
    assert "hidden={!journeyOpen}" in home
    assert "<h1" in HOME
    assert "<form onSubmit={start}" in HOME
    assert 'openJourneyStep("property")' in home
    journey = (ROOT / "frontend_next" / "components" / "guided-journey" / "guided-property-journey.tsx").read_text(encoding="utf-8")
    sidebar = (ROOT / "frontend_next" / "components" / "sidebar.tsx").read_text(encoding="utf-8")
    assert "<h1" not in journey
    assert "<h1" not in sidebar


def test_hero_animation_is_local_and_reduced_motion_safe() -> None:
    assert 'import "./home.css";' in PAGE
    for animation in ("hero-reveal", "hero-orb"):
        assert animation in HERO
        assert animation in CSS
    assert "hero-sequence" in WALKTHROUGH
    assert "hero-sequence" in CSS
    assert "@media (prefers-reduced-motion: reduce)" in CSS
    assert "motion-reduce:animate-none" in HERO
    lowered = HERO.lower()
    assert all(term not in lowered for term in ("http://", "https://", "<img", "minion", "小黃人"))


def test_friendly_walkthrough_has_five_scenes_and_controls() -> None:
    assert "FriendlyIntroWalkthrough" in HERO
    for key in ("intro.scene1", "intro.scene2", "intro.scene3", "intro.scene4", "intro.scene5"):
        assert f'copy("{key}")' in WALKTHROUGH
    assert 'copy("intro.skipButton")' in WALKTHROUGH or "略過介紹" in WALKTHROUGH
    assert 'copy("intro.replayButton")' in WALKTHROUGH or "重新播放介紹" in WALKTHROUGH
    assert "prefers-reduced-motion: reduce" in WALKTHROUGH
    assert "if (!playing || reducedMotion) return" in WALKTHROUGH
