"""
Data Quality Validator — Enforces strict data integrity before any quantitative use.

The pipeline MUST fail explicitly when data is corrupt. No strategy should ever
silently consume bad data. Every validation rule is documented with its rationale.
"""

from __future__ import annotations

import logging

import polars as pl

from src.domain.interfaces import IDataQualityValidator

logger = logging.getLogger(__name__)


class DataQualityValidator(IDataQualityValidator):
    """Validates OHLCV DataFrames against a comprehensive set of rules.

    Each rule returns error messages. An empty list means the data passed validation.
    The pipeline should abort if any errors are returned.
    """

    def __init__(
        self,
        max_gap_days: int = 5,
        max_daily_return_pct: float = 50.0,
        min_rows: int = 10,
    ) -> None:
        self.max_gap_days = max_gap_days
        self.max_daily_return_pct = max_daily_return_pct
        self.min_rows = min_rows

    def validate(self, df: pl.DataFrame, symbol: str) -> list[str]:
        """Run all validation rules and return accumulated errors."""
        errors: list[str] = []

        if df.is_empty():
            errors.append(f"[{symbol}] DataFrame is empty — no data to validate")
            return errors

        errors.extend(self._check_required_columns(df, symbol))
        if errors:
            return errors  # Can't continue without required columns

        errors.extend(self._check_minimum_rows(df, symbol))
        errors.extend(self._check_null_prices(df, symbol))
        errors.extend(self._check_negative_prices(df, symbol))
        errors.extend(self._check_ohlc_consistency(df, symbol))
        errors.extend(self._check_duplicate_timestamps(df, symbol))
        errors.extend(self._check_temporal_gaps(df, symbol))
        errors.extend(self._check_abnormal_returns(df, symbol))
        errors.extend(self._check_zero_volume(df, symbol))
        errors.extend(self._check_sorted_timestamps(df, symbol))

        if errors:
            logger.warning("Data quality issues for %s: %d errors found", symbol, len(errors))
        else:
            logger.info("Data quality validation passed for %s (%d rows)", symbol, len(df))

        return errors

    @staticmethod
    def _check_required_columns(df: pl.DataFrame, symbol: str) -> list[str]:
        """Verify all required OHLCV columns exist."""
        required = {"timestamp", "open", "high", "low", "close", "volume"}
        missing = required - set(df.columns)
        if missing:
            return [f"[{symbol}] Missing required columns: {sorted(missing)}"]
        return []

    def _check_minimum_rows(self, df: pl.DataFrame, symbol: str) -> list[str]:
        """Ensure minimum data points for meaningful analysis."""
        if len(df) < self.min_rows:
            return [f"[{symbol}] Only {len(df)} rows — minimum {self.min_rows} required"]
        return []

    @staticmethod
    def _check_null_prices(df: pl.DataFrame, symbol: str) -> list[str]:
        """Detect null/NaN values in price columns."""
        errors: list[str] = []
        price_cols = ["open", "high", "low", "close"]
        for col in price_cols:
            null_count = df[col].null_count()
            if null_count > 0:
                errors.append(f"[{symbol}] Column '{col}' has {null_count} null values")
        return errors

    @staticmethod
    def _check_negative_prices(df: pl.DataFrame, symbol: str) -> list[str]:
        """Prices must never be negative."""
        errors: list[str] = []
        price_cols = ["open", "high", "low", "close"]
        for col in price_cols:
            neg_count = df.filter(pl.col(col) < 0).height
            if neg_count > 0:
                errors.append(f"[{symbol}] Column '{col}' has {neg_count} negative values")
        return errors

    @staticmethod
    def _check_ohlc_consistency(df: pl.DataFrame, symbol: str) -> list[str]:
        """OHLC consistency: high >= low, high >= open, high >= close, etc."""
        errors: list[str] = []

        # High must be >= Low
        violations = df.filter(pl.col("high") < pl.col("low")).height
        if violations > 0:
            errors.append(f"[{symbol}] {violations} rows where high < low")

        # High must be >= Open and >= Close
        violations = df.filter(
            (pl.col("high") < pl.col("open")) | (pl.col("high") < pl.col("close"))
        ).height
        if violations > 0:
            errors.append(f"[{symbol}] {violations} rows where high < open or high < close")

        # Low must be <= Open and <= Close
        violations = df.filter(
            (pl.col("low") > pl.col("open")) | (pl.col("low") > pl.col("close"))
        ).height
        if violations > 0:
            errors.append(f"[{symbol}] {violations} rows where low > open or low > close")

        return errors

    @staticmethod
    def _check_duplicate_timestamps(df: pl.DataFrame, symbol: str) -> list[str]:
        """No duplicate timestamps allowed."""
        dup_count = len(df) - df["timestamp"].n_unique()
        if dup_count > 0:
            return [f"[{symbol}] {dup_count} duplicate timestamps found"]
        return []

    def _check_temporal_gaps(self, df: pl.DataFrame, symbol: str) -> list[str]:
        """Detect unexpectedly large gaps in the time series (excluding weekends)."""
        errors: list[str] = []
        if len(df) < 2:
            return errors

        timestamps = df.sort("timestamp")["timestamp"]
        # Calculate day differences
        diffs = (
            df.sort("timestamp")
            .with_columns((pl.col("timestamp").diff().dt.total_days()).alias("day_diff"))
            .filter(pl.col("day_diff") > self.max_gap_days)
        )

        if len(diffs) > 0:
            gap_count = len(diffs)
            max_gap = diffs["day_diff"].max()
            errors.append(
                f"[{symbol}] {gap_count} temporal gaps > {self.max_gap_days} days "
                f"(max gap: {max_gap} days)"
            )

        return errors

    def _check_abnormal_returns(self, df: pl.DataFrame, symbol: str) -> list[str]:
        """Flag suspiciously large single-day returns."""
        errors: list[str] = []

        returns = df.sort("timestamp").with_columns(
            (pl.col("close").pct_change() * 100).alias("daily_return_pct")
        )

        extreme = returns.filter(pl.col("daily_return_pct").abs() > self.max_daily_return_pct)

        if len(extreme) > 0:
            errors.append(
                f"[{symbol}] {len(extreme)} days with |return| > {self.max_daily_return_pct}% "
                f"— verify these are not data errors"
            )

        return errors

    @staticmethod
    def _check_zero_volume(df: pl.DataFrame, symbol: str) -> list[str]:
        """Warn about zero-volume days (potential stale data)."""
        zero_vol = df.filter(pl.col("volume") == 0).height
        if zero_vol > 0:
            pct = zero_vol / len(df) * 100
            if pct > 5.0:  # Only flag if > 5% of data
                return [
                    f"[{symbol}] {zero_vol} rows ({pct:.1f}%) with zero volume "
                    f"— potential stale data"
                ]
        return []

    @staticmethod
    def _check_sorted_timestamps(df: pl.DataFrame, symbol: str) -> list[str]:
        """Data must be sorted by timestamp ascending."""
        if not df["timestamp"].is_sorted():
            return [f"[{symbol}] Timestamps are not sorted ascending"]
        return []
