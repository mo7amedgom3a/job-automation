"""Redis-backed deduplication cache with an in-memory fallback."""

from __future__ import annotations

import hashlib
import logging
import os
import time
from typing import Optional

try:
    import redis
except ImportError:  # pragma: no cover - only used when dependency is absent.
    redis = None

logger = logging.getLogger(__name__)


class DeduplicationCache:
    """URL deduplication cache backed by Redis when available."""

    def __init__(
        self,
        ttl_seconds: int | None = None,
        redis_url: str | None = None,
        namespace: str = "jobs:seen",
    ) -> None:
        self.ttl = ttl_seconds or int(os.getenv("CACHE_TTL_SECONDS", str(7 * 24 * 3600)))
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://redis:6379/0")
        self.namespace = namespace
        self._store: dict[str, float] = {}
        self._store_val: dict[str, tuple[str, float]] = {}
        self._redis = self._connect_redis()

    def get_value(self, key: str) -> str | None:
        if self._redis is not None:
            return self._redis.get(key)

        entry = self._store_val.get(key)
        if entry is None:
            return None
        val, expiry = entry
        if time.time() > expiry:
            del self._store_val[key]
            return None
        return val

    def set_value(self, key: str, value: str, ttl: int) -> None:
        if self._redis is not None:
            self._redis.setex(key, ttl, value)
            return
        self._store_val[key] = (value, time.time() + ttl)

    def delete(self, key: str) -> None:
        if self._redis is not None:
            self._redis.delete(key)
            return
        if key in self._store_val:
            del self._store_val[key]

    def is_seen(self, url: str) -> bool:
        key = self._key(url)
        if self._redis is not None:
            return bool(self._redis.exists(key))

        entry = self._store.get(key)
        if entry is None:
            return False
        if time.time() - entry > self.ttl:
            del self._store[key]
            return False
        return True

    def mark_seen(self, url: str) -> None:
        key = self._key(url)
        if self._redis is not None:
            self._redis.setex(key, self.ttl, str(int(time.time())))
            return
        self._store[key] = time.time()

    def clear(self) -> None:
        if self._redis is not None:
            cursor = 0
            pattern = f"{self.namespace}:*"
            while True:
                cursor, keys = self._redis.scan(cursor=cursor, match=pattern, count=500)
                if keys:
                    self._redis.delete(*keys)
                if cursor == 0:
                    break
            return
        self._store.clear()

    def size(self) -> int:
        if self._redis is not None:
            cursor = 0
            total = 0
            pattern = f"{self.namespace}:*"
            while True:
                cursor, keys = self._redis.scan(cursor=cursor, match=pattern, count=500)
                total += len(keys)
                if cursor == 0:
                    return total

        self._evict_expired()
        return len(self._store)

    def oldest(self) -> Optional[str]:
        if self._redis is not None:
            cursor = 0
            oldest_ts: int | None = None
            pattern = f"{self.namespace}:*"
            while True:
                cursor, keys = self._redis.scan(cursor=cursor, match=pattern, count=500)
                for key in keys:
                    value = self._redis.get(key)
                    if value is None:
                        continue
                    ts = int(value)
                    oldest_ts = ts if oldest_ts is None else min(oldest_ts, ts)
                if cursor == 0:
                    break
            if oldest_ts is None:
                return None
            return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(oldest_ts))

        if not self._store:
            return None
        oldest_ts = min(self._store.values())
        return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(oldest_ts))

    def _key(self, url: str) -> str:
        digest = hashlib.md5(url.strip().lower().encode()).hexdigest()
        return f"{self.namespace}:{digest}"

    def _evict_expired(self) -> None:
        now = time.time()
        stale = [k for k, v in self._store.items() if now - v > self.ttl]
        for k in stale:
            del self._store[k]

    def _connect_redis(self):
        if redis is None:
            logger.warning("redis package is not installed; using in-memory cache fallback.")
            return None
        try:
            client = redis.Redis.from_url(self.redis_url, decode_responses=True)
            client.ping()
            logger.info("Connected to Redis cache at %s", self.redis_url)
            return client
        except Exception as exc:
            if os.getenv("CACHE_REQUIRE_REDIS", "false").lower() == "true":
                raise
            logger.warning("Redis cache unavailable (%s); using in-memory cache fallback.", exc)
            return None
