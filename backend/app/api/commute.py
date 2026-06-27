from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, Header, HTTPException, status

from app.core.config import settings
from app.schemas.commute import (
    CommuteAddressLookupRequest,
    CommuteAddressLookupResponse,
    CommuteNearestStationRequest,
    CommuteNearestStationResponse,
    CommuteRefreshResponse,
    CommuteStatusResponse,
)
from app.services.commute_service import CommuteService, get_commute_service
from app.services.location_resolver import LocationResolver, build_location_resolver
from app.services.tdx_mrt_client import TdxMrtClientError
from app.services.tdx_mrt_snapshot import TdxMrtSnapshotContractError

router = APIRouter(prefix="/commute", tags=["commute"])

COMMUTE_ADDRESS_LOOKUP_DISCLAIMER = "僅供通勤與生活機能參考，不影響地勢災害、貸款、法律或看房結論。"


@router.post("/refresh", response_model=CommuteRefreshResponse)
def refresh_commute_snapshot(
    x_commute_refresh_token: str | None = Header(default=None),
    service: CommuteService = Depends(get_commute_service),
) -> CommuteRefreshResponse:
    expected_token = settings.commute_refresh_token
    if not expected_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Commute refresh is not configured.",
        )
    if not x_commute_refresh_token or not secrets.compare_digest(x_commute_refresh_token, expected_token):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden.")

    try:
        return service.refresh_from_tdx()
    except TdxMrtClientError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"TDX refresh failed: {exc.failure_class}.",
        ) from exc
    except TdxMrtSnapshotContractError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="TDX refresh returned unusable station data.",
        ) from exc


@router.post("/nearest", response_model=CommuteNearestStationResponse)
def find_nearest_commute_station(
    payload: CommuteNearestStationRequest,
    service: CommuteService = Depends(get_commute_service),
) -> CommuteNearestStationResponse:
    result = service.find_nearest_station(latitude=payload.latitude, longitude=payload.longitude)
    if result.status == "unavailable":
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=result.message)
    return result


@router.post("/address-lookup", response_model=CommuteAddressLookupResponse)
def lookup_commute_station_by_address(
    payload: CommuteAddressLookupRequest,
    service: CommuteService = Depends(get_commute_service),
    resolver: LocationResolver = Depends(build_location_resolver),
) -> CommuteAddressLookupResponse:
    commute_status = service.get_status()
    if not commute_status.available:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="通勤資料尚未更新，暫時無法提供最近捷運站資訊。",
        )

    location = resolver.resolve(payload.address)
    if location.status == "unresolved":
        return CommuteAddressLookupResponse(
            status="unresolved",
            source="none",
            message="找不到可信位置，請確認縣市、區域與門牌是否完整。",
        )
    if location.status != "resolved" or location.latitude is None or location.longitude is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="定位服務暫時無法完成查詢，請稍後再試。",
        )

    nearest = service.find_nearest_station(latitude=location.latitude, longitude=location.longitude)
    if nearest.status != "resolved":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="通勤資料尚未更新，暫時無法提供最近捷運站資訊。",
        )

    return CommuteAddressLookupResponse(
        status="resolved",
        source="tdx",
        station_name=nearest.station_name,
        line_ids=nearest.line_ids,
        distance_meters=nearest.distance_meters,
        source_updated_at=nearest.source_updated_at,
        snapshot_generated_at=nearest.snapshot_generated_at,
        message=f"已取得最近捷運站資訊。{COMMUTE_ADDRESS_LOOKUP_DISCLAIMER}",
    )


@router.get("/status", response_model=CommuteStatusResponse)
def get_commute_snapshot_status(
    service: CommuteService = Depends(get_commute_service),
) -> CommuteStatusResponse:
    return service.get_status()
