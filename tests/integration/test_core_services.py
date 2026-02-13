"""
Integration Tests for RISKCAST Core Services.

Tests the integration between:
- Cache
- Circuit breakers
- Encryption
- Event bus
- Tracing
"""

import asyncio
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import structlog

logger = structlog.get_logger(__name__)


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def initialized_core():
    """Initialize core services for testing."""
    from app.core import init_core_services, close_core_services
    
    # Use in-memory/mock services for testing
    with patch("app.core.cache.settings") as mock_settings:
        mock_settings.redis_url = None  # Force fallback
        
        # Initialize with test config
        await init_core_services(
            redis_url=None,
            encryption_key=None,
            use_redis_events=False,
            service_name="riskcast-test",
        )
        
        yield
        
        await close_core_services()


# ============================================================================
# CACHE TESTS
# ============================================================================


class TestCacheIntegration:
    """Test cache functionality."""
    
    @pytest.mark.asyncio
    async def test_cache_set_get(self, initialized_core):
        """Test basic set and get operations."""
        from app.core import get_cache
        
        cache = get_cache()
        
        # Set value
        result = await cache.set("test_key", "test_value", ttl=60)
        assert result is True
        
        # Get value
        value = await cache.get("test_key")
        assert value == "test_value"
    
    @pytest.mark.asyncio
    async def test_cache_json(self, initialized_core):
        """Test JSON serialization."""
        from app.core import get_cache
        
        cache = get_cache()
        
        test_data = {"name": "test", "value": 42, "nested": {"key": "value"}}
        
        await cache.set_json("json_key", test_data, ttl=60)
        result = await cache.get_json("json_key")
        
        assert result == test_data
    
    @pytest.mark.asyncio
    async def test_cache_delete(self, initialized_core):
        """Test delete operations."""
        from app.core import get_cache
        
        cache = get_cache()
        
        await cache.set("delete_key", "value")
        assert await cache.exists("delete_key")
        
        await cache.delete("delete_key")
        assert not await cache.exists("delete_key")


# ============================================================================
# RATE LIMITER TESTS
# ============================================================================


class TestRateLimiterIntegration:
    """Test rate limiter functionality."""
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self, initialized_core):
        """Test rate limiting allows and blocks requests."""
        from app.core import get_rate_limiter
        
        limiter = get_rate_limiter()
        
        # First requests should be allowed
        for i in range(5):
            allowed, remaining, reset_in = await limiter.is_allowed(
                "test_client",
                limit=5,
                window_seconds=60,
            )
            if i < 5:
                assert allowed or remaining == 0
    
    @pytest.mark.asyncio
    async def test_rate_limit_different_keys(self, initialized_core):
        """Different keys have separate limits."""
        from app.core import get_rate_limiter
        
        limiter = get_rate_limiter()
        
        # Client A
        allowed_a, _, _ = await limiter.is_allowed("client_a", limit=1, window_seconds=60)
        
        # Client B should still be allowed
        allowed_b, _, _ = await limiter.is_allowed("client_b", limit=1, window_seconds=60)
        
        assert allowed_a and allowed_b


# ============================================================================
# CIRCUIT BREAKER TESTS
# ============================================================================


class TestCircuitBreakerIntegration:
    """Test circuit breaker functionality."""
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_normal_operation(self, initialized_core):
        """Circuit breaker allows calls in normal state."""
        from app.core import get_circuit_breaker
        
        breaker = get_circuit_breaker("test_service")
        
        async def successful_call():
            return "success"
        
        result = await breaker.call(successful_call)
        assert result == "success"
        assert breaker.state.value == "closed"
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_on_failures(self, initialized_core):
        """Circuit breaker opens after threshold failures."""
        from app.core import get_circuit_breaker, CircuitConfig
        
        config = CircuitConfig(
            failure_threshold=3,
            failure_window_seconds=60,
            recovery_timeout_seconds=5,
        )
        
        breaker = get_circuit_breaker("failing_service", config)
        breaker.reset()  # Start fresh
        
        async def failing_call():
            raise Exception("Service error")
        
        # Make failing calls
        for _ in range(3):
            try:
                await breaker.call(failing_call)
            except Exception:
                pass
        
        assert breaker.state.value == "open"
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_recovery(self, initialized_core):
        """Circuit breaker recovers after timeout."""
        from app.core import get_circuit_breaker, CircuitConfig
        
        config = CircuitConfig(
            failure_threshold=2,
            recovery_timeout_seconds=1,
            success_threshold=1,
        )
        
        breaker = get_circuit_breaker("recovery_service", config)
        breaker.reset()
        
        async def toggle_call():
            if breaker.stats.consecutive_failures >= 2:
                return "recovered"
            raise Exception("Fail")
        
        # Cause failures
        for _ in range(2):
            try:
                await breaker.call(toggle_call)
            except:
                pass
        
        assert breaker.state.value == "open"
        
        # Wait for recovery timeout
        await asyncio.sleep(1.5)
        
        # Should transition to half-open and then closed
        async def success_call():
            return "success"
        
        result = await breaker.call(success_call)
        assert result == "success"


# ============================================================================
# ENCRYPTION TESTS
# ============================================================================


class TestEncryptionIntegration:
    """Test encryption functionality."""
    
    @pytest.mark.asyncio
    async def test_field_encryption(self, initialized_core):
        """Test field-level encryption."""
        from app.core import get_encryptor
        
        encryptor = get_encryptor()
        
        plaintext = "sensitive data 12345"
        
        encrypted = encryptor.encrypt_string(plaintext, context="test")
        assert encrypted != plaintext
        
        decrypted = encryptor.decrypt_string(encrypted, context="test")
        assert decrypted == plaintext
    
    @pytest.mark.asyncio
    async def test_password_hashing(self, initialized_core):
        """Test password hashing and verification."""
        from app.core import get_hasher
        
        hasher = get_hasher()
        
        password = "SecureP@ssw0rd!"
        
        hashed = hasher.hash_password(password)
        assert hashed != password
        
        # Correct password
        assert hasher.verify_password(password, hashed)
        
        # Wrong password
        assert not hasher.verify_password("wrong_password", hashed)
    
    @pytest.mark.asyncio
    async def test_api_key_generation(self, initialized_core):
        """Test API key generation and hashing."""
        from app.core import get_hasher
        
        hasher = get_hasher()
        
        full_key, key_hash = hasher.generate_api_key(prefix="test")
        
        assert full_key.startswith("test_")
        assert len(key_hash) == 64  # SHA-256 hex
        
        # Verify hash
        assert hasher.hash_api_key(full_key) == key_hash
    
    @pytest.mark.asyncio
    async def test_pii_masking(self, initialized_core):
        """Test PII masking functions."""
        from app.core import get_pii_protector
        
        protector = get_pii_protector()
        
        # Email masking
        masked_email = protector.mask_email("john.doe@example.com")
        assert "@" in masked_email
        assert "john.doe" not in masked_email
        
        # Phone masking
        masked_phone = protector.mask_phone("+1-555-123-4567")
        assert masked_phone.endswith("4567")
        assert "555" not in masked_phone
        
        # Name masking
        masked_name = protector.mask_name("John Doe")
        assert masked_name.startswith("J")


# ============================================================================
# EVENT BUS TESTS
# ============================================================================


class TestEventBusIntegration:
    """Test event bus functionality."""
    
    @pytest.mark.asyncio
    async def test_event_publish_subscribe(self, initialized_core):
        """Test event publishing and subscribing."""
        from app.core import get_event_bus, Event, EventType
        
        bus = get_event_bus()
        await bus.start()
        
        received_events = []
        
        async def handler(event: Event):
            received_events.append(event)
        
        # Subscribe
        handler_id = bus.subscribe(
            handler,
            [EventType.SIGNAL_DETECTED],
        )
        
        # Publish
        event = Event(
            event_type=EventType.SIGNAL_DETECTED,
            payload={"signal_id": "test-123"},
        )
        await bus.publish(event)
        
        # Wait for processing
        await asyncio.sleep(0.1)
        
        assert len(received_events) == 1
        assert received_events[0].payload["signal_id"] == "test-123"
        
        # Cleanup
        bus.unsubscribe(handler_id)
    
    @pytest.mark.asyncio
    async def test_event_multiple_subscribers(self, initialized_core):
        """Test multiple subscribers receive same event."""
        from app.core import get_event_bus, Event, EventType
        
        bus = get_event_bus()
        await bus.start()
        
        handler1_count = [0]
        handler2_count = [0]
        
        async def handler1(event: Event):
            handler1_count[0] += 1
        
        async def handler2(event: Event):
            handler2_count[0] += 1
        
        h1_id = bus.subscribe(handler1, [EventType.DECISION_GENERATED])
        h2_id = bus.subscribe(handler2, [EventType.DECISION_GENERATED])
        
        event = Event(
            event_type=EventType.DECISION_GENERATED,
            payload={"decision_id": "dec-123"},
        )
        await bus.publish(event)
        
        await asyncio.sleep(0.1)
        
        assert handler1_count[0] == 1
        assert handler2_count[0] == 1
        
        bus.unsubscribe(h1_id)
        bus.unsubscribe(h2_id)


# ============================================================================
# TRACING TESTS
# ============================================================================


class TestTracingIntegration:
    """Test tracing functionality."""
    
    @pytest.mark.asyncio
    async def test_span_creation(self, initialized_core):
        """Test span creation and attributes."""
        from app.core import get_tracer, get_current_span
        
        tracer = get_tracer()
        
        async with tracer.start_span("test_operation") as span:
            span.set_attribute("test_key", "test_value")
            span.add_event("test_event", {"detail": "info"})
            
            current = get_current_span()
            assert current is not None
            assert current.name == "test_operation"
        
        # Span should be finished
        assert span.end_time is not None
        assert span.status.value == "ok"
    
    @pytest.mark.asyncio
    async def test_nested_spans(self, initialized_core):
        """Test nested span context."""
        from app.core import get_tracer
        
        tracer = get_tracer()
        
        async with tracer.start_span("parent") as parent_span:
            parent_trace_id = parent_span.context.trace_id
            
            async with tracer.start_span("child") as child_span:
                # Same trace
                assert child_span.context.trace_id == parent_trace_id
                # Parent reference
                assert child_span.context.parent_span_id == parent_span.context.span_id
    
    @pytest.mark.asyncio
    async def test_span_error_recording(self, initialized_core):
        """Test error recording on spans."""
        from app.core import get_tracer, SpanStatus
        
        tracer = get_tracer()
        
        try:
            async with tracer.start_span("error_operation") as span:
                raise ValueError("Test error")
        except ValueError:
            pass
        
        assert span.status == SpanStatus.ERROR
        assert span.error is not None
        assert "Test error" in span.error


# ============================================================================
# METRICS TESTS
# ============================================================================


class TestMetricsIntegration:
    """Test metrics collection."""
    
    @pytest.mark.asyncio
    async def test_counter_metrics(self, initialized_core):
        """Test counter metric collection."""
        from app.core import get_metrics
        
        metrics = get_metrics()
        
        metrics.increment("test_requests", tags={"endpoint": "/api"})
        metrics.increment("test_requests", tags={"endpoint": "/api"})
        
        collected = metrics.get_metrics("test_requests")
        assert len(collected) == 2
    
    @pytest.mark.asyncio
    async def test_timer_context_manager(self, initialized_core):
        """Test timer context manager."""
        from app.core import get_metrics
        
        metrics = get_metrics()
        
        with metrics.timer("test_operation"):
            await asyncio.sleep(0.1)
        
        collected = metrics.get_metrics("test_operation_duration_ms")
        assert len(collected) == 1
        assert collected[0].value >= 100  # At least 100ms


# ============================================================================
# HEALTH CHECK TESTS
# ============================================================================


class TestHealthCheck:
    """Test health check functionality."""
    
    @pytest.mark.asyncio
    async def test_core_health(self, initialized_core):
        """Test core health check returns status."""
        from app.core import get_core_health
        
        health = await get_core_health()
        
        assert "status" in health
        assert "components" in health
        assert health["status"] in ["healthy", "degraded", "unhealthy"]
        
        # Check component presence
        assert "cache" in health["components"]
        assert "circuit_breakers" in health["components"]
        assert "encryption" in health["components"]
        assert "event_bus" in health["components"]


# ============================================================================
# END-TO-END FLOW TESTS
# ============================================================================


class TestEndToEndFlow:
    """Test complete flows through multiple services."""
    
    @pytest.mark.asyncio
    async def test_signal_to_decision_flow(self, initialized_core):
        """Test flow from signal detection to decision generation."""
        from app.core import (
            get_event_bus,
            get_cache,
            get_tracer,
            Event,
            EventType,
        )
        
        bus = get_event_bus()
        cache = get_cache()
        tracer = get_tracer()
        
        await bus.start()
        
        decisions_generated = []
        
        async def decision_handler(event: Event):
            # Simulate decision generation
            async with tracer.start_span("generate_decision") as span:
                span.set_attribute("signal_id", event.payload.get("signal_id"))
                
                # Cache the decision
                decision = {
                    "decision_id": "dec-123",
                    "signal_id": event.payload.get("signal_id"),
                    "action": "reroute",
                }
                
                await cache.set_json(
                    f"decision:{decision['decision_id']}",
                    decision,
                    ttl=3600,
                )
                
                decisions_generated.append(decision)
        
        bus.subscribe(decision_handler, [EventType.SIGNAL_DETECTED])
        
        # Simulate signal detection
        async with tracer.start_span("detect_signal") as span:
            signal_event = Event(
                event_type=EventType.SIGNAL_DETECTED,
                payload={
                    "signal_id": "sig-456",
                    "probability": 0.75,
                    "chokepoint": "red_sea",
                },
            )
            await bus.publish(signal_event)
        
        await asyncio.sleep(0.2)
        
        # Verify flow completed
        assert len(decisions_generated) == 1
        
        # Verify decision was cached
        cached_decision = await cache.get_json("decision:dec-123")
        assert cached_decision is not None
        assert cached_decision["signal_id"] == "sig-456"
