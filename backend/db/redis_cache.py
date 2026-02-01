"""Redis cache helpers for cheatsheets."""
import json
from typing import Optional

import redis.asyncio as redis

from config import get_settings

_redis_client: Optional[redis.Redis] = None


async def get_redis() -> Optional[redis.Redis]:
    """Get or create Redis client. Returns None if unavailable."""
    global _redis_client
    if _redis_client is None:
        try:
            settings = get_settings()
            _redis_client = await redis.from_url(settings.REDIS_URL, decode_responses=True)
            await _redis_client.ping()
        except Exception as exc:
            print(f"Redis unavailable: {exc}. Using SQLite only.")
            _redis_client = None
            return None
    return _redis_client


async def cache_get(player_id: str) -> Optional[dict]:
    """Get cheatsheet from cache. Returns None on miss or error."""
    try:
        client = await get_redis()
        if not client:
            return None
        value = await client.get(f"cs:{player_id}")
        return json.loads(value) if value else None
    except Exception:
        return None


async def cache_set(player_id: str, data: dict, ttl: int = 3600) -> None:
    """Set cheatsheet in cache with TTL."""
    try:
        client = await get_redis()
        if client:
            await client.set(f"cs:{player_id}", json.dumps(data), ex=ttl)
    except Exception:
        pass


async def cache_invalidate(player_id: str) -> None:
    """Invalidate cheatsheet cache for player."""
    try:
        client = await get_redis()
        if client:
            await client.delete(f"cs:{player_id}")
    except Exception:
        pass


async def close_redis() -> None:
    """Close Redis connection on app shutdown."""
    global _redis_client
    if _redis_client:
        try:
            await _redis_client.aclose()
        except Exception:
            pass
        finally:
            _redis_client = None
