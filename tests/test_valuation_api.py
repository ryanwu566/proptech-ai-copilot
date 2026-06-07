from fastapi.testclient import TestClient
from backend.api_main import app

client = TestClient(app)


def test_valuation_api_contract() -> None:
    response = client.post("/valuation/estimate", json={"city": "台北市", "district": "大安區", "road": "和平東路二段", "building_type": "住宅大樓", "area_ping": 30, "building_age_years": 15, "floor": 8, "lat": 25.0254, "lng": 121.5434})
    assert response.status_code == 200
    assert {"estimate_total_price", "price_range", "confidence", "comparables", "data_status", "estimate_level"} <= set(response.json())


def test_valuation_data_status_api() -> None:
    response = client.get("/valuation/data-status")
    assert response.status_code == 200
    assert response.json()["coverage"]["records_count"] >= 60
    assert response.json()["active_source"] == "real_price_sample"


def test_health_does_not_depend_on_valuation_provider(monkeypatch) -> None:
    monkeypatch.setattr("services.valuation_service.get_valuation_provider", lambda: (_ for _ in ()).throw(RuntimeError("must not run")))
    assert client.get("/health").status_code == 200
