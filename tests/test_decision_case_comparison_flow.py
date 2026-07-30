"""Static contracts for explicit case comparison in Phase 4."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAGE = (ROOT / "frontend_next/app/page.tsx").read_text(encoding="utf-8")
COMMAND_CENTER = (ROOT / "frontend_next/components/property-case-command-center.tsx").read_text(encoding="utf-8")
CASE_MANAGER = (ROOT / "frontend_next/components/case-manager.tsx").read_text(encoding="utf-8")
WORKBENCH = (ROOT / "frontend_next/components/data-visualization/property-case-comparison-workbench.tsx").read_text(encoding="utf-8")


def test_embedded_command_center_hides_duplicate_comparison_by_default() -> None:
    assert 'showComparison={false}' in PAGE
    assert "showComparison = true" in COMMAND_CENTER
    assert "{showComparison && <PropertyCaseComparisonWorkbench />" in COMMAND_CENTER


def test_saved_cases_require_explicit_selection_and_keep_two_to_three_limit() -> None:
    assert "selectedIds.length < 2" in CASE_MANAGER
    assert "rows.length >= 3" in CASE_MANAGER or "length >= 3" in CASE_MANAGER
    assert 'copy("case.compareCount"' in CASE_MANAGER
    assert "checked={selected}" in CASE_MANAGER
    assert "PropertyCaseComparisonWorkbench" in WORKBENCH

def test_comparison_has_no_ranking_or_purchase_decision_language() -> None:
    source = "\n".join((CASE_MANAGER, WORKBENCH, (ROOT / "frontend_next/lib/property-case-comparison.ts").read_text(encoding="utf-8")))
    for forbidden in ("winner", "第一名", "最佳案件", "推薦購買"):
        assert forbidden not in source.lower()
