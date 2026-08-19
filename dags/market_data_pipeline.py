"""
Market Data Pipeline DAG — Ingestion, Data Quality, and Feature Generation.

Thin orchestration layer: delegates execution to domain and application services.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from pathlib import Path

from airflow import DAG
from airflow.operators.python import PythonOperator

logger = logging.getLogger(__name__)

DEFAULT_UNIVERSE = ["SPY", "QQQ", "IWM", "TLT", "GLD"]
DATA_DIR = Path("data")


def ingest_market_data(**context) -> list[str]:
    """Fetch raw OHLCV market data for universe assets."""
    from src.infrastructure.data_providers.yahoo_finance import YahooFinanceProvider
    from src.infrastructure.storage.parquet_storage import ParquetStorage

    provider = YahooFinanceProvider()
    storage = ParquetStorage(base_dir=DATA_DIR)

    end_date = date.today()
    start_date = end_date - timedelta(days=365 * 2)

    ingested_symbols: list[str] = []
    for symbol in DEFAULT_UNIVERSE:
        try:
            df = provider.fetch_ohlcv(symbol, start_date, end_date)
            storage.save_ohlcv(df, symbol=symbol, frequency="1d")
            ingested_symbols.append(symbol)
            logger.info("Ingested %d rows for %s", len(df), symbol)
        except Exception as e:
            logger.exception("Failed to ingest %s: %s", symbol, e)
            raise

    return ingested_symbols


def validate_data_quality(**context) -> bool:
    """Validate data quality for all ingested assets. Fail fast if corrupted."""
    from src.application.data_quality import DataQualityValidator
    from src.domain.models import QualityCheckStatus
    from src.infrastructure.storage.parquet_storage import ParquetStorage

    storage = ParquetStorage(base_dir=DATA_DIR)
    validator = DataQualityValidator()

    for symbol in DEFAULT_UNIVERSE:
        if not storage.exists(symbol):
            msg = f"Data missing for required symbol: {symbol}"
            raise FileNotFoundError(msg)

        df = storage.load_ohlcv(symbol)
        report = validator.validate_dataset(df, symbol=symbol)

        if report.status == QualityCheckStatus.FAILED:
            msg = f"Data quality validation FAILED for {symbol}: {report.errors}"
            logger.error(msg)
            raise ValueError(msg)

        logger.info("Data quality validation PASSED for %s (%d rows)", symbol, report.rows_checked)

    return True


def compute_features(**context) -> bool:
    """Compute and store quantitative feature datasets for all assets."""
    from src.features.engine import FeatureEngine
    from src.infrastructure.storage.parquet_storage import ParquetStorage

    storage = ParquetStorage(base_dir=DATA_DIR)
    engine = FeatureEngine()

    for symbol in DEFAULT_UNIVERSE:
        df = storage.load_ohlcv(symbol)
        df_features = engine.transform(df)
        storage.save_features(df_features, feature_set_name=f"{symbol}_features", version="v1")
        logger.info("Computed and saved features for %s (%d rows)", symbol, len(df_features))

    return True


default_args = {
    "owner": "quant_platform",
    "depends_on_past": False,
    "start_date": datetime(2024, 1, 1),
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="market_data_pipeline",
    default_args=default_args,
    description="Daily ingestion, quality validation, and feature generation pipeline",
    schedule_interval="0 22 * * 1-5",  # 10 PM UTC on trading days
    catchup=False,
    tags=["market_data", "data_quality", "features"],
) as dag:
    task_ingest = PythonOperator(
        task_id="ingest_market_data",
        python_callable=ingest_market_data,
    )

    task_validate_dq = PythonOperator(
        task_id="validate_data_quality",
        python_callable=validate_data_quality,
    )

    task_compute_features = PythonOperator(
        task_id="compute_features",
        python_callable=compute_features,
    )

    task_ingest >> task_validate_dq >> task_compute_features
