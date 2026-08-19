"""
Portfolios Router — Endpoints for portfolio lifecycle, holdings, and performance.
"""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from apps.api.schemas import (
    PortfolioCreateRequest,
    PortfolioPerformanceResponse,
    PortfolioSnapshotResponse,
    PortfolioSummaryResponse,
    PositionResponse,
)
from src.application.services.portfolio_service import PortfolioService
from src.infrastructure.database.session import get_db

router = APIRouter(prefix="/portfolios", tags=["portfolios"])
logger = logging.getLogger(__name__)

service = PortfolioService()


@router.post("", response_model=PortfolioSummaryResponse, status_code=201)
async def create_portfolio(
    request: PortfolioCreateRequest,
    db: Session = Depends(get_db),
) -> PortfolioSummaryResponse:
    """Create a new systematic investment portfolio."""
    portfolio = service.create_portfolio(
        db=db,
        name=request.name,
        description=request.description,
        initial_cash=request.initial_cash,
    )
    return PortfolioSummaryResponse.model_validate(portfolio)


@router.get("", response_model=list[PortfolioSummaryResponse])
async def list_portfolios(
    limit: int = 50,
    db: Session = Depends(get_db),
) -> list[PortfolioSummaryResponse]:
    """List all portfolios."""
    portfolios = service.list_portfolios(db=db, limit=limit)
    return [PortfolioSummaryResponse.model_validate(p) for p in portfolios]


@router.get("/{portfolio_id}", response_model=PortfolioSummaryResponse)
async def get_portfolio(
    portfolio_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> PortfolioSummaryResponse:
    """Retrieve details for a specific portfolio."""
    portfolio = service.get_portfolio(db=db, portfolio_id=portfolio_id)
    if portfolio is None:
        raise HTTPException(status_code=404, detail=f"Portfolio {portfolio_id} not found")
    return PortfolioSummaryResponse.model_validate(portfolio)


@router.get("/{portfolio_id}/positions", response_model=list[PositionResponse])
async def get_portfolio_positions(
    portfolio_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> list[PositionResponse]:
    """Retrieve current asset positions for a portfolio."""
    portfolio = service.get_portfolio(db=db, portfolio_id=portfolio_id)
    if portfolio is None:
        raise HTTPException(status_code=404, detail=f"Portfolio {portfolio_id} not found")

    positions = service.get_positions(db=db, portfolio_id=portfolio_id)
    total_val = portfolio.total_value if portfolio.total_value > 0 else portfolio.cash

    return [
        PositionResponse(
            symbol=pos.asset.symbol if pos.asset else "UNKNOWN",
            quantity=pos.quantity,
            avg_entry_price=pos.avg_entry_price,
            current_price=pos.current_price,
            market_value=pos.market_value,
            unrealized_pnl=pos.unrealized_pnl,
            weight=pos.market_value / total_val if total_val > 0 else 0.0,
        )
        for pos in positions
    ]


@router.get("/{portfolio_id}/performance", response_model=PortfolioPerformanceResponse)
async def get_portfolio_performance(
    portfolio_id: uuid.UUID,
    limit: int = 100,
    db: Session = Depends(get_db),
) -> PortfolioPerformanceResponse:
    """Retrieve historical performance snapshots for a portfolio."""
    portfolio = service.get_portfolio(db=db, portfolio_id=portfolio_id)
    if portfolio is None:
        raise HTTPException(status_code=404, detail=f"Portfolio {portfolio_id} not found")

    snapshots = service.get_snapshots(db=db, portfolio_id=portfolio_id, limit=limit)
    return PortfolioPerformanceResponse(
        portfolio_id=portfolio_id,
        total_value=portfolio.total_value,
        cash=portfolio.cash,
        snapshots=[PortfolioSnapshotResponse.model_validate(s) for s in snapshots],
    )
