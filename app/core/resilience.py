"""
Resilience Patterns Module.

Production-grade resilience with:
- Circuit Breaker pattern
- Retry with exponential backoff
- Timeout handling
- Bulkhead pattern
- Fallback strategies
"""

import asyncio
import time
from typing import (
    TypeVar, Generic, Callable, Optional, Any, Awaitable, 
    Dict, List, Union
)
from datetime import datetime, timedelta
from enum import Enum
from functools import wraps
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager

from pydantic import BaseModel, Field
import structlog

from app.core.metrics import METRICS

logger = structlog.get_logger(__name__)

T = TypeVar("T")


# ============================================================================
# CIRCUIT BREAKER
# ============================================================================


class CircuitState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, rejecting requests
    HALF_OPEN = "half_open"  # Testing recovery


class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open."""
    
    def __init__(self, service: str, state: CircuitState, retry_after: Optional[datetime] = None):
        self.service = service
        self.state = state
        self.retry_after = retry_after
        super().__init__(f"Circuit breaker for {service} is {state.value}")


# Alias for compatibility
CircuitOpenError = CircuitBreakerError


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    
    failure_threshold: int = 5  # Failures before opening
    success_threshold: int = 3  # Successes to close from half-open
    timeout_seconds: float = 30.0  # Time in open state before half-open
    half_open_max_calls: int = 3  # Max calls in half-open state
    excluded_exceptions: tuple = ()  # Exceptions that don't count as failures
    window_size: int = 10  # Sliding window size for tracking


@dataclass
class CircuitBreakerStats:
    """Statistics for circuit breaker."""
    
    failures: int = 0
    successes: int = 0
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    state_changed_at: datetime = field(default_factory=datetime.utcnow)
    half_open_calls: int = 0
    rejected_calls: int = 0


class CircuitBreaker:
    """
    Circuit Breaker implementation.
    
    States:
    - CLOSED: Normal operation. Tracks failures.
    - OPEN: After threshold failures. Rejects all calls.
    - HALF_OPEN: After timeout. Allows limited calls to test recovery.
    """
    
    def __init__(
        self,
        service: str,
        config: Optional[CircuitBreakerConfig] = None,
    ):
        self.service = service
        self.config = config or CircuitBreakerConfig()
        self._state = CircuitState.CLOSED
        self._stats = CircuitBreakerStats()
        self._lock = asyncio.Lock()
    
    @property
    def state(self) -> CircuitState:
        """Get current state."""
        return self._state
    
    @property
    def stats(self) -> CircuitBreakerStats:
        """Get current statistics."""
        return self._stats
    
    @property
    def metrics(self) -> CircuitBreakerStats:
        """Alias for stats (for compatibility)."""
        return self._stats
    
    @property
    def is_closed(self) -> bool:
        """Check if circuit is closed."""
        return self._state == CircuitState.CLOSED
    
    @property
    def is_open(self) -> bool:
        """Check if circuit is open."""
        return self._state == CircuitState.OPEN
    
    @property
    def is_half_open(self) -> bool:
        """Check if circuit is half-open."""
        return self._state == CircuitState.HALF_OPEN
    
    async def _check_state_transition(self) -> None:
        """Check if state should transition."""
        now = datetime.utcnow()
        
        if self._state == CircuitState.OPEN:
            # Check if timeout has passed
            timeout_at = self._stats.state_changed_at + timedelta(
                seconds=self.config.timeout_seconds
            )
            if now >= timeout_at:
                await self._transition_to(CircuitState.HALF_OPEN)
        
        elif self._state == CircuitState.CLOSED:
            # Check if failures exceeded threshold
            if self._stats.consecutive_failures >= self.config.failure_threshold:
                await self._transition_to(CircuitState.OPEN)
        
        elif self._state == CircuitState.HALF_OPEN:
            # Check success threshold
            if self._stats.consecutive_successes >= self.config.success_threshold:
                await self._transition_to(CircuitState.CLOSED)
    
    async def _transition_to(self, new_state: CircuitState) -> None:
        """Transition to a new state."""
        old_state = self._state
        self._state = new_state
        self._stats.state_changed_at = datetime.utcnow()
        self._stats.half_open_calls = 0
        
        # Reset counters on state change
        if new_state == CircuitState.CLOSED:
            self._stats.consecutive_failures = 0
        elif new_state == CircuitState.HALF_OPEN:
            self._stats.consecutive_successes = 0
        
        # Update metrics
        state_value = {"closed": 0, "open": 1, "half_open": 2}[new_state.value]
        METRICS.circuit_breaker_state.labels(service=self.service).set(state_value)
        
        if new_state == CircuitState.OPEN:
            METRICS.circuit_breaker_trips.labels(service=self.service).inc()
        
        logger.warning(
            "circuit_breaker_state_change",
            service=self.service,
            old_state=old_state.value,
            new_state=new_state.value,
            failures=self._stats.consecutive_failures,
        )
    
    async def _record_success(self) -> None:
        """Record a successful call."""
        self._stats.successes += 1
        self._stats.consecutive_successes += 1
        self._stats.consecutive_failures = 0
        self._stats.last_success_time = datetime.utcnow()
        
        await self._check_state_transition()
    
    async def _record_failure(self, exception: Exception) -> None:
        """Record a failed call."""
        # Check if exception is excluded
        if isinstance(exception, self.config.excluded_exceptions):
            return
        
        self._stats.failures += 1
        self._stats.consecutive_failures += 1
        self._stats.consecutive_successes = 0
        self._stats.last_failure_time = datetime.utcnow()
        
        await self._check_state_transition()
    
    async def can_execute(self) -> bool:
        """Check if a call can be executed."""
        async with self._lock:
            await self._check_state_transition()
            
            if self._state == CircuitState.CLOSED:
                return True
            
            if self._state == CircuitState.OPEN:
                self._stats.rejected_calls += 1
                return False
            
            if self._state == CircuitState.HALF_OPEN:
                if self._stats.half_open_calls < self.config.half_open_max_calls:
                    self._stats.half_open_calls += 1
                    return True
                self._stats.rejected_calls += 1
                return False
            
            return False
    
    async def execute(
        self,
        func: Callable[..., Awaitable[T]],
        *args,
        **kwargs,
    ) -> T:
        """Execute a function with circuit breaker protection."""
        async with self._lock:
            await self._check_state_transition()
            
            if not await self.can_execute():
                retry_after = self._stats.state_changed_at + timedelta(
                    seconds=self.config.timeout_seconds
                )
                raise CircuitBreakerError(self.service, self._state, retry_after)
        
        try:
            result = await func(*args, **kwargs)
            async with self._lock:
                await self._record_success()
            return result
        
        except Exception as e:
            async with self._lock:
                await self._record_failure(e)
            raise
    
    async def reset(self) -> None:
        """Manually reset the circuit breaker."""
        async with self._lock:
            self._stats = CircuitBreakerStats()
            await self._transition_to(CircuitState.CLOSED)
            logger.info("circuit_breaker_reset", service=self.service)


# ============================================================================
# RETRY PATTERN
# ============================================================================


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    
    max_attempts: int = 3
    initial_delay_seconds: float = 1.0
    max_delay_seconds: float = 30.0
    exponential_base: float = 2.0
    jitter: bool = True
    retryable_exceptions: tuple = (Exception,)


class RetryExhaustedError(Exception):
    """Raised when all retry attempts are exhausted."""
    
    def __init__(self, message: str, last_exception: Exception, attempts: int):
        self.last_exception = last_exception
        self.attempts = attempts
        super().__init__(f"{message} after {attempts} attempts: {last_exception}")


async def retry_with_backoff(
    func: Callable[..., Awaitable[T]],
    *args,
    config: Optional[RetryConfig] = None,
    **kwargs,
) -> T:
    """
    Execute a function with retry and exponential backoff.
    
    Args:
        func: Async function to execute
        config: Retry configuration
        *args, **kwargs: Arguments for func
    
    Returns:
        Result of successful function call
    
    Raises:
        RetryExhaustedError: All attempts failed
    """
    config = config or RetryConfig()
    last_exception = None
    
    for attempt in range(1, config.max_attempts + 1):
        try:
            return await func(*args, **kwargs)
        
        except config.retryable_exceptions as e:
            last_exception = e
            
            if attempt == config.max_attempts:
                break
            
            # Calculate delay with exponential backoff
            delay = min(
                config.initial_delay_seconds * (config.exponential_base ** (attempt - 1)),
                config.max_delay_seconds,
            )
            
            # Add jitter
            if config.jitter:
                import random
                delay = delay * (0.5 + random.random())
            
            logger.warning(
                "retry_attempt",
                attempt=attempt,
                max_attempts=config.max_attempts,
                delay_seconds=delay,
                error=str(e),
            )
            
            await asyncio.sleep(delay)
    
    raise RetryExhaustedError(
        f"Function {func.__name__} failed",
        last_exception,
        config.max_attempts,
    )


def with_retry(config: Optional[RetryConfig] = None):
    """
    Decorator for automatic retry.
    
    Usage:
        @with_retry(RetryConfig(max_attempts=5))
        async def fetch_data():
            ...
    """
    config = config or RetryConfig()
    
    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            return await retry_with_backoff(func, *args, config=config, **kwargs)
        return wrapper
    return decorator


# ============================================================================
# TIMEOUT PATTERN
# ============================================================================


class TimeoutError(Exception):
    """Raised when operation times out."""
    
    def __init__(self, operation: str, timeout_seconds: float):
        self.operation = operation
        self.timeout_seconds = timeout_seconds
        super().__init__(f"Operation {operation} timed out after {timeout_seconds}s")


async def with_timeout(
    func: Callable[..., Awaitable[T]],
    timeout_seconds: float,
    operation_name: str = "operation",
    *args,
    **kwargs,
) -> T:
    """
    Execute a function with timeout.
    
    Args:
        func: Async function to execute
        timeout_seconds: Maximum execution time
        operation_name: Name for logging
        *args, **kwargs: Arguments for func
    
    Returns:
        Result of function call
    
    Raises:
        TimeoutError: Operation exceeded timeout
    """
    try:
        return await asyncio.wait_for(
            func(*args, **kwargs),
            timeout=timeout_seconds,
        )
    except asyncio.TimeoutError:
        logger.error(
            "operation_timeout",
            operation=operation_name,
            timeout_seconds=timeout_seconds,
        )
        raise TimeoutError(operation_name, timeout_seconds)


# ============================================================================
# BULKHEAD PATTERN
# ============================================================================


class BulkheadFullError(Exception):
    """Raised when bulkhead is at capacity."""
    
    def __init__(self, name: str, max_concurrent: int):
        self.name = name
        self.max_concurrent = max_concurrent
        super().__init__(f"Bulkhead {name} at capacity ({max_concurrent})")


class Bulkhead:
    """
    Bulkhead pattern for limiting concurrent executions.
    
    Prevents a failing service from consuming all resources.
    """
    
    def __init__(
        self,
        name: str,
        max_concurrent: int = 10,
        max_wait_seconds: float = 5.0,
    ):
        self.name = name
        self.max_concurrent = max_concurrent
        self.max_wait_seconds = max_wait_seconds
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._active_count = 0
    
    @property
    def active_count(self) -> int:
        """Get number of active executions."""
        return self._active_count
    
    @property
    def available_slots(self) -> int:
        """Get number of available slots."""
        return self.max_concurrent - self._active_count
    
    @asynccontextmanager
    async def acquire(self):
        """Acquire a bulkhead slot."""
        try:
            acquired = await asyncio.wait_for(
                self._semaphore.acquire(),
                timeout=self.max_wait_seconds,
            )
            if acquired:
                self._active_count += 1
                try:
                    yield
                finally:
                    self._semaphore.release()
                    self._active_count -= 1
        except asyncio.TimeoutError:
            logger.warning(
                "bulkhead_full",
                name=self.name,
                max_concurrent=self.max_concurrent,
            )
            raise BulkheadFullError(self.name, self.max_concurrent)
    
    async def execute(
        self,
        func: Callable[..., Awaitable[T]],
        *args,
        **kwargs,
    ) -> T:
        """Execute a function with bulkhead protection."""
        async with self.acquire():
            return await func(*args, **kwargs)


# ============================================================================
# FALLBACK PATTERN
# ============================================================================


async def with_fallback(
    primary: Callable[..., Awaitable[T]],
    fallback: Callable[..., Awaitable[T]],
    *args,
    **kwargs,
) -> T:
    """
    Execute primary function with fallback on failure.
    
    Args:
        primary: Primary function to try
        fallback: Fallback function on failure
        *args, **kwargs: Arguments for both functions
    
    Returns:
        Result from primary or fallback
    """
    try:
        return await primary(*args, **kwargs)
    except Exception as e:
        logger.warning(
            "fallback_activated",
            primary=primary.__name__,
            fallback=fallback.__name__,
            error=str(e),
        )
        return await fallback(*args, **kwargs)


# ============================================================================
# COMBINED RESILIENCE
# ============================================================================


class ResilientCall(Generic[T]):
    """
    Builder for resilient function calls.
    
    Combines circuit breaker, retry, timeout, bulkhead, and fallback.
    
    Usage:
        result = await (
            ResilientCall(fetch_data)
            .with_circuit_breaker(breaker)
            .with_retry(RetryConfig(max_attempts=3))
            .with_timeout(5.0)
            .with_fallback(get_cached_data)
            .execute(url)
        )
    """
    
    def __init__(self, func: Callable[..., Awaitable[T]]):
        self._func = func
        self._circuit_breaker: Optional[CircuitBreaker] = None
        self._retry_config: Optional[RetryConfig] = None
        self._timeout_seconds: Optional[float] = None
        self._bulkhead: Optional[Bulkhead] = None
        self._fallback: Optional[Callable[..., Awaitable[T]]] = None
    
    def with_circuit_breaker(self, breaker: CircuitBreaker) -> "ResilientCall[T]":
        """Add circuit breaker."""
        self._circuit_breaker = breaker
        return self
    
    def with_retry(self, config: RetryConfig) -> "ResilientCall[T]":
        """Add retry behavior."""
        self._retry_config = config
        return self
    
    def with_timeout(self, seconds: float) -> "ResilientCall[T]":
        """Add timeout."""
        self._timeout_seconds = seconds
        return self
    
    def with_bulkhead(self, bulkhead: Bulkhead) -> "ResilientCall[T]":
        """Add bulkhead."""
        self._bulkhead = bulkhead
        return self
    
    def with_fallback(self, fallback: Callable[..., Awaitable[T]]) -> "ResilientCall[T]":
        """Add fallback."""
        self._fallback = fallback
        return self
    
    async def execute(self, *args, **kwargs) -> T:
        """Execute the resilient call."""
        
        async def run() -> T:
            result_func = self._func
            
            # Apply timeout
            if self._timeout_seconds:
                original = result_func
                async def with_to(*a, **kw):
                    return await with_timeout(original, self._timeout_seconds, *a, **kw)
                result_func = with_to
            
            # Apply retry
            if self._retry_config:
                original = result_func
                async def with_ret(*a, **kw):
                    return await retry_with_backoff(original, *a, config=self._retry_config, **kw)
                result_func = with_ret
            
            # Apply circuit breaker
            if self._circuit_breaker:
                return await self._circuit_breaker.execute(result_func, *args, **kwargs)
            
            return await result_func(*args, **kwargs)
        
        # Apply bulkhead
        if self._bulkhead:
            run_with_bulkhead = run
            async def bulk_run() -> T:
                return await self._bulkhead.execute(run_with_bulkhead)
            run = bulk_run
        
        # Apply fallback
        if self._fallback:
            return await with_fallback(run, self._fallback)
        
        return await run()


# ============================================================================
# SERVICE REGISTRY
# ============================================================================


class CircuitBreakerRegistry:
    """Registry for circuit breakers."""
    
    _breakers: Dict[str, CircuitBreaker] = {}
    
    @classmethod
    def get_or_create(
        cls,
        service: str,
        config: Optional[CircuitBreakerConfig] = None,
    ) -> CircuitBreaker:
        """Get or create a circuit breaker for a service."""
        if service not in cls._breakers:
            cls._breakers[service] = CircuitBreaker(service, config)
        return cls._breakers[service]
    
    @classmethod
    def get(cls, service: str) -> Optional[CircuitBreaker]:
        """Get a circuit breaker by service name."""
        return cls._breakers.get(service)
    
    @classmethod
    def all(cls) -> Dict[str, CircuitBreaker]:
        """Get all circuit breakers."""
        return cls._breakers.copy()
    
    @classmethod
    async def reset_all(cls) -> None:
        """Reset all circuit breakers."""
        for breaker in cls._breakers.values():
            await breaker.reset()


# Default circuit breakers for external services
POLYMARKET_BREAKER = CircuitBreakerRegistry.get_or_create(
    "polymarket",
    CircuitBreakerConfig(
        failure_threshold=3,
        timeout_seconds=60,
    ),
)

AIS_BREAKER = CircuitBreakerRegistry.get_or_create(
    "ais",
    CircuitBreakerConfig(
        failure_threshold=5,
        timeout_seconds=30,
    ),
)

TWILIO_BREAKER = CircuitBreakerRegistry.get_or_create(
    "twilio",
    CircuitBreakerConfig(
        failure_threshold=3,
        timeout_seconds=120,
    ),
)


# ============================================================================
# RETRY POLICY CLASS
# ============================================================================


class RetryPolicy:
    """
    Retry policy for automatic retries with backoff.
    
    Can be used as a decorator or with explicit execute() call.
    """
    
    def __init__(self, config: Optional[RetryConfig] = None):
        self.config = config or RetryConfig()
    
    def __call__(self, func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        """Use as decorator."""
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            return await retry_with_backoff(func, *args, config=self.config, **kwargs)
        return wrapper
    
    async def execute(
        self,
        func: Callable[..., Awaitable[T]],
        *args,
        **kwargs,
    ) -> T:
        """Execute with retry policy."""
        return await retry_with_backoff(func, *args, config=self.config, **kwargs)


# ============================================================================
# DECORATOR FUNCTIONS
# ============================================================================


def retry(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 30.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retryable_exceptions: tuple = (Exception,),
):
    """
    Decorator for automatic retry with exponential backoff.
    
    Usage:
        @retry(max_attempts=5, initial_delay=0.5)
        async def fetch_data():
            ...
    """
    config = RetryConfig(
        max_attempts=max_attempts,
        initial_delay_seconds=initial_delay,
        max_delay_seconds=max_delay,
        exponential_base=exponential_base,
        jitter=jitter,
        retryable_exceptions=retryable_exceptions,
    )
    
    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            return await retry_with_backoff(func, *args, config=config, **kwargs)
        return wrapper
    return decorator


def timeout(seconds: float, operation_name: str = "operation"):
    """
    Decorator for timeout handling.
    
    Usage:
        @timeout(5.0, "api_call")
        async def api_call():
            ...
    """
    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            return await with_timeout(func, seconds, operation_name, *args, **kwargs)
        return wrapper
    return decorator


def fallback(fallback_func: Callable[..., Awaitable[T]]):
    """
    Decorator for fallback execution.
    
    Usage:
        @fallback(get_cached_value)
        async def get_fresh_value():
            ...
    """
    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            return await with_fallback(func, fallback_func, *args, **kwargs)
        return wrapper
    return decorator


# ============================================================================
# RESILIENCE POLICY
# ============================================================================


class ResiliencePolicy:
    """
    Combined resilience policy with multiple patterns.
    
    Combines circuit breaker, retry, timeout, and fallback into a single policy.
    
    Usage:
        policy = ResiliencePolicy(
            circuit_breaker=breaker,
            retry_config=RetryConfig(max_attempts=3),
            timeout_seconds=5.0,
        )
        
        result = await policy.execute(api_call, url)
    """
    
    def __init__(
        self,
        circuit_breaker: Optional[CircuitBreaker] = None,
        retry_config: Optional[RetryConfig] = None,
        timeout_seconds: Optional[float] = None,
        fallback_func: Optional[Callable[..., Awaitable[T]]] = None,
        bulkhead: Optional[Bulkhead] = None,
    ):
        self.circuit_breaker = circuit_breaker
        self.retry_config = retry_config
        self.timeout_seconds = timeout_seconds
        self.fallback_func = fallback_func
        self.bulkhead = bulkhead
    
    async def execute(
        self,
        func: Callable[..., Awaitable[T]],
        *args,
        **kwargs,
    ) -> T:
        """Execute function with all configured resilience patterns."""
        call = ResilientCall(func)
        
        if self.circuit_breaker:
            call = call.with_circuit_breaker(self.circuit_breaker)
        
        if self.retry_config:
            call = call.with_retry(self.retry_config)
        
        if self.timeout_seconds:
            call = call.with_timeout(self.timeout_seconds)
        
        if self.bulkhead:
            call = call.with_bulkhead(self.bulkhead)
        
        if self.fallback_func:
            call = call.with_fallback(self.fallback_func)
        
        return await call.execute(*args, **kwargs)
    
    def __call__(self, func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        """Use as decorator."""
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            return await self.execute(func, *args, **kwargs)
        return wrapper


# ============================================================================
# MAKE CIRCUIT BREAKER A DECORATOR
# ============================================================================


# Add decorator support to CircuitBreaker
_original_init = CircuitBreaker.__init__


def _new_init(self, service: str, config: Optional[CircuitBreakerConfig] = None):
    _original_init(self, service, config)


def _call(self, func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
    """Use circuit breaker as decorator."""
    @wraps(func)
    async def wrapper(*args, **kwargs) -> T:
        return await self.execute(func, *args, **kwargs)
    return wrapper


CircuitBreaker.__call__ = _call
