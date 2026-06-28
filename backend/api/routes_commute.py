"""TDX MRT commute API routes."""

from __future__ import annotations

import math
import os
from typing import Literal

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator

from services import commute_service, location_resolver


router = APIRouter(prefix="/commute", tags=["commute"])


class CommuteRefreshResponse(BaseModel):
    status: Literal["resolved", "unavailable"]
    source: Literal["tdx", "none"]
    generated_at: str | None = None
    source_station_count: int
    included_station_count: int
    skipped_station_count: int
    line_relation_available: bool


class CommuteStatusResponse(BaseModel):
    available: bool
    source: Literal["tdx", "none"]
    generated_at: str | None = None
    source_station_count: int
    included_station_count: int
    skipped_station_count: int
    line_relation_available: bool


class CommuteNearestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)

    @field_validator("latitude", "longitude")
    @classmethod
    def coordinates_must_be_finite(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("coordinate must be finite")
        return value


class CommuteAddressLookupRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    address: str

    @field_validator("address")
    @classmethod
    def address_must_not_be_blank(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("address is required")
        return normalized


class CommuteLookupResponse(BaseModel):
    status: Literal["resolved", "unresolved", "unavailable"]
    source: Literal["tdx", "none"]
    station_name: str | None = None
    line_ids: list[str] = Field(default_factory=list)
    distance_meters: float | None = None
    source_updated_at: str | None = None
    snapshot_generated_at: str | None = None
    message: str


def _configured_refresh_token() -> str:
    return os.getenv("COMMUTE_REFRESH_TOKEN", "").strip()


def _unavailable_lookup(message: str, status_code: int = 503) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "unavailable",
            "source": "none",
            "station_name": None,
            "line_ids": [],
            "distance_meters": None,
            "source_updated_at": None,
            "snapshot_generated_at": None,
            "message": message,
        },
    )


def _unresolved_lookup(message: str) -> CommuteLookupResponse:
    return CommuteLookupResponse(status="unresolved", source="none", message=message)


@router.post("/refresh", response_model=CommuteRefreshResponse)
def post_commute_refresh(x_commute_refresh_token: str | None = Header(default=None)) -> dict[str, object]:
    expected_token = _configured_refresh_token()
    if not expected_token:
        raise HTTPException(status_code=503, detail="Commute refresh token is not configured")
    if x_commute_refresh_token != expected_token:
        raise HTTPException(status_code=403, detail="Commute refresh is not authorized")
    try:
        return commute_service.refresh_commute_snapshot()
    except commute_service.CommuteServiceError:
        return {
            "status": "unavailable",
            "source": "none",
            "generated_at": None,
            "source_station_count": 0,
            "included_station_count": 0,
            "skipped_station_count": 0,
            "line_relation_available": False,
        }


@router.get("/status", response_model=CommuteStatusResponse)
def get_commute_status() -> dict[str, object]:
    return commute_service.get_commute_status()


@router.post("/nearest", response_model=CommuteLookupResponse)
def post_commute_nearest(request: CommuteNearestRequest) -> CommuteLookupResponse | JSONResponse:
    try:
        return CommuteLookupResponse(**commute_service.find_nearest_station(request.latitude, request.longitude))
    except commute_service.CommuteServiceError:
        return _unavailable_lookup("通勤資料尚未更新，暫時無法提供最近捷運站資訊。")


@router.post("/address-lookup", response_model=CommuteLookupResponse)
def post_commute_address_lookup(request: CommuteAddressLookupRequest) -> CommuteLookupResponse | JSONResponse:
    if not commute_service.has_commute_snapshot():
        return _unavailable_lookup("通勤資料尚未更新，暫時無法提供最近捷運站資訊。")

    resolved_location = location_resolver.resolve_address(request.address)
    if resolved_location.get("status") == "unresolved":
        return _unresolved_lookup("找不到可信位置，請確認縣市、區域與門牌是否完整。")
    if resolved_location.get("status") != "resolved":
        return _unavailable_lookup("定位服務暫時無法完成查詢，請稍後再試。")

    latitude = resolved_location.get("latitude")
    longitude = resolved_location.get("longitude")
    if not isinstance(latitude, (int, float)) or not isinstance(longitude, (int, float)):
        return _unavailable_lookup("定位服務暫時無法完成查詢，請稍後再試。")
    try:
        result = commute_service.find_nearest_station(
            float(latitude),
            float(longitude),
            message=commute_service.ADDRESS_LOOKUP_NOTICE,
        )
    except commute_service.CommuteServiceError:
        return _unavailable_lookup("通勤資料尚未更新，暫時無法提供最近捷運站資訊。")
    return CommuteLookupResponse(**result)
