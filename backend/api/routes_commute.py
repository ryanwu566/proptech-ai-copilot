"""TDX MRT commute API routes."""

from __future__ import annotations

import math
import os
from typing import Literal

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from services import commute_routing_service, commute_service, location_resolver


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


class CommuteRouteRequest(BaseModel):
    """Single origin -> destination travel-time request for a bounded mode.

    ``destination`` accepts either a coordinate pair or a text address (resolved via
    the trusted location resolver). Exactly one destination form must be provided.
    """

    model_config = ConfigDict(extra="forbid")

    origin_latitude: float = Field(ge=-90, le=90)
    origin_longitude: float = Field(ge=-180, le=180)
    destination_address: str | None = None
    destination_latitude: float | None = Field(default=None, ge=-90, le=90)
    destination_longitude: float | None = Field(default=None, ge=-180, le=180)
    mode: Literal["transit", "driving", "walking"] = "transit"

    @field_validator("origin_latitude", "origin_longitude")
    @classmethod
    def origin_must_be_finite(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("coordinate must be finite")
        return value

    @field_validator("destination_address")
    @classmethod
    def address_not_blank_when_present(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @model_validator(mode="after")
    def exactly_one_destination(self) -> "CommuteRouteRequest":
        has_coord = self.destination_latitude is not None and self.destination_longitude is not None
        half_coord = (self.destination_latitude is None) != (self.destination_longitude is None)
        if half_coord:
            raise ValueError("destination latitude and longitude must be provided together")
        has_address = bool(self.destination_address)
        if has_coord and has_address:
            raise ValueError("provide either a destination address or coordinate, not both")
        if not has_coord and not has_address:
            raise ValueError("a destination address or coordinate is required")
        if has_coord and not (math.isfinite(self.destination_latitude) and math.isfinite(self.destination_longitude)):
            raise ValueError("destination coordinate must be finite")
        return self


class CommuteRouteResponse(BaseModel):
    status: Literal["resolved", "unresolved", "unavailable"]
    source: Literal["google_routes", "mock", "none"]
    mode: Literal["transit", "driving", "walking"]
    duration_min: int | None = None
    duration_seconds: int | None = None
    distance_m: int | None = None
    partial: bool
    fallback: bool
    message: str
    disclaimer: str


def _route_unavailable(mode: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content={
            "status": "unavailable",
            "source": "none",
            "mode": mode,
            "duration_min": None,
            "duration_seconds": None,
            "distance_m": None,
            "partial": False,
            "fallback": False,
            "message": message,
            "disclaimer": commute_routing_service.ROUTE_DISCLAIMER,
        },
    )


def _route_unresolved(mode: str, message: str) -> CommuteRouteResponse:
    return CommuteRouteResponse(
        status="unresolved",
        source="none",
        mode=mode,  # type: ignore[arg-type]
        partial=False,
        fallback=False,
        message=message,
        disclaimer=commute_routing_service.ROUTE_DISCLAIMER,
    )


@router.post("/route", response_model=CommuteRouteResponse)
def post_commute_route(request: CommuteRouteRequest) -> CommuteRouteResponse | JSONResponse:
    """Estimate travel time/distance from a property origin to a destination."""

    if request.destination_latitude is not None and request.destination_longitude is not None:
        destination = (float(request.destination_latitude), float(request.destination_longitude))
    else:
        resolved = location_resolver.resolve_address(request.destination_address or "")
        status = resolved.get("status")
        if status == "unresolved":
            return _route_unresolved(request.mode, "找不到可信的目的地位置，請確認地址是否完整。")
        if status != "resolved":
            return _route_unavailable(request.mode, "目的地定位服務暫時無法完成查詢，請稍後再試。")
        dest_lat = resolved.get("latitude")
        dest_lng = resolved.get("longitude")
        if not isinstance(dest_lat, (int, float)) or not isinstance(dest_lng, (int, float)):
            return _route_unavailable(request.mode, "目的地定位服務暫時無法完成查詢，請稍後再試。")
        destination = (float(dest_lat), float(dest_lng))

    try:
        result = commute_routing_service.estimate_commute_route(
            (float(request.origin_latitude), float(request.origin_longitude)),
            destination,
            request.mode,
        )
    except commute_routing_service.InvalidRouteRequestError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return CommuteRouteResponse(**result)
