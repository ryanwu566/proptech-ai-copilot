"""TaxOracle rule engine tests."""

from models.schemas import TaxCase
from rules.tax_rules import evaluate_tax_case


def make_case(**overrides: bool) -> TaxCase:
    values = {
        "case_id": "TEST-001",
        "client_name": "測試客戶",
        "sold_self_occupied": True,
        "residency_condition_met": True,
        "purchase_within_reasonable_period": True,
        "purchased_self_occupied": True,
        "same_owner": True,
        "land_value_available": True,
        "required_docs_complete": True,
        "enters_five_year_monitoring": True,
        "exceptional_circumstances": False,
    }
    values.update(overrides)
    return TaxCase(**values)


def test_eligible_case_is_green() -> None:
    result = evaluate_tax_case(make_case())
    assert result.eligibility_status == "eligible"
    assert result.risk_score == 0
    assert result.signal_color == "green"
    assert len(result.reminder_timeline) == 5


def test_missing_documents_trigger_manual_review() -> None:
    result = evaluate_tax_case(make_case(land_value_available=False, required_docs_complete=False))
    assert result.eligibility_status == "manual_review"
    assert result.risk_score == 25
    assert result.signal_color == "yellow"
    assert "TX006" in result.manual_review_rules
    assert "公告土地現值資料" in result.missing_docs


def test_hard_fail_cannot_be_replaced_by_score() -> None:
    result = evaluate_tax_case(make_case(sold_self_occupied=False))
    assert result.eligibility_status == "not_eligible"
    assert result.risk_score == 35
    assert "TX001" in result.hard_fail_rules

