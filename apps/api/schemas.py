"""
Pydantic Schemas — Request/Response models for the REST API.

These are the API contract — they define exactly what clients send and receive.
They are separate from domain models and ORM models to maintain layer separation.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field

# ==============================================================================
# Health
# ==============================================================================


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "healthy"
    version: str = "0.1.0"
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ==============================================================================
# Assets
# ==============================================================================


class AssetResponse(BaseModel):
    """Asset in the platform universe."""

    id: uuid.UUID
    symbol: str
    name: str
    asset_class: str
    exchange: str
    currency: str
    sector: str | None = None
    is_active: bool

    model_config = {"from_attributes": True}


class AssetCreate(BaseModel):
    """Request to add an asset to the universe."""

    symbol: str = Field(..., min_length=1, max_length=20)
    name: str = Field(..., min_length=1, max_length=200)
    asset_class: str = "etf"
    exchange: str = ""
    currency: str = "USD"
    sector: str | None = None


# ==============================================================================
# Market Data
# ==============================================================================


class MarketDataRequest(BaseModel):
    """Request to ingest market data for a symbol."""

    symbol: str
    start_date: date
    end_date: date
    frequency: str = "1d"
    provider: str = "yahoo_finance"


class MarketDataSummary(BaseModel):
    """Summary of ingested market data."""

    symbol: str
    provider: str
    frequency: str
    start_date: date
    end_date: date
    row_count: int
    parquet_path: str


class PriceBar(BaseModel):
    """A single OHLCV price bar."""

    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    adjusted_close: float | None = None


# ==============================================================================
# Strategies
# ==============================================================================


class StrategyResponse(BaseModel):
    """Strategy definition."""

    id: uuid.UUID
    name: str
    description: str
    category: str
    created_at: datetime

    model_config = {"from_attributes": True}


class StrategyCreate(BaseModel):
    """Request to register a strategy."""

    name: str = Field(..., min_length=1, max_length=100)
    description: str = ""
    category: str = "momentum"


# ==============================================================================
# Backtests
# ==============================================================================


class BacktestRequest(BaseModel):
    """Request to launch a backtest."""

    strategy_name: str
    parameters: dict[str, float | int | str | bool] = Field(default_factory=dict)
    universe: list[str] = Field(default=["SPY", "QQQ", "IWM", "TLT", "GLD"])
    start_date: date = Field(default=date(2020, 1, 1))
    end_date: date = Field(default=date(2024, 1, 1))
    initial_cash: float = 100_000.0
    commission_rate_bps: float = 5.0
    slippage_rate_bps: float = 5.0
    frequency: str = "1d"


class BacktestMetricsResponse(BaseModel):
    """Backtest metrics summary."""

    total_return: float = 0.0
    cagr: float = 0.0
    annualized_volatility: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    total_trades: int = 0
    avg_trade_return: float = 0.0
    best_trade: float = 0.0
    worst_trade: float = 0.0
    exposure_time: float = 0.0
    turnover: float = 0.0
    final_equity: float = 0.0


class BacktestResponse(BaseModel):
    """Complete backtest result."""

    id: str
    strategy_name: str
    status: str
    metrics: BacktestMetricsResponse
    equity_curve: list[float] = Field(default_factory=list)
    dates: list[str] = Field(default_factory=list)
    execution_time_ms: int = 0
    config: dict = Field(default_factory=dict)


class BacktestSummary(BaseModel):
    """Lightweight backtest listing entry."""

    id: str
    strategy_name: str
    status: str
    total_return: float | None = None
    sharpe_ratio: float | None = None
    max_drawdown: float | None = None
    execution_time_ms: int | None = None
    started_at: datetime | None = None


# ==============================================================================
# Data Quality
# ==============================================================================


class DataQualityReport(BaseModel):
    """Result of data quality validation."""

    symbol: str
    is_valid: bool
    errors: list[str] = Field(default_factory=list)
    row_count: int = 0
