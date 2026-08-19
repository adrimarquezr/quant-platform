"""
Integration tests for SQLAlchemy ORM models and Database Session.
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.infrastructure.database.models import (
    AssetORM,
    Base,
    PortfolioORM,
    PositionORM,
    StrategyORM,
    StrategyVersionORM,
)


@pytest.fixture
def in_memory_db() -> Session:
    """Create an in-memory SQLite database for testing ORM mapping."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.mark.integration
class TestDatabaseORM:
    """Test ORM models CRUD operations in SQLite in-memory DB."""

    def test_create_and_query_asset(self, in_memory_db: Session) -> None:
        asset = AssetORM(
            symbol="SPY",
            name="SPDR S&P 500 ETF Trust",
            asset_class="etf",
            exchange="NYSE",
            currency="USD",
            sector="broad_market",
        )
        in_memory_db.add(asset)
        in_memory_db.commit()

        queried = in_memory_db.query(AssetORM).filter_by(symbol="SPY").first()
        assert queried is not None
        assert queried.name == "SPDR S&P 500 ETF Trust"
        assert queried.is_active is True

    def test_create_strategy_with_version(self, in_memory_db: Session) -> None:
        strategy = StrategyORM(
            name="momentum",
            description="Time-series momentum",
            category="momentum",
        )
        in_memory_db.add(strategy)
        in_memory_db.commit()

        version = StrategyVersionORM(
            strategy_id=strategy.id,
            version="1.0.0",
            code_hash="abc123hash",
            default_parameters={"lookback_period": 20},
        )
        in_memory_db.add(version)
        in_memory_db.commit()

        queried_strat = in_memory_db.query(StrategyORM).filter_by(name="momentum").first()
        assert queried_strat is not None
        assert len(queried_strat.versions) == 1
        assert queried_strat.versions[0].version == "1.0.0"

    def test_create_portfolio_and_positions(self, in_memory_db: Session) -> None:
        asset = AssetORM(symbol="SPY", name="SPDR S&P 500 ETF Trust", asset_class="etf")
        portfolio = PortfolioORM(name="Test Portfolio", cash=100000.0, total_value=100000.0)
        in_memory_db.add_all([asset, portfolio])
        in_memory_db.commit()

        position = PositionORM(
            portfolio_id=portfolio.id,
            asset_id=asset.id,
            quantity=100.0,
            avg_entry_price=400.0,
            current_price=410.0,
            market_value=41000.0,
            unrealized_pnl=1000.0,
        )
        in_memory_db.add(position)
        in_memory_db.commit()

        queried_port = in_memory_db.query(PortfolioORM).filter_by(name="Test Portfolio").first()
        assert queried_port is not None
        assert len(queried_port.positions) == 1
        assert queried_port.positions[0].quantity == 100.0
