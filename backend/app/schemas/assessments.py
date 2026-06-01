from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field


class MockAnalysisResult(BaseModel):
    risk_level: Literal["low", "medium", "high"]
    score: int = Field(ge=0, le=100)
    summary: str
    recommendations: list[str]
    details: dict[str, Any] = Field(default_factory=dict)


class AssessmentResponse(BaseModel):
    id: int
    module: str
    created_at: datetime
    result: MockAnalysisResult


class AegisCreditCreate(BaseModel):
    applicant_name: str = Field(min_length=1, max_length=120)
    property_address: str = Field(min_length=1, max_length=255)
    property_value: Decimal = Field(gt=0)
    loan_amount: Decimal = Field(gt=0)
    monthly_income: Decimal = Field(gt=0)
    existing_debt: Decimal = Field(ge=0)
    loan_term_years: int = Field(gt=0, le=40)


class TaxOracleCreate(BaseModel):
    taxpayer_name: str = Field(min_length=1, max_length=120)
    property_address: str = Field(min_length=1, max_length=255)
    assessed_value: Decimal = Field(gt=0)
    replacement_purchase_value: Decimal = Field(default=Decimal("0"), ge=0)
    annual_rental_income: Decimal = Field(ge=0)
    holding_years: int = Field(ge=0, le=100)
    transaction_type: Literal["purchase", "sale", "rental", "inheritance"]
    is_self_use: bool = False
    has_outstanding_tax_debt: bool = False


class LexPropCreate(BaseModel):
    owner_name: str = Field(min_length=1, max_length=120)
    property_address: str = Field(min_length=1, max_length=255)
    title_number: str = Field(min_length=1, max_length=80)
    has_lien: bool = False
    has_easement: bool = False
    dispute_notes: str | None = Field(default=None, max_length=1000)
