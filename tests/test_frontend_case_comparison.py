"""Static contracts for saved-case comparison and candidate ranking."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMPARISON = (ROOT / "frontend_next" / "lib" / "case-comparison.ts").read_text(encoding="utf-8")
PANEL = (ROOT / "frontend_next" / "components" / "case-comparison-panel.tsx").read_text(encoding="utf-8")
MANAGER = (ROOT / "frontend_next" / "components" / "case-manager.tsx").read_text(encoding="utf-8")


def test_case_comparison_is_rule_based_and_uses_saved_data_only() -> None:
    assert "compareSavedCases" in COMPARISON
    assert "savedCases.slice(0, 3)" in COMPARISON
    assert "selected.length < 2" in COMPARISON
    for weight in ("0.30", "0.25", "0.20", "0.15", "0.10"):
        assert weight in COMPARISON
    assert "completionRate" in COMPARISON
    assert "api." not in COMPARISON


def test_comparison_includes_expected_fields_and_missing_data_warnings() -> None:
    for field in ("valuationMid", "monthlyPayment", "monthlyHoldingCost", "locationScore", "riskSignal", "taxStatus"):
        assert field in COMPARISON
    assert "missingDataWarnings" in COMPARISON
    for key in ("case.missing", "common.dataLimit", "valuation.level", "location.risk"):
        assert f'copy("{key}"' in PANEL or f'copy("{key}"' in COMPARISON

def test_comparison_panel_has_ranking_table_and_html_export() -> None:
    for key in ("case.compare", "case.export", "case.status", "valuation.comparables", "location.risk"):
        assert f'copy("{key}"' in PANEL
    assert "buildCaseComparisonHtml" in PANEL
    assert "overflow-x-auto" in PANEL
    assert "min-w-[920px]" in PANEL
    assert "terrainRiskLevel" in PANEL
    assert "terrainRiskStatus" in PANEL

def test_case_manager_supports_two_to_three_case_selection() -> None:
    assert "CaseComparisonPanel" in MANAGER
    for key in ("case.compare", "case.compareCount", "case.missing"):
        assert f'copy("{key}"' in MANAGER
    assert 'type="checkbox"' in MANAGER
    assert "rows.length >= 3" in MANAGER
