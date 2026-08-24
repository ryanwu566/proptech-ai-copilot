from __future__ import annotations

from datetime import date

from fastapi.testclient import TestClient
import pytest

from backend.api_main import app
from services.market_segmentation_service import (
    COMPARABLES_SQL,
    FLOOR_POSITION_RULE,
    SEGMENT_SQL,
    classify_floor_position,
    get_market_segment,
    get_market_segment_comparables,
    normalize_segment_building_type,
    percentile,
)


BASE_FILTERS = {
    "county": "新北市",
    "district": "永和區",
    "period_months": 36,
    "building_type": "住宅大樓",
    "area_min_ping": 30,
    "area_max_ping": 40,
    "age_min_years": None,
    "age_max_years": None,
    "known_age_only": False,
    "floor_position": "",
    "high_value_only": False,
    "high_value_threshold_wan": 3000,
}


class Repository:
    def __init__(self, segment_row=None, comparable_rows=None):
        self.segment_row = segment_row or {}
        self.comparable_rows = comparable_rows or []
        self.segment_filters = None
        self.comparable_filters = None

    def segment(self, filters):
        self.segment_filters = filters
        return self.segment_row

    def comparables(self, filters, limit):
        self.comparable_filters = filters
        return self.comparable_rows[:limit]


def segment_row(count: int, **overrides):
    return {
        "eligible_transaction_count": 30,
        "base_transaction_count": 20,
        "matching_transaction_count": count,
        "known_age_count": 18,
        "unknown_age_count": 2,
        "known_floor_count": 19,
        "unknown_floor_count": 1,
        "average_unit_price_per_ping": 61.25 if count else None,
        "median_unit_price_per_ping": 60 if count else None,
        "p25_unit_price_per_ping": 55 if count else None,
        "p75_unit_price_per_ping": 68 if count else None,
        "average_total_price_wan": 2200 if count else None,
        "period_min": "2024-01" if count else None,
        "period_max": "2026-08" if count else None,
        "source_updated_at": date(2026, 8, 20),
        "building_type_distribution": [
            {"category": "住宅大樓", "count": 24, "raw_values": ["住宅大樓(11層含以上有電梯)"]}
        ],
        **overrides,
    }


@pytest.mark.parametrize(
    ("raw", "normalized"),
    [
        ("住宅大樓(11層含以上有電梯)", "住宅大樓"),
        ("華廈(10層含以下有電梯)", "華廈"),
        ("公寓(5樓含以下無電梯)", "公寓"),
        ("透天厝", "透天厝"),
        ("店面(店鋪)", "店面"),
        ("其他", "其他/未分類"),
        ("辦公商業大樓", "辦公商業大樓"),
    ],
)
def test_building_type_normalization_is_transparent(raw, normalized):
    assert normalize_segment_building_type(raw) == normalized


@pytest.mark.parametrize(
    ("floor", "total", "expected"),
    [(1, 10, "low"), (33, 100, "low"), (34, 100, "middle"), (66, 100, "middle"), (67, 100, "high"), (0, 10, None), (5, 0, None), (11, 10, None)],
)
def test_floor_classification_keeps_unknown_and_invalid_values_unknown(floor, total, expected):
    assert classify_floor_position(floor, total) == expected
    assert "floor <= total_floor" in FLOOR_POSITION_RULE


def test_percentile_matches_continuous_quartile_semantics():
    assert percentile([10, 20, 30, 40], 0.25) == pytest.approx(17.5)
    assert percentile([10, 20, 30, 40], 0.5) == pytest.approx(25)
    assert percentile([10, 20, 30, 40], 0.75) == pytest.approx(32.5)


def test_segment_sql_has_bounded_filters_percentiles_and_unknown_guards():
    assert "percentile_cont(0.25)" in SEGMENT_SQL
    assert "percentile_cont(0.5)" in SEGMENT_SQL
    assert "percentile_cont(0.75)" in SEGMENT_SQL
    assert "area_ping >= request.area_min_ping" in SEGMENT_SQL
    assert "area_ping < request.area_max_ping" in SEGMENT_SQL
    assert "building_age_years > 0" in SEGMENT_SQL
    assert "transaction_period between request.period_from and request.period_to" in SEGMENT_SQL
    assert "= any(request.canonical_keys)" in SEGMENT_SQL
    assert "candidate.total_price >= request.high_value_threshold_wan" in SEGMENT_SQL
    assert "lat" not in SEGMENT_SQL.lower()
    assert "lng" not in SEGMENT_SQL.lower()


def test_segment_result_reports_low_sample_and_unknown_coverage():
    result = get_market_segment(BASE_FILTERS, Repository(segment_row(7)), as_of=date(2026, 8, 24))
    assert result["state"] == "low_sample"
    assert result["matching_transaction_count"] == 7
    assert result["unknown_age_count"] == 2
    assert result["unknown_floor_count"] == 1
    assert result["median_unit_price_per_ping"] == 60
    assert result["p25_unit_price_per_ping"] == 55
    assert result["p75_unit_price_per_ping"] == 68


def test_segment_result_reports_no_data_without_fake_zero_prices():
    result = get_market_segment(BASE_FILTERS, Repository(segment_row(0)), as_of=date(2026, 8, 24))
    assert result["state"] == "no_data"
    assert result["matching_transaction_count"] == 0
    assert result["median_unit_price_per_ping"] is None


def test_age_filter_is_partial_when_unknown_base_rows_were_excluded():
    filters = {**BASE_FILTERS, "age_min_years": 1, "age_max_years": 10}
    result = get_market_segment(filters, Repository(segment_row(12)), as_of=date(2026, 8, 24))
    assert result["state"] == "partial"
    assert result["filters_applied"]["known_age_only"] is True
    assert any("approximate imported field" in item for item in result["caveats"])


def test_comparable_sql_dedupes_and_orders_deterministically_without_a_score():
    assert "partition by coalesce(nullif(trim(matched.dedupe_key), '')" in COMPARABLES_SQL
    assert "abs(area_ping - target_area_ping) asc" in COMPARABLES_SQL
    assert "transaction_period desc" in COMPARABLES_SQL
    assert "id desc" in COMPARABLES_SQL
    assert "similarity" not in COMPARABLES_SQL.lower()
    assert " lat" not in COMPARABLES_SQL.lower()
    assert " lng" not in COMPARABLES_SQL.lower()


def test_comparables_return_actual_deltas_and_no_opaque_score():
    row = {
        "transaction_period": "2026-06",
        "county": "新北市",
        "district": "永和區",
        "road": "永和路一段",
        "raw_building_type": "住宅大樓(11層含以上有電梯)",
        "normalized_building_type": "住宅大樓",
        "area_ping": 34,
        "building_age_years": 8,
        "floor": 9,
        "total_floor": 12,
        "floor_position": "high",
        "unit_price_per_ping": 68,
        "total_price": 2312,
        "area_difference_ping": 1,
    }
    filters = {**BASE_FILTERS, "age_min_years": 6, "age_max_years": 10, "floor_position": "high"}
    result = get_market_segment_comparables(filters, repository=Repository(comparable_rows=[row]), as_of=date(2026, 8, 24))
    assert result["state"] == "low_sample"
    assert result["opaque_similarity_score"] is False
    assert result["coordinates_required"] is False
    assert "similarity_score" not in result["comparables"][0]
    assert result["comparables"][0]["area_difference_ping"] == 1
    assert result["comparables"][0]["age_difference_years"] == 0
    assert result["comparables"][0]["floor_position_relationship"] == "same"
    assert result["comparables"][0]["period_recency_months"] == 2


def test_high_value_proxy_discloses_threshold_and_nonofficial_semantics():
    filters = {**BASE_FILTERS, "high_value_only": True, "high_value_threshold_wan": 5000}
    result = get_market_segment(filters, Repository(segment_row(3)), as_of=date(2026, 8, 24))
    assert result["filters_applied"]["high_value_threshold_wan"] == 5000
    caveat = " ".join(result["caveats"])
    assert "product-defined proxy" in caveat
    assert "not an official government classification" in caveat


def test_api_additive_endpoints_and_canonical_geography(monkeypatch):
    captured = {}

    def segment(payload):
        captured["segment"] = payload
        return {"state": "no_data", "data_status": "no_data"}

    def comparables(payload, limit=8):
        captured["comparables"] = (payload, limit)
        return {"state": "no_data", "data_status": "no_data", "comparables": []}

    monkeypatch.setattr("services.market_segmentation_service.get_market_segment", segment)
    monkeypatch.setattr("services.market_segmentation_service.get_market_segment_comparables", comparables)
    client = TestClient(app)
    response = client.post("/market-insights/segments", json=BASE_FILTERS)
    assert response.status_code == 200
    assert captured["segment"]["county"] == "新北市"
    comparable_response = client.post("/market-insights/segment-comparables", json={**BASE_FILTERS, "limit": 6})
    assert comparable_response.status_code == 200
    assert captured["comparables"][1] == 6


@pytest.mark.parametrize(
    "payload",
    [
        {**BASE_FILTERS, "district": "大安區"},
        {**BASE_FILTERS, "area_min_ping": 40, "area_max_ping": 30},
        {**BASE_FILTERS, "floor_position": "penthouse"},
        {**BASE_FILTERS, "period_from": "2099-01", "period_to": "2099-02"},
        {**BASE_FILTERS, "high_value_threshold_wan": 0},
    ],
)
def test_api_rejects_invalid_filters(payload):
    response = TestClient(app).post("/market-insights/segments", json=payload)
    assert response.status_code == 422
