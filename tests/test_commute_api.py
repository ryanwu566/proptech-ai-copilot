"""Commute API tests."""

from fastapi.testclient import TestClient

from backend.api_main import app
from services.commute_service import set_commute_snapshot_for_testing
from services.tdx_mrt_snapshot import build_tdx_mrt_snapshot


client = TestClient(app)


def setup_function() -> None:
    set_commute_snapshot_for_testing(None)


def teardown_function() -> None:
    set_commute_snapshot_for_testing(None)


def fake_snapshot():
    return build_tdx_mrt_snapshot(
        [
            {
                "StationUID": "ST-A",
                "StationName": {"Zh_tw": "虛構站A"},
                "StationPosition": {"PositionLat": 10.0, "PositionLon": 20.0},
                "SrcUpdateTime": "2026-01-01T00:00:00Z",
            }
        ],
        [{"LineID": "L1", "Stations": [{"StationUID": "ST-A"}]}],
        "2026-01-02T00:00:00Z",
    )


def assert_no_restricted_fields(result: dict[str, object]) -> None:
    serialized = str(result)
    for forbidden in (
        "address",
        "latitude",
        "longitude",
        "formatted_address",
        "station_uid",
        "StationUID",
        "station_position",
        "raw",
        "token",
        "secret",
        "provider",
    ):
        assert forbidden not in serialized


def test_refresh_without_token_is_forbidden(monkeypatch) -> None:
    monkeypatch.setenv("COMMUTE_REFRESH_TOKEN", "test-token")

    response = client.post("/commute/refresh")

    assert response.status_code == 403


def test_refresh_without_configured_token_is_unavailable(monkeypatch) -> None:
    monkeypatch.delenv("COMMUTE_REFRESH_TOKEN", raising=False)

    response = client.post("/commute/refresh", headers={"X-Commute-Refresh-Token": "test-token"})

    assert response.status_code == 503


def test_refresh_success_updates_status(monkeypatch) -> None:
    monkeypatch.setenv("COMMUTE_REFRESH_TOKEN", "test-token")
    monkeypatch.setattr(
        "services.commute_service.refresh_commute_snapshot",
        lambda: {
            "status": "resolved",
            "source": "tdx",
            "generated_at": "2026-01-02T00:00:00Z",
            "source_station_count": 1,
            "included_station_count": 1,
            "skipped_station_count": 0,
            "line_relation_available": True,
        },
    )

    response = client.post("/commute/refresh", headers={"X-Commute-Refresh-Token": "test-token"})

    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "resolved"
    assert result["source"] == "tdx"
    assert result["line_relation_available"] is True
    serialized = str(result)
    assert "StationUID" not in serialized
    assert "raw" not in serialized
    assert "token" not in serialized.lower()


def test_status_reports_unavailable_without_snapshot() -> None:
    response = client.get("/commute/status")

    assert response.status_code == 200
    assert response.json()["available"] is False


def test_nearest_without_snapshot_is_503_and_does_not_refresh(monkeypatch) -> None:
    called = {"refresh": 0}
    monkeypatch.setattr("services.commute_service.refresh_commute_snapshot", lambda: called.__setitem__("refresh", called["refresh"] + 1))

    response = client.post("/commute/nearest", json={"latitude": 10.0, "longitude": 20.0})

    assert response.status_code == 503
    assert called["refresh"] == 0


def test_nearest_success_returns_minimal_station_data() -> None:
    set_commute_snapshot_for_testing(fake_snapshot())

    response = client.post("/commute/nearest", json={"latitude": 10.01, "longitude": 20.01})

    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "resolved"
    assert result["source"] == "tdx"
    assert result["station_name"] == "虛構站A"
    assert result["line_ids"] == ["L1"]
    assert result["distance_meters"] > 0
    assert_no_restricted_fields({key: value for key, value in result.items() if key != "station_name"})


def test_nearest_rejects_invalid_coordinates() -> None:
    assert client.post("/commute/nearest", json={"latitude": 99.0, "longitude": 20.0}).status_code == 422
    assert client.post("/commute/nearest", json={"latitude": 10.0, "longitude": 199.0}).status_code == 422
