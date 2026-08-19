"""
Risk Engine — Quantitative risk evaluation, VaR/CVaR computation, and limit governance.

Key Principles:
    1. Comprehensive metrics: Historical VaR, CVaR/Expected Shortfall, Drawdowns, Beta, HHI.
    2. Explicit governance: Portfolios must be evaluated against configured risk limits.
    3. Transparent verdicts: APPROVED vs REJECTED with explainable RiskViolation records.
"""

from __future__ import annotations

import logging
from datetime import datetime

import numpy as np

from src.domain.interfaces import IRiskEngine
from src.domain.models import (
    DrawdownDetails,
    RiskLimitConfig,
    RiskProfile,
    RiskVerdict,
    RiskViolation,
)

logger = logging.getLogger(__name__)


class RiskEngine(IRiskEngine):
    """Calculates quantitative risk profiles and enforces strict limit governance."""

    def __init__(self, default_limits: RiskLimitConfig | None = None) -> None:
        self.default_limits = default_limits or RiskLimitConfig()

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
        """Evaluate full risk profile of a portfolio or backtest and check limits."""
        active_limits = limits or self.default_limits
        now = timestamp or datetime.utcnow()

        # 1. Historical VaR and CVaR
        var_95 = self.calculate_var(
            returns=returns,
            confidence_level=active_limits.confidence_level,
            lookback_days=active_limits.lookback_days,
        )
        cvar_95 = self.calculate_cvar(
            returns=returns,
            confidence_level=active_limits.confidence_level,
            lookback_days=active_limits.lookback_days,
        )

        # 2. Annualized Volatility
        volatility = self._calculate_annualized_volatility(returns)

        # 3. Drawdown Details
        drawdown_details = self.calculate_drawdown_details(equity_curve)

        # 4. Exposures and Concentration
        gross_exposure = sum(abs(w) for w in current_weights.values())
        net_exposure = sum(current_weights.values())
        concentration_hhi = sum(w**2 for w in current_weights.values())

        # 5. Beta against benchmark
        beta = self._calculate_beta(returns, benchmark_returns) if benchmark_returns else None

        # 6. Correlation matrix
        correlations = self._calculate_correlations(asset_returns) if asset_returns else {}

        # 7. Check Limits and Build Violations
        violations: list[RiskViolation] = []

        # Check: Max Position Weight
        max_pos = max((abs(w) for w in current_weights.values()), default=0.0)
        if max_pos > active_limits.max_position_weight + 1e-4:
            violations.append(
                RiskViolation(
                    rule_name="max_position_weight",
                    description=f"Single position weight ({max_pos:.2%}) exceeds limit ({active_limits.max_position_weight:.2%})",
                    actual_value=float(max_pos),
                    limit_value=float(active_limits.max_position_weight),
                    severity="ERROR",
                )
            )

        # Check: Max Gross Exposure
        if gross_exposure > active_limits.max_gross_exposure + 1e-4:
            violations.append(
                RiskViolation(
                    rule_name="max_gross_exposure",
                    description=f"Gross exposure ({gross_exposure:.2%}) exceeds limit ({active_limits.max_gross_exposure:.2%})",
                    actual_value=float(gross_exposure),
                    limit_value=float(active_limits.max_gross_exposure),
                    severity="ERROR",
                )
            )

        # Check: Max Annualized Volatility
        if volatility > active_limits.max_volatility + 1e-4:
            violations.append(
                RiskViolation(
                    rule_name="max_volatility",
                    description=f"Annualized volatility ({volatility:.2%}) exceeds limit ({active_limits.max_volatility:.2%})",
                    actual_value=float(volatility),
                    limit_value=float(active_limits.max_volatility),
                    severity="ERROR",
                )
            )

        # Check: Max Drawdown
        if drawdown_details.max_drawdown > active_limits.max_drawdown + 1e-4:
            violations.append(
                RiskViolation(
                    rule_name="max_drawdown",
                    description=f"Maximum drawdown ({drawdown_details.max_drawdown:.2%}) exceeds limit ({active_limits.max_drawdown:.2%})",
                    actual_value=float(drawdown_details.max_drawdown),
                    limit_value=float(active_limits.max_drawdown),
                    severity="ERROR",
                )
            )

        # Check: Max VaR (95%)
        if var_95 > active_limits.max_var_95 + 1e-4:
            violations.append(
                RiskViolation(
                    rule_name="max_var_95",
                    description=f"Historical VaR 95% ({var_95:.2%}) exceeds limit ({active_limits.max_var_95:.2%})",
                    actual_value=float(var_95),
                    limit_value=float(active_limits.max_var_95),
                    severity="ERROR",
                )
            )

        verdict = RiskVerdict.REJECTED if violations else RiskVerdict.APPROVED

        return RiskProfile(
            timestamp=now,
            var_95=var_95,
            cvar_95=cvar_95,
            volatility=volatility,
            drawdown_details=drawdown_details,
            gross_exposure=gross_exposure,
            net_exposure=net_exposure,
            concentration_hhi=concentration_hhi,
            beta=beta,
            correlations=correlations,
            verdict=verdict,
            violations=violations,
        )

    # --------------------------------------------------------------------------
    # Mathematical Risk Calculations
    # --------------------------------------------------------------------------

    def calculate_var(
        self,
        returns: list[float],
        confidence_level: float = 0.95,
        lookback_days: int = 252,
    ) -> float:
        """Calculate Historical Value at Risk (VaR).

        VaR is reported as a positive loss fraction.
        E.g. VaR 95% = 0.02 means with 95% confidence, 1-day loss <= 2%.
        """
        if not returns or len(returns) < 5:
            return 0.0

        sample = np.array(returns[-lookback_days:])
        # Alpha percentile (e.g. 5th percentile for 95% confidence)
        alpha = 1.0 - confidence_level
        percentile_val = float(np.percentile(sample, alpha * 100))

        # VaR is positive loss: -percentile_val if negative, else 0.0
        return max(0.0, -percentile_val)

    def calculate_cvar(
        self,
        returns: list[float],
        confidence_level: float = 0.95,
        lookback_days: int = 252,
    ) -> float:
        """Calculate Conditional Value at Risk (CVaR / Expected Shortfall).

        CVaR is the expected loss given that loss exceeds the VaR threshold.
        """
        if not returns or len(returns) < 5:
            return 0.0

        sample = np.array(returns[-lookback_days:])
        alpha = 1.0 - confidence_level
        cutoff = float(np.percentile(sample, alpha * 100))

        tail_returns = sample[sample <= cutoff]
        if len(tail_returns) == 0:
            return max(0.0, -cutoff)

        mean_tail_loss = -float(np.mean(tail_returns))
        return max(0.0, mean_tail_loss)

    def calculate_drawdown_details(
        self,
        equity_curve: list[float],
        dates: list[datetime] | None = None,
    ) -> DrawdownDetails:
        """Track running peak, drawdowns, trough, and recovery status."""
        if not equity_curve:
            return DrawdownDetails(
                current_drawdown=0.0,
                max_drawdown=0.0,
                peak_equity=0.0,
                trough_equity=0.0,
                is_recovered=True,
            )

        eq = np.array(equity_curve, dtype=float)
        running_peak = np.maximum.accumulate(eq)
        drawdowns = np.where(running_peak > 0, (eq - running_peak) / running_peak, 0.0)

        # Drawdowns are <= 0, so max loss is abs(min(drawdowns))
        max_dd_fraction = abs(float(np.min(drawdowns)))
        current_dd_fraction = abs(float(drawdowns[-1]))

        peak_idx = int(np.argmax(running_peak))
        trough_idx = int(np.argmin(drawdowns))

        peak_val = float(running_peak[-1])
        trough_val = float(eq[trough_idx]) if len(eq) > trough_idx else 0.0

        peak_dt = dates[peak_idx] if dates and len(dates) > peak_idx else None
        trough_dt = dates[trough_idx] if dates and len(dates) > trough_idx else None
        is_recovered = bool(current_dd_fraction < 1e-5)

        return DrawdownDetails(
            current_drawdown=current_dd_fraction,
            max_drawdown=max_dd_fraction,
            peak_equity=peak_val,
            trough_equity=trough_val,
            peak_date=peak_dt,
            trough_date=trough_dt,
            is_recovered=is_recovered,
        )

    @staticmethod
    def _calculate_annualized_volatility(returns: list[float], trading_days: int = 252) -> float:
        if not returns or len(returns) < 2:
            return 0.0
        arr = np.array(returns)
        return float(np.std(arr, ddof=1) * np.sqrt(trading_days))

    @staticmethod
    def _calculate_beta(returns: list[float], benchmark_returns: list[float]) -> float | None:
        min_len = min(len(returns), len(benchmark_returns))
        if min_len < 10:
            return None

        r = np.array(returns[-min_len:])
        b = np.array(benchmark_returns[-min_len:])

        var_b = float(np.var(b, ddof=1))
        if var_b < 1e-10:
            return 1.0

        cov_rb = float(np.cov(r, b, ddof=1)[0, 1])
        return float(cov_rb / var_b)

    @staticmethod
    def _calculate_correlations(
        asset_returns: dict[str, list[float]],
    ) -> dict[str, dict[str, float]]:
        symbols = list(asset_returns.keys())
        if len(symbols) < 2:
            return {s: {s: 1.0} for s in symbols}

        min_len = min(len(ret) for ret in asset_returns.values())
        if min_len < 5:
            return {s: {s: 1.0} for s in symbols}

        matrix_data = np.array([asset_returns[s][-min_len:] for s in symbols])
        corr_matrix = np.corrcoef(matrix_data)

        corr_dict: dict[str, dict[str, float]] = {}
        for i, s1 in enumerate(symbols):
            corr_dict[s1] = {}
            for j, s2 in enumerate(symbols):
                corr_dict[s1][s2] = (
                    float(corr_matrix[i, j]) if not np.isnan(corr_matrix[i, j]) else 0.0
                )

        return corr_dict
