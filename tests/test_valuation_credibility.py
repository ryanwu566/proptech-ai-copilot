from services.valuation_providers.postgres_provider import PostgresValuationProvider, _normalize_row
from services.valuation_service import estimate_property, normalize_building_type, normalize_city, normalize_road


PAYLOAD = {"city": "Taipei City", "district": "Central District", "road": "Example Road", "building_type": "Apartment", "area_ping": 30, "building_age_years": 12, "floor": 8, "lat": 25.0, "lng": 121.5}


def row(index: int, source: str, *, road: str = "Example Road", period: str = "2025-01", lat=None, lng=None) -> dict:
    return {"transaction_period": period, "city": "Taipei City", "district": "Central District", "road": road, "building_type": "Apartment", "area_ping": 28 + index / 10, "unit_price_per_ping": 70 + index, "total_price": (70 + index) * (28 + index / 10), "building_age_years": 10, "floor": 8, "lat": lat, "lng": lng, "source": source}


def fake_postgres(monkeypatch, rows: list[dict]) -> None:
    provider = PostgresValuationProvider("postgresql://test")
    monkeypatch.setattr(provider, "query_comparables", lambda _payload: rows)
    monkeypatch.setattr(provider, "match_community", lambda _payload: None)
    monkeypatch.setattr(provider, "data_status", lambda: {"active_source": "postgres", "is_demo_data": False, "is_full_taiwan": False, "data_composition": "official", "coverage": {"cities": [], "districts": [], "roads_count": 1, "records_count": len(rows)}, "last_updated": None, "source_note": "", "user_message": ""})
    provider.last_query_metadata = {"provider_active": "postgres", "candidate_pool_size": len(rows), "query_scope": "road", "requested_city": "Taipei City", "requested_district": "Central District", "requested_road": "Example Road", "db_rows_returned": len(rows), "query_status": "ok"}
    monkeypatch.setattr("services.valuation_service.get_valuation_provider", lambda: provider)


def test_sufficient_official_same_road_records_are_actionable(monkeypatch) -> None:
    fake_postgres(monkeypatch, [row(index, "official_plvr_opendata") for index in range(8)] + [row(20, "real_price_sample")])
    result = estimate_property(PAYLOAD)
    assert result["estimate_data_composition"] == "official"
    assert result["is_actionable"] is True
    assert {item["source"] for item in result["comparables"]} == {"official_plvr_opendata"}


def test_sample_only_is_no_data_and_has_no_numbers(monkeypatch) -> None:
    fake_postgres(monkeypatch, [row(index, "real_price_sample", lat=25.0, lng=121.5) for index in range(10)])
    result = estimate_property(PAYLOAD)
    assert result["valuation_status"] == "no_data"
    assert result["estimate_total_price"] is None
    assert result["comparables"] == []


def test_official_district_scope_is_allowed_with_three_rows(monkeypatch) -> None:
    fake_postgres(monkeypatch, [row(index, "official_plvr_opendata", road="Other Road") for index in range(6)])
    result = estimate_property(PAYLOAD)
    assert result["estimate_data_composition"] == "official_district"
    assert result["estimate_level"] == "district"
    assert result["is_actionable"] is True


def test_missing_coordinates_stay_null(monkeypatch) -> None:
    fake_postgres(monkeypatch, [row(index, "official_plvr_opendata") for index in range(8)])
    result = estimate_property(PAYLOAD)
    assert all(item["distance_m"] is None for item in result["comparables"])


def test_future_official_period_is_excluded(monkeypatch) -> None:
    rows = [row(index, "official_plvr_opendata") for index in range(4)] + [row(2, "official_plvr_opendata", period="2099-12"), row(2, "real_price_sample", period="2099-12")]
    fake_postgres(monkeypatch, rows)
    result = estimate_property(PAYLOAD)
    assert not any(item["transaction_period"] == "2099-12" for item in result["comparables"])


def test_postgres_missing_coordinates_stay_null() -> None:
    normalized = _normalize_row({"area_ping": 30, "unit_price_per_ping": 70, "total_price": 2100, "building_age_years": 10, "floor": 8, "lat": None, "lng": None})
    assert normalized["lat"] is None
    assert normalized["lng"] is None


def test_normalized_fields_keep_scope_comparison_stable() -> None:
    assert normalize_road("Example Road 2段") == normalize_road("Example Road 二段")
    assert normalize_city("Taipei City") == normalize_city("Taipei City")
    assert normalize_building_type("Apartment") == "Apartment"
