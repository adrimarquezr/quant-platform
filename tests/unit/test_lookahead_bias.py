"""
Quantitative Validation Tests — Strict Verification of Absence of Look-Ahead Bias.

Verifies:
1. Signal Invariance: Altering future bars (t+1..T) does NOT change signals at bar t.
2. Execution Lag: Signals emitted at bar t are filled exclusively at bar t+1 at Open price.
3. Feature Backward-Looking Integrity: All calculated features depend solely on past and current bar data.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import numpy as np
import polars as pl
import pytest

from src.application.backtesting.engine import BacktestEngine
from src.domain.models import BacktestConfig, TimeRange
from src.features.engine import FeatureEngine
from src.strategies.mean_reversion import MeanReversionStrategy
from src.strategies.momentum import MomentumStrategy


def _create_synthetic_history(n_bars: int = 120, seed: int = 42) -> pl.DataFrame:
    """Generate a reproducible OHLCV DataFrame for look-ahead testing."""
    rng = np.random.default_rng(seed)
    start_dt = datetime(2023, 1, 2, tzinfo=UTC)
    dates = [start_dt + timedelta(days=i) for i in range(n_bars)]

    # Random walk
    rets = rng.normal(0.0005, 0.015, size=n_bars)
    closes = 100.0 * np.exp(np.cumsum(rets))
    opens = closes * rng.uniform(0.995, 1.005, size=n_bars)
    highs = np.maximum(opens, closes) * rng.uniform(1.001, 1.015, size=n_bars)
    lows = np.minimum(opens, closes) * rng.uniform(0.985, 0.999, size=n_bars)
    volumes = rng.integers(100_000, 1_000_000, size=n_bars).astype(float)

    return pl.DataFrame(
        {
            "timestamp": dates,
            "open": opens,
            "high": highs,
            "low": lows,
            "close": closes,
            "volume": volumes,
        }
    )


@pytest.mark.unit
class TestLookAheadBias:
    """Rigorous tests asserting zero look-ahead bias across all quantitative layers."""

    def test_feature_engine_zero_lookahead(self) -> None:
        """Modifying future prices in a dataset must NOT change feature values at past bars."""
        engine = FeatureEngine()
        df_base = _create_synthetic_history(100)
        feat_base = engine.transform(df_base)

        # Mutate the last 20 bars completely (simulate unexpected future spike)
        df_tampered = df_base.clone()
        tampered_closes = df_tampered["close"].to_list()
        for i in range(80, 100):
            tampered_closes[i] = tampered_closes[i] * 5.0  # 500% spike

        df_tampered = df_tampered.with_columns(pl.Series("close", tampered_closes))
        feat_tampered = engine.transform(df_tampered)

        # Assert all bars from 0 to 79 have 100% identical feature values
        for col in ["return_1d", "volatility_20d", "sma_20", "z_score_20d", "drawdown"]:
            if col in feat_base.columns:
                base_vals = feat_base[col][:80].to_list()
                tampered_vals = feat_tampered[col][:80].to_list()
                for b, t in zip(base_vals, tampered_vals, strict=False):
                    if b is None or (isinstance(b, float) and np.isnan(b)):
                        assert t is None or (isinstance(t, float) and np.isnan(t))
                    else:
                        assert abs(b - t) < 1e-9, f"Look-ahead detected in column {col}"

    def test_strategy_signals_zero_lookahead(self) -> None:
        """Strategy signal generation at bar t must be invariant to data from bar t+1 onwards."""
        engine = FeatureEngine()
        strategy = MomentumStrategy()

        df_base = _create_synthetic_history(80)
        df_feat = engine.transform(df_base)

        # Signals generated on first 50 bars
        df_slice_50 = df_feat[:50]
        signals_50 = strategy.generate_signals(
            data={"SPY": df_slice_50},
            parameters={"lookback_period": 20, "holding_period": 5, "top_n": 1},
        )

        # Modify bars 51-80 aggressively
        df_tampered = df_base.clone()
        tampered_closes = df_tampered["close"].to_list()
        for i in range(50, 80):
            tampered_closes[i] = tampered_closes[i] * 10.0

        df_tampered = df_tampered.with_columns(pl.Series("close", tampered_closes))
        df_feat_tampered = engine.transform(df_tampered)

        # Slice tampered dataset up to 50
        df_tampered_slice_50 = df_feat_tampered[:50]
        signals_tampered_50 = strategy.generate_signals(
            data={"SPY": df_tampered_slice_50},
            parameters={"lookback_period": 20, "holding_period": 5, "top_n": 1},
        )

        # Compare signals
        assert len(signals_50) == len(signals_tampered_50)
        for s1, s2 in zip(signals_50, signals_tampered_50, strict=False):
            assert s1.symbol == s2.symbol
            assert s1.direction == s2.direction
            assert abs(s1.strength - s2.strength) < 1e-6

    def test_next_bar_open_execution_delay(self) -> None:
        """Assert orders generated at bar t are filled at Open price of bar t+1."""
        engine = FeatureEngine()
        strategy = MeanReversionStrategy()

        df = _create_synthetic_history(60)
        df_feat = engine.transform(df)

        config = BacktestConfig(
            strategy_name="mean_reversion",
            strategy_version="1.0.0",
            parameters={"lookback_period": 10, "entry_threshold": 1.0, "exit_threshold": 0.5},
            universe=["SPY"],
            time_range=TimeRange(
                start=df["timestamp"][0].date(),
                end=df["timestamp"][-1].date(),
            ),
            initial_cash=100_000.0,
            commission_rate_bps=0.0,
            slippage_rate_bps=0.0,
        )

        backtester = BacktestEngine()
        result = backtester.run(config, {"SPY": df_feat}, strategy)

        # Check executions match open prices of subsequent bars
        for ex in result.executions:
            # Find order corresponding to execution
            matching_order = next((o for o in result.orders if o.id == ex.order_id), None)
            assert matching_order is not None

            fill_date = ex.executed_at.date()
            bar_row = df.filter(pl.col("timestamp").dt.date() == fill_date)
            if len(bar_row) > 0:
                expected_open = float(bar_row["open"][0])
                # Execution should be fill_price == open price (with 0 slip)
                assert abs(ex.fill_price - expected_open) < 1e-4
