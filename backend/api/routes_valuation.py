"""Comparable-sales valuation API."""

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(prefix="/valuation", tags=["valuation"])


class ValuationRequest(BaseModel):
    city: str
    district: str
    road: str
    building_type: str
    area_ping: float = Field(gt=0)
    building_age_years: float = Field(ge=0)
    floor: int = Field(ge=0)
    lat: float | None = None
    lng: float | None = None


@router.post("/estimate")
def estimate(request: ValuationRequest) -> dict[str, Any]:
    from services.valuation_service import estimate_property
    return estimate_property(request.model_dump())
