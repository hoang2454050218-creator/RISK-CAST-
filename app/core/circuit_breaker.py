"""
Production Circuit Breaker for RISKCAST.

Implements circuit breaker pattern for:
- External API calls
- Database connections
- Redis operations
- Third-party services
"""

import asyncio
import functools
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Callable, TypeVar, Generic
from enum import Enum
from collections import deque

import structlog

logger = structlog.get_logger(__name__)

T = TypeVar("T")


class CircuitState(str, Enum):
    """Circuit breaker states."""
    
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if recovered


@dataclass
class CircuitStats:
    """Statistics for circuit breaker."""
    
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    rejected_calls: int = 0
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    
    @property
    def failure_rate(self) -> float:
        """Calculate failure rate."""
        if self.total_calls == 0:
            return 0.0
        return self.failed_calls / self.total_calls
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_calls == 0:
            return 0.0
        return self.successful_calls / self.total_calls


@dataclass
class CircuitConfig:
    """Configuration for circuit breaker."""
    
    # Failure threshold to open circuit
    failure_threshold: int = 5
    
    # Time window for counting failures (seconds)
    failure_window_seconds: int = 60
    
    # Time to wait before allowing trial request (seconds)
    recovery_timeout_seconds: int = 30
    
    # Number of successful trial requests to close circuit
    success_threshold: int = 3
    
    # Whether to track failure rate instead of count
    use_failure_rate: bool = False
    failure_rate_threshold: float = 0.5
    
    # Minimum calls before calculating failure rate
    minimum_calls: int = 10
    
    # Exceptions to count as failures (empty = all)
    failure_exceptions: tuple = ()
    
    # Exceptions to not count as failures
    excluded_exceptions: tuple = ()


class CircuitBreaker:
    """
    Production-grade circuit breaker.
    
    Features:
    - Configurable failure thresholds
    - Sliding window for failure counting
    - Half-open state with gradual recovery
    - Detailed statistics
    - Event callbacks
    """
    
    def __init__(
        self,
        name: str,
        config: CircuitConfig = None,
        on_state_change: Callable[[str, CircuitState, CircuitState], None] = None,
    ):
        self._name = name
        self._config = config or CircuitConfig()
        self._state = CircuitState.CLOSED
        self._stats = CircuitStats()
        self._opened_at: Optional[datetime] = None
        self._failure_timestamps: deque = deque()
        self._lock = asyncio.Lock()
        self._on_state_change = on_state_change
    
    @property
    def name(self) -> str:
        """Get circuit breaker name."""
        return self._name
    
    @property
    def state(self) -> CircuitState:
        """Get current state."""
        return self._state
    
    @property
    def stats(self) -> CircuitStats:
        """Get statistics."""
        return self._stats
    
    def _should_count_failure(self, error: Exception) -> bool:
        """Check if exception should count as failure."""
        # Check excluded exceptions
        if self._config.excluded_exceptions:
            if isinstance(error, self._config.excluded_exceptions):
                return False
        
        # Check failure exceptions (if specified)
        if self._config.failure_exceptions:
            return isinstance(error, self._config.failure_exceptions)
        
        return True
    
    def _clean_old_failures(self) -> None:
        """Remove failures outside the window."""
        cutoff = datetime.utcnow() - timedelta(
            seconds=self._config.failure_window_seconds
        )
        
        while self._failure_timestamps and self._failure_timestamps[0] < cutoff:
            self._failure_timestamps.popleft()
    
    def _should_open(self) -> bool:
        """Check if circuit should open."""
        if self._config.use_failure_rate:
            if self._stats.total_calls < self._config.minimum_calls:
                return False
            return self._stats.failure_rate >= self._config.failure_rate_threshold
        else:
            self._clean_old_failures()
            return len(self._failure_timestamps) >= self._config.failure_threshold
    
    def _should_attempt_reset(self) -> bool:
        """Check if we should attempt to reset circuit."""
        if not self._opened_at:
            return True
        
        elapsed = (datetime.utcnow() - self._opened_at).total_seconds()
        return elapsed >= self._config.recovery_timeout_seconds
    
    def _transition_to(self, new_state: CircuitState) -> None:
        """Transition to new state."""
        old_state = self._state
        self._state = new_state
        
        logger.info(
            "circuit_state_changed",
            circuit=self._name,
            old_state=old_state.value,
            new_state=new_state.value,
        )
        
        if self._on_state_change:
            self._on_state_change(self._name, old_state, new_state)
        
        if new_state == CircuitState.OPEN:
            self._opened_at = datetime.utcnow()
        elif new_state == CircuitState.CLOSED:
            self._stats.consecutive_failures = 0
            self._failure_timestamps.clear()
    
    def _on_success(self) -> None:
        """Handle successful call."""
        self._stats.total_calls += 1
        self._stats.successful_calls += 1
        self._stats.last_success_time = datetime.utcnow()
        self._stats.consecutive_failures = 0
        self._stats.consecutive_successes += 1
        
        if self._state == CircuitState.HALF_OPEN:
            if self._stats.consecutive_successes >= self._config.success_threshold:
                self._transition_to(CircuitState.CLOSED)
    
    def _on_failure(self, error: Exception) -> None:
        """Handle failed call."""
        self._stats.total_calls += 1
        self._stats.failed_calls += 1
        self._stats.last_failure_time = datetime.utcnow()
        self._stats.consecutive_successes = 0
        
        if self._should_count_failure(error):
            self._stats.consecutive_failures += 1
            self._failure_timestamps.append(datetime.utcnow())
            
            if self._state == CircuitState.CLOSED:
                if self._should_open():
                    self._transition_to(CircuitState.OPEN)
            
            elif self._state == CircuitState.HALF_OPEN:
                self._transition_to(CircuitState.OPEN)
    
    async def call(
        self,
        func: Callable[..., T],
        *args,
        **kwargs,
    ) -> T:
        """Execute function through circuit breaker."""
        async with self._lock:
            # Check if open
            if self._state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self._transition_to(CircuitState.HALF_OPEN)
                else:
                    self._stats.rejected_calls += 1
                    raise CircuitOpenError(
                        f"Circuit '{self._name}' is open, request rejected"
                    )
        
        try:
            # Execute function
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            async with self._lock:
                self._on_success()
            
            return result
            
        except Exception as e:
            async with self._lock:
                self._on_failure(e)
            raise
    
    def reset(self) -> None:
        """Manually reset the circuit breaker."""
        self._state = CircuitState.CLOSED
        self._stats = CircuitStats()
        self._opened_at = None
        self._failure_timestamps.clear()
        logger.info("circuit_reset", circuit=self._name)


class CircuitOpenError(Exception):
    """Raised when circuit is open."""
    pass


# ============================================================================
# CIRCUIT BREAKER REGISTRY
# ============================================================================


class CircuitBreakerRegistry:
    """
    Registry for managing multiple circuit breakers.
    
    Provides:
    - Centralized circuit breaker management
    - Health monitoring
    - Bulk operations
    """
    
    def __init__(self):
        self._breakers: Dict[str, CircuitBreaker] = {}
        self._default_config = CircuitConfig()
    
    def get_or_create(
        self,
        name: str,
        config: CircuitConfig = None,
    ) -> CircuitBreaker:
        """Get existing or create new circuit breaker."""
        if name not in self._breakers:
            self._breakers[name] = CircuitBreaker(
                name=name,
                config=config or self._default_config,
                on_state_change=self._on_state_change,
            )
        return self._breakers[name]
    
    def _on_state_change(
        self,
        name: str,
        old_state: CircuitState,
        new_state: CircuitState,
    ) -> None:
        """Handle state change callback."""
        # Could emit metrics, alerts, etc.
        pass
    
    def get_health(self) -> Dict[str, Dict[str, Any]]:
        """Get health status of all circuit breakers."""
        return {
            name: {
                "state": breaker.state.value,
                "stats": {
                    "total_calls": breaker.stats.total_calls,
                    "successful_calls": breaker.stats.successful_calls,
                    "failed_calls": breaker.stats.failed_calls,
                    "rejected_calls": breaker.stats.rejected_calls,
                    "failure_rate": breaker.stats.failure_rate,
                },
            }
            for name, breaker in self._breakers.items()
        }
    
    def get_all_health(self) -> Dict[str, Dict[str, Any]]:
        """Alias for get_health() for compatibility."""
        return self.get_health()
    
    def reset_all(self) -> None:
        """Reset all circuit breakers."""
        for breaker in self._breakers.values():
            breaker.reset()


# ============================================================================
# DECORATOR
# ============================================================================


def circuit_breaker(
    name: str,
    config: CircuitConfig = None,
    fallback: Callable = None,
):
    """
    Decorator to apply circuit breaker to a function.
    
    Args:
        name: Circuit breaker name
        config: Circuit breaker configuration
        fallback: Fallback function when circuit is open
    """
    def decorator(func: Callable) -> Callable:
        breaker = get_registry().get_or_create(name, config)
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await breaker.call(func, *args, **kwargs)
            except CircuitOpenError:
                if fallback:
                    if asyncio.iscoroutinefunction(fallback):
                        return await fallback(*args, **kwargs)
                    return fallback(*args, **kwargs)
                raise
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                # For sync functions, we need to run in event loop
                loop = asyncio.get_event_loop()
                return loop.run_until_complete(breaker.call(func, *args, **kwargs))
            except CircuitOpenError:
                if fallback:
                    return fallback(*args, **kwargs)
                raise
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


# ============================================================================
# GLOBAL REGISTRY
# ============================================================================


_registry: Optional[CircuitBreakerRegistry] = None


def get_registry() -> CircuitBreakerRegistry:
    """Get global circuit breaker registry."""
    global _registry
    if _registry is None:
        _registry = CircuitBreakerRegistry()
    return _registry


def get_circuit_breaker(name: str, config: CircuitConfig = None) -> CircuitBreaker:
    """Get a circuit breaker by name."""
    return get_registry().get_or_create(name, config)


def get_circuit_breaker_registry() -> CircuitBreakerRegistry:
    """Get the global circuit breaker registry (alias for get_registry)."""
    return get_registry()


# ============================================================================
# PRE-CONFIGURED CIRCUIT BREAKERS
# ============================================================================


# Polymarket API
POLYMARKET_CONFIG = CircuitConfig(
    failure_threshold=3,
    failure_window_seconds=60,
    recovery_timeout_seconds=60,
    success_threshold=2,
)

# Database
DATABASE_CONFIG = CircuitConfig(
    failure_threshold=5,
    failure_window_seconds=30,
    recovery_timeout_seconds=15,
    success_threshold=3,
)

# Redis
REDIS_CONFIG = CircuitConfig(
    failure_threshold=3,
    failure_window_seconds=30,
    recovery_timeout_seconds=10,
    success_threshold=2,
)

# WhatsApp API
WHATSAPP_CONFIG = CircuitConfig(
    failure_threshold=5,
    failure_window_seconds=120,
    recovery_timeout_seconds=120,
    success_threshold=3,
)


def get_polymarket_breaker() -> CircuitBreaker:
    """Get Polymarket circuit breaker."""
    return get_circuit_breaker("polymarket", POLYMARKET_CONFIG)


def get_database_breaker() -> CircuitBreaker:
    """Get database circuit breaker."""
    return get_circuit_breaker("database", DATABASE_CONFIG)


def get_redis_breaker() -> CircuitBreaker:
    """Get Redis circuit breaker."""
    return get_circuit_breaker("redis", REDIS_CONFIG)


def get_whatsapp_breaker() -> CircuitBreaker:
    """Get WhatsApp circuit breaker."""
    return get_circuit_breaker("whatsapp", WHATSAPP_CONFIG)
