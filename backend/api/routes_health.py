"""Health-check routes."""

from __future__ import annotations

from fastapi import APIRouter

from backend.db import health_check


router = APIRouter(tags=["health"])


@router.get("/health")
def get_health() -> dict[str, object]:
    """Return backend and SQLite health for deployment checks."""

    return {"status": "ok", "sqlite": health_check(), "mode": "mock-data"}
