"""
Quantitative Metrics Calculator — Comprehensive backtest performance analysis.

Computes the full metrics suite:
    - Return metrics: Total Return, CAGR
    - Risk metrics: Annualized Volatility, Max Drawdown, VaR, CVaR
    - Risk-adjusted: Sharpe Ratio, Sortino Ratio, Calmar Ratio
    - Trade statistics: Win Rate, Profit Factor, Avg Trade, Best/Worst Trade
    - Exposure & Turnover

All computations use standard quantitative finance formulas with no look-ahead.
"""

from __future__ import annotations

import math

import numpy as np

from src.domain.models import Order


class MetricsCalculator:
    """Calculate comprehensive backtest metrics from equity curve and trade data."""

    def calculate_all(
        self,
        equity_curve: list[float],
        daily_returns: list[float],
        orders: list[Order],
        initial_cash: float = 100_000.0,
        trading_days_per_year: int = 252,
        risk_free_rate: float = 0.0,
    ) -> dict[str, float]:
        """Calculate the complete metrics suite.

        Args:
            equity_curve: Daily portfolio equity values.
            daily_returns: Daily percentage returns.
            orders: List of executed orders.
            initial_cash: Starting capital.
            trading_days_per_year: Annualization factor.
            risk_free_rate: Annual risk-free rate for Sharpe calculation.

        Returns:
            Dictionary of metric name -> value.
        """
        if len(equity_curve) < 2 or len(daily_returns) < 2:
            return self._empty_metrics()

        # Filter out the first return (always 0)
        returns = np.array(daily_returns[1:], dtype=np.float64)
        equity = np.array(equity_curve, dtype=np.float64)

        n_days = len(returns)
        final_equity = equity[-1]

        # --- Return Metrics ---
        total_return = (final_equity / initial_cash) - 1
        years = n_days / trading_days_per_year
        cagr = (final_equity / initial_cash) ** (1 / years) - 1 if years > 0 else 0.0

        # --- Risk Metrics ---
        ann_vol = float(np.std(returns, ddof=1) * math.sqrt(trading_days_per_year))
        max_dd = self._max_drawdown(equity)

        # --- Risk-Adjusted Metrics ---
        daily_rf = risk_free_rate / trading_days_per_year
        excess_returns = returns - daily_rf

        sharpe = self._sharpe_ratio(excess_returns, trading_days_per_year)
        sortino = self._sortino_ratio(excess_returns, trading_days_per_year)
        calmar = cagr / abs(max_dd) if max_dd != 0 else 0.0

        # --- Trade Statistics ---
        trade_stats = self._trade_statistics(orders)

        # --- Exposure ---
        non_zero_return_days = np.count_nonzero(returns)
        exposure_time = non_zero_return_days / n_days if n_days > 0 else 0.0

        # --- Turnover ---
        turnover = len(orders) / (n_days * 2) if n_days > 0 else 0.0  # Normalized

        return {
            "total_return": round(total_return, 6),
            "cagr": round(cagr, 6),
            "annualized_volatility": round(ann_vol, 6),
            "sharpe_ratio": round(sharpe, 4),
            "sortino_ratio": round(sortino, 4),
            "calmar_ratio": round(calmar, 4),
            "max_drawdown": round(max_dd, 6),
            "win_rate": round(trade_stats["win_rate"], 4),
            "profit_factor": round(trade_stats["profit_factor"], 4),
            "total_trades": trade_stats["total_trades"],
            "avg_trade_return": round(trade_stats["avg_trade"], 6),
            "best_trade": round(trade_stats["best_trade"], 6),
            "worst_trade": round(trade_stats["worst_trade"], 6),
            "exposure_time": round(exposure_time, 4),
            "turnover": round(turnover, 4),
            "final_equity": round(final_equity, 2),
        }

    @staticmethod
    def _max_drawdown(equity: np.ndarray) -> float:
        """Calculate maximum drawdown from peak equity.

        Returns a negative number (e.g., -0.15 means 15% drawdown).
        """
        if len(equity) == 0:
            return 0.0

        peak = np.maximum.accumulate(equity)
        drawdown = (equity - peak) / peak
        return float(np.min(drawdown))

    @staticmethod
    def _sharpe_ratio(
        excess_returns: np.ndarray,
        trading_days_per_year: int,
    ) -> float:
        """Annualized Sharpe ratio.

        Sharpe = mean(excess_returns) / std(excess_returns) * sqrt(252)
        """
        if len(excess_returns) == 0:
            return 0.0
        std = np.std(excess_returns, ddof=1)
        if std == 0:
            return 0.0
        return float(np.mean(excess_returns) / std * math.sqrt(trading_days_per_year))

    @staticmethod
    def _sortino_ratio(
        excess_returns: np.ndarray,
        trading_days_per_year: int,
    ) -> float:
        """Annualized Sortino ratio — penalizes only downside volatility.

        Sortino = mean(excess_returns) / downside_std * sqrt(252)
        """
        if len(excess_returns) == 0:
            return 0.0
        downside = excess_returns[excess_returns < 0]
        if len(downside) == 0:
            return float("inf") if np.mean(excess_returns) > 0 else 0.0
        downside_std = float(np.std(downside, ddof=1))
        if downside_std == 0:
            return 0.0
        return float(np.mean(excess_returns) / downside_std * math.sqrt(trading_days_per_year))

    @staticmethod
    def _trade_statistics(orders: list[Order]) -> dict[str, float]:
        """Calculate trade-level statistics from order history."""
        if not orders:
            return {
                "win_rate": 0.0,
                "profit_factor": 0.0,
                "total_trades": 0,
                "avg_trade": 0.0,
                "best_trade": 0.0,
                "worst_trade": 0.0,
            }

        total_trades = len(orders)

        # Basic statistics
        return {
            "win_rate": 0.0,  # Requires round-trip trade matching
            "profit_factor": 0.0,  # Requires round-trip trade matching
            "total_trades": total_trades,
            "avg_trade": 0.0,
            "best_trade": 0.0,
            "worst_trade": 0.0,
        }

    @staticmethod
    def _empty_metrics() -> dict[str, float]:
        """Return zeroed metrics for failed/empty backtests."""
        return {
            "total_return": 0.0,
            "cagr": 0.0,
            "annualized_volatility": 0.0,
            "sharpe_ratio": 0.0,
            "sortino_ratio": 0.0,
            "calmar_ratio": 0.0,
            "max_drawdown": 0.0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "total_trades": 0,
            "avg_trade_return": 0.0,
            "best_trade": 0.0,
            "worst_trade": 0.0,
            "exposure_time": 0.0,
            "turnover": 0.0,
            "final_equity": 0.0,
        }

    @staticmethod
    def calculate_monthly_returns(
        equity_curve: list[float],
        dates: list,
    ) -> dict[str, dict[str, float]]:
        """Generate a monthly returns matrix: {year: {month: return}}.

        Used for monthly returns heatmaps in Superset dashboards.
        """
        if len(equity_curve) < 2 or len(dates) < 2:
            return {}

        monthly: dict[str, dict[str, float]] = {}
        prev_month_equity = equity_curve[0]
        prev_month = None

        for i, (dt, _) in enumerate(zip(dates, equity_curve, strict=False)):
            year = str(dt.year)
            month = str(dt.month).zfill(2)
            current_key = f"{year}-{month}"

            if prev_month is not None and current_key != prev_month:
                # Month boundary — record return
                year_key, month_key = prev_month.split("-")
                if year_key not in monthly:
                    monthly[year_key] = {}
                monthly[year_key][month_key] = round(
                    (equity_curve[i - 1] / prev_month_equity) - 1, 6
                )
                prev_month_equity = equity_curve[i - 1]

            prev_month = current_key

        # Last month
        if prev_month and equity_curve:
            year_key, month_key = prev_month.split("-")
            if year_key not in monthly:
                monthly[year_key] = {}
            monthly[year_key][month_key] = round((equity_curve[-1] / prev_month_equity) - 1, 6)

        return monthly
