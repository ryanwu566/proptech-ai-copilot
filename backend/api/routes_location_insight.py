"""Decision-oriented location insight API."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field, model_validator

from services.location_insight_service import analyze_location


router = APIRouter(prefix="/location", tags=["location-insight"])


class LocationInsightRequest(BaseModel):
    city: str = ""
    district: str = ""
    road: str = ""
    address: str = ""
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    radius_m: int = Field(default=800, ge=100, le=1500)
    property_price: float | None = Field(default=None, gt=0)
    area_ping: float | None = Field(default=None, gt=0)
    building_type: str = ""
    use_existing_poi_sources: bool = True

    @model_validator(mode="after")
    def coordinates_are_paired(self) -> "LocationInsightRequest":
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("latitude and longitude must be provided together")
        return self


@router.post("/insight")
def post_location_insight(request: LocationInsightRequest) -> dict[str, Any]:
    return analyze_location(**request.model_dump())
