"""
Backtests Router — Launch backtests and retrieve results.

Thin orchestration layer: receives request, builds domain config, delegates to
BacktestEngine, and returns structured results.
"""

from __future__ import annotations

import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException

from apps.api.schemas import (
    BacktestMetricsResponse,
    BacktestRequest,
    BacktestResponse,
    BacktestSummary,
)
from src.application.backtesting.engine import BacktestEngine
from src.domain.models import BacktestConfig, TimeRange
from src.features.engine import compute_all_features
from src.infrastructure.data_providers.yahoo_finance import YahooFinanceProvider
from src.infrastructure.storage.parquet_storage import ParquetStorage
from src.strategies.mean_reversion import MeanReversionStrategy
from src.strategies.momentum import MomentumStrategy

router = APIRouter(prefix="/backtests", tags=["backtests"])
logger = logging.getLogger(__name__)

# In-memory store for MVP (will be replaced by PostgreSQL persistence)
_backtest_results: dict[str, BacktestResponse] = {}

# Strategy registry
STRATEGY_REGISTRY: dict[str, type] = {
    "momentum": MomentumStrategy,
    "mean_reversion": MeanReversionStrategy,
}

provider = YahooFinanceProvider()
storage = ParquetStorage(base_dir=Path("data"))
engine = BacktestEngine()


@router.post("", response_model=BacktestResponse, status_code=201)
async def run_backtest(request: BacktestRequest) -> BacktestResponse:
    """Launch a backtest with the specified strategy and parameters.

    Pipeline:
        1. Resolve strategy from registry
        2. Load/fetch market data
        3. Compute features
        4. Run backtest engine
        5. Return structured results
    """
    # 1. Resolve strategy
    strategy_cls = STRATEGY_REGISTRY.get(request.strategy_name)
    if strategy_cls is None:
        raise HTTPException(
            status_code=404,
            detail=f"Strategy '{request.strategy_name}' not found. "
            f"Available: {list(STRATEGY_REGISTRY.keys())}",
        )
    strategy = strategy_cls()

    # 2. Load or fetch market data
    data: dict[str, object] = {}
    for symbol in request.universe:
        try:
            if storage.exists(symbol):
                df = storage.load_ohlcv(symbol)
            else:
                df = provider.fetch_ohlcv(
                    symbol, request.start_date, request.end_date, request.frequency
                )
                storage.save_ohlcv(df, symbol, request.frequency)
        except Exception as e:
            logger.exception("Failed to load data for %s", symbol)
            raise HTTPException(
                status_code=500, detail=f"Failed to load data for {symbol}: {e}"
            ) from e

        # 3. Compute features
        df = compute_all_features(df)

        # Filter date range
        start_dt = request.start_date
        end_dt = request.end_date
        df = df.filter(
            (df["timestamp"].dt.date() >= start_dt) & (df["timestamp"].dt.date() <= end_dt)
        )
        data[symbol] = df

    # 4. Build config and run backtest
    config = BacktestConfig(
        strategy_name=request.strategy_name,
        strategy_version=strategy.version,
        parameters=request.parameters,
        universe=request.universe,
        time_range=TimeRange(start=request.start_date, end=request.end_date),
        initial_cash=request.initial_cash,
        commission_rate_bps=request.commission_rate_bps,
        slippage_rate_bps=request.slippage_rate_bps,
        frequency=request.frequency,
    )

    result = engine.run(config, data, strategy)

    # 5. Build response
    backtest_id = str(uuid.uuid4())
    metrics = (
        BacktestMetricsResponse(**result.metrics) if result.metrics else BacktestMetricsResponse()
    )

    response = BacktestResponse(
        id=backtest_id,
        strategy_name=request.strategy_name,
        status=result.status.value,
        metrics=metrics,
        equity_curve=result.equity_curve,
        dates=[d.isoformat() if hasattr(d, "isoformat") else str(d) for d in result.dates],
        execution_time_ms=result.execution_time_ms,
        config={
            "universe": request.universe,
            "start_date": request.start_date.isoformat(),
            "end_date": request.end_date.isoformat(),
            "initial_cash": request.initial_cash,
            "parameters": request.parameters,
        },
    )

    # Store for retrieval
    _backtest_results[backtest_id] = response

    logger.info(
        "Backtest %s completed: strategy=%s, return=%.4f, sharpe=%.2f, time=%dms",
        backtest_id,
        request.strategy_name,
        metrics.total_return,
        metrics.sharpe_ratio,
        result.execution_time_ms,
    )

    return response


@router.get("", response_model=list[BacktestSummary])
async def list_backtests() -> list[BacktestSummary]:
    """List all completed backtests."""
    return [
        BacktestSummary(
            id=bt_id,
            strategy_name=bt.strategy_name,
            status=bt.status,
            total_return=bt.metrics.total_return,
            sharpe_ratio=bt.metrics.sharpe_ratio,
            max_drawdown=bt.metrics.max_drawdown,
            execution_time_ms=bt.execution_time_ms,
        )
        for bt_id, bt in _backtest_results.items()
    ]


@router.get("/{backtest_id}", response_model=BacktestResponse)
async def get_backtest(backtest_id: str) -> BacktestResponse:
    """Retrieve a specific backtest result."""
    if backtest_id not in _backtest_results:
        raise HTTPException(status_code=404, detail=f"Backtest {backtest_id} not found")
    return _backtest_results[backtest_id]


@router.get("/strategies/available", response_model=list[str])
async def list_available_strategies() -> list[str]:
    """List available strategy names."""
    return list(STRATEGY_REGISTRY.keys())
