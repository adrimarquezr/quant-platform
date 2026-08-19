"""
Feature Engine — Vectorized feature computation using Polars.

All features are computed using strictly backward-looking windows to prevent
look-ahead bias. Functions are pure (no side effects, no state) and operate
on Polars expressions for maximum performance.

Feature categories:
    - Momentum: Returns over various horizons
    - Volatility: Rolling vol, ATR, realized vol
    - Trend: SMA, EMA, price/SMA ratios, crossovers
    - Statistical: Z-scores, percentile ranks, rolling stats
    - Risk: Drawdown, beta, rolling correlation
"""

from __future__ import annotations

import polars as pl

# ==============================================================================
# Momentum Features
# ==============================================================================


def add_momentum_features(
    df: pl.DataFrame,
    periods: list[int] | None = None,
) -> pl.DataFrame:
    """Add log and simple return features over multiple horizons.

    All returns are backward-looking: return_Nd at time t uses data from [t-N, t].
    """
    if periods is None:
        periods = [1, 5, 20, 60, 120, 252]

    exprs: list[pl.Expr] = []
    for p in periods:
        # Simple return: (close_t / close_{t-p}) - 1
        exprs.append((pl.col("close") / pl.col("close").shift(p) - 1).alias(f"return_{p}d"))
        # Log return: ln(close_t / close_{t-p})
        exprs.append((pl.col("close") / pl.col("close").shift(p)).log().alias(f"log_return_{p}d"))

    return df.with_columns(exprs)


# ==============================================================================
# Volatility Features
# ==============================================================================


def add_volatility_features(
    df: pl.DataFrame,
    windows: list[int] | None = None,
) -> pl.DataFrame:
    """Add rolling volatility, ATR, and realized volatility.

    - Rolling volatility: std(daily returns) * sqrt(252) over a backward window.
    - ATR (Average True Range): Mean of True Range over a backward window.
    - Realized volatility: Sum of squared log returns over a backward window.
    """
    if windows is None:
        windows = [20, 60]

    exprs: list[pl.Expr] = []

    # Daily return for volatility calculation
    daily_ret = pl.col("close").pct_change().alias("_daily_return")

    for w in windows:
        # Annualized rolling volatility
        exprs.append(
            (pl.col("_daily_return").rolling_std(w) * (252**0.5)).alias(f"volatility_{w}d")
        )

        # Realized volatility (sum of squared log returns, annualized)
        exprs.append(
            ((pl.col("close") / pl.col("close").shift(1)).log().pow(2).rolling_sum(w) * (252 / w))
            .sqrt()
            .alias(f"realized_vol_{w}d")
        )

    # True Range components
    tr_expr = pl.max_horizontal(
        pl.col("high") - pl.col("low"),
        (pl.col("high") - pl.col("close").shift(1)).abs(),
        (pl.col("low") - pl.col("close").shift(1)).abs(),
    ).alias("true_range")

    # Add daily return first, then other features
    df = df.with_columns(daily_ret)
    df = df.with_columns(exprs)
    df = df.with_columns(tr_expr)

    # ATR for each window
    atr_exprs = [pl.col("true_range").rolling_mean(w).alias(f"atr_{w}d") for w in windows]
    df = df.with_columns(atr_exprs)

    # Clean up intermediate column
    df = df.drop("_daily_return")

    return df


# ==============================================================================
# Trend Features
# ==============================================================================


def add_trend_features(
    df: pl.DataFrame,
    sma_periods: list[int] | None = None,
    ema_periods: list[int] | None = None,
) -> pl.DataFrame:
    """Add SMA, EMA, price-to-moving-average ratios, and crossover signals.

    - SMA: Simple moving average (backward-looking window).
    - EMA: Exponential moving average.
    - Price/SMA ratio: Relative position to moving average.
    - Crossovers: SMA short-term vs long-term crossover detection.
    """
    if sma_periods is None:
        sma_periods = [20, 50, 200]
    if ema_periods is None:
        ema_periods = [12, 26]

    exprs: list[pl.Expr] = []

    # Simple Moving Averages
    for p in sma_periods:
        exprs.append(pl.col("close").rolling_mean(p).alias(f"sma_{p}"))
        exprs.append(
            (pl.col("close") / pl.col("close").rolling_mean(p)).alias(f"price_sma_{p}_ratio")
        )

    # Exponential Moving Averages
    for p in ema_periods:
        exprs.append(pl.col("close").ewm_mean(span=p, adjust=False).alias(f"ema_{p}"))

    df = df.with_columns(exprs)

    # Moving average crossovers (golden cross / death cross detection)
    if 50 in sma_periods and 200 in sma_periods:
        df = df.with_columns(
            (pl.col("sma_50") > pl.col("sma_200")).cast(pl.Int8).alias("golden_cross_signal"),
            (
                (pl.col("sma_50") > pl.col("sma_200")).cast(pl.Int8)
                - (pl.col("sma_50") > pl.col("sma_200")).shift(1).cast(pl.Int8)
            ).alias("sma_crossover_change"),
        )

    # MACD (EMA 12 - EMA 26) if both periods present
    if 12 in ema_periods and 26 in ema_periods:
        df = df.with_columns(
            (pl.col("ema_12") - pl.col("ema_26")).alias("macd_line"),
        )
        df = df.with_columns(
            pl.col("macd_line").ewm_mean(span=9, adjust=False).alias("macd_signal"),
        )
        df = df.with_columns(
            (pl.col("macd_line") - pl.col("macd_signal")).alias("macd_histogram"),
        )

    return df


# ==============================================================================
# Statistical Features
# ==============================================================================


def add_statistical_features(
    df: pl.DataFrame,
    z_score_window: int = 20,
    percentile_window: int = 252,
) -> pl.DataFrame:
    """Add z-score, percentile rank, rolling skewness, and kurtosis.

    - Z-score: (close - rolling_mean) / rolling_std over a backward window.
    - Percentile rank: Current close as a percentile within the rolling window.
    - Rolling skew/kurtosis: Distribution shape of returns.
    """
    exprs: list[pl.Expr] = []

    # Z-score: how many standard deviations from rolling mean
    exprs.append(
        (
            (pl.col("close") - pl.col("close").rolling_mean(z_score_window))
            / pl.col("close").rolling_std(z_score_window)
        ).alias(f"z_score_{z_score_window}d")
    )

    # Rolling min/max for percentile-like positioning
    exprs.append(
        (
            (pl.col("close") - pl.col("close").rolling_min(percentile_window))
            / (
                pl.col("close").rolling_max(percentile_window)
                - pl.col("close").rolling_min(percentile_window)
            )
        ).alias(f"percentile_rank_{percentile_window}d")
    )

    # Rolling skewness of daily returns
    exprs.append(
        pl.col("close")
        .pct_change()
        .rolling_skew(z_score_window)
        .alias(f"return_skew_{z_score_window}d")
    )

    df = df.with_columns(exprs)
    return df


# ==============================================================================
# Risk Features
# ==============================================================================


def add_risk_features(df: pl.DataFrame, drawdown_window: int = 252) -> pl.DataFrame:
    """Add drawdown and rolling high watermark.

    - Drawdown: Current decline from rolling maximum (always <= 0).
    - High watermark: Rolling maximum close price.
    """
    df = df.with_columns(
        pl.col("close").rolling_max(drawdown_window).alias("rolling_high"),
    )
    df = df.with_columns(
        ((pl.col("close") / pl.col("rolling_high")) - 1).alias("drawdown"),
    )
    return df


# ==============================================================================
# Convenience: Compute All Features
# ==============================================================================


def compute_all_features(
    df: pl.DataFrame,
    momentum_periods: list[int] | None = None,
    volatility_windows: list[int] | None = None,
    sma_periods: list[int] | None = None,
    ema_periods: list[int] | None = None,
) -> pl.DataFrame:
    """Apply all feature groups to a DataFrame.

    This is the standard pipeline for enriching raw OHLCV data with
    quantitative features before feeding into strategies.
    """
    df = add_momentum_features(df, momentum_periods)
    df = add_volatility_features(df, volatility_windows)
    df = add_trend_features(df, sma_periods, ema_periods)
    df = add_statistical_features(df)
    df = add_risk_features(df)
    return df
