from services.valuation_providers.postgres_provider import PostgresValuationProvider, _normalize_row
from services.valuation_service import estimate_property, normalize_building_type


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


def test_limited_official_records_are_kept_and_capped(monkeypatch) -> None:
    rows = [row(index, "official_plvr_opendata") for index in range(4)]
    rows += [row(index + 10, "real_price_sample") for index in range(4)]
    rows += [row(index + 20, "official_plvr_opendata", road="建國南路一段") for index in range(6)]
    fake_postgres(monkeypatch, rows)
    result = estimate_property(PAYLOAD)
    assert result["estimate_data_composition"] == "official_limited"
    assert result["estimate_source_label"] == "官方 PLVR（樣本較少）+ 展示樣本補充"
    assert result["estimate_level"] == "road"
    assert result["official_same_road_count"] == 4
    assert result["official_same_district_count"] == 10
    assert result["sample_same_road_count"] == 4
    assert result["confidence_score"] <= 70
    assert [item["source"] for item in result["comparables"][:4]] == ["official_plvr_opendata"] * 4
    assert all(item["road"] == "和平東路二段" for item in result["comparables"])
    assert all(item["source_label"] for item in result["comparables"])
    assert "官方同路段資料較少" in result["confidence_reason"]


def test_mixed_non_road_data_confidence_is_capped(monkeypatch) -> None:
    rows = [row(index, "official_plvr_opendata", road="復興南路二段") for index in range(4)]
    rows += [row(index + 10, "real_price_sample", road="新生南路二段") for index in range(4)]
    fake_postgres(monkeypatch, rows)
    result = estimate_property(PAYLOAD)
    assert result["estimate_data_composition"] == "mixed"
    assert result["confidence_score"] <= 80


def test_official_district_used_only_without_same_road_official_or_sample(monkeypatch) -> None:
    rows = [row(index, "official_plvr_opendata", road="建國南路一段") for index in range(6)]
    fake_postgres(monkeypatch, rows)
    result = estimate_property(PAYLOAD)
    assert result["estimate_data_composition"] == "official_district"
    assert result["estimate_level"] == "district"
    assert result["official_same_road_count"] == 0
    assert result["official_same_district_count"] == 6
    assert result["sample_same_road_count"] == 0
    assert result["confidence_score"] <= 60
    assert "指定路段官方資料不足" in result["confidence_reason"]


def test_same_road_sample_beats_district_official_when_no_same_road_official(monkeypatch) -> None:
    rows = [row(index, "official_plvr_opendata", road="建國南路一段") for index in range(4)]
    rows += [row(index + 10, "real_price_sample") for index in range(4)]
    fake_postgres(monkeypatch, rows)
    result = estimate_property(PAYLOAD)
    assert result["estimate_data_composition"] == "sample"
    assert result["estimate_level"] == "road"
    assert all(item["road"] == "和平東路二段" for item in result["comparables"])
    assert all(item["source"] == "real_price_sample" for item in result["comparables"])


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


def test_normalized_building_type_matches_official_label(monkeypatch) -> None:
    rows = [row(index, "official_plvr_opendata") for index in range(4)]
    rows[0]["building_type"] = "住宅大樓(11層含以上有電梯)"
    rows += [row(index + 10, "real_price_sample") for index in range(4)]
    fake_postgres(monkeypatch, rows)
    result = estimate_property(PAYLOAD)
    official = next(item for item in result["comparables"] if item["building_type"].startswith("住宅大樓("))
    assert official["normalized_building_type"] == "住宅大樓"
    assert "同建物類型" in official["note"]
    assert normalize_building_type("華廈(10層含以下有電梯)") == "華廈"
