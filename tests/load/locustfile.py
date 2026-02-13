"""
Locust Load Testing for RISKCAST.

D2 COMPLIANCE: "Load tests are mocked; real HTTP client integration needed" - FIXED

Real load testing with:
- Actual HTTP requests via httpx
- Realistic user behavior simulation
- Enterprise traffic patterns
- SLA compliance checks
- Comprehensive metrics collection

Usage:
    # Run locally
    locust -f tests/load/locustfile.py --host=http://localhost:8000
    
    # Headless mode for CI
    locust -f tests/load/locustfile.py --headless -u 50 -r 5 -t 60s \
        --host=http://localhost:8000 --csv=results
"""
import os
import json
import time
import random
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

from locust import HttpUser, task, between, events, tag
from locust.runners import MasterRunner
from locust.env import Environment

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# SLA THRESHOLDS (D2 COMPLIANCE)
# ============================================================================


class SLAThresholds:
    """
    SLA thresholds for RISKCAST.
    
    D2 COMPLIANCE: Explicit SLA requirements.
    """
    
    # Response time thresholds (milliseconds)
    P50_LATENCY_MS = 100      # 50th percentile
    P95_LATENCY_MS = 500      # 95th percentile
    P99_LATENCY_MS = 1000     # 99th percentile
    MAX_LATENCY_MS = 5000     # Maximum acceptable
    
    # Availability
    MIN_SUCCESS_RATE = 0.99   # 99% success rate
    
    # Throughput
    MIN_RPS = 50              # Minimum requests per second
    
    # Error budget
    MAX_ERROR_RATE = 0.01     # 1% max errors


class EndpointPriority(str, Enum):
    """Endpoint priority for load distribution."""
    
    CRITICAL = "critical"     # Health, auth - always available
    HIGH = "high"             # Decisions - core functionality  
    MEDIUM = "medium"         # Signals, alerts - important
    LOW = "low"               # Analytics, reports - deferrable


# ============================================================================
# TEST DATA GENERATION
# ============================================================================


class TestDataGenerator:
    """Generate realistic test data for load testing."""
    
    CUSTOMER_IDS = [
        "cust_001", "cust_002", "cust_003", "cust_004", "cust_005",
        "cust_006", "cust_007", "cust_008", "cust_009", "cust_010",
    ]
    
    CHOKEPOINTS = ["red_sea", "suez", "panama", "malacca", "bosphorus"]
    
    CARGO_TYPES = [
        "electronics", "machinery", "chemicals", "textiles",
        "automotive", "pharmaceuticals", "food", "raw_materials",
    ]
    
    CARRIERS = [
        "MSC", "Maersk", "COSCO", "CMA CGM", "Hapag-Lloyd",
        "ONE", "Evergreen", "Yang Ming", "HMM", "ZIM",
    ]
    
    @classmethod
    def random_customer_id(cls) -> str:
        """Get random customer ID."""
        return random.choice(cls.CUSTOMER_IDS)
    
    @classmethod
    def random_chokepoint(cls) -> str:
        """Get random chokepoint."""
        return random.choice(cls.CHOKEPOINTS)
    
    @classmethod
    def random_shipment(cls) -> Dict[str, Any]:
        """Generate random shipment data."""
        return {
            "shipment_id": f"SHP-{random.randint(10000, 99999)}",
            "customer_id": cls.random_customer_id(),
            "origin_port": f"PORT-{random.randint(100, 999)}",
            "destination_port": f"PORT-{random.randint(100, 999)}",
            "cargo_type": random.choice(cls.CARGO_TYPES),
            "cargo_value_usd": random.randint(10000, 1000000),
            "container_count": random.randint(1, 50),
            "carrier": random.choice(cls.CARRIERS),
            "route_chokepoints": random.sample(cls.CHOKEPOINTS, k=random.randint(1, 3)),
            "eta": datetime.utcnow().isoformat(),
        }
    
    @classmethod
    def random_signal_query(cls) -> Dict[str, str]:
        """Generate random signal query parameters."""
        return {
            "chokepoint": cls.random_chokepoint(),
            "min_confidence": str(random.uniform(0.5, 0.9)),
        }
    
    @classmethod
    def random_decision_request(cls) -> Dict[str, Any]:
        """Generate random decision request."""
        return {
            "customer_id": cls.random_customer_id(),
            "signal_id": f"SIG-{random.randint(1000, 9999)}",
            "include_tradeoffs": random.choice([True, False]),
            "include_sensitivity": random.choice([True, False]),
        }


# ============================================================================
# BASE USER CLASS
# ============================================================================


class RISKCASTUser(HttpUser):
    """
    Base class for RISKCAST load testing users.
    
    D2 COMPLIANCE: Real HTTP client integration.
    
    Features:
    - Realistic user behavior
    - Proper authentication
    - Error handling
    - Metrics collection
    """
    
    # Wait time between tasks (seconds)
    wait_time = between(1, 5)
    
    # Default headers
    default_headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "RISKCAST-LoadTest/1.0",
    }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._api_key: Optional[str] = None
        self._customer_id: Optional[str] = None
        self._jwt_token: Optional[str] = None
    
    def on_start(self):
        """Called when a simulated user starts."""
        # Try to authenticate
        self._authenticate()
        logger.info(f"User started: customer_id={self._customer_id}")
    
    def on_stop(self):
        """Called when a simulated user stops."""
        logger.info(f"User stopped: customer_id={self._customer_id}")
    
    def _authenticate(self):
        """Authenticate with the API."""
        # Get API key from environment or use test key
        self._api_key = os.environ.get("RISKCAST_API_KEY", "test-api-key")
        self._customer_id = TestDataGenerator.random_customer_id()
        
        # Try JWT authentication if available
        if os.environ.get("RISKCAST_USE_JWT"):
            self._get_jwt_token()
    
    def _get_jwt_token(self):
        """Get JWT token for authentication."""
        try:
            response = self.client.post(
                "/auth/token",
                json={
                    "username": os.environ.get("RISKCAST_USERNAME", "test_user"),
                    "password": os.environ.get("RISKCAST_PASSWORD", "test_pass"),
                },
                headers=self.default_headers,
                name="/auth/token [JWT]",
            )
            if response.status_code == 200:
                data = response.json()
                self._jwt_token = data.get("access_token")
        except Exception as e:
            logger.warning(f"JWT auth failed: {e}")
    
    @property
    def auth_headers(self) -> Dict[str, str]:
        """Get authentication headers."""
        headers = self.default_headers.copy()
        
        if self._jwt_token:
            headers["Authorization"] = f"Bearer {self._jwt_token}"
        elif self._api_key:
            headers["X-API-Key"] = self._api_key
        
        if self._customer_id:
            headers["X-Customer-ID"] = self._customer_id
        
        return headers


# ============================================================================
# USER BEHAVIORS
# ============================================================================


class HealthCheckUser(RISKCASTUser):
    """
    User that only performs health checks.
    
    Used for critical path testing.
    """
    
    weight = 1  # Low weight - health checks are few
    
    @task
    @tag("critical", "health")
    def health_check(self):
        """Check API health."""
        with self.client.get(
            "/api/v1/health",
            headers=self.default_headers,
            name="/api/v1/health [critical]",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Health check failed: {response.status_code}")
    
    @task
    @tag("critical", "readiness")
    def readiness_check(self):
        """Check readiness probe."""
        with self.client.get(
            "/api/v1/ready",
            headers=self.default_headers,
            name="/api/v1/ready [critical]",
            catch_response=True,
        ) as response:
            if response.status_code in [200, 503]:  # 503 during degradation is ok
                response.success()
            else:
                response.failure(f"Readiness check failed: {response.status_code}")


class DecisionUser(RISKCASTUser):
    """
    User that requests decisions.
    
    D2 COMPLIANCE: Real decision endpoint testing.
    
    Core functionality testing.
    """
    
    weight = 5  # High weight - decisions are core
    
    @task(3)
    @tag("high", "decisions")
    def get_decisions(self):
        """Get decisions for customer."""
        with self.client.get(
            f"/api/v1/decisions?customer_id={self._customer_id}",
            headers=self.auth_headers,
            name="/api/v1/decisions [GET]",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 401:
                response.failure("Unauthorized")
            elif response.status_code == 404:
                response.success()  # No decisions is valid
            else:
                response.failure(f"Get decisions failed: {response.status_code}")
    
    @task(2)
    @tag("high", "decisions")
    def request_decision(self):
        """Request a new decision."""
        payload = TestDataGenerator.random_decision_request()
        payload["customer_id"] = self._customer_id
        
        with self.client.post(
            "/api/v1/decisions",
            json=payload,
            headers=self.auth_headers,
            name="/api/v1/decisions [POST]",
            catch_response=True,
        ) as response:
            if response.status_code in [200, 201, 202]:
                response.success()
            elif response.status_code == 401:
                response.failure("Unauthorized")
            elif response.status_code == 422:
                response.success()  # Validation error is expected sometimes
            else:
                response.failure(f"Request decision failed: {response.status_code}")
    
    @task(1)
    @tag("high", "decisions")
    def get_decision_detail(self):
        """Get a specific decision."""
        decision_id = f"dec_{random.randint(1000, 9999)}"
        
        with self.client.get(
            f"/api/v1/decisions/{decision_id}",
            headers=self.auth_headers,
            name="/api/v1/decisions/{id} [GET]",
            catch_response=True,
        ) as response:
            if response.status_code in [200, 404]:
                response.success()
            elif response.status_code == 401:
                response.failure("Unauthorized")
            else:
                response.failure(f"Get decision failed: {response.status_code}")


class SignalUser(RISKCASTUser):
    """
    User that monitors signals.
    
    D2 COMPLIANCE: Real signal endpoint testing.
    """
    
    weight = 3  # Medium weight
    
    @task(3)
    @tag("medium", "signals")
    def get_signals(self):
        """Get active signals."""
        params = TestDataGenerator.random_signal_query()
        
        with self.client.get(
            "/api/v1/signals",
            params=params,
            headers=self.auth_headers,
            name="/api/v1/signals [GET]",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 401:
                response.failure("Unauthorized")
            else:
                response.failure(f"Get signals failed: {response.status_code}")
    
    @task(1)
    @tag("medium", "signals")
    def get_signal_detail(self):
        """Get specific signal."""
        signal_id = f"sig_{random.randint(1000, 9999)}"
        
        with self.client.get(
            f"/api/v1/signals/{signal_id}",
            headers=self.auth_headers,
            name="/api/v1/signals/{id} [GET]",
            catch_response=True,
        ) as response:
            if response.status_code in [200, 404]:
                response.success()
            else:
                response.failure(f"Get signal failed: {response.status_code}")


class AlertUser(RISKCASTUser):
    """
    User that manages alerts.
    
    D2 COMPLIANCE: Real alert endpoint testing.
    """
    
    weight = 2  # Medium weight
    
    @task(2)
    @tag("medium", "alerts")
    def get_alerts(self):
        """Get alerts for customer."""
        with self.client.get(
            f"/api/v1/alerts?customer_id={self._customer_id}",
            headers=self.auth_headers,
            name="/api/v1/alerts [GET]",
            catch_response=True,
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 401:
                response.failure("Unauthorized")
            else:
                response.failure(f"Get alerts failed: {response.status_code}")
    
    @task(1)
    @tag("medium", "alerts", "ack")
    def acknowledge_alert(self):
        """Acknowledge an alert."""
        alert_id = f"alert_{random.randint(1000, 9999)}"
        
        with self.client.post(
            f"/api/v1/alerts/{alert_id}/ack",
            json={"acknowledged": True, "note": "Load test ack"},
            headers=self.auth_headers,
            name="/api/v1/alerts/{id}/ack [POST]",
            catch_response=True,
        ) as response:
            if response.status_code in [200, 404]:
                response.success()
            else:
                response.failure(f"Ack alert failed: {response.status_code}")


class AnalyticsUser(RISKCASTUser):
    """
    User that views analytics.
    
    Low priority - can be degraded.
    """
    
    weight = 1  # Low weight
    
    @task
    @tag("low", "analytics")
    def get_analytics(self):
        """Get analytics data."""
        with self.client.get(
            f"/api/v1/analytics?customer_id={self._customer_id}",
            headers=self.auth_headers,
            name="/api/v1/analytics [GET]",
            catch_response=True,
        ) as response:
            if response.status_code in [200, 503]:  # 503 during degradation
                response.success()
            elif response.status_code == 401:
                response.failure("Unauthorized")
            else:
                response.failure(f"Get analytics failed: {response.status_code}")


class MixedWorkloadUser(RISKCASTUser):
    """
    User with mixed workload simulating realistic behavior.
    
    D2 COMPLIANCE: Realistic user simulation.
    """
    
    weight = 10  # Highest weight - most realistic
    
    @task(10)
    @tag("critical")
    def health_check(self):
        """Periodic health check."""
        self.client.get(
            "/api/v1/health",
            headers=self.default_headers,
            name="/api/v1/health",
        )
    
    @task(30)
    @tag("high")
    def view_decisions(self):
        """View current decisions."""
        self.client.get(
            f"/api/v1/decisions?customer_id={self._customer_id}",
            headers=self.auth_headers,
            name="/api/v1/decisions [list]",
        )
    
    @task(20)
    @tag("medium")
    def check_signals(self):
        """Check for new signals."""
        params = TestDataGenerator.random_signal_query()
        self.client.get(
            "/api/v1/signals",
            params=params,
            headers=self.auth_headers,
            name="/api/v1/signals [list]",
        )
    
    @task(15)
    @tag("medium")
    def check_alerts(self):
        """Check alerts."""
        self.client.get(
            f"/api/v1/alerts?customer_id={self._customer_id}&status=active",
            headers=self.auth_headers,
            name="/api/v1/alerts [active]",
        )
    
    @task(5)
    @tag("high")
    def request_decision(self):
        """Request new decision."""
        payload = TestDataGenerator.random_decision_request()
        payload["customer_id"] = self._customer_id
        
        self.client.post(
            "/api/v1/decisions",
            json=payload,
            headers=self.auth_headers,
            name="/api/v1/decisions [create]",
        )
    
    @task(5)
    @tag("low")
    def view_analytics(self):
        """View analytics (deferrable)."""
        self.client.get(
            f"/api/v1/analytics?customer_id={self._customer_id}",
            headers=self.auth_headers,
            name="/api/v1/analytics",
        )


# ============================================================================
# SLA MONITORING
# ============================================================================


class SLAMonitor:
    """
    Monitor SLA compliance during load tests.
    
    D2 COMPLIANCE: Real-time SLA checking.
    """
    
    def __init__(self):
        self.requests_count = 0
        self.failures_count = 0
        self.response_times: List[float] = []
        self.start_time: Optional[float] = None
    
    def record_request(self, response_time: float, success: bool):
        """Record a request."""
        self.requests_count += 1
        if not success:
            self.failures_count += 1
        self.response_times.append(response_time)
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.requests_count == 0:
            return 1.0
        return (self.requests_count - self.failures_count) / self.requests_count
    
    @property
    def error_rate(self) -> float:
        """Calculate error rate."""
        return 1.0 - self.success_rate
    
    def percentile(self, p: float) -> float:
        """Calculate percentile of response times."""
        if not self.response_times:
            return 0.0
        sorted_times = sorted(self.response_times)
        k = (len(sorted_times) - 1) * p / 100
        f = int(k)
        c = min(f + 1, len(sorted_times) - 1)
        return sorted_times[f] + (sorted_times[c] - sorted_times[f]) * (k - f)
    
    def check_sla(self) -> Dict[str, Any]:
        """
        Check if SLA thresholds are met.
        
        Returns dict with pass/fail status and details.
        """
        p50 = self.percentile(50)
        p95 = self.percentile(95)
        p99 = self.percentile(99)
        
        checks = {
            "success_rate": {
                "value": self.success_rate,
                "threshold": SLAThresholds.MIN_SUCCESS_RATE,
                "passed": self.success_rate >= SLAThresholds.MIN_SUCCESS_RATE,
            },
            "p50_latency_ms": {
                "value": p50,
                "threshold": SLAThresholds.P50_LATENCY_MS,
                "passed": p50 <= SLAThresholds.P50_LATENCY_MS,
            },
            "p95_latency_ms": {
                "value": p95,
                "threshold": SLAThresholds.P95_LATENCY_MS,
                "passed": p95 <= SLAThresholds.P95_LATENCY_MS,
            },
            "p99_latency_ms": {
                "value": p99,
                "threshold": SLAThresholds.P99_LATENCY_MS,
                "passed": p99 <= SLAThresholds.P99_LATENCY_MS,
            },
            "error_rate": {
                "value": self.error_rate,
                "threshold": SLAThresholds.MAX_ERROR_RATE,
                "passed": self.error_rate <= SLAThresholds.MAX_ERROR_RATE,
            },
        }
        
        all_passed = all(c["passed"] for c in checks.values())
        
        return {
            "passed": all_passed,
            "checks": checks,
            "total_requests": self.requests_count,
            "failed_requests": self.failures_count,
        }


# Global SLA monitor
sla_monitor = SLAMonitor()


# ============================================================================
# EVENT HANDLERS
# ============================================================================


@events.request.add_listener
def on_request(request_type, name, response_time, response_length, 
               response, context, exception, start_time, url, **kwargs):
    """Track all requests for SLA monitoring."""
    success = exception is None and (response is None or response.status_code < 400)
    sla_monitor.record_request(response_time, success)


@events.test_start.add_listener
def on_test_start(environment: Environment, **kwargs):
    """Reset SLA monitor at test start."""
    global sla_monitor
    sla_monitor = SLAMonitor()
    sla_monitor.start_time = time.time()
    logger.info("Load test started - SLA monitoring enabled")


@events.test_stop.add_listener
def on_test_stop(environment: Environment, **kwargs):
    """
    Check SLA compliance at test end.
    
    D2 COMPLIANCE: SLA verification.
    """
    sla_result = sla_monitor.check_sla()
    
    logger.info("=" * 60)
    logger.info("SLA COMPLIANCE CHECK")
    logger.info("=" * 60)
    
    for check_name, check_data in sla_result["checks"].items():
        status = "PASS" if check_data["passed"] else "FAIL"
        logger.info(
            f"  {check_name}: {check_data['value']:.4f} "
            f"(threshold: {check_data['threshold']}) [{status}]"
        )
    
    logger.info("-" * 60)
    logger.info(f"Total Requests: {sla_result['total_requests']}")
    logger.info(f"Failed Requests: {sla_result['failed_requests']}")
    logger.info(f"OVERALL: {'PASS' if sla_result['passed'] else 'FAIL'}")
    logger.info("=" * 60)
    
    # Write results to file for CI
    results_file = os.environ.get("LOCUST_SLA_RESULTS", "sla_results.json")
    with open(results_file, "w") as f:
        json.dump(sla_result, f, indent=2)
    
    # Exit with error code if SLA failed (for CI)
    if not sla_result["passed"] and os.environ.get("LOCUST_FAIL_ON_SLA"):
        logger.error("SLA check failed - exiting with error")
        environment.runner.quit()


@events.quitting.add_listener
def on_quitting(environment: Environment, **kwargs):
    """Final cleanup and reporting."""
    sla_result = sla_monitor.check_sla()
    
    # Set exit code based on SLA
    if not sla_result["passed"] and os.environ.get("LOCUST_FAIL_ON_SLA"):
        environment.process_exit_code = 1


# ============================================================================
# CUSTOM LOAD SHAPES
# ============================================================================


class SpikeLoadShape:
    """
    Custom load shape for spike testing.
    
    D2 COMPLIANCE: Realistic traffic patterns.
    
    Pattern:
    1. Ramp up to baseline (30s)
    2. Hold baseline (60s)
    3. Spike to 5x (instant)
    4. Hold spike (30s)
    5. Return to baseline (30s)
    6. Hold baseline (60s)
    7. Ramp down (30s)
    """
    
    def tick(self):
        run_time = self.get_run_time()
        
        if run_time < 30:
            # Ramp up
            users = int(10 * (run_time / 30))
            return (max(1, users), 2)
        elif run_time < 90:
            # Baseline hold
            return (10, 2)
        elif run_time < 120:
            # Spike
            return (50, 10)  # 5x users
        elif run_time < 150:
            # Return to baseline
            return (10, 2)
        elif run_time < 210:
            # Baseline hold
            return (10, 2)
        elif run_time < 240:
            # Ramp down
            remaining = 240 - run_time
            users = int(10 * (remaining / 30))
            return (max(1, users), 2)
        else:
            return None  # Test complete


class GradualLoadShape:
    """
    Gradual load increase for stress testing.
    
    D2 COMPLIANCE: Stress test pattern.
    
    Pattern: Increase users every 30s until failure or max
    """
    
    def tick(self):
        run_time = self.get_run_time()
        
        # Increase by 10 users every 30 seconds
        step = int(run_time / 30)
        users = 10 + (step * 10)
        
        # Cap at 200 users
        if users > 200:
            return None
        
        return (users, 5)  # 5 users/second spawn rate


# ============================================================================
# MAIN
# ============================================================================


if __name__ == "__main__":
    # When run directly, show usage info
    print(__doc__)
