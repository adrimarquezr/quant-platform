"""
Data Quality Validator — Enforces strict data integrity before any quantitative use.

The pipeline MUST fail explicitly when data is corrupt. No strategy should ever
silently consume bad data. Every validation rule is documented with its rationale.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

import polars as pl

from src.domain.interfaces import IDataQualityValidator
from src.domain.models import DataQualityCheckResult, DataQualityReport, QualityCheckStatus

logger = logging.getLogger(__name__)


class DataQualityValidator(IDataQualityValidator):
    """Validates OHLCV DataFrames against a comprehensive set of quantitative rules.

    Each check outputs a DataQualityCheckResult with PASSED/FAILED/WARNING.
    The overall report is PASSED only if all critical checks pass.
    """

    def __init__(
        self,
        max_gap_days: int = 5,
        max_daily_return_pct: float = 50.0,
        min_rows: int = 10,
        max_zero_volume_pct: float = 5.0,
    ) -> None:
        self.max_gap_days = max_gap_days
        self.max_daily_return_pct = max_daily_return_pct
        self.min_rows = min_rows
        self.max_zero_volume_pct = max_zero_volume_pct

    def validate(self, df: pl.DataFrame, symbol: str) -> list[str]:
        """Backward-compatible validation returning a list of error strings."""
        report = self.validate_dataset(df, symbol)
        return report.errors

    def validate_dataset(
        self,
        df: pl.DataFrame,
        symbol: str,
        dataset_name: str = "daily_ohlcv",
    ) -> DataQualityReport:
        """Run all data quality checks and return a structured DataQualityReport."""
        checks: list[DataQualityCheckResult] = []
        now = datetime.now(UTC)

        if df.is_empty():
            checks.append(
                DataQualityCheckResult(
                    check_name="empty_dataset",
                    status=QualityCheckStatus.FAILED,
                    message=f"[{symbol}] DataFrame is empty — no data to validate",
                )
            )
            return DataQualityReport(
                dataset=dataset_name,
                symbol=symbol,
                status=QualityCheckStatus.FAILED,
                rows_checked=0,
                checks=checks,
                timestamp=now,
            )

        # 1. Schema & Required Columns
        schema_check = self._check_schema(df, symbol)
        checks.append(schema_check)
        if schema_check.status == QualityCheckStatus.FAILED:
            return DataQualityReport(
                dataset=dataset_name,
                symbol=symbol,
                status=QualityCheckStatus.FAILED,
                rows_checked=len(df),
                checks=checks,
                timestamp=now,
            )

        # 2. Minimum Rows
        checks.append(self._check_minimum_rows(df, symbol))

        # 3. Missing / Null Values
        checks.append(self._check_nulls(df, symbol))

        # 4. Duplicate Timestamps
        checks.append(self._check_duplicates(df, symbol))

        # 5. Price Positivity & Non-Zero
        checks.append(self._check_prices(df, symbol))

        # 6. OHLC Logical Consistency
        checks.append(self._check_ohlc_consistency(df, symbol))

        # 7. Timestamp Sorting & Monotonicity
        checks.append(self._check_timestamps(df, symbol))

        # 8. Unexpected Temporal Gaps
        checks.append(self._check_temporal_gaps(df, symbol))

        # 9. Abnormal Return Spikes
        checks.append(self._check_abnormal_returns(df, symbol))

        # 10. Volume Checks
        checks.append(self._check_volume(df, symbol))

        # Determine overall status
        has_failed = any(c.status == QualityCheckStatus.FAILED for c in checks)
        has_warning = any(c.status == QualityCheckStatus.WARNING for c in checks)
        overall_status = (
            QualityCheckStatus.FAILED
            if has_failed
            else (QualityCheckStatus.WARNING if has_warning else QualityCheckStatus.PASSED)
        )

        report = DataQualityReport(
            dataset=dataset_name,
            symbol=symbol,
            status=overall_status,
            rows_checked=len(df),
            checks=checks,
            timestamp=now,
        )

        if has_failed:
            logger.warning(
                "Data quality FAILED for %s: %d errors found", symbol, len(report.errors)
            )
        else:
            logger.info("Data quality PASSED for %s (%d rows)", symbol, len(df))

        return report

    @staticmethod
    def _check_schema(df: pl.DataFrame, symbol: str) -> DataQualityCheckResult:
        """Verify presence and schema of required OHLCV columns."""
        required = {"timestamp", "open", "high", "low", "close", "volume"}
        missing = required - set(df.columns)
        if missing:
            return DataQualityCheckResult(
                check_name="schema",
                status=QualityCheckStatus.FAILED,
                message=f"[{symbol}] Missing required columns: {sorted(missing)}",
                details={"missing_columns": str(sorted(missing))},
            )
        return DataQualityCheckResult(
            check_name="schema",
            status=QualityCheckStatus.PASSED,
            message="Schema and required columns verified",
        )

    def _check_minimum_rows(self, df: pl.DataFrame, symbol: str) -> DataQualityCheckResult:
        """Verify sufficient row count for statistical analysis."""
        row_count = len(df)
        if row_count < self.min_rows:
            return DataQualityCheckResult(
                check_name="minimum_rows",
                status=QualityCheckStatus.FAILED,
                message=f"[{symbol}] Only {row_count} rows — minimum {self.min_rows} required",
                details={"row_count": row_count, "min_required": self.min_rows},
            )
        return DataQualityCheckResult(
            check_name="minimum_rows",
            status=QualityCheckStatus.PASSED,
            message=f"Row count ({row_count}) satisfies minimum threshold",
            details={"row_count": row_count},
        )

    @staticmethod
    def _check_nulls(df: pl.DataFrame, symbol: str) -> DataQualityCheckResult:
        """Detect null / NaN / None values in price and timestamp columns."""
        checked_cols = ["timestamp", "open", "high", "low", "close", "volume"]
        null_counts = {col: df[col].null_count() for col in checked_cols if col in df.columns}
        total_nulls = sum(null_counts.values())

        if total_nulls > 0:
            details = {col: count for col, count in null_counts.items() if count > 0}
            return DataQualityCheckResult(
                check_name="nulls",
                status=QualityCheckStatus.FAILED,
                message=f"[{symbol}] Found {total_nulls} null values in columns: {details}",
                details={"total_nulls": total_nulls, **details},
            )
        return DataQualityCheckResult(
            check_name="nulls",
            status=QualityCheckStatus.PASSED,
            message="No null or NaN values detected",
        )

    @staticmethod
    def _check_duplicates(df: pl.DataFrame, symbol: str) -> DataQualityCheckResult:
        """Ensure all timestamps are unique."""
        dup_count = len(df) - df["timestamp"].n_unique()
        if dup_count > 0:
            return DataQualityCheckResult(
                check_name="duplicates",
                status=QualityCheckStatus.FAILED,
                message=f"[{symbol}] Found {dup_count} duplicate timestamps",
                details={"duplicate_count": dup_count},
            )
        return DataQualityCheckResult(
            check_name="duplicates",
            status=QualityCheckStatus.PASSED,
            message="All timestamps are unique",
        )

    @staticmethod
    def _check_prices(df: pl.DataFrame, symbol: str) -> DataQualityCheckResult:
        """Prices must be strictly positive (open, high, low, close > 0)."""
        price_cols = ["open", "high", "low", "close"]
        invalid_rows = 0
        details: dict[str, int] = {}

        for col in price_cols:
            count_non_pos = df.filter((pl.col(col) <= 0) | pl.col(col).is_null()).height
            if count_non_pos > 0:
                details[f"non_positive_{col}"] = count_non_pos
                invalid_rows += count_non_pos

        if invalid_rows > 0:
            return DataQualityCheckResult(
                check_name="prices",
                status=QualityCheckStatus.FAILED,
                message=f"[{symbol}] Detected non-positive (zero or negative) prices: {details}",
                details=details,
            )
        return DataQualityCheckResult(
            check_name="prices",
            status=QualityCheckStatus.PASSED,
            message="All price values are strictly positive",
        )

    @staticmethod
    def _check_ohlc_consistency(df: pl.DataFrame, symbol: str) -> DataQualityCheckResult:
        """Enforce strict OHLC inequalities:
        low <= open, low <= close, high >= open, high >= close, low <= high.
        """
        violations_high_low = df.filter(pl.col("high") < pl.col("low")).height
        violations_high_open_close = df.filter(
            (pl.col("high") < pl.col("open")) | (pl.col("high") < pl.col("close"))
        ).height
        violations_low_open_close = df.filter(
            (pl.col("low") > pl.col("open")) | (pl.col("low") > pl.col("close"))
        ).height

        total_violations = (
            violations_high_low + violations_high_open_close + violations_low_open_close
        )
        if total_violations > 0:
            details = {
                "high_less_than_low": violations_high_low,
                "high_below_open_or_close": violations_high_open_close,
                "low_above_open_or_close": violations_low_open_close,
            }
            return DataQualityCheckResult(
                check_name="ohlc",
                status=QualityCheckStatus.FAILED,
                message=f"[{symbol}] {total_violations} OHLC inequality violations found: {details}",
                details=details,
            )
        return DataQualityCheckResult(
            check_name="ohlc",
            status=QualityCheckStatus.PASSED,
            message="OHLC price relationships (high >= open/close/low, low <= open/close/high) are valid",
        )

    @staticmethod
    def _check_timestamps(df: pl.DataFrame, symbol: str) -> DataQualityCheckResult:
        """Verify timestamps are strictly ascending."""
        if not df["timestamp"].is_sorted():
            return DataQualityCheckResult(
                check_name="timestamps",
                status=QualityCheckStatus.FAILED,
                message=f"[{symbol}] Timestamps are not sorted in ascending order",
            )
        return DataQualityCheckResult(
            check_name="timestamps",
            status=QualityCheckStatus.PASSED,
            message="Timestamps are strictly sorted ascending",
        )

    def _check_temporal_gaps(self, df: pl.DataFrame, symbol: str) -> DataQualityCheckResult:
        """Detect unexpectedly large calendar day gaps in historical data."""
        if len(df) < 2:
            return DataQualityCheckResult(
                check_name="gaps",
                status=QualityCheckStatus.PASSED,
                message="Dataset has fewer than 2 rows; gap check skipped",
            )

        diffs = (
            df.sort("timestamp")
            .with_columns((pl.col("timestamp").diff().dt.total_days()).alias("day_diff"))
            .filter(pl.col("day_diff") > self.max_gap_days)
        )

        if len(diffs) > 0:
            gap_count = len(diffs)
            max_gap = float(str(diffs["day_diff"].max() or 0))
            return DataQualityCheckResult(
                check_name="gaps",
                status=QualityCheckStatus.WARNING,
                message=f"[{symbol}] {gap_count} temporal gaps > {self.max_gap_days} days (max gap: {max_gap:.0f} days)",
                details={"gap_count": gap_count, "max_gap_days": max_gap},
            )
        return DataQualityCheckResult(
            check_name="gaps",
            status=QualityCheckStatus.PASSED,
            message=f"No temporal gaps exceeding {self.max_gap_days} days detected",
        )

    def _check_abnormal_returns(self, df: pl.DataFrame, symbol: str) -> DataQualityCheckResult:
        """Flag suspicious single-day price return outliers."""
        if len(df) < 2:
            return DataQualityCheckResult(
                check_name="abnormal_returns",
                status=QualityCheckStatus.PASSED,
                message="Single row dataset; abnormal return check skipped",
            )

        returns = df.sort("timestamp").with_columns(
            (pl.col("close").pct_change() * 100).alias("daily_return_pct")
        )
        extreme = returns.filter(pl.col("daily_return_pct").abs() > self.max_daily_return_pct)

        if len(extreme) > 0:
            count = len(extreme)
            max_return = float(str(extreme["daily_return_pct"].abs().max() or 0))
            return DataQualityCheckResult(
                check_name="abnormal_returns",
                status=QualityCheckStatus.WARNING,
                message=f"[{symbol}] {count} days with |return| > {self.max_daily_return_pct}% (max: {max_return:.1f}%)",
                details={"outlier_count": count, "max_daily_return_pct": max_return},
            )
        return DataQualityCheckResult(
            check_name="abnormal_returns",
            status=QualityCheckStatus.PASSED,
            message=f"Daily price changes are within +/-{self.max_daily_return_pct}%",
        )

    def _check_volume(self, df: pl.DataFrame, symbol: str) -> DataQualityCheckResult:
        """Verify volume is non-negative and not excessively zero."""
        negative_vol = df.filter(pl.col("volume") < 0).height
        if negative_vol > 0:
            return DataQualityCheckResult(
                check_name="volume",
                status=QualityCheckStatus.FAILED,
                message=f"[{symbol}] {negative_vol} rows with negative volume",
                details={"negative_volume_rows": negative_vol},
            )

        zero_vol = df.filter(pl.col("volume") == 0).height
        if zero_vol > 0:
            pct = (zero_vol / len(df)) * 100
            if pct > self.max_zero_volume_pct:
                return DataQualityCheckResult(
                    check_name="volume",
                    status=QualityCheckStatus.WARNING,
                    message=f"[{symbol}] {zero_vol} rows ({pct:.1f}%) with zero volume (exceeds {self.max_zero_volume_pct}%)",
                    details={"zero_volume_rows": zero_vol, "zero_volume_pct": pct},
                )

        return DataQualityCheckResult(
            check_name="volume",
            status=QualityCheckStatus.PASSED,
            message="Volume is non-negative and activity levels are healthy",
        )
