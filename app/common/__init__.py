"""
Common utilities for RISKCAST.

Provides shared functionality:
- Resilience patterns (retry, circuit breaker)
- Metrics collection
- Distributed tracing
- Caching utilities
"""

from app.common.resilience import (
    retry_with_backoff,
    CircuitBreaker,
    circuit_breaker,
    CircuitState,
    CircuitOpenError,
    RetryExhaustedError,
    with_timeout,
    with_fallback,
)
from app.common.metrics import (
    get_metrics,
    get_metrics_content_type,
    record_decision,
    record_delivery,
    record_http_request,
    update_gauges,
    set_service_info,
    track_time,
    track_counter,
)
from app.common.tracing import (
    init_tracing,
    TracingConfig,
    instrument_fastapi,
    instrument_httpx,
    create_span,
    trace_function,
    get_current_trace_id,
    inject_trace_context,
    shutdown_tracing,
)

__all__ = [
    # Resilience
    "retry_with_backoff",
    "CircuitBreaker",
    "circuit_breaker",
    "CircuitState",
    "CircuitOpenError",
    "RetryExhaustedError",
    "with_timeout",
    "with_fallback",
    # Metrics
    "get_metrics",
    "get_metrics_content_type",
    "record_decision",
    "record_delivery",
    "record_http_request",
    "update_gauges",
    "set_service_info",
    "track_time",
    "track_counter",
    # Tracing
    "init_tracing",
    "TracingConfig",
    "instrument_fastapi",
    "instrument_httpx",
    "create_span",
    "trace_function",
    "get_current_trace_id",
    "inject_trace_context",
    "shutdown_tracing",
]
