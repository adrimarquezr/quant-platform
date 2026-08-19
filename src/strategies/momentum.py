"""
Momentum Strategy — Time-Series and Cross-Sectional Momentum.

Time-Series Momentum (TSMOM):
    Go long when the trailing return over a lookback period is positive,
    go short (or flat) when it is negative.

Cross-Sectional Momentum (CSMOM):
    Rank assets by trailing return and go long the top quantile,
    short the bottom quantile.

Reference: Moskowitz, Ooi & Pedersen (2012), "Time Series Momentum"
"""

from __future__ import annotations

from datetime import datetime

import polars as pl

from src.domain.interfaces import IStrategy
from src.domain.models import Signal, SignalDirection


class MomentumStrategy(IStrategy):
    """Multi-horizon momentum strategy.

    Default behavior: Time-series momentum using configurable lookback and threshold.
    """

    @property
    def name(self) -> str:
        return "momentum"

    @property
    def version(self) -> str:
        return "1.0.0"

    def generate_signals(
        self,
        data: dict[str, pl.DataFrame],
        parameters: dict[str, float | int | str | bool],
    ) -> list[Signal]:
        """Generate momentum signals for each symbol.

        Parameters:
            lookback_period: Number of days for return calculation (default: 20).
            threshold: Minimum absolute return to generate a signal (default: 0.0).
            mode: 'time_series' or 'cross_sectional' (default: 'time_series').
        """
        lookback = int(parameters.get("lookback_period", 20))
        threshold = float(parameters.get("threshold", 0.0))
        mode = str(parameters.get("mode", "time_series"))

        if mode == "cross_sectional":
            return self._cross_sectional_signals(data, lookback, threshold, parameters)
        return self._time_series_signals(data, lookback, threshold)

    def _time_series_signals(
        self,
        data: dict[str, pl.DataFrame],
        lookback: int,
        threshold: float,
    ) -> list[Signal]:
        """Time-series momentum: each asset evaluated independently."""
        signals: list[Signal] = []

        for symbol, df in data.items():
            if len(df) < lookback + 1:
                continue

            # Use the return column if available, otherwise compute
            return_col = f"return_{lookback}d"
            if return_col not in df.columns:
                df = df.with_columns(
                    (pl.col("close") / pl.col("close").shift(lookback) - 1).alias(return_col)
                )

            # Get the last row (most recent signal)
            last_row = df.tail(1)
            ret_value = last_row[return_col].item()
            timestamp = last_row["timestamp"].item()

            if ret_value is None:
                continue

            # Determine direction and strength
            if ret_value > threshold:
                direction = SignalDirection.LONG
                strength = min(ret_value / (threshold + 0.01), 1.0)  # Normalize
            elif ret_value < -threshold:
                direction = SignalDirection.SHORT
                strength = max(ret_value / (threshold + 0.01), -1.0)
            else:
                direction = SignalDirection.FLAT
                strength = 0.0

            # Ensure timestamp is a Python datetime
            if not isinstance(timestamp, datetime):
                timestamp = datetime(timestamp.year, timestamp.month, timestamp.day)

            signals.append(
                Signal(
                    symbol=symbol,
                    timestamp=timestamp,
                    direction=direction,
                    strength=max(-1.0, min(1.0, strength)),
                    metadata={"lookback": float(lookback), "return": float(ret_value)},
                )
            )

        return signals

    def _cross_sectional_signals(
        self,
        data: dict[str, pl.DataFrame],
        lookback: int,
        threshold: float,
        parameters: dict[str, float | int | str | bool],
    ) -> list[Signal]:
        """Cross-sectional momentum: rank assets, long top, short bottom."""
        top_pct = float(parameters.get("top_pct", 0.2))
        bottom_pct = float(parameters.get("bottom_pct", 0.2))

        # Collect trailing returns for each symbol
        returns_map: dict[str, tuple[float, datetime]] = {}
        for symbol, df in data.items():
            if len(df) < lookback + 1:
                continue
            return_col = f"return_{lookback}d"
            if return_col not in df.columns:
                df = df.with_columns(
                    (pl.col("close") / pl.col("close").shift(lookback) - 1).alias(return_col)
                )
            last_row = df.tail(1)
            ret_val = last_row[return_col].item()
            ts = last_row["timestamp"].item()
            if ret_val is not None:
                if not isinstance(ts, datetime):
                    ts = datetime(ts.year, ts.month, ts.day)
                returns_map[symbol] = (float(ret_val), ts)

        if not returns_map:
            return []

        # Sort by return descending
        sorted_symbols = sorted(returns_map.keys(), key=lambda s: returns_map[s][0], reverse=True)
        n = len(sorted_symbols)
        top_n = max(1, int(n * top_pct))
        bottom_n = max(1, int(n * bottom_pct))

        signals: list[Signal] = []
        for i, symbol in enumerate(sorted_symbols):
            ret_val, ts = returns_map[symbol]
            if i < top_n:
                signals.append(
                    Signal(
                        symbol=symbol,
                        timestamp=ts,
                        direction=SignalDirection.LONG,
                        strength=1.0 - i / top_n,
                        metadata={"rank": float(i), "return": ret_val},
                    )
                )
            elif i >= n - bottom_n:
                signals.append(
                    Signal(
                        symbol=symbol,
                        timestamp=ts,
                        direction=SignalDirection.SHORT,
                        strength=-1.0 + (n - 1 - i) / bottom_n,
                        metadata={"rank": float(i), "return": ret_val},
                    )
                )
            else:
                signals.append(
                    Signal(
                        symbol=symbol,
                        timestamp=ts,
                        direction=SignalDirection.FLAT,
                        strength=0.0,
                        metadata={"rank": float(i), "return": ret_val},
                    )
                )

        return signals

    def get_parameter_schema(self) -> dict[str, dict[str, object]]:
        return {
            "lookback_period": {"type": "int", "default": 20, "min": 5, "max": 252},
            "threshold": {"type": "float", "default": 0.0, "min": 0.0, "max": 0.5},
            "mode": {
                "type": "str",
                "default": "time_series",
                "options": ["time_series", "cross_sectional"],
            },
            "top_pct": {"type": "float", "default": 0.2, "min": 0.05, "max": 0.5},
            "bottom_pct": {"type": "float", "default": 0.2, "min": 0.05, "max": 0.5},
        }
