"""Loan payment calculator API."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field, model_validator

from services.loan_calculator_service import calculate_loan


router = APIRouter(prefix="/loan", tags=["loan-calculator"])


class LoanCalculateRequest(BaseModel):
    property_price: float = Field(gt=0)
    down_payment_ratio: float = Field(default=0.2, ge=0, le=1)
    annual_interest_rate: float = Field(default=2.2, ge=0)
    loan_years: int = Field(default=30, gt=0)
    monthly_income: float | None = Field(default=None, gt=0)
    grace_period_years: int = Field(default=0, ge=0)
    include_sensitivity: bool = True

    @model_validator(mode="after")
    def validate_grace_period(self) -> "LoanCalculateRequest":
        if self.grace_period_years >= self.loan_years:
            raise ValueError("grace_period_years must be less than loan_years")
        return self


@router.post("/calculate")
def post_calculate_loan(request: LoanCalculateRequest) -> dict[str, Any]:
    """Return a deterministic mortgage payment estimate without persistence."""

    return calculate_loan(**request.model_dump())
