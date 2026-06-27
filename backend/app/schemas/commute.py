from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CommuteStationSnapshot(BaseModel):
    station_uid: str
    station_name: str
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    line_ids: list[str]
    source_updated_at: datetime


class CommuteSnapshot(BaseModel):
    source: Literal["tdx"] = "tdx"
    generated_at: datetime
    stations: list[CommuteStationSnapshot]
    source_station_count: int
    included_station_count: int
    skipped_station_count: int
    line_relation_available: bool


class CommuteRefreshResponse(BaseModel):
    status: Literal["ready"]
    source: Literal["tdx"]
    generated_at: datetime
    source_station_count: int
    included_station_count: int
    skipped_station_count: int
    line_relation_available: bool


class CommuteNearestStationRequest(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class CommuteNearestStationResponse(BaseModel):
    status: Literal["resolved", "unavailable"]
    source: Literal["tdx", "none"]
    station_name: str | None = None
    line_ids: list[str] = Field(default_factory=list)
    distance_meters: float | None = None
    source_updated_at: datetime | None = None
    snapshot_generated_at: datetime | None = None
    message: str


class CommuteAddressLookupRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    address: str

    @field_validator("address")
    @classmethod
    def address_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("address is required")
        return value


class CommuteAddressLookupResponse(BaseModel):
    status: Literal["resolved", "unresolved", "unavailable"]
    source: Literal["tdx", "none"]
    station_name: str | None = None
    line_ids: list[str] = Field(default_factory=list)
    distance_meters: float | None = None
    source_updated_at: datetime | None = None
    snapshot_generated_at: datetime | None = None
    message: str


class CommuteStatusResponse(BaseModel):
    available: bool
    source: Literal["tdx", "none"]
    generated_at: datetime | None = None
    source_station_count: int | None = None
    included_station_count: int | None = None
    skipped_station_count: int | None = None
    line_relation_available: bool | None = None
