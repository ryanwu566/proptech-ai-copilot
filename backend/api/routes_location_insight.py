"""Decision-oriented location insight API."""

from __future__ import annotations

from typing import Any, Literal

from services.input_limits import BoundedInputModel
from services.anti_abuse import provider_operation

from fastapi import APIRouter
from pydantic import BaseModel, Field, field_validator, model_validator

from services import location_resolver
from services.location_insight_service import analyze_location
from services.ris_village_resolver import get_default_ris_village_resolver


router = APIRouter(prefix="/location", tags=["location-insight"])


class LocationInsightRequest(BoundedInputModel):
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


class LocationResolveRequest(BoundedInputModel):
    address: str

    @field_validator("address")
    @classmethod
    def address_must_not_be_blank(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("address is required")
        return normalized


class LocationResolveCandidate(BaseModel):
    """One bounded provider candidate; blocked candidates are shown but never confirmable."""

    source: Literal["tgos", "google"]
    formatted_address: str | None = None
    latitude: float
    longitude: float
    county: str | None = None
    district: str | None = None
    postal_code: str | None = None
    place_id: str | None = None
    admin_check: Literal["consistent", "county_unverified", "county_mismatch", "district_mismatch"]
    confirmable: bool
    block_reason: Literal["administrative_mismatch", "address_mismatch", "low_precision"] | None = None


class LocationResolveResponse(BaseModel):
    status: Literal["resolved", "ambiguous", "unresolved", "unavailable"]
    source: Literal["tgos", "google", "none"]
    formatted_address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    confidence: Literal["high", "unknown"]
    message: str
    # Administrative area already present in the same geocoder response; never a second provider call.
    county: str | None = None
    district: str | None = None
    postal_code: str | None = None
    place_id: str | None = None
    resolution_reason: Literal["accepted", "multiple_candidates", "administrative_mismatch", "address_mismatch", "low_precision", "no_match", "unavailable"] = "unavailable"
    candidates: list[LocationResolveCandidate] = Field(default_factory=list, max_length=5)


@router.post("/insight")
@provider_operation("location")
def post_location_insight(request: LocationInsightRequest) -> dict[str, Any]:
    return analyze_location(**request.model_dump(), village_resolver=get_default_ris_village_resolver())


@router.post("/resolve", response_model=LocationResolveResponse)
def post_location_resolve(request: LocationResolveRequest) -> dict[str, Any]:
    return location_resolver.resolve_address(request.address)
