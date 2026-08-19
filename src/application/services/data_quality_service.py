"""
Data Quality Application Service — Executes validations and manages audit logs.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

import polars as pl
from sqlalchemy.orm import Session

from src.application.data_quality import DataQualityValidator
from src.domain.models import DataQualityReport
from src.infrastructure.database.models import DataQualityCheckORM, DataQualityRunORM

logger = logging.getLogger(__name__)


class DataQualityService:
    """Service layer for Data Quality validations and persistence."""

    def __init__(self, validator: DataQualityValidator | None = None) -> None:
        self.validator = validator or DataQualityValidator()

    def validate_and_record(
        self,
        df: pl.DataFrame,
        symbol: str,
        dataset_name: str = "daily_ohlcv",
        db: Session | None = None,
    ) -> DataQualityReport:
        """Run validation on a dataset and optionally persist results to PostgreSQL."""
        report = self.validator.validate_dataset(df, symbol=symbol, dataset_name=dataset_name)

        if db is not None:
            try:
                run_orm = DataQualityRunORM(
                    id=uuid.uuid4(),
                    dataset=report.dataset,
                    symbol=report.symbol,
                    status=report.status.value,
                    rows_checked=report.rows_checked,
                    created_at=datetime.now(UTC),
                )
                db.add(run_orm)
                db.flush()

                for check in report.checks:
                    check_orm = DataQualityCheckORM(
                        id=uuid.uuid4(),
                        run_id=run_orm.id,
                        check_name=check.check_name,
                        status=check.status.value,
                        message=check.message,
                        details_json=check.details if check.details else None,
                    )
                    db.add(check_orm)

                db.commit()
                logger.info("Persisted DataQualityRun %s for symbol %s", run_orm.id, symbol)
            except Exception as e:
                db.rollback()
                logger.exception("Failed to persist data quality run for %s: %s", symbol, e)

        return report

    def get_runs(
        self, db: Session, limit: int = 50, symbol: str | None = None
    ) -> list[DataQualityRunORM]:
        """Retrieve recent data quality runs."""
        query = db.query(DataQualityRunORM)
        if symbol:
            query = query.filter(DataQualityRunORM.symbol == symbol)
        return query.order_by(DataQualityRunORM.created_at.desc()).limit(limit).all()

    def get_run_by_id(self, db: Session, run_id: uuid.UUID) -> DataQualityRunORM | None:
        """Retrieve a specific data quality run with its checks."""
        return db.query(DataQualityRunORM).filter(DataQualityRunORM.id == run_id).first()
