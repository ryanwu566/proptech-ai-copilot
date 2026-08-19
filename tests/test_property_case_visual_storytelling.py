"""Static contracts for the Phase 4 Property Case visual evidence layer."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMMAND = (ROOT / "frontend_next/components/property-case-command-center.tsx").read_text(encoding="utf-8")
HELPER = (ROOT / "frontend_next/lib/property-case-visualization.ts").read_text(encoding="utf-8")
RUNTIME_COPY = (ROOT / "frontend_next/lib/runtime-copy.ts").read_text(encoding="utf-8")
COMPONENTS = "\n".join(
    (ROOT / "frontend_next/components/data-visualization" / name).read_text(encoding="utf-8")
    for name in (
        "property-case-overview.tsx",
        "property-case-completeness-chart.tsx",
        "property-case-financial-comparison.tsx",
        "property-case-due-diligence-matrix.tsx",
        "property-case-viewing-readiness.tsx",
        "property-case-timeline-chart.tsx",
        "property-case-evidence-details.tsx",
        "property-case-missing-data-panel.tsx",
    )
)
# Combined: source components + translation resource for trust boundary checks
ALL_SOURCE = COMPONENTS + "\n" + RUNTIME_COPY


def test_property_case_visual_model_is_pure_and_null_safe() -> None:
    assert "buildPropertyCaseVisualModel" in HELPER
    for forbidden in ("fetch(", "api.", "localStorage", "sessionStorage", "Date.now", "JSON.stringify"):
        assert forbidden not in HELPER


def test_summary_is_before_detail_sections() -> None:
    assert COMMAND.index("<PropertyCaseOverview") < COMMAND.index("WorkspaceSectionPicker")
    assert "PropertyCaseCompletenessChart" in COMMAND
    assert "PropertyCaseMissingDataPanel" in COMMAND
    assert "PropertyCaseEvidenceDetails" in COMMAND


def test_completeness_is_explicit_items_not_a_risk_score() -> None:
    for text in ("completedCount", "totalCount", "completionRatio", "尚無可評估項目"):
        assert text in HELPER
    for forbidden in ("riskScore", "investmentScore", "qualityScore", "安全分數"):
        assert forbidden not in HELPER


def test_all_required_completeness_sections_are_present() -> None:
    for section in ("basic", "financial", "value_tax", "location_market", "due_diligence", "viewing_offer", "decision", "timeline"):
        assert f'"{section}"' in HELPER


def test_unknown_partial_missing_and_blocked_are_visible() -> None:
    for state in ("completed", "partial", "missing", "blocked", "not_assessed"):
        assert state in HELPER or state in COMPONENTS
    # Labels are now stored in runtime-copy.ts via copy() calls; verify keys are referenced
    for key in ("viz.completenessStateMissing", "viz.completenessStateBlocked", "viz.completenessStateNotAssessed", "viz.completenessStatePartial"):
        assert key in COMPONENTS


def test_missing_data_is_not_replaced_with_zero() -> None:
    assert '"未提供"' in ALL_SOURCE or "viz.financialNotProvided" in COMPONENTS
    assert "missingItems" in HELPER
    assert "資料不足不會被填成 0" in ALL_SOURCE or "viz.missingNote" in COMPONENTS


def test_financial_visualization_reuses_existing_analysis_results() -> None:
    assert "financialScenarios" in COMMAND
    assert "PropertyCaseFinancialComparison" in COMMAND
    assert "totalCommitment" in COMPONENTS
    assert "monthlyPayment" in COMPONENTS
    assert "不選出最佳方案" in ALL_SOURCE or "viz.financialDesc" in COMPONENTS


def test_financial_disclosure_is_the_only_table_scroll_region() -> None:
    financial = (ROOT / "frontend_next/components/data-visualization/property-case-financial-comparison.tsx").read_text(encoding="utf-8")
    assert "overflow-x-auto" in financial
    assert "<details" in financial
    assert "min-w-[620px]" in financial


def test_due_diligence_preserves_statuses_and_order() -> None:
    source = (ROOT / "frontend_next/components/data-visualization/property-case-due-diligence-matrix.tsx").read_text(encoding="utf-8")
    assert "groupDueDiligenceItems" in source
    assert "blocked" in source
    assert "not_applicable" in source
    assert "DUE_DILIGENCE_STATUS_LABELS" in source or "getLocalizedStructuredLabel" in source
    assert "查看完整盡職調查項目" in source or "viz.evidenceDetailsTitle" in source


def test_viewing_and_offer_visual_is_reference_only() -> None:
    source = (ROOT / "frontend_next/components/data-visualization/property-case-viewing-readiness.tsx").read_text(encoding="utf-8")
    combined = source + "\n" + RUNTIME_COPY
    for text in ("完成看屋", "待問問題", "出價方案", "不自動產生或選擇出價"):
        assert text in combined or "viz.viewing" in source
    for forbidden in ("best", "recommend", "自動出價"):
        assert forbidden not in source.lower()


def test_timeline_does_not_fabricate_dates() -> None:
    source = (ROOT / "frontend_next/components/data-visualization/property-case-timeline-chart.tsx").read_text(encoding="utf-8")
    combined = source + "\n" + RUNTIME_COPY
    assert "event.event_date" in source or "event_date" in source
    assert "日期未提供" in combined or "viz.timelineDateNotProvided" in source
    assert "Date.now" not in source
    assert ".sort(" not in source


def test_main_visuals_have_text_and_accessibility_labels() -> None:
    chart = (ROOT / "frontend_next/components/data-visualization/property-case-completeness-chart.tsx").read_text(encoding="utf-8")
    timeline = (ROOT / "frontend_next/components/data-visualization/property-case-timeline-chart.tsx").read_text(encoding="utf-8")
    for source in (chart, timeline):
        assert 'role="img"' in source or "aria-label" in source


def test_main_visuals_do_not_require_horizontal_scrolling() -> None:
    for name in ("property-case-completeness-chart.tsx", "property-case-timeline-chart.tsx", "property-case-overview.tsx"):
        source = (ROOT / "frontend_next/components/data-visualization" / name).read_text(encoding="utf-8")
        assert "overflow-x-auto" not in source
        assert "min-w-[" not in source


def test_evidence_disclosure_is_closed_and_allowlisted() -> None:
    source = (ROOT / "frontend_next/components/data-visualization/property-case-evidence-details.tsx").read_text(encoding="utf-8")
    combined = source + "\n" + RUNTIME_COPY
    assert "<details" in source
    assert "<summary" in source
    assert "未整理的內部回應" in combined or "viz.evidenceDetailsBoundary" in source
    for forbidden in ("JSON.stringify", "raw_payload", "provider payload", "SQL", "token", "exception"):
        assert forbidden not in source


def test_command_center_keeps_existing_domain_helpers_and_no_api_calls() -> None:
    for helper in ("buildPropertyCaseDraft", "buildPropertyCaseReadiness", "buildPropertyCaseFinancialAnalysis", "buildDueDiligenceReadiness", "buildViewingOfferReadiness", "buildTimelineReadiness"):
        assert helper in COMMAND
    for forbidden in ("fetch(", "api.", "localStorage", "sessionStorage", "URLSearchParams", "location.hash"):
        assert forbidden not in COMMAND


def test_existing_trust_boundaries_remain_referenced() -> None:
    evidence = (ROOT / "frontend_next/components/property-comparison-report.tsx").read_text(encoding="utf-8")
    storage = (ROOT / "frontend_next/lib/case-storage.ts").read_text(encoding="utf-8")
    assert "canBuildPropertyComparisonReport" in evidence
    assert "transferable" in storage
    assert "proptech.savedCases.v1" in storage


def test_buttons_and_checkbox_labels_are_keyboard_safe() -> None:
    comparison = (ROOT / "frontend_next/components/data-visualization/property-case-comparison-workbench.tsx").read_text(encoding="utf-8")
    assert 'type="button"' in comparison
    assert 'type="checkbox"' in comparison
    assert "aria-label" in comparison
    assert "autofocus" not in comparison.lower()
