"""
Deduplication Cache
Simple in-memory URL cache with TTL (default 7 days).
Swap the backend for Redis if you want persistence across restarts.
"""

import time
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class DeduplicationCache:
    """
    Thread-safe in-memory set of seen URLs with TTL expiry.
    All stored as (url_hash → timestamp) to keep memory low.
    """

    def __init__(self, ttl_seconds: int = 7 * 24 * 3600):  # 7 days
        self.ttl     = ttl_seconds
        self._store: dict[str, float] = {}   # hash → seen_at timestamp

    def is_seen(self, url: str) -> bool:
        key = self._key(url)
        entry = self._store.get(key)
        if entry is None:
            return False
        # Expire if too old
        if time.time() - entry > self.ttl:
            del self._store[key]
            return False
        return True

    def mark_seen(self, url: str):
        self._store[self._key(url)] = time.time()

    def clear(self):
        self._store.clear()

    def size(self) -> int:
        self._evict_expired()
        return len(self._store)

    def oldest(self) -> Optional[str]:
        if not self._store:
            return None
        oldest_ts = min(self._store.values())
        return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(oldest_ts))

    def _key(self, url: str) -> str:
        import hashlib
        return hashlib.md5(url.strip().lower().encode()).hexdigest()

    def _evict_expired(self):
        now   = time.time()
        stale = [k for k, v in self._store.items() if now - v > self.ttl]
        for k in stale:
            del self._store[k]
