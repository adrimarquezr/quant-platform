"""
Tests for Domain Models — validates invariants, constraints, and business rules.
"""

from __future__ import annotations

from datetime import date, datetime

import pytest

from src.domain.models import (
    BacktestConfig,
    Bar,
    PortfolioState,
    Position,
    Signal,
    SignalDirection,
    TimeRange,
)


@pytest.mark.unit
class TestTimeRange:
    """Test TimeRange value object invariants."""

    def test_valid_range(self) -> None:
        tr = TimeRange(start=date(2023, 1, 1), end=date(2023, 12, 31))
        assert tr.days == 364

    def test_same_day_range(self) -> None:
        tr = TimeRange(start=date(2023, 1, 1), end=date(2023, 1, 1))
        assert tr.days == 0

    def test_invalid_range_raises(self) -> None:
        with pytest.raises(ValueError, match=r"start.*must be <= end"):
            TimeRange(start=date(2023, 12, 31), end=date(2023, 1, 1))


@pytest.mark.unit
class TestBar:
    """Test Bar value object invariants."""

    def test_valid_bar(self) -> None:
        bar = Bar(
            symbol="SPY",
            timestamp=datetime(2023, 1, 2),
            open=100,
            high=105,
            low=99,
            close=103,
            volume=1e6,
        )
        assert bar.symbol == "SPY"

    def test_high_less_than_low_raises(self) -> None:
        with pytest.raises(ValueError, match=r"high.*low"):
            Bar(
                symbol="SPY",
                timestamp=datetime(2023, 1, 2),
                open=100,
                high=95,
                low=99,
                close=103,
                volume=1e6,
            )

    def test_negative_price_raises(self) -> None:
        with pytest.raises(ValueError, match="Negative"):
            Bar(
                symbol="SPY",
                timestamp=datetime(2023, 1, 2),
                open=-5,
                high=105,
                low=99,
                close=103,
                volume=1e6,
            )


@pytest.mark.unit
class TestSignal:
    """Test Signal value object invariants."""

    def test_valid_signal(self) -> None:
        signal = Signal(
            symbol="SPY",
            timestamp=datetime(2023, 1, 2),
            direction=SignalDirection.LONG,
            strength=0.8,
        )
        assert signal.strength == 0.8

    def test_strength_out_of_range_raises(self) -> None:
        with pytest.raises(ValueError, match="strength"):
            Signal(
                symbol="SPY",
                timestamp=datetime(2023, 1, 2),
                direction=SignalDirection.LONG,
                strength=1.5,
            )


@pytest.mark.unit
class TestPortfolioState:
    """Test PortfolioState entity calculations."""

    def test_total_equity_with_positions(self) -> None:
        state = PortfolioState(
            timestamp=datetime(2023, 1, 2),
            cash=50_000,
            positions={
                "SPY": Position(
                    asset_symbol="SPY", quantity=100, avg_entry_price=400, current_price=450
                ),
                "QQQ": Position(
                    asset_symbol="QQQ", quantity=50, avg_entry_price=300, current_price=320
                ),
            },
        )
        # 50000 + (100*450) + (50*320) = 50000 + 45000 + 16000 = 111000
        assert state.total_equity == 111_000

    def test_cash_only_portfolio(self) -> None:
        state = PortfolioState(timestamp=datetime(2023, 1, 2), cash=100_000)
        assert state.total_equity == 100_000
        assert state.exposure == 0.0

    def test_unrealized_pnl(self) -> None:
        pos = Position(asset_symbol="SPY", quantity=100, avg_entry_price=400, current_price=450)
        assert pos.unrealized_pnl == 5000  # 100 * (450 - 400)
        assert pos.market_value == 45000


@pytest.mark.unit
class TestBacktestConfig:
    """Test BacktestConfig invariants."""

    def test_execution_delay_must_be_positive(self) -> None:
        """Anti look-ahead: execution_delay_bars must be >= 1."""
        with pytest.raises(ValueError, match="execution_delay_bars"):
            BacktestConfig(
                strategy_name="test",
                strategy_version="1.0",
                parameters={},
                universe=["SPY"],
                time_range=TimeRange(start=date(2023, 1, 1), end=date(2023, 12, 31)),
                execution_delay_bars=0,  # INVALID
            )

    def test_initial_cash_must_be_positive(self) -> None:
        with pytest.raises(ValueError, match="initial_cash"):
            BacktestConfig(
                strategy_name="test",
                strategy_version="1.0",
                parameters={},
                universe=["SPY"],
                time_range=TimeRange(start=date(2023, 1, 1), end=date(2023, 12, 31)),
                initial_cash=-1000,
            )
