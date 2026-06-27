from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.api.commute import get_commute_service
from app.main import app
from app.schemas.commute import CommuteNearestStationResponse, CommuteStatusResponse
from app.schemas.location import LocationResolveResponse
from app.services.location_resolver import build_location_resolver


GENERATED_AT = datetime(2026, 1, 1, tzinfo=timezone.utc)
SOURCE_UPDATED_AT = datetime(2026, 1, 2, tzinfo=timezone.utc)


class FakeResolvedResolver:
    def __init__(self) -> None:
        self.calls = 0

    def resolve(self, address: str) -> LocationResolveResponse:
        self.calls += 1
        return LocationResolveResponse(
            status="resolved",
            source="google",
            formatted_address="hidden formatted address",
            latitude=10.0,
            longitude=20.0,
            confidence="medium",
            message="hidden provider message",
        )


class FakeUnresolvedResolver(FakeResolvedResolver):
    def resolve(self, address: str) -> LocationResolveResponse:
        self.calls += 1
        return LocationResolveResponse(
            status="unresolved",
            source="none",
            formatted_address=None,
            latitude=None,
            longitude=None,
            confidence="unknown",
            message="hidden unresolved message",
        )


class FakeUnavailableResolver(FakeResolvedResolver):
    def resolve(self, address: str) -> LocationResolveResponse:
        self.calls += 1
        return LocationResolveResponse(
            status="unavailable",
            source="none",
            formatted_address=None,
            latitude=None,
            longitude=None,
            confidence="unknown",
            message="hidden unavailable message",
        )


class FakeCommuteService:
    def __init__(self, *, available: bool = True) -> None:
        self.available = available
        self.nearest_calls = 0
        self.refresh_calls = 0

    def get_status(self) -> CommuteStatusResponse:
        if not self.available:
            return CommuteStatusResponse(available=False, source="none")
        return CommuteStatusResponse(
            available=True,
            source="tdx",
            generated_at=GENERATED_AT,
            source_station_count=2,
            included_station_count=2,
            skipped_station_count=0,
            line_relation_available=True,
        )

    def find_nearest_station(self, latitude: float, longitude: float) -> CommuteNearestStationResponse:  # noqa: ARG002
        self.nearest_calls += 1
        return CommuteNearestStationResponse(
            status="resolved",
            source="tdx",
            station_name="Fictional Station",
            line_ids=["L1"],
            distance_meters=42.5,
            source_updated_at=SOURCE_UPDATED_AT,
            snapshot_generated_at=GENERATED_AT,
            message="最近捷運站僅供通勤生活圈初步參考，仍需確認實際步行路線與出入口狀況。",
        )

    def refresh_from_tdx(self):  # noqa: ANN201
        self.refresh_calls += 1
        raise AssertionError("address lookup must not refresh TDX")


class UnavailableNearestService(FakeCommuteService):
    def find_nearest_station(self, latitude: float, longitude: float) -> CommuteNearestStationResponse:  # noqa: ARG002
        self.nearest_calls += 1
        return CommuteNearestStationResponse(
            status="unavailable",
            source="none",
            message="not available",
        )


def run_with_overrides(service: FakeCommuteService, resolver: object, payload: dict[str, object]):
    app.dependency_overrides[get_commute_service] = lambda: service
    app.dependency_overrides[build_location_resolver] = lambda: resolver
    client = TestClient(app)
    try:
        return client.post("/api/commute/address-lookup", json=payload)
    finally:
        app.dependency_overrides.clear()


def test_address_lookup_with_snapshot_and_resolved_location_returns_minimized_commute_result() -> None:
    service = FakeCommuteService()
    resolver = FakeResolvedResolver()

    response = run_with_overrides(service, resolver, {"address": "Fictional Address"})

    assert response.status_code == 200
    payload = response.json()
    assert resolver.calls == 1
    assert service.nearest_calls == 1
    assert service.refresh_calls == 0
    assert payload["status"] == "resolved"
    assert payload["source"] == "tdx"
    assert payload["station_name"] == "Fictional Station"
    assert payload["line_ids"] == ["L1"]
    assert payload["distance_meters"] == 42.5
    assert payload["source_updated_at"]
    assert payload["snapshot_generated_at"]
    assert "僅供通勤與生活機能參考" in payload["message"]


def test_success_response_excludes_address_coordinates_provider_station_uid_token_and_raw_payload() -> None:
    response = run_with_overrides(
        FakeCommuteService(),
        FakeResolvedResolver(),
        {"address": "Fictional Address"},
    )

    payload = response.json()
    text = str(payload)
    forbidden_keys = {
        "address",
        "latitude",
        "longitude",
        "formatted_address",
        "StationUID",
        "station_uid",
        "raw",
        "payload",
        "token",
        "provider",
    }
    assert forbidden_keys.isdisjoint(payload.keys())
    assert "Fictional Address" not in text
    assert "hidden formatted address" not in text
    assert "hidden provider message" not in text


def test_missing_snapshot_returns_503_without_calling_location_resolver() -> None:
    service = FakeCommuteService(available=False)
    resolver = FakeResolvedResolver()

    response = run_with_overrides(service, resolver, {"address": "Fictional Address"})

    assert response.status_code == 503
    assert resolver.calls == 0
    assert service.nearest_calls == 0
    assert service.refresh_calls == 0


def test_blank_address_returns_422_without_calling_resolver_or_commute_service() -> None:
    service = FakeCommuteService()
    resolver = FakeResolvedResolver()

    response = run_with_overrides(service, resolver, {"address": " \t\n "})

    assert response.status_code == 422
    assert resolver.calls == 0
    assert service.nearest_calls == 0
    assert service.refresh_calls == 0


def test_extra_fields_are_rejected() -> None:
    response = run_with_overrides(
        FakeCommuteService(),
        FakeResolvedResolver(),
        {"address": "Fictional Address", "latitude": 10.0, "longitude": 20.0},
    )

    assert response.status_code == 422


def test_unresolved_location_returns_200_unresolved_without_nearest_lookup() -> None:
    service = FakeCommuteService()
    resolver = FakeUnresolvedResolver()

    response = run_with_overrides(service, resolver, {"address": "Fictional Address"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "unresolved"
    assert payload["source"] == "none"
    assert payload["station_name"] is None
    assert service.nearest_calls == 0
    assert "找不到可信位置" in payload["message"]


def test_unavailable_location_returns_503_without_nearest_lookup() -> None:
    service = FakeCommuteService()
    resolver = FakeUnavailableResolver()

    response = run_with_overrides(service, resolver, {"address": "Fictional Address"})

    assert response.status_code == 503
    assert resolver.calls == 1
    assert service.nearest_calls == 0


def test_unavailable_nearest_result_returns_503_without_refresh() -> None:
    service = UnavailableNearestService()
    resolver = FakeResolvedResolver()

    response = run_with_overrides(service, resolver, {"address": "Fictional Address"})

    assert response.status_code == 503
    assert service.nearest_calls == 1
    assert service.refresh_calls == 0


def test_disclaimer_is_conservative_and_avoids_overclaims() -> None:
    response = run_with_overrides(
        FakeCommuteService(),
        FakeResolvedResolver(),
        {"address": "Fictional Address"},
    )

    message = response.json()["message"]
    assert "不影響地勢災害、貸款、法律或看房結論" in message
    for overclaim in ["值得買", "值得看房", "安全", "保證", "最佳"]:
        assert overclaim not in message
