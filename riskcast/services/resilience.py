"""
Resilience Patterns — Retry with Backoff + Circuit Breaker.

Applied to all external calls: OMEN, Claude, webhooks.
"""

import asyncio
import random
import time
from enum import Enum
from typing import Callable, TypeVar

import structlog

logger = structlog.get_logger(__name__)

T = TypeVar("T")


# ── Retry with Exponential Backoff ─────────────────────────────────────────


async def retry_with_backoff(
    fn: Callable,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 16.0,
    jitter: float = 0.5,
    retry_on: tuple = (Exception,),
    operation_name: str = "operation",
) -> T:
    """
    Retry an async function with exponential backoff and jitter.

    Strategy: base_delay * 2^attempt + random(0, jitter)
    """
    last_exc = None
    for attempt in range(max_retries + 1):
        try:
            return await fn()
        except retry_on as exc:
            last_exc = exc
            if attempt == max_retries:
                logger.error(
                    "retry_exhausted",
                    operation=operation_name,
                    attempts=attempt + 1,
                    error=str(exc),
                )
                raise
            delay = min(base_delay * (2 ** attempt), max_delay)
            delay += random.uniform(0, jitter)
            logger.warning(
                "retry_attempt",
                operation=operation_name,
                attempt=attempt + 1,
                max_retries=max_retries,
                delay=round(delay, 2),
                error=str(exc),
            )
            await asyncio.sleep(delay)

    raise last_exc  # Should never reach here


# ── Circuit Breaker ─────────────────────────────────────────────────────────


class CircuitState(str, Enum):
    CLOSED = "closed"       # Normal operation
    OPEN = "open"           # Rejecting all requests
    HALF_OPEN = "half_open" # Testing with one request


class CircuitBreaker:
    """
    Prevent cascade failures when external services are down.

    States: CLOSED → OPEN → HALF_OPEN → CLOSED
    - CLOSED: normal. After `failure_threshold` failures in `window_seconds` → OPEN
    - OPEN: reject immediately for `recovery_timeout` seconds
    - HALF_OPEN: allow 1 request. Success → CLOSED; Failure → OPEN
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        window_seconds: float = 60.0,
        recovery_timeout: float = 30.0,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.window_seconds = window_seconds
        self.recovery_timeout = recovery_timeout

        self._state = CircuitState.CLOSED
        self._failures: list[float] = []
        self._opened_at: float = 0.0
        self._half_open_in_progress = False

    @property
    def state(self) -> CircuitState:
        if self._state == CircuitState.OPEN:
            if time.monotonic() - self._opened_at >= self.recovery_timeout:
                self._state = CircuitState.HALF_OPEN
                logger.info("circuit_half_open", breaker=self.name)
        return self._state

    async def call(self, fn: Callable, *args, **kwargs) -> T:
        """Execute fn through the circuit breaker."""
        state = self.state

        if state == CircuitState.OPEN:
            logger.warning("circuit_open_rejected", breaker=self.name)
            raise CircuitOpenError(f"Circuit breaker '{self.name}' is OPEN")

        if state == CircuitState.HALF_OPEN:
            if self._half_open_in_progress:
                raise CircuitOpenError(f"Circuit breaker '{self.name}' is testing")
            self._half_open_in_progress = True

        try:
            result = await fn(*args, **kwargs)
            self._on_success()
            return result
        except Exception as exc:
            self._on_failure()
            raise

    def _on_success(self) -> None:
        if self._state in (CircuitState.HALF_OPEN, CircuitState.OPEN):
            logger.info("circuit_closed", breaker=self.name)
        self._state = CircuitState.CLOSED
        self._failures.clear()
        self._half_open_in_progress = False

    def _on_failure(self) -> None:
        now = time.monotonic()
        self._half_open_in_progress = False

        if self._state == CircuitState.HALF_OPEN:
            self._state = CircuitState.OPEN
            self._opened_at = now
            logger.warning("circuit_reopened", breaker=self.name)
            return

        # Prune old failures outside window
        cutoff = now - self.window_seconds
        self._failures = [t for t in self._failures if t > cutoff]
        self._failures.append(now)

        if len(self._failures) >= self.failure_threshold:
            self._state = CircuitState.OPEN
            self._opened_at = now
            logger.warning(
                "circuit_opened",
                breaker=self.name,
                failures=len(self._failures),
                threshold=self.failure_threshold,
            )

    def reset(self) -> None:
        """Manually reset the circuit breaker."""
        self._state = CircuitState.CLOSED
        self._failures.clear()
        self._half_open_in_progress = False


class CircuitOpenError(Exception):
    """Raised when a circuit breaker is open and rejects a call."""
    pass


# ── Pre-configured breakers for known services ────────────────────────────

omen_breaker = CircuitBreaker(name="omen", failure_threshold=5, recovery_timeout=30.0)
llm_breaker = CircuitBreaker(name="claude_llm", failure_threshold=3, recovery_timeout=60.0)
webhook_breaker = CircuitBreaker(name="webhook", failure_threshold=5, recovery_timeout=30.0)
