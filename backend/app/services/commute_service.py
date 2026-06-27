from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Lock
from typing import Protocol

from app.schemas.commute import (
    CommuteNearestStationResponse,
    CommuteRefreshResponse,
    CommuteSnapshot,
    CommuteStatusResponse,
    CommuteStationSnapshot,
)
from app.services.tdx_mrt_client import TdxMrtClient, build_tdx_mrt_client
from app.services.tdx_mrt_snapshot import build_tdx_mrt_snapshot

EARTH_RADIUS_METERS = 6_371_000


class TdxMrtRecordClient(Protocol):
    def fetch_station_and_line_records(self) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
        ...


@dataclass(slots=True)
class NearestStationResult:
    station: CommuteStationSnapshot
    distance_meters: float
    snapshot_generated_at: datetime


class CommuteService:
    def __init__(self, tdx_client: TdxMrtRecordClient | None = None) -> None:
        self._tdx_client = tdx_client or build_tdx_mrt_client()
        self._snapshot: CommuteSnapshot | None = None
        self._lock = Lock()

    def refresh_from_tdx(self) -> CommuteRefreshResponse:
        station_records, line_records = self._tdx_client.fetch_station_and_line_records()
        next_snapshot = build_tdx_mrt_snapshot(
            station_records=station_records,
            line_records=line_records,
            generated_at=datetime.now(timezone.utc),
        )
        with self._lock:
            self._snapshot = next_snapshot
        return _to_refresh_response(next_snapshot)

    def find_nearest_station(self, latitude: float, longitude: float) -> CommuteNearestStationResponse:
        _validate_coordinate(latitude=latitude, longitude=longitude)
        with self._lock:
            snapshot = self._snapshot

        if snapshot is None:
            return CommuteNearestStationResponse(
                status="unavailable",
                source="none",
                message="捷運通勤資料尚未建立，請先完成官方資料刷新。",
            )

        nearest: NearestStationResult | None = None
        for station in snapshot.stations:
            distance = _haversine_meters(latitude, longitude, station.latitude, station.longitude)
            candidate = NearestStationResult(
                station=station,
                distance_meters=distance,
                snapshot_generated_at=snapshot.generated_at,
            )
            if _is_better_candidate(candidate, nearest):
                nearest = candidate

        if nearest is None:
            return CommuteNearestStationResponse(
                status="unavailable",
                source="none",
                message="捷運通勤資料暫時無法提供最近站結果。",
            )

        return CommuteNearestStationResponse(
            status="resolved",
            source="tdx",
            station_name=nearest.station.station_name,
            line_ids=nearest.station.line_ids,
            distance_meters=round(nearest.distance_meters, 2),
            source_updated_at=nearest.station.source_updated_at,
            snapshot_generated_at=nearest.snapshot_generated_at,
            message="最近捷運站僅供通勤生活圈初步參考，仍需確認實際步行路線與出入口狀況。",
        )

    def get_status(self) -> CommuteStatusResponse:
        with self._lock:
            snapshot = self._snapshot
        if snapshot is None:
            return CommuteStatusResponse(available=False, source="none")
        return CommuteStatusResponse(
            available=True,
            source="tdx",
            generated_at=snapshot.generated_at,
            source_station_count=snapshot.source_station_count,
            included_station_count=snapshot.included_station_count,
            skipped_station_count=snapshot.skipped_station_count,
            line_relation_available=snapshot.line_relation_available,
        )


def _to_refresh_response(snapshot: CommuteSnapshot) -> CommuteRefreshResponse:
    return CommuteRefreshResponse(
        status="ready",
        source="tdx",
        generated_at=snapshot.generated_at,
        source_station_count=snapshot.source_station_count,
        included_station_count=snapshot.included_station_count,
        skipped_station_count=snapshot.skipped_station_count,
        line_relation_available=snapshot.line_relation_available,
    )


def _validate_coordinate(*, latitude: float, longitude: float) -> None:
    if not math.isfinite(latitude) or latitude < -90 or latitude > 90:
        raise ValueError("latitude_out_of_range")
    if not math.isfinite(longitude) or longitude < -180 or longitude > 180:
        raise ValueError("longitude_out_of_range")


def _haversine_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    a = math.sin(delta_lat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    return 2 * EARTH_RADIUS_METERS * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _is_better_candidate(candidate: NearestStationResult, current: NearestStationResult | None) -> bool:
    if current is None:
        return True
    if candidate.distance_meters < current.distance_meters:
        return True
    if candidate.distance_meters > current.distance_meters:
        return False
    return candidate.station.station_uid < current.station.station_uid


commute_service = CommuteService()


def get_commute_service() -> CommuteService:
    return commute_service
