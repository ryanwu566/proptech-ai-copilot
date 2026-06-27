from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.api.commute import get_commute_service
from app.core.config import settings
from app.main import app
from app.schemas.commute import CommuteNearestStationResponse, CommuteRefreshResponse, CommuteStatusResponse
from app.services.tdx_mrt_client import TdxMrtClientError


GENERATED_AT = datetime(2026, 1, 1, tzinfo=timezone.utc)
SOURCE_UPDATED_AT = datetime(2026, 1, 2, tzinfo=timezone.utc)


class FakeCommuteService:
    def __init__(self) -> None:
        self.refresh_calls = 0
        self.nearest_calls = 0

    def refresh_from_tdx(self) -> CommuteRefreshResponse:
        self.refresh_calls += 1
        return CommuteRefreshResponse(
            status="ready",
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
            station_name="Nearest Test Station",
            line_ids=["L1", "L2"],
            distance_meters=123.45,
            source_updated_at=SOURCE_UPDATED_AT,
            snapshot_generated_at=GENERATED_AT,
            message="最近捷運站僅供通勤生活圈初步參考，仍需確認實際步行路線與出入口狀況。",
        )

    def get_status(self) -> CommuteStatusResponse:
        return CommuteStatusResponse(
            available=True,
            source="tdx",
            generated_at=GENERATED_AT,
            source_station_count=2,
            included_station_count=2,
            skipped_station_count=0,
            line_relation_available=True,
        )


class UnavailableNearestService(FakeCommuteService):
    def find_nearest_station(self, latitude: float, longitude: float) -> CommuteNearestStationResponse:  # noqa: ARG002
        self.nearest_calls += 1
        return CommuteNearestStationResponse(
            status="unavailable",
            source="none",
            message="捷運通勤資料尚未建立，請先完成官方資料刷新。",
        )


class FailingRefreshService(FakeCommuteService):
    def refresh_from_tdx(self) -> CommuteRefreshResponse:
        self.refresh_calls += 1
        raise TdxMrtClientError("credentials_unavailable")


def test_refresh_with_valid_token_returns_metadata(monkeypatch) -> None:
    service = FakeCommuteService()
    monkeypatch.setattr(settings, "commute_refresh_token", "refresh-token")
    app.dependency_overrides[get_commute_service] = lambda: service
    client = TestClient(app)

    try:
        response = client.post("/api/commute/refresh", headers={"X-Commute-Refresh-Token": "refresh-token"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert service.refresh_calls == 1
    assert payload["status"] == "ready"
    assert payload["source"] == "tdx"
    assert payload["included_station_count"] == 2
    assert "stations" not in payload
    assert "token" not in str(payload).lower()


def test_refresh_bad_or_missing_token_returns_403_without_calling_service(monkeypatch) -> None:
    service = FakeCommuteService()
    monkeypatch.setattr(settings, "commute_refresh_token", "refresh-token")
    app.dependency_overrides[get_commute_service] = lambda: service
    client = TestClient(app)

    try:
        missing = client.post("/api/commute/refresh")
        wrong = client.post("/api/commute/refresh", headers={"X-Commute-Refresh-Token": "wrong"})
    finally:
        app.dependency_overrides.clear()

    assert missing.status_code == 403
    assert wrong.status_code == 403
    assert service.refresh_calls == 0


def test_refresh_missing_backend_token_returns_503_without_calling_service(monkeypatch) -> None:
    service = FakeCommuteService()
    monkeypatch.setattr(settings, "commute_refresh_token", None)
    app.dependency_overrides[get_commute_service] = lambda: service
    client = TestClient(app)

    try:
        response = client.post("/api/commute/refresh", headers={"X-Commute-Refresh-Token": "anything"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert service.refresh_calls == 0


def test_refresh_tdx_failure_returns_503(monkeypatch) -> None:
    service = FailingRefreshService()
    monkeypatch.setattr(settings, "commute_refresh_token", "refresh-token")
    app.dependency_overrides[get_commute_service] = lambda: service
    client = TestClient(app)

    try:
        response = client.post("/api/commute/refresh", headers={"X-Commute-Refresh-Token": "refresh-token"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert service.refresh_calls == 1
    assert "secret" not in response.text.lower()


def test_nearest_returns_minimized_result_and_does_not_refresh_tdx() -> None:
    service = FakeCommuteService()
    app.dependency_overrides[get_commute_service] = lambda: service
    client = TestClient(app)

    try:
        response = client.post("/api/commute/nearest", json={"latitude": 10.0, "longitude": 20.0})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert service.nearest_calls == 1
    assert service.refresh_calls == 0
    assert payload["status"] == "resolved"
    assert payload["source"] == "tdx"
    assert payload["station_name"] == "Nearest Test Station"
    assert payload["line_ids"] == ["L1", "L2"]
    assert "station_uid" not in payload
    assert "raw" not in str(payload).lower()
    assert "token" not in str(payload).lower()


def test_nearest_without_snapshot_returns_503() -> None:
    service = UnavailableNearestService()
    app.dependency_overrides[get_commute_service] = lambda: service
    client = TestClient(app)

    try:
        response = client.post("/api/commute/nearest", json={"latitude": 10.0, "longitude": 20.0})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert service.nearest_calls == 1
    assert service.refresh_calls == 0


def test_nearest_invalid_coordinates_return_422() -> None:
    service = FakeCommuteService()
    app.dependency_overrides[get_commute_service] = lambda: service
    client = TestClient(app)

    try:
        bad_lat = client.post("/api/commute/nearest", json={"latitude": 91.0, "longitude": 20.0})
        bad_lon = client.post("/api/commute/nearest", json={"latitude": 10.0, "longitude": 181.0})
    finally:
        app.dependency_overrides.clear()

    assert bad_lat.status_code == 422
    assert bad_lon.status_code == 422
    assert service.nearest_calls == 0


def test_status_returns_metadata_without_station_records() -> None:
    service = FakeCommuteService()
    app.dependency_overrides[get_commute_service] = lambda: service
    client = TestClient(app)

    try:
        response = client.get("/api/commute/status")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["available"] is True
    assert payload["source"] == "tdx"
    assert payload["included_station_count"] == 2
    assert "stations" not in payload
