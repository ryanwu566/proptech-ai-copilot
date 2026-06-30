"""Static contracts for Property Case Command Center v2."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMMAND_CENTER_PATH = ROOT / "frontend_next/components/property-case-command-center.tsx"
CASE_ROUTE_PATH = ROOT / "frontend_next/app/cases/[caseId]/page.tsx"
CASE_MANAGER_PATH = ROOT / "frontend_next/components/case-manager.tsx"
CASE_MODEL_PATH = ROOT / "frontend_next/lib/property-case.ts"
VIEWING_DECISION_PANEL_PATH = ROOT / "frontend_next/components/viewing-decision-panel.tsx"
VIEWING_DECISION_LIB_PATH = ROOT / "frontend_next/lib/viewing-decision.ts"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_case_command_center_route_and_list_entry_exist() -> None:
    route = read(CASE_ROUTE_PATH)
    manager = read(CASE_MANAGER_PATH)

    assert "PropertyCaseCommandCenter" in route
    assert "caseId" in route
    assert "/cases/${encodeURIComponent(saved.id)}" in manager
    assert "案件工作台" in manager


def test_case_command_center_reuses_case_domain_and_readiness_helpers() -> None:
    source = read(COMMAND_CENTER_PATH)

    assert "buildPropertyCaseDraft" in source
    assert "buildPropertyCaseReadiness" in source
    assert "PARTIAL_CASE_PRINT_NOTICE" in source
    assert "PropertyDecisionStatus" in source
    assert "window.print()" in source
    assert "server PDF" not in source


def test_case_command_center_has_required_workbench_sections() -> None:
    source = read(COMMAND_CENTER_PATH)

    for label in (
        "基本案件資料",
        "資金與貸款參考",
        "財務資料與決策試算",
        "估價、成本與稅費手動欄位",
        "位置、通勤、地勢與市場資料",
    ):
        assert label in source

    for state in ("draft", "reviewing", "shortlisted", "rejected", "purchased"):
        assert state in source


def test_case_command_center_does_not_auto_query_or_persist_case_data() -> None:
    source = read(COMMAND_CENTER_PATH)

    for forbidden in (
        "fetch(",
        "api.",
        "/market-insights/query",
        "/commute",
        "/terrain",
        "api.valuation",
        "api.loan",
        "api.tax",
        "localStorage",
        "sessionStorage",
        "document.cookie",
        "URLSearchParams",
        "location.search",
        "location.hash",
    ):
        assert forbidden not in source


def test_market_and_commute_are_manual_references_not_decision_autofill() -> None:
    source = read(COMMAND_CENTER_PATH)

    assert "Market Insight" in source
    assert "Direct Market Query Mode" in source
    assert "county 必填" in source
    assert "district 選填" in source
    assert "不會自動寫入案件判斷" in source
    assert "貼到備註或決策備註" in source


def test_property_case_model_supports_command_center_fields_without_raw_payloads() -> None:
    source = read(CASE_MODEL_PATH)

    for field in (
        "PropertyDecisionStatus",
        "decision_status",
        "decision_note",
        "last_reviewed_at",
        "valuation_tax_input",
        "user_estimated_value",
        "user_estimated_tax_cost",
    ):
        assert field in source

    for forbidden in ("raw payload", "provider raw", "token", "secret", "StationUID"):
        assert forbidden not in source


def test_viewing_decision_files_are_not_rewired_to_command_center() -> None:
    combined = read(VIEWING_DECISION_PANEL_PATH) + read(VIEWING_DECISION_LIB_PATH)

    assert "PropertyCaseCommandCenter" not in combined
    assert "locationMarketNote" not in combined
    assert "valuation_tax_input" not in combined
