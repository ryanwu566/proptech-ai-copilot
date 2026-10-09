"""Terrain and disaster risk analysis API."""

from __future__ import annotations

from typing import Any

from services.input_limits import BoundedInputModel
from services.anti_abuse import provider_operation

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, model_validator

from services.official_data_registry import public_source_status
from services.terrain_risk_service import TerrainRiskLocationError, analyze_terrain_risk


router = APIRouter(prefix="/terrain-risk", tags=["terrain-risk"])


@router.get("/sources")
def get_terrain_source_status() -> dict[str, object]:
    """Return source metadata without querying or claiming provider availability."""

    return public_source_status("terrain")


class TerrainRiskRequest(BoundedInputModel):
    address: str = ""
    city: str = ""
    district: str = ""
    road: str = ""
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    radius_m: int = Field(default=500, ge=100, le=2000)
    include_layers: list[str] | None = Field(default=None, max_length=16)

    @model_validator(mode="after")
    def coordinates_are_paired(self) -> "TerrainRiskRequest":
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("latitude and longitude must be provided together")
        return self


@router.post("/analyze")
@provider_operation("terrain")
def post_terrain_risk(request: TerrainRiskRequest) -> dict[str, Any]:
    from services.provider_observability import observe_response
    try:
        result = analyze_terrain_risk(**request.model_dump())
        observe_response("nlsc", result.get("terrain", {}))
        for key, capability in {"flood": "wra", "debris_flow": "ardswc-debris-flow", "landslide": "ardswc-landslide", "geological_sensitivity": "gsmma", "liquefaction": "liquefaction"}.items():
            hazard = result.get("hazards", {}).get(key, {})
            if hazard and hazard.get("status") != "skipped":
                source = hazard.get("source") or {}
                observe_response(capability, {"status": hazard.get("status"), "reason_code": "matched" if hazard.get("matched") else "not_matched_in_loaded_layer" if hazard.get("status") == "available" else "source_unavailable", "dataset_version": hazard.get("dataset_version") or source.get("dataset_version") if isinstance(source, dict) else None})
        return result
    except TerrainRiskLocationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
