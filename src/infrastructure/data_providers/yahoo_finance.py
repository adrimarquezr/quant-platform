"""
Yahoo Finance Data Provider — Fetches OHLCV data via yfinance.

This is the default provider for the MVP. It wraps yfinance and normalizes
the output into a standard Polars DataFrame schema that all downstream
components expect.
"""

from __future__ import annotations

import logging
from datetime import date

import polars as pl
import yfinance as yf

from src.domain.interfaces import IMarketDataProvider

logger = logging.getLogger(__name__)

# Standard column schema expected by all downstream consumers
OHLCV_SCHEMA = ["timestamp", "open", "high", "low", "close", "volume", "adjusted_close"]


class YahooFinanceProvider(IMarketDataProvider):
    """Fetches daily OHLCV data from Yahoo Finance."""

    def get_provider_name(self) -> str:
        return "yahoo_finance"

    def fetch_ohlcv(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
        frequency: str = "1d",
    ) -> pl.DataFrame:
        """Fetch OHLCV for a single symbol and return a normalized Polars DataFrame."""
        logger.info(
            "Fetching %s from Yahoo Finance: %s to %s (%s)",
            symbol,
            start_date,
            end_date,
            frequency,
        )

        ticker = yf.Ticker(symbol)
        hist = ticker.history(
            start=start_date.isoformat(),
            end=end_date.isoformat(),
            interval=frequency,
            auto_adjust=False,
        )

        if hist.empty:
            msg = f"No data returned from Yahoo Finance for {symbol}"
            raise ValueError(msg)

        # Reset index to make Date a column
        hist = hist.reset_index()

        # Convert to Polars and normalize column names
        df = pl.from_pandas(hist)

        # Normalize column names (yfinance returns capitalized columns)
        rename_map = {
            "Date": "timestamp",
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Volume": "volume",
            "Adj Close": "adjusted_close",
        }

        # Handle both possible column name formats
        existing_cols = set(df.columns)
        actual_renames = {k: v for k, v in rename_map.items() if k in existing_cols}
        df = df.rename(actual_renames)

        # If no adjusted_close column, use close
        if "adjusted_close" not in df.columns:
            df = df.with_columns(pl.col("close").alias("adjusted_close"))

        # Select and order standard columns
        available = [c for c in OHLCV_SCHEMA if c in df.columns]
        df = df.select(available)

        # Ensure timestamp is datetime type and timezone-naive
        df = df.with_columns(pl.col("timestamp").dt.replace_time_zone(None).cast(pl.Datetime("us")))

        # Sort by timestamp ascending
        df = df.sort("timestamp")

        # Cast numeric columns to Float64
        numeric_cols = ["open", "high", "low", "close", "volume", "adjusted_close"]
        for col in numeric_cols:
            if col in df.columns:
                df = df.with_columns(pl.col(col).cast(pl.Float64))

        logger.info("Fetched %d bars for %s", len(df), symbol)
        return df

    def fetch_multiple(
        self,
        symbols: list[str],
        start_date: date,
        end_date: date,
        frequency: str = "1d",
    ) -> dict[str, pl.DataFrame]:
        """Fetch OHLCV data for multiple symbols."""
        result: dict[str, pl.DataFrame] = {}
        for symbol in symbols:
            try:
                result[symbol] = self.fetch_ohlcv(symbol, start_date, end_date, frequency)
            except Exception:
                logger.exception("Failed to fetch data for %s", symbol)
                raise
        return result
