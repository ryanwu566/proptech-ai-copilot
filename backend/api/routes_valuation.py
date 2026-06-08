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


class ValuationTrendRequest(BaseModel):
    city: str
    district: str
    road: str
    building_type: str
    area_ping: float = Field(gt=0)
    building_age_years: float = Field(ge=0)
    horizon_months: list[int] = Field(default_factory=lambda: [6, 12, 36])


class PropertySearchRequest(BaseModel):
    city: str = ""
    districts: list[str] = Field(default_factory=list)
    budget_min: float | None = Field(default=None, ge=0)
    budget_max: float = Field(gt=0)
    area_ping_min: float | None = Field(default=None, ge=0)
    area_ping_max: float | None = Field(default=None, ge=0)
    building_type: str = ""
    building_age_max: float | None = Field(default=None, ge=0)
    floor_min: int | None = Field(default=None, ge=0)
    period_since: str = ""
    limit: int = Field(default=50, ge=1, le=100)


@router.get("/data-status")
def data_status() -> dict[str, Any]:
    """Return the active valuation provider and coverage summary."""

    from services.valuation_service import get_valuation_data_status
    return get_valuation_data_status()


@router.post("/estimate")
def estimate(request: ValuationRequest) -> dict[str, Any]:
    from services.valuation_service import estimate_property
    return estimate_property(request.model_dump())


@router.post("/trend")
def trend(request: ValuationTrendRequest) -> dict[str, Any]:
    """Return official-PLVR historical trends and bounded scenarios."""

    from services.valuation_trend_service import analyze_valuation_trend
    return analyze_valuation_trend(request.model_dump())


@router.post("/property-search")
def property_search(request: PropertySearchRequest) -> dict[str, Any]:
    """Return official historical transaction directions, not live listings."""

    from services.property_search_service import search_properties
    return search_properties(request.model_dump())
