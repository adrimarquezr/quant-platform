"""
Domain Interfaces — Abstract contracts for infrastructure adapters.

These define WHAT the domain needs, not HOW it's implemented.
Concrete implementations live in src/infrastructure/.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date, datetime

import polars as pl

from src.domain.models import (
    BacktestConfig,
    BacktestResult,
    DataQualityReport,
    DrawdownDetails,
    PortfolioConstraints,
    PortfolioConstructionMethod,
    RiskLimitConfig,
    RiskProfile,
    Signal,
    TargetWeights,
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

    @abstractmethod
    def validate_dataset(
        self,
        df: pl.DataFrame,
        symbol: str,
        dataset_name: str = "daily_ohlcv",
    ) -> DataQualityReport:
        """Perform formal validation and produce a structured DataQualityReport."""


class IPortfolioEngine(ABC):
    """Contract for Portfolio Construction and Constraint Management."""

    @abstractmethod
    def construct_weights(
        self,
        signals: list[Signal],
        current_weights: dict[str, float] | None = None,
        volatilities: dict[str, float] | None = None,
        method: PortfolioConstructionMethod = PortfolioConstructionMethod.EQUAL_WEIGHT,
        constraints: PortfolioConstraints | None = None,
        timestamp: datetime | None = None,
    ) -> TargetWeights:
        """Compute constrained target weights from signals and market metrics."""


class IRiskEngine(ABC):
    """Contract for Portfolio Risk Evaluation and Limit Governance."""

    @abstractmethod
    def evaluate_risk(
        self,
        equity_curve: list[float],
        returns: list[float],
        current_weights: dict[str, float],
        asset_returns: dict[str, list[float]] | None = None,
        benchmark_returns: list[float] | None = None,
        limits: RiskLimitConfig | None = None,
        timestamp: datetime | None = None,
    ) -> RiskProfile:
        """Evaluate portfolio risk profile and verify risk limits."""

    @abstractmethod
    def calculate_var(
        self,
        returns: list[float],
        confidence_level: float = 0.95,
        lookback_days: int = 252,
    ) -> float:
        """Calculate Historical Value at Risk (VaR)."""

    @abstractmethod
    def calculate_cvar(
        self,
        returns: list[float],
        confidence_level: float = 0.95,
        lookback_days: int = 252,
    ) -> float:
        """Calculate Conditional Value at Risk (CVaR / Expected Shortfall)."""

    @abstractmethod
    def calculate_drawdown_details(
        self,
        equity_curve: list[float],
        dates: list[datetime] | None = None,
    ) -> DrawdownDetails:
        """Calculate detailed drawdown metrics (peak, trough, recovery, current)."""
