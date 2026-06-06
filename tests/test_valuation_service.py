from services import valuation_service
from services.valuation_service import estimate_property


def test_estimate_returns_range_and_comparables() -> None:
    result = estimate_property({"city": "台北市", "district": "大安區", "road": "和平東路二段", "building_type": "住宅大樓", "area_ping": 30, "building_age_years": 15, "floor": 8, "lat": 25.0254, "lng": 121.5434})
    assert result["estimate_total_price"] > 0
    assert result["price_range"]["low"] <= result["price_range"]["mid"] <= result["price_range"]["high"]
    assert len(result["comparables"]) >= 3


def test_insufficient_data_does_not_crash(monkeypatch) -> None:
    monkeypatch.setattr(valuation_service, "load_transactions", lambda: ())
    assert estimate_property({"city": "無", "district": "無", "road": "無", "building_type": "住宅大樓", "area_ping": 30, "building_age_years": 15, "floor": 8})["confidence"] == "low"
