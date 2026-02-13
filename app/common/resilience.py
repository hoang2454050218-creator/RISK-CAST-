"""
Resilience patterns for external service calls.

Implements:
- Retry with exponential backoff
- Circuit breaker pattern
- Timeout handling
- Fallback responses

These patterns are CRITICAL for production reliability.
Without them, one failing service can cascade and bring down everything.
"""

import asyncio
import time
from functools import wraps
from typing import Callable, TypeVar, ParamSpec, Optional, Any
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime

import structlog

logger = structlog.get_logger(__name__)

P = ParamSpec("P")
T = TypeVar("T")


# ============================================================================
# EXCEPTIONS
# ============================================================================


class CircuitOpenError(Exception):
    """Raised when circuit breaker is open and rejecting calls."""

    def __init__(self, service_name: str, recovery_time: float):
        self.service_name = service_name
        self.recovery_time = recovery_time
        super().__init__(
            f"Circuit breaker open for {service_name}. "
            f"Recovery in {recovery_time:.1f}s"
        )


class RetryExhaustedError(Exception):
    """Raised when all retry attempts have been exhausted."""

    def __init__(self, attempts: int, last_error: Exception):
        self.attempts = attempts
        self.last_error = last_error
        super().__init__(
            f"All {attempts} retry attempts exhausted. Last error: {last_error}"
        )


# ============================================================================
# RETRY WITH EXPONENTIAL BACKOFF
# ============================================================================


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    retryable_exceptions: tuple = (Exception,),
    on_retry: Optional[Callable[[int, Exception], None]] = None,
):
    """
    Decorator for retry with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay between retries (seconds)
        max_delay: Maximum delay between retries (seconds)
        exponential_base: Base for exponential backoff calculation
        retryable_exceptions: Tuple of exceptions that trigger retry
        on_retry: Optional callback called on each retry (attempt, exception)

    Usage:
        @retry_with_backoff(max_retries=3)
        async def fetch_data():
            response = await client.get("/data")
            return response.json()

    Backoff formula: delay = min(base_delay * (exponential_base ** attempt), max_delay)
    Example with defaults: 1s, 2s, 4s, 8s, ... up to 60s
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            last_exception: Optional[Exception] = None

            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e

                    if attempt < max_retries:
                        # Calculate delay with exponential backoff
                        delay = min(
                            base_delay * (exponential_base ** attempt),
                            max_delay
                        )

                        # Add jitter (±10%) to prevent thundering herd
                        import random
                        jitter = delay * 0.1 * (2 * random.random() - 1)
                        delay = max(0.1, delay + jitter)

                        logger.warning(
                            "retry_attempt",
                            function=func.__name__,
                            attempt=attempt + 1,
                            max_retries=max_retries,
                            delay_seconds=round(delay, 2),
                            error_type=type(e).__name__,
                            error=str(e)[:200],
                        )

                        if on_retry:
                            on_retry(attempt + 1, e)

                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            "retry_exhausted",
                            function=func.__name__,
                            attempts=max_retries + 1,
                            error_type=type(e).__name__,
                            error=str(e)[:200],
                        )

            raise RetryExhaustedError(max_retries + 1, last_exception)

        @wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            last_exception: Optional[Exception] = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e

                    if attempt < max_retries:
                        delay = min(
                            base_delay * (exponential_base ** attempt),
                            max_delay
                        )
                        import random
                        jitter = delay * 0.1 * (2 * random.random() - 1)
                        delay = max(0.1, delay + jitter)

                        logger.warning(
                            "retry_attempt_sync",
                            function=func.__name__,
                            attempt=attempt + 1,
                            delay_seconds=round(delay, 2),
                        )

                        time.sleep(delay)

            raise RetryExhaustedError(max_retries + 1, last_exception)

        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


# ============================================================================
# CIRCUIT BREAKER
# ============================================================================


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation, requests pass through
    OPEN = "open"  # Too many failures, requests rejected immediately
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerState:
    """Internal state for circuit breaker."""

    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: float = 0.0
    last_state_change: float = field(default_factory=time.time)
    half_open_calls: int = 0


class CircuitBreaker:
    """
    Circuit breaker implementation.

    Prevents cascading failures by "breaking" the circuit when a service
    is failing, giving it time to recover.

    States:
    - CLOSED: Normal operation, all requests pass through
    - OPEN: Service is failing, requests are rejected immediately
    - HALF_OPEN: Testing if service has recovered

    Transitions:
    - CLOSED → OPEN: After failure_threshold consecutive failures
    - OPEN → HALF_OPEN: After recovery_timeout seconds
    - HALF_OPEN → CLOSED: After half_open_success_threshold successes
    - HALF_OPEN → OPEN: On any failure

    Usage:
        breaker = CircuitBreaker(name="omen_api")

        try:
            async with breaker:
                result = await omen_client.get_signals()
        except CircuitOpenError:
            # Use cached/fallback data
            result = get_cached_signals()
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        half_open_max_calls: int = 3,
        half_open_success_threshold: int = 2,
    ):
        """
        Initialize circuit breaker.

        Args:
            name: Name for logging/metrics
            failure_threshold: Failures before opening circuit
            recovery_timeout: Seconds before trying half-open
            half_open_max_calls: Max calls allowed in half-open state
            half_open_success_threshold: Successes needed to close circuit
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        self.half_open_success_threshold = half_open_success_threshold

        self._state = CircuitBreakerState()
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        """Current circuit state."""
        return self._state.state

    @property
    def is_closed(self) -> bool:
        """Whether circuit is closed (normal operation)."""
        return self._state.state == CircuitState.CLOSED

    @property
    def is_open(self) -> bool:
        """Whether circuit is open (rejecting calls)."""
        return self._state.state == CircuitState.OPEN

    async def __aenter__(self):
        """Enter circuit breaker context."""
        await self._before_call()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit circuit breaker context."""
        if exc_type is None:
            await self._on_success()
        else:
            await self._on_failure(exc_val)
        return False  # Don't suppress exceptions

    async def _before_call(self):
        """Check if call is allowed."""
        async with self._lock:
            now = time.time()

            if self._state.state == CircuitState.OPEN:
                # Check if recovery timeout has passed
                time_since_failure = now - self._state.last_failure_time

                if time_since_failure >= self.recovery_timeout:
                    # Transition to half-open
                    self._transition_to(CircuitState.HALF_OPEN)
                    logger.info(
                        "circuit_half_open",
                        name=self.name,
                        time_since_failure=round(time_since_failure, 1),
                    )
                else:
                    # Still in recovery period
                    remaining = self.recovery_timeout - time_since_failure
                    raise CircuitOpenError(self.name, remaining)

            if self._state.state == CircuitState.HALF_OPEN:
                # Limit calls in half-open state
                if self._state.half_open_calls >= self.half_open_max_calls:
                    raise CircuitOpenError(self.name, 0)
                self._state.half_open_calls += 1

    async def _on_success(self):
        """Record successful call."""
        async with self._lock:
            if self._state.state == CircuitState.HALF_OPEN:
                self._state.success_count += 1

                if self._state.success_count >= self.half_open_success_threshold:
                    # Service recovered, close circuit
                    self._transition_to(CircuitState.CLOSED)
                    logger.info(
                        "circuit_closed",
                        name=self.name,
                        recovery_successes=self._state.success_count,
                    )
            elif self._state.state == CircuitState.CLOSED:
                # Reset failure count on success
                self._state.failure_count = 0

    async def _on_failure(self, error: Exception):
        """Record failed call."""
        async with self._lock:
            now = time.time()

            if self._state.state == CircuitState.HALF_OPEN:
                # Any failure in half-open reopens circuit
                self._transition_to(CircuitState.OPEN)
                self._state.last_failure_time = now
                logger.warning(
                    "circuit_reopened",
                    name=self.name,
                    error_type=type(error).__name__,
                )

            elif self._state.state == CircuitState.CLOSED:
                self._state.failure_count += 1
                self._state.last_failure_time = now

                if self._state.failure_count >= self.failure_threshold:
                    # Too many failures, open circuit
                    self._transition_to(CircuitState.OPEN)
                    logger.error(
                        "circuit_opened",
                        name=self.name,
                        failure_count=self._state.failure_count,
                        error_type=type(error).__name__,
                    )

    def _transition_to(self, new_state: CircuitState):
        """Transition to a new state."""
        old_state = self._state.state
        self._state.state = new_state
        self._state.last_state_change = time.time()

        # Reset counters on state change
        if new_state == CircuitState.CLOSED:
            self._state.failure_count = 0
            self._state.success_count = 0
        elif new_state == CircuitState.HALF_OPEN:
            self._state.half_open_calls = 0
            self._state.success_count = 0

        logger.debug(
            "circuit_state_change",
            name=self.name,
            from_state=old_state.value,
            to_state=new_state.value,
        )

    def get_stats(self) -> dict:
        """Get circuit breaker statistics."""
        return {
            "name": self.name,
            "state": self._state.state.value,
            "failure_count": self._state.failure_count,
            "success_count": self._state.success_count,
            "last_failure_time": self._state.last_failure_time,
            "last_state_change": self._state.last_state_change,
        }


# ============================================================================
# CIRCUIT BREAKER DECORATOR
# ============================================================================


# Global registry of circuit breakers
_circuit_breakers: dict[str, CircuitBreaker] = {}


def get_circuit_breaker(name: str, **kwargs) -> CircuitBreaker:
    """Get or create a circuit breaker by name."""
    if name not in _circuit_breakers:
        _circuit_breakers[name] = CircuitBreaker(name=name, **kwargs)
    return _circuit_breakers[name]


def circuit_breaker(
    name: Optional[str] = None,
    failure_threshold: int = 5,
    recovery_timeout: float = 60.0,
):
    """
    Decorator version of circuit breaker.

    Args:
        name: Circuit breaker name (defaults to function name)
        failure_threshold: Failures before opening circuit
        recovery_timeout: Seconds before trying half-open

    Usage:
        @circuit_breaker(failure_threshold=5, recovery_timeout=60)
        async def call_external_api():
            ...
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        breaker_name = name or func.__name__
        breaker = get_circuit_breaker(
            breaker_name,
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
        )

        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            async with breaker:
                return await func(*args, **kwargs)

        # Attach breaker for testing/inspection
        wrapper.circuit_breaker = breaker
        return wrapper

    return decorator


# ============================================================================
# TIMEOUT WRAPPER
# ============================================================================


def with_timeout(timeout_seconds: float):
    """
    Decorator to add timeout to async functions.

    Usage:
        @with_timeout(30.0)
        async def slow_operation():
            ...
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            try:
                return await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=timeout_seconds,
                )
            except asyncio.TimeoutError:
                logger.error(
                    "operation_timeout",
                    function=func.__name__,
                    timeout_seconds=timeout_seconds,
                )
                raise

        return wrapper

    return decorator


# ============================================================================
# FALLBACK WRAPPER
# ============================================================================


def with_fallback(fallback_value: Any = None, fallback_func: Optional[Callable] = None):
    """
    Decorator to provide fallback on failure.

    Args:
        fallback_value: Static value to return on failure
        fallback_func: Function to call for fallback (receives exception)

    Usage:
        @with_fallback(fallback_value=[])
        async def get_items():
            ...

        @with_fallback(fallback_func=lambda e: get_cached_items())
        async def get_items():
            ...
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger.warning(
                    "using_fallback",
                    function=func.__name__,
                    error_type=type(e).__name__,
                    error=str(e)[:100],
                )

                if fallback_func:
                    result = fallback_func(e)
                    if asyncio.iscoroutine(result):
                        return await result
                    return result

                return fallback_value

        return wrapper

    return decorator
