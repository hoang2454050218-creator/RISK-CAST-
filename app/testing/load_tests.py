"""
Load Testing Utilities for RISKCAST.

Provides:
- Simple load test framework
- Request generators
- Metrics collection
- Performance assertions

For production-grade load testing, use Locust or k6.
"""

import asyncio
import time
import statistics
from typing import (
    Optional, 
    Callable, 
    List, 
    Dict, 
    Any,
    Awaitable,
)
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict
import random

import structlog

logger = structlog.get_logger(__name__)


# ============================================================================
# METRICS
# ============================================================================


@dataclass
class RequestMetrics:
    """Metrics for a single request."""
    duration_ms: float
    status_code: int
    success: bool
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class LoadTestMetrics:
    """Aggregated load test metrics."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    
    # Latency stats
    min_latency_ms: float = float("inf")
    max_latency_ms: float = 0
    mean_latency_ms: float = 0
    median_latency_ms: float = 0
    p95_latency_ms: float = 0
    p99_latency_ms: float = 0
    
    # Throughput
    requests_per_second: float = 0
    
    # Error breakdown
    errors: Dict[str, int] = field(default_factory=dict)
    status_codes: Dict[int, int] = field(default_factory=dict)
    
    # Timing
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_seconds: float = 0
    
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_requests == 0:
            return 0.0
        return self.successful_requests / self.total_requests
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "success_rate": round(self.success_rate(), 4),
            "latency": {
                "min_ms": round(self.min_latency_ms, 2),
                "max_ms": round(self.max_latency_ms, 2),
                "mean_ms": round(self.mean_latency_ms, 2),
                "median_ms": round(self.median_latency_ms, 2),
                "p95_ms": round(self.p95_latency_ms, 2),
                "p99_ms": round(self.p99_latency_ms, 2),
            },
            "requests_per_second": round(self.requests_per_second, 2),
            "duration_seconds": round(self.duration_seconds, 2),
            "status_codes": self.status_codes,
            "errors": self.errors,
        }


# ============================================================================
# LOAD TEST RUNNER
# ============================================================================


class LoadTestRunner:
    """
    Simple load test runner.
    
    Usage:
        runner = LoadTestRunner(
            request_func=make_api_request,
            requests_per_second=100,
            duration_seconds=60,
        )
        metrics = await runner.run()
    """
    
    def __init__(
        self,
        request_func: Callable[[], Awaitable[RequestMetrics]],
        requests_per_second: float = 10,
        duration_seconds: float = 60,
        max_concurrent: int = 100,
        warmup_seconds: float = 5,
    ):
        self.request_func = request_func
        self.rps = requests_per_second
        self.duration = duration_seconds
        self.max_concurrent = max_concurrent
        self.warmup = warmup_seconds
        
        self._results: List[RequestMetrics] = []
        self._semaphore: Optional[asyncio.Semaphore] = None
        self._stop_event = asyncio.Event()
    
    async def run(self) -> LoadTestMetrics:
        """Run the load test."""
        self._results = []
        self._semaphore = asyncio.Semaphore(self.max_concurrent)
        self._stop_event.clear()
        
        logger.info(
            "load_test_starting",
            rps=self.rps,
            duration=self.duration,
            warmup=self.warmup,
        )
        
        # Warmup phase
        if self.warmup > 0:
            logger.info("load_test_warmup_starting")
            await self._run_phase(self.warmup, warmup=True)
            self._results = []  # Clear warmup results
        
        # Main phase
        start_time = datetime.utcnow()
        await self._run_phase(self.duration, warmup=False)
        end_time = datetime.utcnow()
        
        # Calculate metrics
        metrics = self._calculate_metrics(start_time, end_time)
        
        logger.info(
            "load_test_completed",
            total_requests=metrics.total_requests,
            success_rate=metrics.success_rate(),
            rps=metrics.requests_per_second,
            p99_latency=metrics.p99_latency_ms,
        )
        
        return metrics
    
    async def _run_phase(self, duration: float, warmup: bool = False) -> None:
        """Run a test phase."""
        end_time = time.time() + duration
        interval = 1.0 / self.rps
        
        tasks = []
        
        while time.time() < end_time:
            task = asyncio.create_task(self._make_request())
            tasks.append(task)
            
            # Rate limiting
            await asyncio.sleep(interval)
            
            # Clean up completed tasks periodically
            if len(tasks) > self.max_concurrent * 2:
                done = [t for t in tasks if t.done()]
                tasks = [t for t in tasks if not t.done()]
        
        # Wait for remaining tasks
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _make_request(self) -> None:
        """Make a single request."""
        async with self._semaphore:
            try:
                result = await self.request_func()
                self._results.append(result)
            except Exception as e:
                self._results.append(RequestMetrics(
                    duration_ms=0,
                    status_code=0,
                    success=False,
                    error=str(e),
                ))
    
    def _calculate_metrics(
        self,
        start_time: datetime,
        end_time: datetime,
    ) -> LoadTestMetrics:
        """Calculate metrics from results."""
        metrics = LoadTestMetrics()
        metrics.start_time = start_time
        metrics.end_time = end_time
        metrics.duration_seconds = (end_time - start_time).total_seconds()
        
        if not self._results:
            return metrics
        
        latencies = []
        
        for result in self._results:
            metrics.total_requests += 1
            
            if result.success:
                metrics.successful_requests += 1
                latencies.append(result.duration_ms)
            else:
                metrics.failed_requests += 1
                error_key = result.error or "unknown"
                metrics.errors[error_key] = metrics.errors.get(error_key, 0) + 1
            
            metrics.status_codes[result.status_code] = (
                metrics.status_codes.get(result.status_code, 0) + 1
            )
        
        # Latency statistics
        if latencies:
            latencies.sort()
            metrics.min_latency_ms = min(latencies)
            metrics.max_latency_ms = max(latencies)
            metrics.mean_latency_ms = statistics.mean(latencies)
            metrics.median_latency_ms = statistics.median(latencies)
            
            # Percentiles
            p95_idx = int(len(latencies) * 0.95)
            p99_idx = int(len(latencies) * 0.99)
            metrics.p95_latency_ms = latencies[p95_idx] if p95_idx < len(latencies) else latencies[-1]
            metrics.p99_latency_ms = latencies[p99_idx] if p99_idx < len(latencies) else latencies[-1]
        
        # Throughput
        metrics.requests_per_second = (
            metrics.total_requests / metrics.duration_seconds
            if metrics.duration_seconds > 0 else 0
        )
        
        return metrics
    
    def stop(self) -> None:
        """Stop the load test."""
        self._stop_event.set()


# ============================================================================
# REQUEST GENERATORS
# ============================================================================


class RequestGenerator:
    """
    Generates test requests.
    
    Usage:
        generator = RequestGenerator(base_url="http://localhost:8000")
        
        async def make_request():
            return await generator.get_decisions("CUST-001")
        
        runner = LoadTestRunner(make_request, rps=100)
    """
    
    def __init__(
        self,
        base_url: str,
        api_key: Optional[str] = None,
        http_client: Optional[Any] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self._client = http_client
    
    def _get_headers(self) -> Dict[str, str]:
        """Get common headers."""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers
    
    async def health_check(self) -> RequestMetrics:
        """Health check request."""
        import httpx
        
        start = time.time()
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/health",
                    timeout=10.0,
                )
            
            duration_ms = (time.time() - start) * 1000
            return RequestMetrics(
                duration_ms=duration_ms,
                status_code=response.status_code,
                success=response.status_code == 200,
            )
        except Exception as e:
            duration_ms = (time.time() - start) * 1000
            return RequestMetrics(
                duration_ms=duration_ms,
                status_code=0,
                success=False,
                error=str(e),
            )
    
    async def get_decisions(self, customer_id: str) -> RequestMetrics:
        """Get decisions request."""
        import httpx
        
        start = time.time()
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/api/v1/customers/{customer_id}/decisions",
                    headers=self._get_headers(),
                    timeout=30.0,
                )
            
            duration_ms = (time.time() - start) * 1000
            return RequestMetrics(
                duration_ms=duration_ms,
                status_code=response.status_code,
                success=200 <= response.status_code < 300,
            )
        except Exception as e:
            duration_ms = (time.time() - start) * 1000
            return RequestMetrics(
                duration_ms=duration_ms,
                status_code=0,
                success=False,
                error=str(e),
            )
    
    async def generate_decision(
        self,
        customer_id: str,
        signal_id: str,
    ) -> RequestMetrics:
        """Generate decision request."""
        import httpx
        
        start = time.time()
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/decisions/generate",
                    headers=self._get_headers(),
                    json={
                        "customer_id": customer_id,
                        "signal_id": signal_id,
                    },
                    timeout=60.0,
                )
            
            duration_ms = (time.time() - start) * 1000
            return RequestMetrics(
                duration_ms=duration_ms,
                status_code=response.status_code,
                success=200 <= response.status_code < 300,
            )
        except Exception as e:
            duration_ms = (time.time() - start) * 1000
            return RequestMetrics(
                duration_ms=duration_ms,
                status_code=0,
                success=False,
                error=str(e),
            )


# ============================================================================
# PERFORMANCE ASSERTIONS
# ============================================================================


class PerformanceAssertions:
    """
    Assertions for performance testing.
    
    Usage:
        assertions = PerformanceAssertions(metrics)
        assertions.assert_success_rate(0.99)
        assertions.assert_p99_latency(500)
    """
    
    def __init__(self, metrics: LoadTestMetrics):
        self.metrics = metrics
        self._failures: List[str] = []
    
    def assert_success_rate(self, min_rate: float) -> "PerformanceAssertions":
        """Assert minimum success rate."""
        actual = self.metrics.success_rate()
        if actual < min_rate:
            self._failures.append(
                f"Success rate {actual:.4f} below minimum {min_rate}"
            )
        return self
    
    def assert_p95_latency(self, max_ms: float) -> "PerformanceAssertions":
        """Assert maximum p95 latency."""
        actual = self.metrics.p95_latency_ms
        if actual > max_ms:
            self._failures.append(
                f"p95 latency {actual:.2f}ms exceeds maximum {max_ms}ms"
            )
        return self
    
    def assert_p99_latency(self, max_ms: float) -> "PerformanceAssertions":
        """Assert maximum p99 latency."""
        actual = self.metrics.p99_latency_ms
        if actual > max_ms:
            self._failures.append(
                f"p99 latency {actual:.2f}ms exceeds maximum {max_ms}ms"
            )
        return self
    
    def assert_mean_latency(self, max_ms: float) -> "PerformanceAssertions":
        """Assert maximum mean latency."""
        actual = self.metrics.mean_latency_ms
        if actual > max_ms:
            self._failures.append(
                f"Mean latency {actual:.2f}ms exceeds maximum {max_ms}ms"
            )
        return self
    
    def assert_throughput(self, min_rps: float) -> "PerformanceAssertions":
        """Assert minimum throughput."""
        actual = self.metrics.requests_per_second
        if actual < min_rps:
            self._failures.append(
                f"Throughput {actual:.2f} RPS below minimum {min_rps} RPS"
            )
        return self
    
    def assert_no_errors(self) -> "PerformanceAssertions":
        """Assert no errors occurred."""
        if self.metrics.failed_requests > 0:
            self._failures.append(
                f"{self.metrics.failed_requests} requests failed"
            )
        return self
    
    def verify(self) -> bool:
        """Verify all assertions passed."""
        if self._failures:
            for failure in self._failures:
                logger.error("performance_assertion_failed", message=failure)
            raise AssertionError(
                f"Performance assertions failed:\n" + "\n".join(self._failures)
            )
        return True
    
    @property
    def passed(self) -> bool:
        """Check if all assertions passed."""
        return len(self._failures) == 0


# ============================================================================
# LOAD TEST SCENARIOS
# ============================================================================


class LoadTestScenarios:
    """
    Predefined load test scenarios.
    """
    
    @staticmethod
    async def baseline_test(
        base_url: str,
        api_key: Optional[str] = None,
    ) -> LoadTestMetrics:
        """
        Baseline test - low load to establish baseline metrics.
        
        10 RPS for 30 seconds.
        """
        generator = RequestGenerator(base_url, api_key)
        runner = LoadTestRunner(
            request_func=generator.health_check,
            requests_per_second=10,
            duration_seconds=30,
            warmup_seconds=5,
        )
        return await runner.run()
    
    @staticmethod
    async def stress_test(
        base_url: str,
        api_key: Optional[str] = None,
    ) -> LoadTestMetrics:
        """
        Stress test - high load to find breaking point.
        
        100 RPS for 60 seconds.
        """
        generator = RequestGenerator(base_url, api_key)
        runner = LoadTestRunner(
            request_func=generator.health_check,
            requests_per_second=100,
            duration_seconds=60,
            warmup_seconds=10,
        )
        return await runner.run()
    
    @staticmethod
    async def endurance_test(
        base_url: str,
        api_key: Optional[str] = None,
    ) -> LoadTestMetrics:
        """
        Endurance test - sustained load over time.
        
        50 RPS for 10 minutes.
        """
        generator = RequestGenerator(base_url, api_key)
        runner = LoadTestRunner(
            request_func=generator.health_check,
            requests_per_second=50,
            duration_seconds=600,
            warmup_seconds=30,
        )
        return await runner.run()
    
    @staticmethod
    async def spike_test(
        base_url: str,
        api_key: Optional[str] = None,
    ) -> List[LoadTestMetrics]:
        """
        Spike test - sudden increase in load.
        
        10 RPS -> 200 RPS -> 10 RPS
        """
        generator = RequestGenerator(base_url, api_key)
        results = []
        
        # Normal load
        runner = LoadTestRunner(
            request_func=generator.health_check,
            requests_per_second=10,
            duration_seconds=30,
            warmup_seconds=0,
        )
        results.append(await runner.run())
        
        # Spike
        runner = LoadTestRunner(
            request_func=generator.health_check,
            requests_per_second=200,
            duration_seconds=30,
            warmup_seconds=0,
        )
        results.append(await runner.run())
        
        # Recovery
        runner = LoadTestRunner(
            request_func=generator.health_check,
            requests_per_second=10,
            duration_seconds=30,
            warmup_seconds=0,
        )
        results.append(await runner.run())
        
        return results
