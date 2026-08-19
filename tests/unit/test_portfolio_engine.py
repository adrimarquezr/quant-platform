"""
Tests for Portfolio Engine — construction methods, weighting algorithms, and constraints.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from src.application.portfolio.engine import PortfolioEngine
from src.domain.models import (
    PortfolioConstraints,
    PortfolioConstructionMethod,
    Signal,
    SignalDirection,
)


@pytest.mark.unit
class TestPortfolioEngine:
    """Test suite for PortfolioEngine."""

    def setup_method(self) -> None:
        self.engine = PortfolioEngine()
        self.now = datetime(2024, 1, 15)

    def test_equal_weight_long_only(self) -> None:
        """Equal weight should distribute 1/N to active long signals."""
        signals = [
            Signal(symbol="SPY", timestamp=self.now, direction=SignalDirection.LONG, strength=1.0),
            Signal(symbol="QQQ", timestamp=self.now, direction=SignalDirection.LONG, strength=1.0),
            Signal(symbol="IWM", timestamp=self.now, direction=SignalDirection.LONG, strength=1.0),
            Signal(symbol="TLT", timestamp=self.now, direction=SignalDirection.LONG, strength=1.0),
        ]
        target = self.engine.construct_weights(
            signals=signals,
            method=PortfolioConstructionMethod.EQUAL_WEIGHT,
            constraints=PortfolioConstraints(max_position_weight=0.50),
        )
        assert len(target.weights) == 4
        for w in target.weights.values():
            assert abs(w - 0.25) < 1e-4
        assert abs(target.gross_exposure - 1.0) < 1e-4

    def test_equal_weight_long_short(self) -> None:
        """Equal weight long/short should have signed weights."""
        signals = [
            Signal(symbol="SPY", timestamp=self.now, direction=SignalDirection.LONG, strength=1.0),
            Signal(symbol="QQQ", timestamp=self.now, direction=SignalDirection.SHORT, strength=1.0),
        ]
        target = self.engine.construct_weights(
            signals=signals,
            method=PortfolioConstructionMethod.EQUAL_WEIGHT,
            constraints=PortfolioConstraints(max_position_weight=0.60),
        )
        assert abs(target.weights["SPY"] - 0.50) < 1e-4
        assert abs(target.weights["QQQ"] - (-0.50)) < 1e-4
        assert abs(target.gross_exposure - 1.0) < 1e-4
        assert abs(target.net_exposure - 0.0) < 1e-4

    def test_inverse_volatility_allocation(self) -> None:
        """Lower volatility asset should receive higher weight."""
        signals = [
            Signal(
                symbol="LOW_VOL", timestamp=self.now, direction=SignalDirection.LONG, strength=1.0
            ),
            Signal(
                symbol="HIGH_VOL", timestamp=self.now, direction=SignalDirection.LONG, strength=1.0
            ),
        ]
        volatilities = {"LOW_VOL": 0.10, "HIGH_VOL": 0.30}
        target = self.engine.construct_weights(
            signals=signals,
            volatilities=volatilities,
            method=PortfolioConstructionMethod.INVERSE_VOLATILITY,
            constraints=PortfolioConstraints(max_position_weight=0.80),
        )
        # 1/0.10 = 10, 1/0.30 = 3.333 -> weights 10/13.333 = 0.75, 3.333/13.333 = 0.25
        assert target.weights["LOW_VOL"] > target.weights["HIGH_VOL"]
        assert abs(target.weights["LOW_VOL"] - 0.75) < 1e-2
        assert abs(target.weights["HIGH_VOL"] - 0.25) < 1e-2

    def test_volatility_targeting(self) -> None:
        """Volatility targeting scales positions to match target portfolio volatility."""
        signals = [
            Signal(symbol="SPY", timestamp=self.now, direction=SignalDirection.LONG, strength=1.0),
        ]
        volatilities = {"SPY": 0.20}
        # Target vol 10% on an asset with 20% vol -> weight scaled to 0.50
        constraints = PortfolioConstraints(target_volatility=0.10, max_position_weight=1.0)
        target = self.engine.construct_weights(
            signals=signals,
            volatilities=volatilities,
            method=PortfolioConstructionMethod.VOLATILITY_TARGETING,
            constraints=constraints,
        )
        assert abs(target.weights["SPY"] - 0.50) < 1e-2

    def test_max_position_weight_clipping(self) -> None:
        """Positions exceeding max_position_weight must be capped."""
        signals = [
            Signal(symbol="SPY", timestamp=self.now, direction=SignalDirection.LONG, strength=1.0),
            Signal(symbol="QQQ", timestamp=self.now, direction=SignalDirection.LONG, strength=1.0),
        ]
        constraints = PortfolioConstraints(max_position_weight=0.30, max_gross_exposure=1.0)
        target = self.engine.construct_weights(
            signals=signals,
            method=PortfolioConstructionMethod.EQUAL_WEIGHT,
            constraints=constraints,
        )
        # Equal weight was 0.50 each, but capped at 0.30
        assert target.weights["SPY"] <= 0.30 + 1e-6
        assert target.weights["QQQ"] <= 0.30 + 1e-6

    def test_max_turnover_dampening(self) -> None:
        """Turnover constraint must smoothly damp rebalancing when delta exceeds limit."""
        # Current: 100% SPY. Target: 100% QQQ. Turnover would be 1.0 (100%).
        current_weights = {"SPY": 1.0, "QQQ": 0.0}
        signals = [
            Signal(symbol="QQQ", timestamp=self.now, direction=SignalDirection.LONG, strength=1.0),
            Signal(symbol="SPY", timestamp=self.now, direction=SignalDirection.FLAT, strength=0.0),
        ]
        constraints = PortfolioConstraints(max_turnover=0.30, max_position_weight=1.0)
        target = self.engine.construct_weights(
            signals=signals,
            current_weights=current_weights,
            constraints=constraints,
        )
        assert target.turnover <= 0.30 + 1e-4
        assert target.weights["SPY"] > 0.60  # Damped transition, still holds some SPY
        assert target.weights["QQQ"] > 0.20

    def test_all_flat_signals(self) -> None:
        """When all signals are flat, target weights are 0."""
        signals = [
            Signal(symbol="SPY", timestamp=self.now, direction=SignalDirection.FLAT, strength=0.0),
            Signal(symbol="QQQ", timestamp=self.now, direction=SignalDirection.FLAT, strength=0.0),
        ]
        target = self.engine.construct_weights(signals=signals)
        assert all(w == 0.0 for w in target.weights.values())
