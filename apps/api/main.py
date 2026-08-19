"""
FastAPI Application — Entrypoint for the Quant Platform REST API.

Assembles all routers, configures middleware, and manages application lifecycle.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.api.routers import (
    backtests,
    data_quality,
    health,
    market_data,
    portfolios,
    risk,
    strategies,
)
from src.infrastructure.database.session import init_db

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:  # noqa: ARG001
    """Application lifecycle — startup and shutdown hooks."""
    logger.info("🚀 Quant Platform API starting up...")
    try:
        init_db()
        logger.info("✅ Database tables initialized successfully.")
    except Exception as exc:
        logger.warning("⚠️ Database initialization skipped or failed: %s", exc)
    yield
    logger.info("🛑 Quant Platform API shutting down...")


app = FastAPI(
    title="Quant Platform API",
    description=(
        "Quantitative Research & Systematic Trading Platform — "
        "Market data ingestion, strategy backtesting, portfolio construction, "
        "and risk management via a clean REST API."
    ),
    version="0.2.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — allow frontend dev servers, Superset, and local tools
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "*",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(health.router)
app.include_router(market_data.router)
app.include_router(backtests.router)
app.include_router(portfolios.router)
app.include_router(risk.router)
app.include_router(data_quality.router)
app.include_router(strategies.router)
