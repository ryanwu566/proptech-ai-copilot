"""Fail-closed production metrics scrape endpoint."""

from __future__ import annotations

import os
import secrets

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import PlainTextResponse

from services.metrics import BoundedMetricsRegistry, valid_scrape_token
from services.production_config import METRICS_SCRAPE_TOKEN_ENV


METRICS_SCRAPE_TOKEN_HEADER = "X-Metrics-Scrape-Token"


def build_metrics_router(registry: BoundedMetricsRegistry) -> APIRouter:
    router = APIRouter(tags=["operations"])

    @router.get("/metrics", include_in_schema=False, response_class=PlainTextResponse)
    def get_metrics(request: Request) -> PlainTextResponse:
        expected = os.getenv(METRICS_SCRAPE_TOKEN_ENV, "")
        provided = request.headers.get(METRICS_SCRAPE_TOKEN_HEADER, "")
        if (
            not valid_scrape_token(expected)
            or not valid_scrape_token(provided)
            or not secrets.compare_digest(provided, expected)
        ):
            raise HTTPException(status_code=404, detail="Not Found")
        return PlainTextResponse(
            registry.render_prometheus(),
            media_type="text/plain; version=0.0.4",
        )

    return router
