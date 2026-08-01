"""Optional first-party performance metric ingestion with a strict allowlist."""

from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from services.performance_telemetry import validate_metric_payload


router = APIRouter(tags=["performance"])
_buckets: dict[str, list[float]] = {}


class PerformanceMetricRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    metric: str = Field(min_length=1, max_length=8)
    value: float = Field(ge=0, le=120000)
    route: str = Field(min_length=1, max_length=120)
    viewport_class: str = Field(default="unknown", max_length=12)
    release_version: str = Field(default="unknown", max_length=40)
    locale: str = Field(default="unknown", max_length=12)
    pilot_mode: str = Field(default="normal", max_length=40)
    device_class: str = Field(default="unknown", max_length=12)
    sampled: bool = False


@router.post("/performance/metrics", status_code=202)
def record_performance_metric(request: Request, payload: PerformanceMetricRequest) -> dict[str, str]:
    key = request.client.host if request.client else "unknown"
    now = time.monotonic()
    recent = [stamp for stamp in _buckets.get(key, []) if stamp > now - 60]
    if len(recent) >= 60:
        raise HTTPException(status_code=429, detail="Performance telemetry is temporarily limited.")
    if len(_buckets) > 1000:
        _buckets.clear()
    recent.append(now)
    _buckets[key] = recent
    try:
        validate_metric_payload(payload.model_dump())
    except ValueError:
        raise HTTPException(status_code=422, detail="Performance telemetry is invalid.")
    return {"status": "accepted"}
