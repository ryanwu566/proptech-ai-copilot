"""Market mortgage-rate reference API."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter


router = APIRouter(prefix="/mortgage-rates", tags=["mortgage-rates"])


@router.get("/latest")
def get_latest_rate() -> dict[str, Any]:
    """Return the latest monthly reference or a safe mock fallback."""

    from services.mortgage_rate_service import get_latest_mortgage_rate

    return get_latest_mortgage_rate()
