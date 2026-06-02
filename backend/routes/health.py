"""Health and readiness endpoints."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    summary="Health & Readiness Check",
    description="Simple health probe that reports readiness of the service and the current server UTC time.",
)
async def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "job-aggregator-service",
        "time": datetime.utcnow().isoformat(),
    }
