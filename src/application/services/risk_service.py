"""
Risk Application Service — Orchestrates risk audits, metric logging, and violation alerts.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from src.application.risk.engine import RiskEngine
from src.domain.models import RiskLimitConfig, RiskProfile
from src.infrastructure.database.models import RiskMetricORM, RiskViolationORM

logger = logging.getLogger(__name__)


class RiskService:
    """Service layer for Risk audits, calculations, and persistence."""

    def __init__(self, engine: RiskEngine | None = None) -> None:
        self.engine = engine or RiskEngine()

    def evaluate_and_record(
        self,
        equity_curve: list[float],
        returns: list[float],
        current_weights: dict[str, float],
        db: Session | None = None,
        portfolio_id: uuid.UUID | None = None,
        backtest_id: uuid.UUID | None = None,
        asset_returns: dict[str, list[float]] | None = None,
        benchmark_returns: list[float] | None = None,
        limits: RiskLimitConfig | None = None,
    ) -> RiskProfile:
        """Calculate risk profile and optionally persist metrics and violations to database."""
        profile = self.engine.evaluate_risk(
            equity_curve=equity_curve,
            returns=returns,
            current_weights=current_weights,
            asset_returns=asset_returns,
            benchmark_returns=benchmark_returns,
            limits=limits,
        )

        if db is not None:
            try:
                now = datetime.utcnow()

                # Save point in time metric snapshot
                metric_orm = RiskMetricORM(
                    id=uuid.uuid4(),
                    portfolio_id=portfolio_id,
                    backtest_id=backtest_id,
                    timestamp=now,
                    var_95=profile.var_95,
                    cvar_95=profile.cvar_95,
                    volatility=profile.volatility,
                    beta=profile.beta,
                    max_drawdown=profile.drawdown_details.max_drawdown,
                    concentration=profile.concentration_hhi,
                    leverage=profile.gross_exposure,
                )
                db.add(metric_orm)

                # Save violations if any
                for v in profile.violations:
                    violation_orm = RiskViolationORM(
                        id=uuid.uuid4(),
                        portfolio_id=portfolio_id,
                        backtest_id=backtest_id,
                        rule_name=v.rule_name,
                        description=v.description,
                        actual_value=v.actual_value,
                        limit_value=v.limit_value,
                        severity=v.severity,
                        created_at=now,
                    )
                    db.add(violation_orm)

                db.commit()
                logger.info(
                    "Recorded risk profile: verdict=%s, violations=%d",
                    profile.verdict.value,
                    len(profile.violations),
                )
            except Exception as e:
                db.rollback()
                logger.exception("Failed to persist risk metrics: %s", e)

        return profile

    def get_metrics_for_portfolio(
        self, db: Session, portfolio_id: uuid.UUID, limit: int = 50
    ) -> list[RiskMetricORM]:
        """Retrieve historical risk metrics for a specific portfolio."""
        return (
            db.query(RiskMetricORM)
            .filter(RiskMetricORM.portfolio_id == portfolio_id)
            .order_by(RiskMetricORM.timestamp.desc())
            .limit(limit)
            .all()
        )

    def get_violations(
        self,
        db: Session,
        portfolio_id: uuid.UUID | None = None,
        limit: int = 50,
    ) -> list[RiskViolationORM]:
        """Query logged risk violations."""
        query = db.query(RiskViolationORM)
        if portfolio_id:
            query = query.filter(RiskViolationORM.portfolio_id == portfolio_id)
        return query.order_by(RiskViolationORM.created_at.desc()).limit(limit).all()
