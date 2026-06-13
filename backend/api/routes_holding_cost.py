"""Holding-cost calculator API."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from services.holding_cost_service import calculate_holding_cost


router = APIRouter(prefix="/holding-cost", tags=["holding-cost"])


class HoldingCostRequest(BaseModel):
    property_price: float = Field(gt=0)
    loan_monthly_payment: float = Field(default=0, ge=0)
    monthly_income: float | None = Field(default=None, gt=0)
    area_ping: float | None = Field(default=None, ge=0)
    management_fee_per_ping: float = Field(default=80, ge=0)
    repair_reserve_per_ping: float = Field(default=50, ge=0)
    annual_home_tax_rate: float = Field(default=0.0012, ge=0)
    annual_land_tax_rate: float = Field(default=0.001, ge=0)
    annual_insurance: float = Field(default=3000, ge=0)
    include_tax_estimate: bool = True


@router.post("/calculate")
def post_calculate_holding_cost(request: HoldingCostRequest) -> dict[str, Any]:
    """Return a simplified holding-cost estimate without persistence."""

    return calculate_holding_cost(**request.model_dump())
