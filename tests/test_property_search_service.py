"""Property Finder filtering and safe aggregation tests."""

from datetime import UTC, datetime

from services.property_search_service import search_properties


def row(index: int, **overrides: object) -> dict[str, object]:
    current = datetime.now(UTC).strftime("%Y-%m")
    value: dict[str, object] = {
        "transaction_period": current, "city": "Taipei City", "district": "Central District",
        "road": "Example Road", "building_type": "Apartment", "area_ping": 30 + index,
        "total_price": 1800 + index * 20, "unit_price_per_ping": 60, "building_age_years": 15,
        "floor": 8, "source": "official_plvr_opendata",
    }
    value.update(overrides)
    return value


def test_property_search_filters_budget_city_district_and_type() -> None:
    rows = [row(0), row(1, city="Other City"), row(2, district="Other District"), row(3, building_type="Villa"), row(4, total_price=2600)]
    result = search_properties({"city": "Taipei City", "districts": ["Central District"], "budget_max": 2200, "building_type": "Apartment"}, rows)
    assert result["summary"]["matched_count"] == 1
    assert result["matched_transactions"][0]["total_price"] == 1800


def test_property_search_excludes_sample_future_and_outside_window() -> None:
    rows = [row(0), row(1, source="real_price_sample"), row(2, source="mock_fallback"), row(3, transaction_period="2099-01"), row(4, transaction_period="2020-01")]
    result = search_properties({"budget_max": 3000}, rows)
    assert result["summary"]["matched_count"] == 1
    assert all(item["source_label"] for item in result["matched_transactions"])


def test_property_search_empty_result_is_safe_and_friendly() -> None:
    result = search_properties({"budget_max": 100}, [row(0)])
    assert result["search_status"] == "no_data"
    assert result["is_actionable"] is False
    assert result["summary"]["matched_count"] == 0
    assert "官方交易資料" in result["summary"]["message"]
    assert result["district_suggestions"] == []
    assert result["road_suggestions"] == []


def test_property_search_limit_is_capped_at_100() -> None:
    rows = [row(index, road=f"Example Road {index}") for index in range(140)]
    result = search_properties({"budget_max": 10000, "limit": 999}, rows)
    assert len(result["matched_transactions"]) == 100


def test_property_search_suggestion_contract_and_explainable_methodology() -> None:
    result = search_properties({"budget_min": 1500, "budget_max": 2500}, [row(index) for index in range(5)])
    district = result["district_suggestions"][0]
    road = result["road_suggestions"][0]
    assert {"sample_count", "median_total_price", "p25_total_price", "p75_total_price", "score", "reason"} <= set(district)
    assert {"road", "sample_count", "median_unit_price_per_ping", "score", "reason"} <= set(road)
