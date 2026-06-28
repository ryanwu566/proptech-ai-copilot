"""TDX MRT snapshot transformer tests."""

import pytest

from services.tdx_mrt_snapshot import TdxMrtSnapshotError, build_tdx_mrt_snapshot


def station(uid: str = "ST-A", name: object | None = None, lat: object = 10.0, lon: object = 20.0, updated: object = "2026-01-01T00:00:00Z") -> dict[str, object]:
    return {
        "StationUID": uid,
        "StationName": name if name is not None else {"Zh_tw": "虛構站A"},
        "StationPosition": {"PositionLat": lat, "PositionLon": lon},
        "SrcUpdateTime": updated,
        "StationAddress": "must not persist",
    }


def line(line_id: str = "L1", station_uid: str = "ST-A") -> dict[str, object]:
    return {"LineID": line_id, "Stations": [{"StationUID": station_uid, "StationName": {"Zh_tw": "ignored"}}]}


def test_valid_station_and_line_records_build_minimal_snapshot() -> None:
    snapshot = build_tdx_mrt_snapshot([station()], [line()], "2026-01-02T00:00:00Z")

    assert snapshot.source == "tdx"
    assert snapshot.generated_at == "2026-01-02T00:00:00Z"
    assert snapshot.source_station_count == 1
    assert snapshot.included_station_count == 1
    assert snapshot.skipped_station_count == 0
    assert snapshot.line_relation_available is True
    record = snapshot.stations[0].to_safe_dict()
    assert record == {
        "station_uid": "ST-A",
        "station_name": "虛構站A",
        "latitude": 10.0,
        "longitude": 20.0,
        "line_ids": ["L1"],
        "source_updated_at": "2026-01-01T00:00:00Z",
    }
    serialized = str(snapshot.to_status_dict()) + str(record)
    assert "StationAddress" not in serialized
    assert "token" not in serialized
    assert "raw" not in serialized


def test_line_ids_are_merged_deduped_and_sorted() -> None:
    snapshot = build_tdx_mrt_snapshot(
        [station()],
        [
            {"LineID": "L2", "Stations": [{"Station": {"StationUID": "ST-A"}}]},
            {"LineID": "L1", "Stations": [{"StationUID": "ST-A"}, {"StationID": "ST-A"}]},
            {"LineID": "L2", "Stations": ["ST-A"]},
        ],
        "2026-01-02T00:00:00Z",
    )

    assert snapshot.stations[0].line_ids == ("L1", "L2")
    assert snapshot.line_relation_available is True


def test_invalid_station_records_are_skipped() -> None:
    snapshot = build_tdx_mrt_snapshot(
        [
            station(uid="BAD-COORD", lat="999"),
            station(uid="BAD-NAME", name={}),
            station(uid="BAD-DATE", updated=""),
            station(uid="ST-OK"),
        ],
        [],
        "2026-01-02T00:00:00Z",
    )

    assert snapshot.source_station_count == 4
    assert snapshot.included_station_count == 1
    assert snapshot.skipped_station_count == 3
    assert snapshot.line_relation_available is False


def test_duplicate_consistent_station_records_are_deduped() -> None:
    snapshot = build_tdx_mrt_snapshot([station(), station()], [line()], "2026-01-02T00:00:00Z")

    assert snapshot.included_station_count == 1
    assert len(snapshot.stations) == 1


def test_duplicate_conflicting_station_records_fail() -> None:
    with pytest.raises(TdxMrtSnapshotError):
        build_tdx_mrt_snapshot([station(), station(name={"Zh_tw": "虛構站B"})], [], "2026-01-02T00:00:00Z")


def test_missing_line_records_do_not_block_snapshot() -> None:
    snapshot = build_tdx_mrt_snapshot([station()], None, "2026-01-02T00:00:00Z")

    assert snapshot.included_station_count == 1
    assert snapshot.stations[0].line_ids == ()
    assert snapshot.line_relation_available is False


def test_invalid_line_relation_is_skipped_without_breaking_snapshot() -> None:
    snapshot = build_tdx_mrt_snapshot(
        [station()],
        [{"LineID": "", "Stations": [{"StationUID": "ST-A"}]}, {"LineID": "L1", "Stations": [{"unknown": "ST-A"}]}],
        "2026-01-02T00:00:00Z",
    )

    assert snapshot.stations[0].line_ids == ()
    assert snapshot.line_relation_available is False


def test_all_invalid_stations_fail() -> None:
    with pytest.raises(TdxMrtSnapshotError):
        build_tdx_mrt_snapshot([station(lat="not-a-number"), station(updated="")], [], "2026-01-02T00:00:00Z")
