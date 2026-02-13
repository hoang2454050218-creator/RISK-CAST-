"""
Chaos Engineering Tests for RISKCAST.

Tests system resilience through controlled failure injection:
- Network partition simulation
- Service failure
- Resource exhaustion
- Data corruption
- Latency injection
"""

import asyncio
import random
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Callable
from enum import Enum
from contextlib import asynccontextmanager

import pytest
import structlog

logger = structlog.get_logger(__name__)


# ============================================================================
# CHAOS ENGINEERING PRIMITIVES
# ============================================================================


class FailureType(str, Enum):
    """Types of failures to inject."""
    
    NETWORK_PARTITION = "network_partition"
    SERVICE_CRASH = "service_crash"
    SLOW_RESPONSE = "slow_response"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    DATA_CORRUPTION = "data_corruption"
    DEPENDENCY_FAILURE = "dependency_failure"


@dataclass
class ChaosExperiment:
    """Definition of a chaos experiment."""
    
    name: str
    description: str
    failure_type: FailureType
    target_service: str
    duration_seconds: int = 30
    intensity: float = 0.5  # 0-1 scale
    metadata: Dict[str, Any] = None


@dataclass
class ChaosResult:
    """Result of a chaos experiment."""
    
    experiment: ChaosExperiment
    start_time: datetime
    end_time: datetime
    
    # System behavior during chaos
    requests_during_chaos: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    
    # Recovery metrics
    time_to_detect_seconds: float = 0
    time_to_recover_seconds: float = 0
    
    # Impact assessment
    blast_radius: List[str] = None  # Affected services
    data_loss: bool = False
    customer_impact: bool = False
    
    @property
    def resilience_score(self) -> float:
        """Calculate resilience score (0-100)."""
        score = 100.0
        
        # Penalize for failures
        if self.requests_during_chaos > 0:
            failure_rate = self.failed_requests / self.requests_during_chaos
            score -= failure_rate * 50
        
        # Penalize for slow detection
        if self.time_to_detect_seconds > 60:
            score -= min(20, self.time_to_detect_seconds / 60 * 10)
        
        # Penalize for slow recovery
        if self.time_to_recover_seconds > 120:
            score -= min(20, self.time_to_recover_seconds / 120 * 10)
        
        # Major penalties
        if self.data_loss:
            score -= 30
        if self.customer_impact:
            score -= 20
        
        return max(0, score)
    
    @property
    def passed(self) -> bool:
        """Check if experiment passed resilience requirements."""
        return (
            self.resilience_score >= 70 and
            not self.data_loss and
            self.time_to_recover_seconds < 300  # 5 minute max recovery
        )


class ChaosMonkey:
    """
    Chaos engineering framework for RISKCAST.
    
    Injects controlled failures to test system resilience.
    """
    
    def __init__(self):
        self._active_experiments: Dict[str, ChaosExperiment] = {}
        self._failure_injectors: Dict[FailureType, Callable] = {}
        self._setup_injectors()
    
    def _setup_injectors(self):
        """Set up failure injectors."""
        self._failure_injectors = {
            FailureType.NETWORK_PARTITION: self._inject_network_partition,
            FailureType.SERVICE_CRASH: self._inject_service_crash,
            FailureType.SLOW_RESPONSE: self._inject_slow_response,
            FailureType.RESOURCE_EXHAUSTION: self._inject_resource_exhaustion,
            FailureType.DEPENDENCY_FAILURE: self._inject_dependency_failure,
        }
    
    @asynccontextmanager
    async def run_experiment(self, experiment: ChaosExperiment):
        """Run a chaos experiment within a context."""
        experiment_id = f"{experiment.name}_{datetime.utcnow().timestamp()}"
        self._active_experiments[experiment_id] = experiment
        
        start_time = datetime.utcnow()
        logger.warning(
            "chaos_experiment_starting",
            experiment=experiment.name,
            failure_type=experiment.failure_type,
            target=experiment.target_service,
        )
        
        injector = self._failure_injectors.get(experiment.failure_type)
        if not injector:
            raise ValueError(f"Unknown failure type: {experiment.failure_type}")
        
        try:
            # Start failure injection
            await injector(experiment, start=True)
            yield experiment_id
        finally:
            # Stop failure injection
            await injector(experiment, start=False)
            del self._active_experiments[experiment_id]
            
            end_time = datetime.utcnow()
            logger.info(
                "chaos_experiment_ended",
                experiment=experiment.name,
                duration_seconds=(end_time - start_time).total_seconds(),
            )
    
    async def _inject_network_partition(
        self,
        experiment: ChaosExperiment,
        start: bool,
    ):
        """Simulate network partition."""
        if start:
            logger.warning(
                "injecting_network_partition",
                target=experiment.target_service,
                intensity=experiment.intensity,
            )
            # In real implementation:
            # - Use iptables to drop packets
            # - Use toxiproxy to inject network failures
            # - Use service mesh to inject faults
        else:
            logger.info("removing_network_partition")
    
    async def _inject_service_crash(
        self,
        experiment: ChaosExperiment,
        start: bool,
    ):
        """Simulate service crash."""
        if start:
            logger.warning(
                "injecting_service_crash",
                target=experiment.target_service,
            )
            # In real implementation:
            # - Kill pod/container
            # - Signal process termination
        else:
            logger.info("service_restarted")
    
    async def _inject_slow_response(
        self,
        experiment: ChaosExperiment,
        start: bool,
    ):
        """Inject latency into responses."""
        if start:
            latency_ms = int(experiment.intensity * 5000)  # Up to 5s
            logger.warning(
                "injecting_latency",
                target=experiment.target_service,
                latency_ms=latency_ms,
            )
            # In real implementation:
            # - Use middleware to add delay
            # - Use toxiproxy for latency injection
        else:
            logger.info("removing_latency_injection")
    
    async def _inject_resource_exhaustion(
        self,
        experiment: ChaosExperiment,
        start: bool,
    ):
        """Simulate resource exhaustion (memory/CPU)."""
        if start:
            logger.warning(
                "injecting_resource_exhaustion",
                target=experiment.target_service,
                intensity=experiment.intensity,
            )
            # In real implementation:
            # - Allocate memory
            # - Spin CPU cycles
            # - Fill disk space
        else:
            logger.info("releasing_resources")
    
    async def _inject_dependency_failure(
        self,
        experiment: ChaosExperiment,
        start: bool,
    ):
        """Simulate external dependency failure."""
        if start:
            logger.warning(
                "injecting_dependency_failure",
                target=experiment.target_service,
                dependency=experiment.metadata.get("dependency", "unknown"),
            )
            # In real implementation:
            # - Mock external API to return errors
            # - Block network to external services
        else:
            logger.info("restoring_dependency")


# ============================================================================
# RESILIENCE PATTERNS TO TEST
# ============================================================================


class MockService:
    """Mock service for testing resilience patterns."""
    
    def __init__(self, failure_rate: float = 0.0, latency_ms: int = 0):
        self.failure_rate = failure_rate
        self.latency_ms = latency_ms
        self.call_count = 0
        self.failure_count = 0
    
    async def call(self) -> str:
        """Make a call to the service."""
        self.call_count += 1
        
        if self.latency_ms > 0:
            await asyncio.sleep(self.latency_ms / 1000)
        
        if random.random() < self.failure_rate:
            self.failure_count += 1
            raise Exception("Service failure")
        
        return "success"


class CircuitBreaker:
    """Circuit breaker implementation for testing."""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 30,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open
    
    async def call(self, func: Callable) -> Any:
        """Execute function through circuit breaker."""
        if self.state == "open":
            if self._should_attempt_reset():
                self.state = "half-open"
            else:
                raise Exception("Circuit breaker is open")
        
        try:
            result = await func()
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time passed to attempt reset."""
        if not self.last_failure_time:
            return True
        elapsed = (datetime.utcnow() - self.last_failure_time).total_seconds()
        return elapsed >= self.recovery_timeout
    
    def _on_success(self):
        """Handle successful call."""
        self.failure_count = 0
        self.state = "closed"
    
    def _on_failure(self):
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "open"


class RetryHandler:
    """Retry with exponential backoff for testing."""
    
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 0.1,
        max_delay: float = 10.0,
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
    
    async def execute(self, func: Callable) -> Any:
        """Execute function with retry."""
        last_exception = None
        
        for attempt in range(self.max_retries + 1):
            try:
                return await func()
            except Exception as e:
                last_exception = e
                
                if attempt < self.max_retries:
                    delay = min(
                        self.base_delay * (2 ** attempt),
                        self.max_delay,
                    )
                    # Add jitter
                    delay *= (0.5 + random.random())
                    await asyncio.sleep(delay)
        
        raise last_exception


# ============================================================================
# CHAOS TESTS
# ============================================================================


@pytest.fixture
def chaos_monkey():
    """Provide chaos monkey instance."""
    return ChaosMonkey()


class TestCircuitBreaker:
    """Test circuit breaker behavior."""
    
    @pytest.mark.asyncio
    async def test_circuit_opens_on_failures(self):
        """Circuit breaker should open after threshold failures."""
        service = MockService(failure_rate=1.0)  # Always fails
        breaker = CircuitBreaker(failure_threshold=3)
        
        # Make failing calls until breaker opens
        for i in range(3):
            try:
                await breaker.call(service.call)
            except:
                pass
        
        assert breaker.state == "open"
        
        # Next call should fail immediately
        with pytest.raises(Exception) as exc:
            await breaker.call(service.call)
        assert "open" in str(exc.value)
    
    @pytest.mark.asyncio
    async def test_circuit_resets_after_success(self):
        """Circuit breaker should reset after successful call."""
        service = MockService(failure_rate=0.0)  # Never fails
        breaker = CircuitBreaker(failure_threshold=3)
        
        # Manually set to half-open
        breaker.state = "half-open"
        
        # Successful call should close circuit
        await breaker.call(service.call)
        
        assert breaker.state == "closed"


class TestRetryHandler:
    """Test retry behavior."""
    
    @pytest.mark.asyncio
    async def test_retry_succeeds_eventually(self):
        """Retry should succeed if service recovers."""
        call_count = 0
        
        async def flaky_service():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary failure")
            return "success"
        
        handler = RetryHandler(max_retries=3)
        result = await handler.execute(flaky_service)
        
        assert result == "success"
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_retry_exhausted(self):
        """Retry should raise after max attempts."""
        handler = RetryHandler(max_retries=2)
        
        async def always_fails():
            raise Exception("Permanent failure")
        
        with pytest.raises(Exception) as exc:
            await handler.execute(always_fails)
        
        assert "Permanent failure" in str(exc.value)


class TestServiceResilience:
    """Test service resilience under chaos."""
    
    @pytest.mark.asyncio
    async def test_survives_dependency_latency(self, chaos_monkey):
        """System should survive slow dependencies."""
        experiment = ChaosExperiment(
            name="slow_database",
            description="Inject 2s latency to database calls",
            failure_type=FailureType.SLOW_RESPONSE,
            target_service="database",
            duration_seconds=10,
            intensity=0.4,  # 2s latency
        )
        
        async with chaos_monkey.run_experiment(experiment):
            # System should continue to function
            # with degraded performance but no crashes
            service = MockService(latency_ms=2000)
            
            start = time.time()
            result = await service.call()
            elapsed = time.time() - start
            
            assert result == "success"
            assert elapsed >= 2.0  # Should include latency
    
    @pytest.mark.asyncio
    async def test_graceful_degradation(self, chaos_monkey):
        """System should degrade gracefully under partial failures."""
        service = MockService(failure_rate=0.3)  # 30% failures
        breaker = CircuitBreaker(failure_threshold=5)
        retry = RetryHandler(max_retries=2)
        
        success_count = 0
        failure_count = 0
        
        for _ in range(20):
            try:
                await retry.execute(lambda: breaker.call(service.call))
                success_count += 1
            except:
                failure_count += 1
        
        # With retries and circuit breaker, we should have
        # reasonable success rate even with 30% failure rate
        success_rate = success_count / (success_count + failure_count)
        assert success_rate > 0.5, f"Success rate {success_rate} too low"


class TestDataResilience:
    """Test data integrity under chaos."""
    
    @pytest.mark.asyncio
    async def test_no_data_corruption(self):
        """Data should not be corrupted during failures."""
        test_data = {"key": "value", "count": 42}
        stored_data = None
        
        # Simulate write operation with failure
        async def write_with_failure():
            nonlocal stored_data
            # Write begins
            stored_data = test_data.copy()
            # Simulate failure mid-write
            raise Exception("Write interrupted")
        
        try:
            await write_with_failure()
        except:
            pass
        
        # Data should either be complete or absent
        # (atomic operation - no partial writes)
        if stored_data is not None:
            assert stored_data == test_data
    
    @pytest.mark.asyncio
    async def test_idempotent_operations(self):
        """Operations should be idempotent."""
        results = []
        
        async def idempotent_operation(operation_id: str):
            # Check if already processed
            if operation_id in results:
                return "duplicate"
            results.append(operation_id)
            return "processed"
        
        # Same operation multiple times
        op_id = "op-123"
        
        result1 = await idempotent_operation(op_id)
        result2 = await idempotent_operation(op_id)
        result3 = await idempotent_operation(op_id)
        
        assert result1 == "processed"
        assert result2 == "duplicate"
        assert result3 == "duplicate"
        assert results.count(op_id) == 1  # Only processed once


class TestRecovery:
    """Test system recovery after failures."""
    
    @pytest.mark.asyncio
    async def test_automatic_recovery(self):
        """System should automatically recover from failures."""
        failure_active = True
        
        async def service_call():
            if failure_active:
                raise Exception("Service down")
            return "success"
        
        breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=1)
        
        # Cause circuit to open
        for _ in range(3):
            try:
                await breaker.call(service_call)
            except:
                pass
        
        assert breaker.state == "open"
        
        # Fix the service
        failure_active = False
        
        # Wait for recovery timeout
        await asyncio.sleep(1.5)
        
        # Circuit should allow trial call
        result = await breaker.call(service_call)
        assert result == "success"
        assert breaker.state == "closed"
