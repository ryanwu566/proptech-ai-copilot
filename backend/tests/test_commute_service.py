from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.services.commute_service import CommuteService
from app.services.tdx_mrt_client import TdxMrtClientError


SOURCE_UPDATED_AT = "2026-01-02T00:00:00+00:00"


def station_record(uid: str, name: str, lat: float, lon: float) -> dict[str, object]:
    return {
        "StationUID": uid,
        "StationName": {"Zh_tw": name},
        "StationPosition": {"PositionLat": lat, "PositionLon": lon},
        "SrcUpdateTime": SOURCE_UPDATED_AT,
    }


def line_record(line_id: str, station_uids: list[str]) -> dict[str, object]:
    return {
        "LineID": line_id,
        "Stations": [{"StationUID": station_uid} for station_uid in station_uids],
    }


class FakeTdxClient:
    def __init__(self, station_records: list[dict[str, object]], line_records: list[dict[str, object]]) -> None:
        self.station_records = station_records
        self.line_records = line_records
        self.calls = 0

    def fetch_station_and_line_records(self) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
        self.calls += 1
        return self.station_records, self.line_records


class FailingTdxClient:
    def fetch_station_and_line_records(self) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
        raise TdxMrtClientError("service_unavailable")


def test_refresh_builds_snapshot_and_nearest_station_uses_haversine() -> None:
    client = FakeTdxClient(
        [
            station_record("S001", "Near Station", 10.0, 20.0),
            station_record("S002", "Far Station", 11.0, 21.0),
        ],
        [line_record("L2", ["S001"]), line_record("L1", ["S001", "S002"])],
    )
    service = CommuteService(client)

    refresh = service.refresh_from_tdx()
    nearest = service.find_nearest_station(latitude=10.001, longitude=20.001)

    assert refresh.status == "ready"
    assert refresh.included_station_count == 2
    assert nearest.status == "resolved"
    assert nearest.source == "tdx"
    assert nearest.station_name == "Near Station"
    assert nearest.line_ids == ["L1", "L2"]
    assert nearest.distance_meters is not None and nearest.distance_meters > 0
    assert nearest.source_updated_at is not None
    assert nearest.snapshot_generated_at is not None


def test_equal_distance_uses_station_uid_tie_break_without_returning_uid() -> None:
    service = CommuteService(
        FakeTdxClient(
            [
                station_record("S002", "Second Station", 10.0, 20.0),
                station_record("S001", "First Station", 10.0, 20.0),
            ],
            [],
        )
    )
    service.refresh_from_tdx()

    nearest = service.find_nearest_station(latitude=10.0, longitude=20.0)
    dumped = nearest.model_dump()

    assert nearest.station_name == "First Station"
    assert "station_uid" not in dumped


def test_no_snapshot_returns_unavailable_and_does_not_call_tdx() -> None:
    client = FakeTdxClient([], [])
    service = CommuteService(client)

    result = service.find_nearest_station(latitude=10.0, longitude=20.0)

    assert result.status == "unavailable"
    assert result.source == "none"
    assert client.calls == 0


def test_refresh_failure_keeps_previous_snapshot_available() -> None:
    service = CommuteService(
        FakeTdxClient([station_record("S001", "Existing Station", 10.0, 20.0)], [])
    )
    service.refresh_from_tdx()
    service._tdx_client = FailingTdxClient()  # noqa: SLF001

    with pytest.raises(TdxMrtClientError):
        service.refresh_from_tdx()

    nearest = service.find_nearest_station(latitude=10.0, longitude=20.0)
    assert nearest.status == "resolved"
    assert nearest.station_name == "Existing Station"


def test_invalid_coordinates_raise_value_error() -> None:
    service = CommuteService(FakeTdxClient([station_record("S001", "Station", 10.0, 20.0)], []))
    service.refresh_from_tdx()

    with pytest.raises(ValueError):
        service.find_nearest_station(latitude=91.0, longitude=20.0)

    with pytest.raises(ValueError):
        service.find_nearest_station(latitude=10.0, longitude=181.0)


def test_status_hides_station_records_and_reports_metadata_only() -> None:
    service = CommuteService(FakeTdxClient([station_record("S001", "Station", 10.0, 20.0)], []))

    empty_status = service.get_status()
    assert empty_status.available is False
    assert empty_status.source == "none"

    service.refresh_from_tdx()
    status = service.get_status()
    dumped = status.model_dump()

    assert status.available is True
    assert status.source == "tdx"
    assert status.included_station_count == 1
    assert "stations" not in dumped
    assert "station_uid" not in dumped
