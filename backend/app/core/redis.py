from __future__ import annotations

import json
import logging
from typing import Any

import redis.asyncio as aioredis
from fastapi import HTTPException, status

from app.core.config import settings

logger = logging.getLogger(__name__)


class ServiceUnavailableException(HTTPException):
    """Raised when Redis is unreachable or experiencing connection issues."""
    
    def __init__(self, detail: str = "Cache service temporarily unavailable"):
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=detail
        )


# ---------------------------------------------------------------------------
# Singleton client
# ---------------------------------------------------------------------------
_redis_client: aioredis.Redis | None = None


async def init_redis() -> aioredis.Redis:
    """Create (or return the existing) Redis connection pool.

    Called once during application startup via the lifespan handler.
    """
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
        # Verify the connection is reachable at startup
        await _redis_client.ping()
        logger.info("Redis connection established: %s", settings.REDIS_URL)
    return _redis_client


async def close_redis() -> None:
    """Close the Redis connection pool (call on app shutdown)."""
    global _redis_client
    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None
        logger.info("Redis connection closed")


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------
async def get_redis() -> aioredis.Redis:
    """Return the shared Redis client.

    Raises RuntimeError if init_redis() was never called (i.e. the lifespan
    handler was not wired up correctly).
    """
    if _redis_client is None:
        # Lazy initialisation as a fallback — avoids hard failures in tests
        return await init_redis()
    return _redis_client


# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------
async def set_cache(
    redis: aioredis.Redis,
    key: str,
    value: Any,
    ttl: int = settings.CACHE_TTL,
) -> None:
    """Serialise *value* to JSON and store it under *key* with a TTL.

    Args:
        redis: The Redis client (inject via ``Depends(get_redis)``).
        key:   Cache key string.
        value: Any JSON-serialisable Python object.
        ttl:   Time-to-live in seconds (default: ``settings.CACHE_TTL``).
    """
    try:
        serialised = json.dumps(value, default=str)
        await redis.set(key, serialised, ex=ttl)
    except (aioredis.ConnectionError, aioredis.TimeoutError) as exc:
        # Connection errors should be logged but not crash the request
        logger.error("Redis connection error during set_cache for key=%r: %s", key, exc)
    except Exception as exc:
        # Other errors (serialization, etc.) should be logged as warnings
        logger.warning("set_cache failed for key=%r: %s", key, exc)


async def get_cache(redis: aioredis.Redis, key: str) -> Any | None:
    """Return the deserialised value for *key*, or ``None`` on a cache miss.

    Args:
        redis: The Redis client.
        key:   Cache key string.

    Returns:
        The deserialised Python object, or ``None`` if the key does not exist.

    Raises:
        ServiceUnavailableException: If Redis is unreachable (connection error).
        
    Notes:
        This function differentiates between:
        - Cache miss (key doesn't exist): returns None
        - Redis connection error: raises ServiceUnavailableException
        - Deserialization error: logs warning and returns None
    """
    try:
        raw = await redis.get(key)
        if raw is None:
            # Cache miss — key doesn't exist
            return None
        return json.loads(raw)
    except (aioredis.ConnectionError, aioredis.TimeoutError) as exc:
        # Redis is down or unreachable — raise exception to signal service degradation
        logger.error("Redis connection error during get_cache for key=%r: %s", key, exc)
        raise ServiceUnavailableException(
            detail="Cache service temporarily unavailable. Please try again."
        )
    except json.JSONDecodeError as exc:
        # Deserialization failed — log and treat as cache miss
        logger.warning("JSON decode error for key=%r: %s", key, exc)
        return None
    except Exception as exc:
        # Unexpected error — log and treat as cache miss to avoid breaking the request
        logger.warning("Unexpected error in get_cache for key=%r: %s", key, exc)
        return None


async def delete_cache(redis: aioredis.Redis, key: str) -> None:
    """Delete *key* from the cache.

    Args:
        redis: The Redis client.
        key:   Cache key string.
    """
    try:
        await redis.delete(key)
    except (aioredis.ConnectionError, aioredis.TimeoutError) as exc:
        logger.error("Redis connection error during delete_cache for key=%r: %s", key, exc)
    except Exception as exc:
        logger.warning("delete_cache failed for key=%r: %s", key, exc)
