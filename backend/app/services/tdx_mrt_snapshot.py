from __future__ import annotations

import math
from datetime import datetime
from typing import Any, Iterable

from app.schemas.commute import CommuteSnapshot, CommuteStationSnapshot


class TdxMrtSnapshotContractError(ValueError):
    """Raised when TDX station records violate the snapshot contract."""


def build_tdx_mrt_snapshot(
    station_records: Iterable[dict[str, Any]],
    line_records: Iterable[dict[str, Any]] | None,
    generated_at: datetime,
) -> CommuteSnapshot:
    station_list = list(station_records)
    line_list = list(line_records or [])
    line_ids_by_station_identifier = _build_line_index(line_list)
    snapshots: dict[str, CommuteStationSnapshot] = {}
    skipped_count = 0

    for record in station_list:
        parsed = _parse_station_record(record, line_ids_by_station_identifier)
        if parsed is None:
            skipped_count += 1
            continue

        existing = snapshots.get(parsed.station_uid)
        if existing is None:
            snapshots[parsed.station_uid] = parsed
            continue

        _ensure_duplicate_is_consistent(existing, parsed)
        snapshots[parsed.station_uid] = existing.model_copy(
            update={"line_ids": sorted(set(existing.line_ids).union(parsed.line_ids))}
        )

    if not snapshots:
        raise TdxMrtSnapshotContractError("TDX MRT snapshot requires at least one valid station record.")

    stations = sorted(snapshots.values(), key=lambda station: station.station_uid)
    return CommuteSnapshot(
        generated_at=generated_at,
        stations=stations,
        source_station_count=len(station_list),
        included_station_count=len(stations),
        skipped_station_count=skipped_count,
        line_relation_available=any(station.line_ids for station in stations),
    )


def _parse_station_record(
    record: dict[str, Any],
    line_ids_by_station_identifier: dict[str, set[str]],
) -> CommuteStationSnapshot | None:
    station_uid = _clean_string(record.get("StationUID"))
    station_id = _clean_string(record.get("StationID"))
    station_name = _extract_station_name(record.get("StationName"))
    position = record.get("StationPosition")
    source_updated_at = _parse_datetime(record.get("SrcUpdateTime"))

    if not station_uid or not station_name or not isinstance(position, dict) or source_updated_at is None:
        return None

    latitude = _parse_coordinate(position.get("PositionLat"), minimum=-90, maximum=90)
    longitude = _parse_coordinate(position.get("PositionLon"), minimum=-180, maximum=180)
    if latitude is None or longitude is None:
        return None

    station_identifiers = {station_uid}
    if station_id:
        station_identifiers.add(station_id)
    line_ids = sorted({
        line_id
        for station_identifier in station_identifiers
        for line_id in line_ids_by_station_identifier.get(station_identifier, set())
        if line_id
    })
    return CommuteStationSnapshot(
        station_uid=station_uid,
        station_name=station_name,
        latitude=latitude,
        longitude=longitude,
        line_ids=line_ids,
        source_updated_at=source_updated_at,
    )


def _build_line_index(line_records: list[dict[str, Any]]) -> dict[str, set[str]]:
    line_ids_by_station_identifier: dict[str, set[str]] = {}
    for record in line_records:
        line_id = _clean_string(record.get("LineID"))
        stations = record.get("Stations")
        if not line_id or not isinstance(stations, list):
            continue

        for station in stations:
            if not isinstance(station, dict):
                continue
            station_identifier = _extract_line_station_identifier(station)
            if station_identifier:
                line_ids_by_station_identifier.setdefault(station_identifier, set()).add(line_id)
    return line_ids_by_station_identifier


def _extract_line_station_identifier(station: dict[str, Any]) -> str | None:
    direct_identifier = _clean_string(station.get("StationUID")) or _clean_string(station.get("StationID"))
    if direct_identifier:
        return direct_identifier

    nested_station = station.get("Station")
    if isinstance(nested_station, dict):
        return _clean_string(nested_station.get("StationUID")) or _clean_string(nested_station.get("StationID"))
    return None


def _extract_station_name(value: Any) -> str | None:
    if isinstance(value, str):
        return _clean_string(value)
    if isinstance(value, dict):
        for key in ("Zh_tw", "ZhTW", "zh_tw", "Name", "En"):
            name = _clean_string(value.get(key))
            if name:
                return name
    return None


def _parse_coordinate(value: Any, *, minimum: float, maximum: float) -> float | None:
    try:
        coordinate = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(coordinate) or coordinate < minimum or coordinate > maximum:
        return None
    return coordinate


def _parse_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    text = _clean_string(value)
    if not text:
        return None
    normalized = text.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def _clean_string(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text or None


def _ensure_duplicate_is_consistent(
    existing: CommuteStationSnapshot,
    candidate: CommuteStationSnapshot,
) -> None:
    if existing.station_name != candidate.station_name:
        raise TdxMrtSnapshotContractError("Conflicting station name for duplicate StationUID.")
    if existing.latitude != candidate.latitude or existing.longitude != candidate.longitude:
        raise TdxMrtSnapshotContractError("Conflicting station coordinates for duplicate StationUID.")
    if existing.source_updated_at != candidate.source_updated_at:
        raise TdxMrtSnapshotContractError("Conflicting source update time for duplicate StationUID.")
