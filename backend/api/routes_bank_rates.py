"""Bank posted-rate reference APIs."""

from typing import Any

from fastapi import APIRouter, Query

router = APIRouter(prefix="/bank-rates", tags=["bank-rates"])


@router.get("/institutions")
def institutions() -> dict[str, Any]:
    from services.bank_rate_service import list_institutions
    return list_institutions()


@router.get("/mortgage")
def mortgage(bank_code: str = Query(min_length=1)) -> dict[str, Any]:
    from services.bank_rate_service import get_bank_mortgage_rates
    return get_bank_mortgage_rates(bank_code)
