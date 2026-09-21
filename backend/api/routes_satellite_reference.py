"""Bounded satellite reference endpoint."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field

from services.satellite_reference import (
    SatelliteReferenceResponse,
    fetch_satellite_reference,
)


router = APIRouter(prefix="/terrain", tags=["terrain"])


class SatelliteReferenceRequest(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False, extra="forbid")

    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


@router.post("/satellite-reference", response_model=SatelliteReferenceResponse)
async def post_satellite_reference(request: SatelliteReferenceRequest) -> SatelliteReferenceResponse:
    return await fetch_satellite_reference(
        latitude=request.latitude,
        longitude=request.longitude,
    )
