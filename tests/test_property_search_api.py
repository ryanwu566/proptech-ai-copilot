"""Property Finder API contracts."""

from fastapi.testclient import TestClient

from backend.api_main import app


client = TestClient(app)


def test_property_search_api_contract() -> None:
    response = client.post("/valuation/property-search", json={"budget_max": 2500, "limit": 20})
    assert response.status_code == 200
    assert {"summary", "district_suggestions", "road_suggestions", "matched_transactions", "disclaimer"} <= set(response.json())


def test_property_search_api_rejects_limit_above_100() -> None:
    response = client.post("/valuation/property-search", json={"budget_max": 2500, "limit": 101})
    assert response.status_code == 422
