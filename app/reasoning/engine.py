"""
Multi-layer Reasoning Engine.

This is the BRAIN of RISKCAST.

Orchestrates the 6-layer reasoning pipeline:
1. FACTUAL    - Gather and validate facts
2. TEMPORAL   - Timeline and deadline analysis
3. CAUSAL     - Causal chain identification (LLM-enhanced)
4. COUNTERFACTUAL - What-if scenario analysis
5. STRATEGIC  - Strategy alignment check
6. META       - Decision to decide

Each layer builds on previous layers' outputs.
The meta layer decides whether to proceed or escalate.

LLM Enhancement:
    When an ANTHROPIC_API_KEY is configured, the engine enhances
    causal analysis and generates natural language explanations.
    If LLM is unavailable, all layers fall back to rule-based logic.

Usage:
    engine = ReasoningEngine()
    trace = await engine.reason(signal, reality, context)
    
    if trace.escalated:
        # Handle escalation
    else:
        # Use trace.final_decision
"""

from datetime import datetime
from typing import Optional, Any
import uuid
import structlog

from app.reasoning.deterministic import generate_deterministic_trace_id
from app.reasoning.schemas import (
    ReasoningLayer,
    ReasoningTrace,
    LayerOutput,
    FactualLayerOutput,
    TemporalLayerOutput,
    CausalLayerOutput,
    CounterfactualLayerOutput,
    StrategicLayerOutput,
    MetaLayerOutput,
)
from app.reasoning.layers import (
    FactualLayer,
    TemporalLayer,
    CausalLayer,
    CounterfactualLayer,
    StrategicLayer,
    MetaLayer,
)
from app.reasoning.llm_service import ReasoningLLMService, get_reasoning_llm_service

logger = structlog.get_logger(__name__)


class ReasoningEngine:
    """
    6-layer reasoning engine for enterprise-grade decision making.
    
    The engine executes layers in sequence, each building on previous outputs.
    The final meta layer decides whether to proceed with the decision
    or escalate to human review.
    
    Key features:
    - Full reasoning trace for audit and debugging
    - Explicit confidence scores at each layer
    - Quality-based escalation decisions
    - Timing tracking for performance monitoring
    
    Thread Safety:
    - Each call creates its own trace
    - Safe for concurrent use
    """
    
    def __init__(
        self,
        factual_layer: Optional[FactualLayer] = None,
        temporal_layer: Optional[TemporalLayer] = None,
        causal_layer: Optional[CausalLayer] = None,
        counterfactual_layer: Optional[CounterfactualLayer] = None,
        strategic_layer: Optional[StrategicLayer] = None,
        meta_layer: Optional[MetaLayer] = None,
        llm_service: Optional[ReasoningLLMService] = None,
    ):
        """
        Initialize reasoning engine with layers.
        
        Args:
            Each layer can be customized or left as default.
            llm_service: Optional LLM service for enhanced reasoning.
                         If not provided, attempts to initialize from env.
        """
        self._factual = factual_layer or FactualLayer()
        self._temporal = temporal_layer or TemporalLayer()
        self._causal = causal_layer or CausalLayer()
        self._counterfactual = counterfactual_layer or CounterfactualLayer()
        self._strategic = strategic_layer or StrategicLayer()
        self._meta = meta_layer or MetaLayer()
        
        # LLM enhancement layer (optional)
        try:
            self._llm = llm_service or get_reasoning_llm_service()
        except Exception:
            self._llm = None
        
        if self._llm and self._llm.is_available:
            logger.info("reasoning_engine_llm_enabled")
        else:
            logger.info("reasoning_engine_llm_disabled", msg="Using rule-based reasoning only")
    
    async def reason(
        self,
        signal: Any,  # OmenSignal
        reality: Any,  # RealitySnapshot
        context: Any,  # CustomerContext
    ) -> ReasoningTrace:
        """
        Execute full reasoning pipeline.
        
        Runs all 6 layers in sequence:
        1. Factual: Gather and validate facts
        2. Temporal: Analyze timeline and deadlines
        3. Causal: Build causal chain
        4. Counterfactual: What-if analysis
        5. Strategic: Check strategy alignment
        6. Meta: Decide to decide or escalate
        
        Args:
            signal: The OmenSignal triggering this decision
            reality: Current RealitySnapshot from Oracle
            context: CustomerContext with profile and shipments
            
        Returns:
            ReasoningTrace with all layer outputs and final decision/escalation
        """
        # Generate deterministic trace ID for reproducibility
        trace_id = generate_deterministic_trace_id(signal, context)
        started_at = datetime.utcnow()
        
        logger.info(
            "reasoning_started",
            trace_id=trace_id,
            signal_id=getattr(signal, "signal_id", None),
            customer_id=getattr(getattr(context, "profile", None), "customer_id", None),
        )
        
        layers = {}
        
        try:
            # Layer 1: Factual
            factual_output = await self._execute_layer(
                layer=self._factual,
                layer_type=ReasoningLayer.FACTUAL,
                inputs={"signal": signal, "reality": reality, "context": context},
            )
            layers[ReasoningLayer.FACTUAL] = factual_output
            
            # Layer 2: Temporal
            temporal_output = await self._execute_layer(
                layer=self._temporal,
                layer_type=ReasoningLayer.TEMPORAL,
                inputs={"factual": factual_output, "context": context, "signal": signal},
            )
            layers[ReasoningLayer.TEMPORAL] = temporal_output
            
            # Layer 3: Causal
            causal_output = await self._execute_layer(
                layer=self._causal,
                layer_type=ReasoningLayer.CAUSAL,
                inputs={"factual": factual_output, "signal": signal},
            )
            layers[ReasoningLayer.CAUSAL] = causal_output
            
            # Layer 4: Counterfactual
            counterfactual_output = await self._execute_layer(
                layer=self._counterfactual,
                layer_type=ReasoningLayer.COUNTERFACTUAL,
                inputs={
                    "factual": factual_output,
                    "temporal": temporal_output,
                    "causal": causal_output,
                    "context": context,
                },
            )
            layers[ReasoningLayer.COUNTERFACTUAL] = counterfactual_output
            
            # Layer 5: Strategic
            strategic_output = await self._execute_layer(
                layer=self._strategic,
                layer_type=ReasoningLayer.STRATEGIC,
                inputs={
                    "counterfactual": counterfactual_output,
                    "context": context,
                },
            )
            layers[ReasoningLayer.STRATEGIC] = strategic_output
            
            # Layer 6: Meta (decides whether to decide)
            meta_output = await self._execute_layer(
                layer=self._meta,
                layer_type=ReasoningLayer.META,
                inputs={
                    "all_layers": layers,
                    "context": context,
                },
            )
            layers[ReasoningLayer.META] = meta_output
            
        except Exception as e:
            logger.error(
                "reasoning_failed",
                trace_id=trace_id,
                error=str(e),
            )
            raise
        
        completed_at = datetime.utcnow()
        
        # Extract final decision from meta layer
        final_decision = None
        if meta_output.should_decide:
            final_decision = meta_output.if_decide.get("final_action") or meta_output.if_decide.get("action")
        
        # LLM Enhancement: Enhance causal analysis if available
        llm_enhanced = False
        llm_explanation = None
        llm_causal_enhancement = None
        
        if self._llm and self._llm.is_available:
            try:
                # Enhance causal chain with LLM
                signal_type = getattr(signal, "event_type", "unknown")
                signal_desc = getattr(signal, "description", str(signal))
                chokepoints = getattr(signal, "chokepoint", "")
                
                existing_chain = []
                if causal_output and hasattr(causal_output, "causal_chain"):
                    existing_chain = [
                        {"cause": link.cause, "effect": link.effect, "strength": link.strength}
                        for link in causal_output.causal_chain
                    ]
                
                llm_causal_enhancement = await self._llm.enhance_causal_analysis(
                    event_type=signal_type,
                    signal_description=signal_desc[:500],
                    affected_chokepoints=[chokepoints] if chokepoints else [],
                    existing_chain=existing_chain,
                )
                
                # Generate natural language explanation
                if final_decision:
                    customer_ctx = {
                        "company_name": getattr(getattr(context, "profile", None), "company_name", "Unknown"),
                        "industry": getattr(getattr(context, "profile", None), "industry", "General"),
                        "risk_tolerance": getattr(getattr(context, "profile", None), "risk_tolerance", "BALANCED"),
                    }
                    llm_explanation = await self._llm.generate_decision_explanation(
                        decision_action=str(final_decision),
                        reasoning_trace={
                            "data_quality_score": factual_output.data_quality_score if factual_output else 0,
                            "final_confidence": meta_output.reasoning_confidence,
                            "escalated": not meta_output.should_decide,
                        },
                        customer_context=customer_ctx,
                    )
                
                llm_enhanced = True
                logger.info("reasoning_llm_enhancement_complete")
                
            except Exception as e:
                logger.warning("reasoning_llm_enhancement_failed", error=str(e))
        
        # Build reasoning trace
        trace = ReasoningTrace(
            trace_id=trace_id,
            started_at=started_at,
            completed_at=completed_at,
            total_duration_ms=int((completed_at - started_at).total_seconds() * 1000),
            factual=factual_output,
            temporal=temporal_output,
            causal=causal_output,
            counterfactual=counterfactual_output,
            strategic=strategic_output,
            meta=meta_output,
            final_decision=final_decision,
            final_confidence=meta_output.reasoning_confidence,
            escalated=not meta_output.should_decide,
            escalation_reason=meta_output.escalation_reason,
            data_quality_score=factual_output.data_quality_score,
            reasoning_quality_score=self._calculate_reasoning_quality(layers),
        )
        
        # Attach LLM enhancements to trace metadata
        if llm_enhanced:
            trace.llm_enhanced = True
            trace.llm_explanation = llm_explanation
            trace.llm_causal_enhancement = llm_causal_enhancement
        
        logger.info(
            "reasoning_completed",
            trace_id=trace_id,
            duration_ms=trace.total_duration_ms,
            escalated=trace.escalated,
            final_decision=trace.final_decision,
            final_confidence=trace.final_confidence,
        )
        
        return trace
    
    async def reason_partial(
        self,
        signal: Any,
        reality: Any,
        context: Any,
        stop_after: ReasoningLayer,
    ) -> ReasoningTrace:
        """
        Execute partial reasoning pipeline (for debugging/testing).
        
        Runs layers up to and including `stop_after`.
        
        Args:
            signal, reality, context: Same as `reason()`
            stop_after: Stop after this layer
            
        Returns:
            Partial ReasoningTrace
        """
        trace_id = f"trace_partial_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"
        started_at = datetime.utcnow()
        
        layers = {}
        layer_order = [
            ReasoningLayer.FACTUAL,
            ReasoningLayer.TEMPORAL,
            ReasoningLayer.CAUSAL,
            ReasoningLayer.COUNTERFACTUAL,
            ReasoningLayer.STRATEGIC,
            ReasoningLayer.META,
        ]
        
        # Run layers up to stop_after
        factual_output = None
        temporal_output = None
        causal_output = None
        counterfactual_output = None
        strategic_output = None
        meta_output = None
        
        for layer_type in layer_order:
            if layer_type == ReasoningLayer.FACTUAL:
                factual_output = await self._execute_layer(
                    self._factual, layer_type,
                    {"signal": signal, "reality": reality, "context": context},
                )
                layers[layer_type] = factual_output
            elif layer_type == ReasoningLayer.TEMPORAL:
                temporal_output = await self._execute_layer(
                    self._temporal, layer_type,
                    {"factual": factual_output, "context": context, "signal": signal},
                )
                layers[layer_type] = temporal_output
            elif layer_type == ReasoningLayer.CAUSAL:
                causal_output = await self._execute_layer(
                    self._causal, layer_type,
                    {"factual": factual_output, "signal": signal},
                )
                layers[layer_type] = causal_output
            elif layer_type == ReasoningLayer.COUNTERFACTUAL:
                counterfactual_output = await self._execute_layer(
                    self._counterfactual, layer_type,
                    {"factual": factual_output, "temporal": temporal_output,
                     "causal": causal_output, "context": context},
                )
                layers[layer_type] = counterfactual_output
            elif layer_type == ReasoningLayer.STRATEGIC:
                strategic_output = await self._execute_layer(
                    self._strategic, layer_type,
                    {"counterfactual": counterfactual_output, "context": context},
                )
                layers[layer_type] = strategic_output
            elif layer_type == ReasoningLayer.META:
                meta_output = await self._execute_layer(
                    self._meta, layer_type,
                    {"all_layers": layers, "context": context},
                )
                layers[layer_type] = meta_output
            
            if layer_type == stop_after:
                break
        
        completed_at = datetime.utcnow()
        
        return ReasoningTrace(
            trace_id=trace_id,
            started_at=started_at,
            completed_at=completed_at,
            total_duration_ms=int((completed_at - started_at).total_seconds() * 1000),
            factual=factual_output,
            temporal=temporal_output,
            causal=causal_output,
            counterfactual=counterfactual_output,
            strategic=strategic_output,
            meta=meta_output,
            final_decision=meta_output.if_decide.get("final_action") if meta_output and meta_output.should_decide else None,
            final_confidence=meta_output.reasoning_confidence if meta_output else 0.0,
            escalated=not meta_output.should_decide if meta_output else True,
            escalation_reason=meta_output.escalation_reason if meta_output else "Partial trace",
            data_quality_score=factual_output.data_quality_score if factual_output else 0.0,
            reasoning_quality_score=self._calculate_reasoning_quality(layers),
        )
    
    async def _execute_layer(
        self,
        layer: Any,
        layer_type: ReasoningLayer,
        inputs: dict,
    ) -> LayerOutput:
        """Execute a single layer with timing and error handling."""
        started_at = datetime.utcnow()
        
        try:
            output = await layer.execute(inputs)
            
            # Ensure timing is set
            if output.started_at is None:
                output.started_at = started_at
            if output.completed_at is None:
                output.completed_at = datetime.utcnow()
            if output.duration_ms == 0:
                output.duration_ms = int(
                    (output.completed_at - output.started_at).total_seconds() * 1000
                )
            
            logger.debug(
                "layer_executed",
                layer=layer_type.value,
                duration_ms=output.duration_ms,
                confidence=output.confidence,
            )
            
            return output
            
        except Exception as e:
            logger.error(
                "layer_execution_failed",
                layer=layer_type.value,
                error=str(e),
            )
            raise
    
    def _calculate_reasoning_quality(
        self,
        layers: dict[ReasoningLayer, LayerOutput],
    ) -> float:
        """Calculate overall reasoning quality score."""
        scores = []
        
        for layer_type, layer_output in layers.items():
            if layer_output is not None:
                scores.append(layer_output.confidence)
        
        if not scores:
            return 0.0
        
        return sum(scores) / len(scores)


# ============================================================================
# FACTORY
# ============================================================================


def create_reasoning_engine(
    factual_layer: Optional[FactualLayer] = None,
    temporal_layer: Optional[TemporalLayer] = None,
    causal_layer: Optional[CausalLayer] = None,
    counterfactual_layer: Optional[CounterfactualLayer] = None,
    strategic_layer: Optional[StrategicLayer] = None,
    meta_layer: Optional[MetaLayer] = None,
    llm_service: Optional[ReasoningLLMService] = None,
) -> ReasoningEngine:
    """
    Factory function to create ReasoningEngine.
    
    All layers are optional - defaults will be used if not provided.
    If llm_service is provided or ANTHROPIC_API_KEY is set, the engine
    will use LLM to enhance causal analysis and generate explanations.
    
    Returns:
        Configured ReasoningEngine with optional LLM enhancement
    """
    return ReasoningEngine(
        factual_layer=factual_layer,
        temporal_layer=temporal_layer,
        causal_layer=causal_layer,
        counterfactual_layer=counterfactual_layer,
        strategic_layer=strategic_layer,
        meta_layer=meta_layer,
        llm_service=llm_service,
    )
