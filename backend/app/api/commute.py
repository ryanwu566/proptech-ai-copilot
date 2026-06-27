from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, Header, HTTPException, status

from app.core.config import settings
from app.schemas.commute import (
    CommuteNearestStationRequest,
    CommuteNearestStationResponse,
    CommuteRefreshResponse,
    CommuteStatusResponse,
)
from app.services.commute_service import CommuteService, get_commute_service
from app.services.tdx_mrt_client import TdxMrtClientError
from app.services.tdx_mrt_snapshot import TdxMrtSnapshotContractError

router = APIRouter(prefix="/commute", tags=["commute"])


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


@router.get("/status", response_model=CommuteStatusResponse)
def get_commute_snapshot_status(
    service: CommuteService = Depends(get_commute_service),
) -> CommuteStatusResponse:
    return service.get_status()
