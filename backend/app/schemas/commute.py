from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


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
