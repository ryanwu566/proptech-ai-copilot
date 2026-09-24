from __future__ import annotations

from datetime import date

from fastapi.testclient import TestClient

from backend.api_main import app


DISTRICT_CODE = "65000010001"


def _observation(
    yyymm: str = "11507",
    *,
    total_population: int = 20,
    child_ratio: float | None = 0.1,
) -> dict[str, object]:
    return {
        "statistic_yyymm": yyymm,
        "statistic_month": date(int(yyymm[:-2]) + 1911, int(yyymm[-2:]), 1),
        "district_code": DISTRICT_CODE,
        "site_id": "臺北市大安區",
        "village": "測試里",
        "household_count": 8,
        "total_population": total_population,
        "male_population": 10,
        "female_population": 10,
        "age_0_14": 2,
        "age_15_64": 16,
        "age_65_plus": 2,
        "child_ratio": child_ratio,
        "working_age_ratio": None if child_ratio is None else 0.8,
        "elderly_ratio": None if child_ratio is None else 0.1,
        "average_household_size": None if child_ratio is None else 2.5,
        "audit_reasons": ["sex_total_mismatch"],
        "source_provider": "RIS",
        "source_dataset": "ODRP014",
    }


class FakeService:
    def __init__(self) -> None:
        self.latest_result: dict[str, object] | None = _observation()
        self.exact_result: dict[str, object] | None = _observation("11504")
        self.history_result: list[dict[str, object]] = [_observation("11504"), _observation("11507")]
        self.history_limits: list[int] = []

    def latest(self, district_code: str):
        assert district_code == DISTRICT_CODE
        return self.latest_result

    def exact_month(self, district_code: str, month: str):
        assert district_code == DISTRICT_CODE
        assert month == "11504"
        return self.exact_result

    def history(self, district_code: str, *, limit: int):
        assert district_code == DISTRICT_CODE
        self.history_limits.append(limit)
        return self.history_result


def _client(service: FakeService) -> TestClient:
    from backend.api.routes_demographics import get_demographics_query_service

    app.dependency_overrides[get_demographics_query_service] = lambda: service
    return TestClient(app)


def _clear_override() -> None:
    from backend.api.routes_demographics import get_demographics_query_service

    app.dependency_overrides.pop(get_demographics_query_service, None)


def test_latest_response_has_stable_observation_contract() -> None:
    service = FakeService()
    client = _client(service)
    try:
        response = client.get(f"/demographics/villages/{DISTRICT_CODE}/latest")
    finally:
        _clear_override()

    assert response.status_code == 200
    assert response.json() == {
        "data_status": "available",
        "observation": {
            **_observation(),
            "statistic_month": "2026-07-01",
        },
    }


def test_exact_month_response_preserves_zero_and_null_values() -> None:
    service = FakeService()
    service.exact_result = _observation("11504", total_population=0, child_ratio=None)
    client = _client(service)
    try:
        response = client.get(f"/demographics/villages/{DISTRICT_CODE}?month=11504")
    finally:
        _clear_override()

    assert response.status_code == 200
    observation = response.json()["observation"]
    assert observation["total_population"] == 0
    assert observation["child_ratio"] is None
    assert observation["average_household_size"] is None
    assert observation["audit_reasons"] == ["sex_total_mismatch"]


def test_history_defaults_to_13_and_returns_ascending_contract() -> None:
    service = FakeService()
    client = _client(service)
    try:
        response = client.get(f"/demographics/villages/{DISTRICT_CODE}/history")
    finally:
        _clear_override()

    assert response.status_code == 200
    payload = response.json()
    assert service.history_limits == [13]
    assert payload["data_status"] == "available"
    assert payload["order"] == "asc"
    assert payload["limit"] == 13
    assert payload["count"] == 2
    assert [item["statistic_yyymm"] for item in payload["items"]] == ["11504", "11507"]


def test_history_accepts_custom_and_max_limit_but_rejects_above_max() -> None:
    service = FakeService()
    client = _client(service)
    try:
        custom = client.get(f"/demographics/villages/{DISTRICT_CODE}/history?limit=7")
        maximum = client.get(f"/demographics/villages/{DISTRICT_CODE}/history?limit=120")
        too_large = client.get(f"/demographics/villages/{DISTRICT_CODE}/history?limit=121")
    finally:
        _clear_override()

    assert custom.status_code == 200
    assert maximum.status_code == 200
    assert too_large.status_code == 422
    assert service.history_limits == [7, 120]


def test_latest_and_exact_missing_rows_return_safe_not_found() -> None:
    service = FakeService()
    service.latest_result = None
    service.exact_result = None
    client = _client(service)
    try:
        latest = client.get(f"/demographics/villages/{DISTRICT_CODE}/latest")
        exact = client.get(f"/demographics/villages/{DISTRICT_CODE}?month=11504")
    finally:
        _clear_override()

    assert latest.status_code == exact.status_code == 404
    assert latest.json()["detail"]["code"] == "not_found"
    assert exact.json()["detail"]["code"] == "not_found"


def test_empty_history_is_200_no_data() -> None:
    service = FakeService()
    service.history_result = []
    client = _client(service)
    try:
        response = client.get(f"/demographics/villages/{DISTRICT_CODE}/history")
    finally:
        _clear_override()

    assert response.status_code == 200
    assert response.json() == {
        "data_status": "no_data",
        "district_code": DISTRICT_CODE,
        "order": "asc",
        "limit": 13,
        "count": 0,
        "items": [],
    }


def test_district_code_and_month_validation_are_bounded_without_fixed_11_digits() -> None:
    class BoundedNumericService(FakeService):
        def latest(self, district_code: str):
            return self.latest_result

    service = BoundedNumericService()
    client = _client(service)
    try:
        short_numeric = client.get("/demographics/villages/123/latest")
        alphabetic = client.get("/demographics/villages/not-numeric/latest")
        oversized = client.get(f"/demographics/villages/{'1' * 33}/latest")
        invalid_month = client.get(f"/demographics/villages/{DISTRICT_CODE}?month=11513")
    finally:
        _clear_override()

    assert short_numeric.status_code == 200
    assert alphabetic.status_code == 422
    assert oversized.status_code == 422
    assert invalid_month.status_code == 422


def test_database_unavailable_is_safe_503_without_exception_or_sql_leak() -> None:
    from services.ris_population_query import RisPopulationQueryUnavailable

    class UnavailableService(FakeService):
        def latest(self, district_code: str):
            raise RisPopulationQueryUnavailable(
                "postgresql://user:password@production/private SELECT * FROM secrets"
            )

    client = _client(UnavailableService())
    try:
        response = client.get(f"/demographics/villages/{DISTRICT_CODE}/latest")
    finally:
        _clear_override()

    body = response.text.lower()
    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "unavailable"
    for forbidden in ("password", "production", "select", "postgresql"):
        assert forbidden not in body


def test_router_registration_and_openapi_expose_only_the_three_get_paths() -> None:
    paths = app.openapi()["paths"]

    assert set(path for path in paths if path.startswith("/demographics/")) == {
        "/demographics/villages/{district_code}/latest",
        "/demographics/villages/{district_code}/history",
        "/demographics/villages/{district_code}",
    }
    assert all(set(paths[path]) == {"get"} for path in paths if path.startswith("/demographics/"))
