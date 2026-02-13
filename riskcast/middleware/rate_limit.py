"""
Rate Limiter Middleware — Token bucket per tenant + per API key.

Prevents abuse while allowing burst traffic.
Uses in-memory storage (fine for single-process; use Redis for multi-process).

NO endpoint is exempt from rate limiting except health/docs.
"""

import time
from collections import defaultdict
from dataclasses import dataclass, field

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from riskcast.config import settings

logger = structlog.get_logger(__name__)

# ONLY truly public/internal endpoints are exempt
EXEMPT_PATHS = frozenset({"/health", "/docs", "/openapi.json", "/redoc"})


@dataclass
class TokenBucket:
    """Token bucket for rate limiting."""

    tokens: float = 20.0
    last_refill: float = field(default_factory=time.monotonic)
    rate: float = 100.0 / 60.0  # tokens per second
    capacity: float = 20.0

    def consume(self) -> bool:
        """Try to consume a token. Returns True if allowed."""
        now = time.monotonic()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
        self.last_refill = now

        if self.tokens >= 1:
            self.tokens -= 1
            return True
        return False


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Per-tenant / per-API-key rate limiter using token bucket algorithm.

    Extracts tenant from request.state.company_id (set by TenantMiddleware).
    Returns 429 when rate exceeded.
    """

    def __init__(self, app, rate: int | None = None, burst: int | None = None):
        super().__init__(app)
        self.rate = rate or settings.rate_limit_default
        self.burst = burst or settings.rate_limit_burst
        self._buckets: dict[str, TokenBucket] = defaultdict(
            lambda: TokenBucket(
                tokens=float(self.burst),
                rate=self.rate / 60.0,
                capacity=float(self.burst),
            )
        )

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path

        if path in EXEMPT_PATHS:
            return await call_next(request)

        # Rate limit key: company_id or API key prefix or IP
        company_id = getattr(request.state, "company_id", None)
        api_key_prefix = getattr(request.state, "api_key_prefix", None)

        if api_key_prefix:
            key = f"apikey:{api_key_prefix}"
        elif company_id:
            key = f"tenant:{company_id}"
        else:
            key = f"ip:{request.client.host if request.client else 'unknown'}"

        bucket = self._buckets[key]

        if not bucket.consume():
            logger.warning("rate_limit_exceeded", key=key, path=path)
            return Response(
                status_code=429,
                content='{"error":"Rate limit exceeded. Please retry after a moment.","status":429}',
                media_type="application/json",
                headers={"Retry-After": "10"},
            )

        response = await call_next(request)
        return response
