"""Loan calculator API tests."""

from fastapi.testclient import TestClient

from backend.api_main import app


client = TestClient(app)


def test_loan_calculator_api_contract() -> None:
    response = client.post(
        "/loan/calculate",
        json={"property_price": 1000, "monthly_income": 10, "annual_interest_rate": 2.2, "loan_years": 30},
    )
    assert response.status_code == 200
    result = response.json()
    assert {
        "property_price_wan",
        "down_payment_wan",
        "loan_amount_wan",
        "monthly_payment",
        "total_payment",
        "total_interest",
        "income_burden_ratio",
        "affordability_level",
        "sensitivity",
        "disclaimer",
    } <= set(result)
    assert result["affordability_level"] != "unknown"


def test_loan_calculator_does_not_require_income() -> None:
    response = client.post("/loan/calculate", json={"property_price": 1000})
    assert response.status_code == 200
    assert response.json()["affordability_level"] == "unknown"


def test_loan_calculator_rejects_invalid_fields() -> None:
    for payload in (
        {"property_price": 1000, "loan_years": 0},
        {"property_price": 1000, "down_payment_ratio": -0.1},
        {"property_price": 1000, "down_payment_ratio": 1.1},
        {"property_price": 1000, "loan_years": 20, "grace_period_years": 20},
    ):
        assert client.post("/loan/calculate", json=payload).status_code == 422
