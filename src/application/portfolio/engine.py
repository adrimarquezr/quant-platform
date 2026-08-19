"""
Portfolio Engine — Translates strategy signals into constrained target portfolio weights.

Core Principles:
    1. Separation of concerns: Signal generation != Portfolio construction != Execution.
    2. Rigorous weighting: Equal weight, Inverse volatility, Volatility targeting.
    3. Strict constraint enforcement: Position limits, Gross exposure caps, Max turnover.
"""

from __future__ import annotations

import logging
from datetime import datetime

from src.domain.interfaces import IPortfolioEngine
from src.domain.models import (
    PortfolioConstraints,
    PortfolioConstructionMethod,
    Signal,
    SignalDirection,
    TargetWeights,
)

logger = logging.getLogger(__name__)


class PortfolioEngine(IPortfolioEngine):
    """Systematic Portfolio Construction Engine with constraint management."""

    def __init__(self, default_constraints: PortfolioConstraints | None = None) -> None:
        self.default_constraints = default_constraints or PortfolioConstraints()

    def construct_weights(
        self,
        signals: list[Signal],
        current_weights: dict[str, float] | None = None,
        volatilities: dict[str, float] | None = None,
        method: PortfolioConstructionMethod = PortfolioConstructionMethod.EQUAL_WEIGHT,
        constraints: PortfolioConstraints | None = None,
        timestamp: datetime | None = None,
    ) -> TargetWeights:
        """Compute constrained target weights from trading signals and market parameters.

        Args:
            signals: List of Signal objects from strategies.
            current_weights: Existing portfolio weights before rebalancing (for turnover).
            volatilities: Annualized or rolling asset volatilities (symbol -> vol).
            method: Weighting scheme (Equal Weight, Inverse Vol, Vol Targeting).
            constraints: Portfolio limits (max position, gross exposure, turnover).
            timestamp: Timestamp of the rebalance decision.

        Returns:
            TargetWeights with constrained target allocation per asset.
        """
        active_constraints = constraints or self.default_constraints
        now = timestamp or datetime.utcnow()
        current_weights = current_weights or {}
        volatilities = volatilities or {}

        # Filter out flat signals
        active_signals = [
            s for s in signals if s.direction != SignalDirection.FLAT and s.strength != 0.0
        ]

        if not active_signals:
            # All signals flat -> target weights 0 for active, apply turnover check
            raw_weights: dict[str, float] = {s.symbol: 0.0 for s in signals}
            final_weights, turnover = self._apply_turnover_constraint(
                target_weights=raw_weights,
                current_weights=current_weights,
                max_turnover=active_constraints.max_turnover,
            )
            return TargetWeights(
                weights=final_weights,
                timestamp=now,
                method=method,
                turnover=turnover,
                metadata={"status": "all_flat"},
            )

        # 1. Base Weighting
        if method == PortfolioConstructionMethod.INVERSE_VOLATILITY:
            raw_weights = self._inverse_volatility_weights(active_signals, volatilities)
        elif method == PortfolioConstructionMethod.VOLATILITY_TARGETING:
            base_weights = self._inverse_volatility_weights(active_signals, volatilities)
            target_vol = active_constraints.target_volatility or 0.10
            raw_weights = self._apply_volatility_targeting(base_weights, volatilities, target_vol)
        else:
            # Default: Equal Weight
            raw_weights = self._equal_weights(active_signals)

        # Include symbols from input signals that are flat as 0.0
        for s in signals:
            if s.symbol not in raw_weights:
                raw_weights[s.symbol] = 0.0

        # 2. Apply Position Limits and Gross Exposure Cap
        constrained_weights = self._apply_position_and_exposure_constraints(
            weights=raw_weights,
            max_position_weight=active_constraints.max_position_weight,
            max_gross_exposure=active_constraints.max_gross_exposure,
        )

        # 3. Apply Turnover Limit relative to current holdings
        final_weights, turnover = self._apply_turnover_constraint(
            target_weights=constrained_weights,
            current_weights=current_weights,
            max_turnover=active_constraints.max_turnover,
        )

        return TargetWeights(
            weights=final_weights,
            timestamp=now,
            method=method,
            turnover=turnover,
            metadata={
                "active_assets": float(len([w for w in final_weights.values() if abs(w) > 1e-6])),
                "gross_exposure": sum(abs(w) for w in final_weights.values()),
                "net_exposure": sum(final_weights.values()),
            },
        )

    # --------------------------------------------------------------------------
    # Weighting Algorithms
    # --------------------------------------------------------------------------

    def _equal_weights(self, active_signals: list[Signal]) -> dict[str, float]:
        """Equal weight allocation: 1 / N for each active asset, signed by direction."""
        n = len(active_signals)
        if n == 0:
            return {}

        unit_weight = 1.0 / n
        weights: dict[str, float] = {}
        for s in active_signals:
            sign = 1.0 if s.direction == SignalDirection.LONG else -1.0
            weights[s.symbol] = sign * unit_weight * abs(s.strength)

        # Normalize so sum of absolute weights = 1.0
        return self._normalize_gross(weights, 1.0)

    def _inverse_volatility_weights(
        self,
        active_signals: list[Signal],
        volatilities: dict[str, float],
        fallback_vol: float = 0.20,
    ) -> dict[str, float]:
        """Inverse volatility weighting: weight_i proportional to (1 / vol_i)."""
        raw_inv_vols: dict[str, float] = {}

        for s in active_signals:
            vol = volatilities.get(s.symbol, fallback_vol)
            if vol <= 0.0001:  # Protect against zero / near-zero vol
                vol = fallback_vol

            inv_vol = (1.0 / vol) * abs(s.strength)
            sign = 1.0 if s.direction == SignalDirection.LONG else -1.0
            raw_inv_vols[s.symbol] = sign * inv_vol

        return self._normalize_gross(raw_inv_vols, 1.0)

    def _apply_volatility_targeting(
        self,
        base_weights: dict[str, float],
        volatilities: dict[str, float],
        target_vol: float,
        fallback_vol: float = 0.20,
    ) -> dict[str, float]:
        """Scale weights to achieve an overall annualized portfolio volatility target."""
        if not base_weights or target_vol <= 0:
            return base_weights

        # Estimate simple portfolio weighted volatility (conservative upper bound)
        weighted_vol = sum(
            abs(w) * volatilities.get(sym, fallback_vol) for sym, w in base_weights.items()
        )

        if weighted_vol <= 1e-6:
            return base_weights

        vol_scalar = target_vol / weighted_vol
        # Apply scalar (capped at 2.0x leverage)
        vol_scalar = min(vol_scalar, 2.0)

        return {sym: w * vol_scalar for sym, w in base_weights.items()}

    # --------------------------------------------------------------------------
    # Constraint Algorithms
    # --------------------------------------------------------------------------

    def _apply_position_and_exposure_constraints(
        self,
        weights: dict[str, float],
        max_position_weight: float,
        max_gross_exposure: float,
    ) -> dict[str, float]:
        """Enforce maximum weight per position and maximum total gross exposure."""
        constrained: dict[str, float] = {}

        # 1. Clip individual positions to max_position_weight
        for sym, w in weights.items():
            if abs(w) > max_position_weight:
                constrained[sym] = max_position_weight if w > 0 else -max_position_weight
            else:
                constrained[sym] = w

        # 2. Check and scale down if gross exposure exceeds limit
        gross_exposure = sum(abs(w) for w in constrained.values())
        if gross_exposure > max_gross_exposure and gross_exposure > 0:
            scale = max_gross_exposure / gross_exposure
            constrained = {sym: w * scale for sym, w in constrained.items()}

        return constrained

    def _apply_turnover_constraint(
        self,
        target_weights: dict[str, float],
        current_weights: dict[str, float],
        max_turnover: float,
    ) -> tuple[dict[str, float], float]:
        """Enforce maximum rebalancing turnover constraint.

        Turnover = 0.5 * sum(|w_target - w_current|)
        If turnover > max_turnover, adjust target linearly:
            w_final = w_current + alpha * (w_target - w_current), where alpha = max_turnover / turnover.
        """
        all_symbols = set(target_weights.keys()).union(set(current_weights.keys()))
        diff_sum = 0.0

        for sym in all_symbols:
            w_tgt = target_weights.get(sym, 0.0)
            w_cur = current_weights.get(sym, 0.0)
            diff_sum += abs(w_tgt - w_cur)

        turnover = 0.5 * diff_sum

        if turnover <= max_turnover or turnover <= 1e-6:
            # Within limits
            return target_weights, turnover

        # Exceeded limit -> damp adjustment
        alpha = max_turnover / turnover
        adjusted_weights: dict[str, float] = {}
        for sym in all_symbols:
            w_tgt = target_weights.get(sym, 0.0)
            w_cur = current_weights.get(sym, 0.0)
            w_adj = w_cur + alpha * (w_tgt - w_cur)
            if abs(w_adj) > 1e-6:
                adjusted_weights[sym] = w_adj

        actual_turnover = max_turnover
        return adjusted_weights, actual_turnover

    @staticmethod
    def _normalize_gross(weights: dict[str, float], target_gross: float = 1.0) -> dict[str, float]:
        """Scale weights so sum(abs(weights)) == target_gross."""
        gross = sum(abs(w) for w in weights.values())
        if gross <= 1e-8:
            return dict.fromkeys(weights, 0.0)
        scale = target_gross / gross
        return {s: w * scale for s, w in weights.items()}
