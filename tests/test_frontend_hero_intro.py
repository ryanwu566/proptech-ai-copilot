"""Static contracts for the lightweight animated landing hero."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HERO = (ROOT / "frontend_next" / "components" / "hero-intro.tsx").read_text(encoding="utf-8")
PAGE = (ROOT / "frontend_next" / "app" / "page.tsx").read_text(encoding="utf-8")
CSS = (ROOT / "frontend_next" / "app" / "globals.css").read_text(encoding="utf-8")


def test_hero_intro_and_product_message_exist() -> None:
    assert "HeroIntro" in HERO
    assert "從找房到決策，一次完成" in HERO
    assert "整合實價登錄、估價、貸款、持有成本、區位與風險燈號" in HERO
    for node in ("找房雷達", "實價估價", "貸款月付", "持有成本", "區位分析", "風險總評", "看屋報告"):
        assert node in HERO


def test_hero_ctas_have_real_navigation_handlers() -> None:
    for handler in ("onStart", "onWorkspace", "onReport"):
        assert f"onClick={{{handler}}}" in HERO
    assert 'openViewingFlow("property-finder")' in PAGE
    assert 'openViewingFlow("immersive-workspace")' in PAGE
    assert 'openViewingFlow("decision-report")' in PAGE
    assert "proptech:pending-section" in PAGE
    assert "scrollIntoView" in PAGE
    assert "disabled={!reportReady}" in HERO


def test_hero_animation_is_local_and_reduced_motion_safe() -> None:
    for animation in ("hero-reveal", "hero-sequence", "hero-flow-line", "hero-orb"):
        assert animation in HERO
        assert animation in CSS
    assert "@media (prefers-reduced-motion: reduce)" in CSS
    assert "motion-reduce:animate-none" in HERO
    lowered = HERO.lower()
    forbidden = ["http" + "://", "https" + "://", "<im" + "g", "min" + "ion", "小" + "黃人"]
    assert all(term not in lowered for term in forbidden)
