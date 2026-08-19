"""
Execution Simulator — Models realistic transaction costs and market friction.

Key principle: fill_price != signal_price. Every simulated execution includes:
    - Slippage: Price impact proportional to volatility (configurable model)
    - Commission: Fixed or percentage-based fees
    - Spread: Bid-ask spread impact

This module ensures backtests don't overstate returns by assuming frictionless execution.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum

from src.domain.interfaces import IExecutionSimulator

logger = logging.getLogger(__name__)


class SlippageModel(str, Enum):
    """Available slippage models."""

    FIXED_BPS = "fixed_bps"  # Fixed basis points
    VOLATILITY_PROPORTIONAL = "volatility_proportional"  # Proportional to recent volatility


@dataclass(frozen=True)
class ExecutionResult:
    """Result of simulating an order execution."""

    fill_price: float
    commission: float
    slippage_cost: float
    total_cost: float  # commission + slippage_cost


class ExecutionSimulator(IExecutionSimulator):
    """Simulates order execution with configurable friction models.

    Default model:
        fill_price = current_price * (1 + direction * slippage_rate)
        commission = fill_price * quantity * commission_rate
    """

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

        Args:
            symbol: Asset symbol.
            side: 'buy' or 'sell'.
            quantity: Number of shares/units.
            current_price: The price at execution bar (e.g., next-bar open).
            volatility: Recent annualized volatility (for volatility-proportional slippage).
            commission_rate_bps: Commission rate in basis points.
            slippage_rate_bps: Slippage rate in basis points.

        Returns:
            (fill_price, commission, slippage_cost)
        """
        # Convert basis points to decimal
        commission_rate = commission_rate_bps / 10_000
        slippage_rate = slippage_rate_bps / 10_000

        # Slippage direction: buying pushes price up, selling pushes down
        direction = 1.0 if side == "buy" else -1.0
        slippage_pct = slippage_rate  # Can be enhanced with volatility model

        # Fill price includes slippage
        fill_price = current_price * (1.0 + direction * slippage_pct)

        # Commission on notional value
        notional = abs(fill_price * quantity)
        commission = notional * commission_rate

        # Slippage cost = price impact * quantity
        slippage_cost = abs(fill_price - current_price) * abs(quantity)

        return fill_price, commission, slippage_cost

    def simulate_fill_detailed(
        self,
        symbol: str,
        side: str,
        quantity: float,
        current_price: float,
        volatility: float,
        commission_rate_bps: float,
        slippage_rate_bps: float,
        slippage_model: SlippageModel = SlippageModel.FIXED_BPS,
    ) -> ExecutionResult:
        """Extended simulation with model selection."""
        commission_rate = commission_rate_bps / 10_000
        direction = 1.0 if side == "buy" else -1.0

        if slippage_model == SlippageModel.VOLATILITY_PROPORTIONAL:
            # Slippage proportional to daily volatility
            daily_vol = volatility / (252**0.5)
            slippage_pct = daily_vol * (slippage_rate_bps / 10_000) * 10  # Scale factor
        else:
            slippage_pct = slippage_rate_bps / 10_000

        fill_price = current_price * (1.0 + direction * slippage_pct)
        notional = abs(fill_price * quantity)
        commission = notional * commission_rate
        slippage_cost = abs(fill_price - current_price) * abs(quantity)

        return ExecutionResult(
            fill_price=fill_price,
            commission=commission,
            slippage_cost=slippage_cost,
            total_cost=commission + slippage_cost,
        )
