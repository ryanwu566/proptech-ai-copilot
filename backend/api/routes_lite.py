"""Lite demo API routes for the secondary product modules."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from rules.legal_risk_rules import summarize_legal_risk
from rules.mortgage_rules import evaluate_mortgage_risk
router = APIRouter(tags=["lite-demos"])


class MortgageRiskRequest(BaseModel):
    """Aegis-Credit Lite heuristic inputs."""

    monthly_income: int = Field(ge=0)
    monthly_debt: int = Field(ge=0)
    cash: int = Field(ge=0)
    property_count: int = Field(ge=0)
    mortgage_count: int = Field(ge=0)
    property_price: int = Field(ge=0)


class LegalRiskRequest(BaseModel):
    """Privacy-safe LexProp Lite fuzzy matching inputs."""

    city: str = ""
    district: str = ""
    road_masked: str = ""
    community: str = ""


@router.post("/aegis-credit/analyze")
def post_mortgage_risk(request: MortgageRiskRequest) -> dict[str, object]:
    """Run the existing Aegis-Credit Lite heuristic."""

    return evaluate_mortgage_risk(**request.model_dump())


@router.post("/lexprop/query")
def post_legal_risk(request: LegalRiskRequest) -> dict[str, Any]:
    """Run the existing privacy-preserving mock judgment lookup."""

    from services.data_service import MockDataError, load_mock_csv

    try:
        judgments = load_mock_csv("mock_judgments.csv")
    except MockDataError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return summarize_legal_risk(judgments, **request.model_dump())
