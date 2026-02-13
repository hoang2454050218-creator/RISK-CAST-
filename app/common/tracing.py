"""
Distributed Tracing with OpenTelemetry.

Provides request tracing across services for debugging and performance analysis.

Components:
1. Trace Context - Propagates trace IDs across services
2. Spans - Track individual operations
3. Attributes - Add context to spans
4. Exporters - Send traces to backend (Jaeger, etc.)
"""

from typing import Optional, Any
from functools import wraps
from contextlib import contextmanager
import time

import structlog

# OpenTelemetry imports (optional - graceful degradation)
try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False

logger = structlog.get_logger(__name__)


# ============================================================================
# CONFIGURATION
# ============================================================================


class TracingConfig:
    """Tracing configuration."""

    def __init__(
        self,
        service_name: str = "riskcast",
        environment: str = "development",
        enabled: bool = True,
        jaeger_endpoint: Optional[str] = None,
        sample_rate: float = 1.0,
    ):
        self.service_name = service_name
        self.environment = environment
        self.enabled = enabled and OTEL_AVAILABLE
        self.jaeger_endpoint = jaeger_endpoint
        self.sample_rate = sample_rate


# Global config
_config: Optional[TracingConfig] = None
_tracer: Optional[Any] = None


# ============================================================================
# INITIALIZATION
# ============================================================================


def init_tracing(config: Optional[TracingConfig] = None):
    """
    Initialize OpenTelemetry tracing.

    Args:
        config: Tracing configuration
    """
    global _config, _tracer

    if config is None:
        config = TracingConfig()

    _config = config

    if not config.enabled:
        logger.info("tracing_disabled")
        return

    if not OTEL_AVAILABLE:
        logger.warning("opentelemetry_not_installed")
        return

    # Create resource
    resource = Resource.create({
        "service.name": config.service_name,
        "deployment.environment": config.environment,
    })

    # Create tracer provider
    provider = TracerProvider(resource=resource)

    # Add exporters
    if config.jaeger_endpoint:
        try:
            from opentelemetry.exporter.jaeger.thrift import JaegerExporter

            jaeger_exporter = JaegerExporter(
                agent_host_name=config.jaeger_endpoint.split(":")[0],
                agent_port=int(config.jaeger_endpoint.split(":")[1]) if ":" in config.jaeger_endpoint else 6831,
            )
            provider.add_span_processor(BatchSpanProcessor(jaeger_exporter))
            logger.info("jaeger_exporter_configured", endpoint=config.jaeger_endpoint)
        except Exception as e:
            logger.warning("jaeger_exporter_failed", error=str(e))
    else:
        # Console exporter for development
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

    # Set global tracer provider
    trace.set_tracer_provider(provider)

    # Get tracer
    _tracer = trace.get_tracer(config.service_name)

    logger.info(
        "tracing_initialized",
        service=config.service_name,
        environment=config.environment,
    )


def instrument_fastapi(app):
    """
    Instrument FastAPI application.

    Args:
        app: FastAPI application instance
    """
    if not OTEL_AVAILABLE or not _config or not _config.enabled:
        return

    try:
        FastAPIInstrumentor.instrument_app(app)
        logger.info("fastapi_instrumented")
    except Exception as e:
        logger.warning("fastapi_instrumentation_failed", error=str(e))


def instrument_httpx():
    """Instrument httpx HTTP client."""
    if not OTEL_AVAILABLE or not _config or not _config.enabled:
        return

    try:
        HTTPXClientInstrumentor().instrument()
        logger.info("httpx_instrumented")
    except Exception as e:
        logger.warning("httpx_instrumentation_failed", error=str(e))


# ============================================================================
# SPAN CREATION
# ============================================================================


@contextmanager
def create_span(
    name: str,
    attributes: Optional[dict[str, Any]] = None,
    kind: str = "internal",
):
    """
    Create a new span as context manager.

    Args:
        name: Span name
        attributes: Span attributes
        kind: Span kind (internal, server, client, producer, consumer)

    Usage:
        with create_span("process_signal", {"signal_id": signal.id}) as span:
            # Do work
            span.set_attribute("result", "success")
    """
    if not OTEL_AVAILABLE or not _tracer:
        # No-op context manager
        class NoOpSpan:
            def set_attribute(self, key, value): pass
            def add_event(self, name, attributes=None): pass
            def set_status(self, status): pass
            def record_exception(self, exc): pass

        yield NoOpSpan()
        return

    # Map kind string to SpanKind
    span_kinds = {
        "internal": trace.SpanKind.INTERNAL,
        "server": trace.SpanKind.SERVER,
        "client": trace.SpanKind.CLIENT,
        "producer": trace.SpanKind.PRODUCER,
        "consumer": trace.SpanKind.CONSUMER,
    }
    span_kind = span_kinds.get(kind, trace.SpanKind.INTERNAL)

    with _tracer.start_as_current_span(name, kind=span_kind) as span:
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, value)
        yield span


def trace_function(
    name: Optional[str] = None,
    attributes: Optional[dict[str, Any]] = None,
):
    """
    Decorator to trace a function.

    Args:
        name: Span name (defaults to function name)
        attributes: Static attributes to add

    Usage:
        @trace_function("process_decision")
        async def process(decision):
            ...
    """
    def decorator(func):
        span_name = name or func.__name__

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            with create_span(span_name, attributes) as span:
                try:
                    result = await func(*args, **kwargs)
                    span.set_attribute("success", True)
                    return result
                except Exception as e:
                    span.set_attribute("success", False)
                    span.record_exception(e)
                    raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            with create_span(span_name, attributes) as span:
                try:
                    result = func(*args, **kwargs)
                    span.set_attribute("success", True)
                    return result
                except Exception as e:
                    span.set_attribute("success", False)
                    span.record_exception(e)
                    raise

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


# ============================================================================
# TRACE CONTEXT
# ============================================================================


def get_current_trace_id() -> Optional[str]:
    """Get current trace ID."""
    if not OTEL_AVAILABLE:
        return None

    span = trace.get_current_span()
    if span:
        context = span.get_span_context()
        if context.is_valid:
            return format(context.trace_id, "032x")
    return None


def get_current_span_id() -> Optional[str]:
    """Get current span ID."""
    if not OTEL_AVAILABLE:
        return None

    span = trace.get_current_span()
    if span:
        context = span.get_span_context()
        if context.is_valid:
            return format(context.span_id, "016x")
    return None


def inject_trace_context(headers: dict) -> dict:
    """
    Inject trace context into headers for propagation.

    Args:
        headers: Headers dict to inject into

    Returns:
        Headers with trace context
    """
    if not OTEL_AVAILABLE:
        return headers

    propagator = TraceContextTextMapPropagator()
    propagator.inject(headers)
    return headers


def extract_trace_context(headers: dict):
    """
    Extract trace context from headers.

    Args:
        headers: Headers containing trace context

    Returns:
        Context object
    """
    if not OTEL_AVAILABLE:
        return None

    propagator = TraceContextTextMapPropagator()
    return propagator.extract(headers)


# ============================================================================
# LOGGING INTEGRATION
# ============================================================================


def add_trace_to_log_context() -> dict:
    """
    Get trace context for logging.

    Returns:
        Dict with trace_id and span_id for structlog
    """
    trace_id = get_current_trace_id()
    span_id = get_current_span_id()

    context = {}
    if trace_id:
        context["trace_id"] = trace_id
    if span_id:
        context["span_id"] = span_id

    return context


# ============================================================================
# SHUTDOWN
# ============================================================================


def shutdown_tracing():
    """Shutdown tracing and flush spans."""
    if not OTEL_AVAILABLE:
        return

    try:
        provider = trace.get_tracer_provider()
        if hasattr(provider, "shutdown"):
            provider.shutdown()
        logger.info("tracing_shutdown")
    except Exception as e:
        logger.warning("tracing_shutdown_failed", error=str(e))
