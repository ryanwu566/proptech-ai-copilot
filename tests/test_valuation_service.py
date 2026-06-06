from collections import Counter

from services import valuation_service
from services.valuation_service import estimate_property, load_transactions


PAYLOAD = {
    "city": "台北市",
    "district": "大安區",
    "road": "和平東路二段",
    "building_type": "住宅大樓",
    "area_ping": 30,
    "building_age_years": 15,
    "floor": 8,
    "lat": 25.0254,
    "lng": 121.5434,
}


def test_estimate_returns_explainable_range_and_comparables() -> None:
    result = estimate_property(PAYLOAD)
    assert result["estimate_total_price"] > 0
    assert result["price_range"]["low"] <= result["price_range"]["mid"] <= result["price_range"]["high"]
    assert len(result["comparables"]) >= 3
    assert result["source_details"]["formal_appraisal"] is False
    assert result["valuation_explanation"]["same_road_count"] >= 1
    assert all("similarity_score" in row and "weight" in row for row in result["comparables"])


def test_sample_has_three_demo_regions_with_at_least_twenty_rows_each() -> None:
    rows = load_transactions()
    counts = Counter((row["city"], row["district"], row["road"]) for row in rows)
    assert len(rows) >= 60
    assert counts[("台北市", "大安區", "和平東路二段")] >= 20
    assert counts[("台北市", "信義區", "松仁路")] >= 20
    assert counts[("新北市", "板橋區", "文化路二段")] >= 20


def test_insufficient_data_does_not_crash(monkeypatch) -> None:
    monkeypatch.setattr(valuation_service, "load_transactions", lambda: ())
    assert estimate_property(PAYLOAD)["confidence"] == "low"
