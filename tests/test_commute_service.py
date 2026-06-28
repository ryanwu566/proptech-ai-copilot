"""Commute service tests."""

import pytest

from services.commute_service import (
    ADDRESS_LOOKUP_NOTICE,
    CommuteServiceError,
    find_nearest_station,
    get_commute_status,
    refresh_commute_snapshot,
    set_commute_snapshot_for_testing,
)
from services.tdx_mrt_client import TdxMrtPayload
from services.tdx_mrt_snapshot import build_tdx_mrt_snapshot


class FakeClient:
    def __init__(self) -> None:
        self.calls = 0

    def refresh_payload(self) -> TdxMrtPayload:
        self.calls += 1
        return TdxMrtPayload(
            station_records=[
                {
                    "StationUID": "ST-A",
                    "StationName": {"Zh_tw": "虛構站A"},
                    "StationPosition": {"PositionLat": 10.0, "PositionLon": 20.0},
                    "SrcUpdateTime": "2026-01-01T00:00:00Z",
                },
                {
                    "StationUID": "ST-B",
                    "StationName": {"Zh_tw": "虛構站B"},
                    "StationPosition": {"PositionLat": 10.1, "PositionLon": 20.1},
                    "SrcUpdateTime": "2026-01-01T00:00:00Z",
                },
            ],
            line_records=[{"LineID": "L1", "Stations": [{"StationUID": "ST-A"}]}],
        )


def setup_function() -> None:
    set_commute_snapshot_for_testing(None)


def teardown_function() -> None:
    set_commute_snapshot_for_testing(None)


def test_refresh_updates_status_and_snapshot() -> None:
    client = FakeClient()

    result = refresh_commute_snapshot(client, generated_at="2026-01-02T00:00:00Z")
    status = get_commute_status()

    assert client.calls == 1
    assert result["status"] == "resolved"
    assert result["source"] == "tdx"
    assert result["included_station_count"] == 2
    assert result["line_relation_available"] is True
    assert status["available"] is True
    assert status["generated_at"] == "2026-01-02T00:00:00Z"


def test_nearest_uses_existing_snapshot_without_refreshing() -> None:
    snapshot = build_tdx_mrt_snapshot(
        [
            {
                "StationUID": "ST-A",
                "StationName": {"Zh_tw": "虛構站A"},
                "StationPosition": {"PositionLat": 10.0, "PositionLon": 20.0},
                "SrcUpdateTime": "2026-01-01T00:00:00Z",
            },
            {
                "StationUID": "ST-B",
                "StationName": {"Zh_tw": "虛構站B"},
                "StationPosition": {"PositionLat": 11.0, "PositionLon": 21.0},
                "SrcUpdateTime": "2026-01-01T00:00:00Z",
            },
        ],
        [{"LineID": "L1", "Stations": [{"StationUID": "ST-A"}]}],
        "2026-01-02T00:00:00Z",
    )
    set_commute_snapshot_for_testing(snapshot)

    result = find_nearest_station(10.01, 20.01, message=ADDRESS_LOOKUP_NOTICE)

    assert result["status"] == "resolved"
    assert result["source"] == "tdx"
    assert result["station_name"] == "虛構站A"
    assert result["line_ids"] == ["L1"]
    assert result["distance_meters"] > 0
    assert result["message"] == ADDRESS_LOOKUP_NOTICE
    serialized = str(result)
    assert "station_uid" not in serialized
    assert "StationUID" not in serialized
    assert "raw" not in serialized


def test_nearest_without_snapshot_fails_without_refreshing() -> None:
    with pytest.raises(CommuteServiceError):
        find_nearest_station(10.0, 20.0)
