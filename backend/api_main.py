"""FastAPI entry point for the productized PropTech AI Copilot demo."""

from __future__ import annotations

import os
import json
import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exception_handlers import (
    http_exception_handler,
    request_validation_exception_handler,
)
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.api.routes_health import router as health_router
from backend.api.routes_holding_cost import router as holding_cost_router
from backend.api.routes_location_insight import router as location_insight_router
from backend.api.routes_bank_rates import router as bank_rates_router
from backend.api.routes_commute import router as commute_router
from backend.api.routes_loan_calculator import router as loan_calculator_router
from backend.api.routes_lite import router as lite_router
from backend.api.routes_map import router as map_router
from backend.api.routes_market import router as market_router
from backend.api.routes_mortgage_rates import router as mortgage_rates_router
from backend.api.routes_road import router as road_router
from backend.api.routes_taxoracle import router as taxoracle_router
from backend.api.routes_terrain_risk import router as terrain_risk_router
from backend.api.routes_valuation import router as valuation_router
from backend.api.routes_pilot import router as pilot_router
from backend.api.routes_performance import router as performance_router
from backend.api.routes_parcel_geometry import router as parcel_geometry_router
from backend.api.v1 import router as vnext_router
from backend.api.v1.errors import structured_error_response, vnext_error_handler
from services.observability import build_observation, normalize_correlation_id
from services.production_config import assert_startup_configuration
from services.security import safe_origin, security_headers
from services.production_config import MAINTENANCE_MODE_ENV
from services.vnext.errors import ErrorCode, VNextError


DEFAULT_DEV_CORS_ORIGINS = ("http://localhost:3000", "http://127.0.0.1:3000")
CORS_ALLOWED_ORIGINS_ENV = "CORS_ALLOWED_ORIGINS"
LEGACY_CORS_ORIGINS_ENV = "CORS_ORIGINS"


def parse_cors_allowed_origins(raw: str) -> list[str]:
    """Parse a comma-separated CORS allowlist without enabling wildcard credentials."""

    origins = []
    for item in raw.split(","):
        origin = safe_origin(item.strip())
        if origin and origin not in origins:
            origins.append(origin)
    return origins


def configured_cors_origins() -> list[str]:
    configured = os.getenv(CORS_ALLOWED_ORIGINS_ENV, "").strip()
    legacy = os.getenv(LEGACY_CORS_ORIGINS_ENV, "").strip()
    parsed = parse_cors_allowed_origins(configured or legacy)
    return parsed or list(DEFAULT_DEV_CORS_ORIGINS)


@asynccontextmanager
async def app_lifespan(_app: FastAPI):
    """Validate production configuration before accepting requests."""

    assert_startup_configuration()
    yield
    # Shutdown: close GREEN connection pool if it was initialized.
    # Safe no-op if pool was never created (PLVR_DATA_BACKEND != green).
    from services.compact_green_query import close_green_pool
    close_green_pool()


app = FastAPI(
    title="PropTech AI Copilot API",
    description="Productized demo API using deterministic TaxOracle rules and offline mock data.",
    version="0.1.0",
    lifespan=app_lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=configured_cors_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Accept", "Origin", "Authorization", "Idempotency-Key", "If-Match", "X-Correlation-ID", "X-CSRF-Token", "X-Pilot-Session-Token", "X-Pilot-Admin-Token", "X-Pilot-Review-Token", "X-Pilot-Admin-Bootstrap", "X-Pilot-Review-Bootstrap"],
    expose_headers=["X-Correlation-ID", "ETag", "Retry-After"],
)

logger = logging.getLogger("proptech.observability")


@app.middleware("http")
async def privacy_safe_observability(request: Request, call_next):
    correlation_id = normalize_correlation_id(request.headers.get("X-Correlation-ID"))
    request.state.correlation_id = correlation_id
    started = time.monotonic()
    content_length = request.headers.get("content-length")
    request_body_limit = 11_000_000 if request.url.path == "/parcel-geometry/upload" else 1_000_000
    if content_length and content_length.isdigit() and int(content_length) > request_body_limit:
        if request.url.path.startswith("/v1"):
            response = structured_error_response(request, VNextError.validation_failed())
        else:
            response = JSONResponse(status_code=413, content={"status": "error", "message": "Request body is too large.", "support_reference": correlation_id})
        response.headers["X-Correlation-ID"] = correlation_id
        for name, value in security_headers(private=True).items():
            response.headers.setdefault(name, value)
        return response
    origin = safe_origin(request.headers.get("origin"))
    if origin and request.method not in {"GET", "HEAD", "OPTIONS"} and origin not in {item.lower().rstrip("/") for item in configured_cors_origins()}:
        if request.url.path.startswith("/v1"):
            response = structured_error_response(request, VNextError.permission_denied())
        else:
            response = JSONResponse(status_code=403, content={"status": "error", "message": "Request origin is not allowed.", "support_reference": correlation_id})
        response.headers["X-Correlation-ID"] = correlation_id
        for name, value in security_headers(private=request.url.path.startswith("/pilot")).items():
            response.headers.setdefault(name, value)
        return response
    maintenance = os.getenv(MAINTENANCE_MODE_ENV, "").strip().lower() in {"1", "true", "yes", "on"}
    if maintenance and request.method in {"POST", "PUT", "PATCH", "DELETE"} and not request.url.path.startswith(("/health", "/liveness", "/readiness", "/release-version", "/source-status", "/compatibility")):
        if request.url.path.startswith("/v1"):
            response = structured_error_response(request, VNextError(ErrorCode.MAINTENANCE))
        else:
            response = JSONResponse(status_code=503, content={"status": "maintenance", "message": "服務正在維護中，請稍後再試。"})
        response.headers["X-Correlation-ID"] = correlation_id
        for name, value in security_headers(production=os.getenv("APP_ENV", "development").strip().lower() in {"production", "preview"}, private=True).items():
            response.headers.setdefault(name, value)
        return response
    try:
        response = await call_next(request)
    except Exception:
        observation = build_observation(correlation_id=correlation_id, route=request.url.path, method=request.method, status_code=500, duration_ms=int((time.monotonic() - started) * 1000), error_code="server_error")
        logger.warning("request_failed %s", json.dumps(observation, ensure_ascii=True, separators=(",", ":")))
        if request.url.path.startswith("/v1"):
            response = structured_error_response(request, VNextError(ErrorCode.INTERNAL_ERROR))
        else:
            response = JSONResponse(status_code=500, content={"status": "error", "message": "The request could not be completed.", "support_reference": correlation_id})
    response.headers["X-Correlation-ID"] = correlation_id
    production = os.getenv("APP_ENV", "development").strip().lower() in {"production", "preview"}
    private = request.url.path.startswith("/v1") or request.url.path.startswith("/pilot") or request.url.path.startswith("/professional-review") or request.url.path.startswith("/client-errors") or request.url.path.startswith("/parcel-geometry")
    for name, value in security_headers(production=production, private=private).items():
        response.headers.setdefault(name, value)
    if response.status_code >= 400:
        observation = build_observation(correlation_id=correlation_id, route=request.url.path, method=request.method, status_code=response.status_code, duration_ms=int((time.monotonic() - started) * 1000), error_code="request_failed")
        logger.info("request_completed %s", json.dumps(observation, ensure_ascii=True, separators=(",", ":")))
    return response


app.add_exception_handler(VNextError, vnext_error_handler)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, error: RequestValidationError):
    if request.url.path.startswith("/v1"):
        return structured_error_response(request, VNextError.validation_failed())
    return await request_validation_exception_handler(request, error)


@app.exception_handler(StarletteHTTPException)
async def api_http_exception_handler(request: Request, error: StarletteHTTPException):
    if request.url.path.startswith("/v1"):
        code = {
            401: ErrorCode.AUTHENTICATION_REQUIRED,
            403: ErrorCode.PERMISSION_DENIED,
            404: ErrorCode.NOT_FOUND,
        }.get(error.status_code, ErrorCode.VALIDATION_FAILED)
        return structured_error_response(request, VNextError(code))
    return await http_exception_handler(request, error)


app.include_router(health_router)
app.include_router(holding_cost_router)
app.include_router(location_insight_router)
app.include_router(bank_rates_router)
app.include_router(commute_router)
app.include_router(loan_calculator_router)
app.include_router(taxoracle_router)
app.include_router(terrain_risk_router)
app.include_router(market_router)
app.include_router(map_router)
app.include_router(road_router)
app.include_router(mortgage_rates_router)
app.include_router(lite_router)
app.include_router(valuation_router)
app.include_router(pilot_router)
app.include_router(performance_router)
app.include_router(parcel_geometry_router)
app.include_router(vnext_router)
