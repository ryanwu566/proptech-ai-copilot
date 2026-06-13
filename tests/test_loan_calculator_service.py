"""Loan calculator service tests."""

import pytest

from services.loan_calculator_service import calculate_loan


def test_standard_loan_payment_is_reasonable() -> None:
    result = calculate_loan(1000, 0.2, 2.2, 30, monthly_income=10)
    assert result["down_payment_wan"] == 200
    assert result["loan_amount_wan"] == 800
    assert 30_000 < result["monthly_payment"] < 31_000
    assert result["total_payment"] > 8_000_000
    assert result["total_interest"] > 0
    assert result["income_burden_ratio"] == pytest.approx(result["monthly_payment"] / 100_000, abs=0.0001)


def test_zero_interest_and_unknown_affordability() -> None:
    result = calculate_loan(1200, annual_interest_rate=0, loan_years=20)
    assert result["monthly_payment"] == 40_000
    assert result["total_interest"] == 0
    assert result["income_burden_ratio"] is None
    assert result["affordability_level"] == "unknown"


def test_sensitivity_contains_base_and_higher_rates() -> None:
    result = calculate_loan(1000, annual_interest_rate=2.2)
    assert [item["annual_interest_rate"] for item in result["sensitivity"]] == [1.7, 2.2, 2.7, 3.2]
    base = result["sensitivity"][1]
    assert base["difference_from_base"] == 0
    assert result["sensitivity"][-1]["monthly_payment"] > base["monthly_payment"]


def test_sensitivity_keeps_four_scenarios_when_flooring_at_zero() -> None:
    result = calculate_loan(1000, annual_interest_rate=0.2)
    assert [item["annual_interest_rate"] for item in result["sensitivity"]] == [0, 0.2, 0.7, 1.2]


def test_grace_period_returns_interest_only_and_post_grace_payments() -> None:
    result = calculate_loan(1000, annual_interest_rate=2.2, loan_years=30, grace_period_years=3)
    assert result["grace_period_monthly_payment"] == 14_667
    assert result["post_grace_monthly_payment"] == result["monthly_payment"]
    assert result["post_grace_monthly_payment"] > 0
    assert result["total_interest"] > calculate_loan(1000, annual_interest_rate=2.2, loan_years=30)["total_interest"]


def test_zero_grace_period_has_stable_null_fields() -> None:
    result = calculate_loan(1000, grace_period_years=0)
    assert result["grace_period_monthly_payment"] is None
    assert result["post_grace_monthly_payment"] is None


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("loan_years", 0),
        ("down_payment_ratio", -0.1),
        ("down_payment_ratio", 1.1),
        ("grace_period_years", 30),
    ],
)
def test_invalid_inputs_raise_validation_error(field: str, value: float) -> None:
    inputs = {"property_price": 1000, field: value}
    with pytest.raises(ValueError):
        calculate_loan(**inputs)
