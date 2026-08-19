"""
Tests for Data Quality Validator — verifies all validation rules detect issues.
"""

from __future__ import annotations

import polars as pl
import pytest

from src.application.data_quality import DataQualityValidator


@pytest.mark.unit
class TestDataQualityValidator:
    """Test that the validator catches all data quality issues."""

    def setup_method(self) -> None:
        self.validator = DataQualityValidator()

    def test_valid_data_passes(self, sample_ohlcv_df: pl.DataFrame) -> None:
        """Clean data should produce zero errors."""
        errors = self.validator.validate(sample_ohlcv_df, "TEST")
        assert errors == [], f"Expected no errors, got: {errors}"

    def test_empty_dataframe_fails(self) -> None:
        """Empty DataFrame must be rejected."""
        df = pl.DataFrame(
            {"timestamp": [], "open": [], "high": [], "low": [], "close": [], "volume": []}
        )
        errors = self.validator.validate(df, "TEST")
        assert len(errors) > 0
        assert any("empty" in e.lower() for e in errors)

    def test_missing_columns_detected(self) -> None:
        """Missing required columns must be caught."""
        df = pl.DataFrame({"timestamp": [1, 2], "open": [100, 101]})
        errors = self.validator.validate(df, "TEST")
        assert len(errors) > 0
        assert any("missing" in e.lower() for e in errors)

    def test_null_prices_detected(self, corrupt_ohlcv_df: pl.DataFrame) -> None:
        """Null values in price columns must be flagged."""
        errors = self.validator.validate(corrupt_ohlcv_df, "TEST")
        assert any("null" in e.lower() for e in errors)

    def test_negative_prices_detected(self, corrupt_ohlcv_df: pl.DataFrame) -> None:
        """Negative prices must be flagged."""
        errors = self.validator.validate(corrupt_ohlcv_df, "TEST")
        assert any("negative" in e.lower() for e in errors)

    def test_duplicate_timestamps_detected(self, corrupt_ohlcv_df: pl.DataFrame) -> None:
        """Duplicate timestamps must be flagged."""
        errors = self.validator.validate(corrupt_ohlcv_df, "TEST")
        assert any("duplicate" in e.lower() for e in errors)

    def test_ohlc_consistency_detected(self, corrupt_ohlcv_df: pl.DataFrame) -> None:
        """OHLC violations (e.g., high < low) must be flagged."""
        errors = self.validator.validate(corrupt_ohlcv_df, "TEST")
        assert any("high" in e.lower() and "low" in e.lower() for e in errors)

    def test_minimum_rows_enforced(self) -> None:
        """Too few rows must be rejected."""
        from datetime import datetime

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
        errors = validator.validate(df, "TEST")
        assert any("minimum" in e.lower() or "only" in e.lower() for e in errors)
