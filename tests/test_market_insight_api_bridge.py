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


def test_market_coverage_operator_routes_are_mounted() -> None:
    route_paths = {getattr(route, "path", "") for route in app.routes}

    assert "/market-insights/coverage/bootstrap" in route_paths
    assert "/market-insights/coverage/reconcile" in route_paths
    assert "/market-insights/coverage/audit" in route_paths


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
        json={"county": "Demo County"},
        headers={"X-Market-Read-Model-Refresh-Token": "expected"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["coverage_status"] == "covered"
    assert payload["processed_region_count"] == 3
    assert "raw_rows" not in payload
    assert "must not leak" not in str(payload)


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
        json={"county": "Demo County"},
        headers={"X-Market-Read-Model-Refresh-Token": "expected"},
    )

    assert response.status_code == 503
    payload = response.json()
    assert payload == {
        "status": "unavailable",
        "operation": "reconcile",
        "county": "Demo County",
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
        json={"county": "Demo County"},
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
