"""Commute address lookup API tests."""

from fastapi.testclient import TestClient

from backend.api_main import app
from services.commute_service import ADDRESS_LOOKUP_NOTICE, set_commute_snapshot_for_testing
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


def assert_restricted_fields_absent(result: dict[str, object]) -> None:
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


def test_address_lookup_without_snapshot_does_not_call_location_resolver(monkeypatch) -> None:
    called = {"resolver": 0}

    def fake_resolve(address: str) -> dict[str, object]:
        called["resolver"] += 1
        return {"status": "resolved", "latitude": 10.0, "longitude": 20.0}

    monkeypatch.setattr("services.location_resolver.resolve_address", fake_resolve)

    response = client.post("/commute/address-lookup", json={"address": "虛構地址"})

    assert response.status_code == 503
    assert response.json()["status"] == "unavailable"
    assert called["resolver"] == 0


def test_address_lookup_blank_address_is_422_and_does_not_call_services(monkeypatch) -> None:
    called = {"resolver": 0, "nearest": 0}
    monkeypatch.setattr("services.location_resolver.resolve_address", lambda address: called.__setitem__("resolver", called["resolver"] + 1))
    monkeypatch.setattr("services.commute_service.find_nearest_station", lambda *args, **kwargs: called.__setitem__("nearest", called["nearest"] + 1))

    response = client.post("/commute/address-lookup", json={"address": " \n\t "})

    assert response.status_code == 422
    assert called == {"resolver": 0, "nearest": 0}


def test_address_lookup_unresolved_does_not_call_nearest(monkeypatch) -> None:
    set_commute_snapshot_for_testing(fake_snapshot())
    called = {"nearest": 0}
    monkeypatch.setattr("services.location_resolver.resolve_address", lambda address: {"status": "unresolved"})
    monkeypatch.setattr("services.commute_service.find_nearest_station", lambda *args, **kwargs: called.__setitem__("nearest", called["nearest"] + 1))

    response = client.post("/commute/address-lookup", json={"address": "虛構地址"})

    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "unresolved"
    assert result["source"] == "none"
    assert called["nearest"] == 0
    assert ADDRESS_LOOKUP_NOTICE not in result["message"]
    assert_restricted_fields_absent(result)


def test_address_lookup_unavailable_does_not_call_nearest(monkeypatch) -> None:
    set_commute_snapshot_for_testing(fake_snapshot())
    called = {"nearest": 0}
    monkeypatch.setattr("services.location_resolver.resolve_address", lambda address: {"status": "unavailable"})
    monkeypatch.setattr("services.commute_service.find_nearest_station", lambda *args, **kwargs: called.__setitem__("nearest", called["nearest"] + 1))

    response = client.post("/commute/address-lookup", json={"address": "虛構地址"})

    assert response.status_code == 503
    result = response.json()
    assert result["status"] == "unavailable"
    assert called["nearest"] == 0
    assert ADDRESS_LOOKUP_NOTICE not in result["message"]
    assert_restricted_fields_absent(result)


def test_address_lookup_resolved_returns_minimal_commute_result(monkeypatch) -> None:
    set_commute_snapshot_for_testing(fake_snapshot())
    called = {"resolver": 0}

    def fake_resolve(address: str) -> dict[str, object]:
        called["resolver"] += 1
        return {"status": "resolved", "latitude": 10.01, "longitude": 20.01, "formatted_address": "must not leak"}

    monkeypatch.setattr("services.location_resolver.resolve_address", fake_resolve)

    response = client.post("/commute/address-lookup", json={"address": "虛構地址"})

    assert response.status_code == 200
    result = response.json()
    assert called["resolver"] == 1
    assert result["status"] == "resolved"
    assert result["source"] == "tdx"
    assert result["station_name"] == "虛構站A"
    assert result["line_ids"] == ["L1"]
    assert result["distance_meters"] > 0
    assert result["source_updated_at"] == "2026-01-01T00:00:00Z"
    assert result["snapshot_generated_at"] == "2026-01-02T00:00:00Z"
    assert result["message"] == ADDRESS_LOOKUP_NOTICE
    assert_restricted_fields_absent({key: value for key, value in result.items() if key != "station_name"})


def test_address_lookup_does_not_call_refresh_or_tdx_client(monkeypatch) -> None:
    set_commute_snapshot_for_testing(fake_snapshot())
    called = {"refresh": 0}
    monkeypatch.setattr("services.location_resolver.resolve_address", lambda address: {"status": "resolved", "latitude": 10.01, "longitude": 20.01})
    monkeypatch.setattr("services.commute_service.refresh_commute_snapshot", lambda: called.__setitem__("refresh", called["refresh"] + 1))

    response = client.post("/commute/address-lookup", json={"address": "虛構地址"})

    assert response.status_code == 200
    assert called["refresh"] == 0
