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
from collections import deque
from collections.abc import Sequence
from typing import Any

import numpy as np

from src.domain.models import Execution, Order, OrderSide


class MetricsCalculator:
    """Calculate comprehensive backtest metrics from equity curve and trade data."""

    def calculate_all(
        self,
        equity_curve: Sequence[float],
        daily_returns: Sequence[float],
        orders: Sequence[Order],
        executions: Sequence[Execution] | None = None,
        initial_cash: float = 100_000.0,
        trading_days_per_year: int = 252,
        risk_free_rate: float = 0.0,
    ) -> dict[str, float]:
        """Calculate the complete metrics suite.

        Args:
            equity_curve: Daily portfolio equity values.
            daily_returns: Daily percentage returns.
            orders: Sequence of executed orders.
            executions: Optional sequence of fills for precise trade analytics.
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
        final_equity = float(equity[-1])

        # --- Return Metrics ---
        total_return = (final_equity / initial_cash) - 1.0
        years = n_days / trading_days_per_year
        cagr = (final_equity / initial_cash) ** (1.0 / years) - 1.0 if years > 0 else 0.0

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
        trade_stats = self._trade_statistics(orders, executions)

        # --- Exposure ---
        non_zero_return_days = int(np.count_nonzero(returns))
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
    def _trade_statistics(
        orders: Sequence[Order],
        executions: Sequence[Execution] | None = None,
    ) -> dict[str, float]:
        """Calculate trade-level statistics from order history using FIFO lot matching."""
        if not orders:
            return {
                "win_rate": 0.0,
                "profit_factor": 0.0,
                "total_trades": 0.0,
                "avg_trade": 0.0,
                "best_trade": 0.0,
                "worst_trade": 0.0,
            }

        # Build execution map order_id -> execution if available
        exec_map: dict[Any, Execution] = {}
        if executions:
            for execution_item in executions:
                exec_map[execution_item.order_id] = execution_item

        # Group orders by symbol
        symbol_orders: dict[str, list[tuple[str, float, float, float]]] = {}
        for order in orders:
            sym = order.asset_symbol
            if sym not in symbol_orders:
                symbol_orders[sym] = []

            side = "buy" if order.side in (OrderSide.BUY, "buy") else "sell"
            exec_item = exec_map.get(order.id)
            price = exec_item.fill_price if exec_item else (order.limit_price or 100.0)
            qty = exec_item.fill_quantity if exec_item else order.quantity
            friction = (exec_item.commission + exec_item.slippage) if exec_item else 0.0

            symbol_orders[sym].append((side, qty, price, friction))

        closed_trade_pnls: list[float] = []
        closed_trade_returns: list[float] = []

        for _sym, fill_list in symbol_orders.items():
            # Lot queue: list of [side, remaining_qty, price, friction_per_unit]
            lots: deque[list[Any]] = deque()

            for side, qty, price, friction in fill_list:
                remaining_qty = qty
                friction_per_unit = friction / qty if qty > 0 else 0.0

                while lots and remaining_qty > 1e-6:
                    lot_side, lot_qty, lot_price, lot_fric_unit = lots[0]
                    if lot_side == side:
                        # Same direction -> add to inventory
                        break

                    # Opposite direction -> match round-trip
                    matched_qty = min(lot_qty, remaining_qty)
                    if lot_side == "buy" and side == "sell":
                        # Long position closed
                        pnl = (price - lot_price) * matched_qty - (
                            (lot_fric_unit + friction_per_unit) * matched_qty
                        )
                        ret = (price - lot_price) / lot_price if lot_price > 0 else 0.0
                    else:
                        # Short position closed
                        pnl = (lot_price - price) * matched_qty - (
                            (lot_fric_unit + friction_per_unit) * matched_qty
                        )
                        ret = (lot_price - price) / lot_price if lot_price > 0 else 0.0

                    closed_trade_pnls.append(pnl)
                    closed_trade_returns.append(ret)

                    remaining_qty -= matched_qty
                    lots[0][1] -= matched_qty
                    if lots[0][1] <= 1e-6:
                        lots.popleft()

                if remaining_qty > 1e-6:
                    lots.append([side, remaining_qty, price, friction_per_unit])

        if not closed_trade_pnls:
            return {
                "win_rate": 0.0,
                "profit_factor": 0.0,
                "total_trades": float(len(orders)),
                "avg_trade": 0.0,
                "best_trade": 0.0,
                "worst_trade": 0.0,
            }

        total_closed = len(closed_trade_pnls)
        wins = [pnl for pnl in closed_trade_pnls if pnl > 0]
        losses = [abs(pnl) for pnl in closed_trade_pnls if pnl < 0]

        win_rate = len(wins) / total_closed if total_closed > 0 else 0.0
        gross_profit = sum(wins)
        gross_loss = sum(losses)

        if gross_loss > 0:
            profit_factor = gross_profit / gross_loss
        elif gross_profit > 0:
            profit_factor = 100.0  # All wins cap
        else:
            profit_factor = 0.0

        avg_trade = float(np.mean(closed_trade_returns)) if closed_trade_returns else 0.0
        best_trade = float(np.max(closed_trade_returns)) if closed_trade_returns else 0.0
        worst_trade = float(np.min(closed_trade_returns)) if closed_trade_returns else 0.0

        return {
            "win_rate": win_rate,
            "profit_factor": profit_factor,
            "total_trades": float(total_closed),
            "avg_trade": avg_trade,
            "best_trade": best_trade,
            "worst_trade": worst_trade,
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
            "total_trades": 0.0,
            "avg_trade_return": 0.0,
            "best_trade": 0.0,
            "worst_trade": 0.0,
            "exposure_time": 0.0,
            "turnover": 0.0,
            "final_equity": 0.0,
        }

    @staticmethod
    def calculate_monthly_returns(
        equity_curve: Sequence[float],
        dates: Sequence[Any],
    ) -> dict[str, dict[str, float]]:
        """Generate a monthly returns matrix: {year: {month: return}}.

        Used for monthly returns heatmaps in Superset dashboards.
        """
        if len(equity_curve) < 2 or len(dates) < 2:
            return {}

        monthly: dict[str, dict[str, float]] = {}
        prev_month_equity = float(equity_curve[0])
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
                    (float(equity_curve[i - 1]) / prev_month_equity) - 1.0, 6
                )
                prev_month_equity = float(equity_curve[i - 1])

            prev_month = current_key

        # Last month
        if prev_month and equity_curve:
            year_key, month_key = prev_month.split("-")
            if year_key not in monthly:
                monthly[year_key] = {}
            monthly[year_key][month_key] = round(
                (float(equity_curve[-1]) / prev_month_equity) - 1.0, 6
            )

        return monthly
