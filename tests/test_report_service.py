"""Report and persisted history integration tests."""

from __future__ import annotations

import pandas as pd

from backend.repositories.sqlite_repo import get_tax_analysis, list_tax_analyses
from models.schemas import DISCLAIMER, TaxCase
from services.report_service import generate_tax_html_report
from services.tax_service import analyze_tax_case


def make_case(case_id: str = "REPORT-001") -> TaxCase:
    """Build a complete eligible case for report tests."""

    return TaxCase(
        case_id=case_id,
        client_name="報告測試客戶",
        sold_self_occupied=True,
        residency_condition_met=True,
        purchase_within_reasonable_period=True,
        purchased_self_occupied=True,
        same_owner=True,
        land_value_available=True,
        required_docs_complete=True,
        enters_five_year_monitoring=True,
        exceptional_circumstances=False,
    )


def test_html_report_contains_required_sections() -> None:
    case = make_case()
    result = analyze_tax_case(case, persist=False)
    html = generate_tax_html_report(case, result)
    assert "案件摘要" in html
    assert "eligible" in html
    assert "風險分數" in html
    assert "Rule Trace" in html
    assert "補件清單" in html
    assert "五年列管 Timeline" in html
    assert result["ai_explanation"]["headline"] in html
    assert DISCLAIMER in html


def test_tax_analysis_can_be_reloaded_from_history() -> None:
    case = make_case("HISTORY-001")
    analyze_tax_case(case)
    row = next(row for row in list_tax_analyses() if row["case_id"] == case.case_id)
    stored = get_tax_analysis(row["id"])
    assert stored is not None
    assert stored["payload"]["case_input"]["client_name"] == case.client_name
    assert stored["payload"]["eligibility_status"] == "eligible"


def test_all_demo_cases_generate_html_reports() -> None:
    """Ensure the competition demo cases keep their expected outputs."""

    expected = {
        "DEMO-LOW": ("eligible", "green"),
        "DEMO-MEDIUM": ("manual_review", "yellow"),
        "DEMO-HIGH": ("not_eligible", "red"),
    }
    for row in pd.read_csv("data/mock_tax_cases.csv").to_dict("records"):
        case = TaxCase(**row)
        result = analyze_tax_case(case, persist=False)
        html = generate_tax_html_report(case, result)
        assert (result["eligibility_status"], result["signal_color"]) == expected[case.case_id]
        assert f"TaxOracle 報告 - {case.case_id}" in html
        assert len(html.encode("utf-8")) > 1000
