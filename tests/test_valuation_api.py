from fastapi.testclient import TestClient
from backend.api_main import app

client = TestClient(app)


def test_valuation_api_contract() -> None:
    response = client.post("/valuation/estimate", json={"city": "台北市", "district": "大安區", "road": "和平東路二段", "building_type": "住宅大樓", "area_ping": 30, "building_age_years": 15, "floor": 8, "lat": 25.0254, "lng": 121.5434})
    assert response.status_code == 200
    assert {"estimate_total_price", "price_range", "confidence", "comparables"} <= set(response.json())
