"""
Tests for Data Quality Validator — verifies all validation rules detect issues.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import polars as pl
import pytest

from src.application.data_quality import DataQualityValidator
from src.domain.models import QualityCheckStatus


@pytest.mark.unit
class TestDataQualityValidator:
    """Test that the validator catches all data quality issues."""

    def setup_method(self) -> None:
        self.validator = DataQualityValidator()

    def test_valid_data_passes(self, sample_ohlcv_df: pl.DataFrame) -> None:
        """Clean data should produce zero errors and PASSED status."""
        report = self.validator.validate_dataset(sample_ohlcv_df, "TEST")
        assert report.is_valid
        assert report.status == QualityCheckStatus.PASSED
        assert report.errors == []
        assert report.rows_checked == len(sample_ohlcv_df)
        assert "schema" in report.check_summary

    def test_empty_dataframe_fails(self) -> None:
        """Empty DataFrame must be rejected."""
        df = pl.DataFrame(
            {"timestamp": [], "open": [], "high": [], "low": [], "close": [], "volume": []}
        )
        report = self.validator.validate_dataset(df, "TEST")
        assert not report.is_valid
        assert report.status == QualityCheckStatus.FAILED
        assert any("empty" in e.lower() for e in report.errors)

    def test_missing_columns_detected(self) -> None:
        """Missing required columns must be caught."""
        df = pl.DataFrame({"timestamp": [1, 2], "open": [100, 101]})
        report = self.validator.validate_dataset(df, "TEST")
        assert not report.is_valid
        assert any("missing" in e.lower() for e in report.errors)

    def test_null_prices_detected(self, corrupt_ohlcv_df: pl.DataFrame) -> None:
        """Null values in price columns must be flagged."""
        report = self.validator.validate_dataset(corrupt_ohlcv_df, "TEST")
        assert not report.is_valid
        assert any("null" in e.lower() for e in report.errors)

    def test_negative_prices_detected(self, corrupt_ohlcv_df: pl.DataFrame) -> None:
        """Negative prices must be flagged."""
        report = self.validator.validate_dataset(corrupt_ohlcv_df, "TEST")
        assert not report.is_valid
        assert any("non-positive" in e.lower() or "negative" in e.lower() for e in report.errors)

    def test_duplicate_timestamps_detected(self, corrupt_ohlcv_df: pl.DataFrame) -> None:
        """Duplicate timestamps must be flagged."""
        report = self.validator.validate_dataset(corrupt_ohlcv_df, "TEST")
        assert not report.is_valid
        assert any("duplicate" in e.lower() for e in report.errors)

    def test_ohlc_consistency_detected(self, corrupt_ohlcv_df: pl.DataFrame) -> None:
        """OHLC violations (e.g., high < low) must be flagged."""
        report = self.validator.validate_dataset(corrupt_ohlcv_df, "TEST")
        assert not report.is_valid
        assert any("ohlc" in e.lower() for e in report.errors)

    def test_minimum_rows_enforced(self) -> None:
        """Too few rows must be rejected."""
        df = pl.DataFrame(
            {
                "timestamp": [datetime(2023, 1, i) for i in range(1, 4)],
                "open": [100.0, 101.0, 102.0],
                "high": [102.0, 103.0, 104.0],
                "low": [99.0, 100.0, 101.0],
                "close": [101.0, 102.0, 103.0],
                "volume": [1e6, 1e6, 1e6],
            }
        )
        validator = DataQualityValidator(min_rows=10)
        report = validator.validate_dataset(df, "TEST")
        assert not report.is_valid
        assert any("minimum" in e.lower() or "only" in e.lower() for e in report.errors)

    def test_unsorted_timestamps_detected(self) -> None:
        """Timestamps that are not sorted ascending must fail."""
        df = pl.DataFrame(
            {
                "timestamp": [
                    datetime(2023, 1, 3),
                    datetime(2023, 1, 1),
                    datetime(2023, 1, 2),
                    datetime(2023, 1, 4),
                    datetime(2023, 1, 5),
                    datetime(2023, 1, 6),
                    datetime(2023, 1, 7),
                    datetime(2023, 1, 8),
                    datetime(2023, 1, 9),
                    datetime(2023, 1, 10),
                ],
                "open": [100.0] * 10,
                "high": [105.0] * 10,
                "low": [95.0] * 10,
                "close": [102.0] * 10,
                "volume": [1000.0] * 10,
            }
        )
        report = self.validator.validate_dataset(df, "TEST")
        assert not report.is_valid
        assert any("sorted" in e.lower() for e in report.errors)

    def test_negative_volume_detected(self) -> None:
        """Negative trading volume must fail."""
        dates = [datetime(2023, 1, 1) + timedelta(days=i) for i in range(12)]
        df = pl.DataFrame(
            {
                "timestamp": dates,
                "open": [100.0] * 12,
                "high": [105.0] * 12,
                "low": [95.0] * 12,
                "close": [102.0] * 12,
                "volume": [1000.0] * 11 + [-50.0],
            }
        )
        report = self.validator.validate_dataset(df, "TEST")
        assert not report.is_valid
        assert any("volume" in e.lower() for e in report.errors)

    def test_temporal_gap_warning(self) -> None:
        """Temporal gaps exceeding max_gap_days should trigger a WARNING."""
        dates = [datetime(2023, 1, 1) + timedelta(days=i) for i in range(5)] + [
            datetime(2023, 1, 20) + timedelta(days=i) for i in range(6)
        ]
        df = pl.DataFrame(
            {
                "timestamp": dates,
                "open": [100.0] * 11,
                "high": [105.0] * 11,
                "low": [95.0] * 11,
                "close": [102.0] * 11,
                "volume": [1000.0] * 11,
            }
        )
        validator = DataQualityValidator(max_gap_days=5)
        report = validator.validate_dataset(df, "TEST")
        assert report.status == QualityCheckStatus.WARNING
        assert any(
            c.check_name == "gaps" and c.status == QualityCheckStatus.WARNING for c in report.checks
        )
