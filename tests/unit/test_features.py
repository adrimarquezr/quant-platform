"""
Tests for the Feature Engine — verifies correctness and no look-ahead bias.
"""

from __future__ import annotations

import polars as pl
import pytest

from src.features.engine import (
    add_momentum_features,
    add_risk_features,
    add_statistical_features,
    add_trend_features,
    add_volatility_features,
    compute_all_features,
)


@pytest.mark.unit
class TestMomentumFeatures:
    """Test momentum feature calculations."""

    def test_return_columns_created(self, sample_ohlcv_df: pl.DataFrame) -> None:
        """Verify return columns are added for each period."""
        df = add_momentum_features(sample_ohlcv_df, periods=[1, 5, 20])
        assert "return_1d" in df.columns
        assert "return_5d" in df.columns
        assert "return_20d" in df.columns
        assert "log_return_1d" in df.columns

    def test_1d_return_calculation(self, sample_ohlcv_df: pl.DataFrame) -> None:
        """Verify 1-day return = (close_t / close_{t-1}) - 1."""
        df = add_momentum_features(sample_ohlcv_df, periods=[1])
        # Row 1 should have return = close[1]/close[0] - 1
        close_0 = df["close"][0]
        close_1 = df["close"][1]
        expected = close_1 / close_0 - 1
        actual = df["return_1d"][1]
        assert abs(actual - expected) < 1e-10

    def test_first_row_is_null(self, sample_ohlcv_df: pl.DataFrame) -> None:
        """First row of return_1d should be null (no previous bar)."""
        df = add_momentum_features(sample_ohlcv_df, periods=[1])
        assert df["return_1d"][0] is None

    def test_no_look_ahead_in_returns(self, sample_ohlcv_df: pl.DataFrame) -> None:
        """Returns at row t must only depend on data up to row t."""
        df = add_momentum_features(sample_ohlcv_df, periods=[5])
        # return_5d at index 10 should only use close[5] and close[10]
        close_5 = df["close"][5]
        close_10 = df["close"][10]
        expected = close_10 / close_5 - 1
        actual = df["return_5d"][10]
        assert abs(actual - expected) < 1e-10


@pytest.mark.unit
class TestVolatilityFeatures:
    """Test volatility feature calculations."""

    def test_volatility_columns_created(self, sample_ohlcv_df: pl.DataFrame) -> None:
        df = add_volatility_features(sample_ohlcv_df, windows=[20])
        assert "volatility_20d" in df.columns
        assert "atr_20d" in df.columns
        assert "true_range" in df.columns

    def test_volatility_is_positive(self, sample_ohlcv_df: pl.DataFrame) -> None:
        """Volatility should be non-negative where computed."""
        df = add_volatility_features(sample_ohlcv_df, windows=[20])
        non_null = df.filter(pl.col("volatility_20d").is_not_null())
        assert (non_null["volatility_20d"] >= 0).all()

    def test_true_range_formula(self, sample_ohlcv_df: pl.DataFrame) -> None:
        """True Range = max(H-L, |H-prev_C|, |L-prev_C|)."""
        df = add_volatility_features(sample_ohlcv_df, windows=[20])
        # Check row 5
        h = df["high"][5]
        low = df["low"][5]
        prev_c = df["close"][4]
        expected_tr = max(h - low, abs(h - prev_c), abs(low - prev_c))
        actual_tr = df["true_range"][5]
        assert abs(actual_tr - expected_tr) < 1e-8


@pytest.mark.unit
class TestTrendFeatures:
    """Test trend feature calculations."""

    def test_sma_columns_created(self, sample_ohlcv_df: pl.DataFrame) -> None:
        df = add_trend_features(sample_ohlcv_df, sma_periods=[20], ema_periods=[12])
        assert "sma_20" in df.columns
        assert "price_sma_20_ratio" in df.columns
        assert "ema_12" in df.columns

    def test_sma_value(self, sample_ohlcv_df: pl.DataFrame) -> None:
        """SMA(20) at row 19 should equal mean of close[0:20]."""
        df = add_trend_features(sample_ohlcv_df, sma_periods=[20], ema_periods=[])
        expected_sma = sum(df["close"][i] for i in range(20)) / 20
        actual_sma = df["sma_20"][19]
        assert abs(actual_sma - expected_sma) < 1e-8


@pytest.mark.unit
class TestStatisticalFeatures:
    """Test statistical feature calculations."""

    def test_z_score_column_created(self, sample_ohlcv_df: pl.DataFrame) -> None:
        df = add_statistical_features(sample_ohlcv_df, z_score_window=20)
        assert "z_score_20d" in df.columns
        assert "percentile_rank_252d" in df.columns

    def test_z_score_range(self, sample_ohlcv_df: pl.DataFrame) -> None:
        """Z-scores should typically be in [-4, 4] for normal data."""
        df = add_statistical_features(sample_ohlcv_df, z_score_window=20)
        non_null = df.filter(pl.col("z_score_20d").is_not_null())
        assert (non_null["z_score_20d"].abs() < 10).all()


@pytest.mark.unit
class TestRiskFeatures:
    """Test risk feature calculations."""

    def test_drawdown_columns_created(self, sample_ohlcv_df: pl.DataFrame) -> None:
        df = add_risk_features(sample_ohlcv_df)
        assert "drawdown" in df.columns
        assert "rolling_high" in df.columns

    def test_drawdown_is_non_positive(self, sample_ohlcv_df: pl.DataFrame) -> None:
        """Drawdown should always be <= 0."""
        df = add_risk_features(sample_ohlcv_df)
        non_null = df.filter(pl.col("drawdown").is_not_null())
        assert (non_null["drawdown"] <= 0.0001).all()  # Small epsilon for float


@pytest.mark.unit
class TestComputeAllFeatures:
    """Test the convenience all-features function."""

    def test_all_feature_groups_present(self, sample_ohlcv_df: pl.DataFrame) -> None:
        """Verify all feature groups are computed."""
        df = compute_all_features(sample_ohlcv_df)
        assert "return_1d" in df.columns  # Momentum
        assert "volatility_20d" in df.columns  # Volatility
        assert "sma_20" in df.columns  # Trend
        assert "z_score_20d" in df.columns  # Statistical
        assert "drawdown" in df.columns  # Risk

    def test_row_count_preserved(self, sample_ohlcv_df: pl.DataFrame) -> None:
        """Feature computation should not change the number of rows."""
        df = compute_all_features(sample_ohlcv_df)
        assert len(df) == len(sample_ohlcv_df)
