"""
Backtesting Engine — Deterministic, next-bar execution backtester.

Core invariants:
    1. Signal at bar t → execution at bar t + execution_delay (default: t+1 open)
    2. Same (data + strategy + config) → identical result (deterministic)
    3. No look-ahead: signals only see data up to and including bar t
    4. Transaction costs are always applied (commission + slippage)

The engine iterates through time, asks the strategy for signals at each bar,
then executes them at the next bar, tracking cash, positions, and equity.
"""

from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime

import polars as pl

from src.domain.interfaces import IBacktestEngine, IStrategy
from src.domain.models import (
    BacktestConfig,
    BacktestResult,
    BacktestStatus,
    Execution,
    Order,
    OrderSide,
    OrderStatus,
    OrderType,
    SignalDirection,
)
from src.execution.simulator import ExecutionSimulator

logger = logging.getLogger(__name__)


class BacktestEngine(IBacktestEngine):
    """Vectorized backtesting engine with next-bar execution.

    Architecture:
        For each bar t:
            1. Update portfolio mark-to-market using bar t prices
            2. Ask strategy for signals using data[:t] (no future data)
            3. Queue orders based on signals
            4. At bar t+1: execute queued orders at open price + slippage
            5. Record equity, returns, orders, executions
    """

    def __init__(self) -> None:
        self.simulator = ExecutionSimulator()

    def run(
        self,
        config: BacktestConfig,
        data: dict[str, pl.DataFrame],
        strategy: IStrategy,
    ) -> BacktestResult:
        """Execute a full backtest run.

        Args:
            config: Immutable backtest configuration.
            data: Symbol -> OHLCV+features DataFrame (must be sorted by timestamp).
            strategy: Strategy instance implementing IStrategy.

        Returns:
            BacktestResult with equity curve, returns, orders, executions, and metrics.
        """
        start_time = time.perf_counter_ns()

        # --- Preparation ---
        # Align all symbols to a common date index
        common_dates = self._get_common_dates(data)
        if len(common_dates) < 2:
            return self._empty_result(config, "Insufficient common dates")

        # Build price lookup: symbol -> {date -> {open, high, low, close, volume}}
        price_lookup = self._build_price_lookup(data, common_dates)

        # --- State ---
        cash = config.initial_cash
        positions: dict[str, float] = {}  # symbol -> quantity
        avg_prices: dict[str, float] = {}  # symbol -> average entry price

        equity_curve: list[float] = []
        returns_list: list[float] = []
        date_list: list[datetime] = []
        all_orders: list[Order] = []
        all_executions: list[Execution] = []

        # Pending orders from previous bar's signals (next-bar execution)
        pending_signals: list[
            tuple[str, SignalDirection, float]
        ] = []  # (symbol, direction, strength)

        prev_equity = config.initial_cash

        # --- Main Loop ---
        for i, current_date in enumerate(common_dates):
            # Step 1: Execute pending orders from PREVIOUS bar's signals
            if pending_signals and i > 0:
                for symbol, direction, strength in pending_signals:
                    if symbol not in price_lookup or current_date not in price_lookup[symbol]:
                        continue

                    bar_data = price_lookup[symbol][current_date]
                    exec_price = bar_data["open"]  # Execute at open of execution bar
                    current_position = positions.get(symbol, 0.0)

                    # Determine target position based on signal
                    portfolio_value = self._calculate_equity(
                        cash, positions, price_lookup, current_date
                    )
                    target_notional = portfolio_value * abs(strength) / max(len(config.universe), 1)

                    if direction == SignalDirection.LONG and current_position <= 0:
                        # Buy to go long
                        quantity = target_notional / exec_price if exec_price > 0 else 0
                        if quantity > 0:
                            order, execution, _cost = self._execute_order(
                                symbol, "buy", quantity, exec_price, config, current_date
                            )
                            cash -= (
                                execution.fill_price * execution.fill_quantity
                            ) + execution.commission
                            positions[symbol] = current_position + execution.fill_quantity
                            avg_prices[symbol] = execution.fill_price
                            all_orders.append(order)
                            all_executions.append(execution)

                    elif direction == SignalDirection.SHORT and current_position >= 0:
                        # Sell to go short (or close long)
                        if current_position > 0:
                            # Close existing long
                            order, execution, _cost = self._execute_order(
                                symbol, "sell", current_position, exec_price, config, current_date
                            )
                            cash += (
                                execution.fill_price * execution.fill_quantity
                            ) - execution.commission
                            positions[symbol] = 0.0
                            all_orders.append(order)
                            all_executions.append(execution)

                    elif direction == SignalDirection.FLAT and current_position != 0:
                        # Close position
                        side = "sell" if current_position > 0 else "buy"
                        qty = abs(current_position)
                        order, execution, _cost = self._execute_order(
                            symbol, side, qty, exec_price, config, current_date
                        )
                        if side == "sell":
                            cash += (
                                execution.fill_price * execution.fill_quantity
                            ) - execution.commission
                        else:
                            cash -= (
                                execution.fill_price * execution.fill_quantity
                            ) + execution.commission
                        positions[symbol] = 0.0
                        all_orders.append(order)
                        all_executions.append(execution)

                pending_signals = []

            # Step 2: Mark-to-market and record equity
            current_equity = self._calculate_equity(cash, positions, price_lookup, current_date)
            equity_curve.append(current_equity)
            daily_return = (current_equity / prev_equity - 1) if prev_equity > 0 else 0.0
            returns_list.append(daily_return)
            date_list.append(current_date)
            prev_equity = current_equity

            # Step 3: Generate signals using data UP TO current bar (no look-ahead)
            sliced_data = self._slice_data_up_to(data, current_date)
            signals = strategy.generate_signals(sliced_data, dict(config.parameters))

            # Step 4: Queue signals for next-bar execution
            for signal in signals:
                pending_signals.append((signal.symbol, signal.direction, signal.strength))

        # --- Calculate Metrics ---
        elapsed_ms = int((time.perf_counter_ns() - start_time) / 1_000_000)
        metrics = self._calculate_metrics(
            equity_curve, returns_list, all_orders, config, executions=all_executions
        )

        return BacktestResult(
            config=config,
            status=BacktestStatus.COMPLETED,
            equity_curve=equity_curve,
            returns=returns_list,
            dates=date_list,
            orders=all_orders,
            executions=all_executions,
            metrics=metrics,
            execution_time_ms=elapsed_ms,
        )

    # --------------------------------------------------------------------------
    # Helper methods
    # --------------------------------------------------------------------------

    def _get_common_dates(self, data: dict[str, pl.DataFrame]) -> list[datetime]:
        """Find dates common to all symbols, sorted ascending."""
        date_sets = []
        for df in data.values():
            dates = set(df["timestamp"].to_list())
            date_sets.append(dates)

        if not date_sets:
            return []

        common = date_sets[0]
        for ds in date_sets[1:]:
            common = common.intersection(ds)

        return sorted(common)

    def _build_price_lookup(
        self, data: dict[str, pl.DataFrame], common_dates: list[datetime]
    ) -> dict[str, dict[datetime, dict[str, float]]]:
        """Build a fast price lookup: symbol -> date -> {open, close, ...}."""
        lookup: dict[str, dict[datetime, dict[str, float]]] = {}
        common_set = set(common_dates)

        for symbol, df in data.items():
            symbol_lookup: dict[datetime, dict[str, float]] = {}
            for row in df.iter_rows(named=True):
                ts = row["timestamp"]
                if ts in common_set:
                    symbol_lookup[ts] = {
                        "open": float(row["open"]),
                        "high": float(row["high"]),
                        "low": float(row["low"]),
                        "close": float(row["close"]),
                        "volume": float(row["volume"]),
                    }
            lookup[symbol] = symbol_lookup

        return lookup

    def _calculate_equity(
        self,
        cash: float,
        positions: dict[str, float],
        price_lookup: dict[str, dict[datetime, dict[str, float]]],
        current_date: datetime,
    ) -> float:
        """Calculate total portfolio equity at a given date."""
        equity = cash
        for symbol, qty in positions.items():
            if symbol in price_lookup and current_date in price_lookup[symbol]:
                equity += qty * price_lookup[symbol][current_date]["close"]
        return equity

    def _execute_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        exec_price: float,
        config: BacktestConfig,
        current_date: datetime,
    ) -> tuple[Order, Execution, float]:
        """Create an Order + Execution with simulated friction."""
        fill_price, commission, slippage_cost = self.simulator.simulate_fill(
            symbol=symbol,
            side=side,
            quantity=quantity,
            current_price=exec_price,
            volatility=0.20,  # Default; will be enhanced with actual vol
            commission_rate_bps=config.commission_rate_bps,
            slippage_rate_bps=config.slippage_rate_bps,
        )

        order = Order(
            id=uuid.uuid4(),
            asset_symbol=symbol,
            side=OrderSide.BUY if side == "buy" else OrderSide.SELL,
            order_type=OrderType.MARKET,
            quantity=quantity,
            status=OrderStatus.FILLED,
            created_at=current_date,
            filled_at=current_date,
        )

        execution = Execution(
            id=uuid.uuid4(),
            order_id=order.id,
            fill_price=fill_price,
            fill_quantity=quantity,
            commission=commission,
            slippage=slippage_cost,
            executed_at=current_date,
        )

        total_cost = commission + slippage_cost
        return order, execution, total_cost

    def _slice_data_up_to(
        self, data: dict[str, pl.DataFrame], current_date: datetime
    ) -> dict[str, pl.DataFrame]:
        """Slice data to include only rows up to and including current_date.

        This is the KEY anti-look-ahead mechanism: the strategy only sees
        historical data, never future bars.
        """
        sliced: dict[str, pl.DataFrame] = {}
        for symbol, df in data.items():
            sliced[symbol] = df.filter(pl.col("timestamp") <= current_date)
        return sliced

    def _calculate_metrics(
        self,
        equity_curve: list[float],
        returns: list[float],
        orders: list[Order],
        config: BacktestConfig,
        executions: list[Execution] | None = None,
    ) -> dict[str, float]:
        """Calculate comprehensive backtest metrics.

        Delegates to the MetricsCalculator for the full suite.
        """
        from src.application.backtesting.metrics import MetricsCalculator

        calculator = MetricsCalculator()
        return calculator.calculate_all(
            equity_curve=equity_curve,
            daily_returns=returns,
            orders=orders,
            executions=executions,
            initial_cash=config.initial_cash,
            trading_days_per_year=252,
        )

    def _empty_result(self, config: BacktestConfig, reason: str) -> BacktestResult:
        """Return an empty/failed backtest result."""
        logger.warning("Backtest failed: %s", reason)
        return BacktestResult(
            config=config,
            status=BacktestStatus.FAILED,
            equity_curve=[],
            returns=[],
            dates=[],
            orders=[],
            executions=[],
            metrics={},
            execution_time_ms=0,
        )
