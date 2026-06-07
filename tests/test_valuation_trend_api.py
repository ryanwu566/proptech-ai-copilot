from datetime import UTC, datetime

from fastapi.testclient import TestClient

from backend.api_main import app
from services.valuation_providers.postgres_provider import PostgresValuationProvider
from services.valuation_trend_service import _shift_month


client = TestClient(app)


def test_valuation_trend_api_contract(monkeypatch) -> None:
    current = datetime.now(UTC).strftime("%Y-%m")
    rows = [
        {
            "transaction_period": _shift_month(current, -(index % 12)),
            "city": "新北市",
            "district": "板橋區",
            "road": "文化路二段",
            "building_type": "住宅大樓",
            "area_ping": 30,
            "building_age_years": 15,
            "unit_price_per_ping": 58 + index % 5,
            "total_price": 1800,
            "source": "official_plvr_opendata",
        }
        for index in range(35)
    ]
    provider = PostgresValuationProvider("postgresql://test")
    monkeypatch.setattr(provider, "query_trend_rows", lambda _payload: rows)
    monkeypatch.setattr("services.valuation_trend_service.get_valuation_provider", lambda: provider)
    response = client.post(
        "/valuation/trend",
        json={"city": "新北市", "district": "板橋區", "road": "文化路二段", "building_type": "住宅大樓", "area_ping": 30, "building_age_years": 15, "horizon_months": [6, 12, 36]},
    )
    payload = response.json()
    assert response.status_code == 200
    assert payload["data_scope"] == "road"
    assert payload["road_sample_count"] == 35
    assert payload["monthly_series"]
    assert payload["scenario_forecast"]["base"]
