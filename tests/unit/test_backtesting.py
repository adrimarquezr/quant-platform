"""
Tests for the Backtesting Engine and Metrics Calculator.
"""

from __future__ import annotations

from datetime import date

import polars as pl
import pytest

from src.application.backtesting.engine import BacktestEngine
from src.application.backtesting.metrics import MetricsCalculator
from src.domain.models import BacktestConfig, BacktestStatus, TimeRange
from src.features.engine import compute_all_features
from src.strategies.mean_reversion import MeanReversionStrategy
from src.strategies.momentum import MomentumStrategy


@pytest.mark.unit
class TestMetricsCalculator:
    """Test quantitative metrics calculations."""

    def setup_method(self) -> None:
        self.calc = MetricsCalculator()

    def test_total_return(self) -> None:
        """Total return = (final / initial) - 1."""
        equity = [100_000.0, 101_000.0, 102_000.0, 110_000.0]
        returns = [0.0, 0.01, 0.0099, 0.0784]
        metrics = self.calc.calculate_all(equity, returns, [], initial_cash=100_000.0)
        assert abs(metrics["total_return"] - 0.10) < 0.01

    def test_max_drawdown(self) -> None:
        """Max drawdown of [100, 110, 90, 95] should be ~-18.18%."""
        equity = [100.0, 110.0, 90.0, 95.0]
        dd = MetricsCalculator._max_drawdown(__import__("numpy").array(equity))
        expected = (90.0 - 110.0) / 110.0  # -0.1818
        assert abs(dd - expected) < 0.001

    def test_sharpe_ratio_zero_vol(self) -> None:
        """Zero volatility returns should produce Sharpe = 0."""
        import numpy as np

        sharpe = MetricsCalculator._sharpe_ratio(np.array([0.0, 0.0, 0.0]), 252)
        assert sharpe == 0.0

    def test_empty_equity_returns_empty_metrics(self) -> None:
        metrics = self.calc.calculate_all([], [], [])
        assert metrics["total_return"] == 0.0
        assert metrics["sharpe_ratio"] == 0.0

    def test_monthly_returns_structure(self) -> None:
        """Monthly returns should produce a year -> month -> return dict."""
        from datetime import datetime

        dates = [datetime(2023, 1, d) for d in range(2, 30)] + [
            datetime(2023, 2, d) for d in range(1, 25)
        ]
        equity = [float(x) for x in range(100, 100 + len(dates))]
        result = MetricsCalculator.calculate_monthly_returns(equity, dates)
        assert "2023" in result

    def test_trade_statistics_round_trip(self) -> None:
        """Test FIFO trade matching for win rate, profit factor, and trade returns."""
        import uuid

        from src.domain.models import Execution, Order, OrderSide

        o1 = Order(id=uuid.uuid4(), asset_symbol="SPY", side=OrderSide.BUY, quantity=10.0)
        ex1 = Execution(order_id=o1.id, fill_price=100.0, fill_quantity=10.0, commission=1.0)

        # Sell 10 at 110 (win: profit = 100 - 2 = 98)
        o2 = Order(id=uuid.uuid4(), asset_symbol="SPY", side=OrderSide.SELL, quantity=10.0)
        ex2 = Execution(order_id=o2.id, fill_price=110.0, fill_quantity=10.0, commission=1.0)

        # Buy 10 at 100
        o3 = Order(id=uuid.uuid4(), asset_symbol="SPY", side=OrderSide.BUY, quantity=10.0)
        ex3 = Execution(order_id=o3.id, fill_price=100.0, fill_quantity=10.0, commission=1.0)

        # Sell 10 at 95 (loss: profit = -50 - 2 = -52)
        o4 = Order(id=uuid.uuid4(), asset_symbol="SPY", side=OrderSide.SELL, quantity=10.0)
        ex4 = Execution(order_id=o4.id, fill_price=95.0, fill_quantity=10.0, commission=1.0)

        orders = [o1, o2, o3, o4]
        executions = [ex1, ex2, ex3, ex4]

        stats = MetricsCalculator._trade_statistics(orders, executions)
        assert stats["total_trades"] == 2.0
        assert stats["win_rate"] == 0.5
        assert stats["profit_factor"] > 1.0
        assert stats["best_trade"] == 0.10
        assert stats["worst_trade"] == -0.05


@pytest.mark.unit
class TestBacktestEngine:
    """Test the backtesting engine determinism and correctness."""

    def setup_method(self) -> None:
        self.engine = BacktestEngine()

    def test_deterministic_results(self, sample_multi_symbol_data: dict[str, pl.DataFrame]) -> None:
        """Same inputs must produce identical outputs (determinism)."""
        config = BacktestConfig(
            strategy_name="momentum",
            strategy_version="1.0.0",
            parameters={"lookback_period": 20, "threshold": 0.0},
            universe=list(sample_multi_symbol_data.keys()),
            time_range=TimeRange(start=date(2023, 1, 2), end=date(2023, 3, 14)),
            initial_cash=100_000,
        )

        # Compute features
        data = {s: compute_all_features(df) for s, df in sample_multi_symbol_data.items()}

        strategy = MomentumStrategy()
        result1 = self.engine.run(config, data, strategy)
        result2 = self.engine.run(config, data, strategy)

        assert result1.equity_curve == result2.equity_curve
        assert result1.metrics == result2.metrics

    def test_backtest_completes(self, sample_multi_symbol_data: dict[str, pl.DataFrame]) -> None:
        """A basic backtest should complete without errors."""
        config = BacktestConfig(
            strategy_name="momentum",
            strategy_version="1.0.0",
            parameters={"lookback_period": 10, "threshold": 0.0},
            universe=list(sample_multi_symbol_data.keys()),
            time_range=TimeRange(start=date(2023, 1, 2), end=date(2023, 3, 14)),
        )
        data = {s: compute_all_features(df) for s, df in sample_multi_symbol_data.items()}
        strategy = MomentumStrategy()
        result = self.engine.run(config, data, strategy)

        assert result.status == BacktestStatus.COMPLETED
        assert len(result.equity_curve) > 0
        assert len(result.returns) > 0
        assert result.execution_time_ms >= 0

    def test_initial_equity_equals_initial_cash(
        self, sample_multi_symbol_data: dict[str, pl.DataFrame]
    ) -> None:
        """First equity point should equal initial cash."""
        config = BacktestConfig(
            strategy_name="momentum",
            strategy_version="1.0.0",
            parameters={"lookback_period": 20},
            universe=list(sample_multi_symbol_data.keys()),
            time_range=TimeRange(start=date(2023, 1, 2), end=date(2023, 3, 14)),
            initial_cash=50_000,
        )
        data = {s: compute_all_features(df) for s, df in sample_multi_symbol_data.items()}
        strategy = MomentumStrategy()
        result = self.engine.run(config, data, strategy)

        assert result.equity_curve[0] == 50_000

    def test_mean_reversion_runs(self, sample_multi_symbol_data: dict[str, pl.DataFrame]) -> None:
        """Mean reversion strategy should also work through the engine."""
        config = BacktestConfig(
            strategy_name="mean_reversion",
            strategy_version="1.0.0",
            parameters={"lookback_period": 10, "entry_threshold": 1.5, "exit_threshold": 0.5},
            universe=list(sample_multi_symbol_data.keys()),
            time_range=TimeRange(start=date(2023, 1, 2), end=date(2023, 3, 14)),
        )
        data = {s: compute_all_features(df) for s, df in sample_multi_symbol_data.items()}
        strategy = MeanReversionStrategy()
        result = self.engine.run(config, data, strategy)

        assert result.status == BacktestStatus.COMPLETED


@pytest.mark.unit
class TestExecutionSimulator:
    """Test the execution simulator friction model."""

    def test_buy_slippage_increases_price(self) -> None:
        """Buying should result in a higher fill price due to slippage."""
        from src.execution.simulator import ExecutionSimulator

        sim = ExecutionSimulator()
        fill_price, commission, slippage = sim.simulate_fill(
            symbol="SPY",
            side="buy",
            quantity=100,
            current_price=450.0,
            volatility=0.20,
            commission_rate_bps=5.0,
            slippage_rate_bps=5.0,
        )
        assert fill_price > 450.0  # Slippage pushed price up
        assert commission > 0
        assert slippage > 0

    def test_sell_slippage_decreases_price(self) -> None:
        """Selling should result in a lower fill price due to slippage."""
        from src.execution.simulator import ExecutionSimulator

        sim = ExecutionSimulator()
        fill_price, _commission, _slippage = sim.simulate_fill(
            symbol="SPY",
            side="sell",
            quantity=100,
            current_price=450.0,
            volatility=0.20,
            commission_rate_bps=5.0,
            slippage_rate_bps=5.0,
        )
        assert fill_price < 450.0  # Slippage pushed price down

    def test_zero_commission(self) -> None:
        """Zero commission rate should produce zero commission."""
        from src.execution.simulator import ExecutionSimulator

        sim = ExecutionSimulator()
        _, commission, _ = sim.simulate_fill(
            symbol="SPY",
            side="buy",
            quantity=100,
            current_price=450.0,
            volatility=0.20,
            commission_rate_bps=0.0,
            slippage_rate_bps=5.0,
        )
        assert commission == 0.0
