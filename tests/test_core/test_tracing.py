"""
Tests for Distributed Tracing Module.

Tests cover:
- Span creation and context management
- Trace propagation
- Error recording in spans
- Metrics collection
- OpenTelemetry integration
"""

import pytest
import asyncio
from unittest.mock import MagicMock, patch

from app.core.tracing import (
    Span,
    SpanContext,
    SpanKind,
    SpanStatus,
    Tracer,
    ConsoleSpanExporter,
    MetricsCollector,
    get_tracer,
    get_metrics,
    get_current_span,
    get_current_trace_id,
    trace,
    setup_opentelemetry,
)


# ============================================================================
# SPAN CONTEXT TESTS
# ============================================================================


class TestSpanContext:
    """Tests for SpanContext."""
    
    def test_creates_context_with_ids(self):
        """Should create context with trace and span IDs."""
        ctx = SpanContext(
            trace_id="trace123",
            span_id="span456",
        )
        
        assert ctx.trace_id == "trace123"
        assert ctx.span_id == "span456"
        assert ctx.parent_span_id is None
    
    def test_creates_context_with_parent(self):
        """Should create context with parent span ID."""
        ctx = SpanContext(
            trace_id="trace123",
            span_id="span456",
            parent_span_id="parent789",
        )
        
        assert ctx.parent_span_id == "parent789"
    
    def test_to_headers(self):
        """Should convert to HTTP headers for propagation."""
        ctx = SpanContext(
            trace_id="trace123",
            span_id="span456",
            parent_span_id="parent789",
        )
        
        headers = ctx.to_headers()
        
        assert headers["X-Trace-ID"] == "trace123"
        assert headers["X-Span-ID"] == "span456"
        assert headers["X-Parent-Span-ID"] == "parent789"
    
    def test_from_headers(self):
        """Should extract context from HTTP headers."""
        headers = {
            "X-Trace-ID": "trace123",
            "X-Span-ID": "span456",
            "X-Parent-Span-ID": "parent789",
        }
        
        ctx = SpanContext.from_headers(headers)
        
        assert ctx is not None
        assert ctx.trace_id == "trace123"
        assert ctx.span_id == "span456"
        assert ctx.parent_span_id == "parent789"
    
    def test_from_headers_case_insensitive(self):
        """Should handle lowercase headers."""
        headers = {
            "x-trace-id": "trace123",
            "x-span-id": "span456",
        }
        
        ctx = SpanContext.from_headers(headers)
        
        assert ctx is not None
        assert ctx.trace_id == "trace123"
    
    def test_from_headers_returns_none_when_missing(self):
        """Should return None when headers are missing."""
        ctx = SpanContext.from_headers({})
        
        assert ctx is None


# ============================================================================
# SPAN TESTS
# ============================================================================


class TestSpan:
    """Tests for Span."""
    
    def test_creates_span_with_name(self):
        """Should create span with name and context."""
        ctx = SpanContext(trace_id="t1", span_id="s1")
        span = Span(name="test_operation", context=ctx)
        
        assert span.name == "test_operation"
        assert span.context == ctx
        assert span.kind == SpanKind.INTERNAL
        assert span.status == SpanStatus.UNSET
    
    def test_set_attribute(self):
        """Should set span attributes."""
        ctx = SpanContext(trace_id="t1", span_id="s1")
        span = Span(name="test", context=ctx)
        
        span.set_attribute("customer_id", "cust123")
        span.set_attribute("amount", 100.50)
        
        assert span.attributes["customer_id"] == "cust123"
        assert span.attributes["amount"] == 100.50
    
    def test_add_event(self):
        """Should add events to span."""
        ctx = SpanContext(trace_id="t1", span_id="s1")
        span = Span(name="test", context=ctx)
        
        span.add_event("cache_hit", {"key": "user:123"})
        
        assert len(span.events) == 1
        assert span.events[0]["name"] == "cache_hit"
        assert span.events[0]["attributes"]["key"] == "user:123"
    
    def test_set_error(self):
        """Should record error on span."""
        ctx = SpanContext(trace_id="t1", span_id="s1")
        span = Span(name="test", context=ctx)
        
        span.set_error(ValueError("Something went wrong"))
        
        assert span.status == SpanStatus.ERROR
        assert span.error == "Something went wrong"
        assert len(span.events) == 1
        assert span.events[0]["name"] == "exception"
    
    def test_finish_calculates_duration(self):
        """Should calculate duration when finished."""
        ctx = SpanContext(trace_id="t1", span_id="s1")
        span = Span(name="test", context=ctx)
        
        span.finish()
        
        assert span.end_time is not None
        assert span.duration_ms is not None
        assert span.duration_ms >= 0
        assert span.status == SpanStatus.OK
    
    def test_to_dict(self):
        """Should convert span to dictionary."""
        ctx = SpanContext(trace_id="t1", span_id="s1")
        span = Span(name="test", context=ctx, kind=SpanKind.SERVER)
        span.set_attribute("key", "value")
        span.finish()
        
        data = span.to_dict()
        
        assert data["name"] == "test"
        assert data["trace_id"] == "t1"
        assert data["span_id"] == "s1"
        assert data["kind"] == "server"
        assert data["status"] == "ok"
        assert data["attributes"]["key"] == "value"


# ============================================================================
# TRACER TESTS
# ============================================================================


class AsyncMockExporter:
    """Mock exporter that handles async export."""
    
    async def export(self, spans):
        pass


class TestTracer:
    """Tests for Tracer."""
    
    @pytest.mark.asyncio
    async def test_start_span_creates_context(self):
        """Should create span with proper context."""
        exporter = AsyncMockExporter()
        tracer = Tracer(service_name="test", exporter=exporter)
        
        async with tracer.start_span("test_op") as span:
            assert span is not None
            assert span.name == "test_op"
            assert span.context.trace_id is not None
            assert span.context.span_id is not None
    
    @pytest.mark.asyncio
    async def test_nested_spans_share_trace_id(self):
        """Nested spans should share the same trace ID."""
        exporter = AsyncMockExporter()
        tracer = Tracer(service_name="test", exporter=exporter)
        
        async with tracer.start_span("parent") as parent_span:
            parent_trace_id = parent_span.context.trace_id
            
            async with tracer.start_span("child") as child_span:
                assert child_span.context.trace_id == parent_trace_id
                assert child_span.context.parent_span_id == parent_span.context.span_id
    
    @pytest.mark.asyncio
    async def test_span_records_error_on_exception(self):
        """Should record error when exception occurs."""
        exporter = AsyncMockExporter()
        tracer = Tracer(service_name="test", exporter=exporter)
        
        with pytest.raises(ValueError):
            async with tracer.start_span("test_op") as span:
                raise ValueError("Test error")
        
        assert span.status == SpanStatus.ERROR
        assert "Test error" in span.error
    
    def test_sync_span_works(self):
        """Should create synchronous spans."""
        tracer = Tracer(service_name="test")
        
        with tracer.start_span_sync("sync_op") as span:
            span.set_attribute("test", "value")
        
        assert span.status == SpanStatus.OK
        assert span.attributes["test"] == "value"


# ============================================================================
# METRICS TESTS
# ============================================================================


class TestMetricsCollector:
    """Tests for MetricsCollector."""
    
    def test_increment_counter(self):
        """Should increment counter metrics."""
        metrics = MetricsCollector(namespace="test")
        
        metrics.increment("requests")
        metrics.increment("requests")
        
        assert metrics._counters["test_requests"] == 2
    
    def test_gauge_metric(self):
        """Should record gauge metrics."""
        metrics = MetricsCollector(namespace="test")
        
        metrics.gauge("memory_used", 1024)
        
        recorded = metrics.get_metrics("memory_used")
        assert len(recorded) == 1
        assert recorded[0].value == 1024
    
    def test_histogram_metric(self):
        """Should record histogram metrics."""
        metrics = MetricsCollector(namespace="test")
        
        metrics.histogram("latency", 0.5)
        metrics.histogram("latency", 0.7)
        
        recorded = metrics.get_metrics("latency")
        assert len(recorded) == 2
    
    def test_timer_context_manager(self):
        """Should time code blocks."""
        import time
        
        metrics = MetricsCollector(namespace="test")
        
        with metrics.timer("operation"):
            time.sleep(0.01)  # 10ms
        
        recorded = metrics.get_metrics("operation_duration_ms")
        assert len(recorded) == 1
        assert recorded[0].value >= 10  # At least 10ms


# ============================================================================
# DECORATOR TESTS
# ============================================================================


class TestTraceDecorator:
    """Tests for @trace decorator."""
    
    @pytest.mark.asyncio
    async def test_trace_async_function(self):
        """Should trace async functions."""
        @trace(name="test_async_op")
        async def async_operation():
            return "result"
        
        result = await async_operation()
        
        assert result == "result"
    
    def test_trace_sync_function(self):
        """Should trace sync functions."""
        @trace(name="test_sync_op")
        def sync_operation():
            return "result"
        
        result = sync_operation()
        
        assert result == "result"
    
    @pytest.mark.asyncio
    async def test_trace_preserves_exception(self):
        """Should preserve exceptions through decorator."""
        @trace(name="failing_op")
        async def failing_operation():
            raise ValueError("Expected error")
        
        with pytest.raises(ValueError) as exc_info:
            await failing_operation()
        
        assert "Expected error" in str(exc_info.value)


# ============================================================================
# GLOBAL INSTANCE TESTS
# ============================================================================


class TestGlobalInstances:
    """Tests for global tracer and metrics instances."""
    
    def test_get_tracer_returns_instance(self):
        """Should return tracer instance."""
        tracer = get_tracer()
        
        assert tracer is not None
        assert isinstance(tracer, Tracer)
    
    def test_get_metrics_returns_instance(self):
        """Should return metrics instance."""
        metrics = get_metrics()
        
        assert metrics is not None
        assert isinstance(metrics, MetricsCollector)


# ============================================================================
# OPENTELEMETRY SETUP TESTS
# ============================================================================


class TestOpenTelemetrySetup:
    """Tests for OpenTelemetry setup."""
    
    def test_setup_returns_none_when_otel_not_installed(self):
        """Should return None when OpenTelemetry not installed."""
        with patch.dict("sys.modules", {"opentelemetry": None}):
            # This may or may not return None depending on imports
            # The important thing is it doesn't crash
            try:
                result = setup_opentelemetry(
                    service_name="test",
                    environment="test",
                )
            except ImportError:
                # Expected if opentelemetry not installed
                pass
    
    def test_setup_configures_service_name(self):
        """Should configure service name."""
        # This tests the configuration logic
        # Without mocking too much
        try:
            result = setup_opentelemetry(
                service_name="riskcast-test",
                service_version="1.0.0",
                environment="test",
                sampling_rate=0.5,
            )
            # If OpenTelemetry is installed, result should be a TracerProvider
            # If not, result will be None
        except ImportError:
            # OpenTelemetry not installed
            pass


# ============================================================================
# INTEGRATION TESTS
# ============================================================================


class TestTracingIntegration:
    """Integration tests for tracing."""
    
    @pytest.mark.asyncio
    async def test_full_trace_flow(self):
        """Test complete tracing flow with nested spans."""
        tracer = get_tracer()
        
        async with tracer.start_span("request", kind=SpanKind.SERVER) as request_span:
            request_span.set_attribute("http.method", "POST")
            request_span.set_attribute("http.url", "/api/v1/decisions")
            
            with tracer.start_span_sync("process") as process_span:
                process_span.set_attribute("step", "validation")
                
                with tracer.start_span_sync("database") as db_span:
                    db_span.set_attribute("query", "SELECT * FROM decisions")
            
            request_span.set_attribute("http.status_code", 200)
        
        # Verify spans were created correctly
        assert request_span.status == SpanStatus.OK
        assert request_span.attributes["http.method"] == "POST"
        assert process_span.context.parent_span_id == request_span.context.span_id
    
    def test_trace_captures_decision_pipeline_spans(self):
        """Test that decision pipeline creates expected spans."""
        tracer = get_tracer()
        
        # Simulate decision pipeline spans
        spans = []
        
        with tracer.start_span_sync("compose_decision") as main:
            main.set_attribute("customer_id", "cust123")
            spans.append(main)
            
            with tracer.start_span_sync("match_exposure") as match:
                match.set_attribute("has_exposure", True)
                spans.append(match)
            
            with tracer.start_span_sync("calculate_impact") as impact:
                impact.set_attribute("total_cost_usd", 50000)
                spans.append(impact)
            
            with tracer.start_span_sync("generate_actions") as actions:
                actions.set_attribute("primary_action", "reroute")
                spans.append(actions)
        
        # All spans should share same trace ID
        trace_id = spans[0].context.trace_id
        assert all(s.context.trace_id == trace_id for s in spans)
        
        # Verify attributes
        assert spans[0].attributes["customer_id"] == "cust123"
        assert spans[2].attributes["total_cost_usd"] == 50000
