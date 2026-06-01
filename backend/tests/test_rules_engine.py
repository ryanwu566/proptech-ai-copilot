from decimal import Decimal

from app.schemas.assessments import AegisCreditCreate, LexPropCreate, TaxOracleCreate
from app.services.rules_engine import (
    analyze_aegis_credit,
    analyze_lex_prop,
    analyze_tax_oracle,
)


def test_aegis_credit_outputs_loan_band_and_stress_test() -> None:
    payload = AegisCreditCreate(
        applicant_name="Test Buyer",
        property_address="Taipei",
        property_value=Decimal("10000000"),
        loan_amount=Decimal("8500000"),
        monthly_income=Decimal("120000"),
        existing_debt=Decimal("35000"),
        loan_term_years=30,
    )

    result = analyze_aegis_credit(payload)

    assert result.score >= 75
    assert result.risk_level == "high"
    assert result.details["loan_ratio_band"] == ["50.00%", "60.00%"]
    assert "stress_test" in result.details
    assert result.details["stress_test"]["annual_rate"] == "4.00%"


def test_tax_oracle_eligible_repurchase_refund_case() -> None:
    payload = TaxOracleCreate(
        taxpayer_name="Owner",
        property_address="Taichung",
        assessed_value=Decimal("8000000"),
        replacement_purchase_value=Decimal("9000000"),
        annual_rental_income=Decimal("0"),
        holding_years=3,
        transaction_type="sale",
        is_self_use=True,
        has_outstanding_tax_debt=False,
    )

    result = analyze_tax_oracle(payload)

    assert result.details["eligible"] is True
    assert result.risk_level == "low"
    assert result.details["calculation_method"] == "deterministic_rules_only_no_llm"
    assert len(result.details["five_year_monitoring_reminders"]) == 5


def test_tax_oracle_lists_blockers_for_ineligible_case() -> None:
    payload = TaxOracleCreate(
        taxpayer_name="Owner",
        property_address="Kaohsiung",
        assessed_value=Decimal("9000000"),
        replacement_purchase_value=Decimal("5000000"),
        annual_rental_income=Decimal("240000"),
        holding_years=1,
        transaction_type="rental",
        is_self_use=False,
        has_outstanding_tax_debt=True,
    )

    result = analyze_tax_oracle(payload)

    assert result.details["eligible"] is False
    assert result.score >= 75
    assert len(result.details["blockers"]) >= 4


def test_lex_prop_keyword_classifier_matches_risk_categories() -> None:
    payload = LexPropCreate(
        owner_name="Seller",
        property_address="New Taipei",
        title_number="A-123",
        has_lien=False,
        has_easement=False,
        dispute_notes="曾有漏水，管委會紀錄提到共有物糾紛與非自然身故。",
    )

    result = analyze_lex_prop(payload)
    categories = {item["category"] for item in result.details["matched_categories"]}

    assert {"water_leak", "hoa_committee", "unnatural_death", "co_owned_dispute"} <= categories
    assert result.score >= 70
    assert result.details["classifier"] == "keyword_rules_only"
