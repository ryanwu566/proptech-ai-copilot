"""TaxOracle API routes backed by the existing deterministic services."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from backend.repositories.sqlite_repo import get_tax_analysis, list_tax_analyses
from models.schemas import TaxCase
router = APIRouter(tags=["taxoracle"])


class TaxCaseRequest(BaseModel):
    """HTTP request contract mirroring the existing TaxCase dataclass."""

    case_id: str
    client_name: str
    sold_self_occupied: bool
    residency_condition_met: bool
    purchase_within_reasonable_period: bool
    purchased_self_occupied: bool
    same_owner: bool
    land_value_available: bool
    required_docs_complete: bool
    enters_five_year_monitoring: bool
    exceptional_circumstances: bool

    def to_tax_case(self) -> TaxCase:
        """Convert validated HTTP input into the domain dataclass."""

        return TaxCase(**self.model_dump())


@router.get("/demo-cases")
def get_demo_cases() -> list[dict[str, Any]]:
    """Return bundled TaxOracle demo cases for the frontend selector."""

    from services.data_service import MockDataError, load_mock_csv

    try:
        records = load_mock_csv("mock_tax_cases.csv").to_dict("records")
    except MockDataError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return [_normalize_demo_case(record) for record in records]


@router.post("/taxoracle/analyze")
def post_taxoracle_analysis(request: TaxCaseRequest) -> dict[str, Any]:
    """Run the existing deterministic TaxOracle service and persist history."""

    from services.tax_service import analyze_tax_case

    return analyze_tax_case(request.to_tax_case())


@router.post("/taxoracle/report", response_class=HTMLResponse)
def post_taxoracle_report(request: TaxCaseRequest) -> str:
    """Generate downloadable HTML without persisting a duplicate analysis."""

    from services.report_service import generate_tax_html_report
    from services.tax_service import analyze_tax_case

    case = request.to_tax_case()
    result = analyze_tax_case(case, persist=False)
    return generate_tax_html_report(case, result)


@router.get("/history")
def get_history() -> list[dict[str, Any]]:
    """Return recent persisted TaxOracle analyses."""

    return list_tax_analyses()


@router.get("/history/{analysis_id}")
def get_history_detail(analysis_id: int) -> dict[str, Any]:
    """Return one persisted TaxOracle result for frontend review."""

    result = get_tax_analysis(analysis_id)
    if result is None:
        raise HTTPException(status_code=404, detail="找不到該筆歷史案件。")
    return result


def _normalize_demo_case(record: dict[str, Any]) -> dict[str, Any]:
    """Normalize pandas values for JSON and Pydantic consumers."""

    normalized = dict(record)
    for key in TaxCaseRequest.model_fields:
        if key not in {"case_id", "client_name"}:
            normalized[key] = str(normalized[key]).strip().lower() in {"true", "1", "yes"}
    return normalized
