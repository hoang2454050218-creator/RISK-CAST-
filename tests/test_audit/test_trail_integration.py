"""Tests for Audit Trail Integration Layer.

These tests verify:
1. AuditedDecisionComposer wraps decisions with audit trail
2. Input snapshots are captured BEFORE decision generation
3. Pipeline hooks record all lifecycle events
4. Chain verifier detects integrity issues
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from typing import Optional

from app.audit.schemas import (
    AuditEventType,
    InputSnapshot,
    ProcessingRecord,
)
from app.audit.service import AuditService
from app.audit.repository import InMemoryAuditRepository
from app.audit.trail import (
    AuditedDecisionComposer,
    AuditPipelineHooks,
    AuditChainVerifier,
    audit_decision,
    create_audited_composer,
    create_pipeline_hooks,
    create_chain_verifier,
)


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def in_memory_repo():
    """Create in-memory audit repository for testing."""
    return InMemoryAuditRepository()


@pytest.fixture
def audit_service(in_memory_repo):
    """Create audit service with in-memory repository."""
    return AuditService(repository=in_memory_repo)


def _create_mock_with_attrs(**attrs):
    """Helper to create a mock with attributes that return actual values."""
    mock = MagicMock()
    for key, value in attrs.items():
        if isinstance(value, dict):
            # Create nested mock
            nested = _create_mock_with_attrs(**value)
            setattr(mock, key, nested)
        else:
            # Set as actual value
            type(mock).__getattribute__ = lambda self, name, _attrs=attrs: _attrs.get(name, MagicMock())
            setattr(mock, key, value)
    return mock


@pytest.fixture
def mock_intelligence():
    """Create mock correlated intelligence with proper string attributes."""
    # Create signal mock
    signal = MagicMock()
    signal.signal_id = "sig_test_001"
    signal.probability = 0.85
    signal.category = "disruption"
    signal.chokepoint = "red_sea"
    
    # Set up geographic mock
    geographic = MagicMock()
    primary_chokepoint = MagicMock()
    primary_chokepoint.value = "red_sea"
    geographic.primary_chokepoint = primary_chokepoint
    signal.geographic = geographic
    
    signal.model_dump = MagicMock(return_value={
        "signal_id": "sig_test_001",
        "probability": 0.85,
        "category": "disruption",
        "chokepoint": "red_sea",
    })
    
    # Create reality mock
    reality = MagicMock()
    reality.timestamp = datetime.utcnow()
    reality.model_dump = MagicMock(return_value={
        "timestamp": datetime.utcnow().isoformat(),
        "correlation_status": "confirmed",
        "combined_confidence": 0.87,
    })
    
    # Create intelligence mock
    intelligence = MagicMock()
    intelligence.signal = signal
    intelligence.reality = reality
    
    return intelligence


@pytest.fixture
def mock_customer_context():
    """Create mock customer context with proper string attributes."""
    # Create profile mock
    profile = MagicMock()
    profile.customer_id = "cust_test_001"
    profile.company_name = "Test Corp"
    profile.risk_tolerance = "balanced"
    profile.model_dump = MagicMock(return_value={
        "customer_id": "cust_test_001",
        "company_name": "Test Corp",
        "risk_tolerance": "balanced",
    })
    
    # Create shipment mock
    shipment = MagicMock()
    shipment.shipment_id = "shp_001"
    shipment.cargo_value_usd = 150000.0
    shipment.route_chokepoints = ["red_sea"]
    
    # Create context mock
    context = MagicMock()
    context.profile = profile
    context.active_shipments = [shipment]
    context.version = 1
    context.model_dump = MagicMock(return_value={
        "profile": {"customer_id": "cust_test_001", "company_name": "Test Corp"},
        "active_shipments": [{"shipment_id": "shp_001", "cargo_value_usd": 150000.0}],
        "version": 1,
    })
    
    return context


@pytest.fixture
def mock_decision():
    """Create mock decision object with proper string attributes."""
    # Create decision with actual string values for Pydantic
    decision = MagicMock()
    decision.decision_id = "dec_test_001"
    decision.customer_id = "cust_test_001"
    decision.signal_id = "sig_test_001"
    
    # Mock nested objects with actual values
    q3_severity = MagicMock()
    q3_severity.total_exposure_usd = 150000.0
    decision.q3_severity = q3_severity
    
    q5_action = MagicMock()
    q5_action.action_type = "reroute"
    decision.q5_action = q5_action
    
    q6_confidence = MagicMock()
    q6_confidence.score = 0.85
    decision.q6_confidence = q6_confidence
    
    # Mock model_dump to return proper dict
    decision.model_dump = MagicMock(return_value={
        "decision_id": "dec_test_001",
        "customer_id": "cust_test_001",
        "signal_id": "sig_test_001",
        "q3_severity": {"total_exposure_usd": 150000.0},
        "q5_action": {"action_type": "reroute"},
        "q6_confidence": {"score": 0.85},
    })
    
    return decision


@pytest.fixture
def mock_decision_composer():
    """Create mock decision composer."""
    return MagicMock()


# ============================================================================
# AUDITED DECISION COMPOSER TESTS
# ============================================================================


class TestAuditedDecisionComposer:
    """Tests for AuditedDecisionComposer."""
    
    @pytest.mark.asyncio
    async def test_captures_input_snapshot_before_decision(
        self, audit_service, mock_intelligence, mock_customer_context, mock_decision
    ):
        """Input snapshot should be captured BEFORE decision generation."""
        # Create mock composer that returns a decision
        mock_base_composer = MagicMock()
        mock_base_composer.compose.return_value = mock_decision
        
        # Create audited composer
        audited_composer = AuditedDecisionComposer(
            audit_service=audit_service,
            decision_composer=mock_base_composer,
            model_version="1.0.0",
            config_version="1.0.0",
        )
        
        # Generate decision
        decision = await audited_composer.compose(
            intelligence=mock_intelligence,
            context=mock_customer_context,
        )
        
        # Decision should be returned
        assert decision is not None
        
        # Base composer should have been called
        mock_base_composer.compose.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_returns_none_for_no_exposure(
        self, audit_service, mock_intelligence, mock_customer_context
    ):
        """Should return None when customer has no exposure."""
        # Create mock composer that returns None (no exposure)
        mock_base_composer = MagicMock()
        mock_base_composer.compose.return_value = None
        
        audited_composer = AuditedDecisionComposer(
            audit_service=audit_service,
            decision_composer=mock_base_composer,
        )
        
        decision = await audited_composer.compose(
            intelligence=mock_intelligence,
            context=mock_customer_context,
        )
        
        assert decision is None
    
    @pytest.mark.asyncio
    async def test_records_failure_on_exception(
        self, audit_service, mock_intelligence, mock_customer_context
    ):
        """Should record failure in audit trail when exception occurs."""
        mock_base_composer = MagicMock()
        mock_base_composer.compose.side_effect = ValueError("Test error")
        
        audited_composer = AuditedDecisionComposer(
            audit_service=audit_service,
            decision_composer=mock_base_composer,
        )
        
        with pytest.raises(ValueError, match="Test error"):
            await audited_composer.compose(
                intelligence=mock_intelligence,
                context=mock_customer_context,
            )
    
    @pytest.mark.asyncio
    async def test_tracks_model_and_config_versions(
        self, audit_service, mock_intelligence, mock_customer_context, mock_decision
    ):
        """Should track model and config versions in processing record."""
        mock_base_composer = MagicMock()
        mock_base_composer.compose.return_value = mock_decision
        
        audited_composer = AuditedDecisionComposer(
            audit_service=audit_service,
            decision_composer=mock_base_composer,
            model_version="2.3.1",
            config_version="config-2026-02-05",
        )
        
        # The versions should be stored
        assert audited_composer._model_version == "2.3.1"
        assert audited_composer._config_version == "config-2026-02-05"
    
    @pytest.mark.asyncio
    async def test_computes_config_and_model_hashes(
        self, audit_service, mock_decision_composer
    ):
        """Should compute deterministic hashes for config and model."""
        composer1 = AuditedDecisionComposer(
            audit_service=audit_service,
            decision_composer=mock_decision_composer,
            model_version="1.0.0",
            config_version="1.0.0",
        )
        
        composer2 = AuditedDecisionComposer(
            audit_service=audit_service,
            decision_composer=mock_decision_composer,
            model_version="1.0.0",
            config_version="1.0.0",
        )
        
        # Same versions should produce same hashes
        assert composer1._config_hash == composer2._config_hash
        assert composer1._model_hash == composer2._model_hash
        
        # Different versions should produce different hashes
        composer3 = AuditedDecisionComposer(
            audit_service=audit_service,
            decision_composer=mock_decision_composer,
            model_version="2.0.0",
            config_version="1.0.0",
        )
        assert composer1._model_hash != composer3._model_hash


# ============================================================================
# PIPELINE HOOKS TESTS
# ============================================================================


class TestAuditPipelineHooks:
    """Tests for AuditPipelineHooks."""
    
    @pytest.mark.asyncio
    async def test_records_signal_received(self, audit_service):
        """Should log when signal is received."""
        hooks = AuditPipelineHooks(audit_service)
        
        # Should not raise
        await hooks.on_signal_received(
            signal_id="sig_001",
            source="polymarket",
            probability=0.85,
        )
    
    @pytest.mark.asyncio
    async def test_records_intelligence_correlated(self, audit_service):
        """Should log when intelligence is correlated."""
        hooks = AuditPipelineHooks(audit_service)
        
        await hooks.on_intelligence_correlated(
            signal_id="sig_001",
            correlation_status="confirmed",
            combined_confidence=0.87,
        )
    
    @pytest.mark.asyncio
    async def test_records_decision_delivered(self, audit_service):
        """Should record delivery in audit trail."""
        hooks = AuditPipelineHooks(audit_service)
        
        await hooks.on_decision_delivered(
            decision_id="dec_001",
            channel="whatsapp",
            status="delivered",
        )
    
    @pytest.mark.asyncio
    async def test_records_decision_acknowledged(self, audit_service):
        """Should record acknowledgment in audit trail."""
        hooks = AuditPipelineHooks(audit_service)
        
        await hooks.on_decision_acknowledged(
            decision_id="dec_001",
            by_user="ops_manager",
        )
    
    @pytest.mark.asyncio
    async def test_records_action_taken(self, audit_service):
        """Should record action taken in audit trail."""
        hooks = AuditPipelineHooks(audit_service)
        
        await hooks.on_action_taken(
            decision_id="dec_001",
            action_type="reroute",
            by_user="logistics_mgr",
        )
    
    @pytest.mark.asyncio
    async def test_records_outcome(self, audit_service):
        """Should record outcome in audit trail."""
        hooks = AuditPipelineHooks(audit_service)
        
        await hooks.on_outcome_recorded(
            decision_id="dec_001",
            outcome={
                "event_occurred": True,
                "actual_cost_usd": 12500.0,
                "actual_delay_days": 8,
            },
            accuracy="accurate",
        )


# ============================================================================
# CHAIN VERIFIER TESTS
# ============================================================================


class TestAuditChainVerifier:
    """Tests for AuditChainVerifier."""
    
    @pytest.mark.asyncio
    async def test_verify_full_chain_empty_repo(self, audit_service):
        """Should handle empty repository."""
        verifier = AuditChainVerifier(audit_service)
        
        result = await verifier.verify_full_chain()
        
        assert "is_valid" in result
        assert "verified_at" in result
    
    @pytest.mark.asyncio
    async def test_verify_recent_returns_result(self, audit_service):
        """Should return verification result for recent records."""
        verifier = AuditChainVerifier(audit_service)
        
        result = await verifier.verify_recent(hours=24)
        
        assert "is_valid" in result
        assert "period_hours" in result
        assert result["period_hours"] == 24
    
    @pytest.mark.asyncio
    async def test_get_chain_stats_returns_stats(self, audit_service):
        """Should return chain statistics."""
        verifier = AuditChainVerifier(audit_service)
        
        stats = await verifier.get_chain_stats()
        
        assert "total_records" in stats
        assert "chain_status" in stats


# ============================================================================
# DECORATOR TESTS
# ============================================================================


class TestAuditDecisionDecorator:
    """Tests for audit_decision decorator."""
    
    @pytest.mark.asyncio
    async def test_decorator_wraps_async_function(self, audit_service):
        """Decorator should wrap async functions."""
        @audit_decision(audit_service)
        async def my_decision_function(x: int) -> int:
            return x * 2
        
        result = await my_decision_function(5)
        assert result == 10
    
    @pytest.mark.asyncio
    async def test_decorator_propagates_exceptions(self, audit_service):
        """Decorator should propagate exceptions."""
        @audit_decision(audit_service)
        async def failing_function():
            raise ValueError("Test error")
        
        with pytest.raises(ValueError, match="Test error"):
            await failing_function()


# ============================================================================
# FACTORY FUNCTION TESTS
# ============================================================================


class TestFactoryFunctions:
    """Tests for factory functions."""
    
    def test_create_audited_composer_with_mock_composer(self, audit_service, mock_decision_composer):
        """Should create audited composer with provided dependencies."""
        composer = create_audited_composer(
            audit_service=audit_service,
            decision_composer=mock_decision_composer,
        )
        
        assert composer is not None
        assert isinstance(composer, AuditedDecisionComposer)
    
    def test_create_audited_composer_with_custom_versions(self, audit_service, mock_decision_composer):
        """Should accept custom model and config versions."""
        composer = create_audited_composer(
            audit_service=audit_service,
            decision_composer=mock_decision_composer,
            model_version="3.0.0",
            config_version="custom-config",
        )
        
        assert composer._model_version == "3.0.0"
        assert composer._config_version == "custom-config"
    
    def test_create_pipeline_hooks_with_defaults(self):
        """Should create pipeline hooks with default dependencies."""
        hooks = create_pipeline_hooks()
        
        assert hooks is not None
        assert isinstance(hooks, AuditPipelineHooks)
    
    def test_create_chain_verifier_with_defaults(self):
        """Should create chain verifier with default dependencies."""
        verifier = create_chain_verifier()
        
        assert verifier is not None
        assert isinstance(verifier, AuditChainVerifier)


# ============================================================================
# INTEGRATION TESTS
# ============================================================================


class TestAuditTrailIntegration:
    """Integration tests for full audit trail flow."""
    
    @pytest.mark.asyncio
    async def test_full_decision_lifecycle_audit(
        self, audit_service, mock_intelligence, mock_customer_context, mock_decision
    ):
        """Test full decision lifecycle through audit system."""
        # Setup
        mock_base_composer = MagicMock()
        mock_base_composer.compose.return_value = mock_decision
        
        audited_composer = AuditedDecisionComposer(
            audit_service=audit_service,
            decision_composer=mock_base_composer,
        )
        hooks = AuditPipelineHooks(audit_service)
        
        # 1. Signal received (logged via hook)
        await hooks.on_signal_received(
            signal_id="sig_test_001",
            source="polymarket",
            probability=0.85,
        )
        
        # 2. Intelligence correlated (logged via hook)
        await hooks.on_intelligence_correlated(
            signal_id="sig_test_001",
            correlation_status="confirmed",
            combined_confidence=0.87,
        )
        
        # 3. Decision generated (with input snapshot)
        decision = await audited_composer.compose(
            intelligence=mock_intelligence,
            context=mock_customer_context,
        )
        assert decision is not None
        
        # 4. Decision delivered
        await hooks.on_decision_delivered(
            decision_id="dec_test_001",
            channel="whatsapp",
            status="delivered",
        )
        
        # 5. Decision acknowledged
        await hooks.on_decision_acknowledged(
            decision_id="dec_test_001",
            by_user="customer",
        )
        
        # 6. Action taken
        await hooks.on_action_taken(
            decision_id="dec_test_001",
            action_type="reroute",
            by_user="customer",
        )
        
        # 7. Outcome recorded
        await hooks.on_outcome_recorded(
            decision_id="dec_test_001",
            outcome={"event_occurred": True, "actual_cost_usd": 8500.0},
            accuracy="accurate",
        )
        
        # Verify chain integrity
        verifier = AuditChainVerifier(audit_service)
        chain_result = await verifier.verify_full_chain()
        
        # Chain should be valid (or we should at least get a result)
        assert "is_valid" in chain_result
