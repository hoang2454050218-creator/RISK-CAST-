"""Tests for Decision Composer with ReasoningEngine Integration.

Tests the DecisionComposer's new async compose_decision method that
integrates the 6-layer ReasoningEngine (A1 Cognitive Excellence).

This addresses audit gap A1:
- 6-layer reasoning pipeline integration
- Reasoning trace linkage in decisions
- Escalation handling
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.oracle.schemas import CorrelatedIntelligence
from app.riskcast.composers.decision import (
    DecisionComposer,
    create_decision_composer,
    create_decision_composer_with_reasoning,
)
from app.riskcast.schemas.customer import CustomerContext
from app.riskcast.schemas.decision import DecisionObject


# =============================================================================
# MOCK FIXTURES
# =============================================================================


@pytest.fixture
def mock_reasoning_engine():
    """Create mock ReasoningEngine."""
    engine = AsyncMock()
    
    # Create mock reasoning trace
    mock_trace = MagicMock()
    mock_trace.trace_id = "trace_test_001"
    mock_trace.escalated = False
    mock_trace.escalation_reason = None
    mock_trace.total_duration_ms = 150
    mock_trace.reasoning_quality_score = 0.85
    mock_trace.data_quality_score = 0.90
    mock_trace.final_decision = "reroute"
    mock_trace.final_confidence = 0.82
    
    # Mock layer outputs
    mock_factual = MagicMock()
    mock_factual.confidence = 0.88
    mock_factual.data_quality_score = 0.90
    mock_factual.validated_facts = {
        "affected_shipments": ["PO-4521"],
        "exposure_usd": 150000,
    }
    
    mock_temporal = MagicMock()
    mock_temporal.confidence = 0.85
    mock_temporal.insights = {
        "decision_window_hours": 24,
        "key_dates": ["2024-02-10"],
    }
    
    mock_causal = MagicMock()
    mock_causal.confidence = 0.82
    mock_causal.causal_chain = [
        "Houthi attacks detected",
        "Carriers avoiding Red Sea",
        "Extended transit times",
    ]
    
    mock_counterfactual = MagicMock()
    mock_counterfactual.confidence = 0.80
    
    mock_strategic = MagicMock()
    mock_strategic.confidence = 0.83
    
    mock_meta = MagicMock()
    mock_meta.should_decide = True
    mock_meta.reasoning_confidence = 0.82
    mock_meta.if_decide = {"action": "reroute"}
    mock_meta.escalation_reason = None
    
    mock_trace.factual = mock_factual
    mock_trace.temporal = mock_temporal
    mock_trace.causal = mock_causal
    mock_trace.counterfactual = mock_counterfactual
    mock_trace.strategic = mock_strategic
    mock_trace.meta = mock_meta
    
    engine.reason = AsyncMock(return_value=mock_trace)
    
    return engine


@pytest.fixture
def mock_escalated_reasoning_engine():
    """Create mock ReasoningEngine that escalates."""
    engine = AsyncMock()
    
    mock_trace = MagicMock()
    mock_trace.trace_id = "trace_escalated_001"
    mock_trace.escalated = True
    mock_trace.escalation_reason = "Insufficient data confidence for autonomous decision"
    mock_trace.total_duration_ms = 120
    mock_trace.reasoning_quality_score = 0.45
    mock_trace.data_quality_score = 0.50
    
    # Mock layer outputs (partial execution)
    mock_factual = MagicMock()
    mock_factual.confidence = 0.45
    mock_factual.data_quality_score = 0.50
    
    mock_meta = MagicMock()
    mock_meta.should_decide = False
    mock_meta.reasoning_confidence = 0.45
    mock_meta.escalation_reason = "Insufficient data confidence for autonomous decision"
    
    mock_trace.factual = mock_factual
    mock_trace.meta = mock_meta
    
    engine.reason = AsyncMock(return_value=mock_trace)
    
    return engine


@pytest.fixture
def mock_audit_service():
    """Create mock AuditService."""
    service = AsyncMock()
    service.capture_inputs = AsyncMock()
    service.record_escalation = AsyncMock()
    service.record_decision = AsyncMock()
    return service


@pytest.fixture
def mock_calibrator():
    """Create mock PersistentCalibrator."""
    calibrator = AsyncMock()
    
    # Return a CalibrationResult
    mock_result = MagicMock()
    mock_result.raw_confidence = 0.80
    mock_result.calibrated_confidence = 0.78  # Slight adjustment
    mock_result.adjustment = -0.02
    mock_result.was_adjusted = True
    
    calibrator.calibrate_and_persist = AsyncMock(return_value=mock_result)
    calibrator.record_prediction = AsyncMock()
    
    return calibrator


# =============================================================================
# FACTORY TESTS
# =============================================================================


class TestDecisionComposerFactory:
    """Tests for factory functions."""

    def test_create_decision_composer_without_reasoning(self):
        """Factory should create instance without reasoning."""
        composer = create_decision_composer()
        
        assert isinstance(composer, DecisionComposer)
        assert composer._reasoning_enabled is False

    def test_create_decision_composer_with_reasoning(self, mock_reasoning_engine):
        """Factory should create instance with reasoning enabled."""
        composer = create_decision_composer_with_reasoning(
            reasoning_engine=mock_reasoning_engine,
        )
        
        assert isinstance(composer, DecisionComposer)
        assert composer._reasoning_enabled is True

    def test_create_with_all_dependencies(
        self,
        mock_reasoning_engine,
        mock_audit_service,
        mock_calibrator,
    ):
        """Factory should accept all dependencies."""
        composer = create_decision_composer_with_reasoning(
            reasoning_engine=mock_reasoning_engine,
            audit_service=mock_audit_service,
            calibrator=mock_calibrator,
        )
        
        assert composer._reasoning is mock_reasoning_engine
        assert composer._audit is mock_audit_service
        assert composer._calibrator is mock_calibrator


# =============================================================================
# COMPOSE_DECISION ASYNC METHOD TESTS
# =============================================================================


class TestComposeDecisionAsync:
    """Tests for async compose_decision method."""

    @pytest.mark.asyncio
    async def test_compose_decision_with_reasoning(
        self,
        mock_reasoning_engine,
        confirmed_intelligence: CorrelatedIntelligence,
        sample_customer_context: CustomerContext,
    ):
        """compose_decision should produce valid DecisionObject with reasoning."""
        composer = create_decision_composer_with_reasoning(
            reasoning_engine=mock_reasoning_engine,
        )
        
        decision = await composer.compose_decision(
            confirmed_intelligence,
            sample_customer_context,
        )
        
        assert decision is not None
        assert isinstance(decision, DecisionObject)
        
        # Should have reasoning linkage
        assert decision.reasoning_trace_id == "trace_test_001"
        assert decision.reasoning_quality_score == 0.85
        assert decision.data_quality_score == 0.90

    @pytest.mark.asyncio
    async def test_compose_decision_calls_reasoning_engine(
        self,
        mock_reasoning_engine,
        confirmed_intelligence: CorrelatedIntelligence,
        sample_customer_context: CustomerContext,
    ):
        """compose_decision should call reasoning engine."""
        composer = create_decision_composer_with_reasoning(
            reasoning_engine=mock_reasoning_engine,
        )
        
        await composer.compose_decision(confirmed_intelligence, sample_customer_context)
        
        mock_reasoning_engine.reason.assert_called_once()

    @pytest.mark.asyncio
    async def test_compose_decision_escalation(
        self,
        mock_escalated_reasoning_engine,
        confirmed_intelligence: CorrelatedIntelligence,
        sample_customer_context: CustomerContext,
    ):
        """compose_decision should return None on escalation."""
        composer = create_decision_composer_with_reasoning(
            reasoning_engine=mock_escalated_reasoning_engine,
        )
        
        decision = await composer.compose_decision(
            confirmed_intelligence,
            sample_customer_context,
        )
        
        # Should return None when META layer escalates
        assert decision is None

    @pytest.mark.asyncio
    async def test_compose_decision_audit_captured(
        self,
        mock_reasoning_engine,
        mock_audit_service,
        confirmed_intelligence: CorrelatedIntelligence,
        sample_customer_context: CustomerContext,
    ):
        """compose_decision should capture audit inputs."""
        composer = create_decision_composer_with_reasoning(
            reasoning_engine=mock_reasoning_engine,
            audit_service=mock_audit_service,
        )
        
        await composer.compose_decision(confirmed_intelligence, sample_customer_context)
        
        # Should capture inputs
        mock_audit_service.capture_inputs.assert_called_once()
        # Should record decision
        mock_audit_service.record_decision.assert_called_once()

    @pytest.mark.asyncio
    async def test_compose_decision_escalation_recorded(
        self,
        mock_escalated_reasoning_engine,
        mock_audit_service,
        confirmed_intelligence: CorrelatedIntelligence,
        sample_customer_context: CustomerContext,
    ):
        """compose_decision should record escalation in audit."""
        composer = create_decision_composer_with_reasoning(
            reasoning_engine=mock_escalated_reasoning_engine,
            audit_service=mock_audit_service,
        )
        
        await composer.compose_decision(confirmed_intelligence, sample_customer_context)
        
        # Should record escalation
        mock_audit_service.record_escalation.assert_called_once()

    @pytest.mark.asyncio
    async def test_compose_decision_calibration(
        self,
        mock_reasoning_engine,
        mock_calibrator,
        confirmed_intelligence: CorrelatedIntelligence,
        sample_customer_context: CustomerContext,
    ):
        """compose_decision should use calibrator."""
        composer = create_decision_composer_with_reasoning(
            reasoning_engine=mock_reasoning_engine,
            calibrator=mock_calibrator,
        )
        
        decision = await composer.compose_decision(
            confirmed_intelligence,
            sample_customer_context,
        )
        
        # Should call calibrator
        mock_calibrator.calibrate_and_persist.assert_called_once()
        
        # Decision confidence should reflect calibration
        assert decision is not None
        # Q6 should have calibration info
        assert "calibrated" in decision.q6_confidence.factors

    @pytest.mark.asyncio
    async def test_compose_decision_fallback_without_reasoning(
        self,
        confirmed_intelligence: CorrelatedIntelligence,
        sample_customer_context: CustomerContext,
    ):
        """compose_decision should fallback to sync compose without reasoning engine."""
        # Create composer without reasoning engine
        composer = create_decision_composer()
        
        decision = await composer.compose_decision(
            confirmed_intelligence,
            sample_customer_context,
        )
        
        # Should still produce a decision (via fallback)
        assert decision is not None
        assert isinstance(decision, DecisionObject)
        
        # But won't have reasoning linkage
        assert not hasattr(decision, 'reasoning_trace_id') or decision.reasoning_trace_id is None


# =============================================================================
# REASONING QUALITY INTEGRATION TESTS
# =============================================================================


class TestReasoningQualityIntegration:
    """Tests for reasoning quality metrics in decisions."""

    @pytest.mark.asyncio
    async def test_q6_includes_reasoning_quality(
        self,
        mock_reasoning_engine,
        confirmed_intelligence: CorrelatedIntelligence,
        sample_customer_context: CustomerContext,
    ):
        """Q6 confidence should include reasoning quality metrics."""
        composer = create_decision_composer_with_reasoning(
            reasoning_engine=mock_reasoning_engine,
        )
        
        decision = await composer.compose_decision(
            confirmed_intelligence,
            sample_customer_context,
        )
        
        assert decision is not None
        q6 = decision.q6_confidence
        
        # Should have reasoning quality factors
        assert "reasoning_quality" in q6.factors
        assert "data_quality" in q6.factors
        assert "layer_confidences" in q6.factors

    @pytest.mark.asyncio
    async def test_q6_layer_confidences(
        self,
        mock_reasoning_engine,
        confirmed_intelligence: CorrelatedIntelligence,
        sample_customer_context: CustomerContext,
    ):
        """Q6 should include individual layer confidences."""
        composer = create_decision_composer_with_reasoning(
            reasoning_engine=mock_reasoning_engine,
        )
        
        decision = await composer.compose_decision(
            confirmed_intelligence,
            sample_customer_context,
        )
        
        assert decision is not None
        layer_confidences = decision.q6_confidence.factors.get("layer_confidences", {})
        
        # Should have all 6 layers
        assert "factual" in layer_confidences
        assert "temporal" in layer_confidences
        assert "causal" in layer_confidences


# =============================================================================
# Q4 CAUSAL ENHANCEMENT TESTS
# =============================================================================


class TestQ4CausalEnhancement:
    """Tests for Q4 causal chain from reasoning."""

    @pytest.mark.asyncio
    async def test_q4_uses_reasoning_causal_chain(
        self,
        mock_reasoning_engine,
        confirmed_intelligence: CorrelatedIntelligence,
        sample_customer_context: CustomerContext,
    ):
        """Q4 should use causal chain from reasoning layer."""
        composer = create_decision_composer_with_reasoning(
            reasoning_engine=mock_reasoning_engine,
        )
        
        decision = await composer.compose_decision(
            confirmed_intelligence,
            sample_customer_context,
        )
        
        assert decision is not None
        q4 = decision.q4_why
        
        # Should have causal chain from reasoning
        assert len(q4.causal_chain) >= 1
        # Should include the causal chain from mock
        assert "Houthi attacks detected" in q4.causal_chain or "carriers" in str(q4.causal_chain).lower()


# =============================================================================
# Q2 TEMPORAL ENHANCEMENT TESTS
# =============================================================================


class TestQ2TemporalEnhancement:
    """Tests for Q2 temporal insights from reasoning."""

    @pytest.mark.asyncio
    async def test_q2_uses_temporal_insights(
        self,
        mock_reasoning_engine,
        confirmed_intelligence: CorrelatedIntelligence,
        sample_customer_context: CustomerContext,
    ):
        """Q2 should use temporal insights from reasoning layer."""
        composer = create_decision_composer_with_reasoning(
            reasoning_engine=mock_reasoning_engine,
        )
        
        decision = await composer.compose_decision(
            confirmed_intelligence,
            sample_customer_context,
        )
        
        assert decision is not None
        q2 = decision.q2_when
        
        # Should have urgency set
        assert q2.urgency is not None
        assert q2.urgency_reason is not None


# =============================================================================
# CALIBRATION UPDATE TESTS
# =============================================================================


class TestCalibrationUpdate:
    """Tests for calibration updates in Q6."""

    @pytest.mark.asyncio
    async def test_q6_calibration_adjustment(
        self,
        mock_reasoning_engine,
        mock_calibrator,
        confirmed_intelligence: CorrelatedIntelligence,
        sample_customer_context: CustomerContext,
    ):
        """Q6 should reflect calibration adjustments."""
        composer = create_decision_composer_with_reasoning(
            reasoning_engine=mock_reasoning_engine,
            calibrator=mock_calibrator,
        )
        
        decision = await composer.compose_decision(
            confirmed_intelligence,
            sample_customer_context,
        )
        
        assert decision is not None
        q6 = decision.q6_confidence
        
        # Should have calibration adjustment recorded
        assert q6.factors.get("calibrated") is True
        assert "calibration_adjustment" in q6.factors

    @pytest.mark.asyncio
    async def test_prediction_recorded_for_calibration(
        self,
        mock_reasoning_engine,
        mock_calibrator,
        confirmed_intelligence: CorrelatedIntelligence,
        sample_customer_context: CustomerContext,
    ):
        """Prediction should be recorded for future calibration."""
        composer = create_decision_composer_with_reasoning(
            reasoning_engine=mock_reasoning_engine,
            calibrator=mock_calibrator,
        )
        
        await composer.compose_decision(
            confirmed_intelligence,
            sample_customer_context,
        )
        
        # Should record prediction
        mock_calibrator.record_prediction.assert_called_once()
