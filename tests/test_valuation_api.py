from fastapi.testclient import TestClient

from backend.api_main import app
from services.valuation_providers.postgres_provider import PostgresValuationProvider


client = TestClient(app)


def payload() -> dict[str, object]:
    return {
        "city": "Taipei City",
        "district": "Central District",
        "road": "Example Road",
        "building_type": "Apartment",
        "area_ping": 30,
        "building_age_years": 15,
        "floor": 8,
    }


def test_valuation_api_returns_safe_unavailable_by_default(monkeypatch) -> None:
    monkeypatch.delenv("VALUATION_DATABASE_URL", raising=False)
    monkeypatch.delenv("VALUATION_DEMO_MODE", raising=False)
    response = client.post("/valuation/estimate", json=payload())
    result = response.json()
    assert response.status_code == 200
    assert result["valuation_status"] == "unavailable"
    assert result["result_origin"] == "none"
    assert result["is_actionable"] is False
    assert result["estimate_total_price"] is None
    assert result["comparables"] == []


def test_valuation_data_status_api_is_safe_when_provider_is_unavailable(monkeypatch) -> None:
    monkeypatch.delenv("VALUATION_DATABASE_URL", raising=False)
    monkeypatch.delenv("VALUATION_DEMO_MODE", raising=False)
    response = client.get("/valuation/data-status")
    result = response.json()
    assert response.status_code == 200
    assert result["active_source"] == "unavailable"
    assert result["coverage"]["records_count"] == 0
    assert result["operator_attention_required"] is True


def test_health_does_not_depend_on_valuation_provider(monkeypatch) -> None:
    monkeypatch.setattr("services.valuation_service.get_valuation_provider", lambda: (_ for _ in ()).throw(RuntimeError("must not run")))
    assert client.get("/health").status_code == 200


def test_official_estimate_response_has_no_provider_internals(monkeypatch) -> None:
    def make_row(index: int) -> dict[str, object]:
        return {
            "transaction_period": "2026-03",
            "city": "Taipei City",
            "district": "Central District",
            "road": "Example Road",
            "building_type": "Apartment",
            "area_ping": 28 + index,
            "unit_price_per_ping": 70 + index,
            "total_price": (70 + index) * (28 + index),
            "building_age_years": 15,
            "floor": 8,
            "lat": None,
            "lng": None,
            "source": "official_plvr_opendata",
        }

    rows = [make_row(index) for index in range(4)]
    provider = PostgresValuationProvider("postgresql://test")
    monkeypatch.setattr(provider, "available", lambda: True)
    monkeypatch.setattr(provider, "query_comparables", lambda _payload: rows)
    monkeypatch.setattr(provider, "match_community", lambda _payload: None)
    monkeypatch.setattr(provider, "data_status", lambda: {"active_source": "postgres", "is_demo_data": False, "is_full_taiwan": False, "data_composition": "official", "coverage": {"cities": [], "districts": [], "roads_count": 1, "records_count": 4}, "last_updated": None, "source_note": "", "user_message": ""})
    provider.last_query_metadata = {"provider_active": "postgres", "candidate_pool_size": 4, "query_scope": "road", "requested_city": "Taipei City", "requested_district": "Central District", "requested_road": "Example Road", "db_rows_returned": 4, "query_status": "ok"}
    monkeypatch.setattr("services.valuation_service.get_valuation_provider", lambda: provider)

    response = client.post("/valuation/estimate", json=payload())
    result = response.json()
    assert response.status_code == 200
    assert result["valuation_status"] == "available"
    assert result["result_origin"] == "official"
    assert result["is_actionable"] is True
    assert len(result["comparables"]) >= 3
    assert set(result["source_details"]) <= {"provider_active", "candidate_pool_size", "query_scope", "requested_city", "requested_district", "requested_road", "db_rows_returned", "query_status"}


# ---------------------------------------------------------------------------
# DEFECT-007: area_ping upper bound validation (residential scope: <= 500 坪)
# ---------------------------------------------------------------------------
# Rationale: This is a residential property valuation tool. Taiwan residential
# properties range from ~10 to ~150 坪 (even the largest luxury penthouses
# rarely exceed 200 坪). 500 坪 provides generous headroom while rejecting
# absurd values that produce meaningless estimates.
# ---------------------------------------------------------------------------


def test_area_ping_normal_residential_accepted() -> None:
    """Normal residential area (30 坪) must be accepted."""
    p = payload()
    p["area_ping"] = 30
    response = client.post("/valuation/estimate", json=p)
    assert response.status_code == 200


def test_area_ping_upper_boundary_accepted() -> None:
    """Exact upper boundary (500 坪) must be accepted."""
    p = payload()
    p["area_ping"] = 500
    response = client.post("/valuation/estimate", json=p)
    assert response.status_code == 200


def test_area_ping_above_boundary_rejected() -> None:
    """Value immediately above boundary (500.1 坪) must be rejected with 422."""
    p = payload()
    p["area_ping"] = 500.1
    response = client.post("/valuation/estimate", json=p)
    assert response.status_code == 422


def test_area_ping_absurd_value_rejected() -> None:
    """Absurd value (99999 坪) must be rejected with 422."""
    p = payload()
    p["area_ping"] = 99999
    response = client.post("/valuation/estimate", json=p)
    assert response.status_code == 422


def test_area_ping_zero_rejected() -> None:
    """Zero area must be rejected (gt=0)."""
    p = payload()
    p["area_ping"] = 0
    response = client.post("/valuation/estimate", json=p)
    assert response.status_code == 422


def test_area_ping_negative_rejected() -> None:
    """Negative area must be rejected."""
    p = payload()
    p["area_ping"] = -5
    response = client.post("/valuation/estimate", json=p)
    assert response.status_code == 422


def test_valuation_trend_area_ping_boundary() -> None:
    """Trend endpoint uses the same area_ping bound."""
    trend_payload = {
        "city": "Taipei City",
        "district": "Central District",
        "road": "Example Road",
        "building_type": "Apartment",
        "area_ping": 500,
        "building_age_years": 15,
        "floor": 8,
    }
    response = client.post("/valuation/trend", json=trend_payload)
    assert response.status_code == 200
    trend_payload["area_ping"] = 501
    response = client.post("/valuation/trend", json=trend_payload)
    assert response.status_code == 422
