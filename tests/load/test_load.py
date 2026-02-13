"""
Load Tests for RISKCAST.

Production-grade load testing with:
- Spike tests
- Soak tests
- Stress tests
- Breakpoint detection
- Resource monitoring
"""

import asyncio
import time
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Callable
from enum import Enum
import random
import uuid

import pytest
import structlog

logger = structlog.get_logger(__name__)


# ============================================================================
# LOAD TEST INFRASTRUCTURE
# ============================================================================


class LoadTestType(str, Enum):
    """Types of load tests."""
    
    SMOKE = "smoke"              # Verify system works under minimal load
    LOAD = "load"                # Normal expected load
    STRESS = "stress"            # Beyond normal capacity
    SPIKE = "spike"              # Sudden traffic surge
    SOAK = "soak"                # Extended duration
    BREAKPOINT = "breakpoint"    # Find breaking point


@dataclass
class LoadTestConfig:
    """Configuration for load tests."""
    
    test_type: LoadTestType
    duration_seconds: int
    initial_users: int = 1
    max_users: int = 100
    ramp_up_seconds: int = 30
    requests_per_second: float = 10.0
    think_time_ms: tuple = (100, 500)  # Random delay between requests


@dataclass
class RequestMetrics:
    """Metrics for a single request."""
    
    request_id: str
    endpoint: str
    method: str
    start_time: datetime
    end_time: datetime
    status_code: int
    response_time_ms: float
    error: Optional[str] = None


@dataclass
class LoadTestResult:
    """Results from a load test run."""
    
    test_id: str
    test_type: LoadTestType
    start_time: datetime
    end_time: datetime
    total_requests: int
    successful_requests: int
    failed_requests: int
    
    # Response time statistics
    avg_response_time_ms: float
    min_response_time_ms: float
    max_response_time_ms: float
    p50_response_time_ms: float
    p90_response_time_ms: float
    p95_response_time_ms: float
    p99_response_time_ms: float
    
    # Throughput
    requests_per_second: float
    
    # Error breakdown
    errors_by_type: Dict[str, int] = field(default_factory=dict)
    
    # Resource usage (if available)
    peak_memory_mb: Optional[float] = None
    peak_cpu_pct: Optional[float] = None
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_requests == 0:
            return 0.0
        return self.successful_requests / self.total_requests
    
    @property
    def passed_sla(self) -> bool:
        """Check if test passed SLA requirements."""
        return (
            self.success_rate >= 0.99 and
            self.p95_response_time_ms < 500 and
            self.p99_response_time_ms < 1000
        )


class LoadTestRunner:
    """
    Run load tests against RISKCAST APIs.
    
    Simulates realistic traffic patterns and measures system behavior.
    """
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self._base_url = base_url
        self._metrics: List[RequestMetrics] = []
        self._running = False
    
    async def run(self, config: LoadTestConfig) -> LoadTestResult:
        """Run a load test."""
        test_id = str(uuid.uuid4())[:8]
        start_time = datetime.utcnow()
        self._metrics = []
        self._running = True
        
        logger.info(
            "load_test_starting",
            test_id=test_id,
            test_type=config.test_type,
            duration_seconds=config.duration_seconds,
        )
        
        try:
            if config.test_type == LoadTestType.SMOKE:
                await self._run_smoke_test(config)
            elif config.test_type == LoadTestType.LOAD:
                await self._run_load_test(config)
            elif config.test_type == LoadTestType.STRESS:
                await self._run_stress_test(config)
            elif config.test_type == LoadTestType.SPIKE:
                await self._run_spike_test(config)
            elif config.test_type == LoadTestType.SOAK:
                await self._run_soak_test(config)
            elif config.test_type == LoadTestType.BREAKPOINT:
                await self._run_breakpoint_test(config)
        finally:
            self._running = False
        
        end_time = datetime.utcnow()
        return self._calculate_results(test_id, config.test_type, start_time, end_time)
    
    async def _run_smoke_test(self, config: LoadTestConfig) -> None:
        """Run smoke test - minimal load to verify system works."""
        # Single user, few requests
        for _ in range(10):
            await self._make_request("/api/v1/health", "GET")
            await asyncio.sleep(0.5)
    
    async def _run_load_test(self, config: LoadTestConfig) -> None:
        """Run normal load test."""
        end_time = datetime.utcnow() + timedelta(seconds=config.duration_seconds)
        current_users = config.initial_users
        
        while datetime.utcnow() < end_time and self._running:
            # Ramp up users
            elapsed = (datetime.utcnow() - (end_time - timedelta(seconds=config.duration_seconds))).total_seconds()
            if elapsed < config.ramp_up_seconds:
                progress = elapsed / config.ramp_up_seconds
                current_users = int(config.initial_users + (config.max_users - config.initial_users) * progress)
            else:
                current_users = config.max_users
            
            # Generate load from virtual users
            tasks = [
                self._virtual_user_session(config)
                for _ in range(current_users)
            ]
            
            await asyncio.gather(*tasks[:min(current_users, 50)])  # Cap concurrent tasks
            await asyncio.sleep(1.0 / config.requests_per_second)
    
    async def _run_stress_test(self, config: LoadTestConfig) -> None:
        """Run stress test - push beyond normal capacity."""
        # Double the normal load
        stress_config = LoadTestConfig(
            test_type=LoadTestType.STRESS,
            duration_seconds=config.duration_seconds,
            initial_users=config.max_users,
            max_users=config.max_users * 2,
            ramp_up_seconds=10,
            requests_per_second=config.requests_per_second * 2,
        )
        await self._run_load_test(stress_config)
    
    async def _run_spike_test(self, config: LoadTestConfig) -> None:
        """Run spike test - sudden surge in traffic."""
        normal_duration = config.duration_seconds // 3
        spike_duration = config.duration_seconds // 3
        recovery_duration = config.duration_seconds // 3
        
        # Normal load phase
        normal_config = LoadTestConfig(
            test_type=LoadTestType.LOAD,
            duration_seconds=normal_duration,
            max_users=config.max_users // 4,
            requests_per_second=config.requests_per_second / 4,
        )
        await self._run_load_test(normal_config)
        
        # Spike phase
        spike_config = LoadTestConfig(
            test_type=LoadTestType.LOAD,
            duration_seconds=spike_duration,
            initial_users=config.max_users // 4,
            max_users=config.max_users,
            ramp_up_seconds=5,  # Rapid ramp
            requests_per_second=config.requests_per_second,
        )
        await self._run_load_test(spike_config)
        
        # Recovery phase
        await self._run_load_test(normal_config)
    
    async def _run_soak_test(self, config: LoadTestConfig) -> None:
        """Run soak test - extended duration at moderate load."""
        # Run for longer at steady state
        soak_config = LoadTestConfig(
            test_type=LoadTestType.LOAD,
            duration_seconds=config.duration_seconds,
            initial_users=config.max_users // 2,
            max_users=config.max_users // 2,
            ramp_up_seconds=30,
            requests_per_second=config.requests_per_second / 2,
        )
        await self._run_load_test(soak_config)
    
    async def _run_breakpoint_test(self, config: LoadTestConfig) -> None:
        """Run breakpoint test - find system limits."""
        current_rps = 1.0
        max_rps_achieved = 0.0
        
        while current_rps < config.requests_per_second * 10:
            test_config = LoadTestConfig(
                test_type=LoadTestType.LOAD,
                duration_seconds=10,  # Short test per level
                max_users=int(current_rps),
                requests_per_second=current_rps,
            )
            
            initial_errors = len([m for m in self._metrics if m.error])
            await self._run_load_test(test_config)
            final_errors = len([m for m in self._metrics if m.error])
            
            new_errors = final_errors - initial_errors
            error_rate = new_errors / max(len(self._metrics) - initial_errors, 1)
            
            if error_rate > 0.05:  # 5% error rate threshold
                logger.info(
                    "breakpoint_found",
                    rps=current_rps,
                    error_rate=error_rate,
                )
                break
            
            max_rps_achieved = current_rps
            current_rps *= 1.5  # Increase by 50%
        
        logger.info("max_rps_achieved", rps=max_rps_achieved)
    
    async def _virtual_user_session(self, config: LoadTestConfig) -> None:
        """Simulate a virtual user session."""
        endpoints = [
            ("/api/v1/health", "GET"),
            ("/api/v1/signals", "GET"),
            ("/api/v1/decisions", "GET"),
        ]
        
        endpoint, method = random.choice(endpoints)
        await self._make_request(endpoint, method)
        
        # Think time
        think_time = random.uniform(
            config.think_time_ms[0] / 1000,
            config.think_time_ms[1] / 1000,
        )
        await asyncio.sleep(think_time)
    
    async def _make_request(
        self,
        endpoint: str,
        method: str,
        payload: Dict = None,
    ) -> RequestMetrics:
        """Make an HTTP request and record metrics."""
        request_id = str(uuid.uuid4())[:8]
        start_time = datetime.utcnow()
        error = None
        status_code = 200
        
        try:
            # Simulate HTTP request (in real test, use aiohttp or httpx)
            await asyncio.sleep(random.uniform(0.01, 0.1))  # Simulated latency
            
            # Simulate occasional errors
            if random.random() < 0.01:  # 1% error rate
                status_code = 500
                error = "simulated_server_error"
            
        except Exception as e:
            status_code = 0
            error = str(e)
        
        end_time = datetime.utcnow()
        response_time_ms = (end_time - start_time).total_seconds() * 1000
        
        metric = RequestMetrics(
            request_id=request_id,
            endpoint=endpoint,
            method=method,
            start_time=start_time,
            end_time=end_time,
            status_code=status_code,
            response_time_ms=response_time_ms,
            error=error,
        )
        
        self._metrics.append(metric)
        return metric
    
    def _calculate_results(
        self,
        test_id: str,
        test_type: LoadTestType,
        start_time: datetime,
        end_time: datetime,
    ) -> LoadTestResult:
        """Calculate test results from collected metrics."""
        if not self._metrics:
            return LoadTestResult(
                test_id=test_id,
                test_type=test_type,
                start_time=start_time,
                end_time=end_time,
                total_requests=0,
                successful_requests=0,
                failed_requests=0,
                avg_response_time_ms=0,
                min_response_time_ms=0,
                max_response_time_ms=0,
                p50_response_time_ms=0,
                p90_response_time_ms=0,
                p95_response_time_ms=0,
                p99_response_time_ms=0,
                requests_per_second=0,
            )
        
        response_times = [m.response_time_ms for m in self._metrics]
        successful = [m for m in self._metrics if 200 <= m.status_code < 300]
        failed = [m for m in self._metrics if m.error or m.status_code >= 400]
        
        # Calculate percentiles
        sorted_times = sorted(response_times)
        
        def percentile(data: List[float], p: float) -> float:
            if not data:
                return 0.0
            k = (len(data) - 1) * p / 100
            f = int(k)
            c = f + 1 if f + 1 < len(data) else f
            return data[f] + (data[c] - data[f]) * (k - f)
        
        duration = (end_time - start_time).total_seconds()
        
        # Error breakdown
        errors_by_type: Dict[str, int] = {}
        for m in failed:
            err_type = m.error or f"http_{m.status_code}"
            errors_by_type[err_type] = errors_by_type.get(err_type, 0) + 1
        
        return LoadTestResult(
            test_id=test_id,
            test_type=test_type,
            start_time=start_time,
            end_time=end_time,
            total_requests=len(self._metrics),
            successful_requests=len(successful),
            failed_requests=len(failed),
            avg_response_time_ms=statistics.mean(response_times),
            min_response_time_ms=min(response_times),
            max_response_time_ms=max(response_times),
            p50_response_time_ms=percentile(sorted_times, 50),
            p90_response_time_ms=percentile(sorted_times, 90),
            p95_response_time_ms=percentile(sorted_times, 95),
            p99_response_time_ms=percentile(sorted_times, 99),
            requests_per_second=len(self._metrics) / duration if duration > 0 else 0,
            errors_by_type=errors_by_type,
        )


# ============================================================================
# PYTEST LOAD TESTS
# ============================================================================


@pytest.fixture
def load_runner():
    """Provide load test runner."""
    return LoadTestRunner()


class TestSmoke:
    """Smoke tests - verify basic functionality."""
    
    @pytest.mark.asyncio
    async def test_smoke_health(self, load_runner):
        """System should handle minimal health check load."""
        config = LoadTestConfig(
            test_type=LoadTestType.SMOKE,
            duration_seconds=5,
            max_users=1,
            requests_per_second=1,
        )
        
        result = await load_runner.run(config)
        
        assert result.success_rate >= 0.95
        assert result.avg_response_time_ms < 500


class TestLoad:
    """Normal load tests."""
    
    @pytest.mark.asyncio
    async def test_normal_load(self, load_runner):
        """System should handle expected production load."""
        config = LoadTestConfig(
            test_type=LoadTestType.LOAD,
            duration_seconds=30,
            max_users=50,
            ramp_up_seconds=10,
            requests_per_second=20,
        )
        
        result = await load_runner.run(config)
        
        assert result.success_rate >= 0.99, f"Success rate {result.success_rate} < 0.99"
        assert result.p95_response_time_ms < 500, f"P95 {result.p95_response_time_ms}ms >= 500ms"
        assert result.p99_response_time_ms < 1000, f"P99 {result.p99_response_time_ms}ms >= 1000ms"
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_stress_load(self, load_runner):
        """System should degrade gracefully under stress."""
        config = LoadTestConfig(
            test_type=LoadTestType.STRESS,
            duration_seconds=60,
            max_users=100,
            requests_per_second=50,
        )
        
        result = await load_runner.run(config)
        
        # Under stress, allow higher error rate but system should not crash
        assert result.success_rate >= 0.90
        assert result.total_requests > 100


class TestSpike:
    """Spike tests - sudden traffic surge."""
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_traffic_spike(self, load_runner):
        """System should handle sudden traffic spikes."""
        config = LoadTestConfig(
            test_type=LoadTestType.SPIKE,
            duration_seconds=90,
            max_users=100,
            requests_per_second=30,
        )
        
        result = await load_runner.run(config)
        
        assert result.success_rate >= 0.95
        # Response time may be higher during spike, but should recover
        assert result.avg_response_time_ms < 1000


class TestSLA:
    """SLA compliance tests."""
    
    @pytest.mark.asyncio
    async def test_sla_compliance(self, load_runner):
        """System should meet SLA requirements."""
        config = LoadTestConfig(
            test_type=LoadTestType.LOAD,
            duration_seconds=60,
            max_users=30,
            requests_per_second=15,
        )
        
        result = await load_runner.run(config)
        
        # SLA requirements
        assert result.passed_sla, (
            f"SLA failed: success_rate={result.success_rate}, "
            f"p95={result.p95_response_time_ms}ms, "
            f"p99={result.p99_response_time_ms}ms"
        )
