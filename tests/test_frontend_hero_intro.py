"""Static contracts for the lightweight user-oriented landing hero."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HERO = (ROOT / "frontend_next" / "components" / "hero-intro.tsx").read_text(encoding="utf-8")
PAGE = (ROOT / "frontend_next" / "app" / "page.tsx").read_text(encoding="utf-8")
CSS = (ROOT / "frontend_next" / "app" / "globals.css").read_text(encoding="utf-8")


def test_hero_intro_explains_the_buying_decision_task() -> None:
    assert "HeroIntro" in HERO
    assert "不知道這間房值不值得看？先跑一份看屋決策報告。" in HERO
    assert "輸入預算、地點或路段" in HERO
    for stage in ("輸入條件", "系統分析", "產出報告"):
        assert stage in HERO
    for capability in ("合理價格區間", "每月要繳多少", "房貸之外還要花多少", "附近生活機能", "值不值得繼續看"):
        assert capability in HERO


def test_hero_ctas_keep_real_navigation_handlers() -> None:
    for handler in ("onStart", "onWorkspace", "onReport"):
        assert f"onClick={{{handler}}}" in HERO
    assert "continueWorkflow" in PAGE
    assert "workflowStatus.nextActionTargetId" in PAGE
    assert 'openViewingFlow("immersive-workspace")' in PAGE
    assert 'openViewingFlow("decision-report")' in PAGE
    assert "disabled={!reportReady}" in HERO


def test_hero_animation_is_local_and_reduced_motion_safe() -> None:
    for animation in ("hero-reveal", "hero-sequence", "hero-flow-line", "hero-orb"):
        assert animation in HERO
        assert animation in CSS
    assert "@media (prefers-reduced-motion: reduce)" in CSS
    assert "motion-reduce:animate-none" in HERO
    lowered = HERO.lower()
    assert all(term not in lowered for term in ("http://", "https://", "<img", "minion", "小黃人"))
