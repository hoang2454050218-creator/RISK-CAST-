"""
Redis Cache Module - Production-grade caching layer.

Provides:
- Async Redis client with connection pooling
- Typed cache operations
- Automatic serialization/deserialization
- Cache key namespacing
- TTL management
- Health checks
- Graceful degradation
"""

import json
import asyncio
from typing import Optional, Any, TypeVar, Generic, Callable
from datetime import timedelta
from functools import wraps
import hashlib

import structlog
from pydantic import BaseModel

from app.core.config import settings

logger = structlog.get_logger(__name__)

T = TypeVar("T")


# ============================================================================
# REDIS CLIENT
# ============================================================================


class RedisCache:
    """
    Production Redis cache client.
    
    Features:
    - Connection pooling
    - Automatic reconnection
    - Graceful degradation on failure
    - Namespace support
    - JSON serialization
    """
    
    def __init__(
        self,
        url: str = None,
        namespace: str = "riskcast",
        default_ttl: int = 300,
        max_connections: int = 50,
    ):
        self._url = url or settings.redis_url
        self._namespace = namespace
        self._default_ttl = default_ttl
        self._max_connections = max_connections
        self._client = None
        self._pool = None
        self._connected = False
        self._lock = asyncio.Lock()
    
    async def connect(self) -> bool:
        """Connect to Redis."""
        if self._connected:
            return True
        
        async with self._lock:
            if self._connected:
                return True
            
            try:
                import redis.asyncio as redis
                
                self._pool = redis.ConnectionPool.from_url(
                    self._url,
                    max_connections=self._max_connections,
                    decode_responses=True,
                )
                self._client = redis.Redis(connection_pool=self._pool)
                
                # Test connection
                await self._client.ping()
                
                self._connected = True
                logger.info("redis_connected", url=self._url[:20] + "...")
                return True
                
            except Exception as e:
                logger.warning("redis_connection_failed", error=str(e))
                self._connected = False
                return False
    
    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self._client:
            await self._client.close()
        if self._pool:
            await self._pool.disconnect()
        self._connected = False
        logger.info("redis_disconnected")
    
    async def health_check(self) -> dict:
        """Check Redis health."""
        try:
            if not self._connected:
                await self.connect()
            
            if self._client:
                await self._client.ping()
                info = await self._client.info("memory")
                return {
                    "status": "healthy",
                    "connected": True,
                    "used_memory": info.get("used_memory_human", "unknown"),
                }
        except Exception as e:
            return {
                "status": "unhealthy",
                "connected": False,
                "error": str(e),
            }
    
    def _key(self, key: str) -> str:
        """Generate namespaced key."""
        return f"{self._namespace}:{key}"
    
    async def get(self, key: str) -> Optional[str]:
        """Get value from cache."""
        if not self._connected:
            if not await self.connect():
                return None
        
        try:
            value = await self._client.get(self._key(key))
            if value:
                logger.debug("cache_hit", key=key)
            else:
                logger.debug("cache_miss", key=key)
            return value
        except Exception as e:
            logger.warning("cache_get_error", key=key, error=str(e))
            return None
    
    async def set(
        self,
        key: str,
        value: str,
        ttl: Optional[int] = None,
    ) -> bool:
        """Set value in cache."""
        if not self._connected:
            if not await self.connect():
                return False
        
        try:
            ttl = ttl or self._default_ttl
            await self._client.setex(self._key(key), ttl, value)
            logger.debug("cache_set", key=key, ttl=ttl)
            return True
        except Exception as e:
            logger.warning("cache_set_error", key=key, error=str(e))
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        if not self._connected:
            return False
        
        try:
            await self._client.delete(self._key(key))
            logger.debug("cache_delete", key=key)
            return True
        except Exception as e:
            logger.warning("cache_delete_error", key=key, error=str(e))
            return False
    
    async def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern."""
        if not self._connected:
            return 0
        
        try:
            keys = await self._client.keys(self._key(pattern))
            if keys:
                count = await self._client.delete(*keys)
                logger.info("cache_delete_pattern", pattern=pattern, count=count)
                return count
            return 0
        except Exception as e:
            logger.warning("cache_delete_pattern_error", pattern=pattern, error=str(e))
            return 0
    
    async def get_json(self, key: str) -> Optional[dict]:
        """Get JSON value from cache."""
        value = await self.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                logger.warning("cache_json_decode_error", key=key)
                return None
        return None
    
    async def set_json(
        self,
        key: str,
        value: dict,
        ttl: Optional[int] = None,
    ) -> bool:
        """Set JSON value in cache."""
        try:
            json_str = json.dumps(value, default=str)
            return await self.set(key, json_str, ttl)
        except Exception as e:
            logger.warning("cache_json_encode_error", key=key, error=str(e))
            return False
    
    async def get_model(self, key: str, model_class: type[T]) -> Optional[T]:
        """Get Pydantic model from cache."""
        data = await self.get_json(key)
        if data:
            try:
                return model_class(**data)
            except Exception as e:
                logger.warning("cache_model_parse_error", key=key, error=str(e))
                return None
        return None
    
    async def set_model(
        self,
        key: str,
        model: BaseModel,
        ttl: Optional[int] = None,
    ) -> bool:
        """Set Pydantic model in cache."""
        try:
            json_str = model.model_dump_json()
            return await self.set(key, json_str, ttl)
        except Exception as e:
            logger.warning("cache_model_encode_error", key=key, error=str(e))
            return False
    
    async def incr(self, key: str, amount: int = 1) -> Optional[int]:
        """Increment counter."""
        if not self._connected:
            if not await self.connect():
                return None
        
        try:
            return await self._client.incrby(self._key(key), amount)
        except Exception as e:
            logger.warning("cache_incr_error", key=key, error=str(e))
            return None
    
    async def expire(self, key: str, ttl: int) -> bool:
        """Set expiration on key."""
        if not self._connected:
            return False
        
        try:
            return await self._client.expire(self._key(key), ttl)
        except Exception as e:
            logger.warning("cache_expire_error", key=key, error=str(e))
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        if not self._connected:
            return False
        
        try:
            return await self._client.exists(self._key(key)) > 0
        except Exception as e:
            return False


# ============================================================================
# RATE LIMITER (Redis-backed)
# ============================================================================


class RedisRateLimiter:
    """
    Production-grade rate limiter using Redis.
    
    Implements sliding window algorithm for accurate rate limiting.
    """
    
    def __init__(self, cache: RedisCache):
        self._cache = cache
    
    async def is_allowed(
        self,
        key: str,
        limit: int,
        window_seconds: int = 60,
    ) -> tuple[bool, int, int]:
        """
        Check if request is allowed.
        
        Returns:
            Tuple of (allowed, remaining, reset_seconds)
        """
        if not self._cache._connected:
            # Fail open if Redis is down
            return True, limit - 1, window_seconds
        
        try:
            import time
            
            now = time.time()
            window_start = now - window_seconds
            rate_key = f"rate:{key}"
            
            # Use Redis pipeline for atomic operations
            pipe = self._cache._client.pipeline()
            
            # Remove old entries
            pipe.zremrangebyscore(
                self._cache._key(rate_key),
                "-inf",
                window_start,
            )
            
            # Count current entries
            pipe.zcard(self._cache._key(rate_key))
            
            # Add current request
            pipe.zadd(
                self._cache._key(rate_key),
                {str(now): now},
            )
            
            # Set expiration
            pipe.expire(self._cache._key(rate_key), window_seconds)
            
            results = await pipe.execute()
            current_count = results[1]
            
            if current_count >= limit:
                # Get oldest entry to calculate reset time
                oldest = await self._cache._client.zrange(
                    self._cache._key(rate_key), 0, 0, withscores=True
                )
                if oldest:
                    reset_at = oldest[0][1] + window_seconds
                    reset_seconds = max(1, int(reset_at - now))
                else:
                    reset_seconds = window_seconds
                
                return False, 0, reset_seconds
            
            remaining = limit - current_count - 1
            return True, remaining, window_seconds
            
        except Exception as e:
            logger.warning("rate_limit_error", key=key, error=str(e))
            # Fail open
            return True, limit - 1, window_seconds


# ============================================================================
# IDEMPOTENCY STORE (Redis-backed)
# ============================================================================


class RedisIdempotencyStore:
    """
    Redis-backed idempotency store.
    
    Prevents duplicate operations within a time window.
    """
    
    def __init__(self, cache: RedisCache, ttl_seconds: int = 86400):
        self._cache = cache
        self._ttl = ttl_seconds
    
    async def check_and_set(
        self,
        idempotency_key: str,
        customer_id: str,
    ) -> Optional[dict]:
        """
        Check if request was already processed.
        
        Returns:
            Previous response if exists, None if new request
        """
        full_key = f"idempotency:{customer_id}:{idempotency_key}"
        
        # Try to get existing
        existing = await self._cache.get_json(full_key)
        if existing:
            logger.info(
                "idempotency_hit",
                key=idempotency_key,
                customer_id=customer_id,
            )
            return existing.get("response")
        
        # Mark as processing
        await self._cache.set_json(
            full_key,
            {"status": "processing", "response": None},
            ttl=self._ttl,
        )
        
        return None
    
    async def set_response(
        self,
        idempotency_key: str,
        customer_id: str,
        response: dict,
    ) -> None:
        """Store the response for an idempotency key."""
        full_key = f"idempotency:{customer_id}:{idempotency_key}"
        await self._cache.set_json(
            full_key,
            {"status": "completed", "response": response},
            ttl=self._ttl,
        )


# ============================================================================
# CACHE DECORATOR
# ============================================================================


def cached(
    ttl: int = 300,
    key_prefix: str = "",
    key_builder: Optional[Callable[..., str]] = None,
):
    """
    Decorator for caching function results.
    
    Usage:
        @cached(ttl=600, key_prefix="user")
        async def get_user(user_id: str):
            ...
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            cache = get_cache()
            
            # Build cache key
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                key_parts = [key_prefix or func.__name__]
                key_parts.extend(str(a) for a in args)
                key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
                cache_key = ":".join(key_parts)
            
            # Try cache
            cached_value = await cache.get_json(cache_key)
            if cached_value is not None:
                return cached_value
            
            # Call function
            result = await func(*args, **kwargs)
            
            # Cache result
            if result is not None:
                await cache.set_json(cache_key, result, ttl=ttl)
            
            return result
        
        return wrapper
    return decorator


# ============================================================================
# GLOBAL INSTANCE
# ============================================================================


_cache: Optional[RedisCache] = None
_rate_limiter: Optional[RedisRateLimiter] = None
_idempotency_store: Optional[RedisIdempotencyStore] = None


async def init_cache() -> RedisCache:
    """Initialize global cache instance."""
    global _cache, _rate_limiter, _idempotency_store
    
    _cache = RedisCache(
        url=settings.redis_url,
        namespace="riskcast",
        default_ttl=300,
        max_connections=settings.redis_max_connections,
    )
    await _cache.connect()
    
    _rate_limiter = RedisRateLimiter(_cache)
    _idempotency_store = RedisIdempotencyStore(_cache)
    
    return _cache


async def close_cache() -> None:
    """Close cache connection."""
    global _cache
    if _cache:
        await _cache.disconnect()
        _cache = None


def get_cache() -> RedisCache:
    """Get global cache instance."""
    global _cache
    if _cache is None:
        _cache = RedisCache()
    return _cache


def get_rate_limiter() -> RedisRateLimiter:
    """Get global rate limiter."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RedisRateLimiter(get_cache())
    return _rate_limiter


def get_idempotency_store() -> RedisIdempotencyStore:
    """Get global idempotency store."""
    global _idempotency_store
    if _idempotency_store is None:
        _idempotency_store = RedisIdempotencyStore(get_cache())
    return _idempotency_store
