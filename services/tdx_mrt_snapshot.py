"""TDX MRT snapshot transformer for offline commute lookup."""

from __future__ import annotations

import math
import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

SNAPSHOT_SCHEMA_VERSION = "tdx-mrt-v1"
STALE_AFTER_DAYS = 30


class TdxMrtSnapshotError(ValueError):
    """Raised when official station payloads violate the snapshot contract."""


@dataclass(frozen=True)
class CommuteStationSnapshot:
    station_uid: str
    station_name: str
    latitude: float
    longitude: float
    line_ids: tuple[str, ...]
    source_updated_at: str

    def to_safe_dict(self) -> dict[str, Any]:
        return {
            "station_uid": self.station_uid,
            "station_name": self.station_name,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "line_ids": list(self.line_ids),
            "source_updated_at": self.source_updated_at,
        }


@dataclass(frozen=True)
class CommuteSnapshot:
    source: str
    generated_at: str
    stations: tuple[CommuteStationSnapshot, ...]
    source_station_count: int
    included_station_count: int
    skipped_station_count: int
    line_relation_available: bool

    def to_status_dict(self) -> dict[str, Any]:
        station_content = json.dumps([station.to_safe_dict() for station in self.stations], ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return {
            "snapshot_schema_version": SNAPSHOT_SCHEMA_VERSION,
            "snapshot_version": "sha256:" + hashlib.sha256(station_content).hexdigest(),
            **self.freshness_metadata(),
            "source": self.source,
            "generated_at": self.generated_at,
            "source_station_count": self.source_station_count,
            "included_station_count": self.included_station_count,
            "skipped_station_count": self.skipped_station_count,
            "line_relation_available": self.line_relation_available,
        }

    def freshness_metadata(self) -> dict[str, Any]:
        """Evaluate actual SrcUpdateTime; refreshing old content cannot make it fresh."""
        checked_at = datetime.now(UTC)
        base = {"freshness_as_of": checked_at.isoformat(), "stale_after_days": STALE_AFTER_DAYS, "source_updated_at": None, "source_age_days": None}
        try:
            timestamps = [datetime.fromisoformat(station.source_updated_at.replace("Z", "+00:00")) for station in self.stations]
            if not timestamps or any(stamp.tzinfo is None for stamp in timestamps):
                raise ValueError("source time missing timezone")
        except (ValueError, TypeError):
            return {**base, "freshness_status": "unknown", "freshness_reason_code": "source_timestamp_invalid"}
        if any(stamp > checked_at for stamp in timestamps):
            return {**base, "freshness_status": "unknown", "freshness_reason_code": "source_timestamp_future"}
        oldest = min(timestamps).astimezone(UTC)
        age = (checked_at - oldest).days
        stale = age > STALE_AFTER_DAYS
        return {**base, "source_updated_at": oldest.isoformat(), "source_age_days": age, "freshness_status": "stale" if stale else "current", "freshness_reason_code": "snapshot_source_stale" if stale else "snapshot_source_current"}


def _as_non_empty_string(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _station_name(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if not isinstance(value, dict):
        return ""
    for key in ("Zh_tw", "zh_tw", "ZhTw", "zh-TW", "Name", "name", "En"):
        candidate = _as_non_empty_string(value.get(key))
        if candidate:
            return candidate
    return ""


def _coordinate(value: Any, *, minimum: float, maximum: float) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(parsed) or parsed < minimum or parsed > maximum:
        return None
    return parsed


def _station_uid(record: dict[str, Any]) -> str:
    return _as_non_empty_string(record.get("StationUID") or record.get("StationID"))


def _line_station_uid(record: Any) -> str:
    if isinstance(record, str):
        return record.strip()
    if not isinstance(record, dict):
        return ""
    direct = _as_non_empty_string(record.get("StationUID") or record.get("StationID"))
    if direct:
        return direct
    nested = record.get("Station")
    if isinstance(nested, dict):
        return _as_non_empty_string(nested.get("StationUID") or nested.get("StationID"))
    return ""


def _parse_station(record: Any) -> CommuteStationSnapshot | None:
    if not isinstance(record, dict):
        return None
    station_uid = _station_uid(record)
    station_name = _station_name(record.get("StationName"))
    position = record.get("StationPosition")
    source_updated_at = _as_non_empty_string(record.get("SrcUpdateTime"))
    if not station_uid or not station_name or not isinstance(position, dict) or not source_updated_at:
        return None
    latitude = _coordinate(position.get("PositionLat"), minimum=-90, maximum=90)
    longitude = _coordinate(position.get("PositionLon"), minimum=-180, maximum=180)
    if latitude is None or longitude is None:
        return None
    return CommuteStationSnapshot(
        station_uid=station_uid,
        station_name=station_name,
        latitude=latitude,
        longitude=longitude,
        line_ids=(),
        source_updated_at=source_updated_at,
    )


def _line_relations(line_records: list[dict[str, Any]]) -> dict[str, set[str]]:
    relations: dict[str, set[str]] = {}
    for line in line_records:
        if not isinstance(line, dict):
            continue
        line_id = _as_non_empty_string(line.get("LineID"))
        stations = line.get("Stations")
        if not line_id or not isinstance(stations, list):
            continue
        for station in stations:
            station_uid = _line_station_uid(station)
            if station_uid:
                relations.setdefault(station_uid, set()).add(line_id)
    return relations


def _merge_station(existing: CommuteStationSnapshot, incoming: CommuteStationSnapshot) -> CommuteStationSnapshot:
    if (
        existing.station_name != incoming.station_name
        or existing.latitude != incoming.latitude
        or existing.longitude != incoming.longitude
        or existing.source_updated_at != incoming.source_updated_at
    ):
        raise TdxMrtSnapshotError("Conflicting station records for the same identifier")
    return existing


def build_tdx_mrt_snapshot(
    station_records: list[dict[str, Any]],
    line_records: list[dict[str, Any]] | None,
    generated_at: str,
) -> CommuteSnapshot:
    """Build a minimal, serializable TDX MRT snapshot from official payloads."""

    stations_by_uid: dict[str, CommuteStationSnapshot] = {}
    source_station_count = len(station_records)
    for record in station_records:
        station = _parse_station(record)
        if station is None:
            continue
        existing = stations_by_uid.get(station.station_uid)
        stations_by_uid[station.station_uid] = _merge_station(existing, station) if existing else station

    if not stations_by_uid:
        raise TdxMrtSnapshotError("No valid station records for commute snapshot")

    relations = _line_relations(line_records or [])
    relation_applied = False
    merged: list[CommuteStationSnapshot] = []
    for station_uid in sorted(stations_by_uid):
        station = stations_by_uid[station_uid]
        line_ids = tuple(sorted(item for item in relations.get(station_uid, set()) if item))
        if line_ids:
            relation_applied = True
        merged.append(
            CommuteStationSnapshot(
                station_uid=station.station_uid,
                station_name=station.station_name,
                latitude=station.latitude,
                longitude=station.longitude,
                line_ids=line_ids,
                source_updated_at=station.source_updated_at,
            )
        )

    return CommuteSnapshot(
        source="tdx",
        generated_at=generated_at,
        stations=tuple(merged),
        source_station_count=source_station_count,
        included_station_count=len(merged),
        skipped_station_count=source_station_count - len(merged),
        line_relation_available=relation_applied,
    )
