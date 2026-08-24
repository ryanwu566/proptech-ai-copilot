"""Static contracts for the lightweight user-oriented landing hero."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HERO = (ROOT / "frontend_next" / "components" / "hero-intro.tsx").read_text(encoding="utf-8")
PAGE = (ROOT / "frontend_next" / "app" / "page.tsx").read_text(encoding="utf-8")
CSS = (ROOT / "frontend_next" / "app" / "globals.css").read_text(encoding="utf-8")
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


def test_hero_animation_is_local_and_reduced_motion_safe() -> None:
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
