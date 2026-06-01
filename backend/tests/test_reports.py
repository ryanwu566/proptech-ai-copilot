from datetime import datetime, timezone
from decimal import Decimal

from app.services.reports import build_report_context, render_report_html


class FakeAegisAssessment:
    id = 7
    applicant_name = "Test Buyer"
    property_address = "Taipei"
    property_value = Decimal("10000000")
    loan_amount = Decimal("7500000")
    monthly_income = Decimal("120000")
    existing_debt = Decimal("20000")
    loan_term_years = 30
    created_at = datetime(2026, 5, 27, tzinfo=timezone.utc)
    mock_result = {
        "risk_level": "medium",
        "score": 52,
        "summary": "Deterministic mortgage rules completed.",
        "recommendations": ["Review debt-to-income ratio."],
        "details": {"loan_ratio_band": ["60.00%", "70.00%"]},
    }


def test_report_html_contains_required_sections() -> None:
    context = build_report_context("aegis-credit", FakeAegisAssessment())
    html = render_report_html(context)

    assert "Input Summary" in html
    assert "Analysis Result" in html
    assert "Risk Score" in html
    assert "Recommended Handling" in html
    assert "Data Sources" in html
    assert "Disclaimer" in html
    assert "Test Buyer" in html
    assert "Deterministic mortgage rules completed." in html
