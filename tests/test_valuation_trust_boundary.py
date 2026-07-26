from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient

from backend.api_main import app
from services.property_search_service import search_properties
from services.valuation_providers.postgres_provider import PostgresValuationProvider
from services.valuation_providers.unavailable_provider import UnavailableValuationProvider
from services.valuation_service import estimate_property, get_valuation_provider
from services.valuation_trend_service import analyze_valuation_trend


client = TestClient(app)


def request_payload() -> dict[str, object]:
    return {"city": "Taipei City", "district": "Central District", "road": "Example Road", "building_type": "Apartment", "area_ping": 30, "building_age_years": 10, "floor": 5}


def official_row(index: int, period: str = "2026-01") -> dict[str, object]:
    return {"transaction_period": period, "city": "Taipei City", "district": "Central District", "road": "Example Road", "building_type": "Apartment", "area_ping": 30 + index, "unit_price_per_ping": 60 + index, "total_price": (60 + index) * (30 + index), "building_age_years": 10, "floor": 5, "source": "official_plvr_opendata"}


class FakePostgres(PostgresValuationProvider):
    def __init__(self, rows: list[dict[str, object]] | None = None, failure: bool = False) -> None:
        super().__init__("postgresql://fake")
        self.rows = rows or []
        self.failure = failure
        self.last_query_metadata = {"provider_active": "postgres", "candidate_pool_size": len(self.rows), "query_scope": "road", "requested_city": "Taipei City", "requested_district": "Central District", "requested_road": "Example Road", "db_rows_returned": len(self.rows), "query_status": "ok"}

    def available(self) -> bool:
        return True

    def data_status(self) -> dict[str, object]:
        return {"active_source": "postgres", "is_demo_data": False, "is_full_taiwan": False, "data_composition": "official", "coverage": {"cities": [], "districts": [], "roads_count": 1, "records_count": len(self.rows)}, "last_updated": None, "source_note": "", "user_message": ""}

    def query_comparables(self, _request: dict[str, object], limit: int = 50) -> list[dict[str, object]]:
        if self.failure:
            self.last_query_metadata["query_status"] = "failed"
            self.last_query_metadata["candidate_pool_size"] = 0
            return []
        return self.rows[:limit]

    def match_community(self, _request: dict[str, object]) -> None:
        return None


def test_default_provider_is_unavailable_and_does_not_select_sample(monkeypatch) -> None:
    monkeypatch.delenv("VALUATION_DATABASE_URL", raising=False)
    monkeypatch.delenv("VALUATION_DEMO_MODE", raising=False)
    provider = get_valuation_provider(sample_path=Path("missing-demo-sample.csv"))
    assert provider.source == "unavailable"
    assert provider.is_demo_data is False


def test_explicit_demo_mode_is_non_actionable(monkeypatch) -> None:
    monkeypatch.setenv("VALUATION_DEMO_MODE", "true")
    result = estimate_property({**request_payload(), "address_text": ""})
    assert result["valuation_status"] == "demo"
    assert result["result_origin"] == "demo"
    assert result["is_actionable"] is False


def test_database_query_failure_never_falls_back_or_leaks_error(monkeypatch) -> None:
    provider = FakePostgres(failure=True)
    monkeypatch.setattr("services.valuation_service.get_valuation_provider", lambda: provider)
    response = client.post("/valuation/estimate", json=request_payload())
    result = response.json()
    assert response.status_code == 200
    assert result["valuation_status"] == "unavailable"
    assert result["valuation_reason_code"] == "provider_query_failed"
    assert result["estimate_total_price"] is None
    assert "safe_error" not in str(result)


def test_official_result_requires_three_positive_comparables(monkeypatch) -> None:
    provider = FakePostgres([official_row(index) for index in range(2)])
    monkeypatch.setattr("services.valuation_service.get_valuation_provider", lambda: provider)
    result = client.post("/valuation/estimate", json=request_payload()).json()
    assert result["valuation_status"] == "no_data"
    assert result["valuation_reason_code"] == "official_comparables_insufficient"
    assert result["estimate_total_price"] is None
    assert result["price_range"] == {"low": None, "mid": None, "high": None}
    assert result["comparables"] == []


def test_trend_insufficient_months_has_null_metrics() -> None:
    result = analyze_valuation_trend(request_payload(), [official_row(0), official_row(1)])
    assert result["trend_status"] == "no_data"
    assert result["is_actionable"] is False
    assert result["recent_median_unit_price"] is None
    assert result["trend_annualized_rate"] is None
    assert result["scenario_forecast"] == {"conservative": [], "base": [], "optimistic": []}


def test_trend_provider_unavailable_is_not_zero(monkeypatch) -> None:
    monkeypatch.setattr("services.valuation_trend_service.get_valuation_provider", lambda: UnavailableValuationProvider())
    result = analyze_valuation_trend(request_payload())
    assert result["trend_status"] == "unavailable"
    assert result["recent_median_unit_price"] is None
    assert result["trend_annualized_rate"] is None


def test_property_search_no_data_is_not_a_zero_price_result() -> None:
    result = search_properties({"budget_max": 100}, [official_row(0)])
    assert result["search_status"] == "no_data"
    assert result["is_actionable"] is False
    assert result["summary"]["matched_count"] == 0
    assert result["matched_transactions"] == []


def test_public_route_exception_is_safe(monkeypatch) -> None:
    monkeypatch.setattr("services.valuation_service.estimate_property", lambda _payload: (_ for _ in ()).throw(RuntimeError("private database detail")))
    response = client.post("/valuation/estimate", json=request_payload())
    assert response.status_code == 200
    assert response.json()["valuation_status"] == "unavailable"
    assert "private database detail" not in response.text
