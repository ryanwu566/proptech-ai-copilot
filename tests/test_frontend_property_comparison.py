"""Static contracts for property comparison report UI."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CASE_COMPARISON = (ROOT / "frontend_next" / "lib" / "case-comparison.ts").read_text(encoding="utf-8")
PROPERTY_COMPARISON = (ROOT / "frontend_next" / "lib" / "property-comparison.ts").read_text(encoding="utf-8")
CASE_MANAGER = (ROOT / "frontend_next" / "components" / "case-manager.tsx").read_text(encoding="utf-8")
PANEL = (ROOT / "frontend_next" / "components" / "case-comparison-panel.tsx").read_text(encoding="utf-8")
REPORT = (ROOT / "frontend_next" / "components" / "property-comparison-report.tsx").read_text(encoding="utf-8")
PRINT_REPORT = (ROOT / "frontend_next" / "components" / "print-comparison-report.tsx").read_text(encoding="utf-8")
VIEWING_DECISION = (ROOT / "frontend_next" / "components" / "viewing-decision-panel.tsx").read_text(encoding="utf-8")
TERRAIN_RISK = (ROOT / "frontend_next" / "components" / "terrain-risk-analysis.tsx").read_text(encoding="utf-8")


def test_comparison_case_limit_is_two_to_three() -> None:
    assert "PROPERTY_COMPARISON_MIN_CASES = 2" in PROPERTY_COMPARISON
    assert "PROPERTY_COMPARISON_MAX_CASES = 3" in PROPERTY_COMPARISON
    assert "savedCases.slice(0, 3)" in CASE_COMPARISON
    assert "rows.length >= 3" in CASE_MANAGER
    assert "selectedIds.includes(item.id)).slice(0, 3)" in PANEL


def test_report_is_built_from_existing_comparison_result_only() -> None:
    assert "buildPropertyComparisonReport" in PROPERTY_COMPARISON
    assert "CaseComparisonResult" in PROPERTY_COMPARISON
    assert "PropertyComparisonReport" in PANEL
    for source in (PROPERTY_COMPARISON, REPORT, PRINT_REPORT):
      assert "api." not in source
      assert "fetch(" not in source


def test_report_export_uses_browser_print_not_new_pdf_api() -> None:
    assert "window.print()" in PRINT_REPORT
    assert "列印／另存 PDF" in PRINT_REPORT
    assert "new Blob" not in PRINT_REPORT
    assert "download" not in PRINT_REPORT


def test_report_has_conservative_limitations_and_missing_data_language() -> None:
    assert "資料不足或暫時不可用不代表沒有風險" in PROPERTY_COMPARISON
    assert "購買建議" in PROPERTY_COMPARISON
    assert "法律意見" in PROPERTY_COMPARISON
    assert "貸款承諾" in PROPERTY_COMPARISON
    assert "稅務申報建議" in PROPERTY_COMPARISON
    assert "地勢或災害資料不足" in PROPERTY_COMPARISON


def test_report_does_not_add_browser_persistence_or_raw_fields() -> None:
    combined = PROPERTY_COMPARISON + REPORT + PRINT_REPORT
    for forbidden in ("localStorage", "sessionStorage", "document.cookie", "location.search", "location.hash"):
        assert forbidden not in combined
    for forbidden in ("provider raw", "raw payload", "token", "secret", "StationUID", "raw error"):
        assert forbidden not in PRINT_REPORT


def test_viewing_decision_and_terrain_components_are_not_rewired() -> None:
    assert "PropertyComparisonReport" not in VIEWING_DECISION
    assert "buildPropertyComparisonReport" not in VIEWING_DECISION
    assert "PropertyComparisonReport" not in TERRAIN_RISK
