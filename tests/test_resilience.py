"""
Tests for Resilience Patterns.

Tests:
- Circuit breaker behavior
- Retry with exponential backoff
- Bulkhead isolation
- Timeout handling
- Fallback execution
"""

import asyncio
import pytest
import time

from app.core.resilience import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerRegistry,
    CircuitOpenError,
    CircuitState,
    RetryPolicy,
    RetryConfig,
    Bulkhead,
    BulkheadFullError,
    ResiliencePolicy,
    retry,
    timeout,
    fallback,
)


# ============================================================================
# CIRCUIT BREAKER TESTS
# ============================================================================


class TestCircuitBreaker:
    """Tests for CircuitBreaker."""
    
    @pytest.fixture
    def breaker(self):
        """Create a circuit breaker with low thresholds for testing."""
        config = CircuitBreakerConfig(
            failure_threshold=3,
            success_threshold=2,
            timeout_seconds=1.0,  # Short timeout for tests
            window_size=5,
        )
        return CircuitBreaker("test", config)
    
    @pytest.mark.asyncio
    async def test_starts_closed(self, breaker):
        """Circuit breaker starts in closed state."""
        assert breaker.state == CircuitState.CLOSED
        assert breaker.is_closed
        assert not breaker.is_open
    
    @pytest.mark.asyncio
    async def test_opens_after_failures(self, breaker):
        """Circuit opens after threshold failures."""
        call_count = 0
        
        @breaker
        async def failing_func():
            nonlocal call_count
            call_count += 1
            raise Exception("Test failure")
        
        # Make 3 failing calls
        for _ in range(3):
            with pytest.raises(Exception):
                await failing_func()
        
        assert breaker.state == CircuitState.OPEN
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_rejects_when_open(self, breaker):
        """Open circuit rejects calls immediately."""
        # Force open state
        @breaker
        async def failing_func():
            raise Exception("Test failure")
        
        for _ in range(3):
            with pytest.raises(Exception):
                await failing_func()
        
        # Now circuit should reject
        with pytest.raises(CircuitOpenError):
            await failing_func()
        
        # Verify rejection was tracked
        assert breaker.metrics.rejected_calls >= 1
    
    @pytest.mark.asyncio
    async def test_half_open_after_timeout(self, breaker):
        """Circuit transitions to half-open after timeout."""
        # Open the circuit
        @breaker
        async def failing_func():
            raise Exception("Test failure")
        
        for _ in range(3):
            with pytest.raises(Exception):
                await failing_func()
        
        assert breaker.state == CircuitState.OPEN
        
        # Wait for timeout
        await asyncio.sleep(1.1)
        
        # Should be half-open now
        assert breaker.state == CircuitState.HALF_OPEN
    
    @pytest.mark.asyncio
    async def test_closes_after_successes(self, breaker):
        """Circuit closes after successful calls in half-open."""
        # Open the circuit
        @breaker
        async def flexible_func(should_fail: bool):
            if should_fail:
                raise Exception("Test failure")
            return "success"
        
        for _ in range(3):
            with pytest.raises(Exception):
                await flexible_func(True)
        
        # Wait for half-open
        await asyncio.sleep(1.1)
        
        # Make successful calls
        await flexible_func(False)
        await flexible_func(False)
        
        assert breaker.state == CircuitState.CLOSED
    
    @pytest.mark.asyncio
    async def test_reopens_on_failure_in_half_open(self, breaker):
        """Circuit reopens on failure in half-open state."""
        @breaker
        async def failing_func():
            raise Exception("Test failure")
        
        # Open circuit
        for _ in range(3):
            with pytest.raises(Exception):
                await failing_func()
        
        # Wait for half-open
        await asyncio.sleep(1.1)
        
        # Fail in half-open
        with pytest.raises(Exception):
            await failing_func()
        
        assert breaker.state == CircuitState.OPEN
    
    def test_metrics_tracking(self, breaker):
        """Metrics are tracked correctly."""
        assert breaker.metrics.total_calls == 0
        assert breaker.metrics.successful_calls == 0
        assert breaker.metrics.failed_calls == 0
    
    def test_registry(self):
        """Circuit breaker registry works."""
        breaker1 = CircuitBreakerRegistry.get_or_create("service1")
        breaker2 = CircuitBreakerRegistry.get_or_create("service1")
        breaker3 = CircuitBreakerRegistry.get_or_create("service2")
        
        assert breaker1 is breaker2  # Same name = same instance
        assert breaker1 is not breaker3  # Different name = different instance


# ============================================================================
# RETRY TESTS
# ============================================================================


class TestRetryPolicy:
    """Tests for RetryPolicy."""
    
    @pytest.mark.asyncio
    async def test_succeeds_without_retry(self):
        """Successful call doesn't retry."""
        call_count = 0
        
        @retry(max_attempts=3)
        async def success_func():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = await success_func()
        
        assert result == "success"
        assert call_count == 1
    
    @pytest.mark.asyncio
    async def test_retries_on_failure(self):
        """Failed calls are retried."""
        call_count = 0
        
        @retry(max_attempts=3, base_delay_seconds=0.01)
        async def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Temporary failure")
            return "success"
        
        result = await flaky_func()
        
        assert result == "success"
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_gives_up_after_max_attempts(self):
        """Gives up after max retry attempts."""
        call_count = 0
        
        @retry(max_attempts=3, base_delay_seconds=0.01)
        async def always_fails():
            nonlocal call_count
            call_count += 1
            raise Exception("Persistent failure")
        
        with pytest.raises(Exception, match="Persistent failure"):
            await always_fails()
        
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_exponential_backoff(self):
        """Delay increases exponentially."""
        config = RetryConfig(
            max_attempts=4,
            base_delay_seconds=0.1,
            exponential_base=2.0,
            jitter=False,
        )
        policy = RetryPolicy(config)
        
        delays = [policy.calculate_delay(i) for i in range(4)]
        
        assert delays[0] == pytest.approx(0.1, rel=0.01)
        assert delays[1] == pytest.approx(0.2, rel=0.01)
        assert delays[2] == pytest.approx(0.4, rel=0.01)
        assert delays[3] == pytest.approx(0.8, rel=0.01)
    
    @pytest.mark.asyncio
    async def test_max_delay_cap(self):
        """Delay is capped at max_delay."""
        config = RetryConfig(
            max_attempts=10,
            base_delay_seconds=1.0,
            max_delay_seconds=5.0,
            exponential_base=2.0,
            jitter=False,
        )
        policy = RetryPolicy(config)
        
        delay = policy.calculate_delay(10)
        
        assert delay == 5.0


# ============================================================================
# BULKHEAD TESTS
# ============================================================================


class TestBulkhead:
    """Tests for Bulkhead."""
    
    @pytest.fixture
    def bulkhead(self):
        """Create a bulkhead with low concurrency for testing."""
        return Bulkhead(
            name="test",
            max_concurrent=2,
            max_waiting=2,
            wait_timeout_seconds=0.5,
        )
    
    @pytest.mark.asyncio
    async def test_allows_within_limit(self, bulkhead):
        """Allows calls within concurrency limit."""
        call_count = 0
        
        @bulkhead
        async def quick_func():
            nonlocal call_count
            call_count += 1
            await asyncio.sleep(0.01)
            return "done"
        
        results = await asyncio.gather(
            quick_func(),
            quick_func(),
        )
        
        assert all(r == "done" for r in results)
        assert call_count == 2
    
    @pytest.mark.asyncio
    async def test_queues_excess_calls(self, bulkhead):
        """Excess calls are queued."""
        active = 0
        max_active = 0
        
        @bulkhead
        async def slow_func():
            nonlocal active, max_active
            active += 1
            max_active = max(max_active, active)
            await asyncio.sleep(0.1)
            active -= 1
            return "done"
        
        # Start 4 calls (2 will run, 2 will queue)
        results = await asyncio.gather(
            slow_func(),
            slow_func(),
            slow_func(),
            slow_func(),
        )
        
        assert all(r == "done" for r in results)
        assert max_active <= 2  # Never exceeded limit
    
    @pytest.mark.asyncio
    async def test_rejects_when_full(self, bulkhead):
        """Rejects when both running and waiting are full."""
        @bulkhead
        async def very_slow_func():
            await asyncio.sleep(10)  # Very slow
        
        # Start calls to fill up the bulkhead
        tasks = []
        for _ in range(4):  # 2 running + 2 waiting = full
            tasks.append(asyncio.create_task(very_slow_func()))
        
        await asyncio.sleep(0.1)  # Let tasks start
        
        # This call should be rejected
        with pytest.raises(BulkheadFullError):
            await very_slow_func()
        
        # Cancel tasks
        for task in tasks:
            task.cancel()


# ============================================================================
# TIMEOUT TESTS
# ============================================================================


class TestTimeout:
    """Tests for timeout decorator."""
    
    @pytest.mark.asyncio
    async def test_completes_within_timeout(self):
        """Function completing within timeout succeeds."""
        @timeout(1.0)
        async def quick_func():
            await asyncio.sleep(0.1)
            return "done"
        
        result = await quick_func()
        assert result == "done"
    
    @pytest.mark.asyncio
    async def test_raises_on_timeout(self):
        """Function exceeding timeout raises TimeoutError."""
        @timeout(0.1)
        async def slow_func():
            await asyncio.sleep(1.0)
            return "done"
        
        with pytest.raises(TimeoutError):
            await slow_func()


# ============================================================================
# FALLBACK TESTS
# ============================================================================


class TestFallback:
    """Tests for fallback decorator."""
    
    @pytest.mark.asyncio
    async def test_uses_primary_on_success(self):
        """Uses primary function when it succeeds."""
        def fallback_func():
            return "fallback"
        
        @fallback(fallback_func)
        async def primary_func():
            return "primary"
        
        result = await primary_func()
        assert result == "primary"
    
    @pytest.mark.asyncio
    async def test_uses_fallback_on_failure(self):
        """Uses fallback when primary fails."""
        def fallback_func():
            return "fallback"
        
        @fallback(fallback_func)
        async def failing_func():
            raise Exception("Primary failed")
        
        result = await failing_func()
        assert result == "fallback"
    
    @pytest.mark.asyncio
    async def test_async_fallback(self):
        """Works with async fallback functions."""
        async def async_fallback():
            return "async fallback"
        
        @fallback(async_fallback)
        async def failing_func():
            raise Exception("Primary failed")
        
        result = await failing_func()
        assert result == "async fallback"


# ============================================================================
# COMBINED RESILIENCE TESTS
# ============================================================================


class TestResiliencePolicy:
    """Tests for combined resilience policy."""
    
    @pytest.mark.asyncio
    async def test_combined_policy(self):
        """Combined policy applies all patterns."""
        call_count = 0
        
        policy = ResiliencePolicy(
            name="test",
            circuit_breaker=CircuitBreakerConfig(
                failure_threshold=5,
                timeout_seconds=30,
            ),
            retry_config=RetryConfig(
                max_attempts=2,
                base_delay_seconds=0.01,
            ),
            timeout_seconds=5.0,
        )
        
        @policy
        async def test_func():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = await test_func()
        
        assert result == "success"
        assert call_count == 1
    
    def test_policy_status(self):
        """Policy status includes all components."""
        policy = ResiliencePolicy(
            name="test",
            circuit_breaker=CircuitBreakerConfig(),
            bulkhead_max_concurrent=10,
        )
        
        status = policy.get_status()
        
        assert status["name"] == "test"
        assert "circuit_breaker" in status
        assert "bulkhead" in status
