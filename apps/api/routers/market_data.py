"""
Market Data Router — Endpoints for data ingestion, retrieval, and quality validation.

No business logic here — delegates to application services.
"""

from __future__ import annotations

import logging
from datetime import date
from pathlib import Path

from fastapi import APIRouter, HTTPException

from apps.api.schemas import DataQualityReport, MarketDataRequest, MarketDataSummary, PriceBar
from src.application.data_quality import DataQualityValidator
from src.infrastructure.data_providers.yahoo_finance import YahooFinanceProvider
from src.infrastructure.storage.parquet_storage import ParquetStorage

router = APIRouter(prefix="/market-data", tags=["market-data"])
logger = logging.getLogger(__name__)

# Service instances — in production these would be injected via DI
provider = YahooFinanceProvider()
storage = ParquetStorage(base_dir=Path("data"))
validator = DataQualityValidator()


@router.post("/ingest", response_model=MarketDataSummary)
async def ingest_market_data(request: MarketDataRequest) -> MarketDataSummary:
    """Ingest OHLCV data from a provider and persist to Parquet.

    Pipeline: Provider → Validation → Parquet Storage
    """
    try:
        # Fetch data
        df = provider.fetch_ohlcv(
            symbol=request.symbol,
            start_date=request.start_date,
            end_date=request.end_date,
            frequency=request.frequency,
        )

        # Validate data quality
        errors = validator.validate(df, request.symbol)
        if errors:
            raise HTTPException(
                status_code=422,
                detail={"message": "Data quality validation failed", "errors": errors},
            )

        # Persist to Parquet
        path = storage.save_ohlcv(df, request.symbol, request.frequency)

        return MarketDataSummary(
            symbol=request.symbol,
            provider=request.provider,
            frequency=request.frequency,
            start_date=request.start_date,
            end_date=request.end_date,
            row_count=len(df),
            parquet_path=str(path),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to ingest data for %s", request.symbol)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/prices/{symbol}", response_model=list[PriceBar])
async def get_prices(
    symbol: str,
    start_date: date | None = None,
    end_date: date | None = None,
    limit: int = 100,
) -> list[PriceBar]:
    """Retrieve price data from the Parquet data lake."""
    try:
        df = storage.load_ohlcv(symbol)

        # Apply date filters
        if start_date:
            df = df.filter(df["timestamp"].dt.date() >= start_date)
        if end_date:
            df = df.filter(df["timestamp"].dt.date() <= end_date)

        df = df.tail(limit)

        return [
            PriceBar(
                timestamp=row["timestamp"],
                open=row["open"],
                high=row["high"],
                low=row["low"],
                close=row["close"],
                volume=row["volume"],
                adjusted_close=row.get("adjusted_close"),
            )
            for row in df.iter_rows(named=True)
        ]
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"No data found for {symbol}") from None
    except Exception as e:
        logger.exception("Error fetching prices for %s", symbol)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/symbols", response_model=list[str])
async def list_symbols() -> list[str]:
    """List all symbols with ingested data."""
    return storage.list_symbols()


@router.post("/validate/{symbol}", response_model=DataQualityReport)
async def validate_data(symbol: str) -> DataQualityReport:
    """Run data quality validation on stored data for a symbol."""
    try:
        df = storage.load_ohlcv(symbol)
        errors = validator.validate(df, symbol)
        return DataQualityReport(
            symbol=symbol,
            is_valid=len(errors) == 0,
            errors=errors,
            row_count=len(df),
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"No data found for {symbol}") from None
