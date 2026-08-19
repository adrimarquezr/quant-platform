"""
Database session management — SQLAlchemy engine and session factory.
"""

from __future__ import annotations

import os
from collections.abc import Generator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.infrastructure.database.models import Base

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://quant_user:change_me_in_production@localhost:5432/quant_platform",
)


def get_engine(url: str | None = None) -> Engine:
    """Create a SQLAlchemy engine."""
    return create_engine(
        url or DATABASE_URL,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        echo=False,
    )


engine = get_engine()
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency — yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db(url: str | None = None) -> None:
    """Create all tables. Used for development and testing."""
    target_engine = get_engine(url) if url else engine
    Base.metadata.create_all(bind=target_engine)
