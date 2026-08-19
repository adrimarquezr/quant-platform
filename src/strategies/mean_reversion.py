"""
Mean Reversion Strategy — Z-Score based mean reversion.

Core idea: prices tend to revert to a rolling mean. When the z-score
(deviations from rolling mean in units of rolling std) exceeds a threshold,
bet on reversion.

    Long when z-score < -entry_threshold  (price is "too low")
    Short when z-score > +entry_threshold (price is "too high")
    Flat when abs(z-score) < exit_threshold (price reverted close to mean)

Reference: Avellaneda & Lee (2010), "Statistical Arbitrage in the US Equities Market"
"""

from __future__ import annotations

import math
from datetime import datetime

import polars as pl

from src.domain.interfaces import IStrategy
from src.domain.models import Signal, SignalDirection


class MeanReversionStrategy(IStrategy):
    """Z-score based mean reversion strategy with robust edge case handling."""

    @property
    def name(self) -> str:
        return "mean_reversion"

    @property
    def version(self) -> str:
        return "1.0.0"

    def generate_signals(
        self,
        data: dict[str, pl.DataFrame],
        parameters: dict[str, float | int | str | bool],
    ) -> list[Signal]:
        """Generate mean reversion signals based on z-score thresholds.

        Parameters:
            lookback_period: Rolling window for mean/std calculation (default: 20).
            entry_threshold: Z-score threshold to enter a position (default: 2.0).
            exit_threshold: Z-score threshold to exit a position (default: 0.5).
        """
        lookback = max(2, int(parameters.get("lookback_period", 20)))
        entry_threshold = float(parameters.get("entry_threshold", 2.0))
        exit_threshold = float(parameters.get("exit_threshold", 0.5))

        signals: list[Signal] = []

        for symbol, df in data.items():
            if df.is_empty() or len(df) < lookback:
                continue

            # Compute rolling mean and std
            rolling_mean_col = pl.col("close").rolling_mean(lookback)
            rolling_std_col = pl.col("close").rolling_std(lookback)

            z_col = f"z_score_{lookback}d"
            if z_col not in df.columns:
                df = df.with_columns(
                    pl.when(rolling_std_col > 1e-8)
                    .then((pl.col("close") - rolling_mean_col) / rolling_std_col)
                    .otherwise(0.0)
                    .alias(z_col)
                )

            # Get the most recent z-score
            last_row = df.tail(1)
            z_value = last_row[z_col].item()
            timestamp = last_row["timestamp"].item()

            if z_value is None or math.isnan(z_value) or math.isinf(z_value):
                z_value = 0.0

            if not isinstance(timestamp, datetime):
                timestamp = datetime(timestamp.year, timestamp.month, timestamp.day)

            # Signal logic: mean reversion
            if z_value < -entry_threshold:
                # Price is significantly below mean → expect upward reversion → LONG
                direction = SignalDirection.LONG
                strength = min(abs(z_value) / (entry_threshold * 2), 1.0)
            elif z_value > entry_threshold:
                # Price is significantly above mean → expect downward reversion → SHORT
                direction = SignalDirection.SHORT
                strength = -min(abs(z_value) / (entry_threshold * 2), 1.0)
            elif abs(z_value) < exit_threshold:
                # Price reverted close to mean → go FLAT
                direction = SignalDirection.FLAT
                strength = 0.0
            else:
                # Between exit and entry thresholds — hold / flat
                direction = SignalDirection.FLAT
                strength = 0.0

            signals.append(
                Signal(
                    symbol=symbol,
                    timestamp=timestamp,
                    direction=direction,
                    strength=max(-1.0, min(1.0, strength)),
                    metadata={
                        "z_score": float(z_value),
                        "lookback": float(lookback),
                        "entry_threshold": entry_threshold,
                        "exit_threshold": exit_threshold,
                    },
                )
            )

        return signals

    def get_parameter_schema(self) -> dict[str, dict[str, object]]:
        return {
            "lookback_period": {"type": "int", "default": 20, "min": 5, "max": 252},
            "entry_threshold": {"type": "float", "default": 2.0, "min": 0.5, "max": 4.0},
            "exit_threshold": {"type": "float", "default": 0.5, "min": 0.0, "max": 2.0},
        }
