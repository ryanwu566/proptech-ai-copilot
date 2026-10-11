"""Selection trace contracts; expected prices are captured before instrumentation."""
from datetime import UTC, date, datetime
import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from services import valuation_service as vs
from services.valuation_providers.postgres_provider import PostgresValuationProvider, _normalize_row

TARGET = {"city": "台北市", "district": "大安區", "road": "和平東路二段", "building_type": "住宅大樓", "area_ping": 30, "building_age_years": 15, "floor": 8, "lat": 25.0254, "lng": 121.5434}

class FixedDatetime(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 10, 10, 12, tzinfo=UTC)

class FixedDate(date):
    @classmethod
    def today(cls):
        return cls(2026, 10, 10)

def row(i=0, **changes):
    return {"transaction_period": "2026-08", "city": "台北市", "district": "大安區", "road": "和平東路二段", "building_type": "住宅大樓", "area_ping": 30 + i, "building_age_years": 15, "floor": 8, "lat": 25.0254, "lng": 121.5434, "unit_price_per_ping": 60 + i, "total_price": (30 + i) * (60 + i), "source": "official_plvr_opendata", **changes}

def estimate(monkeypatch, rows):
    monkeypatch.setattr(vs, "datetime", FixedDatetime)
    monkeypatch.setattr(vs, "date", FixedDate)
    provider = MagicMock(spec=PostgresValuationProvider)
    provider.source = "postgres"
    provider.is_demo_data = False
    provider.data_status.return_value = {"active_source": "postgres"}
    provider.query_comparables.return_value = rows
    provider.last_query_metadata = {"query_status": "ok", "candidate_pool_size": len(rows)}
    provider.match_community.return_value = None
    monkeypatch.setattr(vs, "get_valuation_provider", lambda: provider)
    return vs.estimate_property(TARGET)

def baselines(monkeypatch):
    cases = {
        "official": [row(i) for i in range(16)],
        "unknown": [_normalize_row(row(i, building_age_years=None, floor=None, lat=None, lng=None)) for i in range(4)],
        "scope": [row(i) for i in range(4)] + [row(5, road="其他路")],
        "outlier": [row(i) for i in range(7)] + [row(8, unit_price_per_ping=400)],
        "no_data": [row(0)],
    }
    fields = ("estimate_total_price", "estimate_unit_price_per_ping", "price_range", "unit_price_distribution", "confidence", "confidence_score", "estimate_level")
    output = {}
    for name, rows in cases.items():
        result = estimate(monkeypatch, rows)
        output[name] = {key: result.get(key) for key in fields}
        output[name]["selected"] = [{key: value for key, value in r.items() if not key.startswith("_explanation")} for r in result["comparables"]]
    monkeypatch.setattr(vs, "get_valuation_provider", lambda: vs.SampleValuationProvider())
    for name, payload in {"demo_road": TARGET, "demo_community": {**TARGET, "address_text": "和平綠境"}, "demo_district": {**TARGET, "road": "其他路"}}.items():
        result = vs.estimate_property(payload)
        output[name] = {key: result.get(key) for key in fields}
        output[name]["selected"] = result["comparables"]
    return output

def test_fixed_valuation_baseline_is_identical(monkeypatch):
    expected = json.loads((Path(__file__).parent / "fixtures/comparable-valuation-baseline.json").read_text(encoding="utf-8"))
    assert baselines(monkeypatch) == expected

def test_selected_and_scope_exclusions_explain_actual_decisions(monkeypatch):
    result = estimate(monkeypatch, [row(i) for i in range(12)] + [row(20, road="其他路")])
    trace = result.get("comparable_decision_trace")
    assert trace is not None, "production selection must emit its own trace"
    assert (trace["considered_count"], trace["selected_count"], trace["excluded_count"]) == (13, 10, 3)
    assert trace["reason_counts"] == {"scope": 1, "rank_limit": 2}
    assert len(trace["selected"]) == 10
    assert trace["selected"][0]["reasons"] == ["selected"]
    assert trace["selected"][0]["dimensions"]["area"]["difference"] == 0
    assert trace["selected"][0]["dimensions"]["floor"]["role"] == "context"

def test_multiple_rejections_window_metrics_source_and_bounded_examples(monkeypatch):
    rows = [row(i) for i in range(4)] + [row(i, transaction_period="2020-01", area_ping=None) for i in range(30)] + [row(90, source="sample")]
    trace = estimate(monkeypatch, rows)["comparable_decision_trace"]
    assert trace["excluded_count"] == 31
    assert trace["reason_counts"] == {"time_window": 30, "required_metrics": 30, "official_source": 1}
    assert len(trace["excluded_examples"]) == 5
    assert trace["excluded_examples"][0]["reasons"] == ["time_window", "required_metrics"]
    assert trace["excluded_examples"][0]["dimensions"]["area"]["comparable"] is None
    assert trace["reference_period"] == "2026-10"
    assert trace["window_start"] == "2023-11"
    assert trace["provider_excluded_count"] is None

def test_no_invented_area_type_floor_parking_distance_filters(monkeypatch):
    rows = [row(i, area_ping=300, building_type="公寓", floor=1, lat=None, lng=None, parking_type="unknown") for i in range(4)]
    trace = estimate(monkeypatch, rows)["comparable_decision_trace"]
    assert trace["excluded_count"] == 0
    dimensions = trace["selected"][0]["dimensions"]
    assert dimensions["area"]["role"] == "ranking"
    assert dimensions["building_type"]["role"] == "ranking"
    assert dimensions["distance"]["comparable"] is None
    assert dimensions["distance"]["threshold"] is None
    assert dimensions["parking"]["comparable"] is None
    assert dimensions["parking"]["role"] == "context"

def test_missing_adapter_fields_do_not_become_zero_in_explanation(monkeypatch):
    trace = estimate(monkeypatch, [_normalize_row(row(i, building_age_years=None, floor=None)) for i in range(4)])["comparable_decision_trace"]
    assert trace["selected"][0]["dimensions"]["age"]["comparable"] is None
    assert trace["selected"][0]["dimensions"]["age"]["difference"] is None
    assert trace["selected"][0]["dimensions"]["floor"]["comparable"] is None

def test_trace_order_is_repeatable_and_duplicates_are_not_falsely_rejected(monkeypatch):
    rows = [row(0)] * 12
    first = estimate(monkeypatch, rows)["comparable_decision_trace"]
    assert first == estimate(monkeypatch, rows)["comparable_decision_trace"]
    assert first["reason_counts"] == {"rank_limit": 2}
    assert len({r["candidate_id"] for r in first["selected"]}) == 10

def test_no_data_trace_still_explains_rejections(monkeypatch):
    result = estimate(monkeypatch, [row(i, transaction_period="2020-01") for i in range(4)])
    assert result["estimate_total_price"] is None
    assert result["comparable_decision_trace"]["reason_counts"] == {"time_window": 4}

def test_price_outliers_are_excluded_at_the_existing_iqr_decision(monkeypatch):
    trace = estimate(monkeypatch, [row(i) for i in range(7)] + [row(8, unit_price_per_ping=400)])["comparable_decision_trace"]
    assert trace["selected_count"] == 7
    assert trace["reason_counts"] == {"price_outlier": 1}
    assert trace["outlier_bounds"] == [56.5, 70.5]
    assert trace["excluded_examples"][0]["dimensions"]["unit_price"]["threshold"] == [56.5, 70.5]

def test_community_distance_rejection_is_not_mislabeled_as_target_distance(monkeypatch):
    rows = [row(i, source="real_price_sample") for i in range(4)] + [row(10, source="real_price_sample", lat=25.1)]
    provider = vs.SampleValuationProvider()
    monkeypatch.setattr(provider, "load_transactions", lambda: tuple(rows))
    monkeypatch.setattr(vs, "get_valuation_provider", lambda: provider)
    monkeypatch.setattr(vs, "match_community", lambda *args: {**TARGET, "community_id": "test", "community_name": "Test", "confidence": "medium"})
    trace = vs.estimate_property(TARGET)["comparable_decision_trace"]
    assert trace["scope"] == "community"
    assert trace["reason_counts"] == {"community_distance": 1}
    excluded = trace["excluded_examples"][0]
    assert excluded["dimensions"]["community_distance"]["comparable"] == 8281
    assert excluded["dimensions"]["community_distance"]["threshold"] == [0, 600]

def test_green_source_missing_values_remain_unknown(monkeypatch):
    from services.compact_green_query import _map_green_row
    rows = [_map_green_row({**row(i, floor=None, building_age_years=None), "period_code": 319}) for i in range(4)]
    trace = estimate(monkeypatch, rows)["comparable_decision_trace"]
    assert trace["selected"][0]["dimensions"]["age"]["comparable"] is None
    assert trace["selected"][0]["dimensions"]["distance"]["comparable"] is None
