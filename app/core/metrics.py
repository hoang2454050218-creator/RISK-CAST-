"""
Comprehensive Metrics Module.

Production-grade metrics with:
- Business metrics (decisions, alerts, outcomes)
- System metrics (latency, throughput, errors)
- Custom metrics (exposure, confidence accuracy)
- Prometheus integration
- OpenTelemetry support
"""

from typing import Optional, Dict, Any
from datetime import datetime
from contextlib import contextmanager
import time
from functools import wraps

from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    Summary,
    Info,
    CollectorRegistry,
    generate_latest,
    CONTENT_TYPE_LATEST,
    REGISTRY as DEFAULT_REGISTRY,
)
from pydantic import BaseModel
import structlog

logger = structlog.get_logger(__name__)


# ============================================================================
# REGISTRY
# ============================================================================

# Use default registry for compatibility
REGISTRY = CollectorRegistry(auto_describe=True)


def _safe_counter(name: str, description: str, labels: list = None) -> Counter:
    """Create counter, reusing if exists."""
    try:
        return Counter(name, description, labels or [])
    except ValueError:
        return DEFAULT_REGISTRY._names_to_collectors.get(name.replace("_total", ""), 
               DEFAULT_REGISTRY._names_to_collectors.get(name))


def _safe_gauge(name: str, description: str, labels: list = None) -> Gauge:
    """Create gauge, reusing if exists."""
    try:
        return Gauge(name, description, labels or [])
    except ValueError:
        return DEFAULT_REGISTRY._names_to_collectors.get(name)


def _safe_histogram(name: str, description: str, labels: list = None, buckets=None) -> Histogram:
    """Create histogram, reusing if exists."""
    try:
        if buckets:
            return Histogram(name, description, labels or [], buckets=buckets)
        return Histogram(name, description, labels or [])
    except ValueError:
        return DEFAULT_REGISTRY._names_to_collectors.get(name)


def _safe_summary(name: str, description: str, labels: list = None) -> Summary:
    """Create summary, reusing if exists."""
    try:
        return Summary(name, description, labels or [])
    except ValueError:
        return DEFAULT_REGISTRY._names_to_collectors.get(name)


# ============================================================================
# BUSINESS METRICS
# ============================================================================


class BusinessMetrics:
    """Business-level metrics for RISKCAST."""
    
    # Decision metrics
    decisions_generated = _safe_counter(
        "riskcast_decisions_generated_total",
        "Total decisions generated",
        ["chokepoint", "severity", "action_type"],
    )
    
    decisions_delivered = _safe_counter(
        "riskcast_decisions_delivered_total",
        "Total decisions delivered to customers",
        ["channel", "status"],
    )
    
    decisions_acknowledged = _safe_counter(
        "riskcast_decisions_acknowledged_total",
        "Total decisions acknowledged by customers",
        ["chokepoint"],
    )
    
    decisions_acted_upon = _safe_counter(
        "riskcast_decisions_acted_total",
        "Total decisions acted upon",
        ["recommended_action", "actual_action"],
    )
    
    # Exposure metrics
    total_exposure_usd = _safe_gauge(
        "riskcast_total_exposure_usd",
        "Total exposure value in USD",
        ["chokepoint"],
    )
    
    affected_shipments = _safe_gauge(
        "riskcast_affected_shipments",
        "Number of affected shipments",
        ["chokepoint", "status"],
    )
    
    # Alert metrics
    alerts_sent = _safe_counter(
        "riskcast_alerts_sent_total",
        "Total alerts sent",
        ["channel", "template", "status"],
    )
    
    alert_delivery_time = _safe_histogram(
        "riskcast_alert_delivery_seconds",
        "Time to deliver alerts",
        ["channel"],
        buckets=[0.5, 1, 2, 5, 10, 30, 60],
    )
    
    # Customer metrics
    active_customers = _safe_gauge(
        "riskcast_active_customers",
        "Number of active customers",
        ["tier"],
    )
    
    customer_shipments = _safe_gauge(
        "riskcast_customer_shipments",
        "Total shipments per customer tier",
        ["tier", "status"],
    )
    
    # Signal metrics
    signals_received = _safe_counter(
        "riskcast_signals_received_total",
        "Total OMEN signals received",
        ["category", "source"],
    )
    
    signals_correlated = _safe_counter(
        "riskcast_signals_correlated_total",
        "Total signals correlated with reality",
        ["correlation_status"],
    )
    
    # Outcome tracking
    prediction_accuracy = _safe_gauge(
        "riskcast_prediction_accuracy",
        "Rolling prediction accuracy",
        ["metric_type", "window"],
    )
    
    confidence_calibration = _safe_gauge(
        "riskcast_confidence_calibration",
        "Confidence calibration score",
        ["bucket"],
    )


# ============================================================================
# SYSTEM METRICS
# ============================================================================


class SystemMetrics:
    """System-level metrics."""
    
    # Request metrics
    request_count = _safe_counter(
        "riskcast_http_requests_total",
        "Total HTTP requests",
        ["method", "endpoint", "status"],
    )
    
    request_latency = _safe_histogram(
        "riskcast_http_request_duration_seconds",
        "HTTP request latency",
        ["method", "endpoint"],
        buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10],
    )
    
    request_size = _safe_summary(
        "riskcast_http_request_size_bytes",
        "HTTP request size",
        ["method", "endpoint"],
    )
    
    response_size = _safe_summary(
        "riskcast_http_response_size_bytes",
        "HTTP response size",
        ["method", "endpoint"],
    )
    
    # Error metrics
    errors_total = _safe_counter(
        "riskcast_errors_total",
        "Total errors",
        ["type", "component"],
    )
    
    # Rate limiting
    rate_limit_checks = _safe_counter(
        "riskcast_rate_limit_checks_total",
        "Rate limit checks",
        ["key_type", "allowed"],
    )
    
    rate_limit_errors = _safe_counter(
        "riskcast_rate_limit_errors_total",
        "Rate limit errors (Redis failures)",
    )
    
    # Circuit breaker
    circuit_breaker_state = _safe_gauge(
        "riskcast_circuit_breaker_state",
        "Circuit breaker state (0=closed, 1=open, 2=half-open)",
        ["service"],
    )
    
    circuit_breaker_trips = _safe_counter(
        "riskcast_circuit_breaker_trips_total",
        "Circuit breaker trips",
        ["service"],
    )
    
    # Database metrics
    db_connections_active = _safe_gauge(
        "riskcast_db_connections_active",
        "Active database connections",
    )
    
    db_connections_pool_size = _safe_gauge(
        "riskcast_db_connections_pool_size",
        "Database connection pool size",
    )
    
    db_query_latency = _safe_histogram(
        "riskcast_db_query_duration_seconds",
        "Database query latency",
        ["operation", "table"],
        buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1],
    )
    
    # Redis metrics
    redis_operations = _safe_counter(
        "riskcast_redis_operations_total",
        "Redis operations",
        ["operation", "status"],
    )
    
    redis_latency = _safe_histogram(
        "riskcast_redis_latency_seconds",
        "Redis operation latency",
        ["operation"],
        buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1],
    )
    
    # External API metrics
    external_api_requests = _safe_counter(
        "riskcast_external_api_requests_total",
        "External API requests",
        ["service", "endpoint", "status"],
    )
    
    external_api_latency = _safe_histogram(
        "riskcast_external_api_latency_seconds",
        "External API latency",
        ["service", "endpoint"],
        buckets=[0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30],
    )


# ============================================================================
# APPLICATION INFO
# ============================================================================


def _safe_info(name: str, description: str) -> Info:
    """Create info metric, reusing if exists."""
    try:
        return Info(name, description)
    except ValueError:
        return DEFAULT_REGISTRY._names_to_collectors.get(name)


app_info = _safe_info(
    "riskcast_app",
    "RISKCAST application information",
)


# ============================================================================
# COMBINED METRICS CLASS
# ============================================================================


class Metrics(BusinessMetrics, SystemMetrics):
    """Combined metrics class with helper methods."""
    
    @staticmethod
    def generate_latest() -> bytes:
        """Generate latest metrics in Prometheus format."""
        return generate_latest()
    
    @staticmethod
    def content_type() -> str:
        """Get Prometheus content type."""
        return CONTENT_TYPE_LATEST


# Global metrics instance
METRICS = Metrics()


# ============================================================================
# DECORATORS
# ============================================================================


def track_latency(metric: Histogram, labels: Dict[str, str] = None):
    """
    Decorator to track function latency.
    
    Usage:
        @track_latency(METRICS.db_query_latency, {"operation": "select", "table": "customers"})
        async def get_customer(customer_id: str):
            ...
    """
    labels = labels or {}
    
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                return await func(*args, **kwargs)
            finally:
                duration = time.perf_counter() - start
                metric.labels(**labels).observe(duration)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                return func(*args, **kwargs)
            finally:
                duration = time.perf_counter() - start
                metric.labels(**labels).observe(duration)
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


def count_calls(metric: Counter, labels: Dict[str, str] = None):
    """
    Decorator to count function calls.
    
    Usage:
        @count_calls(METRICS.signals_received, {"category": "geopolitical"})
        async def process_signal(signal):
            ...
    """
    labels = labels or {}
    
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            metric.labels(**labels).inc()
            return await func(*args, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            metric.labels(**labels).inc()
            return func(*args, **kwargs)
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


# ============================================================================
# CONTEXT MANAGERS
# ============================================================================


@contextmanager
def track_time(metric: Histogram, labels: Dict[str, str] = None):
    """
    Context manager to track operation time.
    
    Usage:
        with track_time(METRICS.db_query_latency, {"operation": "insert"}):
            await session.commit()
    """
    labels = labels or {}
    start = time.perf_counter()
    try:
        yield
    finally:
        duration = time.perf_counter() - start
        metric.labels(**labels).observe(duration)


# ============================================================================
# METRIC RECORDING HELPERS
# ============================================================================


class MetricRecorder:
    """Helper class for recording metrics with business context."""
    
    @staticmethod
    def record_decision(
        chokepoint: str,
        severity: str,
        action_type: str,
        exposure_usd: float,
        confidence: float,
    ) -> None:
        """Record a generated decision."""
        METRICS.decisions_generated.labels(
            chokepoint=chokepoint,
            severity=severity,
            action_type=action_type,
        ).inc()
        
        # Update exposure gauge
        METRICS.total_exposure_usd.labels(chokepoint=chokepoint).set(exposure_usd)
        
        logger.info(
            "metric_decision_recorded",
            chokepoint=chokepoint,
            severity=severity,
            action_type=action_type,
            exposure_usd=exposure_usd,
        )
    
    @staticmethod
    def record_alert(
        channel: str,
        template: str,
        status: str,
        delivery_time_seconds: Optional[float] = None,
    ) -> None:
        """Record an alert."""
        METRICS.alerts_sent.labels(
            channel=channel,
            template=template,
            status=status,
        ).inc()
        
        if delivery_time_seconds is not None:
            METRICS.alert_delivery_time.labels(channel=channel).observe(
                delivery_time_seconds
            )
    
    @staticmethod
    def record_signal(
        category: str,
        source: str,
        correlation_status: Optional[str] = None,
    ) -> None:
        """Record an OMEN signal."""
        METRICS.signals_received.labels(
            category=category,
            source=source,
        ).inc()
        
        if correlation_status:
            METRICS.signals_correlated.labels(
                correlation_status=correlation_status,
            ).inc()
    
    @staticmethod
    def record_api_call(
        service: str,
        endpoint: str,
        status: str,
        latency_seconds: float,
    ) -> None:
        """Record an external API call."""
        METRICS.external_api_requests.labels(
            service=service,
            endpoint=endpoint,
            status=status,
        ).inc()
        
        METRICS.external_api_latency.labels(
            service=service,
            endpoint=endpoint,
        ).observe(latency_seconds)
    
    @staticmethod
    def record_error(error_type: str, component: str) -> None:
        """Record an error."""
        METRICS.errors_total.labels(
            type=error_type,
            component=component,
        ).inc()
    
    @staticmethod
    def update_prediction_accuracy(
        metric_type: str,
        accuracy: float,
        window: str = "24h",
    ) -> None:
        """Update prediction accuracy gauge."""
        METRICS.prediction_accuracy.labels(
            metric_type=metric_type,
            window=window,
        ).set(accuracy)
    
    @staticmethod
    def update_confidence_calibration(
        bucket: str,
        score: float,
    ) -> None:
        """Update confidence calibration score."""
        METRICS.confidence_calibration.labels(bucket=bucket).set(score)


# Global recorder instance
RECORDER = MetricRecorder()


# ============================================================================
# INITIALIZATION
# ============================================================================

import asyncio


def init_metrics(
    app_name: str = "riskcast",
    version: str = "1.0.0",
    environment: str = "development",
) -> None:
    """Initialize metrics with application info."""
    app_info.info({
        "name": app_name,
        "version": version,
        "environment": environment,
    })
    
    logger.info(
        "metrics_initialized",
        app_name=app_name,
        version=version,
        environment=environment,
    )
