"""Redis cache helpers for cheatsheets.

Provides optional caching layer that operates seamlessly whether Redis
is available or not. All operations are no-ops when Redis is unavailable.
"""

import json
import logging

import redis.asyncio as redis
from redis.exceptions import RedisError

from config import get_settings

logger = logging.getLogger(__name__)


class _RedisCache:
    """Internal Redis cache manager with connection state tracking."""

    def __init__(self):
        self._client: redis.Redis | None = None
        self._unavailable: bool = False

    async def get_client(self) -> redis.Redis | None:
        """Get Redis client, returning None if unavailable."""
        if self._unavailable:
            return None

        if self._client is None:
            try:
                settings = get_settings()
                self._client = await redis.from_url(settings.REDIS_URL, decode_responses=True)
                await self._client.ping()
                logger.info("Redis cache connected")
            except Exception:
                self._unavailable = True
                self._client = None
                logger.info("Redis unavailable - caching disabled")
                return None

        return self._client

    async def _execute(self, func) -> None:
        """Execute Redis operation, handling disconnects gracefully."""
        client = await self.get_client()
        if not client:
            return None

        try:
            return await func(client)
        except RedisError:
            self._unavailable = True
            self._client = None
            logger.info("Redis connection lost - caching disabled")
            return None

    async def get(self, player_id: str) -> dict | None:
        """Get cheatsheet from cache."""

        async def _get(client: redis.Redis):
            value = await client.get(f"cs:{player_id}")
            return json.loads(value) if value else None

        return await self._execute(_get)

    async def set(self, player_id: str, data: dict, ttl: int = 3600) -> None:
        """Set cheatsheet in cache with TTL."""

        async def _set(client: redis.Redis):
            await client.set(f"cs:{player_id}", json.dumps(data), ex=ttl)

        await self._execute(_set)

    async def invalidate(self, player_id: str) -> None:
        """Invalidate cheatsheet cache for player."""

        async def _delete(client: redis.Redis):
            await client.delete(f"cs:{player_id}")

        await self._execute(_delete)

    async def close(self) -> None:
        """Close Redis connection."""
        if self._client:
            try:
                await self._client.aclose()
            except Exception:
                pass  # Closing - errors don't matter
            finally:
                self._client = None
        self._unavailable = False


_cache = _RedisCache()


# Public API - maintains backward compatibility
async def get_redis() -> redis.Redis | None:
    """Get Redis client. Returns None if unavailable."""
    return await _cache.get_client()


async def cache_get(player_id: str) -> dict | None:
    """Get cheatsheet from cache. Returns None on miss or unavailable."""
    return await _cache.get(player_id)


async def cache_set(player_id: str, data: dict, ttl: int = 3600) -> None:
    """Set cheatsheet in cache with TTL. No-op if unavailable."""
    await _cache.set(player_id, data, ttl)


async def cache_invalidate(player_id: str) -> None:
    """Invalidate cheatsheet cache for player. No-op if unavailable."""
    await _cache.invalidate(player_id)


async def close_redis() -> None:
    """Close Redis connection on app shutdown."""
    await _cache.close()
