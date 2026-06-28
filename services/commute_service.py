"""In-memory MRT commute service."""

from __future__ import annotations

import math
import threading
from datetime import UTC, datetime
from typing import Any

from services.tdx_mrt_client import TdxMrtClient, TdxMrtClientError
from services.tdx_mrt_snapshot import CommuteSnapshot, CommuteStationSnapshot, TdxMrtSnapshotError, build_tdx_mrt_snapshot


ADDRESS_LOOKUP_NOTICE = "僅供通勤與生活機能參考，不影響地勢災害、貸款、法律或看房結論。"

_snapshot_lock = threading.RLock()
_snapshot: CommuteSnapshot | None = None


class CommuteServiceError(RuntimeError):
    """Raised when commute service cannot provide data."""


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def refresh_commute_snapshot(client: TdxMrtClient | None = None, generated_at: str | None = None) -> dict[str, Any]:
    """Refresh the in-memory snapshot from TDX through a backend-only client."""

    global _snapshot
    active_client = client or TdxMrtClient()
    try:
        payload = active_client.refresh_payload()
        snapshot = build_tdx_mrt_snapshot(payload.station_records, payload.line_records, generated_at or _now_iso())
    except (TdxMrtClientError, TdxMrtSnapshotError) as exc:
        raise CommuteServiceError("Commute snapshot refresh is unavailable") from exc
    with _snapshot_lock:
        _snapshot = snapshot
    return {"status": "resolved", **snapshot.to_status_dict()}


def get_commute_status() -> dict[str, Any]:
    with _snapshot_lock:
        snapshot = _snapshot
    if snapshot is None:
        return {
            "available": False,
            "source": "none",
            "generated_at": None,
            "source_station_count": 0,
            "included_station_count": 0,
            "skipped_station_count": 0,
            "line_relation_available": False,
        }
    return {"available": True, **snapshot.to_status_dict()}


def set_commute_snapshot_for_testing(snapshot: CommuteSnapshot | None) -> None:
    global _snapshot
    with _snapshot_lock:
        _snapshot = snapshot


def has_commute_snapshot() -> bool:
    with _snapshot_lock:
        return _snapshot is not None


def _haversine_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_m = 6_371_000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * radius_m * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _nearest_station(snapshot: CommuteSnapshot, latitude: float, longitude: float) -> tuple[CommuteStationSnapshot, float]:
    nearest: tuple[CommuteStationSnapshot, float] | None = None
    for station in snapshot.stations:
        distance = _haversine_meters(latitude, longitude, station.latitude, station.longitude)
        if nearest is None or distance < nearest[1]:
            nearest = (station, distance)
    if nearest is None:
        raise CommuteServiceError("Commute snapshot has no station records")
    return nearest


def find_nearest_station(latitude: float, longitude: float, *, message: str | None = None) -> dict[str, Any]:
    with _snapshot_lock:
        snapshot = _snapshot
    if snapshot is None:
        raise CommuteServiceError("Commute snapshot is unavailable")
    station, distance = _nearest_station(snapshot, latitude, longitude)
    return {
        "status": "resolved",
        "source": "tdx",
        "station_name": station.station_name,
        "line_ids": list(station.line_ids),
        "distance_meters": round(distance, 1),
        "source_updated_at": station.source_updated_at,
        "snapshot_generated_at": snapshot.generated_at,
        "message": message or "已取得最近捷運站資訊。",
    }
