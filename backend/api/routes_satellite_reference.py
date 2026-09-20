"""Bounded satellite reference endpoint."""

from __future__ import annotations

import os

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field

from services.satellite_reference import (
    SatelliteReferenceResponse,
    build_response,
    feature_enabled,
    fetch_satellite_reference,
)


router = APIRouter(prefix="/terrain", tags=["terrain"])


class SatelliteReferenceRequest(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False, extra="forbid")

    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


@router.post("/satellite-reference", response_model=SatelliteReferenceResponse)
async def post_satellite_reference(request: SatelliteReferenceRequest) -> SatelliteReferenceResponse:
    enabled = feature_enabled(os.getenv("EARTH_ENGINE_SATELLITE_REFERENCE_V1", ""))
    if not enabled:
        return build_response(status="unavailable", reason_code="feature_disabled")
    project = os.getenv("EARTH_ENGINE_PROJECT", "").strip()
    if not project:
        return build_response(status="unavailable", reason_code="credential_unavailable")
    return await fetch_satellite_reference(
        latitude=request.latitude,
        longitude=request.longitude,
        project=project,
    )
