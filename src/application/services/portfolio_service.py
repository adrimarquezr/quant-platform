"""
Portfolio Application Service — Manages portfolio creation, rebalancing, and history.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from src.application.portfolio.engine import PortfolioEngine
from src.domain.models import (
    PortfolioConstraints,
    PortfolioConstructionMethod,
    Signal,
    TargetWeights,
)
from src.infrastructure.database.models import (
    AssetORM,
    PortfolioORM,
    PortfolioSnapshotORM,
    PositionORM,
)

logger = logging.getLogger(__name__)


class PortfolioService:
    """Service layer for Portfolio management, construction, and persistence."""

    def __init__(self, engine: PortfolioEngine | None = None) -> None:
        self.engine = engine or PortfolioEngine()

    def create_portfolio(
        self,
        db: Session,
        name: str,
        description: str = "",
        initial_cash: float = 100_000.0,
    ) -> PortfolioORM:
        """Create and persist a new portfolio."""
        now = datetime.now(UTC)
        portfolio = PortfolioORM(
            id=uuid.uuid4(),
            name=name,
            description=description,
            cash=initial_cash,
            total_value=initial_cash,
            updated_at=now,
        )
        db.add(portfolio)
        db.commit()
        db.refresh(portfolio)

        # Initial snapshot
        snapshot = PortfolioSnapshotORM(
            id=uuid.uuid4(),
            portfolio_id=portfolio.id,
            timestamp=now,
            total_value=initial_cash,
            cash=initial_cash,
            positions_value=0.0,
            daily_return=0.0,
        )
        db.add(snapshot)
        db.commit()

        logger.info("Created portfolio '%s' (%s) with $%.2f cash", name, portfolio.id, initial_cash)
        return portfolio

    def get_portfolio(self, db: Session, portfolio_id: uuid.UUID) -> PortfolioORM | None:
        """Retrieve portfolio by ID."""
        return db.query(PortfolioORM).filter(PortfolioORM.id == portfolio_id).first()

    def list_portfolios(self, db: Session, limit: int = 50) -> list[PortfolioORM]:
        """List all portfolios."""
        return db.query(PortfolioORM).order_by(PortfolioORM.updated_at.desc()).limit(limit).all()

    def get_positions(self, db: Session, portfolio_id: uuid.UUID) -> list[PositionORM]:
        """Retrieve current holdings of a portfolio."""
        return db.query(PositionORM).filter(PositionORM.portfolio_id == portfolio_id).all()

    def get_snapshots(
        self, db: Session, portfolio_id: uuid.UUID, limit: int = 100
    ) -> list[PortfolioSnapshotORM]:
        """Retrieve historical equity snapshots for performance analysis."""
        return (
            db.query(PortfolioSnapshotORM)
            .filter(PortfolioSnapshotORM.portfolio_id == portfolio_id)
            .order_by(PortfolioSnapshotORM.timestamp.asc())
            .limit(limit)
            .all()
        )

    def rebalance(
        self,
        db: Session,
        portfolio_id: uuid.UUID,
        signals: list[Signal],
        volatilities: dict[str, float] | None = None,
        prices: dict[str, float] | None = None,
        method: PortfolioConstructionMethod = PortfolioConstructionMethod.EQUAL_WEIGHT,
        constraints: PortfolioConstraints | None = None,
    ) -> TargetWeights:
        """Construct target weights and rebalance portfolio positions in database."""
        portfolio = self.get_portfolio(db, portfolio_id)
        if portfolio is None:
            msg = f"Portfolio {portfolio_id} not found"
            raise ValueError(msg)

        prices = prices or {}
        current_positions = {p.asset.symbol: p.quantity for p in portfolio.positions if p.asset}

        # Calculate current weights
        total_val = portfolio.total_value if portfolio.total_value > 0 else portfolio.cash
        current_weights: dict[str, float] = {}
        for sym, qty in current_positions.items():
            px = prices.get(sym, 100.0)
            current_weights[sym] = (qty * px) / total_val if total_val > 0 else 0.0

        # Construct target weights via PortfolioEngine
        target_weights = self.engine.construct_weights(
            signals=signals,
            current_weights=current_weights,
            volatilities=volatilities,
            method=method,
            constraints=constraints,
        )

        # Update positions in database
        positions_val = 0.0
        now = datetime.now(UTC)

        for sym, target_w in target_weights.weights.items():
            px = prices.get(sym, 100.0)
            target_notional = total_val * target_w
            target_qty = target_notional / px if px > 0 else 0.0

            # Find or create asset
            asset = db.query(AssetORM).filter(AssetORM.symbol == sym).first()
            if not asset:
                asset = AssetORM(
                    id=uuid.uuid4(),
                    symbol=sym,
                    name=sym,
                    asset_class="etf",
                    currency="USD",
                )
                db.add(asset)
                db.flush()

            # Find existing position
            pos = (
                db.query(PositionORM)
                .filter(PositionORM.portfolio_id == portfolio.id, PositionORM.asset_id == asset.id)
                .first()
            )
            if pos is None:
                pos = PositionORM(
                    id=uuid.uuid4(),
                    portfolio_id=portfolio.id,
                    asset_id=asset.id,
                    quantity=target_qty,
                    avg_entry_price=px,
                    current_price=px,
                    market_value=target_notional,
                    unrealized_pnl=0.0,
                    updated_at=now,
                )
                db.add(pos)
            else:
                pos.quantity = target_qty
                pos.current_price = px
                pos.market_value = target_notional
                pos.unrealized_pnl = target_qty * (px - pos.avg_entry_price)
                pos.updated_at = now

            positions_val += abs(target_notional)

        # Record portfolio snapshot
        portfolio.updated_at = now
        snapshot = PortfolioSnapshotORM(
            id=uuid.uuid4(),
            portfolio_id=portfolio.id,
            timestamp=now,
            total_value=total_val,
            cash=portfolio.cash,
            positions_value=positions_val,
            daily_return=0.0,
        )
        db.add(snapshot)
        db.commit()

        logger.info(
            "Rebalanced portfolio %s using %s: %d target positions",
            portfolio.name,
            method.value,
            len(target_weights.weights),
        )
        return target_weights
