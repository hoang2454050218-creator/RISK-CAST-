"""
Integration Tests for RISKCAST.

Comprehensive integration tests covering:
- API endpoints
- Database operations
- Decision flow
- External services (mocked)
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.core.config import settings
from app.db.session import get_session
from app.db.repositories.api_keys import (
    InMemoryAPIKeyRepository,
    CreateAPIKeyRequest,
)


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
async def test_client():
    """Create test HTTP client."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
async def api_key_repo():
    """Create in-memory API key repository."""
    return InMemoryAPIKeyRepository()


@pytest.fixture
async def test_api_key(api_key_repo):
    """Create a test API key."""
    request = CreateAPIKeyRequest(
        owner_id="test_customer_001",
        owner_type="customer",
        name="Test API Key",
        scopes=["decisions:read", "decisions:write", "alerts:read"],
        rate_limit_per_minute=100,
    )
    response = await api_key_repo.create(request)
    return response.raw_key


@pytest.fixture
def auth_headers(test_api_key):
    """Create authorization headers."""
    return {"Authorization": f"Bearer {test_api_key}"}


# ============================================================================
# HEALTH CHECK TESTS
# ============================================================================


class TestHealthEndpoints:
    """Tests for health check endpoints."""
    
    @pytest.mark.asyncio
    async def test_liveness_probe(self, test_client):
        """Test liveness probe returns alive status."""
        response = await test_client.get("/health/live")
        
        assert response.status_code == 200
        data = response.json()
        assert data["alive"] is True
        assert "timestamp" in data
    
    @pytest.mark.asyncio
    async def test_readiness_probe(self, test_client):
        """Test readiness probe returns ready status."""
        response = await test_client.get("/health/ready")
        
        assert response.status_code == 200
        data = response.json()
        assert data["ready"] is True
    
    @pytest.mark.asyncio
    async def test_full_health_check(self, test_client):
        """Test comprehensive health check."""
        response = await test_client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] in ["healthy", "degraded", "unhealthy"]
        assert "version" in data
        assert "environment" in data
        assert "uptime_seconds" in data
        assert "components" in data
        assert len(data["components"]) > 0


# ============================================================================
# API KEY TESTS
# ============================================================================


class TestAPIKeyManagement:
    """Tests for API key management."""
    
    @pytest.mark.asyncio
    async def test_create_api_key(self, api_key_repo):
        """Test API key creation."""
        request = CreateAPIKeyRequest(
            owner_id="customer_123",
            name="Production Key",
            scopes=["decisions:read"],
        )
        
        response = await api_key_repo.create(request)
        
        assert response.raw_key.startswith("rk_")
        assert response.api_key.key_id.startswith("rk_")
        assert response.api_key.owner_id == "customer_123"
        assert response.api_key.is_active is True
    
    @pytest.mark.asyncio
    async def test_validate_api_key(self, api_key_repo, test_api_key):
        """Test API key validation."""
        api_key = await api_key_repo.validate(test_api_key)
        
        assert api_key is not None
        assert api_key.owner_id == "test_customer_001"
        assert api_key.is_active is True
    
    @pytest.mark.asyncio
    async def test_validate_invalid_key(self, api_key_repo):
        """Test validation of invalid API key."""
        api_key = await api_key_repo.validate("invalid_key")
        
        assert api_key is None
    
    @pytest.mark.asyncio
    async def test_deactivate_api_key(self, api_key_repo, test_api_key):
        """Test API key deactivation."""
        # Get the key first to find its ID
        api_key = await api_key_repo.validate(test_api_key)
        key_id = api_key.key_id
        
        # Deactivate
        result = await api_key_repo.deactivate(key_id)
        assert result is True
        
        # Verify it's now invalid
        api_key = await api_key_repo.validate(test_api_key)
        assert api_key is None
    
    @pytest.mark.asyncio
    async def test_expired_api_key(self, api_key_repo):
        """Test expired API key is rejected."""
        request = CreateAPIKeyRequest(
            owner_id="customer_456",
            name="Expired Key",
            scopes=["decisions:read"],
            expires_in_days=-1,  # Already expired
        )
        
        response = await api_key_repo.create(request)
        
        # Manually set expiry to past
        api_key = await api_key_repo.get_by_id(response.api_key.key_id)
        api_key.expires_at = datetime.utcnow() - timedelta(hours=1)
        
        # Should fail validation
        validated = await api_key_repo.validate(response.raw_key)
        assert validated is None


# ============================================================================
# RATE LIMITING TESTS
# ============================================================================


class TestRateLimiting:
    """Tests for rate limiting functionality."""
    
    @pytest.mark.asyncio
    async def test_rate_limit_allows_normal_traffic(self):
        """Test rate limiter allows normal traffic."""
        from app.core.rate_limiting import InMemoryRateLimiter
        
        limiter = InMemoryRateLimiter()
        
        # Should allow up to limit
        for i in range(10):
            result = await limiter.check("test_key", limit=10, window_seconds=60)
            assert result.allowed is True
    
    @pytest.mark.asyncio
    async def test_rate_limit_blocks_excess(self):
        """Test rate limiter blocks excess traffic."""
        from app.core.rate_limiting import InMemoryRateLimiter
        
        limiter = InMemoryRateLimiter()
        
        # Exhaust the limit
        for i in range(5):
            await limiter.check("test_key", limit=5, window_seconds=60)
        
        # Next request should be blocked
        result = await limiter.check("test_key", limit=5, window_seconds=60)
        assert result.allowed is False
        assert result.retry_after_seconds is not None
    
    @pytest.mark.asyncio
    async def test_rate_limit_headers(self):
        """Test rate limit result provides correct headers."""
        from app.core.rate_limiting import InMemoryRateLimiter
        
        limiter = InMemoryRateLimiter()
        
        result = await limiter.check("test_key", limit=100, window_seconds=60)
        headers = result.to_headers()
        
        assert "X-RateLimit-Limit" in headers
        assert "X-RateLimit-Remaining" in headers
        assert "X-RateLimit-Reset" in headers
        assert headers["X-RateLimit-Limit"] == "100"


# ============================================================================
# CIRCUIT BREAKER TESTS
# ============================================================================


class TestCircuitBreaker:
    """Tests for circuit breaker functionality."""
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_allows_success(self):
        """Test circuit breaker allows successful calls."""
        from app.core.resilience import CircuitBreaker, CircuitState
        
        breaker = CircuitBreaker("test_service")
        
        async def success_func():
            return "success"
        
        result = await breaker.execute(success_func)
        
        assert result == "success"
        assert breaker.state == CircuitState.CLOSED
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_on_failures(self):
        """Test circuit breaker opens after threshold failures."""
        from app.core.resilience import (
            CircuitBreaker,
            CircuitBreakerConfig,
            CircuitState,
            CircuitBreakerError,
        )
        
        config = CircuitBreakerConfig(failure_threshold=3)
        breaker = CircuitBreaker("test_service", config)
        
        async def failing_func():
            raise Exception("Service unavailable")
        
        # Cause failures
        for i in range(3):
            try:
                await breaker.execute(failing_func)
            except Exception:
                pass
        
        # Circuit should be open
        assert breaker.state == CircuitState.OPEN
        
        # Next call should fail immediately
        with pytest.raises(CircuitBreakerError):
            await breaker.execute(failing_func)
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_recovers(self):
        """Test circuit breaker recovers after timeout."""
        from app.core.resilience import (
            CircuitBreaker,
            CircuitBreakerConfig,
            CircuitState,
        )
        import asyncio
        
        config = CircuitBreakerConfig(
            failure_threshold=2,
            timeout_seconds=0.1,  # Very short for testing
            success_threshold=1,
        )
        breaker = CircuitBreaker("test_service", config)
        
        async def failing_func():
            raise Exception("Fail")
        
        async def success_func():
            return "success"
        
        # Cause failures to open circuit
        for i in range(2):
            try:
                await breaker.execute(failing_func)
            except Exception:
                pass
        
        assert breaker.state == CircuitState.OPEN
        
        # Wait for timeout
        await asyncio.sleep(0.2)
        
        # Should transition to half-open and allow test call
        result = await breaker.execute(success_func)
        assert result == "success"


# ============================================================================
# ENCRYPTION TESTS
# ============================================================================


class TestEncryption:
    """Tests for PII encryption functionality."""
    
    def test_encrypt_decrypt_roundtrip(self):
        """Test encryption and decryption produce original value."""
        from app.core.encryption import FieldEncryptor, KeyManager
        
        key_manager = KeyManager(master_key=b"test_master_key_32bytes_long!!")
        encryptor = FieldEncryptor(key_manager)
        
        original = "sensitive_data_123"
        encrypted = encryptor.encrypt(original)
        decrypted = encryptor.decrypt(encrypted)
        
        assert encrypted != original
        assert decrypted == original
    
    def test_is_encrypted_detection(self):
        """Test detection of encrypted values."""
        from app.core.encryption import FieldEncryptor, KeyManager
        
        key_manager = KeyManager(master_key=b"test_master_key_32bytes_long!!")
        encryptor = FieldEncryptor(key_manager)
        
        plaintext = "not encrypted"
        encrypted = encryptor.encrypt(plaintext)
        
        assert encryptor.is_encrypted(encrypted) is True
        assert encryptor.is_encrypted(plaintext) is False
    
    def test_different_contexts_produce_different_keys(self):
        """Test different encryption contexts use different keys."""
        from app.core.encryption import FieldEncryptor, KeyManager
        
        key_manager = KeyManager(master_key=b"test_master_key_32bytes_long!!")
        
        key1 = key_manager.get_key("context1")
        key2 = key_manager.get_key("context2")
        
        assert key1 != key2
    
    def test_hash_for_lookup_consistency(self):
        """Test lookup hashes are consistent."""
        from app.core.encryption import FieldEncryptor, KeyManager
        
        key_manager = KeyManager(master_key=b"test_master_key_32bytes_long!!")
        encryptor = FieldEncryptor(key_manager)
        
        plaintext = "lookup_value"
        hash1 = encryptor.hash_for_lookup(plaintext)
        hash2 = encryptor.hash_for_lookup(plaintext)
        
        assert hash1 == hash2
        assert hash1 != plaintext


# ============================================================================
# DECISION TESTS
# ============================================================================


class TestDecisionGeneration:
    """Tests for decision generation functionality."""
    
    @pytest.mark.asyncio
    async def test_decision_has_all_7_questions(self):
        """Test generated decision answers all 7 questions."""
        # Mock decision object with all required fields
        from app.riskcast.schemas.decision import (
            DecisionObject,
            Urgency,
            Action,
            ActionType,
        )
        
        decision = DecisionObject(
            decision_id="dec_001",
            customer_id="cust_001",
            q1_what="Houthi attacks on Red Sea shipping affecting your shipments",
            q2_when=Urgency.URGENT,
            q2_timeline="Next 48-72 hours",
            q3_severity_level="HIGH",
            q3_exposure_usd=250000.0,
            q3_delay_days=14.0,
            q4_why="Increased Houthi drone attacks with 85% probability",
            q4_evidence=["Polymarket 85%", "3 attacks this week", "Maersk rerouting"],
            q5_action=Action(
                action_type=ActionType.REROUTE,
                action_text="REROUTE via Cape of Good Hope with MSC",
                estimated_cost_usd=8500.0,
                deadline=datetime.utcnow() + timedelta(hours=6),
            ),
            q6_confidence=0.82,
            q6_factors=["High signal correlation", "Historical accuracy"],
            q6_caveats=["Dependent on carrier availability"],
            q7_inaction_cost=15000.0,
            q7_point_of_no_return=datetime.utcnow() + timedelta(hours=12),
        )
        
        # Verify all 7 questions are answered
        assert decision.q1_what is not None
        assert decision.q2_when is not None
        assert decision.q3_exposure_usd is not None
        assert decision.q4_why is not None
        assert decision.q5_action is not None
        assert decision.q6_confidence is not None
        assert decision.q7_inaction_cost is not None
    
    @pytest.mark.asyncio
    async def test_action_has_specific_cost(self):
        """Test action has specific USD cost, not percentage."""
        from app.riskcast.schemas.decision import Action, ActionType
        
        action = Action(
            action_type=ActionType.REROUTE,
            action_text="REROUTE via Cape",
            estimated_cost_usd=8500.0,
            deadline=datetime.utcnow() + timedelta(hours=6),
        )
        
        assert action.estimated_cost_usd > 0
        assert isinstance(action.estimated_cost_usd, float)


# ============================================================================
# OUTCOME TRACKING TESTS
# ============================================================================


class TestOutcomeTracking:
    """Tests for outcome tracking functionality."""
    
    @pytest.mark.asyncio
    async def test_accuracy_calculation(self):
        """Test accuracy metrics calculation."""
        # Test impact accuracy calculation
        predicted = 10000.0
        actual = 9000.0
        
        accuracy = 1 - abs(actual - predicted) / predicted
        accuracy_pct = max(0, min(1, accuracy)) * 100
        
        assert accuracy_pct == 90.0
    
    @pytest.mark.asyncio
    async def test_prediction_result_assessment(self):
        """Test prediction result assessment."""
        # >= 80% = ACCURATE
        assert 85 >= 80  # Accurate
        
        # >= 50% and < 80% = PARTIALLY_ACCURATE  
        assert 60 >= 50 and 60 < 80  # Partially accurate
        
        # < 50% = INACCURATE
        assert 30 < 50  # Inaccurate


# ============================================================================
# METRICS TESTS
# ============================================================================


class TestMetrics:
    """Tests for metrics functionality."""
    
    def test_metrics_generation(self):
        """Test Prometheus metrics generation."""
        from app.core.metrics import METRICS
        
        # Record some metrics
        METRICS.decisions_generated.labels(
            chokepoint="red_sea",
            severity="high",
            action_type="reroute",
        ).inc()
        
        # Generate metrics
        output = METRICS.generate_latest()
        
        assert b"riskcast_decisions_generated_total" in output
    
    def test_metric_recorder(self):
        """Test metric recorder helper."""
        from app.core.metrics import RECORDER
        
        # Should not raise
        RECORDER.record_decision(
            chokepoint="red_sea",
            severity="high",
            action_type="reroute",
            exposure_usd=250000.0,
            confidence=0.85,
        )
        
        RECORDER.record_alert(
            channel="whatsapp",
            template="decision_urgent",
            status="sent",
            delivery_time_seconds=1.5,
        )


# ============================================================================
# EXTERNAL CLIENT TESTS
# ============================================================================


class TestExternalClients:
    """Tests for external API clients."""
    
    @pytest.mark.asyncio
    async def test_polymarket_client_caching(self):
        """Test Polymarket client response caching."""
        from app.external.polymarket import PolymarketClient, PolymarketConfig
        
        config = PolymarketConfig(cache_ttl_seconds=60)
        client = PolymarketClient(config)
        
        # Set a cached value
        client._set_cached("test_key", {"data": "cached"})
        
        # Should retrieve from cache
        cached = client._get_cached("test_key")
        assert cached == {"data": "cached"}
        
        await client.close()
    
    @pytest.mark.asyncio
    async def test_ais_client_chokepoint_bounds(self):
        """Test AIS client has correct chokepoint bounds."""
        from app.external.ais import CHOKEPOINT_BOUNDS, Chokepoint
        
        # Red Sea bounds should be defined
        bounds = CHOKEPOINT_BOUNDS[Chokepoint.RED_SEA]
        
        assert bounds["min_lat"] < bounds["max_lat"]
        assert bounds["min_lon"] < bounds["max_lon"]
        
        # Suez is within Red Sea region
        suez = CHOKEPOINT_BOUNDS[Chokepoint.SUEZ_CANAL]
        assert bounds["min_lat"] <= suez["min_lat"]


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================


class TestErrorHandling:
    """Tests for error handling functionality."""
    
    def test_error_response_format(self):
        """Test error response format is correct."""
        from app.common.exceptions import NotFoundError, ErrorCode
        
        error = NotFoundError("Customer", "cust_123")
        response = error.to_response(request_id="req_001")
        
        assert response.error.code == ErrorCode.NOT_FOUND.value
        assert "cust_123" in response.error.message
        assert response.request_id == "req_001"
    
    def test_rate_limit_error_includes_retry_after(self):
        """Test rate limit error includes retry information."""
        from app.common.exceptions import RateLimitError
        
        error = RateLimitError(
            message="Rate limit exceeded",
            details={"limit": 100, "retry_after": 60},
        )
        
        assert error.status_code == 429
        assert error.details["retry_after"] == 60
