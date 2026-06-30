"""API tests for the Market Insight read model bridge."""

from __future__ import annotations

from fastapi.testclient import TestClient

from backend.api_main import app


client = TestClient(app)


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
