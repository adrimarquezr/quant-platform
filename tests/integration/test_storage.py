"""
Integration tests for Parquet Storage and DuckDB Query Engine.
"""

from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest

from src.infrastructure.storage.parquet_storage import DuckDBQueryEngine, ParquetStorage


@pytest.mark.integration
class TestParquetStorage:
    """Test read/write operations for ParquetStorage."""

    def test_save_and_load_ohlcv(self, tmp_path: Path, sample_ohlcv_df: pl.DataFrame) -> None:
        storage = ParquetStorage(base_dir=tmp_path)
        path = storage.save_ohlcv(sample_ohlcv_df, "SPY")

        assert path.exists()
        assert storage.exists("SPY")

        loaded = storage.load_ohlcv("SPY")
        assert len(loaded) == len(sample_ohlcv_df)
        assert loaded.columns == sample_ohlcv_df.columns

    def test_save_and_load_features(self, tmp_path: Path, sample_ohlcv_df: pl.DataFrame) -> None:
        storage = ParquetStorage(base_dir=tmp_path)
        path = storage.save_features(sample_ohlcv_df, "momentum_features")

        assert path.exists()

        loaded = storage.load_features("momentum_features")
        assert len(loaded) == len(sample_ohlcv_df)

    def test_list_symbols(self, tmp_path: Path, sample_ohlcv_df: pl.DataFrame) -> None:
        storage = ParquetStorage(base_dir=tmp_path)
        storage.save_ohlcv(sample_ohlcv_df, "SPY")
        storage.save_ohlcv(sample_ohlcv_df, "QQQ")

        symbols = storage.list_symbols()
        assert symbols == ["QQQ", "SPY"]

    def test_load_nonexistent_raises(self, tmp_path: Path) -> None:
        storage = ParquetStorage(base_dir=tmp_path)
        with pytest.raises(FileNotFoundError):
            storage.load_ohlcv("NONEXISTENT")


@pytest.mark.integration
class TestDuckDBQueryEngine:
    """Test OLAP queries via DuckDB over Parquet files."""

    def test_query_ohlcv(self, tmp_path: Path, sample_ohlcv_df: pl.DataFrame) -> None:
        storage = ParquetStorage(base_dir=tmp_path)
        storage.save_ohlcv(sample_ohlcv_df, "SPY")

        engine = DuckDBQueryEngine(base_dir=tmp_path)
        result = engine.query_ohlcv("SPY")

        assert len(result) == len(sample_ohlcv_df)
        engine.close()

    def test_custom_sql_query(self, tmp_path: Path, sample_ohlcv_df: pl.DataFrame) -> None:
        storage = ParquetStorage(base_dir=tmp_path)
        storage.save_ohlcv(sample_ohlcv_df, "SPY")

        engine = DuckDBQueryEngine(base_dir=tmp_path)
        # Query max close price
        result = engine.query_ohlcv("SPY", sql="SELECT MAX(close) as max_close FROM {{table}}")

        assert "max_close" in result.columns
        assert result["max_close"][0] > 0
        engine.close()
