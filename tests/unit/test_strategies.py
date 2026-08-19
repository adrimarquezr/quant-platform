"""
Tests for Momentum and Mean Reversion strategies.
"""

from __future__ import annotations

import polars as pl
import pytest

from src.domain.models import SignalDirection
from src.features.engine import compute_all_features
from src.strategies.mean_reversion import MeanReversionStrategy
from src.strategies.momentum import MomentumStrategy


@pytest.mark.unit
class TestMomentumStrategy:
    """Test momentum strategy signal generation."""

    def setup_method(self) -> None:
        self.strategy = MomentumStrategy()

    def test_name_and_version(self) -> None:
        assert self.strategy.name == "momentum"
        assert self.strategy.version == "1.0.0"

    def test_generates_signals(self, sample_multi_symbol_data: dict[str, pl.DataFrame]) -> None:
        """Strategy should produce signals for each symbol."""
        data = {s: compute_all_features(df) for s, df in sample_multi_symbol_data.items()}
        signals = self.strategy.generate_signals(data, {"lookback_period": 10, "threshold": 0.0})
        assert len(signals) > 0
        assert all(s.symbol in sample_multi_symbol_data for s in signals)

    def test_signal_strength_in_range(
        self, sample_multi_symbol_data: dict[str, pl.DataFrame]
    ) -> None:
        """All signal strengths should be in [-1, 1]."""
        data = {s: compute_all_features(df) for s, df in sample_multi_symbol_data.items()}
        signals = self.strategy.generate_signals(data, {"lookback_period": 10, "threshold": 0.0})
        for signal in signals:
            assert -1.0 <= signal.strength <= 1.0

    def test_parameter_schema(self) -> None:
        schema = self.strategy.get_parameter_schema()
        assert "lookback_period" in schema
        assert "threshold" in schema
        assert schema["lookback_period"]["type"] == "int"

    def test_cross_sectional_mode(self, sample_multi_symbol_data: dict[str, pl.DataFrame]) -> None:
        """Cross-sectional mode should rank assets."""
        data = {s: compute_all_features(df) for s, df in sample_multi_symbol_data.items()}
        signals = self.strategy.generate_signals(
            data,
            {"lookback_period": 10, "threshold": 0.0, "mode": "cross_sectional"},
        )
        assert len(signals) > 0


@pytest.mark.unit
class TestMeanReversionStrategy:
    """Test mean reversion strategy signal generation."""

    def setup_method(self) -> None:
        self.strategy = MeanReversionStrategy()

    def test_name_and_version(self) -> None:
        assert self.strategy.name == "mean_reversion"
        assert self.strategy.version == "1.0.0"

    def test_generates_signals(self, sample_multi_symbol_data: dict[str, pl.DataFrame]) -> None:
        data = {s: compute_all_features(df) for s, df in sample_multi_symbol_data.items()}
        signals = self.strategy.generate_signals(
            data, {"lookback_period": 10, "entry_threshold": 2.0, "exit_threshold": 0.5}
        )
        assert len(signals) > 0

    def test_signal_directions_valid(
        self, sample_multi_symbol_data: dict[str, pl.DataFrame]
    ) -> None:
        """All signals should have a valid direction."""
        data = {s: compute_all_features(df) for s, df in sample_multi_symbol_data.items()}
        signals = self.strategy.generate_signals(
            data, {"lookback_period": 10, "entry_threshold": 2.0}
        )
        for signal in signals:
            assert signal.direction in (
                SignalDirection.LONG,
                SignalDirection.SHORT,
                SignalDirection.FLAT,
            )
