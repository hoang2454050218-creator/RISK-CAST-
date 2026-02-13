"""
Redis Cache Service.

Caches hot data to reduce DB load:
- Active signals (per company, TTL 5 min)
- Morning briefs (per company, TTL 30 min)
- Signal summaries (per company, TTL 2 min)

Uses JSON serialization. Graceful degradation if Redis is unavailable.
"""

import json
from typing import Any, Optional

import structlog

from riskcast.config import settings

logger = structlog.get_logger(__name__)

_redis = None


async def get_redis():
    """Lazy-init Redis connection."""
    global _redis
    if _redis is None:
        try:
            import redis.asyncio as aioredis

            _redis = aioredis.from_url(
                settings.redis_url,
                decode_responses=True,
                socket_connect_timeout=3,
            )
            await _redis.ping()
            logger.info("redis_connected")
        except Exception as e:
            logger.warning("redis_unavailable", error=str(e))
            _redis = None
    return _redis


async def cache_get(key: str) -> Optional[Any]:
    """Get from cache. Returns None if miss or Redis unavailable."""
    try:
        r = await get_redis()
        if r is None:
            return None
        val = await r.get(key)
        return json.loads(val) if val else None
    except Exception:
        return None


async def cache_set(key: str, value: Any, ttl_seconds: int = 300) -> bool:
    """Set cache with TTL. Returns False if failed."""
    try:
        r = await get_redis()
        if r is None:
            return False
        await r.set(key, json.dumps(value, ensure_ascii=False, default=str), ex=ttl_seconds)
        return True
    except Exception:
        return False


async def cache_delete(pattern: str) -> int:
    """Delete keys matching pattern. Returns count deleted."""
    try:
        r = await get_redis()
        if r is None:
            return 0
        keys = []
        async for key in r.scan_iter(match=pattern):
            keys.append(key)
        if keys:
            return await r.delete(*keys)
        return 0
    except Exception:
        return 0


async def close_redis():
    """Close Redis connection."""
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None


# ── Cache key builders ───────────────────────────────────────────────────


def signals_key(company_id: str) -> str:
    return f"v2:signals:{company_id}"


def signals_summary_key(company_id: str) -> str:
    return f"v2:signals_summary:{company_id}"


def brief_key(company_id: str, date: str) -> str:
    return f"v2:brief:{company_id}:{date}"


# ── Cache TTLs ───────────────────────────────────────────────────────────

SIGNALS_TTL = 300       # 5 minutes
SUMMARY_TTL = 120       # 2 minutes
BRIEF_TTL = 1800        # 30 minutes
