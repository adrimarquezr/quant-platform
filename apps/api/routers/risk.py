"""
Risk Router — Endpoints for portfolio risk evaluation, limit audits, and violations.
"""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from apps.api.schemas import (
    RiskEvaluateRequest,
    RiskMetricResponse,
    RiskViolationResponse,
)
from src.application.services.risk_service import RiskService
from src.domain.models import RiskLimitConfig
from src.infrastructure.database.models import RiskMetricORM
from src.infrastructure.database.session import get_db

router = APIRouter(prefix="/risk", tags=["risk"])
logger = logging.getLogger(__name__)

service = RiskService()


@router.post("/evaluate", response_model=RiskMetricResponse)
async def evaluate_risk(
    request: RiskEvaluateRequest,
    db: Session = Depends(get_db),
) -> RiskMetricResponse:
    """Evaluate point-in-time risk profile and check compliance against risk limits."""
    limits = RiskLimitConfig(
        max_position_weight=request.max_position_weight,
        max_gross_exposure=request.max_gross_exposure,
        max_volatility=request.max_volatility,
        max_drawdown=request.max_drawdown,
        max_var_95=request.max_var_95,
    )

    profile = service.evaluate_and_record(
        equity_curve=request.equity_curve,
        returns=request.returns,
        current_weights=request.current_weights,
        benchmark_returns=request.benchmark_returns,
        limits=limits,
        db=db,
    )

    violations_resp = [
        RiskViolationResponse(
            rule_name=v.rule_name,
            description=v.description,
            actual_value=v.actual_value,
            limit_value=v.limit_value,
            severity=v.severity,
        )
        for v in profile.violations
    ]

    return RiskMetricResponse(
        timestamp=profile.timestamp,
        var_95=profile.var_95,
        cvar_95=profile.cvar_95,
        volatility=profile.volatility,
        max_drawdown=profile.drawdown_details.max_drawdown,
        current_drawdown=profile.drawdown_details.current_drawdown,
        gross_exposure=profile.gross_exposure,
        net_exposure=profile.net_exposure,
        concentration_hhi=profile.concentration_hhi,
        beta=profile.beta,
        verdict=profile.verdict.value,
        violations=violations_resp,
    )


@router.get("", response_model=list[dict])
async def list_recent_risk_metrics(
    limit: int = 50,
    db: Session = Depends(get_db),
) -> list[dict]:
    """Retrieve recent risk metric audits from the database."""
    metrics = db.query(RiskMetricORM).order_by(RiskMetricORM.timestamp.desc()).limit(limit).all()
    return [
        {
            "id": str(m.id),
            "portfolio_id": str(m.portfolio_id) if m.portfolio_id else None,
            "backtest_id": str(m.backtest_id) if m.backtest_id else None,
            "timestamp": m.timestamp.isoformat() if m.timestamp else None,
            "var_95": m.var_95,
            "cvar_95": m.cvar_95,
            "volatility": m.volatility,
            "max_drawdown": m.max_drawdown,
            "beta": m.beta,
            "leverage": m.leverage,
        }
        for m in metrics
    ]


@router.get("/portfolio/{portfolio_id}", response_model=list[dict])
async def get_portfolio_risk_metrics(
    portfolio_id: uuid.UUID,
    limit: int = 50,
    db: Session = Depends(get_db),
) -> list[dict]:
    """Retrieve historical risk metrics for a specific portfolio."""
    metrics = service.get_metrics_for_portfolio(db=db, portfolio_id=portfolio_id, limit=limit)
    return [
        {
            "id": str(m.id),
            "portfolio_id": str(m.portfolio_id),
            "timestamp": m.timestamp.isoformat() if m.timestamp else None,
            "var_95": m.var_95,
            "cvar_95": m.cvar_95,
            "volatility": m.volatility,
            "max_drawdown": m.max_drawdown,
            "beta": m.beta,
            "leverage": m.leverage,
        }
        for m in metrics
    ]


@router.get("/violations", response_model=list[RiskViolationResponse])
async def list_risk_violations(
    portfolio_id: uuid.UUID | None = None,
    limit: int = 50,
    db: Session = Depends(get_db),
) -> list[RiskViolationResponse]:
    """List risk limit violations recorded across portfolios or backtests."""
    violations = service.get_violations(db=db, portfolio_id=portfolio_id, limit=limit)
    return [
        RiskViolationResponse(
            rule_name=v.rule_name,
            description=v.description,
            actual_value=v.actual_value,
            limit_value=v.limit_value,
            severity=v.severity,
        )
        for v in violations
    ]
