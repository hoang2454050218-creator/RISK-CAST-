"""
Prometheus Metrics.

Provides application metrics for monitoring and alerting.

Metrics Categories:
1. Business Metrics - Decisions, alerts, customers
2. System Metrics - Latency, throughput, errors
3. External API Metrics - OMEN, ORACLE, Twilio

All metrics follow Prometheus naming conventions:
- snake_case names
- Suffixes: _total (counters), _seconds (durations), _bytes (sizes)
- Labels for dimensions
"""

from typing import Optional
from functools import wraps
import time

from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    Info,
    REGISTRY,
    generate_latest,
    CONTENT_TYPE_LATEST,
)

# ============================================================================
# SERVICE INFO
# ============================================================================

SERVICE_INFO = Info(
    "riskcast_service",
    "RISKCAST service information",
)

# ============================================================================
# BUSINESS METRICS
# ============================================================================

# Decisions
DECISIONS_GENERATED = Counter(
    "riskcast_decisions_generated_total",
    "Total number of decisions generated",
    ["chokepoint", "severity", "urgency"],
)

DECISIONS_DELIVERED = Counter(
    "riskcast_decisions_delivered_total",
    "Total number of decisions delivered to customers",
    ["channel", "status"],  # channel: whatsapp/email, status: success/failed
)

DECISIONS_ACKNOWLEDGED = Counter(
    "riskcast_decisions_acknowledged_total",
    "Total number of decisions acknowledged by customers",
    ["action_taken"],  # action: reroute/delay/insure/monitor/ignore
)

DECISION_LATENCY = Histogram(
    "riskcast_decision_latency_seconds",
    "Time taken to generate a decision",
    ["customer_tier", "chokepoint"],
    buckets=[0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 10.0],
)

ACTIVE_DECISIONS = Gauge(
    "riskcast_active_decisions",
    "Number of active (unacknowledged) decisions",
    ["severity"],
)

TOTAL_EXPOSURE = Gauge(
    "riskcast_total_exposure_usd",
    "Total customer exposure in USD",
    ["chokepoint"],
)

# Customer metrics
ACTIVE_CUSTOMERS = Gauge(
    "riskcast_active_customers",
    "Number of active customers",
)

ACTIVE_SHIPMENTS = Gauge(
    "riskcast_active_shipments",
    "Number of active shipments being tracked",
)

CUSTOMER_EXPOSURE = Gauge(
    "riskcast_customer_exposure_usd",
    "Total customer exposure in USD",
    ["chokepoint"],
)

# Signal metrics
SIGNALS_RECEIVED = Counter(
    "riskcast_signals_received_total",
    "Total signals received from OMEN",
    ["category", "chokepoint"],
)

SIGNALS_ACTIONABLE = Gauge(
    "riskcast_signals_actionable",
    "Number of currently actionable signals",
    ["chokepoint"],
)

# ============================================================================
# SYSTEM METRICS
# ============================================================================

# HTTP request metrics
HTTP_REQUESTS = Counter(
    "riskcast_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
)

HTTP_REQUEST_DURATION = Histogram(
    "riskcast_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

# Decision pipeline
DECISION_GENERATION_DURATION = Histogram(
    "riskcast_decision_generation_seconds",
    "Time to generate a decision",
    ["chokepoint"],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0],
)

# ============================================================================
# EXTERNAL API METRICS
# ============================================================================

# OMEN API
OMEN_API_REQUESTS = Counter(
    "riskcast_omen_api_requests_total",
    "Total OMEN API requests",
    ["endpoint", "status"],
)

OMEN_API_DURATION = Histogram(
    "riskcast_omen_api_duration_seconds",
    "OMEN API request duration",
    ["endpoint"],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)

# ORACLE data sources
ORACLE_AIS_REQUESTS = Counter(
    "riskcast_oracle_ais_requests_total",
    "Total AIS data requests",
    ["status"],
)

ORACLE_FREIGHT_REQUESTS = Counter(
    "riskcast_oracle_freight_requests_total",
    "Total freight rate requests",
    ["status"],
)

# Twilio/WhatsApp
TWILIO_API_REQUESTS = Counter(
    "riskcast_twilio_api_requests_total",
    "Total Twilio API requests",
    ["status"],
)

TWILIO_MESSAGE_STATUS = Counter(
    "riskcast_twilio_message_status_total",
    "Twilio message delivery status",
    ["status"],  # queued/sent/delivered/failed
)

# ============================================================================
# CIRCUIT BREAKER METRICS
# ============================================================================

CIRCUIT_BREAKER_STATE = Gauge(
    "riskcast_circuit_breaker_state",
    "Circuit breaker state (0=closed, 1=open, 2=half_open)",
    ["name"],
)

CIRCUIT_BREAKER_FAILURES = Counter(
    "riskcast_circuit_breaker_failures_total",
    "Circuit breaker failure count",
    ["name"],
)

# ============================================================================
# DECORATORS
# ============================================================================


def track_time(metric: Histogram, labels: Optional[dict] = None):
    """Decorator to track function execution time."""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.time()
            try:
                return await func(*args, **kwargs)
            finally:
                duration = time.time() - start
                if labels:
                    metric.labels(**labels).observe(duration)
                else:
                    metric.observe(duration)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start = time.time()
            try:
                return func(*args, **kwargs)
            finally:
                duration = time.time() - start
                if labels:
                    metric.labels(**labels).observe(duration)
                else:
                    metric.observe(duration)

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def track_counter(metric: Counter, labels: Optional[dict] = None):
    """Decorator to increment a counter on function call."""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                result = await func(*args, **kwargs)
                if labels:
                    metric.labels(**labels).inc()
                else:
                    metric.inc()
                return result
            except Exception:
                # Track failures with different label
                if labels:
                    fail_labels = {**labels, "status": "failed"}
                    metric.labels(**fail_labels).inc()
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                result = func(*args, **kwargs)
                if labels:
                    metric.labels(**labels).inc()
                else:
                    metric.inc()
                return result
            except Exception:
                if labels:
                    fail_labels = {**labels, "status": "failed"}
                    metric.labels(**fail_labels).inc()
                raise

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def record_decision(
    chokepoint: str,
    severity: str,
    urgency: str,
    generation_time: float,
):
    """Record decision generation metrics."""
    DECISIONS_GENERATED.labels(
        chokepoint=chokepoint,
        severity=severity,
        urgency=urgency,
    ).inc()

    DECISION_GENERATION_DURATION.labels(
        chokepoint=chokepoint,
    ).observe(generation_time)


def record_delivery(
    channel: str,
    success: bool,
):
    """Record delivery metrics."""
    DECISIONS_DELIVERED.labels(
        channel=channel,
        status="success" if success else "failed",
    ).inc()


def record_http_request(
    method: str,
    endpoint: str,
    status_code: int,
    duration: float,
):
    """Record HTTP request metrics."""
    HTTP_REQUESTS.labels(
        method=method,
        endpoint=endpoint,
        status_code=str(status_code),
    ).inc()

    HTTP_REQUEST_DURATION.labels(
        method=method,
        endpoint=endpoint,
    ).observe(duration)


def update_gauges(
    customers: int,
    shipments: int,
    exposure_by_chokepoint: dict[str, float],
):
    """Update gauge metrics."""
    ACTIVE_CUSTOMERS.set(customers)
    ACTIVE_SHIPMENTS.set(shipments)

    for chokepoint, exposure in exposure_by_chokepoint.items():
        CUSTOMER_EXPOSURE.labels(chokepoint=chokepoint).set(exposure)


def set_service_info(version: str, environment: str):
    """Set service info metric."""
    SERVICE_INFO.info({
        "version": version,
        "environment": environment,
        "service": "riskcast",
    })


def get_metrics() -> bytes:
    """Get all metrics in Prometheus format."""
    return generate_latest(REGISTRY)


def get_metrics_content_type() -> str:
    """Get content type for metrics."""
    return CONTENT_TYPE_LATEST
