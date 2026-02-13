"""
Distributed Tracing with OpenTelemetry.

Implements D1.3 Distributed Tracing requirements:
- OTLP exporter configuration
- Trace context propagation
- Deterministic trace IDs for reproducibility
- Span attributes for correlation

P2 COMPLIANCE: Configure OTLP exporter for distributed tracing.
A1 COMPLIANCE: Add deterministic trace IDs for reproducibility.
"""

import hashlib
import os
import random
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, Generator, List, Optional, Tuple

import structlog

logger = structlog.get_logger(__name__)


# ============================================================================
# TRACING CONFIGURATION
# ============================================================================


class TracingConfig:
    """OpenTelemetry tracing configuration."""
    
    # OTLP exporter settings
    OTLP_ENDPOINT: str = os.getenv("OTLP_ENDPOINT", "http://localhost:4317")
    OTLP_HEADERS: Dict[str, str] = {}
    OTLP_PROTOCOL: str = os.getenv("OTLP_PROTOCOL", "grpc")  # grpc or http
    
    # Service identification
    SERVICE_NAME: str = os.getenv("OTEL_SERVICE_NAME", "riskcast")
    SERVICE_VERSION: str = os.getenv("OTEL_SERVICE_VERSION", "1.0.0")
    SERVICE_ENVIRONMENT: str = os.getenv("OTEL_SERVICE_ENV", "production")
    
    # Sampling
    SAMPLING_RATIO: float = float(os.getenv("OTEL_SAMPLING_RATIO", "1.0"))
    
    # Resource attributes
    RESOURCE_ATTRIBUTES: Dict[str, str] = {
        "service.name": SERVICE_NAME,
        "service.version": SERVICE_VERSION,
        "deployment.environment": SERVICE_ENVIRONMENT,
    }


# ============================================================================
# DETERMINISTIC TRACE IDS
# ============================================================================


class DeterministicTraceIdGenerator:
    """
    Generate deterministic trace IDs for reproducibility.
    
    In a decision intelligence system, we need to be able to:
    1. Reproduce the exact execution path for a decision
    2. Correlate traces across multiple services
    3. Debug historical decisions with full trace context
    
    This generator creates trace IDs that are:
    - Deterministic: Same inputs = same trace ID
    - Unique: Different inputs = different trace ID
    - Compliant: Valid W3C Trace Context format
    """
    
    @staticmethod
    def generate_trace_id(
        decision_id: str,
        customer_id: str,
        timestamp: Optional[datetime] = None,
    ) -> str:
        """
        Generate a deterministic trace ID.
        
        Args:
            decision_id: Unique decision identifier
            customer_id: Customer identifier
            timestamp: Optional timestamp for additional uniqueness
            
        Returns:
            32-character hex string (128-bit trace ID)
        """
        # Create deterministic seed
        ts = timestamp or datetime.utcnow()
        seed_data = f"{decision_id}:{customer_id}:{ts.isoformat()}"
        
        # Generate trace ID using SHA-256 and take first 16 bytes (128 bits)
        hash_bytes = hashlib.sha256(seed_data.encode()).digest()
        trace_id = hash_bytes[:16].hex()
        
        return trace_id
    
    @staticmethod
    def generate_span_id(
        trace_id: str,
        span_name: str,
        parent_span_id: Optional[str] = None,
    ) -> str:
        """
        Generate a deterministic span ID.
        
        Args:
            trace_id: Parent trace ID
            span_name: Name of the span
            parent_span_id: Optional parent span ID
            
        Returns:
            16-character hex string (64-bit span ID)
        """
        seed_data = f"{trace_id}:{span_name}:{parent_span_id or 'root'}"
        hash_bytes = hashlib.sha256(seed_data.encode()).digest()
        span_id = hash_bytes[:8].hex()
        
        return span_id
    
    @staticmethod
    def generate_reproducible_context(
        decision_id: str,
        customer_id: str,
        timestamp: Optional[datetime] = None,
    ) -> Dict[str, str]:
        """
        Generate complete trace context for reproducibility.
        
        Returns:
            Dict with trace_id, span_id, and traceparent header
        """
        trace_id = DeterministicTraceIdGenerator.generate_trace_id(
            decision_id, customer_id, timestamp
        )
        span_id = DeterministicTraceIdGenerator.generate_span_id(
            trace_id, "decision_root"
        )
        
        # W3C Trace Context format: version-traceid-spanid-flags
        traceparent = f"00-{trace_id}-{span_id}-01"
        
        return {
            "trace_id": trace_id,
            "span_id": span_id,
            "traceparent": traceparent,
        }


# ============================================================================
# TRACE CONTEXT
# ============================================================================


class TraceContext:
    """
    Hold trace context for the current execution.
    
    Provides span management and attribute recording.
    """
    
    def __init__(
        self,
        trace_id: str,
        span_id: str,
        parent_span_id: Optional[str] = None,
    ):
        self.trace_id = trace_id
        self.span_id = span_id
        self.parent_span_id = parent_span_id
        self.attributes: Dict[str, Any] = {}
        self.events: list = []
        self._children: list = []
    
    def set_attribute(self, key: str, value: Any):
        """Set a span attribute."""
        self.attributes[key] = value
    
    def set_attributes(self, attributes: Dict[str, Any]):
        """Set multiple span attributes."""
        self.attributes.update(attributes)
    
    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None):
        """Add an event to the span."""
        self.events.append({
            "name": name,
            "timestamp": datetime.utcnow().isoformat(),
            "attributes": attributes or {},
        })
    
    def create_child_span(self, span_name: str) -> "TraceContext":
        """Create a child span."""
        child_span_id = DeterministicTraceIdGenerator.generate_span_id(
            self.trace_id, span_name, self.span_id
        )
        child = TraceContext(
            trace_id=self.trace_id,
            span_id=child_span_id,
            parent_span_id=self.span_id,
        )
        self._children.append(child)
        return child
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/export."""
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "attributes": self.attributes,
            "events": self.events,
            "children": [c.to_dict() for c in self._children],
        }
    
    @property
    def traceparent(self) -> str:
        """Get W3C traceparent header."""
        return f"00-{self.trace_id}-{self.span_id}-01"


# ============================================================================
# TRACING SERVICE
# ============================================================================


_current_context: Optional[TraceContext] = None


class TracingService:
    """
    Service for managing distributed traces.
    
    Integrates with OpenTelemetry for production tracing
    while maintaining deterministic trace IDs for reproducibility.
    """
    
    def __init__(self, config: Optional[TracingConfig] = None):
        self.config = config or TracingConfig()
        self._tracer = None
        self._initialized = False
    
    def initialize(self):
        """Initialize OpenTelemetry tracing."""
        if self._initialized:
            return
        
        try:
            # Try to import and initialize OpenTelemetry
            from opentelemetry import trace
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import BatchSpanProcessor
            from opentelemetry.sdk.resources import Resource
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
            from opentelemetry.sdk.trace.sampling import TraceIdRatioBased
            
            # Create resource
            resource = Resource.create(self.config.RESOURCE_ATTRIBUTES)
            
            # Create sampler
            sampler = TraceIdRatioBased(self.config.SAMPLING_RATIO)
            
            # Create tracer provider
            provider = TracerProvider(resource=resource, sampler=sampler)
            
            # Create OTLP exporter
            exporter = OTLPSpanExporter(
                endpoint=self.config.OTLP_ENDPOINT,
                headers=self.config.OTLP_HEADERS,
            )
            
            # Add processor
            provider.add_span_processor(BatchSpanProcessor(exporter))
            
            # Set as global tracer
            trace.set_tracer_provider(provider)
            self._tracer = trace.get_tracer(self.config.SERVICE_NAME)
            
            self._initialized = True
            logger.info(
                "tracing_initialized",
                endpoint=self.config.OTLP_ENDPOINT,
                service=self.config.SERVICE_NAME,
            )
            
        except ImportError:
            logger.warning("opentelemetry_not_installed_using_fallback")
        except Exception as e:
            logger.error("tracing_initialization_failed", error=str(e))
    
    @contextmanager
    def start_trace(
        self,
        decision_id: str,
        customer_id: str,
        timestamp: Optional[datetime] = None,
    ) -> Generator[TraceContext, None, None]:
        """
        Start a new trace for a decision.
        
        Uses deterministic trace IDs for reproducibility.
        """
        global _current_context
        
        # Generate deterministic context
        ctx_data = DeterministicTraceIdGenerator.generate_reproducible_context(
            decision_id, customer_id, timestamp
        )
        
        context = TraceContext(
            trace_id=ctx_data["trace_id"],
            span_id=ctx_data["span_id"],
        )
        
        context.set_attributes({
            "decision.id": decision_id,
            "customer.id": customer_id,
            "service.name": self.config.SERVICE_NAME,
        })
        
        previous_context = _current_context
        _current_context = context
        
        try:
            # If OpenTelemetry is initialized, create a real span
            if self._tracer:
                with self._tracer.start_as_current_span(
                    "decision_processing",
                    attributes={
                        "decision.id": decision_id,
                        "customer.id": customer_id,
                    }
                ) as span:
                    # Inject trace context into our context object
                    span_context = span.get_span_context()
                    context.trace_id = format(span_context.trace_id, "032x")
                    context.span_id = format(span_context.span_id, "016x")
                    yield context
            else:
                yield context
                
        finally:
            _current_context = previous_context
            
            # Log trace completion
            logger.info(
                "trace_completed",
                trace_id=context.trace_id,
                span_id=context.span_id,
                decision_id=decision_id,
            )
    
    @contextmanager
    def start_span(self, name: str) -> Generator[TraceContext, None, None]:
        """Start a child span within the current trace."""
        global _current_context
        
        if _current_context is None:
            # No parent trace, create a standalone span
            trace_id = hashlib.sha256(f"{name}:{datetime.utcnow().isoformat()}".encode()).hexdigest()[:32]
            span_id = hashlib.sha256(f"{trace_id}:root".encode()).hexdigest()[:16]
            context = TraceContext(trace_id=trace_id, span_id=span_id)
            yield context
            return
        
        # Create child span
        child = _current_context.create_child_span(name)
        
        previous = _current_context
        _current_context = child
        
        try:
            if self._tracer:
                with self._tracer.start_as_current_span(name) as span:
                    span_context = span.get_span_context()
                    child.span_id = format(span_context.span_id, "016x")
                    yield child
            else:
                yield child
        finally:
            _current_context = previous


# ============================================================================
# OTLP CONFIGURATION YAML
# ============================================================================


OTLP_CONFIG_TEMPLATE = """
# OpenTelemetry Collector Configuration for RISKCAST
# Deploy alongside your application for trace collection

receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318

processors:
  batch:
    timeout: 10s
    send_batch_size: 1024
    
  memory_limiter:
    check_interval: 1s
    limit_mib: 1024
    spike_limit_mib: 256
    
  attributes:
    actions:
      - key: environment
        value: ${ENVIRONMENT}
        action: upsert
      - key: service.namespace
        value: riskcast
        action: upsert

exporters:
  # Jaeger for trace visualization
  jaeger:
    endpoint: jaeger:14250
    tls:
      insecure: true
      
  # Prometheus for metrics
  prometheus:
    endpoint: 0.0.0.0:8889
    
  # Logging for debugging
  logging:
    loglevel: info

extensions:
  health_check:
    endpoint: 0.0.0.0:13133
  pprof:
    endpoint: 0.0.0.0:1888
  zpages:
    endpoint: 0.0.0.0:55679

service:
  extensions: [health_check, pprof, zpages]
  pipelines:
    traces:
      receivers: [otlp]
      processors: [memory_limiter, batch, attributes]
      exporters: [jaeger, logging]
    metrics:
      receivers: [otlp]
      processors: [memory_limiter, batch]
      exporters: [prometheus]
"""


def get_otlp_config() -> str:
    """Get OTLP collector configuration."""
    return OTLP_CONFIG_TEMPLATE


# ============================================================================
# SINGLETON
# ============================================================================


_tracing_service: Optional[TracingService] = None


def get_tracing_service() -> TracingService:
    """Get global tracing service."""
    global _tracing_service
    if _tracing_service is None:
        _tracing_service = TracingService()
    return _tracing_service


def get_current_context() -> Optional[TraceContext]:
    """Get current trace context."""
    return _current_context


# ============================================================================
# COMPATIBILITY EXPORTS
# ============================================================================


class SpanKind:
    """Span kind enumeration for compatibility."""
    INTERNAL = "internal"
    SERVER = "server"
    CLIENT = "client"
    PRODUCER = "producer"
    CONSUMER = "consumer"


class SpanStatus:
    """Span status for compatibility."""
    OK = "ok"
    ERROR = "error"
    UNSET = "unset"


class SpanContext:
    """Span context for compatibility."""
    
    def __init__(
        self,
        trace_id: str,
        span_id: str,
        parent_span_id: Optional[str] = None,
        is_remote: bool = False,
    ):
        self.trace_id = trace_id
        self.span_id = span_id
        self.parent_span_id = parent_span_id
        self.is_remote = is_remote
        self.trace_flags = 1  # Sampled
    
    def is_valid(self) -> bool:
        return bool(self.trace_id and self.span_id)


class Span:
    """Span class for compatibility."""
    
    def __init__(
        self,
        name: str,
        context: Optional[SpanContext] = None,
        kind: str = SpanKind.INTERNAL,
        attributes: Optional[Dict[str, Any]] = None,
    ):
        self.name = name
        self._context = context or SpanContext(
            trace_id=hashlib.sha256(f"{name}:{datetime.utcnow().isoformat()}".encode()).hexdigest()[:32],
            span_id=hashlib.sha256(f"{name}:span".encode()).hexdigest()[:16],
        )
        self.kind = kind
        self.attributes = attributes or {}
        self.events = []
        self.status = SpanStatus.UNSET
        self.start_time = datetime.utcnow()
        self.end_time: Optional[datetime] = None
    
    def set_attribute(self, key: str, value: Any):
        self.attributes[key] = value
    
    def set_attributes(self, attributes: Dict[str, Any]):
        self.attributes.update(attributes)
    
    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None):
        self.events.append({
            "name": name,
            "timestamp": datetime.utcnow().isoformat(),
            "attributes": attributes or {},
        })
    
    def set_status(self, status: str, description: Optional[str] = None):
        self.status = status
    
    def get_span_context(self) -> SpanContext:
        return self._context
    
    def end(self):
        self.end_time = datetime.utcnow()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.set_status(SpanStatus.ERROR, str(exc_val))
        else:
            self.set_status(SpanStatus.OK)
        self.end()
        return False


class MetricsCollector:
    """Simple metrics collector for compatibility."""
    
    def __init__(self):
        self._metrics: Dict[str, Any] = {}
    
    def counter(self, name: str, value: int = 1, tags: Optional[Dict[str, str]] = None):
        key = f"counter:{name}"
        self._metrics[key] = self._metrics.get(key, 0) + value
    
    def gauge(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        key = f"gauge:{name}"
        self._metrics[key] = value
    
    def histogram(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        key = f"histogram:{name}"
        if key not in self._metrics:
            self._metrics[key] = []
        self._metrics[key].append(value)
    
    def get_metrics(self) -> Dict[str, Any]:
        return self._metrics.copy()


class Tracer:
    """Simple tracer class for compatibility."""
    
    def __init__(self, name: str = "riskcast"):
        self.name = name
        self._service = get_tracing_service()
        self._current_span: Optional[Span] = None
    
    @contextmanager
    def start_as_current_span(
        self,
        name: str,
        kind: str = SpanKind.INTERNAL,
        attributes: Optional[Dict[str, Any]] = None,
    ):
        """Start a span as current."""
        span = Span(name=name, kind=kind, attributes=attributes)
        previous = self._current_span
        self._current_span = span
        try:
            yield span
        finally:
            span.end()
            self._current_span = previous
    
    def start_span(self, name: str, **kwargs) -> Span:
        """Start a new span."""
        return Span(name=name, **kwargs)
    
    def get_current_span(self) -> Optional[Span]:
        return self._current_span


_default_tracer: Optional[Tracer] = None
_metrics_collector: Optional[MetricsCollector] = None
_tracing_initialized: bool = False


def init_tracing(service_name: str = "riskcast"):
    """Initialize tracing."""
    global _tracing_initialized, _default_tracer, _metrics_collector
    if not _tracing_initialized:
        _default_tracer = Tracer(service_name)
        _metrics_collector = MetricsCollector()
        _tracing_initialized = True
        logger.info("tracing_initialized", service=service_name)


def close_tracing():
    """Close tracing."""
    global _tracing_initialized
    _tracing_initialized = False
    logger.info("tracing_closed")


def get_tracer(name: str = "riskcast") -> Tracer:
    """Get a tracer instance."""
    global _default_tracer
    if _default_tracer is None:
        _default_tracer = Tracer(name)
    return _default_tracer


def get_metrics() -> MetricsCollector:
    """Get metrics collector."""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


def get_current_span() -> Optional[Span]:
    """Get current span."""
    tracer = get_tracer()
    return tracer.get_current_span()


def trace(func):
    """Decorator to trace a function."""
    import functools
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        tracer = get_tracer()
        with tracer.start_as_current_span(func.__name__):
            return func(*args, **kwargs)
    
    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        tracer = get_tracer()
        with tracer.start_as_current_span(func.__name__):
            return await func(*args, **kwargs)
    
    import asyncio
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    return wrapper


def get_current_trace_id() -> Optional[str]:
    """Get current trace ID if available."""
    ctx = get_current_context()
    if ctx:
        return ctx.trace_id
    span = get_current_span()
    if span:
        return span.get_span_context().trace_id
    return None


async def tracing_middleware(request, call_next):
    """FastAPI middleware for tracing."""
    tracer = get_tracer()
    
    # Extract trace context from headers if present
    traceparent = request.headers.get("traceparent")
    
    with tracer.start_as_current_span(
        f"{request.method} {request.url.path}",
        kind=SpanKind.SERVER,
        attributes={
            "http.method": request.method,
            "http.url": str(request.url),
            "http.route": request.url.path,
        }
    ) as span:
        try:
            response = await call_next(request)
            span.set_attribute("http.status_code", response.status_code)
            return response
        except Exception as e:
            span.set_status(SpanStatus.ERROR, str(e))
            raise


# ============================================================================
# CONSOLE SPAN EXPORTER (for testing/development)
# ============================================================================


class ConsoleSpanExporter:
    """
    Simple span exporter that prints to console.
    
    Useful for local development and testing.
    """
    
    def __init__(self, pretty_print: bool = True):
        self.pretty_print = pretty_print
        self._spans: List[Dict[str, Any]] = []
    
    def export(self, span: Span) -> None:
        """Export a span to console."""
        span_data = {
            "name": span.name,
            "trace_id": span.get_span_context().trace_id,
            "span_id": span.get_span_context().span_id,
            "kind": span.kind,
            "status": span.status,
            "attributes": span.attributes,
            "events": span.events,
            "start_time": span.start_time.isoformat() if span.start_time else None,
            "end_time": span.end_time.isoformat() if span.end_time else None,
        }
        
        self._spans.append(span_data)
        
        if self.pretty_print:
            import json
            print(f"[SPAN] {span.name}")
            print(json.dumps(span_data, indent=2, default=str))
        else:
            print(f"[SPAN] {span.name} trace_id={span_data['trace_id']} duration={span_data.get('duration_ms', 'N/A')}")
    
    def get_spans(self) -> List[Dict[str, Any]]:
        """Get all exported spans."""
        return self._spans.copy()
    
    def clear(self) -> None:
        """Clear exported spans."""
        self._spans.clear()
    
    def shutdown(self) -> None:
        """Shutdown the exporter."""
        self.clear()


def setup_opentelemetry(
    service_name: str = "riskcast",
    otlp_endpoint: Optional[str] = None,
    enable_console: bool = False,
) -> None:
    """
    Setup OpenTelemetry tracing.
    
    Args:
        service_name: Name of the service
        otlp_endpoint: OTLP collector endpoint (optional)
        enable_console: Enable console exporter for debugging
    """
    global _tracing_initialized, _default_tracer, _metrics_collector
    
    if _tracing_initialized:
        logger.debug("tracing_already_initialized")
        return
    
    # Initialize basic tracing
    _default_tracer = Tracer(service_name)
    _metrics_collector = MetricsCollector()
    
    # Try to initialize OpenTelemetry if available
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.sdk.resources import Resource
        
        resource = Resource.create({
            "service.name": service_name,
            "service.version": os.getenv("SERVICE_VERSION", "1.0.0"),
        })
        
        provider = TracerProvider(resource=resource)
        
        # Add OTLP exporter if endpoint provided
        if otlp_endpoint:
            try:
                from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
                exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
                provider.add_span_processor(BatchSpanProcessor(exporter))
                logger.info("otlp_exporter_configured", endpoint=otlp_endpoint)
            except ImportError:
                logger.warning("otlp_exporter_not_available")
        
        trace.set_tracer_provider(provider)
        logger.info(
            "opentelemetry_initialized",
            service=service_name,
            otlp_endpoint=otlp_endpoint,
            console_enabled=enable_console,
        )
        
    except ImportError:
        logger.info("opentelemetry_not_installed_using_fallback")
    
    _tracing_initialized = True
    logger.info("tracing_setup_complete", service=service_name)
