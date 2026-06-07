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
    address_text: str = ""


@router.get("/data-status")
def data_status() -> dict[str, Any]:
    """Return the active valuation provider and coverage summary."""

    from services.valuation_service import get_valuation_data_status
    return get_valuation_data_status()


@router.post("/estimate")
def estimate(request: ValuationRequest) -> dict[str, Any]:
    from services.valuation_service import estimate_property
    return estimate_property(request.model_dump())
