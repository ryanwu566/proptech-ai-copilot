"""Property Finder filtering and explainable aggregation tests."""

from datetime import UTC, datetime

from services.property_search_service import search_properties


def row(index: int, **overrides: object) -> dict[str, object]:
    current = datetime.now(UTC).strftime("%Y-%m")
    value: dict[str, object] = {
        "transaction_period": current, "city": "台北市", "district": "大安區",
        "road": "和平東路二段", "building_type": "住宅大樓", "area_ping": 30 + index,
        "total_price": 1800 + index * 20, "unit_price_per_ping": 60, "building_age_years": 15,
        "floor": 8, "source": "official_plvr_opendata",
    }
    value.update(overrides)
    return value


def test_property_search_filters_budget_city_district_and_type() -> None:
    rows = [row(0), row(1, city="新北市"), row(2, district="信義區"), row(3, building_type="公寓"), row(4, total_price=2600)]
    result = search_properties({"city": "台北市", "districts": ["大安區"], "budget_max": 2200, "building_type": "住宅大樓"}, rows)

    assert result["summary"]["matched_count"] == 1
    assert result["matched_transactions"][0]["total_price"] == 1800
    assert result["district_suggestions"][0]["city"] == "台北市"
    assert result["road_suggestions"][0]["road"] == "和平東路二段"


def test_property_search_excludes_sample_future_and_outside_window() -> None:
    rows = [
        row(0), row(1, source="real_price_sample"), row(2, source="mock_fallback"),
        row(3, transaction_period="2099-01"), row(4, transaction_period="2020-01"),
    ]
    result = search_properties({"budget_max": 3000}, rows)

    assert result["summary"]["matched_count"] == 1
    assert all(item["source_label"] == "官方 PLVR" for item in result["matched_transactions"])


def test_property_search_empty_result_is_friendly() -> None:
    result = search_properties({"budget_max": 100}, [row(0)])

    assert result["summary"]["matched_count"] == 0
    assert "沒有符合條件" in result["summary"]["message"]
    assert result["district_suggestions"] == []
    assert result["road_suggestions"] == []


def test_property_search_limit_is_capped_at_100() -> None:
    rows = [row(index, road=f"路段{index}") for index in range(140)]
    result = search_properties({"budget_max": 10000, "limit": 999}, rows)

    assert len(result["matched_transactions"]) == 100


def test_property_search_suggestion_contract_and_explainable_methodology() -> None:
    result = search_properties({"budget_min": 1500, "budget_max": 2500}, [row(index) for index in range(5)])
    district = result["district_suggestions"][0]
    road = result["road_suggestions"][0]

    assert {"sample_count", "median_total_price", "p25_total_price", "p75_total_price", "score", "reason"} <= set(district)
    assert {"road", "sample_count", "median_unit_price_per_ping", "score", "reason"} <= set(road)
    assert "不使用黑箱 AI" in result["methodology"]
