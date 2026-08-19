"""
Pydantic Schemas — Request/Response models for the REST API.

These are the API contract — they define exactly what clients send and receive.
They are separate from domain models and ORM models to maintain layer separation.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime

from pydantic import BaseModel, Field

# ==============================================================================
# Health
# ==============================================================================


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "healthy"
    version: str = "1.0.0"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


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


class DataQualityCheckResponse(BaseModel):
    """Result of an individual check."""

    check_name: str
    status: str
    message: str
    details: dict[str, float | int | str] = Field(default_factory=dict)


class DataQualityReportResponse(BaseModel):
    """Result of data quality validation."""

    dataset: str = "daily_ohlcv"
    symbol: str
    status: str
    is_valid: bool
    rows_checked: int = 0
    errors: list[str] = Field(default_factory=list)
    checks: list[DataQualityCheckResponse] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class DataQualityRunSummary(BaseModel):
    """Summary of a past data quality run."""

    id: uuid.UUID
    dataset: str
    symbol: str
    status: str
    rows_checked: int
    created_at: datetime

    model_config = {"from_attributes": True}


# Keep for backwards compatibility
class DataQualityReport(BaseModel):
    """Result of data quality validation."""

    symbol: str
    is_valid: bool
    errors: list[str] = Field(default_factory=list)
    row_count: int = 0


# ==============================================================================
# Portfolios & Positions
# ==============================================================================


class PortfolioCreateRequest(BaseModel):
    """Request to create a new portfolio."""

    name: str = Field(..., min_length=1, max_length=100)
    description: str = ""
    initial_cash: float = Field(default=100_000.0, gt=0)


class PositionResponse(BaseModel):
    """Holding position in a portfolio."""

    symbol: str
    quantity: float
    avg_entry_price: float
    current_price: float
    market_value: float
    unrealized_pnl: float
    weight: float = 0.0


class PortfolioSummaryResponse(BaseModel):
    """Summary representation of a portfolio."""

    id: uuid.UUID
    name: str
    description: str
    cash: float
    total_value: float
    updated_at: datetime

    model_config = {"from_attributes": True}


class PortfolioSnapshotResponse(BaseModel):
    """Historical snapshot of portfolio value."""

    timestamp: datetime
    total_value: float
    cash: float
    positions_value: float
    daily_return: float | None = None

    model_config = {"from_attributes": True}


class PortfolioPerformanceResponse(BaseModel):
    """Performance history of a portfolio."""

    portfolio_id: uuid.UUID
    total_value: float
    cash: float
    snapshots: list[PortfolioSnapshotResponse] = Field(default_factory=list)


class RebalanceRequest(BaseModel):
    """Request to rebalance a portfolio."""

    method: str = "equal_weight"  # "equal_weight", "inverse_volatility", "volatility_targeting"
    max_position_weight: float = 0.25
    max_gross_exposure: float = 1.00
    max_turnover: float = 0.50
    target_volatility: float | None = None
    universe: list[str] = Field(default=["SPY", "QQQ", "IWM", "TLT", "GLD"])


# ==============================================================================
# Risk Management
# ==============================================================================


class RiskViolationResponse(BaseModel):
    """Detail of a risk limit violation."""

    rule_name: str
    description: str
    actual_value: float
    limit_value: float
    severity: str = "ERROR"


class RiskMetricResponse(BaseModel):
    """Calculated point-in-time risk metrics."""

    timestamp: datetime
    var_95: float
    cvar_95: float
    volatility: float
    max_drawdown: float
    current_drawdown: float
    gross_exposure: float
    net_exposure: float
    concentration_hhi: float
    beta: float | None = None
    verdict: str
    violations: list[RiskViolationResponse] = Field(default_factory=list)


class RiskEvaluateRequest(BaseModel):
    """Request to evaluate risk profile for a sequence of returns or portfolio."""

    equity_curve: list[float]
    returns: list[float]
    current_weights: dict[str, float]
    benchmark_returns: list[float] | None = None
    max_position_weight: float = 0.25
    max_gross_exposure: float = 1.00
    max_volatility: float = 0.20
    max_drawdown: float = 0.15
    max_var_95: float = 0.05
