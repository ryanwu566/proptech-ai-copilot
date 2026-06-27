from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HELPER = ROOT / "frontend" / "lib" / "viewing-decision.ts"
CARD = ROOT / "frontend" / "components" / "viewing-decision-card.tsx"
REPORT_CARD = ROOT / "frontend" / "components" / "viewing-decision-report-card.tsx"
HOME = ROOT / "frontend" / "app" / "page.tsx"
FORM = ROOT / "frontend" / "components" / "assessment-form.tsx"


def helper_source() -> str:
    return HELPER.read_text(encoding="utf-8")


def test_missing_results_stay_conservative() -> None:
    source = helper_source()
    missing_branch = source[source.index("assessments.length === 0") : source.index("if (highRisk)")]

    assert 'status: "needs_more_information"' in missing_branch
    assert 'missingChecks' in missing_branch
    assert 'href: "/tax-oracle"' in missing_branch
    assert 'COPY.notLowRisk' in missing_branch


def test_high_risk_requires_clarification_before_viewing() -> None:
    source = helper_source()
    high_branch = source[source.index("if (highRisk)") : source.index("if (missingChecks.length")]

    assert 'status: "clarify_risk_first"' in high_branch
    assert 'COPY.clarifyLabel' in high_branch
    assert 'moduleHref(highRisk.moduleSlug)' in high_branch
    assert 'COPY.highRiskSuffix' in high_branch


def test_all_three_low_results_can_continue_with_caveats() -> None:
    source = helper_source()
    ready_branch = source[source.index('return { status: "continue_viewing"') : source.index("export function mergeStoredAssessment")]

    assert 'status: "continue_viewing"' in ready_branch
    assert 'COPY.continueLabel' in ready_branch
    assert 'missingChecks: []' in ready_branch
    assert 'COPY.notOverall' in ready_branch


def test_each_status_has_action_target() -> None:
    source = helper_source()

    assert 'href: "/tax-oracle"' in source
    assert 'moduleHref(highRisk.moduleSlug)' in source
    assert 'moduleHref(nextMissing)' in source
    assert 'href: "/"' in source


def test_storage_result_is_sanitized_to_whitelist() -> None:
    helper = helper_source()
    form = FORM.read_text(encoding="utf-8")
    sanitizer = helper[helper.index("export function toViewingDecisionResult") : helper.index("export function moduleHref")]

    assert "toViewingDecisionResult(savedResult.result)" in form
    assert "result: savedResult.result" not in form
    assert "...savedResult.result" not in form
    assert "risk_level" in sanitizer
    assert "summary" in sanitizer
    assert "recommendations" in sanitizer
    assert "score" in sanitizer
    assert "details" not in sanitizer
    assert "property_address" not in sanitizer


def test_old_storage_is_rewritten_after_sanitizing_details() -> None:
    source = helper_source()
    read_branch = source[source.index("export function readStoredViewingAssessments") : source.index("export function writeStoredViewingAssessment")]

    assert "sanitizeModuleAssessment" in read_branch
    assert "window.localStorage.setItem" in read_branch
    assert "JSON.stringify(parsed) !== JSON.stringify(sanitized)" in read_branch
    assert "localStorage.clear" not in source


def test_three_module_records_are_merged_by_slug_without_overwriting_others() -> None:
    source = helper_source()
    merge_branch = source[source.index("export function mergeStoredAssessment") : source.index("export function readStoredViewingAssessments")]

    assert "item.moduleSlug !== sanitized.moduleSlug" in merge_branch
    assert "nextAssessment" in merge_branch
    assert "sanitizeModuleAssessment(nextAssessment)" in merge_branch


def test_frontend_card_uses_existing_result_flow_without_absolute_claims() -> None:
    source = "\n".join([
        HELPER.read_text(encoding="utf-8"),
        CARD.read_text(encoding="utf-8"),
        REPORT_CARD.read_text(encoding="utf-8"),
        HOME.read_text(encoding="utf-8"),
        FORM.read_text(encoding="utf-8"),
    ])

    assert "ViewingDecisionCard" in source
    assert "writeStoredViewingAssessment" in source
    assert "readStoredViewingAssessments" in source
    assert "String.fromCodePoint" in source
    assert "safe" not in source.lower()
    assert "guarantee" not in source.lower()
    assert "NASA" not in source
    assert "Address Resolve" not in source
    assert "TGOS" not in source
    assert "Google" not in source
