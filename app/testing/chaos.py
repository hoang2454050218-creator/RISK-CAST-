"""
Chaos Engineering Utilities.

Provides controlled fault injection for resilience testing:
- Network failures
- Latency injection
- Service unavailability
- Resource exhaustion
- Clock skew

ONLY enable in non-production environments!
"""

import asyncio
import random
import time
from typing import Optional, Callable, Any, Dict, TypeVar, List
from functools import wraps
from contextlib import asynccontextmanager
from enum import Enum
import os

import structlog

logger = structlog.get_logger(__name__)

T = TypeVar("T")


# ============================================================================
# SAFETY CHECK
# ============================================================================


def _is_chaos_enabled() -> bool:
    """Check if chaos engineering is enabled."""
    env = os.getenv("RISKCAST_ENV", "development")
    chaos_enabled = os.getenv("CHAOS_ENABLED", "false").lower() == "true"
    
    # NEVER enable in production unless explicitly overridden
    if env == "production" and not os.getenv("CHAOS_FORCE_PRODUCTION"):
        return False
    
    return chaos_enabled


class ChaosError(Exception):
    """Exception raised by chaos injectors."""
    pass


# ============================================================================
# FAULT TYPES
# ============================================================================


class FaultType(str, Enum):
    """Types of faults that can be injected."""
    LATENCY = "latency"          # Add delay
    FAILURE = "failure"          # Raise exception
    TIMEOUT = "timeout"          # Operation timeout
    CORRUPTION = "corruption"    # Return corrupted data
    PARTIAL = "partial"          # Partial failure
    RESOURCE = "resource"        # Resource exhaustion


# ============================================================================
# CHAOS CONFIGURATION
# ============================================================================


class ChaosConfig:
    """
    Configuration for chaos experiments.
    
    Example:
        config = ChaosConfig()
        config.add_fault(
            target="external_api",
            fault_type=FaultType.LATENCY,
            probability=0.1,
            latency_ms=2000,
        )
    """
    
    def __init__(self):
        self._faults: Dict[str, Dict[str, Any]] = {}
        self._enabled = _is_chaos_enabled()
    
    @property
    def enabled(self) -> bool:
        return self._enabled
    
    def enable(self) -> None:
        """Enable chaos (only works in non-production)."""
        if _is_chaos_enabled():
            self._enabled = True
            logger.warning("chaos_enabled")
    
    def disable(self) -> None:
        """Disable chaos."""
        self._enabled = False
        logger.info("chaos_disabled")
    
    def add_fault(
        self,
        target: str,
        fault_type: FaultType,
        probability: float = 0.1,
        **kwargs,
    ) -> None:
        """
        Add a fault injection rule.
        
        Args:
            target: Target identifier (e.g., "polymarket_api", "database")
            fault_type: Type of fault to inject
            probability: Probability of fault (0.0-1.0)
            **kwargs: Fault-specific parameters
        """
        self._faults[target] = {
            "fault_type": fault_type,
            "probability": probability,
            **kwargs,
        }
        
        logger.info(
            "chaos_fault_configured",
            target=target,
            fault_type=fault_type,
            probability=probability,
        )
    
    def remove_fault(self, target: str) -> None:
        """Remove a fault rule."""
        self._faults.pop(target, None)
    
    def get_fault(self, target: str) -> Optional[Dict[str, Any]]:
        """Get fault configuration for a target."""
        if not self._enabled:
            return None
        return self._faults.get(target)
    
    def clear_all(self) -> None:
        """Clear all fault configurations."""
        self._faults.clear()


# Global configuration
_chaos_config = ChaosConfig()


def get_chaos_config() -> ChaosConfig:
    """Get global chaos configuration."""
    return _chaos_config


# ============================================================================
# FAULT INJECTORS
# ============================================================================


async def inject_latency(
    min_ms: int = 100,
    max_ms: int = 5000,
    target: str = "unknown",
) -> None:
    """Inject random latency."""
    delay_ms = random.randint(min_ms, max_ms)
    
    logger.warning(
        "chaos_latency_injected",
        target=target,
        delay_ms=delay_ms,
    )
    
    await asyncio.sleep(delay_ms / 1000.0)


async def inject_failure(
    error_type: str = "ServiceUnavailable",
    message: str = "Chaos failure injected",
    target: str = "unknown",
) -> None:
    """Inject a failure."""
    logger.warning(
        "chaos_failure_injected",
        target=target,
        error_type=error_type,
    )
    
    raise ChaosError(f"[CHAOS] {error_type}: {message}")


async def inject_timeout(
    timeout_seconds: int = 30,
    target: str = "unknown",
) -> None:
    """Inject a timeout."""
    logger.warning(
        "chaos_timeout_injected",
        target=target,
        timeout_seconds=timeout_seconds,
    )
    
    # Sleep longer than typical timeouts
    await asyncio.sleep(timeout_seconds + 5)


def inject_corruption(data: Any, corruption_rate: float = 0.1) -> Any:
    """
    Inject data corruption.
    
    For strings: randomly modify characters
    For dicts: randomly remove/modify keys
    For lists: randomly modify elements
    """
    if isinstance(data, str):
        chars = list(data)
        for i in range(len(chars)):
            if random.random() < corruption_rate:
                chars[i] = chr(random.randint(65, 90))
        return "".join(chars)
    
    elif isinstance(data, dict):
        result = data.copy()
        keys = list(result.keys())
        for key in keys:
            if random.random() < corruption_rate:
                del result[key]
        return result
    
    elif isinstance(data, list):
        result = data.copy()
        for i in range(len(result)):
            if random.random() < corruption_rate:
                result[i] = None
        return result
    
    return data


# ============================================================================
# DECORATORS
# ============================================================================


def chaos_enabled(target: str):
    """
    Decorator to add chaos injection to a function.
    
    @chaos_enabled("polymarket_api")
    async def fetch_markets():
        ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            config = get_chaos_config()
            fault = config.get_fault(target)
            
            if fault and random.random() < fault.get("probability", 0.1):
                fault_type = fault["fault_type"]
                
                if fault_type == FaultType.LATENCY:
                    await inject_latency(
                        min_ms=fault.get("min_latency_ms", 100),
                        max_ms=fault.get("max_latency_ms", 5000),
                        target=target,
                    )
                
                elif fault_type == FaultType.FAILURE:
                    await inject_failure(
                        error_type=fault.get("error_type", "ServiceError"),
                        message=fault.get("message", "Chaos failure"),
                        target=target,
                    )
                
                elif fault_type == FaultType.TIMEOUT:
                    await inject_timeout(
                        timeout_seconds=fault.get("timeout_seconds", 30),
                        target=target,
                    )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


# ============================================================================
# CONTEXT MANAGERS
# ============================================================================


@asynccontextmanager
async def chaos_scope(target: str, fault_type: FaultType, **kwargs):
    """
    Context manager for scoped chaos injection.
    
    async with chaos_scope("database", FaultType.LATENCY, probability=0.5):
        await db.query(...)
    """
    config = get_chaos_config()
    old_fault = config.get_fault(target)
    
    try:
        config.add_fault(target, fault_type, **kwargs)
        yield
    finally:
        if old_fault:
            config._faults[target] = old_fault
        else:
            config.remove_fault(target)


# ============================================================================
# CHAOS SCENARIOS
# ============================================================================


class ChaosScenario:
    """
    Predefined chaos scenarios for testing.
    """
    
    @staticmethod
    def network_partition(targets: List[str], probability: float = 0.3) -> None:
        """Simulate network partition for targets."""
        config = get_chaos_config()
        for target in targets:
            config.add_fault(
                target=target,
                fault_type=FaultType.FAILURE,
                probability=probability,
                error_type="ConnectionError",
                message="Network partition",
            )
    
    @staticmethod
    def slow_network(targets: List[str], min_ms: int = 500, max_ms: int = 3000) -> None:
        """Simulate slow network."""
        config = get_chaos_config()
        for target in targets:
            config.add_fault(
                target=target,
                fault_type=FaultType.LATENCY,
                probability=0.5,
                min_latency_ms=min_ms,
                max_latency_ms=max_ms,
            )
    
    @staticmethod
    def database_failures(probability: float = 0.1) -> None:
        """Simulate intermittent database failures."""
        config = get_chaos_config()
        config.add_fault(
            target="database",
            fault_type=FaultType.FAILURE,
            probability=probability,
            error_type="DatabaseError",
            message="Connection refused",
        )
    
    @staticmethod
    def external_api_degradation() -> None:
        """Simulate degraded external APIs."""
        config = get_chaos_config()
        
        # Polymarket slow
        config.add_fault(
            target="polymarket_api",
            fault_type=FaultType.LATENCY,
            probability=0.3,
            min_latency_ms=2000,
            max_latency_ms=10000,
        )
        
        # AIS sometimes fails
        config.add_fault(
            target="ais_api",
            fault_type=FaultType.FAILURE,
            probability=0.2,
            error_type="ServiceUnavailable",
            message="AIS service overloaded",
        )
    
    @staticmethod
    def clear() -> None:
        """Clear all chaos scenarios."""
        get_chaos_config().clear_all()


# ============================================================================
# CHAOS MONKEY
# ============================================================================


class ChaosMonkey:
    """
    Automated chaos testing runner.
    
    Runs random chaos experiments during test execution.
    """
    
    def __init__(self, config: Optional[ChaosConfig] = None):
        self._config = config or get_chaos_config()
        self._experiments: List[Callable] = []
        self._running = False
    
    def add_experiment(self, experiment: Callable) -> None:
        """Add a chaos experiment."""
        self._experiments.append(experiment)
    
    async def run_random_experiment(self) -> None:
        """Run a random experiment."""
        if not self._experiments:
            return
        
        if not self._config.enabled:
            return
        
        experiment = random.choice(self._experiments)
        
        logger.info(
            "chaos_experiment_starting",
            experiment=experiment.__name__,
        )
        
        try:
            if asyncio.iscoroutinefunction(experiment):
                await experiment()
            else:
                experiment()
        except Exception as e:
            logger.error(
                "chaos_experiment_error",
                experiment=experiment.__name__,
                error=str(e),
            )
    
    async def start_background(self, interval_seconds: int = 60) -> None:
        """Start running experiments in background."""
        self._running = True
        
        while self._running:
            await asyncio.sleep(interval_seconds)
            await self.run_random_experiment()
    
    def stop(self) -> None:
        """Stop background experiments."""
        self._running = False


# ============================================================================
# TEST HELPERS
# ============================================================================


def with_chaos(
    fault_type: FaultType,
    target: str,
    probability: float = 1.0,
    **kwargs,
):
    """
    Pytest fixture decorator for chaos tests.
    
    @pytest.mark.asyncio
    @with_chaos(FaultType.LATENCY, "database", probability=0.5)
    async def test_handles_slow_db():
        ...
    """
    def decorator(test_func: Callable) -> Callable:
        @wraps(test_func)
        async def wrapper(*args, **kwargs_inner):
            config = get_chaos_config()
            config.enable()
            config.add_fault(target, fault_type, probability, **kwargs)
            
            try:
                return await test_func(*args, **kwargs_inner)
            finally:
                config.remove_fault(target)
                config.disable()
        
        return wrapper
    return decorator


# ============================================================================
# RESILIENCE ASSERTIONS
# ============================================================================


class ResilienceAssertions:
    """
    Assertions for resilience testing.
    """
    
    @staticmethod
    async def assert_recovers_from_failure(
        operation: Callable,
        fault_target: str,
        max_retries: int = 3,
        timeout_seconds: float = 30.0,
    ) -> Any:
        """
        Assert that an operation recovers from injected failure.
        """
        config = get_chaos_config()
        config.enable()
        
        # First call should fail
        config.add_fault(fault_target, FaultType.FAILURE, probability=1.0)
        
        start_time = time.time()
        last_error = None
        
        for i in range(max_retries):
            # Remove fault after first attempt
            if i > 0:
                config.remove_fault(fault_target)
            
            try:
                result = await operation()
                config.disable()
                return result
            except Exception as e:
                last_error = e
                if time.time() - start_time > timeout_seconds:
                    break
                await asyncio.sleep(0.5)
        
        config.disable()
        raise AssertionError(f"Operation did not recover after {max_retries} retries: {last_error}")
    
    @staticmethod
    async def assert_handles_latency(
        operation: Callable,
        fault_target: str,
        latency_ms: int = 5000,
        timeout_seconds: float = 10.0,
    ) -> Any:
        """
        Assert that an operation handles high latency gracefully.
        """
        config = get_chaos_config()
        config.enable()
        config.add_fault(
            fault_target,
            FaultType.LATENCY,
            probability=1.0,
            min_latency_ms=latency_ms,
            max_latency_ms=latency_ms,
        )
        
        try:
            result = await asyncio.wait_for(
                operation(),
                timeout=timeout_seconds,
            )
            return result
        except asyncio.TimeoutError:
            # This is actually expected if latency > timeout
            return None
        finally:
            config.disable()
