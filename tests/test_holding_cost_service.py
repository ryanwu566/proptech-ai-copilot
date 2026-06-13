"""Holding-cost service tests."""

import pytest

from services.holding_cost_service import calculate_holding_cost


def test_basic_holding_cost_case() -> None:
    result = calculate_holding_cost(1000, loan_monthly_payment=30376, area_ping=30, monthly_income=10)
    assert result["monthly_management_fee"] == 2400
    assert result["monthly_repair_reserve"] == 1500
    assert result["annual_home_tax_estimate"] == 12000
    assert result["annual_land_tax_estimate"] == 10000
    assert result["monthly_tax_estimate"] == 1833
    assert result["monthly_insurance"] == 250
    assert result["monthly_total_holding_cost"] == 36359
    assert result["annual_total_holding_cost"] == 436312
    assert result["income_burden_ratio"] == pytest.approx(0.3636)
    assert result["affordability_level"] == "manageable"


def test_without_loan_payment_still_calculates_non_loan_costs() -> None:
    result = calculate_holding_cost(1000, area_ping=30)
    assert result["loan_monthly_payment"] == 0
    assert result["monthly_total_holding_cost"] > 0


def test_without_income_is_unknown() -> None:
    result = calculate_holding_cost(1000)
    assert result["income_burden_ratio"] is None
    assert result["affordability_level"] == "unknown"


def test_without_area_has_stable_zero_area_costs() -> None:
    result = calculate_holding_cost(1000)
    assert result["monthly_management_fee"] == 0
    assert result["monthly_repair_reserve"] == 0
    assert result["input"]["area_ping"] is None


def test_tax_estimate_can_be_disabled() -> None:
    result = calculate_holding_cost(1000, include_tax_estimate=False)
    assert result["monthly_tax_estimate"] == 0
    assert result["annual_home_tax_estimate"] == 0
    assert result["annual_land_tax_estimate"] == 0


@pytest.mark.parametrize(
    ("monthly_cost", "expected"),
    [(30_000, "comfortable"), (35_000, "manageable"), (45_000, "tight"), (55_000, "risky")],
)
def test_affordability_levels(monthly_cost: float, expected: str) -> None:
    result = calculate_holding_cost(
        1000,
        loan_monthly_payment=monthly_cost,
        monthly_income=10,
        annual_insurance=0,
        include_tax_estimate=False,
    )
    assert result["affordability_level"] == expected


@pytest.mark.parametrize("payload", [{"property_price": 0}, {"property_price": 1000, "area_ping": -1}])
def test_invalid_inputs(payload: dict[str, float]) -> None:
    with pytest.raises(ValueError):
        calculate_holding_cost(**payload)
