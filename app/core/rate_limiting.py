"""
Distributed Rate Limiting with Redis.

Production-grade rate limiting with:
- Sliding window algorithm
- Redis-based distributed state
- Per-customer and per-endpoint limits
- Graceful degradation
- Metrics integration
"""

import time
from typing import Optional, Callable
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
from functools import wraps
from contextlib import asynccontextmanager

import redis.asyncio as redis
from pydantic import BaseModel, Field
import structlog

from app.core.config import settings
from app.core.metrics import METRICS

logger = structlog.get_logger(__name__)


# ============================================================================
# CONFIGURATION
# ============================================================================


class RateLimitConfig(BaseModel):
    """Rate limit configuration."""
    
    requests_per_minute: int = Field(default=60)
    requests_per_hour: int = Field(default=1000)
    requests_per_day: int = Field(default=10000)
    burst_size: int = Field(default=10)
    
    # Endpoint-specific overrides
    endpoint_limits: dict[str, int] = Field(default_factory=lambda: {
        "/api/v1/decisions/generate": 30,  # Lower limit for expensive ops
        "/api/v1/health": 1000,  # Higher limit for health checks
    })


class RateLimitResult(BaseModel):
    """Result of a rate limit check."""
    
    allowed: bool
    remaining: int
    limit: int
    reset_at: datetime
    retry_after_seconds: Optional[int] = None
    
    def to_headers(self) -> dict[str, str]:
        """Convert to HTTP headers."""
        headers = {
            "X-RateLimit-Limit": str(self.limit),
            "X-RateLimit-Remaining": str(max(0, self.remaining)),
            "X-RateLimit-Reset": str(int(self.reset_at.timestamp())),
        }
        if self.retry_after_seconds:
            headers["Retry-After"] = str(self.retry_after_seconds)
        return headers


# ============================================================================
# RATE LIMITER INTERFACE
# ============================================================================


class RateLimiter(ABC):
    """Abstract base class for rate limiters."""
    
    @abstractmethod
    async def check(
        self,
        key: str,
        limit: int = 60,
        window_seconds: int = 60,
    ) -> RateLimitResult:
        """Check if request is allowed."""
        pass
    
    @abstractmethod
    async def reset(self, key: str) -> None:
        """Reset rate limit for a key."""
        pass


# ============================================================================
# REDIS IMPLEMENTATION (Sliding Window)
# ============================================================================


class RedisRateLimiter(RateLimiter):
    """
    Redis-based distributed rate limiter using sliding window algorithm.
    
    Uses sorted sets to implement a sliding window:
    - Each request adds a timestamp to the set
    - Old timestamps outside the window are removed
    - Count of remaining timestamps determines rate
    
    This is more accurate than fixed window and handles edge cases better.
    """
    
    def __init__(
        self,
        redis_client: redis.Redis,
        key_prefix: str = "ratelimit:",
    ):
        self._redis = redis_client
        self._prefix = key_prefix
    
    def _make_key(self, key: str, window: str = "minute") -> str:
        """Create Redis key."""
        return f"{self._prefix}{window}:{key}"
    
    async def check(
        self,
        key: str,
        limit: int = 60,
        window_seconds: int = 60,
    ) -> RateLimitResult:
        """
        Check if request is allowed using sliding window.
        
        Args:
            key: Unique identifier (e.g., "customer:123" or "ip:1.2.3.4")
            limit: Max requests in window
            window_seconds: Window duration
        
        Returns:
            RateLimitResult with allowed status and metadata
        """
        now = time.time()
        window_start = now - window_seconds
        redis_key = self._make_key(key)
        
        pipe = self._redis.pipeline()
        
        try:
            # Remove old entries outside window
            pipe.zremrangebyscore(redis_key, "-inf", window_start)
            
            # Count current entries
            pipe.zcard(redis_key)
            
            # Add current request (timestamp as score and value)
            pipe.zadd(redis_key, {str(now): now})
            
            # Set expiry on the key
            pipe.expire(redis_key, window_seconds + 10)
            
            results = await pipe.execute()
            current_count = results[1]
            
            allowed = current_count < limit
            remaining = max(0, limit - current_count - 1)
            reset_at = datetime.utcnow() + timedelta(seconds=window_seconds)
            
            # Record metrics
            METRICS.rate_limit_checks.labels(
                key_type=key.split(":")[0] if ":" in key else "unknown",
                allowed=str(allowed).lower(),
            ).inc()
            
            if not allowed:
                # Calculate retry after
                oldest = await self._redis.zrange(redis_key, 0, 0, withscores=True)
                if oldest:
                    oldest_time = oldest[0][1]
                    retry_after = int(window_seconds - (now - oldest_time)) + 1
                else:
                    retry_after = window_seconds
                
                logger.warning(
                    "rate_limit_exceeded",
                    key=key,
                    limit=limit,
                    window_seconds=window_seconds,
                )
                
                return RateLimitResult(
                    allowed=False,
                    remaining=0,
                    limit=limit,
                    reset_at=reset_at,
                    retry_after_seconds=retry_after,
                )
            
            return RateLimitResult(
                allowed=True,
                remaining=remaining,
                limit=limit,
                reset_at=reset_at,
            )
        
        except redis.RedisError as e:
            # Graceful degradation - allow on Redis failure
            logger.error("rate_limit_redis_error", error=str(e), key=key)
            METRICS.rate_limit_errors.inc()
            
            return RateLimitResult(
                allowed=True,  # Fail open
                remaining=limit,
                limit=limit,
                reset_at=datetime.utcnow() + timedelta(seconds=window_seconds),
            )
    
    async def reset(self, key: str) -> None:
        """Reset rate limit for a key."""
        try:
            redis_key = self._make_key(key)
            await self._redis.delete(redis_key)
            logger.info("rate_limit_reset", key=key)
        except redis.RedisError as e:
            logger.error("rate_limit_reset_error", error=str(e), key=key)


# ============================================================================
# IN-MEMORY IMPLEMENTATION (for testing/fallback)
# ============================================================================


class InMemoryRateLimiter(RateLimiter):
    """In-memory rate limiter for testing and fallback."""
    
    def __init__(self):
        self._windows: dict[str, list[float]] = {}
    
    async def check(
        self,
        key: str,
        limit: int = 60,
        window_seconds: int = 60,
    ) -> RateLimitResult:
        """Check if request is allowed."""
        now = time.time()
        window_start = now - window_seconds
        
        # Initialize window
        if key not in self._windows:
            self._windows[key] = []
        
        # Remove old entries
        self._windows[key] = [
            t for t in self._windows[key] if t > window_start
        ]
        
        current_count = len(self._windows[key])
        allowed = current_count < limit
        
        if allowed:
            self._windows[key].append(now)
        
        remaining = max(0, limit - current_count - 1)
        reset_at = datetime.utcnow() + timedelta(seconds=window_seconds)
        
        if not allowed:
            retry_after = window_seconds
            if self._windows[key]:
                oldest = min(self._windows[key])
                retry_after = int(window_seconds - (now - oldest)) + 1
            
            return RateLimitResult(
                allowed=False,
                remaining=0,
                limit=limit,
                reset_at=reset_at,
                retry_after_seconds=retry_after,
            )
        
        return RateLimitResult(
            allowed=True,
            remaining=remaining,
            limit=limit,
            reset_at=reset_at,
        )
    
    async def reset(self, key: str) -> None:
        """Reset rate limit for a key."""
        self._windows.pop(key, None)


# ============================================================================
# MULTI-TIER RATE LIMITER
# ============================================================================


class MultiTierRateLimiter:
    """
    Multi-tier rate limiter with different windows.
    
    Checks multiple rate limits:
    - Per-minute: Burst protection
    - Per-hour: Sustained usage
    - Per-day: Quota management
    """
    
    def __init__(
        self,
        limiter: RateLimiter,
        config: Optional[RateLimitConfig] = None,
    ):
        self._limiter = limiter
        self._config = config or RateLimitConfig()
    
    async def check(
        self,
        key: str,
        endpoint: Optional[str] = None,
    ) -> RateLimitResult:
        """
        Check all rate limit tiers.
        
        Args:
            key: Rate limit key (e.g., customer ID)
            endpoint: Optional endpoint for specific limits
        
        Returns:
            Most restrictive RateLimitResult
        """
        # Get endpoint-specific limit or default
        minute_limit = self._config.requests_per_minute
        if endpoint and endpoint in self._config.endpoint_limits:
            minute_limit = self._config.endpoint_limits[endpoint]
        
        # Check each tier
        checks = [
            (f"{key}:minute", minute_limit, 60),
            (f"{key}:hour", self._config.requests_per_hour, 3600),
            (f"{key}:day", self._config.requests_per_day, 86400),
        ]
        
        results = []
        for tier_key, limit, window in checks:
            result = await self._limiter.check(tier_key, limit, window)
            results.append(result)
            
            # Early exit if any tier blocks
            if not result.allowed:
                return result
        
        # Return the most restrictive (lowest remaining)
        return min(results, key=lambda r: r.remaining)
    
    async def reset_all(self, key: str) -> None:
        """Reset all rate limit tiers for a key."""
        for suffix in ["minute", "hour", "day"]:
            await self._limiter.reset(f"{key}:{suffix}")


# ============================================================================
# FACTORY FUNCTIONS
# ============================================================================


_rate_limiter: Optional[RateLimiter] = None
_multi_tier_limiter: Optional[MultiTierRateLimiter] = None


async def get_rate_limiter() -> RateLimiter:
    """Get rate limiter instance."""
    global _rate_limiter
    
    if _rate_limiter is None:
        try:
            redis_client = redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
            # Test connection
            await redis_client.ping()
            _rate_limiter = RedisRateLimiter(redis_client)
            logger.info("rate_limiter_initialized", backend="redis")
        except Exception as e:
            logger.warning(
                "rate_limiter_fallback_to_memory",
                error=str(e),
            )
            _rate_limiter = InMemoryRateLimiter()
    
    return _rate_limiter


async def get_multi_tier_limiter() -> MultiTierRateLimiter:
    """Get multi-tier rate limiter instance."""
    global _multi_tier_limiter
    
    if _multi_tier_limiter is None:
        limiter = await get_rate_limiter()
        _multi_tier_limiter = MultiTierRateLimiter(limiter)
    
    return _multi_tier_limiter


# ============================================================================
# DECORATORS
# ============================================================================


def rate_limit(
    key_func: Callable[..., str],
    limit: int = 60,
    window_seconds: int = 60,
):
    """
    Decorator for rate limiting async functions.
    
    Usage:
        @rate_limit(lambda ctx: f"customer:{ctx.customer_id}", limit=30)
        async def generate_decision(ctx: Context) -> Decision:
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            key = key_func(*args, **kwargs)
            limiter = await get_rate_limiter()
            result = await limiter.check(key, limit, window_seconds)
            
            if not result.allowed:
                from app.common.exceptions import RateLimitError
                raise RateLimitError(
                    message=f"Rate limit exceeded. Retry after {result.retry_after_seconds}s",
                    details={
                        "limit": result.limit,
                        "retry_after": result.retry_after_seconds,
                        "reset_at": result.reset_at.isoformat(),
                    },
                )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


@asynccontextmanager
async def rate_limit_context(key: str, limit: int = 60, window_seconds: int = 60):
    """
    Context manager for rate limiting.
    
    Usage:
        async with rate_limit_context(f"customer:{customer_id}"):
            await expensive_operation()
    """
    limiter = await get_rate_limiter()
    result = await limiter.check(key, limit, window_seconds)
    
    if not result.allowed:
        from app.common.exceptions import RateLimitError
        raise RateLimitError(
            message=f"Rate limit exceeded. Retry after {result.retry_after_seconds}s",
            details={
                "limit": result.limit,
                "retry_after": result.retry_after_seconds,
                "reset_at": result.reset_at.isoformat(),
            },
        )
    
    yield result
