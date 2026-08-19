"""
SQLAlchemy ORM Models — Relational schema for the quantitative platform.

Maps domain concepts to PostgreSQL tables using SQLAlchemy 2.0 Declarative style.
Organized into logical groups matching the domain bounded contexts.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """SQLAlchemy declarative base for all ORM models."""

    pass


# ==============================================================================
# Assets & Market Data Metadata
# ==============================================================================


class AssetORM(Base):
    """Tradeable asset in the platform universe."""

    __tablename__ = "assets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    symbol: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    asset_class: Mapped[str] = mapped_column(String(50), nullable=False, default="etf")
    exchange: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="USD")
    sector: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    market_data_metadata: Mapped[list[MarketDataMetadataORM]] = relationship(back_populates="asset")
    positions: Mapped[list[PositionORM]] = relationship(back_populates="asset")


class MarketDataMetadataORM(Base):
    """Tracks what market data has been ingested per asset (metadata only — OHLCV in Parquet)."""

    __tablename__ = "market_data_metadata"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assets.id"), nullable=False
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    frequency: Mapped[str] = mapped_column(String(10), nullable=False, default="1d")
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    row_count: Mapped[int] = mapped_column(Integer, nullable=False)
    parquet_path: Mapped[str] = mapped_column(String(500), nullable=False)
    ingested_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("asset_id", "provider", "frequency", name="uq_market_data_meta"),
    )

    # Relationships
    asset: Mapped[AssetORM] = relationship(back_populates="market_data_metadata")


# ==============================================================================
# Strategies & Versioning
# ==============================================================================


class StrategyORM(Base):
    """A systematic trading strategy definition."""

    __tablename__ = "strategies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    category: Mapped[str] = mapped_column(String(50), nullable=False, default="momentum")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    versions: Mapped[list[StrategyVersionORM]] = relationship(back_populates="strategy")


class StrategyVersionORM(Base):
    """Versioned snapshot of a strategy's code and parameter schema."""

    __tablename__ = "strategy_versions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    strategy_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("strategies.id"), nullable=False
    )
    version: Mapped[str] = mapped_column(String(20), nullable=False)
    code_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    parameter_schema: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    default_parameters: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (UniqueConstraint("strategy_id", "version", name="uq_strategy_version"),)

    # Relationships
    strategy: Mapped[StrategyORM] = relationship(back_populates="versions")
    backtest_configs: Mapped[list[BacktestConfigORM]] = relationship(
        back_populates="strategy_version"
    )


# ==============================================================================
# Backtesting
# ==============================================================================


class BacktestConfigORM(Base):
    """Immutable configuration used for a backtest run — enables exact reproducibility."""

    __tablename__ = "backtest_configs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    strategy_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("strategy_versions.id"), nullable=False
    )
    parameters: Mapped[dict] = mapped_column(JSON, nullable=False)
    universe_symbols: Mapped[str] = mapped_column(Text, nullable=False)  # JSON array as text
    frequency: Mapped[str] = mapped_column(String(10), nullable=False, default="1d")
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    initial_cash: Mapped[float] = mapped_column(Float, nullable=False, default=100_000.0)
    commission_model: Mapped[str] = mapped_column(String(50), nullable=False, default="percentage")
    commission_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0005)
    slippage_model: Mapped[str] = mapped_column(String(50), nullable=False, default="percentage")
    slippage_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0005)
    execution_mode: Mapped[str] = mapped_column(String(50), nullable=False, default="next_bar_open")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    strategy_version: Mapped[StrategyVersionORM] = relationship(back_populates="backtest_configs")
    backtests: Mapped[list[BacktestORM]] = relationship(back_populates="config")


class BacktestORM(Base):
    """A single backtest execution run."""

    __tablename__ = "backtests"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    config_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("backtest_configs.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    final_equity: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_return_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    execution_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    git_commit_sha: Mapped[str | None] = mapped_column(String(40), nullable=True)
    artifact_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    logs: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    config: Mapped[BacktestConfigORM] = relationship(back_populates="backtests")
    metrics: Mapped[BacktestMetricsORM | None] = relationship(
        back_populates="backtest", uselist=False
    )
    orders: Mapped[list[OrderORM]] = relationship(back_populates="backtest")


class BacktestMetricsORM(Base):
    """Aggregated quantitative metrics for a completed backtest."""

    __tablename__ = "backtest_metrics"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    backtest_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("backtests.id"), unique=True, nullable=False
    )
    total_return: Mapped[float] = mapped_column(Float, nullable=False)
    cagr: Mapped[float] = mapped_column(Float, nullable=False)
    annualized_volatility: Mapped[float] = mapped_column(Float, nullable=False)
    sharpe_ratio: Mapped[float] = mapped_column(Float, nullable=False)
    sortino_ratio: Mapped[float] = mapped_column(Float, nullable=False)
    calmar_ratio: Mapped[float] = mapped_column(Float, nullable=False)
    max_drawdown: Mapped[float] = mapped_column(Float, nullable=False)
    win_rate: Mapped[float] = mapped_column(Float, nullable=False)
    profit_factor: Mapped[float] = mapped_column(Float, nullable=False)
    total_trades: Mapped[int] = mapped_column(Integer, nullable=False)
    avg_trade_return: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    best_trade: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    worst_trade: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    exposure_time: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    turnover: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    monthly_returns_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Relationships
    backtest: Mapped[BacktestORM] = relationship(back_populates="metrics")


# ==============================================================================
# Orders & Executions
# ==============================================================================


class OrderORM(Base):
    """An order generated during backtesting or paper trading."""

    __tablename__ = "orders"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    backtest_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("backtests.id"), nullable=True
    )
    asset_symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    order_type: Mapped[str] = mapped_column(String(20), nullable=False, default="market")
    side: Mapped[str] = mapped_column(String(10), nullable=False)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    price: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    filled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    backtest: Mapped[BacktestORM | None] = relationship(back_populates="orders")
    executions: Mapped[list[ExecutionORM]] = relationship(back_populates="order")


class ExecutionORM(Base):
    """A fill event for an order."""

    __tablename__ = "executions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False
    )
    fill_price: Mapped[float] = mapped_column(Float, nullable=False)
    fill_quantity: Mapped[float] = mapped_column(Float, nullable=False)
    commission: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    slippage: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    executed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    order: Mapped[OrderORM] = relationship(back_populates="executions")


# ==============================================================================
# Portfolios & Positions
# ==============================================================================


class PortfolioORM(Base):
    """A portfolio entity (backtest portfolio or paper trading portfolio)."""

    __tablename__ = "portfolios"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    cash: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    total_value: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    positions: Mapped[list[PositionORM]] = relationship(back_populates="portfolio")
    snapshots: Mapped[list[PortfolioSnapshotORM]] = relationship(back_populates="portfolio")


class PositionORM(Base):
    """A holding within a portfolio."""

    __tablename__ = "positions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    portfolio_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("portfolios.id"), nullable=False
    )
    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assets.id"), nullable=False
    )
    quantity: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    avg_entry_price: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    current_price: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    market_value: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    unrealized_pnl: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    portfolio: Mapped[PortfolioORM] = relationship(back_populates="positions")
    asset: Mapped[AssetORM] = relationship(back_populates="positions")


class PortfolioSnapshotORM(Base):
    """Historical snapshot of portfolio value for tracking equity curve."""

    __tablename__ = "portfolio_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    portfolio_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("portfolios.id"), nullable=False
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    total_value: Mapped[float] = mapped_column(Float, nullable=False)
    cash: Mapped[float] = mapped_column(Float, nullable=False)
    positions_value: Mapped[float] = mapped_column(Float, nullable=False)
    daily_return: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Relationships
    portfolio: Mapped[PortfolioORM] = relationship(back_populates="snapshots")


# ==============================================================================
# Risk Metrics
# ==============================================================================


class RiskMetricORM(Base):
    """Point-in-time risk metrics for a portfolio or backtest."""

    __tablename__ = "risk_metrics"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    backtest_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("backtests.id"), nullable=True
    )
    portfolio_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("portfolios.id"), nullable=True
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    var_95: Mapped[float | None] = mapped_column(Float, nullable=True)
    cvar_95: Mapped[float | None] = mapped_column(Float, nullable=True)
    volatility: Mapped[float | None] = mapped_column(Float, nullable=True)
    beta: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_drawdown: Mapped[float | None] = mapped_column(Float, nullable=True)
    concentration: Mapped[float | None] = mapped_column(Float, nullable=True)
    leverage: Mapped[float | None] = mapped_column(Float, nullable=True)
