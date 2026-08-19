"""
Shared test fixtures for the Quant Platform test suite.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import polars as pl
import pytest

# Ensure src and apps are importable
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def sample_ohlcv_df() -> pl.DataFrame:
    """Generate a realistic sample OHLCV DataFrame for testing.

    50 trading days of synthetic data with realistic price movements.
    """
    import numpy as np

    np.random.seed(42)  # Deterministic

    n_days = 50
    base_price = 100.0
    returns = np.random.normal(0.0005, 0.015, n_days)

    closes = [base_price]
    for r in returns[1:]:
        closes.append(closes[-1] * (1 + r))

    dates = pl.date_range(datetime(2023, 1, 2), datetime(2023, 3, 14), "1d", eager=True)[:n_days]

    timestamps = [datetime(d.year, d.month, d.day) for d in dates]

    opens = [c * (1 + np.random.uniform(-0.005, 0.005)) for c in closes]
    highs = [max(o, c) * (1 + abs(np.random.normal(0, 0.008))) for o, c in zip(opens, closes)]
    lows = [min(o, c) * (1 - abs(np.random.normal(0, 0.008))) for o, c in zip(opens, closes)]
    volumes = [np.random.uniform(1e6, 5e6) for _ in range(n_days)]

    return pl.DataFrame(
        {
            "timestamp": timestamps,
            "open": opens,
            "high": highs,
            "low": lows,
            "close": closes,
            "volume": volumes,
            "adjusted_close": closes,
        }
    ).cast(
        {
            "open": pl.Float64,
            "high": pl.Float64,
            "low": pl.Float64,
            "close": pl.Float64,
            "volume": pl.Float64,
            "adjusted_close": pl.Float64,
        }
    )


@pytest.fixture
def sample_multi_symbol_data(sample_ohlcv_df: pl.DataFrame) -> dict[str, pl.DataFrame]:
    """Multiple symbols with the same date range (different prices)."""
    import numpy as np

    np.random.seed(123)
    spy = sample_ohlcv_df.clone()

    # Create QQQ with different returns
    qqq = spy.with_columns(
        (pl.col("close") * 1.5 + pl.Series(np.random.normal(0, 2, len(spy)))).alias("close"),
    )
    qqq = qqq.with_columns(
        pl.col("close").alias("adjusted_close"),
        (pl.col("close") * 1.01).alias("high"),
        (pl.col("close") * 0.99).alias("low"),
        pl.col("close").alias("open"),
    )

    return {"SPY": spy, "QQQ": qqq}


@pytest.fixture
def corrupt_ohlcv_df() -> pl.DataFrame:
    """OHLCV DataFrame with intentional quality issues for validation testing."""
    return pl.DataFrame(
        {
            "timestamp": [
                datetime(2023, 1, 2),
                datetime(2023, 1, 3),
                datetime(2023, 1, 3),  # Duplicate
                datetime(2023, 1, 4),
                datetime(2023, 1, 5),
            ],
            "open": [100.0, 101.0, 101.0, -5.0, 103.0],  # Negative price
            "high": [102.0, 99.0, 103.0, 104.0, 105.0],  # high < low
            "low": [99.0, 100.0, 100.0, 101.0, 102.0],
            "close": [101.0, None, 102.0, 103.0, 104.0],  # Null
            "volume": [1e6, 1e6, 1e6, 1e6, 0.0],
        }
    )
