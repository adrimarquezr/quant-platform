"""
Strategies Router — Strategy discovery and parameter schema inspection.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from src.strategies.mean_reversion import MeanReversionStrategy
from src.strategies.momentum import MomentumStrategy

router = APIRouter(prefix="/strategies", tags=["strategies"])

STRATEGIES = {
    "momentum": MomentumStrategy(),
    "mean_reversion": MeanReversionStrategy(),
}


@router.get("", response_model=list[dict])
async def list_registered_strategies() -> list[dict]:
    """List all available systematic quantitative strategies."""
    return [
        {
            "name": s.name,
            "version": s.version,
            "category": "momentum" if "momentum" in s.name else "mean_reversion",
            "parameter_schema": s.get_parameter_schema(),
        }
        for s in STRATEGIES.values()
    ]


@router.get("/{strategy_name}/schema", response_model=dict)
async def get_strategy_schema(strategy_name: str) -> dict:
    """Retrieve parameter configuration schema for a specific strategy."""
    strategy = STRATEGIES.get(strategy_name)
    if strategy is None:
        raise HTTPException(
            status_code=404,
            detail=f"Strategy '{strategy_name}' not found. Available: {list(STRATEGIES.keys())}",
        )
    return {
        "strategy_name": strategy.name,
        "version": strategy.version,
        "parameters": strategy.get_parameter_schema(),
    }
