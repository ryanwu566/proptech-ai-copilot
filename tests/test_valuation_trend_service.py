from datetime import UTC, datetime

from services.valuation_trend_service import _shift_month, analyze_valuation_trend


PAYLOAD = {
    "city": "台北市",
    "district": "大安區",
    "road": "和平東路二段",
    "building_type": "住宅大樓",
    "area_ping": 30,
    "building_age_years": 15,
    "horizon_months": [6, 12, 36],
}


def row(index: int, *, source: str = "official_plvr_opendata", road: str = "和平東路二段", building_type: str = "住宅大樓", period: str | None = None) -> dict:
    current = datetime.now(UTC).strftime("%Y-%m")
    return {
        "transaction_period": period or _shift_month(current, -(index % 18)),
        "city": "台北市",
        "district": "大安區",
        "road": road,
        "building_type": building_type,
        "area_ping": 28 + index % 5,
        "building_age_years": 15,
        "unit_price_per_ping": 70 + index % 9,
        "total_price": 2200,
        "source": source,
    }


def test_trend_uses_only_official_and_excludes_future() -> None:
    current = datetime.now(UTC).strftime("%Y-%m")
    future = _shift_month(current, 1)
    too_old = _shift_month(current, -40)
    rows = [row(index) for index in range(35)]
    rows += [row(50, source="real_price_sample"), row(51, source="mock_fallback"), row(52, period=future), row(53, period=too_old)]
    result = analyze_valuation_trend(PAYLOAD, rows)
    assert result["data_scope"] == "road"
    assert result["sample_count"] == 35
    assert result["period_max"] < future
    assert result["raw_period_min"] == too_old
    assert result["raw_period_max"] == future
    assert result["effective_period_min"] == result["period_min"]
    assert result["effective_period_max"] == result["period_max"]
    assert result["excluded_future_period_count"] == 1
    assert result["excluded_out_of_window_count"] == 1
    assert result["source"] == "official_plvr_opendata"


def test_trend_falls_back_to_district_type() -> None:
    rows = [row(index) for index in range(10)]
    rows += [row(index + 20, road="復興南路二段") for index in range(100)]
    result = analyze_valuation_trend(PAYLOAD, rows)
    assert result["data_scope"] == "district_type"
    assert result["sample_count"] == 110


def test_trend_low_confidence_and_scenarios_are_bounded() -> None:
    result = analyze_valuation_trend(PAYLOAD, [row(index) for index in range(12)])
    assert result["confidence_level"] == "low"
    assert set(result["scenario_forecast"]) == {"conservative", "base", "optimistic"}
    rates = [item["growth_rate_used"] for values in result["scenario_forecast"].values() for item in values]
    assert all(-0.10 <= rate <= 0.10 for rate in rates)
    assert result["trend_annualized_rate"] <= 0.10


def test_trend_falls_back_to_district_when_type_is_insufficient() -> None:
    rows = [row(index, road="復興南路二段", building_type="公寓") for index in range(40)]
    result = analyze_valuation_trend(PAYLOAD, rows)
    assert result["data_scope"] == "district"
    assert result["district_sample_count"] == 40
