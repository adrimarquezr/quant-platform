"""
Data Quality Router — Endpoints for data validation, quality runs, and audit logs.
"""

from __future__ import annotations

import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from apps.api.schemas import (
    DataQualityCheckResponse,
    DataQualityReportResponse,
    DataQualityRunSummary,
)
from src.application.services.data_quality_service import DataQualityService
from src.infrastructure.data_providers.yahoo_finance import YahooFinanceProvider
from src.infrastructure.database.session import get_db
from src.infrastructure.storage.parquet_storage import ParquetStorage

router = APIRouter(prefix="/data-quality", tags=["data-quality"])
logger = logging.getLogger(__name__)

service = DataQualityService()
storage = ParquetStorage(base_dir=Path("data"))
provider = YahooFinanceProvider()


@router.post("/validate/{symbol}", response_model=DataQualityReportResponse)
async def validate_symbol_data(
    symbol: str,
    db: Session = Depends(get_db),
) -> DataQualityReportResponse:
    """Validate data quality for a specific symbol (loads from storage or fetches)."""
    try:
        if storage.exists(symbol):
            df = storage.load_ohlcv(symbol)
        else:
            from datetime import date, timedelta

            end_d = date.today()
            start_d = end_d - timedelta(days=365 * 2)
            df = provider.fetch_ohlcv(symbol, start_d, end_d)
            storage.save_ohlcv(df, symbol)
    except Exception as e:
        logger.exception("Failed to obtain data for symbol %s: %s", symbol, e)
        raise HTTPException(status_code=500, detail=f"Could not load data for {symbol}: {e}") from e

    report = service.validate_and_record(df=df, symbol=symbol, db=db)

    return DataQualityReportResponse(
        dataset=report.dataset,
        symbol=report.symbol,
        status=report.status.value,
        is_valid=report.is_valid,
        rows_checked=report.rows_checked,
        errors=report.errors,
        checks=[
            DataQualityCheckResponse(
                check_name=c.check_name,
                status=c.status.value,
                message=c.message,
                details=c.details,
            )
            for c in report.checks
        ],
        timestamp=report.timestamp,
    )


@router.get("", response_model=list[DataQualityRunSummary])
async def list_data_quality_runs(
    symbol: str | None = None,
    limit: int = 50,
    db: Session = Depends(get_db),
) -> list[DataQualityRunSummary]:
    """List historical data quality audit runs."""
    runs = service.get_runs(db=db, limit=limit, symbol=symbol)
    return [DataQualityRunSummary.model_validate(r) for r in runs]


@router.get("/{run_id}", response_model=dict)
async def get_data_quality_run(
    run_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> dict:
    """Retrieve details and check results for a specific data quality run."""
    run = service.get_run_by_id(db=db, run_id=run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"DataQualityRun {run_id} not found")

    return {
        "id": str(run.id),
        "dataset": run.dataset,
        "symbol": run.symbol,
        "status": run.status,
        "rows_checked": run.rows_checked,
        "created_at": run.created_at.isoformat() if run.created_at else None,
        "checks": [
            {
                "id": str(c.id),
                "check_name": c.check_name,
                "status": c.status,
                "message": c.message,
                "details": c.details_json,
            }
            for c in run.checks
        ],
    }
