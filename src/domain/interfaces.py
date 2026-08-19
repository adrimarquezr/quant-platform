"""
Domain Interfaces — Abstract contracts for infrastructure adapters.

These define WHAT the domain needs, not HOW it's implemented.
Concrete implementations live in src/infrastructure/.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

import polars as pl

from src.domain.models import (
    BacktestConfig,
    BacktestResult,
    Signal,
)


class IMarketDataProvider(ABC):
    """Contract for fetching market data from any source."""

    @abstractmethod
    def fetch_ohlcv(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
        frequency: str = "1d",
    ) -> pl.DataFrame:
        """Fetch OHLCV data for a single symbol.

        Returns a Polars DataFrame with columns:
            [timestamp, open, high, low, close, volume, adjusted_close]
        Sorted by timestamp ascending.
        """

    @abstractmethod
    def fetch_multiple(
        self,
        symbols: list[str],
        start_date: date,
        end_date: date,
        frequency: str = "1d",
    ) -> dict[str, pl.DataFrame]:
        """Fetch OHLCV data for multiple symbols."""

    @abstractmethod
    def get_provider_name(self) -> str:
        """Return the name of this data provider."""


class IStrategy(ABC):
    """Contract for a systematic trading strategy.

    A strategy receives market data and/or features, and produces signals.
    It must NOT perform portfolio construction or order execution.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique strategy identifier."""

    @property
    @abstractmethod
    def version(self) -> str:
        """Semantic version string."""

    @abstractmethod
    def generate_signals(
        self,
        data: dict[str, pl.DataFrame],
        parameters: dict[str, float | int | str | bool],
    ) -> list[Signal]:
        """Generate trading signals from market data / features.

        Args:
            data: Symbol -> DataFrame with OHLCV + features.
            parameters: Strategy-specific parameters.

        Returns:
            List of Signal objects with direction and strength.
        """

    @abstractmethod
    def get_parameter_schema(self) -> dict[str, dict[str, object]]:
        """Return the schema of configurable parameters.

        Example:
            {
                "lookback_period": {"type": "int", "default": 20, "min": 5, "max": 252},
                "threshold": {"type": "float", "default": 0.02, "min": 0.0, "max": 1.0},
            }
        """


class IBacktestEngine(ABC):
    """Contract for the backtesting engine."""

    @abstractmethod
    def run(
        self,
        config: BacktestConfig,
        data: dict[str, pl.DataFrame],
        strategy: IStrategy,
    ) -> BacktestResult:
        """Execute a full backtest and return the result."""


class IExecutionSimulator(ABC):
    """Contract for simulating order execution with realistic friction."""

    @abstractmethod
    def simulate_fill(
        self,
        symbol: str,
        side: str,
        quantity: float,
        current_price: float,
        volatility: float,
        commission_rate_bps: float,
        slippage_rate_bps: float,
    ) -> tuple[float, float, float]:
        """Simulate filling an order with slippage and commissions.

        Returns:
            (fill_price, commission, slippage_cost)
        """


class IDataQualityValidator(ABC):
    """Contract for data quality validation."""

    @abstractmethod
    def validate(self, df: pl.DataFrame, symbol: str) -> list[str]:
        """Validate a market data DataFrame.

        Returns:
            List of error messages. Empty list means data is valid.
        """
