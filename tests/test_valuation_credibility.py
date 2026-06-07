from services.valuation_providers.postgres_provider import PostgresValuationProvider, _normalize_row
from services.valuation_service import estimate_property


PAYLOAD = {
    "city": "台北市",
    "district": "大安區",
    "road": "和平東路二段",
    "building_type": "住宅大樓",
    "area_ping": 30,
    "building_age_years": 12,
    "floor": 8,
    "lat": 25.0254,
    "lng": 121.5434,
}


def row(index: int, source: str, *, period: str = "2025-01", road: str = "和平東路二段", lat=None, lng=None) -> dict:
    return {
        "transaction_period": period,
        "city": "台北市",
        "district": "大安區",
        "road": road,
        "building_type": "住宅大樓",
        "area_ping": 28 + index / 10,
        "unit_price_per_ping": 70 + index,
        "total_price": (70 + index) * (28 + index / 10),
        "building_age_years": 10,
        "floor": 8,
        "lat": lat,
        "lng": lng,
        "source": source,
    }


def fake_postgres(monkeypatch, rows: list[dict]) -> None:
    provider = PostgresValuationProvider("postgresql://test")
    monkeypatch.setattr(provider, "query_comparables", lambda _payload: rows)
    monkeypatch.setattr(provider, "match_community", lambda _payload: None)
    monkeypatch.setattr(
        provider,
        "data_status",
        lambda: {
            "active_source": "postgres",
            "is_demo_data": False,
            "is_full_taiwan": False,
            "data_composition": "mixed",
            "coverage": {"cities": ["台北市"], "districts": ["大安區"], "roads_count": 1, "records_count": len(rows)},
            "last_updated": None,
            "update_frequency_note": "",
            "source_note": "",
            "user_message": "",
        },
    )
    monkeypatch.setattr("services.valuation_service.get_valuation_provider", lambda: provider)


def test_sufficient_official_same_road_records_exclude_sample(monkeypatch) -> None:
    rows = [row(index, "official_plvr_opendata") for index in range(8)] + [row(20, "real_price_sample")]
    fake_postgres(monkeypatch, rows)
    result = estimate_property(PAYLOAD)
    assert result["estimate_data_composition"] == "official"
    assert {item["source"] for item in result["comparables"]} == {"official_plvr_opendata"}
    assert {item["source_label"] for item in result["comparables"]} == {"官方 PLVR"}


def test_sample_only_confidence_is_capped(monkeypatch) -> None:
    fake_postgres(monkeypatch, [row(index, "real_price_sample", lat=25.0254, lng=121.5434) for index in range(10)])
    result = estimate_property(PAYLOAD)
    assert result["estimate_data_composition"] == "sample"
    assert result["confidence_score"] <= 70


def test_mixed_confidence_is_capped(monkeypatch) -> None:
    rows = [row(index, "official_plvr_opendata") for index in range(4)] + [row(index + 10, "real_price_sample") for index in range(4)]
    fake_postgres(monkeypatch, rows)
    result = estimate_property(PAYLOAD)
    assert result["estimate_data_composition"] == "mixed"
    assert result["confidence_score"] <= 80


def test_missing_coordinates_return_null_distance(monkeypatch) -> None:
    fake_postgres(monkeypatch, [row(index, "official_plvr_opendata") for index in range(8)])
    result = estimate_property(PAYLOAD)
    assert all(item["distance_m"] is None for item in result["comparables"])


def test_future_official_period_is_excluded_but_sample_is_labeled(monkeypatch) -> None:
    rows = [row(index, "official_plvr_opendata") for index in range(4)]
    rows += [row(2, "official_plvr_opendata", period="2099-12"), row(2, "real_price_sample", period="2099-12")]
    fake_postgres(monkeypatch, rows)
    result = estimate_property(PAYLOAD)
    assert not any(item["source"] == "official_plvr_opendata" and item["transaction_period"] == "2099-12" for item in result["comparables"])
    assert any(item["source_label"] == "展示樣本" and item["transaction_period"] == "2099-12" for item in result["comparables"])


def test_postgres_missing_coordinates_stay_null() -> None:
    normalized = _normalize_row({"area_ping": 30, "unit_price_per_ping": 70, "total_price": 2100, "building_age_years": 10, "floor": 8, "lat": None, "lng": None})
    assert normalized["lat"] is None
    assert normalized["lng"] is None
