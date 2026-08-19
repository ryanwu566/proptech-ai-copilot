"""Static contracts for the user-task-oriented homepage."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HERO = (ROOT / "frontend_next" / "components" / "hero-intro.tsx").read_text(encoding="utf-8")
ENTRIES = (ROOT / "frontend_next" / "components" / "workflow-entry-cards.tsx").read_text(encoding="utf-8")
PAGE = (ROOT / "frontend_next" / "app" / "page.tsx").read_text(encoding="utf-8")
RUNTIME_COPY = (ROOT / "frontend_next" / "lib" / "runtime-copy.ts").read_text(encoding="utf-8")


def test_home_explains_the_problem_and_final_outcome() -> None:
    for key in ("hero.title", "hero.description", "hero.primary", "hero.report"):
        assert f't("{key}")' in HERO
    assert "outcomeCards" in HERO


def test_primary_entries_are_user_tasks_with_real_handlers() -> None:
    for key in ("workflow.entryBuyingTitle", "workflow.entryDemoTitle", "workflow.entryCompareTitle"):
        assert f'copy("{key}")' in ENTRIES
    for handler in ("onStartBuying", "onGuidedDemo", "onOpenCompare"):
        assert handler in ENTRIES
        assert handler in PAGE
    assert 'id="recent-cases"' in PAGE
    assert "openCaseComparison" in PAGE


def test_tax_and_advanced_tools_are_secondary_but_retained() -> None:
    assert 'copy("workflow.entryTaxButton")' in ENTRIES or "我要做稅務快篩" in ENTRIES
    assert 'copy("workflow.entryAdvancedButton")' in ENTRIES or "我要看更多工具" in ENTRIES
    assert 'id="advanced-tools"' in PAGE
    assert "Map Insight / GeoMap" in RUNTIME_COPY or "Map Insight / GeoMap" in PAGE
    assert "TaxOracle" in PAGE
