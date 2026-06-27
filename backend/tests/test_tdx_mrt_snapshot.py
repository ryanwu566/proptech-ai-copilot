from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.services.tdx_mrt_snapshot import TdxMrtSnapshotContractError, build_tdx_mrt_snapshot


GENERATED_AT = datetime(2026, 1, 1, tzinfo=timezone.utc)
SOURCE_UPDATED_AT = "2026-01-02T00:00:00+00:00"


def station_record(
    uid: str = "S001",
    station_id: object = "SID001",
    name: object | None = None,
    lat: object = 10.5,
    lon: object = 20.5,
    source_updated_at: object = SOURCE_UPDATED_AT,
    extra: dict[str, object] | None = None,
) -> dict[str, object]:
    record: dict[str, object] = {
        "StationUID": uid,
        "StationID": station_id,
        "StationName": {"Zh_tw": "Test Station"} if name is None else name,
        "StationPosition": {"PositionLat": lat, "PositionLon": lon},
        "SrcUpdateTime": source_updated_at,
    }
    if extra:
        record.update(extra)
    return record


def line_record(line_id: str = "L2", stations: object | None = None) -> dict[str, object]:
    return {
        "LineID": line_id,
        "Stations": [{"StationUID": "S001"}] if stations is None else stations,
    }


def test_valid_station_and_line_records_build_minimized_snapshot() -> None:
    snapshot = build_tdx_mrt_snapshot(
        [station_record(extra={"StationAddress": "hidden", "UnusedField": "ignored"})],
        [line_record("L2"), line_record("L1")],
        GENERATED_AT,
    )

    assert snapshot.source == "tdx"
    assert snapshot.generated_at == GENERATED_AT
    assert snapshot.source_station_count == 1
    assert snapshot.included_station_count == 1
    assert snapshot.skipped_station_count == 0
    assert snapshot.line_relation_available is True

    station = snapshot.stations[0]
    assert station.station_uid == "S001"
    assert station.station_name == "Test Station"
    assert station.latitude == 10.5
    assert station.longitude == 20.5
    assert station.line_ids == ["L1", "L2"]
    assert station.source_updated_at.isoformat() == SOURCE_UPDATED_AT


def test_output_excludes_raw_payload_address_token_and_unknown_fields() -> None:
    snapshot = build_tdx_mrt_snapshot(
        [station_record(extra={"StationAddress": "hidden", "token": "secret", "RawPayload": {"x": 1}})],
        [line_record()],
        GENERATED_AT,
    )

    dumped = snapshot.model_dump()
    dumped_text = str(dumped)
    assert "StationAddress" not in dumped_text
    assert "RawPayload" not in dumped_text
    assert "token" not in dumped_text
    assert "hidden" not in dumped_text
    assert set(dumped["stations"][0]) == {
        "station_uid",
        "station_name",
        "latitude",
        "longitude",
        "line_ids",
        "source_updated_at",
    }


@pytest.mark.parametrize(
    "bad_record",
    [
        station_record(lat=91),
        station_record(lon=181),
        station_record(name={"En": ""}),
        station_record(source_updated_at=None),
    ],
)
def test_invalid_coordinate_missing_name_or_missing_source_time_are_skipped(bad_record: dict[str, object]) -> None:
    snapshot = build_tdx_mrt_snapshot(
        [station_record(uid="S001"), bad_record | {"StationUID": "BAD"}],
        [line_record()],
        GENERATED_AT,
    )

    assert snapshot.included_station_count == 1
    assert snapshot.skipped_station_count == 1
    assert [station.station_uid for station in snapshot.stations] == ["S001"]


def test_consistent_duplicate_station_uid_is_deduped_and_line_ids_are_merged() -> None:
    duplicate = station_record(uid="S001")
    snapshot = build_tdx_mrt_snapshot(
        [station_record(uid="S001"), duplicate],
        [line_record("L2"), line_record("L1"), line_record("L1")],
        GENERATED_AT,
    )

    assert snapshot.included_station_count == 1
    assert snapshot.stations[0].line_ids == ["L1", "L2"]


@pytest.mark.parametrize(
    "conflicting_record",
    [
        station_record(uid="S001", name={"Zh_tw": "Different Station"}),
        station_record(uid="S001", lat=11.5),
        station_record(uid="S001", lon=21.5),
    ],
)
def test_conflicting_duplicate_station_uid_fails(conflicting_record: dict[str, object]) -> None:
    with pytest.raises(TdxMrtSnapshotContractError):
        build_tdx_mrt_snapshot([station_record(uid="S001"), conflicting_record], [], GENERATED_AT)


def test_snapshot_builds_without_line_records_but_marks_relation_unavailable() -> None:
    snapshot = build_tdx_mrt_snapshot([station_record()], [], GENERATED_AT)

    assert snapshot.line_relation_available is False
    assert snapshot.stations[0].line_ids == []


def test_all_invalid_station_records_fail() -> None:
    with pytest.raises(TdxMrtSnapshotContractError):
        build_tdx_mrt_snapshot([station_record(lat="not-a-number")], [line_record()], GENERATED_AT)


def test_line_ids_drop_empty_values_and_sort_unique_values() -> None:
    snapshot = build_tdx_mrt_snapshot(
        [station_record(uid="S001")],
        [
            line_record("L9"),
            line_record(""),
            line_record("L1"),
            line_record("L9"),
        ],
        GENERATED_AT,
    )

    assert snapshot.stations[0].line_ids == ["L1", "L9"]


def test_line_relation_matches_station_records_by_station_id() -> None:
    snapshot = build_tdx_mrt_snapshot(
        [station_record(uid="S001", station_id="SID001")],
        [line_record("L1", stations=[{"StationUID": "S001"}, {"StationID": "SID001"}])],
        GENERATED_AT,
    )

    assert snapshot.line_relation_available is True
    assert snapshot.stations[0].line_ids == ["L1"]


def test_line_relation_matches_official_nested_station_identifier_shape() -> None:
    snapshot = build_tdx_mrt_snapshot(
        [station_record(uid="S001", station_id="SID001")],
        [line_record("L1", stations=[{"Station": {"StationID": "SID001"}}])],
        GENERATED_AT,
    )

    assert snapshot.line_relation_available is True
    assert snapshot.stations[0].line_ids == ["L1"]


def test_unrecognized_line_relation_is_skipped_and_marked_unavailable() -> None:
    snapshot = build_tdx_mrt_snapshot(
        [station_record(uid="S001", station_id="SID001")],
        [
            line_record("L1", stations=[{"StationName": {"Zh_tw": "No Identifier"}}]),
            line_record("L2", stations=[{"StationID": "UNKNOWN"}]),
        ],
        GENERATED_AT,
    )

    assert snapshot.line_relation_available is False
    assert snapshot.stations[0].line_ids == []


def test_station_name_can_be_plain_string() -> None:
    snapshot = build_tdx_mrt_snapshot(
        [station_record(name="Plain Test Station")],
        [line_record()],
        GENERATED_AT,
    )

    assert snapshot.stations[0].station_name == "Plain Test Station"
