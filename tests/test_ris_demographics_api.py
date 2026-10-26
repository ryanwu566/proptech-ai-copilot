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


def test_router_registration_and_openapi_expose_only_the_read_only_get_paths() -> None:
    paths = app.openapi()["paths"]

    assert set(path for path in paths if path.startswith("/demographics/")) == {
        "/demographics/location",
        "/demographics/villages/{district_code}/latest",
        "/demographics/villages/{district_code}/history",
        "/demographics/villages/{district_code}",
    }
    assert all(set(paths[path]) == {"get"} for path in paths if path.startswith("/demographics/"))


class FakeVillageResolver:
    def __init__(self, result: object = None, *, error: Exception | None = None) -> None:
        self.result = result
        self.error = error
        self.calls: list[tuple[float, float]] = []

    def resolve(self, *, latitude: float, longitude: float):
        self.calls.append((latitude, longitude))
        if self.error is not None:
            raise self.error
        return self.result


def _location_client(resolver: FakeVillageResolver) -> TestClient:
    from backend.api.routes_demographics import get_village_demographics_resolver

    app.dependency_overrides[get_village_demographics_resolver] = lambda: resolver
    return TestClient(app)


def _clear_location_override() -> None:
    from backend.api.routes_demographics import get_village_demographics_resolver

    app.dependency_overrides.pop(get_village_demographics_resolver, None)


def _resolved_village() -> dict[str, object]:
    return {
        "status": "resolved", "county": "臺北市", "town": "大安區", "village": "測試里",
        "village_code": DISTRICT_CODE, "district_code": DISTRICT_CODE,
        "source": "nlsc_village_boundary", "source_vintage": "ROC-1150817", "reason": "unique_intersection",
    }


def test_location_demographics_joins_the_confirmed_coordinate_only() -> None:
    from services.ris_demographics_insight import build_demographics_insight

    demographics = build_demographics_insight(_observation("11507"), [_observation("11506"), _observation("11507")])
    resolver = FakeVillageResolver({"location": _resolved_village(), "demographics": demographics})
    client = _location_client(resolver)
    try:
        response = client.get("/demographics/location?latitude=25.026&longitude=121.534")
    finally:
        _clear_location_override()

    assert response.status_code == 200
    body = response.json()
    # The coordinate is the only spatial input; no geocoder administrative label is accepted or forwarded.
    assert resolver.calls == [(25.026, 121.534)]
    assert (body["latitude"], body["longitude"]) == (25.026, 121.534)
    assert body["checked_at"].endswith("+00:00")
    assert body["village_resolution"]["status"] == "resolved"
    assert body["demographics"]["status"] == "available"
    assert body["demographics"]["observed_month_count"] == 2


def test_location_demographics_rejects_admin_label_parameters_as_inputs() -> None:
    resolver = FakeVillageResolver({"location": _resolved_village(), "demographics": {"status": "no_data", "reason": "x"}})
    client = _location_client(resolver)
    try:
        response = client.get("/demographics/location?latitude=25.026&longitude=121.534&county=新北市&village=別的里")
    finally:
        _clear_location_override()

    assert response.status_code == 200
    assert response.json()["village_resolution"]["village"] == "測試里"


def test_location_demographics_preserves_unresolved_and_ambiguous_states() -> None:
    for status, extra in (("unresolved", {}), ("ambiguous", {"candidate_count": 2})):
        village = {"status": status, "county": None, "town": None, "village": None, "village_code": None,
                   "district_code": None, "source": "nlsc_village_boundary", "source_vintage": "ROC-1150817",
                   "reason": "zero_polygon", **extra}
        resolver = FakeVillageResolver({"location": village, "demographics": {"status": "no_data", "reason": "village_identity_not_resolved"}})
        client = _location_client(resolver)
        try:
            response = client.get("/demographics/location?latitude=25.0&longitude=121.5")
        finally:
            _clear_location_override()
        assert response.status_code == 200
        assert response.json()["village_resolution"]["status"] == status
        assert response.json()["demographics"] == {"status": "no_data", "reason": "village_identity_not_resolved"}


def test_location_demographics_fails_closed_when_resolver_breaks() -> None:
    for resolver in (FakeVillageResolver(error=RuntimeError("artifact")), FakeVillageResolver({"unexpected": True})):
        client = _location_client(resolver)
        try:
            response = client.get("/demographics/location?latitude=25.0&longitude=121.5")
        finally:
            _clear_location_override()
        assert response.status_code == 200
        assert response.json()["village_resolution"] == {"status": "unavailable", "reason": "village_resolver_unavailable"}
        assert response.json()["demographics"] == {"status": "no_data", "reason": "demographics_unavailable"}


def test_location_demographics_bounds_coordinates() -> None:
    resolver = FakeVillageResolver({"location": _resolved_village(), "demographics": {"status": "no_data", "reason": "x"}})
    client = _location_client(resolver)
    try:
        responses = [client.get(f"/demographics/location?{query}") for query in (
            "latitude=91&longitude=121.5", "latitude=25&longitude=181", "latitude=nan&longitude=121.5", "latitude=25",
        )]
    finally:
        _clear_location_override()
    assert [response.status_code for response in responses] == [422, 422, 422, 422]
    assert resolver.calls == []
