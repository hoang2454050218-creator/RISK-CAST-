"""
Tests for the 6-Layer Reasoning Engine.

Tests cover:
- All 6 layers execute in sequence
- Each layer produces typed output
- Meta layer correctly decides to escalate when quality low
- Reasoning trace is complete and inspectable
- Layer execution time is tracked
- Warnings propagate through layers
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, AsyncMock
import pytest

from app.reasoning.schemas import (
    ReasoningLayer,
    ReasoningTrace,
    FactualLayerOutput,
    TemporalLayerOutput,
    CausalLayerOutput,
    CounterfactualLayerOutput,
    StrategicLayerOutput,
    MetaLayerOutput,
    VerifiedFact,
    TimelineEvent,
    CausalLink,
    Scenario,
)
from app.reasoning.engine import ReasoningEngine, create_reasoning_engine
from app.reasoning.layers import (
    FactualLayer,
    TemporalLayer,
    CausalLayer,
    CounterfactualLayer,
    StrategicLayer,
    MetaLayer,
)


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def mock_signal():
    """Create mock OmenSignal."""
    signal = MagicMock()
    signal.signal_id = "sig_test_123"
    signal.event_type = "red_sea_disruption"
    signal.chokepoint = "red_sea"
    signal.probability = 0.75
    signal.probability_source = "polymarket"
    signal.confidence_score = 0.80
    signal.evidence = [
        MagicMock(claim="Houthi attacks increasing"),
        MagicMock(claim="Carriers announcing diversions"),
    ]
    signal.created_at = datetime.utcnow() - timedelta(hours=2)
    signal.prediction_date = datetime.utcnow() + timedelta(days=3)
    return signal


@pytest.fixture
def mock_reality():
    """Create mock RealitySnapshot."""
    reality = MagicMock()
    reality.staleness_seconds = 300  # 5 minutes
    reality.chokepoint_health = {
        "red_sea": MagicMock(
            status="disrupted",
            vessels_rerouting=45,
        ),
    }
    reality.rates_impact = MagicMock(increase_percent=35)
    return reality


@pytest.fixture
def mock_context():
    """Create mock CustomerContext."""
    context = MagicMock()
    context.profile = MagicMock(
        customer_id="cust_test_456",
        risk_tolerance="moderate",
        requires_manual_review=False,
        account_manager="manager_123",
        has_sla=True,
    )
    context.active_shipments = [
        MagicMock(
            shipment_id="ship_001",
            cargo_value_usd=150000,
            route_chokepoints=["red_sea"],
            etd=datetime.utcnow() + timedelta(days=5),
            eta=datetime.utcnow() + timedelta(days=15),
            delivery_deadline=datetime.utcnow() + timedelta(days=20),
            current_location="Shanghai",
        ),
        MagicMock(
            shipment_id="ship_002",
            cargo_value_usd=85000,
            route_chokepoints=["red_sea"],
            etd=datetime.utcnow() + timedelta(days=7),
            eta=datetime.utcnow() + timedelta(days=18),
            delivery_deadline=datetime.utcnow() + timedelta(days=25),
            current_location="Ningbo",
        ),
    ]
    return context


@pytest.fixture
def reasoning_engine():
    """Create reasoning engine with default layers."""
    return ReasoningEngine()


# ============================================================================
# LAYER EXECUTION TESTS
# ============================================================================


class TestLayerExecution:
    """Tests for individual layer execution."""
    
    @pytest.mark.asyncio
    async def test_factual_layer_produces_typed_output(
        self, mock_signal, mock_reality, mock_context
    ):
        """Factual layer must produce FactualLayerOutput."""
        layer = FactualLayer()
        
        output = await layer.execute({
            "signal": mock_signal,
            "reality": mock_reality,
            "context": mock_context,
        })
        
        assert isinstance(output, FactualLayerOutput)
        assert output.layer == ReasoningLayer.FACTUAL
        assert output.confidence > 0
        assert len(output.verified_facts) > 0
        assert output.data_quality_score > 0
    
    @pytest.mark.asyncio
    async def test_temporal_layer_produces_typed_output(
        self, mock_signal, mock_context
    ):
        """Temporal layer must produce TemporalLayerOutput."""
        # First run factual
        factual_layer = FactualLayer()
        factual_output = await factual_layer.execute({
            "signal": mock_signal,
            "reality": MagicMock(staleness_seconds=300, chokepoint_health={}),
            "context": mock_context,
        })
        
        # Then run temporal
        layer = TemporalLayer()
        output = await layer.execute({
            "factual": factual_output,
            "context": mock_context,
            "signal": mock_signal,
        })
        
        assert isinstance(output, TemporalLayerOutput)
        assert output.layer == ReasoningLayer.TEMPORAL
        assert output.decision_deadline is not None
        assert output.urgency_level in ["immediate", "urgent", "soon", "watch"]
    
    @pytest.mark.asyncio
    async def test_causal_layer_produces_typed_output(
        self, mock_signal
    ):
        """Causal layer must produce CausalLayerOutput."""
        factual_layer = FactualLayer()
        factual_output = await factual_layer.execute({
            "signal": mock_signal,
            "reality": MagicMock(staleness_seconds=300, chokepoint_health={}),
            "context": MagicMock(profile=MagicMock(customer_id="test"), active_shipments=[]),
        })
        
        layer = CausalLayer()
        output = await layer.execute({
            "factual": factual_output,
            "signal": mock_signal,
        })
        
        assert isinstance(output, CausalLayerOutput)
        assert output.layer == ReasoningLayer.CAUSAL
        assert len(output.root_causes) > 0
        assert len(output.causal_chain) > 0
    
    @pytest.mark.asyncio
    async def test_all_layers_track_execution_time(
        self, reasoning_engine, mock_signal, mock_reality, mock_context
    ):
        """All layers must track execution time."""
        trace = await reasoning_engine.reason(
            mock_signal, mock_reality, mock_context
        )
        
        # Check each layer has timing
        for layer in ReasoningLayer:
            layer_output = trace.get_layer(layer)
            assert layer_output is not None, f"Missing {layer.value} layer"
            assert layer_output.duration_ms >= 0, f"{layer.value} missing duration"
            assert layer_output.started_at is not None
            assert layer_output.completed_at is not None


# ============================================================================
# FULL PIPELINE TESTS
# ============================================================================


class TestReasoningPipeline:
    """Tests for full reasoning pipeline."""
    
    @pytest.mark.asyncio
    async def test_all_6_layers_execute_in_sequence(
        self, reasoning_engine, mock_signal, mock_reality, mock_context
    ):
        """All 6 layers must execute in sequence."""
        trace = await reasoning_engine.reason(
            mock_signal, mock_reality, mock_context
        )
        
        assert trace.is_complete
        assert trace.layer_count == 6
        
        # Verify each layer exists
        assert trace.factual is not None
        assert trace.temporal is not None
        assert trace.causal is not None
        assert trace.counterfactual is not None
        assert trace.strategic is not None
        assert trace.meta is not None
    
    @pytest.mark.asyncio
    async def test_reasoning_trace_is_complete(
        self, reasoning_engine, mock_signal, mock_reality, mock_context
    ):
        """Reasoning trace must be complete and inspectable."""
        trace = await reasoning_engine.reason(
            mock_signal, mock_reality, mock_context
        )
        
        # Trace has ID and timing
        assert trace.trace_id is not None
        assert trace.trace_id.startswith("trace_")
        assert trace.started_at is not None
        assert trace.completed_at is not None
        assert trace.total_duration_ms >= 0  # Can be 0 if very fast
        
        # Trace has quality scores
        assert 0 <= trace.data_quality_score <= 1
        assert 0 <= trace.reasoning_quality_score <= 1
        assert 0 <= trace.final_confidence <= 1
    
    @pytest.mark.asyncio
    async def test_trace_has_final_decision_or_escalation(
        self, reasoning_engine, mock_signal, mock_reality, mock_context
    ):
        """Trace must have either final decision or escalation."""
        trace = await reasoning_engine.reason(
            mock_signal, mock_reality, mock_context
        )
        
        if trace.escalated:
            assert trace.escalation_reason is not None
            assert trace.final_decision is None or trace.final_decision == ""
        else:
            assert trace.final_decision is not None
            assert trace.final_decision in ["reroute", "delay", "insure", "monitor", "do_nothing"]
    
    @pytest.mark.asyncio
    async def test_warnings_propagate_through_layers(
        self, reasoning_engine, mock_signal, mock_reality, mock_context
    ):
        """Warnings from layers must be accessible in trace."""
        trace = await reasoning_engine.reason(
            mock_signal, mock_reality, mock_context
        )
        
        # get_all_warnings should collect from all layers
        all_warnings = trace.get_all_warnings()
        assert isinstance(all_warnings, list)
        
        # Each layer's warnings should be part of all_warnings
        for layer in ReasoningLayer:
            layer_output = trace.get_layer(layer)
            if layer_output and layer_output.warnings:
                for warning in layer_output.warnings:
                    assert warning in all_warnings


# ============================================================================
# META LAYER DECISION TESTS
# ============================================================================


class TestMetaLayerDecisions:
    """Tests for meta layer decision making."""
    
    @pytest.mark.asyncio
    async def test_meta_escalates_on_low_data_quality(self):
        """Meta layer must escalate when data quality is low."""
        # Create mock factual output with low data quality
        factual = FactualLayerOutput(
            layer=ReasoningLayer.FACTUAL,
            verified_facts=[],
            data_quality_score=0.3,  # Below threshold
            data_gaps=["No reality data", "Signal unverified"],
            source_credibility={},
            confidence=0.3,
        )
        
        # Create mock other layers
        temporal = TemporalLayerOutput(
            layer=ReasoningLayer.TEMPORAL,
            event_sequence=[],
            decision_deadline=datetime.utcnow() + timedelta(hours=48),
            action_deadlines={},
            options_by_time={},
            urgency_level="soon",
            urgency_reason="Standard timeline",
            confidence=0.7,
        )
        
        causal = CausalLayerOutput(
            layer=ReasoningLayer.CAUSAL,
            root_causes=["Unknown"],
            causal_chain=[],
            intervention_points=[],
            confounders=[],
            confidence=0.5,
        )
        
        counterfactual = CounterfactualLayerOutput(
            layer=ReasoningLayer.COUNTERFACTUAL,
            scenarios=[],
            regret_matrix={},
            robust_action="monitor",
            robustness_score=0.5,
            decision_boundaries={},
            confidence=0.5,
        )
        
        strategic = StrategicLayerOutput(
            layer=ReasoningLayer.STRATEGIC,
            risk_tolerance_alignment=0.6,
            long_term_impact="neutral",
            long_term_impact_details="",
            relationship_impact="neutral",
            relationship_considerations=[],
            portfolio_exposure=0.1,
            concentration_risk="low",
            confidence=0.6,
        )
        
        meta_layer = MetaLayer()
        meta_output = await meta_layer.execute({
            "all_layers": {
                ReasoningLayer.FACTUAL: factual,
                ReasoningLayer.TEMPORAL: temporal,
                ReasoningLayer.CAUSAL: causal,
                ReasoningLayer.COUNTERFACTUAL: counterfactual,
                ReasoningLayer.STRATEGIC: strategic,
            },
            "context": MagicMock(profile=MagicMock(requires_manual_review=False)),
        })
        
        assert meta_output.should_decide is False
        assert "data quality" in meta_output.decision_reason.lower()
    
    @pytest.mark.asyncio
    async def test_meta_escalates_on_low_robustness(self):
        """Meta layer must escalate when decision robustness is low."""
        factual = FactualLayerOutput(
            layer=ReasoningLayer.FACTUAL,
            verified_facts=[VerifiedFact(
                fact_type="test", value=1, verified=True,
                source="test", source_reliability=0.8
            )],
            data_quality_score=0.7,
            data_gaps=[],
            source_credibility={"test": 0.8},
            confidence=0.7,
        )
        
        counterfactual = CounterfactualLayerOutput(
            layer=ReasoningLayer.COUNTERFACTUAL,
            scenarios=[],
            regret_matrix={},
            robust_action="reroute",
            robustness_score=0.2,  # Very low robustness
            decision_boundaries={},
            confidence=0.5,
        )
        
        meta_layer = MetaLayer()
        meta_output = await meta_layer.execute({
            "all_layers": {
                ReasoningLayer.FACTUAL: factual,
                ReasoningLayer.COUNTERFACTUAL: counterfactual,
            },
            "context": MagicMock(profile=MagicMock(requires_manual_review=False)),
        })
        
        assert meta_output.should_decide is False
        assert "robustness" in meta_output.decision_reason.lower() or "sensitive" in meta_output.decision_reason.lower()
    
    @pytest.mark.asyncio
    async def test_meta_escalates_for_manual_review_customer(self):
        """Meta layer must escalate when customer requires manual review."""
        factual = FactualLayerOutput(
            layer=ReasoningLayer.FACTUAL,
            verified_facts=[],
            data_quality_score=0.9,
            data_gaps=[],
            source_credibility={},
            confidence=0.9,
        )
        
        counterfactual = CounterfactualLayerOutput(
            layer=ReasoningLayer.COUNTERFACTUAL,
            scenarios=[],
            regret_matrix={},
            robust_action="reroute",
            robustness_score=0.8,
            decision_boundaries={},
            confidence=0.8,
        )
        
        meta_layer = MetaLayer()
        meta_output = await meta_layer.execute({
            "all_layers": {
                ReasoningLayer.FACTUAL: factual,
                ReasoningLayer.COUNTERFACTUAL: counterfactual,
            },
            "context": MagicMock(profile=MagicMock(requires_manual_review=True)),
        })
        
        assert meta_output.should_decide is False
        assert "manual review" in meta_output.decision_reason.lower()
    
    @pytest.mark.asyncio
    async def test_meta_proceeds_when_quality_high(self):
        """Meta layer must proceed with decision when quality is high."""
        factual = FactualLayerOutput(
            layer=ReasoningLayer.FACTUAL,
            verified_facts=[
                VerifiedFact(fact_type="test", value=1, verified=True, source="test", source_reliability=0.9),
            ],
            data_quality_score=0.85,
            data_gaps=[],
            source_credibility={"test": 0.9},
            confidence=0.85,
        )
        
        temporal = TemporalLayerOutput(
            layer=ReasoningLayer.TEMPORAL,
            event_sequence=[],
            decision_deadline=datetime.utcnow() + timedelta(hours=48),
            action_deadlines={},
            options_by_time={},
            urgency_level="soon",
            urgency_reason="Adequate time",
            confidence=0.8,
        )
        
        causal = CausalLayerOutput(
            layer=ReasoningLayer.CAUSAL,
            root_causes=["Test cause"],
            causal_chain=[],
            intervention_points=[],
            confounders=[],
            confidence=0.75,
        )
        
        counterfactual = CounterfactualLayerOutput(
            layer=ReasoningLayer.COUNTERFACTUAL,
            scenarios=[],
            regret_matrix={},
            robust_action="reroute",
            robustness_score=0.75,
            decision_boundaries={},
            confidence=0.75,
        )
        
        strategic = StrategicLayerOutput(
            layer=ReasoningLayer.STRATEGIC,
            risk_tolerance_alignment=0.8,
            long_term_impact="neutral",
            long_term_impact_details="",
            relationship_impact="neutral",
            relationship_considerations=[],
            portfolio_exposure=0.1,
            concentration_risk="low",
            confidence=0.8,
        )
        
        meta_layer = MetaLayer()
        meta_output = await meta_layer.execute({
            "all_layers": {
                ReasoningLayer.FACTUAL: factual,
                ReasoningLayer.TEMPORAL: temporal,
                ReasoningLayer.CAUSAL: causal,
                ReasoningLayer.COUNTERFACTUAL: counterfactual,
                ReasoningLayer.STRATEGIC: strategic,
            },
            "context": MagicMock(profile=MagicMock(requires_manual_review=False)),
        })
        
        assert meta_output.should_decide is True
        assert meta_output.if_decide.get("action") or meta_output.if_decide.get("final_action")


# ============================================================================
# FACTORY TESTS
# ============================================================================


class TestFactory:
    """Tests for factory functions."""
    
    def test_create_engine_with_defaults(self):
        """Should create engine with default layers."""
        engine = create_reasoning_engine()
        
        assert engine is not None
        assert engine._factual is not None
        assert engine._temporal is not None
        assert engine._causal is not None
        assert engine._counterfactual is not None
        assert engine._strategic is not None
        assert engine._meta is not None
    
    def test_create_engine_with_custom_layers(self):
        """Should create engine with custom layers."""
        custom_factual = FactualLayer()
        
        engine = create_reasoning_engine(factual_layer=custom_factual)
        
        assert engine._factual is custom_factual


# ============================================================================
# PARTIAL REASONING TESTS
# ============================================================================


class TestPartialReasoning:
    """Tests for partial reasoning execution."""
    
    @pytest.mark.asyncio
    async def test_partial_reasoning_stops_at_layer(
        self, mock_signal, mock_reality, mock_context
    ):
        """Partial reasoning should stop at specified layer."""
        engine = ReasoningEngine()
        
        trace = await engine.reason_partial(
            mock_signal, mock_reality, mock_context,
            stop_after=ReasoningLayer.CAUSAL,
        )
        
        # Should have first 3 layers
        assert trace.factual is not None
        assert trace.temporal is not None
        assert trace.causal is not None
        
        # Should not have later layers
        assert trace.counterfactual is None
        assert trace.strategic is None
        assert trace.meta is None


# ============================================================================
# SCHEMA TESTS
# ============================================================================


class TestSchemas:
    """Tests for reasoning schemas."""
    
    def test_verified_fact_has_required_fields(self):
        """VerifiedFact must have all required fields."""
        fact = VerifiedFact(
            fact_type="test_fact",
            value=42,
            verified=True,
            source="test_source",
            source_reliability=0.85,
        )
        
        assert fact.fact_id is not None
        assert fact.fact_type == "test_fact"
        assert fact.value == 42
        assert fact.source_reliability == 0.85
    
    def test_timeline_event_has_required_fields(self):
        """TimelineEvent must have all required fields."""
        event = TimelineEvent(
            event_type="departure",
            timestamp=datetime.utcnow(),
            description="Ship departing",
            is_past=False,
            confidence=0.9,
        )
        
        assert event.event_id is not None
        assert event.event_type == "departure"
        assert event.confidence == 0.9
    
    def test_scenario_has_required_fields(self):
        """Scenario must have all required fields."""
        scenario = Scenario(
            name="Base Case",
            description="Most likely scenario",
            probability=0.5,
            assumptions=["Event occurs as predicted"],
            outcomes={"delay_days": 10},
            best_action="reroute",
        )
        
        assert scenario.scenario_id is not None
        assert scenario.name == "Base Case"
        assert scenario.probability == 0.5
    
    def test_reasoning_trace_layer_summary(self):
        """ReasoningTrace should provide layer summary."""
        trace = ReasoningTrace(
            factual=FactualLayerOutput(
                layer=ReasoningLayer.FACTUAL,
                verified_facts=[],
                data_quality_score=0.8,
                data_gaps=[],
                source_credibility={},
                confidence=0.8,
                duration_ms=50,
            ),
        )
        
        summary = trace.get_layer_summary()
        
        assert "factual" in summary
        assert summary["factual"]["confidence"] == 0.8
        assert summary["factual"]["duration_ms"] == 50
