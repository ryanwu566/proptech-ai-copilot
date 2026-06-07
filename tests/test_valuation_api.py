from fastapi.testclient import TestClient
from backend.api_main import app
from services.valuation_providers.postgres_provider import PostgresValuationProvider
from services.valuation_service import normalize_road

client = TestClient(app)


def test_valuation_api_contract() -> None:
    response = client.post("/valuation/estimate", json={"city": "台北市", "district": "大安區", "road": "和平東路二段", "building_type": "住宅大樓", "area_ping": 30, "building_age_years": 15, "floor": 8, "lat": 25.0254, "lng": 121.5434})
    assert response.status_code == 200
    assert {"estimate_total_price", "price_range", "confidence", "comparables", "data_status", "estimate_level"} <= set(response.json())


def test_valuation_data_status_api() -> None:
    response = client.get("/valuation/data-status")
    assert response.status_code == 200
    payload = response.json()
    assert payload["coverage"]["records_count"] >= 60
    assert payload["active_source"] == "real_price_sample"
    assert payload["retention_policy_years"] == 3
    assert payload["retention_cutoff_period"]
    assert payload["records_outside_retention_count"] == 0
    assert "rolling 3 年" in payload["retention_note"]


def test_health_does_not_depend_on_valuation_provider(monkeypatch) -> None:
    monkeypatch.setattr("services.valuation_service.get_valuation_provider", lambda: (_ for _ in ()).throw(RuntimeError("must not run")))
    assert client.get("/health").status_code == 200


def test_estimate_endpoint_exposes_real_road_scope_selection(monkeypatch) -> None:
    def make_row(index: int, source: str, road: str) -> dict:
        return {
            "transaction_period": "2026-03",
            "city": "台北市",
            "district": "大安區",
            "road": road,
            "building_type": "住宅大樓(11層含以上有電梯)" if source == "official_plvr_opendata" else "住宅大樓",
            "area_ping": 28 + index,
            "unit_price_per_ping": 70 + index,
            "total_price": (70 + index) * (28 + index),
            "building_age_years": 15,
            "floor": 8,
            "lat": None,
            "lng": None,
            "source": source,
        }

    rows = [make_row(index, "official_plvr_opendata", "和平東路2段") for index in range(4)]
    rows += [make_row(index, "real_price_sample", "和平東路二段") for index in range(4)]
    rows += [make_row(index, "official_plvr_opendata", "建國南路一段") for index in range(10)]
    provider = PostgresValuationProvider("postgresql://test")
    monkeypatch.setattr(provider, "query_comparables", lambda _payload: rows)
    provider.last_query_metadata = {
        "provider_active": "postgres",
        "candidate_pool_size": len(rows),
        "query_scope": "district_pool",
        "requested_city": "台北市",
        "requested_district": "大安區",
        "requested_road": "和平東路二段",
        "db_rows_returned": len(rows),
        "query_status": "ok",
    }
    monkeypatch.setattr(provider, "match_community", lambda _payload: None)
    monkeypatch.setattr(provider, "data_status", lambda: {"active_source": "postgres", "is_demo_data": False, "is_full_taiwan": False, "data_composition": "mixed", "coverage": {"cities": ["台北市"], "districts": ["大安區"], "roads_count": 2, "records_count": 18}, "last_updated": None, "update_frequency_note": "", "source_note": "", "user_message": ""})
    monkeypatch.setattr("services.valuation_service.get_valuation_provider", lambda: provider)

    response = client.post("/valuation/estimate", json={"city": "台北市", "district": "大安區", "road": "和平東路二段", "building_type": "住宅大樓", "area_ping": 30, "building_age_years": 15, "floor": 8})
    payload = response.json()
    assert response.status_code == 200
    assert payload["estimate_data_composition"] == "official_limited"
    assert payload["official_same_road_count"] == 4
    assert payload["official_same_district_count"] == 10
    assert payload["sample_same_road_count"] == 4
    assert payload["sample_same_district_count"] == 0
    assert payload["candidate_pool_size"] == 18
    assert payload["source_details"]["candidate_pool_size"] == 18
    assert payload["source_details"]["query_scope"] == "district_pool"
    assert payload["comparables"]
    assert [item["source"] for item in payload["comparables"][:4]] == ["official_plvr_opendata"] * 4
    assert all(normalize_road(item["road"]) == "和平東路二段" for item in payload["comparables"][:4])
    assert all(normalize_road(item["road"]) == "和平東路二段" for item in payload["comparables"])
