"""Cache management endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from cache.cache import DeduplicationCache
from dependencies import get_cache

router = APIRouter(prefix="/cache", tags=["cache"])


@router.delete(
    "",
    summary="Clear Deduplication & Result Cache",
    description="Flushes all stored entries from the Redis or in-memory cache, including deduplication records and aggregated search results.",
)
async def clear_cache(cache: DeduplicationCache = Depends(get_cache)) -> dict[str, Any]:
    count = cache.size()
    cache.clear()
    return {"cleared": count, "message": f"Removed {count} seen URLs"}


@router.get(
    "/stats",
    summary="Get Cache Stats",
    description="Returns metrics on the deduplication cache, including the number of tracked URLs and the timestamp of the oldest cache entry.",
)
async def cache_stats(cache: DeduplicationCache = Depends(get_cache)) -> dict[str, Any]:
    return {"seen_urls": cache.size(), "oldest_entry": cache.oldest()}
