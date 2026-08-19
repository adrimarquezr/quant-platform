"""
Parquet Data Lake — Local storage for OHLCV time series and feature datasets.

Raw market data and computed features are stored as partitioned Parquet files
for high-performance analytical queries via Polars/DuckDB.
PostgreSQL stores only metadata pointers (MarketDataMetadataORM).
"""

from __future__ import annotations

import logging
from pathlib import Path

import duckdb
import polars as pl

logger = logging.getLogger(__name__)

DEFAULT_DATA_DIR = Path("data")


class ParquetStorage:
    """Read/write Polars DataFrames to/from partitioned Parquet files."""

    def __init__(self, base_dir: Path | str = DEFAULT_DATA_DIR) -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _symbol_path(self, category: str, frequency: str, symbol: str) -> Path:
        """Build the path: data/{category}/{frequency}/{symbol}/data.parquet"""
        path = self.base_dir / category / frequency / symbol
        path.mkdir(parents=True, exist_ok=True)
        return path / "data.parquet"

    def save_ohlcv(
        self,
        df: pl.DataFrame,
        symbol: str,
        frequency: str = "1d",
        category: str = "raw",
    ) -> Path:
        """Persist an OHLCV DataFrame to Parquet."""
        path = self._symbol_path(category, frequency, symbol)
        df.write_parquet(path, compression="zstd")
        logger.info("Saved %d rows for %s to %s", len(df), symbol, path)
        return path

    def load_ohlcv(
        self,
        symbol: str,
        frequency: str = "1d",
        category: str = "raw",
    ) -> pl.DataFrame:
        """Load an OHLCV DataFrame from Parquet."""
        path = self._symbol_path(category, frequency, symbol)
        if not path.exists():
            msg = f"No data file found at {path}"
            raise FileNotFoundError(msg)
        return pl.read_parquet(path)

    def save_features(
        self,
        df: pl.DataFrame,
        feature_set_name: str,
        version: str = "v1",
    ) -> Path:
        """Persist a feature dataset to Parquet."""
        path = self.base_dir / "features" / version
        path.mkdir(parents=True, exist_ok=True)
        file_path = path / f"{feature_set_name}.parquet"
        df.write_parquet(file_path, compression="zstd")
        logger.info("Saved feature set '%s' (%d rows) to %s", feature_set_name, len(df), file_path)
        return file_path

    def load_features(
        self,
        feature_set_name: str,
        version: str = "v1",
    ) -> pl.DataFrame:
        """Load a feature dataset from Parquet."""
        file_path = self.base_dir / "features" / version / f"{feature_set_name}.parquet"
        if not file_path.exists():
            msg = f"Feature set not found: {file_path}"
            raise FileNotFoundError(msg)
        return pl.read_parquet(file_path)

    def list_symbols(self, category: str = "raw", frequency: str = "1d") -> list[str]:
        """List all symbols that have stored data."""
        data_dir = self.base_dir / category / frequency
        if not data_dir.exists():
            return []
        return sorted(
            d.name for d in data_dir.iterdir() if d.is_dir() and (d / "data.parquet").exists()
        )

    def exists(self, symbol: str, frequency: str = "1d", category: str = "raw") -> bool:
        """Check if data exists for a symbol."""
        path = self._symbol_path(category, frequency, symbol)
        return path.exists()


class DuckDBQueryEngine:
    """Execute analytical SQL queries over Parquet files using DuckDB."""

    def __init__(self, base_dir: Path | str = DEFAULT_DATA_DIR) -> None:
        self.base_dir = Path(base_dir)
        self.conn = duckdb.connect(":memory:")

    def query_ohlcv(
        self,
        symbol: str,
        sql: str | None = None,
        frequency: str = "1d",
        category: str = "raw",
    ) -> pl.DataFrame:
        """Run an analytical query over a symbol's Parquet file.

        If no SQL is provided, returns all data.
        Use '{{table}}' as a placeholder for the Parquet file path in your SQL.
        """
        parquet_path = self.base_dir / category / frequency / symbol / "data.parquet"
        if not parquet_path.exists():
            msg = f"No data found at {parquet_path}"
            raise FileNotFoundError(msg)

        parquet_str = str(parquet_path).replace("\\", "/")

        if sql is None:
            sql = f"SELECT * FROM '{parquet_str}' ORDER BY timestamp"
        else:
            sql = sql.replace("{{table}}", f"'{parquet_str}'")

        result = self.conn.execute(sql).pl()
        return result

    def query_sql(self, sql: str) -> pl.DataFrame:
        """Execute arbitrary SQL — useful for cross-symbol analytics."""
        return self.conn.execute(sql).pl()

    def close(self) -> None:
        """Close the DuckDB connection."""
        self.conn.close()
