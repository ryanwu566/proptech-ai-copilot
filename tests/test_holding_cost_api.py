"""Holding-cost API tests."""

from fastapi.testclient import TestClient

from backend.api_main import app


client = TestClient(app)


def test_holding_cost_api_contract() -> None:
    response = client.post(
        "/holding-cost/calculate",
        json={"property_price": 1000, "loan_monthly_payment": 30376, "area_ping": 30, "monthly_income": 10},
    )
    assert response.status_code == 200
    result = response.json()
    assert {
        "input",
        "property_price_wan",
        "loan_monthly_payment",
        "monthly_management_fee",
        "monthly_repair_reserve",
        "monthly_tax_estimate",
        "annual_home_tax_estimate",
        "annual_land_tax_estimate",
        "monthly_insurance",
        "monthly_total_holding_cost",
        "annual_total_holding_cost",
        "income_burden_ratio",
        "affordability_level",
        "affordability_message",
        "cost_breakdown",
        "disclaimer",
    } <= set(result)


def test_holding_cost_api_rejects_invalid_values() -> None:
    assert client.post("/holding-cost/calculate", json={"property_price": 0}).status_code == 422
    assert client.post("/holding-cost/calculate", json={"property_price": 1000, "area_ping": -1}).status_code == 422
