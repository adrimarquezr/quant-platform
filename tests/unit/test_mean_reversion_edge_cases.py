"""
Tests for Mean Reversion Strategy — comprehensive testing of signals and edge cases.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import polars as pl
import pytest

from src.domain.models import SignalDirection
from src.strategies.mean_reversion import MeanReversionStrategy


@pytest.mark.unit
class TestMeanReversionEdgeCases:
    """Test suite for MeanReversionStrategy edge cases and signals."""

    def setup_method(self) -> None:
        self.strategy = MeanReversionStrategy()

    def _create_df(self, prices: list[float]) -> pl.DataFrame:
        dates = [datetime(2023, 1, 1) + timedelta(days=i) for i in range(len(prices))]
        return pl.DataFrame(
            {
                "timestamp": dates,
                "open": prices,
                "high": [p * 1.01 for p in prices],
                "low": [p * 0.99 for p in prices],
                "close": prices,
                "volume": [10000.0] * len(prices),
            }
        )

    def test_entry_long_when_price_plummets(self) -> None:
        """When the last price plunges far below rolling mean, generate LONG signal."""
        # 20 days around 100, then drop to 80
        prices = [100.0 + (i % 2) for i in range(20)] + [80.0]
        df = self._create_df(prices)
        signals = self.strategy.generate_signals(
            {"SPY": df},
            {"lookback_period": 20, "entry_threshold": 2.0, "exit_threshold": 0.5},
        )
        assert len(signals) == 1
        assert signals[0].direction == SignalDirection.LONG
        assert signals[0].strength > 0

    def test_entry_short_when_price_spikes(self) -> None:
        """When the last price spikes far above rolling mean, generate SHORT signal."""
        prices = [100.0 + (i % 2) for i in range(20)] + [130.0]
        df = self._create_df(prices)
        signals = self.strategy.generate_signals(
            {"SPY": df},
            {"lookback_period": 20, "entry_threshold": 2.0, "exit_threshold": 0.5},
        )
        assert len(signals) == 1
        assert signals[0].direction == SignalDirection.SHORT
        assert signals[0].strength < 0

    def test_exit_flat_when_near_mean(self) -> None:
        """When price is within exit threshold of rolling mean, signal is FLAT."""
        prices = [100.0 for _ in range(21)]
        df = self._create_df(prices)
        signals = self.strategy.generate_signals(
            {"SPY": df},
            {"lookback_period": 20, "entry_threshold": 2.0, "exit_threshold": 0.5},
        )
        assert len(signals) == 1
        assert signals[0].direction == SignalDirection.FLAT
        assert signals[0].strength == 0.0

    def test_zero_volatility_constant_prices(self) -> None:
        """Constant prices have std=0 and must safely return FLAT without divide-by-zero."""
        prices = [50.0] * 30
        df = self._create_df(prices)
        signals = self.strategy.generate_signals({"SPY": df}, {"lookback_period": 10})
        assert len(signals) == 1
        assert signals[0].direction == SignalDirection.FLAT
        assert signals[0].metadata["z_score"] == 0.0

    def test_insufficient_data(self) -> None:
        """If data length is less than lookback, no signals are produced."""
        prices = [100.0, 101.0, 102.0]
        df = self._create_df(prices)
        signals = self.strategy.generate_signals({"SPY": df}, {"lookback_period": 20})
        assert len(signals) == 0

    def test_empty_dataframe(self) -> None:
        """Empty input dataframe must return empty signals."""
        df = pl.DataFrame(
            {"timestamp": [], "open": [], "high": [], "low": [], "close": [], "volume": []}
        )
        signals = self.strategy.generate_signals({"SPY": df}, {"lookback_period": 10})
        assert len(signals) == 0
