"""API tests for the Market Insight read model bridge."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.api_main import app


client = TestClient(app)


def _road_market_result(*, level: str = "ROAD", data_status: str = "available") -> dict:
    available = data_status == "available"
    return {
        "city": "台北市",
        "county": "台北市",
        "district": "大安區",
        "period": "2026-09" if available else None,
        "average_unit_price": 75.0 if available else None,
        "avg_price_per_ping": 75.0 if available else None,
        "transaction_count": 10 if available else None,
        "transaction_volume": 10 if available else None,
        "record_count": 10 if available else None,
        "history": [{"period": "2026-09", "average_unit_price": 75.0, "transaction_count": 10}] if available else [],
        "summary": "road analysis",
        "source_name": "Official PLVR OpenData aggregate",
        "source_updated_at": "2026-09-15",
        "coverage_status": "covered",
        "data_status": data_status,
        "caveat": "historical reference only",
        "disclaimer": "historical reference only",
        "requested_scope": "ROAD",
        "requested_city": "台北市",
        "requested_district": "大安區",
        "requested_road": "和平東路2段",
        "normalized_road": "和平東路二段",
        "road_minimum_sample": 10,
        "analysis_level": level,
        "effective_analysis_level": level,
        "effective_scope_label": "台北市 / 大安區 / 和平東路二段" if level == "ROAD" else "",
        "effective_sample_count": 10 if available else 0,
        "road_sample_count": 10 if available else 3,
        "district_sample_count": 20 if available else 8,
        "fallback_applied": level != "ROAD",
        "fallback_reason": None if level == "ROAD" else "district_sample_below_threshold",
        "period_min": "2026-01" if available else None,
        "period_max": "2026-09" if available else None,
        "newest_effective_period": "2026-09" if available else None,
        "median_unit_price_per_ping": 74.0 if available else 999.0,
        "p25_unit_price_per_ping": 68.0 if available else 998.0,
        "p75_unit_price_per_ping": 82.0 if available else 1000.0,
        "median_total_price": 2200.0 if available else 9999.0,
        "median_area_ping": 30.0 if available else 999.0,
        "monthly_series": [{"period": "2026-09", "median_unit_price_per_ping": 74.0, "transaction_count": 10}] if available else [{"private": True}],
        "yearly_series": [{"year": "2026", "median_unit_price_per_ping": 74.0, "transaction_count": 10, "yoy_change_percent": None}] if available else [{"private": True}],
        "year_over_year_change": None,
        "volatility": None,
        "freshness_status": "fresh",
        "freshness_reason_code": "freshness_confirmed",
        "excluded_future_period_count": 1,
        "excluded_out_of_window_count": 2,
        "excluded_invalid_count": 3,
        "address_text": "must never leak",
    }


def test_market_query_accepts_road_and_exposes_separate_requested_and_effective_scopes(monkeypatch) -> None:
    """Rejecting or stripping road scope would make truthful ROAD analysis impossible."""

    from services import market_insight_service

    seen: dict[str, str | None] = {}

    def fake_summary(city: str, district: str, period: str | None = None, road: str | None = None):
        seen.update({"city": city, "district": district, "period": period, "road": road})
        return _road_market_result()

    monkeypatch.setattr(market_insight_service, "get_market_summary", fake_summary)

    response = client.post(
        "/market-insights/query",
        json={"county": "台北市", "district": "大安區", "road": "和平東路2段"},
    )

    assert response.status_code == 200
    assert seen == {"city": "台北市", "district": "大安區", "period": None, "road": "和平東路2段"}
    payload = response.json()
    assert payload["requested_scope"] == "ROAD"
    assert payload["requested_road"] == "和平東路2段"
    assert payload["normalized_road"] == "和平東路二段"
    assert payload["effective_analysis_level"] == "ROAD"
    assert payload["road_sample_count"] == 10
    assert payload["median_unit_price_per_ping"] == 74.0
    assert "address_text" not in payload


def test_not_available_road_response_keeps_explanation_but_clears_all_metrics(monkeypatch) -> None:
    """Residual road metrics in NOT_AVAILABLE would fabricate a market result."""

    from services import market_insight_service

    monkeypatch.setattr(
        market_insight_service,
        "get_market_summary",
        lambda *_args, **_kwargs: _road_market_result(level="NOT_AVAILABLE", data_status="no_data"),
    )

    payload = client.post(
        "/market-insights/query",
        json={"county": "台北市", "district": "大安區", "road": "和平東路二段"},
    ).json()

    assert payload["effective_analysis_level"] == "NOT_AVAILABLE"
    assert payload["road_sample_count"] == 3
    assert payload["district_sample_count"] == 8
    assert payload["fallback_reason"] == "district_sample_below_threshold"
    for field in (
        "average_unit_price",
        "transaction_count",
        "median_unit_price_per_ping",
        "p25_unit_price_per_ping",
        "p75_unit_price_per_ping",
        "median_total_price",
        "median_area_ping",
    ):
        assert payload[field] is None
    assert payload["history"] == []
    assert payload["monthly_series"] == []
    assert payload["yearly_series"] == []


@pytest.mark.parametrize(
    "road",
    [
        "",
        "   ",
        "25.03,121.54",
        "和平東路二段100號",
        "和平東路100號信義路",
        "台北市大安區和平東路二段",
        "和平東路二段/文化路",
        "路" * 81,
        f"信{' ' * 81}義路",
    ],
)
def test_market_query_rejects_invalid_road_without_calling_service(monkeypatch, road: str) -> None:
    """Invalid road input must not silently execute district analysis."""

    from services import market_insight_service

    called = False

    def fake_summary(*_args, **_kwargs):
        nonlocal called
        called = True
        return _road_market_result()

    monkeypatch.setattr(market_insight_service, "get_market_summary", fake_summary)

    response = client.post(
        "/market-insights/query",
        json={"county": "台北市", "district": "大安區", "road": road},
    )

    assert response.status_code == 422
    assert called is False


def test_malformed_road_result_preserves_requested_scope_as_not_available(monkeypatch) -> None:
    """A defensive sanitizer must not erase the validated road on contract failure."""

    from services import market_insight_service

    monkeypatch.setattr(
        market_insight_service,
        "get_market_summary",
        lambda *_args, **_kwargs: {"coverage_status": "covered", "data_status": "available"},
    )

    payload = client.post(
        "/market-insights/query",
        json={"county": "台北市", "district": "大安區", "road": "和平東路2段"},
    ).json()

    assert payload["data_status"] == "no_data"
    assert payload["reason_code"] == "market_result_contract_invalid"
    assert payload["requested_scope"] == "ROAD"
    assert payload["requested_city"] == "台北市"
    assert payload["requested_district"] == "大安區"
    assert payload["requested_road"] == "和平東路2段"
    assert payload["normalized_road"] == "和平東路二段"
    assert payload["effective_analysis_level"] == "NOT_AVAILABLE"
    assert payload["history"] == []
    assert payload["monthly_series"] == []
    assert payload["yearly_series"] == []


def test_market_query_bounds_unknown_fallback_reason(monkeypatch) -> None:
    """Provider text must not leak through the fallback explanation field."""

    from services import market_insight_service

    unsafe = _road_market_result(level="DISTRICT")
    unsafe.update(
        {
            "fallback_applied": True,
            "fallback_reason": "private database explanation",
            "effective_scope_label": "台北市 / 大安區",
        }
    )
    monkeypatch.setattr(market_insight_service, "get_market_summary", lambda *_args, **_kwargs: unsafe)

    payload = client.post(
        "/market-insights/query",
        json={"county": "台北市", "district": "大安區", "road": "和平東路二段"},
    ).json()

    assert payload["fallback_reason"] == "market_road_unknown"
    assert "private database" not in str(payload)


def test_unexpected_road_failure_preserves_safe_requested_scope(monkeypatch) -> None:
    """Technical failure must not erase which validated road was requested."""

    from services import market_insight_service

    def fail(*_args, **_kwargs):
        raise RuntimeError("private provider detail")

    monkeypatch.setattr(market_insight_service, "get_market_summary", fail)

    payload = client.post(
        "/market-insights/query",
        json={"county": "台北市", "district": "大安區", "road": "和平東路2段"},
    ).json()

    assert payload["data_status"] == "unavailable"
    assert payload["requested_scope"] == "ROAD"
    assert payload["requested_road"] == "和平東路2段"
    assert payload["normalized_road"] == "和平東路二段"
    assert payload["effective_analysis_level"] == "NOT_AVAILABLE"
    assert payload["fallback_reason"] == "market_road_unknown"
    assert payload["monthly_series"] == []
    assert payload["yearly_series"] == []
    assert "private provider detail" not in str(payload)


def test_market_status_endpoint_uses_safe_read_model_metadata(monkeypatch) -> None:
    from services import market_insight_service

    monkeypatch.setattr(
        market_insight_service,
        "get_market_status",
        lambda: {
            "read_model_status": "ready",
            "data_status": "available",
            "coverage_status": "partial",
            "source_name": "Official PLVR OpenData aggregate",
            "source_updated_at": "2025-03-05",
            "available_county_count": 1,
            "available_district_count": 2,
            "earliest_period": "2025-01",
            "latest_period": "2025-02",
            "built_at": "2025-03-06T00:00:00+00:00",
            "caveat": "market caveat",
        },
    )

    response = client.get("/market-insights/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["read_model_status"] == "ready"
    assert payload["data_status"] == "available"
    assert "database_url" not in payload
    assert "raw_payload" not in payload


def test_market_catalog_endpoint_returns_available_counties(monkeypatch) -> None:
    from services import market_insight_service

    monkeypatch.setattr(
        market_insight_service,
        "get_market_catalog",
        lambda: {
            "read_model_status": "ready",
            "data_status": "available",
            "coverage_status": "partial",
            "source_name": "Official PLVR OpenData aggregate",
            "source_updated_at": "2025-03-05",
            "available_counties": ["Demo County"],
            "available_county_count": 1,
            "available_district_count": 2,
            "earliest_period": "2025-01",
            "latest_period": "2025-02",
            "built_at": "2025-03-06T00:00:00+00:00",
            "caveat": "market caveat",
        },
    )

    response = client.get("/market-insights/catalog")

    assert response.status_code == 200
    payload = response.json()
    assert payload["available_counties"] == ["Demo County"]
    assert "regions" not in payload


def test_market_regions_endpoint_filters_by_county(monkeypatch) -> None:
    from services import market_insight_service

    seen: dict[str, str] = {}

    def fake_regions(county: str = ""):
        seen["county"] = county
        return {
            "read_model_status": "ready",
            "regions": [{"city": "Demo County", "county": "Demo County", "district": "North", "period": "2025-02"}],
            "data_status": "available",
            "coverage_status": "partial",
            "source_name": "Official PLVR OpenData aggregate",
            "source_updated_at": "2025-03-05",
            "available_county_count": 1,
            "available_district_count": 1,
            "earliest_period": "2025-02",
            "latest_period": "2025-02",
            "built_at": "2025-03-06T00:00:00+00:00",
            "caveat": "market caveat",
        }

    monkeypatch.setattr(market_insight_service, "list_market_regions", fake_regions)

    response = client.get("/market-insights/regions?county=Demo%20County")

    assert response.status_code == 200
    assert seen == {"county": "Demo County"}
    assert response.json()["regions"][0]["district"] == "North"


def test_market_query_accepts_county_alias_and_returns_history(monkeypatch) -> None:
    from services import market_insight_service

    seen: dict[str, str | None] = {}

    def fake_summary(city: str, district: str, period: str | None = None):
        seen.update({"city": city, "district": district, "period": period})
        return {
            "city": city,
            "county": city,
            "district": district,
            "period": period,
            "average_unit_price": 72.5,
            "avg_price_per_ping": 72.5,
            "transaction_count": 3,
            "transaction_volume": 3,
            "record_count": 3,
            "history": [{"period": "2025-02", "average_unit_price": 72.5, "transaction_count": 3}],
            "summary": "aggregate ready",
            "source_name": "Official PLVR OpenData aggregate",
            "source_updated_at": "2025-03-05",
            "coverage_status": "partial",
            "data_status": "available",
            "caveat": "market caveat",
            "disclaimer": "market caveat",
        }

    monkeypatch.setattr(market_insight_service, "get_market_summary", fake_summary)

    response = client.post(
        "/market-insights/query",
        json={"county": "Demo County", "district": "North", "period": "2025-02"},
    )

    assert response.status_code == 200
    assert seen == {"city": "Demo County", "district": "North", "period": "2025-02"}
    payload = response.json()
    assert payload["data_status"] == "available"
    assert payload["history"][0]["period"] == "2025-02"
    assert "address_text" not in payload
    assert "raw_error" not in payload


def test_market_query_allows_county_only_direct_query(monkeypatch) -> None:
    from services import market_insight_service

    seen: dict[str, str | None] = {}

    def fake_summary(city: str, district: str = "", period: str | None = None):
        seen.update({"city": city, "district": district, "period": period})
        return {
            "city": city,
            "county": city,
            "district": district,
            "period": "2025-02",
            "average_unit_price": 70.0,
            "avg_price_per_ping": 70.0,
            "transaction_count": 5,
            "transaction_volume": 5,
            "record_count": 5,
            "history": [{"period": "2025-02", "average_unit_price": 70.0, "transaction_count": 5}],
            "summary": "direct aggregate ready",
            "source_name": "Official PLVR OpenData aggregate",
            "source_updated_at": "2025-03-05",
            "coverage_status": "partial",
            "data_status": "available",
            "caveat": "market caveat",
            "disclaimer": "market caveat",
        }

    monkeypatch.setattr(market_insight_service, "get_market_summary", fake_summary)

    response = client.post("/market-insights/query", json={"county": "Demo County"})

    assert response.status_code == 200
    assert seen == {"city": "Demo County", "district": "", "period": None}
    payload = response.json()
    assert payload["data_status"] == "available"
    assert payload["district"] == ""
    assert "real_price_transactions" not in str(payload)


def test_market_query_blank_county_returns_safe_unavailable(monkeypatch) -> None:
    from services import market_insight_service

    called = {"summary": False}
    monkeypatch.setattr(
        market_insight_service,
        "get_market_summary",
        lambda *_args, **_kwargs: called.update(summary=True),
    )

    response = client.post("/market-insights/query", json={"county": "   ", "district": "North"})

    assert response.status_code == 200
    payload = response.json()
    assert called == {"summary": False}
    assert payload["data_status"] == "unavailable"
    assert payload["average_unit_price"] is None
    assert "raw_error" not in payload


def test_market_query_preserves_no_data_state(monkeypatch) -> None:
    from services import market_insight_service

    def fake_summary(city: str, district: str = "", period: str | None = None):
        return {
            "city": city,
            "county": city,
            "district": district,
            "period": None,
            "average_unit_price": None,
            "avg_price_per_ping": None,
            "transaction_count": None,
            "transaction_volume": None,
            "record_count": None,
            "history": [],
            "summary": "no data",
            "source_name": "Official PLVR OpenData aggregate",
            "source_updated_at": None,
            "coverage_status": "partial",
            "data_status": "no_data",
            "caveat": "market caveat",
            "disclaimer": "market caveat",
        }

    monkeypatch.setattr(market_insight_service, "get_market_summary", fake_summary)

    response = client.post("/market-insights/query", json={"county": "Demo County", "district": "Missing"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["data_status"] == "no_data"
    assert payload["average_unit_price"] is None
    assert payload["history"] == []
    assert "raw_error" not in payload


def test_market_query_preserves_unavailable_state(monkeypatch) -> None:
    from services import market_insight_service

    def fake_summary(city: str, district: str = "", period: str | None = None):
        return {
            "city": city,
            "county": city,
            "district": district,
            "period": None,
            "average_unit_price": None,
            "avg_price_per_ping": None,
            "transaction_count": None,
            "transaction_volume": None,
            "record_count": None,
            "history": [],
            "summary": "unavailable",
            "source_name": None,
            "source_updated_at": None,
            "coverage_status": "unknown",
            "data_status": "unavailable",
            "caveat": "market caveat",
            "disclaimer": "market caveat",
        }

    monkeypatch.setattr(market_insight_service, "get_market_summary", fake_summary)

    response = client.post("/market-insights/query", json={"county": "Demo County"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["data_status"] == "unavailable"
    assert payload["data_status"] != "no_data"
    assert payload["average_unit_price"] is None
    assert payload["history"] == []


def test_market_query_preserves_partial_safe_evidence_without_zero_fill(monkeypatch) -> None:
    from services import market_insight_service

    monkeypatch.setattr(
        market_insight_service,
        "get_market_summary",
        lambda *_args, **_kwargs: {
            "city": "Demo County",
            "county": "Demo County",
            "district": "North",
            "period": "2026-06",
            "average_unit_price": 68.5,
            "avg_price_per_ping": 68.5,
            "transaction_count": None,
            "transaction_volume": None,
            "record_count": 3,
            "history": [{"period": "2026-06", "average_unit_price": 68.5, "transaction_count": 3}],
            "summary": "partial aggregate",
            "source_name": "Official PLVR aggregate",
            "source_updated_at": "2026-07-01",
            "coverage_status": "partial",
            "data_status": "incomplete",
            "sample_status": "limited",
            "caveat": "Some fields are unavailable.",
            "disclaimer": "Regional reference only.",
        },
    )

    response = client.post("/market-insights/query", json={"county": "Demo County", "district": "North"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["data_status"] == "incomplete"
    assert payload["coverage_status"] == "partial"
    assert payload["average_unit_price"] == 68.5
    assert payload["transaction_count"] is None
    assert payload["record_count"] == 3
    assert payload["sample_status"] == "limited"


def test_market_query_available_requires_complete_positive_contract(monkeypatch) -> None:
    from services import market_insight_service

    monkeypatch.setattr(
        market_insight_service,
        "get_market_summary",
        lambda *_args, **_kwargs: {
            "city": "Demo County",
            "county": "Demo County",
            "district": "North",
            "period": "2025-02",
            "average_unit_price": 70.0,
            "avg_price_per_ping": 70.0,
            "transaction_count": 4,
            "transaction_volume": 4,
            "record_count": 4,
            "history": [],
            "summary": "aggregate ready",
            "source_name": "Official PLVR OpenData aggregate",
            "source_updated_at": "2025-03-05",
            "coverage_status": "covered",
            "data_status": "available",
            "caveat": "market caveat",
            "disclaimer": "market caveat",
            "raw_payload": "must not leak",
        },
    )

    response = client.post("/market-insights/query", json={"county": "Demo County", "district": "North"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["data_status"] == "available"
    assert payload["coverage_status"] == "covered"
    assert payload["average_unit_price"] == payload["avg_price_per_ping"]
    assert payload["transaction_count"] == payload["transaction_volume"]
    assert "raw_payload" not in payload


def test_market_query_invalid_available_degrades_to_no_data_without_zero_metrics(monkeypatch) -> None:
    from services import market_insight_service

    monkeypatch.setattr(
        market_insight_service,
        "get_market_summary",
        lambda *_args, **_kwargs: {
            "city": "Demo County",
            "county": "Demo County",
            "district": "North",
            "average_unit_price": float("nan"),
            "avg_price_per_ping": float("nan"),
            "transaction_count": 0,
            "transaction_volume": 0,
            "record_count": 0,
            "history": [],
            "source_name": "Official PLVR OpenData aggregate",
            "coverage_status": "covered",
            "data_status": "available",
        },
    )

    payload = client.post("/market-insights/query", json={"county": "Demo County", "district": "North"}).json()

    assert payload["data_status"] == "no_data"
    assert payload["coverage_status"] == "covered"
    assert payload["average_unit_price"] is None
    assert payload["transaction_count"] is None
    assert payload["transaction_volume"] is None
    assert payload["record_count"] is None
    assert payload["history"] == []
    assert "0" not in payload["summary"]


def test_market_query_unavailable_state_is_not_rewritten_to_no_data(monkeypatch) -> None:
    from services import market_insight_service

    monkeypatch.setattr(
        market_insight_service,
        "get_market_summary",
        lambda *_args, **_kwargs: {
            "city": "Demo County",
            "county": "Demo County",
            "district": "North",
            "average_unit_price": None,
            "avg_price_per_ping": None,
            "transaction_count": None,
            "transaction_volume": None,
            "record_count": None,
            "history": [],
            "summary": "internal details must not leak",
            "source_name": None,
            "coverage_status": "coverage_unknown",
            "data_status": "unavailable",
            "database_url": "must not leak",
        },
    )

    response = client.post("/market-insights/query", json={"county": "Demo County", "district": "North"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["data_status"] == "unavailable"
    assert payload["coverage_status"] == "coverage_unknown"
    assert payload["history"] == []
    assert "database_url" not in payload
    assert "internal details" not in str(payload)


def test_refresh_requires_configured_token_before_db_work(monkeypatch) -> None:
    from services import market_insight_service

    called = {"refresh": False}
    monkeypatch.delenv("MARKET_READ_MODEL_REFRESH_TOKEN", raising=False)
    monkeypatch.setattr(
        market_insight_service,
        "refresh_market_read_model",
        lambda: called.update(refresh=True),
    )

    response = client.post("/market-insights/refresh")

    assert response.status_code == 503
    assert called == {"refresh": False}
    assert response.json()["reason_code"] == "refresh_runtime_not_configured"
    assert set(response.json()) == {"status", "data_status", "coverage_status", "built_at", "message", "reason_code"}


def test_refresh_rejects_wrong_token_before_db_work(monkeypatch) -> None:
    from services import market_insight_service

    called = {"refresh": False}
    monkeypatch.setenv("MARKET_READ_MODEL_REFRESH_TOKEN", "expected")
    monkeypatch.setattr(
        market_insight_service,
        "refresh_market_read_model",
        lambda: called.update(refresh=True),
    )

    response = client.post("/market-insights/refresh", headers={"X-Market-Read-Model-Refresh-Token": "wrong"})

    assert response.status_code == 403
    assert called == {"refresh": False}
    assert "reason_code" not in response.json()


def test_refresh_success_response_is_safe(monkeypatch) -> None:
    from services import market_insight_service

    monkeypatch.setenv("MARKET_READ_MODEL_REFRESH_TOKEN", "expected")
    monkeypatch.setattr(
        market_insight_service,
        "refresh_market_read_model",
        lambda: {
            "status": "resolved",
            "data_status": "available",
            "coverage_status": "partial",
            "built_at": "2025-03-06T00:00:00+00:00",
            "message": "市場 read model 已完成刷新。",
        },
    )

    response = client.post("/market-insights/refresh", headers={"X-Market-Read-Model-Refresh-Token": "expected"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "resolved"
    assert "available_county_count" not in payload
    assert "real_price_transactions" not in str(payload)


def test_refresh_service_503_uses_allowlisted_reason(monkeypatch) -> None:
    from services import market_insight_service

    monkeypatch.setenv("MARKET_READ_MODEL_REFRESH_TOKEN", "expected")
    monkeypatch.setattr(
        market_insight_service,
        "refresh_market_read_model",
        lambda: {
            "status": "unavailable",
            "data_status": "unavailable",
            "coverage_status": "unknown",
            "built_at": None,
            "message": "internal details must be replaced",
            "reason_code": "read_model_no_eligible_source_records",
            "database_url": "must not leak",
        },
    )

    response = client.post("/market-insights/refresh", headers={"X-Market-Read-Model-Refresh-Token": "expected"})

    assert response.status_code == 503
    payload = response.json()
    assert payload["reason_code"] == "read_model_no_eligible_source_records"
    assert set(payload) == {"status", "data_status", "coverage_status", "built_at", "message", "reason_code"}
    assert "database_url" not in payload
    assert "internal details" not in str(payload)


def test_refresh_service_unknown_reason_is_safely_normalized(monkeypatch) -> None:
    from services import market_insight_service

    monkeypatch.setenv("MARKET_READ_MODEL_REFRESH_TOKEN", "expected")
    monkeypatch.setattr(
        market_insight_service,
        "refresh_market_read_model",
        lambda: {
            "status": "unavailable",
            "reason_code": "raw_database_exception",
        },
    )

    response = client.post("/market-insights/refresh", headers={"X-Market-Read-Model-Refresh-Token": "expected"})

    assert response.status_code == 503
    assert response.json()["reason_code"] == "unknown_safe_failure"


def test_refresh_unclassified_exception_is_safe_failure(monkeypatch) -> None:
    from services import market_insight_service

    monkeypatch.setenv("MARKET_READ_MODEL_REFRESH_TOKEN", "expected")

    def fail_refresh():
        raise RuntimeError("raw exception must not leak")

    monkeypatch.setattr(market_insight_service, "refresh_market_read_model", fail_refresh)

    response = client.post("/market-insights/refresh", headers={"X-Market-Read-Model-Refresh-Token": "expected"})

    assert response.status_code == 503
    payload = response.json()
    assert payload["reason_code"] == "unknown_safe_failure"
    assert "raw exception" not in str(payload)


def test_market_coverage_operator_routes_require_existing_token(monkeypatch) -> None:
    from services import plvr_market_aggregate_service

    called = {"bootstrap": False}
    monkeypatch.setenv("MARKET_READ_MODEL_REFRESH_TOKEN", "expected")
    monkeypatch.setattr(
        plvr_market_aggregate_service,
        "bootstrap_market_coverage_metadata",
        lambda: called.update(bootstrap=True),
    )

    response = client.post(
        "/market-insights/coverage/bootstrap",
        headers={"X-Market-Read-Model-Refresh-Token": "wrong"},
    )

    assert response.status_code == 403
    assert called == {"bootstrap": False}
    assert "reason_code" not in response.json()


@pytest.mark.parametrize(
    ("path", "body", "service_name"),
    (
        ("/market-insights/coverage/bootstrap", None, "bootstrap"),
        ("/market-insights/coverage/reconcile", {"county": "placeholder"}, "reconcile"),
        ("/market-insights/coverage/audit", None, "audit"),
    ),
)
def test_market_coverage_operator_routes_are_mounted_and_protected(
    monkeypatch, path: str, body: dict[str, str] | None, service_name: str
) -> None:
    from services import plvr_market_aggregate_service
    from services.taiwan_admin_registry import iter_taiwan_regions

    if service_name == "reconcile":
        body = {"county": iter_taiwan_regions()[0].county}

    called = {"bootstrap": False, "reconcile": False, "audit": False}
    monkeypatch.setenv("MARKET_READ_MODEL_REFRESH_TOKEN", "expected")
    monkeypatch.setattr(
        plvr_market_aggregate_service,
        "bootstrap_market_coverage_metadata",
        lambda: called.update(bootstrap=True),
    )
    monkeypatch.setattr(
        plvr_market_aggregate_service,
        "reconcile_market_coverage",
        lambda *_args, **_kwargs: called.update(reconcile=True),
    )
    monkeypatch.setattr(
        plvr_market_aggregate_service,
        "audit_market_coverage",
        lambda: called.update(audit=True),
    )

    response = client.post(
        path,
        json=body,
        headers={"X-Market-Read-Model-Refresh-Token": "wrong"},
    )

    assert response.status_code == 403
    assert response.status_code != 404
    assert called == {"bootstrap": False, "reconcile": False, "audit": False}
    assert service_name in called
    assert "reason_code" not in response.json()


def test_market_coverage_bootstrap_returns_safe_fields(monkeypatch) -> None:
    from services import plvr_market_aggregate_service

    monkeypatch.setenv("MARKET_READ_MODEL_REFRESH_TOKEN", "expected")
    monkeypatch.setattr(
        plvr_market_aggregate_service,
        "bootstrap_market_coverage_metadata",
        lambda: {
            "status": "resolved",
            "operation": "bootstrap",
            "migration_status": "applied_or_already_present",
            "message": "Market coverage metadata is ready.",
            "sql": "must not leak",
        },
    )

    response = client.post(
        "/market-insights/coverage/bootstrap",
        headers={"X-Market-Read-Model-Refresh-Token": "expected"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload == {
        "status": "resolved",
        "operation": "bootstrap",
        "migration_status": "applied_or_already_present",
        "message": "Market coverage metadata is ready.",
    }
    assert "must not leak" not in str(payload)


def test_market_coverage_bootstrap_failure_returns_safe_reason(monkeypatch) -> None:
    from services import plvr_market_aggregate_service

    monkeypatch.setenv("MARKET_READ_MODEL_REFRESH_TOKEN", "expected")
    monkeypatch.setattr(
        plvr_market_aggregate_service,
        "bootstrap_market_coverage_metadata",
        lambda: {
            "status": "unavailable",
            "operation": "bootstrap",
            "migration_status": "unavailable",
            "message": "safe unavailable",
            "reason_code": "coverage_bootstrap_migration_unavailable",
            "database_url": "must not leak",
        },
    )

    response = client.post(
        "/market-insights/coverage/bootstrap",
        headers={"X-Market-Read-Model-Refresh-Token": "expected"},
    )

    assert response.status_code == 503
    payload = response.json()
    assert payload["reason_code"] == "coverage_bootstrap_migration_unavailable"
    assert set(payload) == {"status", "operation", "migration_status", "message", "reason_code"}
    assert "database_url" not in payload
    assert "must not leak" not in str(payload)


def test_market_coverage_reconcile_returns_counts_without_raw_rows(monkeypatch) -> None:
    from services import plvr_market_aggregate_service

    monkeypatch.setenv("MARKET_READ_MODEL_REFRESH_TOKEN", "expected")
    monkeypatch.setattr(
        plvr_market_aggregate_service,
        "reconcile_market_coverage",
        lambda county: {
            "status": "resolved",
            "operation": "reconcile",
            "county": county,
            "coverage_status": "covered",
            "processed_region_count": 3,
            "covered_region_count": 3,
            "not_covered_region_count": 0,
            "unknown_region_count": 0,
            "message": "Market coverage metadata reconciled.",
            "raw_rows": [{"address": "must not leak"}],
        },
    )

    response = client.post(
        "/market-insights/coverage/reconcile",
        json={"county": "臺北市"},
        headers={"X-Market-Read-Model-Refresh-Token": "expected"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["coverage_status"] == "covered"
    assert payload["processed_region_count"] == 3
    assert payload["persistence_status"] == "applied"
    assert "raw_rows" not in payload
    assert "must not leak" not in str(payload)


def test_market_coverage_reconcile_degraded_completion_is_http_200(monkeypatch) -> None:
    from services import plvr_market_aggregate_service

    monkeypatch.setenv("MARKET_READ_MODEL_REFRESH_TOKEN", "expected")
    monkeypatch.setattr(
        plvr_market_aggregate_service,
        "reconcile_market_coverage",
        lambda county: {
            "status": "resolved",
            "operation": "reconcile",
            "county": county,
            "coverage_status": "coverage_unknown",
            "processed_region_count": 12,
            "covered_region_count": 0,
            "not_covered_region_count": 0,
            "unknown_region_count": 12,
            "persistence_status": "degraded",
            "message": "Market coverage metadata reconciled.",
            "database": "must not leak",
        },
    )

    response = client.post(
        "/market-insights/coverage/reconcile",
        json={"county": "臺北市"},
        headers={"X-Market-Read-Model-Refresh-Token": "expected"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["coverage_status"] == "coverage_unknown"
    assert payload["persistence_status"] == "degraded"
    assert payload["unknown_region_count"] == 12
    assert "reason_code" not in payload
    assert "database" not in payload


def test_market_coverage_reconcile_invalid_county_is_422_without_service(monkeypatch) -> None:
    from services import plvr_market_aggregate_service

    called = {"reconcile": False}
    monkeypatch.setenv("MARKET_READ_MODEL_REFRESH_TOKEN", "expected")
    monkeypatch.setattr(
        plvr_market_aggregate_service,
        "reconcile_market_coverage",
        lambda county: called.update(reconcile=True),
    )

    response = client.post(
        "/market-insights/coverage/reconcile",
        json={"county": "Not A Canonical County"},
        headers={"X-Market-Read-Model-Refresh-Token": "expected"},
    )

    assert response.status_code == 422
    assert called == {"reconcile": False}
    assert "reason_code" not in response.json()


def test_market_coverage_reconcile_failure_returns_safe_reason_only(monkeypatch) -> None:
    from services import plvr_market_aggregate_service

    monkeypatch.setenv("MARKET_READ_MODEL_REFRESH_TOKEN", "expected")
    monkeypatch.setattr(
        plvr_market_aggregate_service,
        "reconcile_market_coverage",
        lambda county: {
            "status": "unavailable",
            "operation": "reconcile",
            "county": county,
            "coverage_status": "coverage_unknown",
            "processed_region_count": 0,
            "covered_region_count": 0,
            "not_covered_region_count": 0,
            "unknown_region_count": 0,
            "message": "raw details must be replaced",
            "reason_code": "coverage_reconcile_metadata_unavailable",
            "sql": "must not leak",
        },
    )

    response = client.post(
        "/market-insights/coverage/reconcile",
        json={"county": "臺北市"},
        headers={"X-Market-Read-Model-Refresh-Token": "expected"},
    )

    assert response.status_code == 503
    payload = response.json()
    assert payload == {
        "status": "unavailable",
        "operation": "reconcile",
        "county": "臺北市",
        "message": "Market coverage metadata is temporarily unavailable.",
        "reason_code": "coverage_reconcile_metadata_unavailable",
    }
    assert "raw details" not in str(payload)
    assert "sql" not in payload


def test_market_coverage_reconcile_unknown_reason_is_safely_normalized(monkeypatch) -> None:
    from services import plvr_market_aggregate_service

    monkeypatch.setenv("MARKET_READ_MODEL_REFRESH_TOKEN", "expected")
    monkeypatch.setattr(
        plvr_market_aggregate_service,
        "reconcile_market_coverage",
        lambda county: {
            "status": "unavailable",
            "county": county,
            "reason_code": "raw_database_exception",
        },
    )

    response = client.post(
        "/market-insights/coverage/reconcile",
        json={"county": "臺北市"},
        headers={"X-Market-Read-Model-Refresh-Token": "expected"},
    )

    assert response.status_code == 503
    assert response.json()["reason_code"] == "coverage_reconcile_unknown_safe_failure"


def test_market_coverage_audit_returns_safe_aggregate_lines(monkeypatch) -> None:
    from services import plvr_market_aggregate_service

    monkeypatch.setenv("MARKET_READ_MODEL_REFRESH_TOKEN", "expected")
    monkeypatch.setattr(
        plvr_market_aggregate_service,
        "audit_market_coverage",
        lambda: {
            "status": "PARTIAL",
            "expected_region_count": 3,
            "covered_region_count": 2,
            "missing_region_count": 1,
            "unknown_region_count": 0,
            "missing_regions": ["Demo County/Demo District"],
            "unknown_regions": [],
            "database_url": "must not leak",
        },
    )

    response = client.post(
        "/market-insights/coverage/audit",
        headers={"X-Market-Read-Model-Refresh-Token": "expected"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["MARKET_COVERAGE"] == "PARTIAL"
    assert payload["EXPECTED_REGION_COUNT"] == 3
    assert payload["MISSING_REGIONS"] == ["Demo County/Demo District"]
    assert "database_url" not in payload
    assert "must not leak" not in str(payload)
