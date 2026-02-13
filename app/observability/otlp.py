"""
OpenTelemetry Protocol (OTLP) integration for RISKCAST.

This module implements GAP D1.2: OTLP telemetry not configured.
Provides distributed tracing, metrics, and logging export via OTLP.
"""

from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union
import asyncio
import time
import structlog

logger = structlog.get_logger(__name__)


class TelemetryType(str, Enum):
    """Types of telemetry data."""
    TRACE = "trace"
    METRIC = "metric"
    LOG = "log"


@dataclass
class OTLPConfig:
    """OTLP exporter configuration."""
    # Endpoint configuration
    endpoint: str = "http://localhost:4317"  # gRPC default
    http_endpoint: str = "http://localhost:4318"  # HTTP default
    use_grpc: bool = True
    
    # Authentication
    headers: Dict[str, str] = None
    
    # Export settings
    export_interval_ms: int = 5000
    export_timeout_ms: int = 10000
    max_export_batch_size: int = 512
    max_queue_size: int = 2048
    
    # Resource attributes
    service_name: str = "riskcast"
    service_version: str = "1.0.0"
    deployment_environment: str = "production"
    
    # Sampling
    trace_sample_rate: float = 1.0  # 100% in production for decisions
    
    # Retry settings
    max_retries: int = 5
    retry_delay_ms: int = 1000
    
    def __post_init__(self):
        if self.headers is None:
            self.headers = {}


@dataclass
class SpanContext:
    """Context for a trace span."""
    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    trace_flags: int = 1  # Sampled
    trace_state: str = ""


@dataclass
class Span:
    """A trace span."""
    name: str
    context: SpanContext
    start_time_ns: int
    end_time_ns: Optional[int] = None
    
    # Span data
    kind: str = "internal"  # internal, server, client, producer, consumer
    status_code: str = "ok"  # ok, error, unset
    status_message: str = ""
    
    # Attributes
    attributes: Dict[str, Any] = None
    
    # Events and links
    events: List[Dict[str, Any]] = None
    links: List[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.attributes is None:
            self.attributes = {}
        if self.events is None:
            self.events = []
        if self.links is None:
            self.links = []
    
    def set_attribute(self, key: str, value: Any) -> None:
        """Set a span attribute."""
        self.attributes[key] = value
    
    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> None:
        """Add an event to the span."""
        self.events.append({
            "name": name,
            "timestamp_ns": time.time_ns(),
            "attributes": attributes or {},
        })
    
    def set_status(self, code: str, message: str = "") -> None:
        """Set span status."""
        self.status_code = code
        self.status_message = message
    
    def end(self, end_time_ns: Optional[int] = None) -> None:
        """End the span."""
        self.end_time_ns = end_time_ns or time.time_ns()
    
    @property
    def duration_ms(self) -> float:
        """Get span duration in milliseconds."""
        if self.end_time_ns:
            return (self.end_time_ns - self.start_time_ns) / 1_000_000
        return (time.time_ns() - self.start_time_ns) / 1_000_000
    
    def to_otlp(self) -> Dict[str, Any]:
        """Convert to OTLP format."""
        return {
            "traceId": self.context.trace_id,
            "spanId": self.context.span_id,
            "parentSpanId": self.context.parent_span_id,
            "name": self.name,
            "kind": self.kind.upper(),
            "startTimeUnixNano": str(self.start_time_ns),
            "endTimeUnixNano": str(self.end_time_ns or time.time_ns()),
            "attributes": [
                {"key": k, "value": self._format_value(v)}
                for k, v in self.attributes.items()
            ],
            "events": [
                {
                    "name": e["name"],
                    "timeUnixNano": str(e["timestamp_ns"]),
                    "attributes": [
                        {"key": k, "value": self._format_value(v)}
                        for k, v in e.get("attributes", {}).items()
                    ],
                }
                for e in self.events
            ],
            "status": {
                "code": 1 if self.status_code == "ok" else 2,
                "message": self.status_message,
            },
        }
    
    def _format_value(self, value: Any) -> Dict[str, Any]:
        """Format value for OTLP."""
        if isinstance(value, bool):
            return {"boolValue": value}
        elif isinstance(value, int):
            return {"intValue": str(value)}
        elif isinstance(value, float):
            return {"doubleValue": value}
        elif isinstance(value, (list, tuple)):
            return {"arrayValue": {"values": [self._format_value(v) for v in value]}}
        else:
            return {"stringValue": str(value)}


@dataclass
class Metric:
    """A metric data point."""
    name: str
    description: str = ""
    unit: str = ""
    
    # Metric type
    metric_type: str = "gauge"  # gauge, counter, histogram, summary
    
    # Data points
    data_points: List[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.data_points is None:
            self.data_points = []
    
    def add_data_point(
        self,
        value: Union[int, float],
        attributes: Optional[Dict[str, Any]] = None,
        timestamp_ns: Optional[int] = None,
    ) -> None:
        """Add a data point."""
        self.data_points.append({
            "value": value,
            "attributes": attributes or {},
            "timestamp_ns": timestamp_ns or time.time_ns(),
        })
    
    def to_otlp(self) -> Dict[str, Any]:
        """Convert to OTLP format."""
        return {
            "name": self.name,
            "description": self.description,
            "unit": self.unit,
            self.metric_type: {
                "dataPoints": [
                    {
                        "attributes": [
                            {"key": k, "value": {"stringValue": str(v)}}
                            for k, v in dp["attributes"].items()
                        ],
                        "timeUnixNano": str(dp["timestamp_ns"]),
                        "asDouble": float(dp["value"]) if isinstance(dp["value"], (int, float)) else 0,
                    }
                    for dp in self.data_points
                ],
            },
        }


class OTLPExporter:
    """
    OTLP exporter for telemetry data.
    
    Exports traces, metrics, and logs to OTLP-compatible backends
    (e.g., Jaeger, Prometheus, Grafana Tempo).
    """
    
    def __init__(self, config: Optional[OTLPConfig] = None):
        self.config = config or OTLPConfig()
        self._span_queue: List[Span] = []
        self._metric_queue: List[Metric] = []
        self._log_queue: List[Dict[str, Any]] = []
        self._running = False
        self._export_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
        
        # Stats
        self._spans_exported = 0
        self._metrics_exported = 0
        self._logs_exported = 0
        self._export_errors = 0
    
    async def start(self) -> None:
        """Start the exporter."""
        if self._running:
            return
        
        self._running = True
        self._export_task = asyncio.create_task(self._export_loop())
        
        logger.info(
            "otlp_exporter_started",
            endpoint=self.config.endpoint,
            service_name=self.config.service_name,
        )
    
    async def stop(self) -> None:
        """Stop the exporter and flush remaining data."""
        self._running = False
        
        # Flush remaining data
        await self._flush()
        
        if self._export_task:
            self._export_task.cancel()
            try:
                await self._export_task
            except asyncio.CancelledError:
                pass
        
        logger.info(
            "otlp_exporter_stopped",
            spans_exported=self._spans_exported,
            metrics_exported=self._metrics_exported,
            export_errors=self._export_errors,
        )
    
    async def _export_loop(self) -> None:
        """Main export loop."""
        interval_s = self.config.export_interval_ms / 1000
        
        while self._running:
            try:
                await asyncio.sleep(interval_s)
                await self._flush()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("otlp_export_loop_error", error=str(e))
                self._export_errors += 1
    
    async def _flush(self) -> None:
        """Flush all queued telemetry."""
        async with self._lock:
            # Export spans
            if self._span_queue:
                spans = self._span_queue[:self.config.max_export_batch_size]
                self._span_queue = self._span_queue[self.config.max_export_batch_size:]
                await self._export_spans(spans)
            
            # Export metrics
            if self._metric_queue:
                metrics = self._metric_queue[:self.config.max_export_batch_size]
                self._metric_queue = self._metric_queue[self.config.max_export_batch_size:]
                await self._export_metrics(metrics)
            
            # Export logs
            if self._log_queue:
                logs = self._log_queue[:self.config.max_export_batch_size]
                self._log_queue = self._log_queue[self.config.max_export_batch_size:]
                await self._export_logs(logs)
    
    async def _export_spans(self, spans: List[Span]) -> None:
        """Export spans via OTLP."""
        if not spans:
            return
        
        payload = {
            "resourceSpans": [{
                "resource": {
                    "attributes": [
                        {"key": "service.name", "value": {"stringValue": self.config.service_name}},
                        {"key": "service.version", "value": {"stringValue": self.config.service_version}},
                        {"key": "deployment.environment", "value": {"stringValue": self.config.deployment_environment}},
                    ],
                },
                "scopeSpans": [{
                    "scope": {"name": "riskcast.tracer", "version": "1.0.0"},
                    "spans": [span.to_otlp() for span in spans],
                }],
            }],
        }
        
        success = await self._send_request("/v1/traces", payload)
        if success:
            self._spans_exported += len(spans)
            logger.debug("otlp_spans_exported", count=len(spans))
    
    async def _export_metrics(self, metrics: List[Metric]) -> None:
        """Export metrics via OTLP."""
        if not metrics:
            return
        
        payload = {
            "resourceMetrics": [{
                "resource": {
                    "attributes": [
                        {"key": "service.name", "value": {"stringValue": self.config.service_name}},
                    ],
                },
                "scopeMetrics": [{
                    "scope": {"name": "riskcast.metrics", "version": "1.0.0"},
                    "metrics": [metric.to_otlp() for metric in metrics],
                }],
            }],
        }
        
        success = await self._send_request("/v1/metrics", payload)
        if success:
            self._metrics_exported += len(metrics)
    
    async def _export_logs(self, logs: List[Dict[str, Any]]) -> None:
        """Export logs via OTLP."""
        if not logs:
            return
        
        payload = {
            "resourceLogs": [{
                "resource": {
                    "attributes": [
                        {"key": "service.name", "value": {"stringValue": self.config.service_name}},
                    ],
                },
                "scopeLogs": [{
                    "scope": {"name": "riskcast.logger", "version": "1.0.0"},
                    "logRecords": logs,
                }],
            }],
        }
        
        success = await self._send_request("/v1/logs", payload)
        if success:
            self._logs_exported += len(logs)
    
    async def _send_request(self, path: str, payload: Dict[str, Any]) -> bool:
        """Send request to OTLP endpoint."""
        import json
        
        try:
            import httpx
            
            endpoint = self.config.http_endpoint + path
            headers = {
                "Content-Type": "application/json",
                **self.config.headers,
            }
            
            async with httpx.AsyncClient(timeout=self.config.export_timeout_ms / 1000) as client:
                response = await client.post(
                    endpoint,
                    json=payload,
                    headers=headers,
                )
                
                if response.status_code >= 400:
                    logger.error(
                        "otlp_export_failed",
                        status=response.status_code,
                        path=path,
                    )
                    self._export_errors += 1
                    return False
                
                return True
                
        except ImportError:
            # httpx not available, log and skip
            logger.warning("httpx_not_available_for_otlp")
            return False
        except Exception as e:
            logger.error("otlp_export_error", error=str(e), path=path)
            self._export_errors += 1
            return False
    
    def record_span(self, span: Span) -> None:
        """Record a span for export."""
        if len(self._span_queue) < self.config.max_queue_size:
            self._span_queue.append(span)
    
    def record_metric(self, metric: Metric) -> None:
        """Record a metric for export."""
        if len(self._metric_queue) < self.config.max_queue_size:
            self._metric_queue.append(metric)
    
    def record_log(
        self,
        severity: str,
        body: str,
        attributes: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
        span_id: Optional[str] = None,
    ) -> None:
        """Record a log for export."""
        severity_map = {
            "trace": 1, "debug": 5, "info": 9,
            "warn": 13, "error": 17, "fatal": 21,
        }
        
        log_record = {
            "timeUnixNano": str(time.time_ns()),
            "severityNumber": severity_map.get(severity.lower(), 9),
            "severityText": severity.upper(),
            "body": {"stringValue": body},
            "attributes": [
                {"key": k, "value": {"stringValue": str(v)}}
                for k, v in (attributes or {}).items()
            ],
        }
        
        if trace_id:
            log_record["traceId"] = trace_id
        if span_id:
            log_record["spanId"] = span_id
        
        if len(self._log_queue) < self.config.max_queue_size:
            self._log_queue.append(log_record)
    
    @property
    def stats(self) -> Dict[str, int]:
        """Get export statistics."""
        return {
            "spans_exported": self._spans_exported,
            "metrics_exported": self._metrics_exported,
            "logs_exported": self._logs_exported,
            "export_errors": self._export_errors,
            "span_queue_size": len(self._span_queue),
            "metric_queue_size": len(self._metric_queue),
            "log_queue_size": len(self._log_queue),
        }


class Tracer:
    """
    Tracer for creating and managing spans.
    
    Provides context propagation and automatic span management.
    """
    
    def __init__(
        self,
        exporter: OTLPExporter,
        service_name: str = "riskcast",
    ):
        self._exporter = exporter
        self._service_name = service_name
        self._current_span: Optional[Span] = None
        
        # Context storage (would use contextvars in production)
        self._context_stack: List[Span] = []
    
    def _generate_id(self, length: int = 16) -> str:
        """Generate a random hex ID."""
        import secrets
        return secrets.token_hex(length)
    
    def start_span(
        self,
        name: str,
        kind: str = "internal",
        attributes: Optional[Dict[str, Any]] = None,
        parent: Optional[Span] = None,
    ) -> Span:
        """Start a new span."""
        # Get parent context
        parent_span = parent or (self._context_stack[-1] if self._context_stack else None)
        
        if parent_span:
            trace_id = parent_span.context.trace_id
            parent_span_id = parent_span.context.span_id
        else:
            trace_id = self._generate_id(16)
            parent_span_id = None
        
        span = Span(
            name=name,
            context=SpanContext(
                trace_id=trace_id,
                span_id=self._generate_id(8),
                parent_span_id=parent_span_id,
            ),
            start_time_ns=time.time_ns(),
            kind=kind,
            attributes=attributes or {},
        )
        
        # Add service attribute
        span.set_attribute("service.name", self._service_name)
        
        return span
    
    @asynccontextmanager
    async def span(
        self,
        name: str,
        kind: str = "internal",
        attributes: Optional[Dict[str, Any]] = None,
    ):
        """Context manager for automatic span management."""
        span = self.start_span(name, kind, attributes)
        self._context_stack.append(span)
        
        try:
            yield span
            span.set_status("ok")
        except Exception as e:
            span.set_status("error", str(e))
            span.add_event("exception", {
                "exception.type": type(e).__name__,
                "exception.message": str(e),
            })
            raise
        finally:
            span.end()
            self._context_stack.pop()
            self._exporter.record_span(span)
    
    def trace_function(self, name: Optional[str] = None):
        """Decorator to trace a function."""
        def decorator(func: Callable):
            span_name = name or func.__name__
            
            if asyncio.iscoroutinefunction(func):
                async def async_wrapper(*args, **kwargs):
                    async with self.span(span_name):
                        return await func(*args, **kwargs)
                return async_wrapper
            else:
                def sync_wrapper(*args, **kwargs):
                    span = self.start_span(span_name)
                    try:
                        result = func(*args, **kwargs)
                        span.set_status("ok")
                        return result
                    except Exception as e:
                        span.set_status("error", str(e))
                        raise
                    finally:
                        span.end()
                        self._exporter.record_span(span)
                return sync_wrapper
        
        return decorator
    
    @property
    def current_span(self) -> Optional[Span]:
        """Get the current active span."""
        return self._context_stack[-1] if self._context_stack else None


class MetricsCollector:
    """
    Collector for application metrics.
    
    Provides counters, gauges, and histograms.
    """
    
    def __init__(self, exporter: OTLPExporter):
        self._exporter = exporter
        self._counters: Dict[str, float] = {}
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, List[float]] = {}
    
    def increment(
        self,
        name: str,
        value: float = 1.0,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Increment a counter."""
        key = f"{name}:{hash(frozenset((attributes or {}).items()))}"
        self._counters[key] = self._counters.get(key, 0) + value
        
        metric = Metric(
            name=name,
            metric_type="sum",
        )
        metric.add_data_point(self._counters[key], attributes)
        self._exporter.record_metric(metric)
    
    def gauge(
        self,
        name: str,
        value: float,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Set a gauge value."""
        key = f"{name}:{hash(frozenset((attributes or {}).items()))}"
        self._gauges[key] = value
        
        metric = Metric(
            name=name,
            metric_type="gauge",
        )
        metric.add_data_point(value, attributes)
        self._exporter.record_metric(metric)
    
    def histogram(
        self,
        name: str,
        value: float,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record a histogram value."""
        key = f"{name}:{hash(frozenset((attributes or {}).items()))}"
        if key not in self._histograms:
            self._histograms[key] = []
        self._histograms[key].append(value)
        
        # For simplicity, export as gauge with the latest value
        # In production, would compute actual histogram buckets
        metric = Metric(
            name=name,
            metric_type="gauge",
        )
        metric.add_data_point(value, attributes)
        self._exporter.record_metric(metric)


# Global instances
_exporter: Optional[OTLPExporter] = None
_tracer: Optional[Tracer] = None
_metrics: Optional[MetricsCollector] = None


async def init_telemetry(config: Optional[OTLPConfig] = None) -> Tuple[Tracer, MetricsCollector]:
    """Initialize telemetry system."""
    global _exporter, _tracer, _metrics
    
    config = config or OTLPConfig()
    _exporter = OTLPExporter(config)
    _tracer = Tracer(_exporter, config.service_name)
    _metrics = MetricsCollector(_exporter)
    
    await _exporter.start()
    
    logger.info("telemetry_initialized", service=config.service_name)
    
    return _tracer, _metrics


async def shutdown_telemetry() -> None:
    """Shutdown telemetry system."""
    global _exporter
    
    if _exporter:
        await _exporter.stop()
    
    logger.info("telemetry_shutdown")


def get_tracer() -> Tracer:
    """Get the global tracer."""
    if _tracer is None:
        raise RuntimeError("Telemetry not initialized. Call init_telemetry() first.")
    return _tracer


def get_metrics() -> MetricsCollector:
    """Get the global metrics collector."""
    if _metrics is None:
        raise RuntimeError("Telemetry not initialized. Call init_telemetry() first.")
    return _metrics
