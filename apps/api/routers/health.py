"""
Health Router — Service health and readiness endpoints.
"""

from __future__ import annotations

from fastapi import APIRouter

from apps.api.schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Check if the service is healthy and responsive."""
    return HealthResponse()
