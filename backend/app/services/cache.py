"""Redis-based async cache service."""

from __future__ import annotations

import asyncio
import functools
import json
import logging
from collections.abc import Callable, Coroutine
from typing import Any, Optional, TypeVar

import redis.asyncio as aioredis

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

F = TypeVar("F", bound=Callable[..., Coroutine[Any, Any, Any]])

_redis_client: Optional[aioredis.Redis] = None


async def get_redis_client() -> aioredis.Redis:
    """Return (or lazily create) the shared async Redis client."""
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True,
            health_check_interval=30,
        )
        logger.info("Redis client initialised", extra={"url": settings.REDIS_URL})
    return _redis_client


class RedisCache:
    """
    Thin async wrapper around the Redis client.

    All values are JSON-serialised so that arbitrary Python objects can be
    stored without a pickle dependency.
    """

    def __init__(self, default_ttl: int = settings.REDIS_CACHE_EXPIRY) -> None:
        self.default_ttl = default_ttl

    async def _client(self) -> aioredis.Redis:
        return await get_redis_client()

    async def get(self, key: str) -> Optional[Any]:
        """
        Return the cached value for *key*, or ``None`` if missing / expired.
        """
        try:
            client = await self._client()
            raw = await client.get(key)
            if raw is None:
                return None
            return json.loads(raw)
        except Exception as exc:
            logger.warning("Cache GET error", extra={"key": key, "error": str(exc)})
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> bool:
        """
        Store *value* under *key* with an optional TTL (seconds).

        Returns ``True`` on success, ``False`` on error.
        """
        try:
            client = await self._client()
            serialised = json.dumps(value, default=str)
            effective_ttl = ttl if ttl is not None else self.default_ttl
            await client.set(key, serialised, ex=effective_ttl)
            return True
        except Exception as exc:
            logger.warning("Cache SET error", extra={"key": key, "error": str(exc)})
            return False

    async def delete(self, key: str) -> bool:
        """Remove a key from the cache."""
        try:
            client = await self._client()
            await client.delete(key)
            return True
        except Exception as exc:
            logger.warning("Cache DELETE error", extra={"key": key, "error": str(exc)})
            return False

    async def exists(self, key: str) -> bool:
        """Return ``True`` if the key exists in the cache."""
        try:
            client = await self._client()
            return bool(await client.exists(key))
        except Exception:
            return False

    async def get_or_set(
        self,
        key: str,
        factory: Callable[[], Coroutine[Any, Any, Any]],
        ttl: Optional[int] = None,
    ) -> Any:
        """
        Return the cached value for *key*, or call *factory* to produce it,
        store the result, and return it.

        Args:
            key:     Cache key.
            factory: Async callable that produces the value on cache miss.
            ttl:     Optional TTL in seconds.
        """
        cached = await self.get(key)
        if cached is not None:
            return cached

        value = await factory()
        await self.set(key, value, ttl=ttl)
        return value

    async def invalidate_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching *pattern* (supports Redis glob syntax).

        Returns the number of keys deleted.
        """
        try:
            client = await self._client()
            deleted = 0
            async for key in client.scan_iter(match=pattern, count=100):
                await client.delete(key)
                deleted += 1
            logger.info(
                "Cache invalidated by pattern",
                extra={"pattern": pattern, "deleted": deleted},
            )
            return deleted
        except Exception as exc:
            logger.warning(
                "Cache invalidate_pattern error",
                extra={"pattern": pattern, "error": str(exc)},
            )
            return 0

    async def ping(self) -> bool:
        """Return True when Redis is reachable."""
        try:
            client = await self._client()
            return await client.ping()
        except Exception:
            return False

    async def close(self) -> None:
        """Close the Redis connection gracefully."""
        global _redis_client
        if _redis_client is not None:
            await _redis_client.aclose()
            _redis_client = None


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

cache = RedisCache()


# ---------------------------------------------------------------------------
# Decorator
# ---------------------------------------------------------------------------


def cache_decorator(
    key_prefix: str,
    ttl: Optional[int] = None,
    key_builder: Optional[Callable[..., str]] = None,
) -> Callable[[F], F]:
    """
    Decorator that caches the return value of an async function in Redis.

    Usage::

        @cache_decorator(key_prefix="user_profile", ttl=300)
        async def get_user_profile(user_id: str) -> dict:
            ...

    The default key is ``{key_prefix}:{arg0}:{arg1}:...``.
    Supply *key_builder* to customise key construction.
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            if key_builder is not None:
                cache_key = key_builder(*args, **kwargs)
            else:
                parts = [key_prefix] + [str(a) for a in args]
                parts += [f"{k}={v}" for k, v in sorted(kwargs.items())]
                cache_key = ":".join(parts)

            cached = await cache.get(cache_key)
            if cached is not None:
                logger.debug("Cache hit", extra={"key": cache_key})
                return cached

            result = await func(*args, **kwargs)
            await cache.set(cache_key, result, ttl=ttl)
            return result

        return wrapper  # type: ignore

    return decorator
