"""Truthful road-level Market Insight evidence selection and statistics."""

from __future__ import annotations

from datetime import date

import pytest

from services.market_road_analysis import (
    analyze_market_road,
    effective_window,
    is_valid_market_road,
    normalize_market_road,
    valid_market_rows,
)


AS_OF = date(2026, 9, 21)


def _row(**overrides):
    row = {
        "source": "official_plvr_opendata",
        "transaction_period": "2026-09",
        "city": "台北市",
        "district": "大安區",
        "road": "和平東路二段",
        "unit_price_per_ping": 60,
        "total_price": 1800,
        "area_ping": 30,
        "imported_at": "2026-09-15T00:00:00+00:00",
    }
    row.update(overrides)
    return row


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (" 和平東路2段 ", "和平東路二段"),
        ("臺 灣 大 道 3 段", "台灣大道三段"),
        ("文化路二段", "文化路二段"),
        ("忠孝東路10段", "忠孝東路十段"),
    ],
)
def test_normalize_market_road_preserves_exact_section_identity(raw: str, expected: str) -> None:
    """A broken canonicalizer would split equivalent official road identities."""

    assert normalize_market_road(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "   ",
        "25.03,121.54",
        "和平東路二段100號",
        "和平東路100號信義路",
        "和平東路二段/文化路",
        "和平東路二段，100號",
        f"信{' ' * 81}義路",
    ],
)
def test_invalid_market_road_is_rejected(raw: str) -> None:
    """Invalid road input must not silently become a district query."""

    assert is_valid_market_road(raw) is False


def test_region_prefixed_road_is_not_reinterpreted_as_district_fallback() -> None:
    """A full address fragment must fail closed instead of selecting district evidence."""

    result = analyze_market_road(
        _rows(20),
        "台北市",
        "大安區",
        "台北市大安區和平東路二段",
        as_of=AS_OF,
    )

    assert result["effective_analysis_level"] == "NOT_AVAILABLE"
    assert result["fallback_reason"] == "market_road_invalid"


def test_different_roads_and_sections_do_not_collide() -> None:
    """Removing meaningful name or section characters would create fake precision."""

    values = {
        normalize_market_road(value)
        for value in ["文化路一段", "文化路二段", "文華路二段"]
    }

    assert len(values) == 3


def test_effective_window_is_exactly_36_inclusive_months() -> None:
    """An off-by-one window could wrongly promote a road to sufficient evidence."""

    assert effective_window(AS_OF) == ("2023-10", "2026-09")


def test_valid_market_rows_filters_before_threshold_count() -> None:
    """Raw, future, stale, sample, and invalid metrics must not satisfy the threshold."""

    rows = [
        _row(transaction_period="2023-10"),
        _row(transaction_period="2026-09"),
        _row(transaction_period="2026-10"),
        _row(transaction_period="2023-09"),
        _row(source="sample"),
        _row(transaction_period="2026-13"),
        _row(unit_price_per_ping=0),
        _row(unit_price_per_ping=501),
        _row(total_price=0),
        _row(area_ping=0),
        _row(district="信義區"),
    ]

    valid, quality = valid_market_rows(rows, "臺北市", "大安區", as_of=AS_OF)

    assert [row["transaction_period"] for row in valid] == ["2023-10", "2026-09"]
    assert quality["excluded_future_period_count"] == 1
    assert quality["excluded_out_of_window_count"] == 1
    assert quality["excluded_invalid_count"] == 7


def test_valid_market_rows_returns_copies_without_raw_address_fields() -> None:
    """A later response builder must not be able to leak a stored PLVR address."""

    valid, _quality = valid_market_rows(
        [_row(address_text="台北市大安區和平東路二段100號", raw_note="private")],
        "台北市",
        "大安區",
        as_of=AS_OF,
    )

    assert valid == [
        {
            "source": "official_plvr_opendata",
            "transaction_period": "2026-09",
            "city": "台北市",
            "district": "大安區",
            "road": "和平東路二段",
            "unit_price_per_ping": 60.0,
            "total_price": 1800.0,
            "area_ping": 30.0,
            "imported_at": "2026-09-15T00:00:00+00:00",
        }
    ]


def _rows(
    count: int,
    *,
    road: str = "和平東路二段",
    price: float = 80,
    period: str = "2026-09",
    city: str = "台北市",
    district: str = "大安區",
) -> list[dict]:
    return [
        _row(
            city=city,
            district=district,
            road=road,
            transaction_period=period,
            unit_price_per_ping=price,
            total_price=price * 30,
            area_ping=30,
        )
        for _index in range(count)
    ]


@pytest.mark.parametrize("road_count", [10, 11])
def test_at_least_ten_valid_road_rows_select_road(road_count: int) -> None:
    """Changing the ROAD comparison from >= to > would reject the exact boundary."""

    result = analyze_market_road(
        _rows(road_count) + _rows(4, road="信義路", price=20),
        "台北市",
        "大安區",
        "和平東路2段",
        as_of=AS_OF,
    )

    assert result["effective_analysis_level"] == "ROAD"
    assert result["road_sample_count"] == road_count
    assert result["effective_sample_count"] == road_count
    assert result["fallback_applied"] is False
    assert result["fallback_reason"] is None
    assert result["median_unit_price_per_ping"] == 80


@pytest.mark.parametrize("road_count", [0, 9])
def test_insufficient_road_rows_select_sufficient_district(road_count: int) -> None:
    """A road below ten must never retain road labels or road-only metrics."""

    result = analyze_market_road(
        _rows(road_count, price=70) + _rows(11, road="信義路", price=30),
        "台北市",
        "大安區",
        "和平東路二段",
        as_of=AS_OF,
    )

    assert result["effective_analysis_level"] == "DISTRICT"
    assert result["road_sample_count"] == road_count
    assert result["district_sample_count"] == road_count + 11
    assert result["effective_sample_count"] == road_count + 11
    assert result["fallback_applied"] is True
    assert result["fallback_reason"] == "road_sample_below_threshold"
    assert result["effective_scope_label"] == "台北市 / 大安區"
    assert result["median_unit_price_per_ping"] == 30


def test_district_below_ten_is_not_available_without_city_fallback() -> None:
    """A city-wide pool must not rescue an insufficient requested district."""

    result = analyze_market_road(
        _rows(9) + _rows(50, district="信義區", road="松仁路", price=100),
        "台北市",
        "大安區",
        "和平東路二段",
        as_of=AS_OF,
    )

    assert result["effective_analysis_level"] == "NOT_AVAILABLE"
    assert result["road_sample_count"] == 9
    assert result["district_sample_count"] == 9
    assert result["effective_sample_count"] == 0
    assert result["fallback_applied"] is True
    assert result["fallback_reason"] == "district_sample_below_threshold"
    assert result["median_unit_price_per_ping"] is None
    assert result["history"] == []


def test_old_rows_do_not_widen_the_window_to_reach_ten() -> None:
    """Adding older evidence must not alter the effective 36-month threshold."""

    result = analyze_market_road(
        _rows(9) + _rows(20, period="2023-09"),
        "台北市",
        "大安區",
        "和平東路二段",
        as_of=AS_OF,
    )

    assert result["effective_analysis_level"] == "NOT_AVAILABLE"
    assert result["road_sample_count"] == 9
    assert result["district_sample_count"] == 9
    assert result["excluded_out_of_window_count"] == 20


def test_invalid_and_future_rows_do_not_satisfy_threshold() -> None:
    """Counting raw rows instead of valid rows would fabricate ROAD sufficiency."""

    result = analyze_market_road(
        _rows(9)
        + [_row(transaction_period="2026-10")]
        + [_row(source="sample")]
        + [_row(unit_price_per_ping=0)],
        "台北市",
        "大安區",
        "和平東路二段",
        as_of=AS_OF,
    )

    assert result["effective_analysis_level"] == "NOT_AVAILABLE"
    assert result["road_sample_count"] == 9
    assert result["excluded_future_period_count"] == 1
    assert result["excluded_invalid_count"] == 2


def test_road_metrics_never_include_other_district_roads() -> None:
    """Selecting ROAD but aggregating the district pool would mislabel district data."""

    result = analyze_market_road(
        _rows(10, price=80) + _rows(40, road="信義路", price=20),
        "台北市",
        "大安區",
        "和平東路二段",
        as_of=AS_OF,
    )

    assert result["median_unit_price_per_ping"] == 80
    assert result["transaction_count"] == 10
    assert result["district_sample_count"] == 50


def test_requested_road_remains_separate_after_district_fallback() -> None:
    """Overwriting the request scope would hide why fallback occurred."""

    result = analyze_market_road(
        _rows(7) + _rows(5, road="信義路"),
        "臺北市",
        "大安區",
        " 和平東路2段 ",
        as_of=AS_OF,
    )

    assert result["requested_scope"] == "ROAD"
    assert result["requested_city"] == "台北市"
    assert result["requested_district"] == "大安區"
    assert result["requested_road"] == "和平東路2段"
    assert result["normalized_road"] == "和平東路二段"
    assert result["effective_analysis_level"] == "DISTRICT"


def test_effective_scope_statistics_are_complete_and_address_free() -> None:
    """Road statistics must be directly supported and safe for the public response."""

    rows = [
        _row(
            transaction_period="2026-01" if index < 4 else "2026-02" if index < 7 else "2026-03",
            unit_price_per_ping=(index + 1) * 10,
            total_price=(index + 1) * 300,
            area_ping=21 + index,
            address_text=f"private-{index}",
        )
        for index in range(10)
    ]

    result = analyze_market_road(rows, "台北市", "大安區", "和平東路二段", as_of=AS_OF)

    assert result["period_min"] == "2026-01"
    assert result["period_max"] == "2026-03"
    assert result["newest_effective_period"] == "2026-03"
    assert result["median_unit_price_per_ping"] == 55
    assert result["p25_unit_price_per_ping"] == 32.5
    assert result["p75_unit_price_per_ping"] == 77.5
    assert result["median_total_price"] == 1650
    assert result["median_area_ping"] == 25.5
    assert [point["transaction_count"] for point in result["monthly_series"]] == [4, 3, 3]
    assert result["yearly_series"] == [
        {
            "year": "2026",
            "median_unit_price_per_ping": 55.0,
            "transaction_count": 10,
            "yoy_change_percent": None,
        }
    ]
    assert result["volatility"] is not None
    assert "address_text" not in str(result)
    assert "private-" not in str(result)


def test_yoy_requires_ten_rows_in_each_of_two_latest_years() -> None:
    """One sufficient overall sample must not imply supported YoY."""

    supported = analyze_market_road(
        _rows(10, period="2025-06", price=50) + _rows(10, period="2026-06", price=60),
        "台北市",
        "大安區",
        "和平東路二段",
        as_of=AS_OF,
    )
    unsupported = analyze_market_road(
        _rows(9, period="2025-06", price=50) + _rows(10, period="2026-06", price=60),
        "台北市",
        "大安區",
        "和平東路二段",
        as_of=AS_OF,
    )

    assert supported["year_over_year_change"] == pytest.approx(0.2)
    assert supported["yearly_series"][-1]["yoy_change_percent"] == 20.0
    assert unsupported["year_over_year_change"] is None
    assert unsupported["yearly_series"][-1]["yoy_change_percent"] is None


def test_yoy_requires_consecutive_calendar_years() -> None:
    """A gap in annual evidence must not be labeled as year-over-year change."""

    result = analyze_market_road(
        _rows(10, period="2024-06", price=50) + _rows(10, period="2026-06", price=60),
        "台北市",
        "大安區",
        "和平東路二段",
        as_of=AS_OF,
    )

    assert result["year_over_year_change"] is None
    assert result["yearly_series"][-1]["yoy_change_percent"] is None


def test_volatility_requires_three_monthly_observations() -> None:
    """Ten records in only two months must not fabricate volatility."""

    result = analyze_market_road(
        _rows(5, period="2026-01", price=50) + _rows(5, period="2026-02", price=60),
        "台北市",
        "大安區",
        "和平東路二段",
        as_of=AS_OF,
    )

    assert result["effective_analysis_level"] == "ROAD"
    assert result["volatility"] is None
