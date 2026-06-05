"""FastAPI entry point for the productized PropTech AI Copilot demo."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes_health import router as health_router
from backend.api.routes_lite import router as lite_router
from backend.api.routes_market import router as market_router
from backend.api.routes_taxoracle import router as taxoracle_router


app = FastAPI(
    title="PropTech AI Copilot API",
    description="Productized demo API using deterministic TaxOracle rules and offline mock data.",
    version="0.1.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(health_router)
app.include_router(taxoracle_router)
app.include_router(market_router)
app.include_router(lite_router)
