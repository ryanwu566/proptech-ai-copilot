"""FastAPI entry point for the productized PropTech AI Copilot demo."""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes_health import router as health_router
from backend.api.routes_holding_cost import router as holding_cost_router
from backend.api.routes_location_insight import router as location_insight_router
from backend.api.routes_bank_rates import router as bank_rates_router
from backend.api.routes_loan_calculator import router as loan_calculator_router
from backend.api.routes_lite import router as lite_router
from backend.api.routes_map import router as map_router
from backend.api.routes_market import router as market_router
from backend.api.routes_mortgage_rates import router as mortgage_rates_router
from backend.api.routes_road import router as road_router
from backend.api.routes_taxoracle import router as taxoracle_router
from backend.api.routes_valuation import router as valuation_router


app = FastAPI(
    title="PropTech AI Copilot API",
    description="Productized demo API using deterministic TaxOracle rules and offline mock data.",
    version="0.1.0",
)

default_origins = ["http://localhost:3000", "http://127.0.0.1:3000"]
configured_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "").split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=configured_origins or default_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(health_router)
app.include_router(holding_cost_router)
app.include_router(location_insight_router)
app.include_router(bank_rates_router)
app.include_router(loan_calculator_router)
app.include_router(taxoracle_router)
app.include_router(market_router)
app.include_router(map_router)
app.include_router(road_router)
app.include_router(mortgage_rates_router)
app.include_router(lite_router)
app.include_router(valuation_router)
