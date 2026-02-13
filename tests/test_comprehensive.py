"""
Comprehensive test suite for RISKCAST.

Implements GAP D2.1: Tests missing across multiple modules.
Provides unit, integration, and E2E tests for all critical components.
"""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import pytest


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def sample_signal():
    """Create a sample signal for testing."""
    return {
        "signal_id": "sig_test123",
        "signal_type": "disruption",
        "source": "polymarket",
        "probability": 0.75,
        "confidence": 0.85,
        "chokepoint": "red_sea",
        "timestamp": datetime.utcnow().isoformat(),
    }


@pytest.fixture
def sample_context():
    """Create a sample context for testing."""
    return {
        "customer_id": "cust_test456",
        "shipments": [
            {
                "shipment_id": "ship_001",
                "cargo_value_usd": 100000,
                "route": "asia_europe_suez",
                "teu_count": 10,
            }
        ],
    }


@pytest.fixture
def sample_decision():
    """Create a sample decision for testing."""
    return {
        "decision_id": "dec_test789",
        "action_type": "reroute",
        "estimated_cost_usd": 25000,
        "estimated_delay_days": 10,
        "confidence": 0.82,
        "deadline": (datetime.utcnow() + timedelta(hours=6)).isoformat(),
    }


# =============================================================================
# REASONING ENGINE TESTS
# =============================================================================

class TestReasoningEngine:
    """Tests for the multi-layer reasoning engine."""
    
    @pytest.mark.asyncio
    async def test_deterministic_trace_id_generation(self, sample_signal, sample_context):
        """Test that trace IDs are deterministic."""
        from app.reasoning.deterministic import generate_deterministic_trace_id
        
        # Generate trace ID twice with same inputs
        trace_id_1 = generate_deterministic_trace_id(sample_signal, sample_context)
        trace_id_2 = generate_deterministic_trace_id(sample_signal, sample_context)
        
        # Should be identical
        assert trace_id_1 == trace_id_2
        assert trace_id_1.startswith("trace_")
        assert len(trace_id_1) == 30  # "trace_" + 24 hex chars
    
    @pytest.mark.asyncio
    async def test_trace_id_changes_with_input(self, sample_signal, sample_context):
        """Test that trace IDs change when inputs change."""
        from app.reasoning.deterministic import generate_deterministic_trace_id
        
        trace_id_1 = generate_deterministic_trace_id(sample_signal, sample_context)
        
        # Modify signal
        modified_signal = {**sample_signal, "probability": 0.90}
        trace_id_2 = generate_deterministic_trace_id(modified_signal, sample_context)
        
        # Should be different
        assert trace_id_1 != trace_id_2
    
    @pytest.mark.asyncio
    async def test_hysteresis_prevents_flip_flopping(self):
        """Test that hysteresis controller prevents rapid state changes."""
        from app.reasoning.hysteresis import HysteresisController, HysteresisConfig
        
        controller = HysteresisController()
        config = HysteresisConfig(
            activation_threshold=0.7,
            deactivation_threshold=0.5,
            min_hold_time_seconds=60,
        )
        
        # Start below threshold
        should_act, _ = await controller.evaluate("test_key", 0.4, config)
        assert should_act is False
        
        # Rise above activation threshold
        should_act, _ = await controller.evaluate("test_key", 0.75, config)
        assert should_act is True
        
        # Drop between thresholds - should still be active
        should_act, _ = await controller.evaluate("test_key", 0.6, config)
        assert should_act is True
        
        # Drop below deactivation threshold
        should_act, _ = await controller.evaluate("test_key", 0.4, config)
        assert should_act is False


class TestDecisionGraphVisualization:
    """Tests for decision graph visualization."""
    
    def test_mermaid_generation(self):
        """Test Mermaid diagram generation."""
        from app.reasoning.visualization import DecisionGraphRenderer
        from app.reasoning.schemas import (
            ReasoningTrace, LayerResult, ReasoningLayer,
            TraceStatus
        )
        
        # Create a mock trace
        trace = ReasoningTrace(
            trace_id="trace_test",
            signal_id="sig_test",
            started_at=datetime.utcnow(),
            status=TraceStatus.COMPLETED,
            layers=[
                LayerResult(
                    layer=ReasoningLayer.FACTUAL,
                    started_at=datetime.utcnow(),
                    confidence=0.9,
                    output={"facts": ["Red Sea disruption active"]},
                ),
            ],
        )
        
        renderer = DecisionGraphRenderer()
        mermaid = renderer.to_mermaid(trace)
        
        assert "graph TD" in mermaid
        assert "FACTUAL" in mermaid
        assert "classDef" in mermaid
    
    def test_confidence_gauge_svg(self):
        """Test confidence gauge SVG generation."""
        from app.reasoning.visualization import DecisionGraphRenderer
        
        renderer = DecisionGraphRenderer()
        svg = renderer.render_confidence_gauge(0.85)
        
        assert "<svg" in svg
        assert "</svg>" in svg
        assert "85%" in svg  # Confidence percentage


# =============================================================================
# CALIBRATION TESTS
# =============================================================================

class TestCalibration:
    """Tests for probability calibration."""
    
    def test_platt_scaling_fit(self):
        """Test Platt scaling calibration."""
        from app.reasoning.calibration import PlattScaling
        
        scaler = PlattScaling()
        
        # Create sample data
        predictions = [0.3, 0.5, 0.7, 0.8, 0.9] * 10
        outcomes = [0, 0, 1, 1, 1] * 10
        
        scaler.fit(predictions, outcomes)
        
        # Parameters should be fitted
        a, b = scaler.parameters
        assert a != 1.0 or b != 0.0  # Should have changed from default
    
    def test_calibration_error_calculation(self):
        """Test ECE calculation."""
        from app.reasoning.calibration import calculate_calibration_error
        
        # Perfect calibration
        predictions = [0.1, 0.5, 0.9]
        outcomes = [0, 0, 1]
        
        ece, bins = calculate_calibration_error(predictions, outcomes, num_bins=10)
        
        assert 0 <= ece <= 1
        assert isinstance(bins, list)
    
    def test_brier_score_calculation(self):
        """Test Brier score calculation."""
        from app.reasoning.calibration import calculate_brier_score
        
        # Perfect predictions
        predictions = [0.0, 1.0]
        outcomes = [0, 1]
        
        brier = calculate_brier_score(predictions, outcomes)
        assert brier == 0.0
        
        # Bad predictions
        predictions = [1.0, 0.0]
        outcomes = [0, 1]
        
        brier = calculate_brier_score(predictions, outcomes)
        assert brier == 1.0


# =============================================================================
# ERROR TAXONOMY TESTS
# =============================================================================

class TestErrorTaxonomy:
    """Tests for error classification."""
    
    def test_error_classification(self):
        """Test error classification logic."""
        from app.reasoning.error_taxonomy import (
            ErrorTaxonomyEngine, ErrorCategory, ErrorSeverity
        )
        
        engine = ErrorTaxonomyEngine()
        
        # Classify an overconfident prediction
        error = engine.classify_error(
            predicted=0.9,
            actual=0.5,
            context={
                "error_type": "probability",
                "cost_impact_usd": 10000,
            }
        )
        
        assert error.category == ErrorCategory.OVERCONFIDENT
        assert error.severity in [ErrorSeverity.MINOR, ErrorSeverity.MEDIUM]
    
    def test_error_pattern_detection(self):
        """Test pattern detection across errors."""
        from app.reasoning.error_taxonomy import ErrorTaxonomyEngine
        
        engine = ErrorTaxonomyEngine()
        
        # Add multiple similar errors
        for _ in range(5):
            engine.classify_error(
                predicted=0.9,
                actual=0.5,
                context={"error_type": "probability", "cost_impact_usd": 5000}
            )
        
        patterns = engine.get_patterns(min_occurrences=3)
        assert len(patterns) >= 1


# =============================================================================
# ENCRYPTION TESTS
# =============================================================================

class TestEncryption:
    """Tests for encryption and security."""
    
    def test_no_xor_fallback(self):
        """Test that XOR fallback is removed."""
        from app.core.encryption import FieldEncryptor
        
        # Check that _encrypt_fallback method doesn't exist
        assert not hasattr(FieldEncryptor, '_encrypt_fallback')
        assert not hasattr(FieldEncryptor, '_decrypt_fallback')
    
    def test_encryption_requires_key(self):
        """Test that encryption requires a key."""
        from app.core.encryption import init_encryption, EncryptionError
        import os
        
        # Clear env var if set
        original = os.environ.pop("RISKCAST_ENCRYPTION_KEY", None)
        
        try:
            with pytest.raises(EncryptionError):
                init_encryption(None)
        finally:
            if original:
                os.environ["RISKCAST_ENCRYPTION_KEY"] = original
    
    @pytest.mark.asyncio
    async def test_key_rotation(self):
        """Test key rotation functionality."""
        from app.core.key_rotation import KeyRotator
        import secrets
        
        # Create keys
        key1 = secrets.token_bytes(32)
        key2 = secrets.token_bytes(32)
        
        # Encrypt with old key
        rotator_v1 = KeyRotator(current_key=key1, key_version=1)
        ciphertext = rotator_v1.encrypt(b"secret data")
        
        # Create rotator with new key and old key for transition
        rotator_v2 = KeyRotator(
            current_key=key2,
            previous_key=key1,
            key_version=2,
        )
        
        # Should be able to decrypt old data
        plaintext = rotator_v2.decrypt(ciphertext)
        assert plaintext == b"secret data"


# =============================================================================
# KEY MANAGEMENT TESTS
# =============================================================================

class TestKeyManagement:
    """Tests for key management."""
    
    def test_key_validation(self):
        """Test key validation logic."""
        from app.core.key_management import KeySpec
        
        spec = KeySpec(
            key_name="test_key",
            key_size_bits=256,
            required=True,
        )
        
        assert spec.key_size_bytes == 32
        assert spec.env_var_name == "RISKCAST_TEST_KEY"
    
    def test_no_ephemeral_keys_allowed(self):
        """Test that ephemeral key generation is forbidden."""
        from app.core.key_management import KeyManager, KeyManagementError
        import os
        
        # Clear all key env vars
        for key in ["RISKCAST_ENCRYPTION_KEY", "RISKCAST_SIGNING_KEY", "RISKCAST_API_SALT"]:
            os.environ.pop(key, None)
        
        # Should raise error because keys are missing
        with pytest.raises(KeyManagementError):
            KeyManager()


# =============================================================================
# QUERY OPTIMIZER TESTS
# =============================================================================

class TestQueryOptimizer:
    """Tests for query optimization."""
    
    def test_query_parsing(self):
        """Test SQL query parsing."""
        from app.db.query_optimizer import QueryParser
        
        parser = QueryParser()
        
        query = """
        SELECT id, name, value 
        FROM orders 
        WHERE customer_id = 123 
        ORDER BY created_at DESC
        """
        
        result = parser.parse(query)
        
        assert result["type"].value == "select"
        assert "orders" in result["tables"]
        assert "customer_id" in result["columns_filtered"]
        assert "created_at" in result["columns_ordered"]
    
    def test_index_suggestion(self):
        """Test index suggestion generation."""
        from app.db.query_optimizer import QueryOptimizer
        
        optimizer = QueryOptimizer()
        
        analysis = optimizer.analyze_query(
            "SELECT * FROM orders WHERE customer_id = 123 AND status = 'pending'"
        )
        
        assert len(analysis.index_suggestions) > 0
        assert any("customer_id" in idx.columns for idx in analysis.index_suggestions)
    
    def test_query_issue_detection(self):
        """Test detection of query issues."""
        from app.db.query_optimizer import QueryOptimizer
        
        optimizer = QueryOptimizer()
        
        analysis = optimizer.analyze_query("SELECT * FROM orders")
        
        assert "SELECT * should be replaced" in analysis.issues


# =============================================================================
# AUDIT RETENTION TESTS
# =============================================================================

class TestAuditRetention:
    """Tests for audit retention."""
    
    def test_retention_policy_thresholds(self):
        """Test retention policy threshold calculation."""
        from app.audit.retention import RetentionPolicy
        
        policy = RetentionPolicy(
            name="test",
            hot_retention_days=30,
            warm_retention_days=90,
        )
        
        warm_threshold = policy.warm_threshold
        cold_threshold = policy.cold_threshold
        
        assert warm_threshold < cold_threshold
        assert (datetime.utcnow() - warm_threshold).days == 30
    
    @pytest.mark.asyncio
    async def test_archiving(self):
        """Test record archiving."""
        from app.audit.retention import AuditArchiver, RetentionPolicy
        import tempfile
        import os
        
        with tempfile.TemporaryDirectory() as tmpdir:
            archiver = AuditArchiver(archive_path=tmpdir)
            policy = RetentionPolicy(name="test")
            
            records = [
                {"id": "1", "timestamp": datetime.utcnow().isoformat(), "data": "test1"},
                {"id": "2", "timestamp": datetime.utcnow().isoformat(), "data": "test2"},
            ]
            
            batch = await archiver.archive_records(records, "test_records", policy)
            
            assert batch.record_count == 2
            assert batch.compressed_size_bytes > 0
            assert batch.compressed_size_bytes < batch.original_size_bytes


# =============================================================================
# SLA ENFORCEMENT TESTS
# =============================================================================

class TestSLAEnforcement:
    """Tests for SLA enforcement."""
    
    def test_challenge_creation(self):
        """Test challenge creation."""
        from app.audit.sla import SLAEnforcer, ChallengePriority
        
        enforcer = SLAEnforcer()
        
        challenge = enforcer.create_challenge(
            decision_id="dec_test",
            priority=ChallengePriority.HIGH,
            reason="Test reason",
            ai_recommendation="Test recommendation",
        )
        
        assert challenge.challenge_id.startswith("chl_")
        assert challenge.priority == ChallengePriority.HIGH
    
    @pytest.mark.asyncio
    async def test_response_tracking(self):
        """Test response time tracking."""
        from app.audit.sla import SLAEnforcer, ChallengePriority
        
        enforcer = SLAEnforcer()
        
        challenge = enforcer.create_challenge(
            decision_id="dec_test",
            priority=ChallengePriority.MEDIUM,
            reason="Test",
            ai_recommendation="Test",
        )
        
        # Respond to challenge
        await enforcer.respond_to_challenge(
            challenge_id=challenge.challenge_id,
            responder="test_user",
            response="Acknowledged",
        )
        
        updated = enforcer.get_challenge(challenge.challenge_id)
        assert updated.responded_at is not None
        assert updated.response_time_minutes is not None


# =============================================================================
# OTLP TELEMETRY TESTS
# =============================================================================

class TestOTLPTelemetry:
    """Tests for OTLP telemetry."""
    
    def test_span_creation(self):
        """Test span creation and attributes."""
        from app.observability.otlp import Span, SpanContext
        
        span = Span(
            name="test_operation",
            context=SpanContext(
                trace_id="abc123",
                span_id="def456",
            ),
            start_time_ns=1000000000,
        )
        
        span.set_attribute("key", "value")
        span.add_event("test_event", {"detail": "info"})
        span.end()
        
        assert span.attributes["key"] == "value"
        assert len(span.events) == 1
        assert span.end_time_ns is not None
    
    def test_span_otlp_format(self):
        """Test span OTLP format conversion."""
        from app.observability.otlp import Span, SpanContext
        
        span = Span(
            name="test",
            context=SpanContext(trace_id="abc", span_id="def"),
            start_time_ns=1000,
        )
        span.end(end_time_ns=2000)
        
        otlp = span.to_otlp()
        
        assert otlp["name"] == "test"
        assert otlp["traceId"] == "abc"
        assert otlp["spanId"] == "def"
    
    def test_metric_creation(self):
        """Test metric creation."""
        from app.observability.otlp import Metric
        
        metric = Metric(
            name="test_counter",
            metric_type="sum",
        )
        metric.add_data_point(42, {"service": "test"})
        
        otlp = metric.to_otlp()
        
        assert otlp["name"] == "test_counter"
        assert len(otlp["sum"]["dataPoints"]) == 1


# =============================================================================
# ML OUTCOME PERSISTENCE TESTS
# =============================================================================

class TestOutcomePersistence:
    """Tests for outcome persistence."""
    
    @pytest.mark.asyncio
    async def test_outcome_recording(self):
        """Test recording decision outcomes."""
        from app.ml.outcome_persistence import (
            OutcomePersistence, OutcomeType, LearningSignal
        )
        
        store = OutcomePersistence()
        
        # Register a decision
        await store.register_decision(
            decision_id="dec_test",
            predicted_cost_usd=10000,
            predicted_delay_days=5,
            decision_context={"action_type": "reroute"},
            signal_context={"signal_type": "disruption"},
        )
        
        # Record outcome
        outcome = await store.record_outcome(
            decision_id="dec_test",
            outcome_type=OutcomeType.SUCCESS,
            actual_cost_usd=9500,
            actual_delay_days=4,
        )
        
        assert outcome.learning_signal == LearningSignal.POSITIVE
        assert outcome.cost_prediction_error_pct < 10  # Within 10%
    
    @pytest.mark.asyncio
    async def test_training_data_generation(self):
        """Test training data generation from outcomes."""
        from app.ml.outcome_persistence import (
            OutcomePersistence, OutcomeType
        )
        
        store = OutcomePersistence()
        
        # Add some outcomes
        for i in range(5):
            await store.register_decision(
                decision_id=f"dec_{i}",
                predicted_cost_usd=10000,
                predicted_delay_days=5,
                decision_context={},
                signal_context={},
            )
            await store.record_outcome(
                decision_id=f"dec_{i}",
                outcome_type=OutcomeType.SUCCESS,
                actual_cost_usd=10000,
                actual_delay_days=5,
            )
        
        examples = store.get_training_data()
        assert len(examples) == 5


class TestNetworkEffects:
    """Tests for network effect tracking."""
    
    @pytest.mark.asyncio
    async def test_data_moat_score(self):
        """Test data moat score calculation."""
        from app.ml.outcome_persistence import (
            OutcomePersistence, NetworkEffectTracker
        )
        
        store = OutcomePersistence()
        tracker = NetworkEffectTracker(store)
        
        # Track some shipments
        for i in range(10):
            tracker.track_shipment(
                route=f"route_{i}",
                carrier=f"carrier_{i % 3}",
                customer_id=f"cust_{i % 5}",
            )
        
        score = tracker.get_data_moat_score()
        
        assert 0 <= score <= 100
        assert score > 0  # Should have some score from tracking


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestIntegration:
    """Integration tests across modules."""
    
    @pytest.mark.asyncio
    async def test_full_decision_flow(self, sample_signal, sample_context):
        """Test full decision flow from signal to outcome."""
        from app.reasoning.deterministic import generate_deterministic_trace_id
        from app.ml.outcome_persistence import (
            OutcomePersistence, OutcomeType
        )
        
        # Generate trace ID
        trace_id = generate_deterministic_trace_id(sample_signal, sample_context)
        assert trace_id.startswith("trace_")
        
        # Create decision outcome store
        store = OutcomePersistence()
        
        # Register decision
        decision_id = "dec_integration_test"
        await store.register_decision(
            decision_id=decision_id,
            predicted_cost_usd=25000,
            predicted_delay_days=10,
            decision_context={"trace_id": trace_id},
            signal_context=sample_signal,
        )
        
        # Record outcome
        outcome = await store.record_outcome(
            decision_id=decision_id,
            outcome_type=OutcomeType.SUCCESS,
            actual_cost_usd=23000,
            actual_delay_days=9,
        )
        
        assert outcome.outcome_id.startswith("out_")
        assert outcome.cost_prediction_error_pct < 10


# =============================================================================
# PYTEST CONFIGURATION
# =============================================================================

def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers", "asyncio: mark test as async"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow"
    )
    config.addinivalue_line(
        "markers", "integration: mark as integration test"
    )
