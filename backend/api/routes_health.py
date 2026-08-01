"""Health-check routes."""

from __future__ import annotations

from fastapi import APIRouter

from backend.db import health_check
from services.production_config import load_runtime_configuration


router = APIRouter(tags=["health"])


@router.get("/health")
def get_health() -> dict[str, object]:
    """Return liveness and persistence categories without exposing values."""

    config = load_runtime_configuration()
    persistence = health_check()
    return {
        "status": "ok",
        "liveness": "ok",
        "persistence": persistence,
        "readiness": "ready" if config.ready and persistence["database"] in {"ok", "available"} else "unavailable",
        "mode": config.mode,
    }
