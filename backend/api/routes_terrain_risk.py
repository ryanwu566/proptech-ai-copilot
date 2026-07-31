"""Terrain and disaster risk analysis API."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, model_validator

from services.official_data_registry import public_source_status
from services.terrain_risk_service import TerrainRiskLocationError, analyze_terrain_risk


router = APIRouter(prefix="/terrain-risk", tags=["terrain-risk"])


@router.get("/sources")
def get_terrain_source_status() -> dict[str, object]:
    """Return source metadata without querying or claiming provider availability."""

    return public_source_status("terrain")


class TerrainRiskRequest(BaseModel):
    address: str = ""
    city: str = ""
    district: str = ""
    road: str = ""
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    radius_m: int = Field(default=500, ge=100, le=2000)
    include_layers: list[str] | None = None

    @model_validator(mode="after")
    def coordinates_are_paired(self) -> "TerrainRiskRequest":
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("latitude and longitude must be provided together")
        return self


@router.post("/analyze")
def post_terrain_risk(request: TerrainRiskRequest) -> dict[str, Any]:
    try:
        return analyze_terrain_risk(**request.model_dump())
    except TerrainRiskLocationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
