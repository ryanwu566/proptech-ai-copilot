from pathlib import Path

from fastapi.testclient import TestClient

from backend.api_main import app
from services.plvr_import_service import city_from_filename
from services.valuation_providers.postgres_provider import PostgresValuationProvider
from services.valuation_service import normalize_road


client = TestClient(app)


def _row(index: int, source: str, road: str) -> dict:
    return {
        "transaction_period": "2026-03",
        "city": "新北市",
        "district": "板橋區",
        "road": road,
        "building_type": "住宅大樓(11層含以上有電梯)" if source == "official_plvr_opendata" else "住宅大樓",
        "area_ping": 28 + index,
        "unit_price_per_ping": 55 + index,
        "total_price": (55 + index) * (28 + index),
        "building_age_years": 15,
        "floor": 8,
        "lat": None,
        "lng": None,
        "source": source,
    }


def test_new_taipei_plvr_filename_mapping() -> None:
    assert city_from_filename(Path("a_lvr_land_a.csv")) == "台北市"
    assert city_from_filename(Path("f_lvr_land_a.csv")) == "新北市"


def test_banqiao_culture_road_official_candidates_are_selected_first(monkeypatch) -> None:
    rows = [_row(index, "official_plvr_opendata", "文化路2段") for index in range(4)]
    rows += [_row(index + 10, "real_price_sample", "文化路二段") for index in range(4)]
    rows += [_row(index + 20, "official_plvr_opendata", "中山路一段") for index in range(5)]

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
            "coverage": {
                "cities": ["台北市", "新北市"],
                "districts": ["大安區", "板橋區"],
                "roads_count": 3,
                "records_count": len(rows),
            },
            "last_updated": None,
            "update_frequency_note": "",
            "source_note": "",
            "user_message": "",
        },
    )
    provider.last_query_metadata = {
        "provider_active": "postgres",
        "candidate_pool_size": len(rows),
        "query_scope": "district_pool",
        "requested_city": "新北市",
        "requested_district": "板橋區",
        "requested_road": "文化路二段",
        "db_rows_returned": len(rows),
        "query_status": "ok",
    }
    monkeypatch.setattr("services.valuation_service.get_valuation_provider", lambda: provider)

    response = client.post(
        "/valuation/estimate",
        json={
            "city": "新北市",
            "district": "板橋區",
            "road": "文化路二段",
            "building_type": "住宅大樓",
            "area_ping": 30,
            "building_age_years": 15,
            "floor": 8,
        },
    )
    payload = response.json()

    assert response.status_code == 200
    assert payload["candidate_pool_size"] == 13
    assert payload["official_same_road_count"] == 4
    assert payload["estimate_data_composition"] == "official_limited"
    assert payload["comparables"]
    assert [item["source"] for item in payload["comparables"][:4]] == ["official_plvr_opendata"] * 4
    assert all(normalize_road(item["road"]) == normalize_road("文化路二段") for item in payload["comparables"])
    assert all(item["source_label"] for item in payload["comparables"])
    assert all(item["distance_m"] is None for item in payload["comparables"])
