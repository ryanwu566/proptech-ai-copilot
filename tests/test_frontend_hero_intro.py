"""Static contracts for the lightweight user-oriented landing hero."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HERO = (ROOT / "frontend_next" / "components" / "hero-intro.tsx").read_text(encoding="utf-8")
PAGE = (ROOT / "frontend_next" / "app" / "page.tsx").read_text(encoding="utf-8")
CSS = (ROOT / "frontend_next" / "app" / "globals.css").read_text(encoding="utf-8")
WALKTHROUGH = (ROOT / "frontend_next" / "components" / "friendly-intro-walkthrough.tsx").read_text(encoding="utf-8")


def test_hero_intro_explains_the_buying_decision_task() -> None:
    assert "HeroIntro" in HERO
    assert "不知道這間房值不值得看？先跑一份看屋決策報告。" in HERO
    assert "輸入預算、地點或路段" in HERO
    for stage in ("輸入條件", "系統分析", "產出報告"):
        assert stage in HERO
    for capability in ("合理價格", "月付", "持有成本", "區位", "風險"):
        assert capability in HERO or capability in WALKTHROUGH


def test_hero_ctas_keep_real_navigation_handlers() -> None:
    for handler in ("onStart", "onWorkspace", "onReport"):
        assert f"onClick={{{handler}}}" in HERO
    assert "continueWorkflow" in PAGE
    assert "workflowStatus.nextActionTargetId" in PAGE
    assert 'openViewingFlow("immersive-workspace")' in PAGE
    assert 'openViewingFlow("decision-report")' in PAGE
    assert "disabled={!reportReady}" in HERO


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
    for scene in ("先告訴我你想看哪裡、預算多少", "用實價登錄幫你找可負擔路段", "看價格、月付和持有成本", "檢查附近生活機能與區位", "紅黃綠燈號和看屋報告"):
        assert scene in WALKTHROUGH
    assert "略過介紹" in WALKTHROUGH
    assert "重新播放介紹" in WALKTHROUGH
    assert "prefers-reduced-motion: reduce" in WALKTHROUGH
    assert "if (!playing || reducedMotion) return" in WALKTHROUGH
