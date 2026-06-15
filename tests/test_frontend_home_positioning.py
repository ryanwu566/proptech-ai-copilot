"""Static contracts for the user-task-oriented homepage."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HERO = (ROOT / "frontend_next" / "components" / "hero-intro.tsx").read_text(encoding="utf-8")
ENTRIES = (ROOT / "frontend_next" / "components" / "workflow-entry-cards.tsx").read_text(encoding="utf-8")
PAGE = (ROOT / "frontend_next" / "app" / "page.tsx").read_text(encoding="utf-8")


def test_home_explains_the_problem_and_final_outcome() -> None:
    assert "不知道這間房值不值得看？先跑一份看屋決策報告。" in HERO
    assert "幫你判斷要不要進一步看屋" in HERO
    for outcome in ("合理價格", "月付壓力", "區位優缺點", "紅黃綠風險燈號", "HTML 報告"):
        assert outcome in HERO


def test_primary_entries_are_user_tasks_with_real_handlers() -> None:
    for task in ("我想判斷一間房值不值得看", "我想快速看一次示範", "我想比較幾個候選物件"):
        assert task in ENTRIES
    for handler in ("onStartBuying", "onGuidedDemo", "onOpenCompare"):
        assert handler in ENTRIES
        assert handler in PAGE
    assert 'id="recent-cases"' in PAGE
    assert "openCaseComparison" in PAGE


def test_tax_and_advanced_tools_are_secondary_but_retained() -> None:
    assert "我要做稅務快篩" in ENTRIES
    assert "我要看更多工具" in ENTRIES
    assert 'id="advanced-tools"' in PAGE
    assert "Map Insight / GeoMap" in PAGE
    assert "TaxOracle" in PAGE
