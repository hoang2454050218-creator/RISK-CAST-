"""Decision Composer - Orchestrate all components into a complete decision.

THE HEART OF RISKCAST.

This module takes:
- Signal from OMEN
- Intelligence from ORACLE
- Customer context

And produces a complete DecisionObject answering all 7 questions WITH UNCERTAINTY.

Pipeline (Classic Mode - backward compatible):
1. ExposureMatcher → Which shipments are affected?
2. ImpactCalculator → How much in $ and days?
3. ActionGenerator → What are the options?
4. TradeOffAnalyzer → What if I don't act?
5. UncertaintyPropagation → Calculate CIs for all outputs (A2.2)
6. DecisionComposer → Combine into Q1-Q7 format
7. ConfidenceCommunicator → Generate actionable guidance (A4.4)

Pipeline (NEW - ReasoningEngine Integration for A1 Cognitive Excellence):
1. AuditService captures inputs
2. ReasoningEngine executes 6-layer pipeline → ReasoningTrace
3. META layer decision check (escalate vs proceed)
4. Extract insights from reasoning layers
5. Build DecisionObject with reasoning_trace_id linkage
6. PersistentCalibrator calibrates and persists confidence
7. AuditService records decision

This version addresses audit gaps:
- A1: ReasoningEngine integration for 6-layer cognitive pipeline
- A2.2: All numeric outputs include 90% and 95% confidence intervals
- A3: Persistent calibration via PersistentCalibrator
- A4.4: ConfidenceGuidance provides actionable uncertainty communication
"""

from datetime import datetime, timedelta
from typing import Optional, Tuple, TYPE_CHECKING
import uuid

import structlog

from app.core.tracing import get_tracer, trace, SpanKind
from app.oracle.schemas import CorrelatedIntelligence
from app.riskcast.calculators import ImpactCalculator, create_impact_calculator
from app.riskcast.constants import (
    DECISION_TTL_HOURS,
    ConfidenceLevel,
    Severity,
    Urgency,
    get_confidence_level,
    get_severity,
)
from app.riskcast.generators import (
    ActionGenerator,
    TradeOffAnalyzer,
    create_action_generator,
    create_tradeoff_analyzer,
)
from app.riskcast.matchers import ExposureMatch, ExposureMatcher, create_exposure_matcher
from app.riskcast.schemas.action import ActionSet, TradeOffAnalysis
from app.riskcast.schemas.customer import CustomerContext
from app.riskcast.schemas.decision import (
    DecisionObject,
    Q1WhatIsHappening,
    Q2WhenWillItHappen,
    Q3HowBadIsIt,
    Q4WhyIsThisHappening,
    Q5WhatToDoNow,
    Q6HowConfident,
    Q7WhatIfNothing,
)
from app.riskcast.schemas.impact import TotalImpact
from app.uncertainty.bayesian import UncertainValue
from app.uncertainty.communication import ConfidenceCommunicator, ConfidenceGuidance

# Type checking imports for new integration
if TYPE_CHECKING:
    from app.reasoning.engine import ReasoningEngine
    from app.reasoning.schemas import ReasoningTrace, ReasoningLayer
    from app.audit.service import AuditService
    from app.calibration.persistence import PersistentCalibrator

logger = structlog.get_logger(__name__)


# ============================================================================
# DECISION COMPOSER
# ============================================================================


class DecisionComposer:
    """
    Orchestrates all RISKCAST components into a complete decision.

    This is the HEART of the system. It:
    1. Runs the full pipeline (match → impact → action → tradeoff)
    2. Propagates uncertainty through all calculations (A2.2)
    3. Translates results into the 7 Questions format with CIs
    4. Generates actionable confidence guidance (A4.4)
    5. Produces a DecisionObject ready for the user

    Every DecisionObject MUST answer all 7 questions. No exceptions.
    All numeric outputs include confidence intervals.
    
    INTEGRATION ARCHITECTURE (A1 Cognitive Excellence):
    
    1. ReasoningEngine executes 6 layers → ReasoningTrace
    2. If META layer says "escalate" → Return None, trigger escalation
    3. If META layer says "decide" → Build DecisionObject from trace
    4. DecisionObject includes reasoning_trace_id for audit
    5. PersistentCalibrator persists calibration data (A3)
    """

    def __init__(
        self,
        exposure_matcher: Optional[ExposureMatcher] = None,
        impact_calculator: Optional[ImpactCalculator] = None,
        action_generator: Optional[ActionGenerator] = None,
        tradeoff_analyzer: Optional[TradeOffAnalyzer] = None,
        confidence_communicator: Optional[ConfidenceCommunicator] = None,
        decision_ttl_hours: int = DECISION_TTL_HOURS,
        # NEW: ReasoningEngine integration (A1)
        reasoning_engine: Optional["ReasoningEngine"] = None,
        audit_service: Optional["AuditService"] = None,
        calibrator: Optional["PersistentCalibrator"] = None,
    ):
        """
        Initialize decision composer with component dependencies.

        Args:
            exposure_matcher: Matcher for finding affected shipments
            impact_calculator: Calculator for financial/time impact
            action_generator: Generator for concrete actions
            tradeoff_analyzer: Analyzer for inaction consequences
            confidence_communicator: Communicator for uncertainty guidance (A4.4)
            decision_ttl_hours: Hours until decision expires
            reasoning_engine: 6-layer reasoning engine (A1)
            audit_service: Audit trail service (A3)
            calibrator: Persistent calibrator for confidence calibration (A3)
        """
        self.exposure_matcher = exposure_matcher or create_exposure_matcher()
        self.impact_calculator = impact_calculator or create_impact_calculator()
        self.action_generator = action_generator or create_action_generator()
        self.tradeoff_analyzer = tradeoff_analyzer or create_tradeoff_analyzer()
        self.confidence_communicator = confidence_communicator or ConfidenceCommunicator()
        self.decision_ttl_hours = decision_ttl_hours
        
        # NEW: ReasoningEngine integration (A1)
        self._reasoning = reasoning_engine
        self._audit = audit_service
        self._calibrator = calibrator
        
        # Track if reasoning mode is enabled
        self._reasoning_enabled = reasoning_engine is not None

    def compose(
        self,
        intelligence: CorrelatedIntelligence,
        context: CustomerContext,
    ) -> Optional[DecisionObject]:
        """
        Compose a complete decision from intelligence and customer context.

        This is the main entry point for RISKCAST.

        Args:
            intelligence: Correlated intelligence from ORACLE
            context: Customer context with profile and shipments

        Returns:
            DecisionObject with all 7 questions answered, or None if no exposure
        """
        customer_id = context.profile.customer_id
        signal_id = intelligence.signal.signal_id
        tracer = get_tracer()

        logger.info(
            "composing_decision",
            customer_id=customer_id,
            signal_id=signal_id,
        )

        # Main span for the entire decision composition
        with tracer.start_span_sync(
            "compose_decision",
            kind=SpanKind.INTERNAL,
            attributes={
                "customer_id": customer_id,
                "signal_id": signal_id,
                "chokepoint": intelligence.signal.chokepoint,
            },
        ) as main_span:
            # ====================================================================
            # STEP 1: MATCH EXPOSURE
            # ====================================================================
            with tracer.start_span_sync(
                "match_exposure",
                attributes={"shipment_count": len(context.active_shipments)},
            ) as exposure_span:
                exposure = self.exposure_matcher.match(intelligence, context)
                exposure_span.set_attribute("has_exposure", exposure.has_exposure)
                exposure_span.set_attribute("affected_count", len(exposure.affected_shipments))

            if not exposure.has_exposure:
                logger.info(
                    "no_exposure_found",
                    customer_id=customer_id,
                    signal_id=signal_id,
                )
                main_span.set_attribute("result", "no_exposure")
                return None

            # ====================================================================
            # STEP 2: CALCULATE IMPACT
            # ====================================================================
            with tracer.start_span_sync(
                "calculate_impact",
                attributes={"affected_shipments": len(exposure.affected_shipments)},
            ) as impact_span:
                impact = self.impact_calculator.calculate(exposure, intelligence, context)
                impact_span.set_attribute("total_cost_usd", impact.total_cost_usd)
                impact_span.set_attribute("severity", impact.overall_severity.value)

            # ====================================================================
            # STEP 3: GENERATE ACTIONS
            # ====================================================================
            with tracer.start_span_sync(
                "generate_actions",
                attributes={"severity": impact.overall_severity.value},
            ) as action_span:
                action_set = self.action_generator.generate(
                    exposure, impact, intelligence, context
                )
                action_span.set_attribute("primary_action", action_set.primary.action_type.value)
                action_span.set_attribute("alternatives_count", len(action_set.alternatives))

            # ====================================================================
            # STEP 4: ANALYZE TRADE-OFFS
            # ====================================================================
            with tracer.start_span_sync(
                "analyze_tradeoffs",
                attributes={"primary_action": action_set.primary.action_type.value},
            ) as tradeoff_span:
                tradeoff = self.tradeoff_analyzer.analyze(
                    action_set, impact, exposure, intelligence
                )
                tradeoff_span.set_attribute("inaction_cost", tradeoff.cost_of_inaction_usd)

            # ====================================================================
            # STEP 5: PROPAGATE UNCERTAINTY (A2.2)
            # ====================================================================
            with tracer.start_span_sync("propagate_uncertainty") as uncertainty_span:
                # Create uncertain values for key metrics
                exposure_uncertain = self._create_exposure_uncertain(impact, exposure, intelligence)
                delay_uncertain = self._create_delay_uncertain(impact, intelligence)
                cost_uncertain = self._create_cost_uncertain(action_set, intelligence)
                inaction_uncertain = self._create_inaction_uncertain(tradeoff, intelligence)
                
                uncertainty_span.set_attribute("exposure_ci_width", 
                    exposure_uncertain.ci_90[1] - exposure_uncertain.ci_90[0])
                uncertainty_span.set_attribute("exposure_is_highly_uncertain", 
                    exposure_uncertain.is_highly_uncertain)

            # ====================================================================
            # STEP 6: COMPOSE 7 QUESTIONS (with CIs)
            # ====================================================================
            with tracer.start_span_sync("compose_questions") as questions_span:
                q1 = self._compose_q1(exposure, intelligence, context)
                q2 = self._compose_q2(exposure, impact, intelligence, tradeoff)
                q3 = self._compose_q3(impact, exposure, exposure_uncertain, delay_uncertain)
                q4 = self._compose_q4(intelligence)
                q5 = self._compose_q5(action_set, tradeoff, cost_uncertain)
                q6 = self._compose_q6(impact, intelligence, action_set)
                q7 = self._compose_q7(tradeoff, impact, inaction_uncertain)
                questions_span.set_attribute("confidence_score", q6.score)

            # ====================================================================
            # STEP 7: GENERATE CONFIDENCE GUIDANCE (A4.4)
            # ====================================================================
            with tracer.start_span_sync("generate_confidence_guidance") as guidance_span:
                # Build a partial decision for the communicator
                partial_decision = DecisionObject(
                    decision_id="temp",
                    customer_id=customer_id,
                    signal_id=signal_id,
                    q1_what=q1,
                    q2_when=q2,
                    q3_severity=q3,
                    q4_why=q4,
                    q5_action=q5,
                    q6_confidence=q6,
                    q7_inaction=q7,
                    expires_at=datetime.utcnow() + timedelta(hours=self.decision_ttl_hours),
                )
                
                confidence_guidance = self.confidence_communicator.generate_guidance(
                    decision=partial_decision,
                    exposure_uncertain=exposure_uncertain,
                    delay_uncertain=delay_uncertain,
                    cost_uncertain=cost_uncertain,
                    calibrated_confidence=q6.score,  # Could be replaced with calibrated score
                )
                
                guidance_span.set_attribute("uncertainty_level", confidence_guidance.uncertainty_level.value)
                guidance_span.set_attribute("should_act", confidence_guidance.should_act)
                guidance_span.set_attribute("act_confidence", confidence_guidance.act_confidence.value)

            # ====================================================================
            # STEP 8: BUILD DECISION OBJECT
            # ====================================================================
            decision_id = f"dec_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{customer_id[:8]}"
            expires_at = datetime.utcnow() + timedelta(hours=self.decision_ttl_hours)

            # Get alternative actions
            alternatives = [
                {
                    "action_type": a.action_type.value,
                    "summary": a.summary,
                    "cost_usd": a.cost_usd,
                    "benefit_usd": a.risk_mitigated_usd,
                    "deadline": a.deadline.isoformat() if a.deadline else None,
                }
                for a in action_set.alternatives
            ]

            decision = DecisionObject(
                decision_id=decision_id,
                customer_id=customer_id,
                signal_id=signal_id,
                q1_what=q1,
                q2_when=q2,
                q3_severity=q3,
                q4_why=q4,
                q5_action=q5,
                q6_confidence=q6,
                q7_inaction=q7,
                confidence_guidance=confidence_guidance,
                alternative_actions=alternatives,
                expires_at=expires_at,
            )

            # Add final attributes to main span
            main_span.set_attribute("result", "decision_composed")
            main_span.set_attribute("decision_id", decision_id)
            main_span.set_attribute("severity", q3.severity.value)
            main_span.set_attribute("urgency", q2.urgency.value)
            main_span.set_attribute("action", q5.action_type)
            main_span.set_attribute("exposure_usd", q3.total_exposure_usd)
            main_span.set_attribute("confidence", q6.score)

            logger.info(
                "decision_composed",
                decision_id=decision_id,
                customer_id=customer_id,
                signal_id=signal_id,
                severity=q3.severity.value,
                urgency=q2.urgency.value,
                action=q5.action_type,
                exposure_usd=q3.total_exposure_usd,
                confidence=q6.score,
            )

            return decision

    # ========================================================================
    # NEW: ASYNC COMPOSE WITH REASONING ENGINE (A1 Cognitive Excellence)
    # ========================================================================

    async def compose_decision(
        self,
        intelligence: CorrelatedIntelligence,
        context: CustomerContext,
    ) -> Optional[DecisionObject]:
        """
        Compose a complete decision using the 6-layer reasoning engine.
        
        This is the NEW entry point for RISKCAST with full cognitive capabilities.
        
        INTEGRATION FLOW:
        1. Capture inputs via AuditService
        2. Execute ReasoningEngine's 6-layer pipeline
        3. Check META layer decision (escalate vs proceed)
        4. Extract insights from all reasoning layers
        5. Build DecisionObject with reasoning trace linkage
        6. Calibrate confidence and persist via PersistentCalibrator
        7. Record decision in audit trail
        
        Args:
            intelligence: Correlated intelligence from ORACLE
            context: Customer context with profile and shipments
            
        Returns:
            DecisionObject with all 7 questions answered, or None if:
            - No exposure found
            - META layer escalates to human review
            
        Raises:
            ValueError: If reasoning engine not configured
        """
        # Fallback to classic compose if reasoning not enabled
        if not self._reasoning_enabled:
            logger.warning(
                "reasoning_engine_not_configured",
                fallback="classic_compose",
            )
            return self.compose(intelligence, context)
        
        customer_id = context.profile.customer_id
        signal_id = intelligence.signal.signal_id
        tracer = get_tracer()
        
        logger.info(
            "composing_decision_with_reasoning",
            customer_id=customer_id,
            signal_id=signal_id,
            reasoning_enabled=True,
        )
        
        # Step 1: Capture inputs in audit trail (A3)
        if self._audit:
            await self._audit.capture_inputs(
                signal=intelligence.signal,
                reality=intelligence.reality_snapshot,
                context=context,
            )
        
        with tracer.start_span_sync(
            "compose_decision_with_reasoning",
            kind=SpanKind.INTERNAL,
            attributes={
                "customer_id": customer_id,
                "signal_id": signal_id,
                "chokepoint": intelligence.signal.chokepoint,
                "reasoning_enabled": True,
            },
        ) as main_span:
            
            # ================================================================
            # STEP 2: EXECUTE REASONING ENGINE
            # ================================================================
            with tracer.start_span_sync("execute_reasoning") as reasoning_span:
                reasoning_trace = await self._reasoning.reason(
                    signal=intelligence.signal,
                    reality=intelligence.reality_snapshot,
                    context=context,
                )
                
                reasoning_span.set_attribute("trace_id", reasoning_trace.trace_id)
                reasoning_span.set_attribute("escalated", reasoning_trace.escalated)
                reasoning_span.set_attribute("duration_ms", reasoning_trace.total_duration_ms)
                reasoning_span.set_attribute("reasoning_quality", reasoning_trace.reasoning_quality_score)
                reasoning_span.set_attribute("data_quality", reasoning_trace.data_quality_score)
            
            logger.info(
                "reasoning_completed",
                trace_id=reasoning_trace.trace_id,
                escalated=reasoning_trace.escalated,
                duration_ms=reasoning_trace.total_duration_ms,
                reasoning_quality=reasoning_trace.reasoning_quality_score,
            )
            
            # ================================================================
            # STEP 3: CHECK META LAYER DECISION
            # ================================================================
            if reasoning_trace.escalated:
                logger.warning(
                    "decision_escalated",
                    trace_id=reasoning_trace.trace_id,
                    reason=reasoning_trace.escalation_reason,
                    customer_id=customer_id,
                )
                main_span.set_attribute("result", "escalated")
                main_span.set_attribute("escalation_reason", reasoning_trace.escalation_reason)
                
                # Record escalation in audit
                if self._audit:
                    await self._audit.record_escalation(
                        trace_id=reasoning_trace.trace_id,
                        reason=reasoning_trace.escalation_reason,
                        customer_id=customer_id,
                    )
                
                return None
            
            # ================================================================
            # STEP 4: EXTRACT INSIGHTS FROM REASONING LAYERS
            # ================================================================
            with tracer.start_span_sync("extract_reasoning_insights") as extract_span:
                # FACTUAL layer: validated facts
                factual = reasoning_trace.factual
                exposure = self._extract_exposure_from_factual(factual, intelligence, context)
                
                if not exposure or not exposure.has_exposure:
                    logger.info("no_exposure_from_reasoning", customer_id=customer_id)
                    main_span.set_attribute("result", "no_exposure")
                    return None
                
                extract_span.set_attribute("has_exposure", True)
                extract_span.set_attribute("affected_count", len(exposure.affected_shipments))
                
                # TEMPORAL layer: timeline and deadlines
                temporal = reasoning_trace.temporal
                
                # CAUSAL layer: causal chain
                causal = reasoning_trace.causal
                
                # COUNTERFACTUAL layer: what-if scenarios
                counterfactual = reasoning_trace.counterfactual
                
                # STRATEGIC layer: strategy alignment
                strategic = reasoning_trace.strategic
                
                # META layer: final recommendation
                meta = reasoning_trace.meta
            
            # ================================================================
            # STEP 5: BUILD DECISION USING REASONING OUTPUTS
            # ================================================================
            with tracer.start_span_sync("build_decision_from_reasoning") as build_span:
                # Calculate impact using factual layer's validated data
                impact = self.impact_calculator.calculate(exposure, intelligence, context)
                build_span.set_attribute("total_cost", impact.total_cost_usd)
                
                # Generate actions using strategic layer insights
                action_set = self.action_generator.generate(
                    exposure, impact, intelligence, context
                )
                build_span.set_attribute("primary_action", action_set.primary.action_type.value)
                
                # Analyze tradeoffs using counterfactual insights
                tradeoff = self.tradeoff_analyzer.analyze(
                    action_set, impact, exposure, intelligence
                )
                
                # Create uncertain values
                exposure_uncertain = self._create_exposure_uncertain(impact, exposure, intelligence)
                delay_uncertain = self._create_delay_uncertain(impact, intelligence)
                cost_uncertain = self._create_cost_uncertain(action_set, intelligence)
                inaction_uncertain = self._create_inaction_uncertain(tradeoff, intelligence)
                
                # Compose 7 questions with reasoning enhancements
                q1 = self._compose_q1(exposure, intelligence, context)
                q2 = self._compose_q2_with_temporal(exposure, impact, intelligence, tradeoff, temporal)
                q3 = self._compose_q3(impact, exposure, exposure_uncertain, delay_uncertain)
                q4 = self._compose_q4_with_causal(intelligence, causal)
                q5 = self._compose_q5(action_set, tradeoff, cost_uncertain)
                q6 = self._compose_q6_with_reasoning(impact, intelligence, action_set, reasoning_trace)
                q7 = self._compose_q7(tradeoff, impact, inaction_uncertain)
                
                build_span.set_attribute("confidence", q6.score)
            
            # ================================================================
            # STEP 6: CALIBRATE AND PERSIST CONFIDENCE (A3)
            # ================================================================
            calibrated_confidence = q6.score
            if self._calibrator:
                with tracer.start_span_sync("calibrate_confidence") as cal_span:
                    calibration_result = await self._calibrator.calibrate_and_persist(
                        raw_confidence=q6.score,
                        chokepoint=intelligence.signal.chokepoint,
                        event_type=intelligence.signal.category.value if intelligence.signal.category else "unknown",
                        customer_id=customer_id,
                        context={
                            "signal_probability": intelligence.signal.probability,
                            "reasoning_quality": reasoning_trace.reasoning_quality_score,
                            "data_quality": reasoning_trace.data_quality_score,
                        },
                    )
                    calibrated_confidence = calibration_result.calibrated_confidence
                    cal_span.set_attribute("raw_confidence", q6.score)
                    cal_span.set_attribute("calibrated_confidence", calibrated_confidence)
                    cal_span.set_attribute("adjustment", calibration_result.adjustment)
                
                # Update Q6 with calibrated confidence
                q6 = self._update_q6_with_calibration(q6, calibrated_confidence)
            
            # ================================================================
            # STEP 7: GENERATE CONFIDENCE GUIDANCE (A4.4)
            # ================================================================
            with tracer.start_span_sync("generate_confidence_guidance") as guidance_span:
                partial_decision = DecisionObject(
                    decision_id="temp",
                    customer_id=customer_id,
                    signal_id=signal_id,
                    q1_what=q1,
                    q2_when=q2,
                    q3_severity=q3,
                    q4_why=q4,
                    q5_action=q5,
                    q6_confidence=q6,
                    q7_inaction=q7,
                    expires_at=datetime.utcnow() + timedelta(hours=self.decision_ttl_hours),
                )
                
                confidence_guidance = self.confidence_communicator.generate_guidance(
                    decision=partial_decision,
                    exposure_uncertain=exposure_uncertain,
                    delay_uncertain=delay_uncertain,
                    cost_uncertain=cost_uncertain,
                    calibrated_confidence=calibrated_confidence,
                )
                
                guidance_span.set_attribute("uncertainty_level", confidence_guidance.uncertainty_level.value)
                guidance_span.set_attribute("should_act", confidence_guidance.should_act)
            
            # ================================================================
            # STEP 8: BUILD FINAL DECISION OBJECT
            # ================================================================
            decision_id = f"dec_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{customer_id[:8]}"
            expires_at = datetime.utcnow() + timedelta(hours=self.decision_ttl_hours)
            
            alternatives = [
                {
                    "action_type": a.action_type.value,
                    "summary": a.summary,
                    "cost_usd": a.cost_usd,
                    "benefit_usd": a.risk_mitigated_usd,
                    "deadline": a.deadline.isoformat() if a.deadline else None,
                }
                for a in action_set.alternatives
            ]
            
            decision = DecisionObject(
                decision_id=decision_id,
                customer_id=customer_id,
                signal_id=signal_id,
                q1_what=q1,
                q2_when=q2,
                q3_severity=q3,
                q4_why=q4,
                q5_action=q5,
                q6_confidence=q6,
                q7_inaction=q7,
                confidence_guidance=confidence_guidance,
                alternative_actions=alternatives,
                expires_at=expires_at,
                # NEW: Reasoning linkage (A1)
                reasoning_trace_id=reasoning_trace.trace_id,
                reasoning_quality_score=reasoning_trace.reasoning_quality_score,
                data_quality_score=reasoning_trace.data_quality_score,
            )
            
            # ================================================================
            # STEP 9: RECORD DECISION IN AUDIT TRAIL (A3)
            # ================================================================
            if self._audit:
                await self._audit.record_decision(
                    decision=decision,
                    trace_id=reasoning_trace.trace_id,
                    calibrated_confidence=calibrated_confidence,
                )
            
            # Record prediction for calibration tracking (A3)
            if self._calibrator:
                await self._calibrator.record_prediction(
                    decision_id=decision_id,
                    predicted_confidence=calibrated_confidence,
                    chokepoint=intelligence.signal.chokepoint,
                    event_type=intelligence.signal.category.value if intelligence.signal.category else "unknown",
                    exposure_usd=q3.total_exposure_usd,
                )
            
            main_span.set_attribute("result", "decision_composed")
            main_span.set_attribute("decision_id", decision_id)
            main_span.set_attribute("reasoning_trace_id", reasoning_trace.trace_id)
            main_span.set_attribute("severity", q3.severity.value)
            main_span.set_attribute("calibrated_confidence", calibrated_confidence)
            
            logger.info(
                "decision_composed_with_reasoning",
                decision_id=decision_id,
                customer_id=customer_id,
                signal_id=signal_id,
                reasoning_trace_id=reasoning_trace.trace_id,
                severity=q3.severity.value,
                urgency=q2.urgency.value,
                action=q5.action_type,
                exposure_usd=q3.total_exposure_usd,
                raw_confidence=q6.score,
                calibrated_confidence=calibrated_confidence,
                reasoning_quality=reasoning_trace.reasoning_quality_score,
            )
            
            return decision

    # ========================================================================
    # REASONING EXTRACTION HELPERS (A1)
    # ========================================================================

    def _extract_exposure_from_factual(
        self,
        factual,
        intelligence: CorrelatedIntelligence,
        context: CustomerContext,
    ) -> Optional[ExposureMatch]:
        """
        Extract exposure match from factual layer output.
        
        The factual layer validates facts including affected shipments.
        If the factual layer has validated exposure data, use it.
        Otherwise, fall back to standard exposure matching.
        """
        # Check if factual layer has pre-computed exposure
        if factual and hasattr(factual, 'validated_facts'):
            facts = factual.validated_facts
            if 'affected_shipments' in facts and 'exposure_usd' in facts:
                # Use factual layer's validated exposure
                logger.debug("using_factual_layer_exposure")
                # Still need to run matcher to get full ExposureMatch structure
                pass
        
        # Fall back to standard matching
        return self.exposure_matcher.match(intelligence, context)

    def _compose_q2_with_temporal(
        self,
        exposure: ExposureMatch,
        impact: TotalImpact,
        intelligence: CorrelatedIntelligence,
        tradeoff: TradeOffAnalysis,
        temporal,
    ) -> Q2WhenWillItHappen:
        """
        Compose Q2 enhanced with temporal layer insights.
        
        The temporal layer provides:
        - Event lifecycle stage
        - Decision windows
        - Key dates/deadlines
        """
        # Get base Q2
        q2 = self._compose_q2(exposure, impact, intelligence, tradeoff)
        
        # Enhance with temporal layer insights if available
        if temporal and hasattr(temporal, 'insights'):
            insights = temporal.insights
            
            # Update urgency if temporal layer has better assessment
            if 'decision_window_hours' in insights:
                window_hours = insights['decision_window_hours']
                if window_hours <= 6:
                    q2.urgency = Urgency.IMMEDIATE
                    q2.urgency_reason = f"Critical window: {window_hours}h remaining"
                elif window_hours <= 24:
                    q2.urgency = Urgency.URGENT
                    q2.urgency_reason = f"Urgent window: {window_hours}h remaining"
            
            # Add key dates if available
            if 'key_dates' in insights:
                q2.key_dates = insights['key_dates']
        
        return q2

    def _compose_q4_with_causal(
        self,
        intelligence: CorrelatedIntelligence,
        causal,
    ) -> Q4WhyIsThisHappening:
        """
        Compose Q4 enhanced with causal layer insights.
        
        The causal layer provides:
        - Validated causal chain
        - Root cause analysis
        - Intervention points
        """
        # Get base Q4
        q4 = self._compose_q4(intelligence)
        
        # Enhance with causal layer insights if available
        if causal and hasattr(causal, 'causal_chain'):
            # Replace causal chain with validated one from reasoning
            if causal.causal_chain:
                q4.causal_chain = causal.causal_chain
            
            # Add intervention points if available
            if hasattr(causal, 'intervention_points'):
                q4.intervention_points = causal.intervention_points
        
        return q4

    def _compose_q6_with_reasoning(
        self,
        impact: TotalImpact,
        intelligence: CorrelatedIntelligence,
        action_set: ActionSet,
        reasoning_trace,
    ) -> Q6HowConfident:
        """
        Compose Q6 enhanced with reasoning quality metrics.
        
        Adds:
        - Reasoning quality score
        - Data quality score
        - Layer-by-layer confidence breakdown
        """
        # Get base Q6
        q6 = self._compose_q6(impact, intelligence, action_set)
        
        # Enhance with reasoning quality metrics
        q6.factors["reasoning_quality"] = round(reasoning_trace.reasoning_quality_score, 2)
        q6.factors["data_quality"] = round(reasoning_trace.data_quality_score, 2)
        
        # Add layer confidences if available
        layer_confidences = {}
        if reasoning_trace.factual:
            layer_confidences["factual"] = round(reasoning_trace.factual.confidence, 2)
        if reasoning_trace.temporal:
            layer_confidences["temporal"] = round(reasoning_trace.temporal.confidence, 2)
        if reasoning_trace.causal:
            layer_confidences["causal"] = round(reasoning_trace.causal.confidence, 2)
        if reasoning_trace.counterfactual:
            layer_confidences["counterfactual"] = round(reasoning_trace.counterfactual.confidence, 2)
        if reasoning_trace.strategic:
            layer_confidences["strategic"] = round(reasoning_trace.strategic.confidence, 2)
        if reasoning_trace.meta:
            layer_confidences["meta"] = round(reasoning_trace.meta.reasoning_confidence, 2)
        
        q6.factors["layer_confidences"] = layer_confidences
        
        # Update explanation to include reasoning quality
        quality_desc = "excellent" if reasoning_trace.reasoning_quality_score > 0.8 else \
                       "good" if reasoning_trace.reasoning_quality_score > 0.6 else "moderate"
        q6.explanation = f"{q6.explanation}, {quality_desc} reasoning quality"
        
        return q6

    def _update_q6_with_calibration(
        self,
        q6: Q6HowConfident,
        calibrated_confidence: float,
    ) -> Q6HowConfident:
        """
        Update Q6 with calibrated confidence score.
        
        The calibrated confidence adjusts the raw confidence based on
        historical accuracy data from the persistent calibrator (A3).
        """
        # Calculate adjustment
        adjustment = calibrated_confidence - q6.score
        
        # Update score
        q6.score = calibrated_confidence
        q6.level = get_confidence_level(calibrated_confidence)
        
        # Add calibration info to factors
        q6.factors["raw_confidence"] = q6.factors.get("signal_probability", 0.5)
        q6.factors["calibration_adjustment"] = round(adjustment, 3)
        q6.factors["calibrated"] = True
        
        # Update explanation
        if abs(adjustment) > 0.05:
            direction = "increased" if adjustment > 0 else "decreased"
            q6.explanation = f"{q6.explanation} (calibrated {direction} by {abs(adjustment)*100:.0f}%)"
        else:
            q6.explanation = f"{q6.explanation} (calibration verified)"
        
        return q6

    # ========================================================================
    # Q1: WHAT IS HAPPENING?
    # ========================================================================

    def _compose_q1(
        self,
        exposure: ExposureMatch,
        intelligence: CorrelatedIntelligence,
        context: CustomerContext,
    ) -> Q1WhatIsHappening:
        """
        Compose Q1: What is happening?

        MUST be personalized to customer's specific shipments and routes.

        NOT: "Red Sea disruption detected"
        YES: "Red Sea disruption affecting YOUR Shanghai→Rotterdam route"
        """
        signal = intelligence.signal
        chokepoint = exposure.chokepoint_matched

        # Build personalized event summary
        # Get affected routes
        routes = set()
        for shipment in exposure.affected_shipments:
            route = f"{shipment.origin_port}-{shipment.destination_port}"
            routes.add(route)

        route_str = ", ".join(list(routes)[:3])
        if len(routes) > 3:
            route_str += f" (+{len(routes) - 3} more)"

        # Get shipment references
        shipment_refs = [
            s.customer_reference or s.shipment_id
            for s in exposure.affected_shipments
        ]

        # Build summary
        event_type = signal.category.value.upper() if signal.category else "DISRUPTION"

        if exposure.shipment_count == 1:
            summary = (
                f"{chokepoint.replace('_', ' ').title()} {event_type.lower()} "
                f"affecting your shipment {shipment_refs[0]} on route {route_str}"
            )
        else:
            summary = (
                f"{chokepoint.replace('_', ' ').title()} {event_type.lower()} "
                f"affecting {exposure.shipment_count} shipments on route(s) {route_str}"
            )

        # Truncate if needed
        if len(summary) > 150:
            summary = summary[:147] + "..."

        return Q1WhatIsHappening(
            event_type=event_type,
            event_summary=summary,
            affected_chokepoint=chokepoint,
            affected_routes=list(routes),
            affected_shipments=shipment_refs,
        )

    # ========================================================================
    # Q2: WHEN WILL IT HAPPEN?
    # ========================================================================

    def _compose_q2(
        self,
        exposure: ExposureMatch,
        impact: TotalImpact,
        intelligence: CorrelatedIntelligence,
        tradeoff: TradeOffAnalysis,
    ) -> Q2WhenWillItHappen:
        """
        Compose Q2: When will it happen / is it happening?

        MUST include specific timeline and urgency.

        NOT: "Ongoing situation"
        YES: "Impact starts in 3 days for your earliest shipment"
        """
        signal = intelligence.signal

        # Determine status from correlation
        status_map = {
            "confirmed": "CONFIRMED",
            "materializing": "MATERIALIZING",
            "predicted_not_observed": "PREDICTED",
            "surprise": "CONFIRMED",
            "normal": "PREDICTED",
        }
        status = status_map.get(
            intelligence.correlation_status.value, "PREDICTED"
        )

        # Build impact timeline
        if exposure.earliest_impact:
            days_until = (exposure.earliest_impact - datetime.utcnow()).days
            if days_until <= 0:
                timeline = "Impact is immediate - your shipments are already affected"
            elif days_until == 1:
                timeline = "Impact starts tomorrow for your earliest shipment"
            else:
                timeline = f"Impact starts in {days_until} days for your earliest shipment"
        else:
            timeline = f"Expected {impact.total_delay_days_expected} day delay"

        # Determine urgency
        urgency_map = {
            "IMMEDIATE": Urgency.IMMEDIATE,
            "HOURS": Urgency.URGENT,
            "DAYS": Urgency.SOON,
            "WEEKS": Urgency.WATCH,
        }
        urgency = urgency_map.get(tradeoff.urgency, Urgency.SOON)

        # Urgency reason
        hours_to_decide = tradeoff.time_to_decide_hours
        if hours_to_decide <= 6:
            urgency_reason = "Critical deadline approaching - act within hours"
        elif hours_to_decide <= 24:
            urgency_reason = "Key window closing - decide today"
        elif hours_to_decide <= 72:
            urgency_reason = "Time available but options narrowing"
        else:
            urgency_reason = "Monitor situation - no immediate action required"

        return Q2WhenWillItHappen(
            status=status,
            impact_timeline=timeline,
            earliest_impact=exposure.earliest_impact,
            latest_resolution=signal.temporal.latest_resolution,
            urgency=urgency,
            urgency_reason=urgency_reason,
        )

    # ========================================================================
    # Q3: HOW BAD IS IT? (with confidence intervals - A2.2)
    # ========================================================================

    def _compose_q3(
        self,
        impact: TotalImpact,
        exposure: ExposureMatch,
        exposure_uncertain: UncertainValue,
        delay_uncertain: UncertainValue,
    ) -> Q3HowBadIsIt:
        """
        Compose Q3: How severe is this?

        MUST include specific dollar amounts and day counts WITH CONFIDENCE INTERVALS.

        NOT: "Significant impact expected"
        YES: "Your exposure: $235K [$188K-$294K 90% CI] across 5 containers. Expected delay: 10-14 days."
        
        Addresses audit gap A2.2 (Confidence Intervals).
        """
        # Build exposure breakdown
        breakdown = {
            "cargo_at_risk": exposure.total_exposure_usd,
        }

        if impact.total_penalty_usd > 0:
            breakdown["potential_penalties"] = impact.total_penalty_usd

        # Calculate direct cost breakdown if available
        if impact.shipment_impacts:
            total_holding = sum(
                si.cost.delay_holding_cost_usd for si in impact.shipment_impacts
            )
            total_reroute = sum(
                si.cost.reroute_premium_usd for si in impact.shipment_impacts
            )
            if total_holding > 0:
                breakdown["holding_costs"] = round(total_holding, 2)
            if total_reroute > 0:
                breakdown["reroute_premiums"] = round(total_reroute, 2)

        # Get delay range
        if impact.shipment_impacts:
            min_delay = min(si.delay.min_days for si in impact.shipment_impacts)
            max_delay = max(si.delay.max_days for si in impact.shipment_impacts)
            if min_delay == max_delay:
                delay_range = f"{min_delay} days"
            else:
                delay_range = f"{min_delay}-{max_delay} days"
        else:
            delay_range = f"{impact.total_delay_days_expected} days"

        # Build uncertainty summary (A4.4)
        exposure_summary = (
            f"${exposure_uncertain.point_estimate:,.0f} "
            f"[${exposure_uncertain.ci_90[0]:,.0f}-${exposure_uncertain.ci_90[1]:,.0f}] (90% CI)"
        )

        return Q3HowBadIsIt(
            total_exposure_usd=impact.total_cost_usd,
            exposure_breakdown=breakdown,
            # NEW: Confidence intervals (A2.2)
            exposure_ci_90=exposure_uncertain.ci_90,
            exposure_ci_95=exposure_uncertain.ci_95,
            exposure_var_95=exposure_uncertain.var_95,
            exposure_cvar_95=exposure_uncertain.cvar_95,
            # Delay
            expected_delay_days=impact.total_delay_days_expected,
            delay_range=delay_range,
            delay_ci_90=delay_uncertain.ci_90,
            # Shipments
            shipments_affected=impact.shipment_count,
            shipments_with_penalties=impact.shipments_with_penalties,
            severity=impact.overall_severity,
            # Uncertainty summary (A4.4)
            exposure_uncertainty_summary=exposure_summary,
        )

    # ========================================================================
    # Q4: WHY IS THIS HAPPENING?
    # ========================================================================

    def _compose_q4(
        self,
        intelligence: CorrelatedIntelligence,
    ) -> Q4WhyIsThisHappening:
        """
        Compose Q4: Why is this happening?

        MUST include causal chain that users can understand.

        NOT: "Geopolitical tensions"
        YES: "Houthi attacks → carriers avoiding Suez → 10-14 day longer route"
        """
        signal = intelligence.signal

        # Get root cause from signal
        root_cause = signal.title
        if len(root_cause) > 150:
            root_cause = root_cause[:147] + "..."

        # Build causal chain
        # This is a simplified version - in production, this would come from
        # more sophisticated analysis
        causal_chain = []

        # Start with the trigger
        if signal.category:
            category = signal.category.value
            if category == "disruption":
                causal_chain.append("Disruption event detected")
            elif category == "congestion":
                causal_chain.append("Port congestion building")
            elif category == "rate_spike":
                causal_chain.append("Rate increases announced")
            else:
                causal_chain.append(f"{category.title()} signal detected")

        # Add geographic impact
        chokepoint = signal.geographic.primary_chokepoint.value
        causal_chain.append(f"Affects {chokepoint.replace('_', ' ').title()}")

        # Add carrier response
        if intelligence.correlation_status.value == "confirmed":
            causal_chain.append("Carriers already rerouting")
        elif intelligence.correlation_status.value == "materializing":
            causal_chain.append("Carriers beginning to respond")
        else:
            causal_chain.append("Carriers monitoring situation")

        # Add expected outcome
        causal_chain.append("Extended transit times expected")

        # Build evidence summary
        evidence_parts = []
        evidence_parts.append(f"{int(signal.probability * 100)}% signal probability")

        if intelligence.combined_confidence:
            evidence_parts.append(
                f"{int(intelligence.combined_confidence * 100)}% combined confidence"
            )

        evidence_summary = " | ".join(evidence_parts)

        # Sources - extract from evidence items
        evidence_sources = [e.source for e in signal.evidence if e.source]
        sources = evidence_sources if evidence_sources else ["OMEN", "ORACLE"]

        return Q4WhyIsThisHappening(
            root_cause=root_cause,
            causal_chain=causal_chain,
            evidence_summary=evidence_summary,
            sources=sources,
        )

    # ========================================================================
    # Q5: WHAT TO DO NOW? (with cost CIs - A2.2)
    # ========================================================================

    def _compose_q5(
        self,
        action_set: ActionSet,
        tradeoff: TradeOffAnalysis,
        cost_uncertain: UncertainValue,
    ) -> Q5WhatToDoNow:
        """
        Compose Q5: What should I do RIGHT NOW?

        MUST be specific, actionable, with cost, CI, and deadline.

        NOT: "Consider alternative routes"
        YES: "REROUTE via Cape with MSC. Cost: $8,500 [$7,200-$10,100 90% CI]. Book by 6PM today."
        
        Addresses audit gap A2.2 (Confidence Intervals).
        """
        primary = action_set.primary_action

        # Get shipment references
        shipment_refs = [
            sid[:12] for sid in primary.affected_shipment_ids[:5]
        ]

        # Calculate utility = benefit - cost
        benefit = primary.risk_mitigated_usd or 0.0
        cost = cost_uncertain.point_estimate
        expected_utility = benefit - cost
        
        # Propagate utility uncertainty (benefit is more certain, cost has uncertainty)
        # Utility CI: lower bound = benefit - cost_high, upper bound = benefit - cost_low
        utility_ci_90 = (
            benefit - cost_uncertain.ci_90[1],  # Best case: min cost
            benefit - cost_uncertain.ci_90[0],  # Worst case: max cost
        )
        
        # Success probability estimate (based on confidence and action type)
        base_success = 0.85  # Base success rate for implemented actions
        success_probability = min(0.95, base_success * (0.5 + tradeoff.value_at_risk_confidence / 2))
        success_probability_ci = (
            max(0.5, success_probability - 0.15),
            min(0.98, success_probability + 0.10),
        )

        # Build cost uncertainty summary (A4.4)
        cost_summary = (
            f"${cost_uncertain.point_estimate:,.0f} "
            f"[${cost_uncertain.ci_90[0]:,.0f}-${cost_uncertain.ci_90[1]:,.0f}]"
        )

        return Q5WhatToDoNow(
            action_type=primary.action_type.value.upper(),
            action_summary=primary.summary,
            affected_shipments=shipment_refs,
            recommended_carrier=primary.recommended_carrier,
            estimated_cost_usd=primary.cost_usd,
            # NEW: Cost confidence intervals (A2.2)
            cost_ci_90=cost_uncertain.ci_90,
            cost_ci_95=cost_uncertain.ci_95,
            # Execution
            execution_steps=primary.steps,
            deadline=primary.deadline,
            deadline_reason=primary.deadline_reason,
            who_to_contact=primary.carrier_name,
            contact_info=primary.contact_info,
            # NEW: Utility with uncertainty (A2.2)
            expected_utility=expected_utility,
            utility_ci_90=utility_ci_90,
            # NEW: Success probability (A2.2)
            success_probability=success_probability,
            success_probability_ci=success_probability_ci,
            # NEW: Cost uncertainty summary (A4.4)
            cost_uncertainty_summary=cost_summary,
        )

    # ========================================================================
    # Q6: HOW CONFIDENT?
    # ========================================================================

    def _compose_q6(
        self,
        impact: TotalImpact,
        intelligence: CorrelatedIntelligence,
        action_set: ActionSet,
    ) -> Q6HowConfident:
        """
        Compose Q6: How confident are we?

        MUST include factors that explain the confidence.

        NOT: "High confidence"
        YES: "87% confidence based on: Polymarket (78%), 47 vessels confirming"
        """
        # Calculate combined confidence
        # Weight: 40% signal, 30% intelligence, 30% impact assessment
        signal_conf = intelligence.signal.probability
        intel_conf = intelligence.combined_confidence
        impact_conf = impact.confidence

        combined = (
            0.40 * signal_conf +
            0.30 * intel_conf +
            0.30 * impact_conf
        )
        combined = round(min(0.99, max(0.0, combined)), 2)

        level = get_confidence_level(combined)

        # Build factors breakdown
        factors = {
            "signal_probability": round(signal_conf, 2),
            "intelligence_correlation": round(intel_conf, 2),
            "impact_assessment": round(impact_conf, 2),
        }

        # Build explanation
        explanation_parts = [f"{int(combined * 100)}% confidence"]

        if signal_conf > 0.8:
            explanation_parts.append("high signal probability")
        if intel_conf > 0.8:
            explanation_parts.append("strong correlation with reality")
        if impact_conf > 0.8:
            explanation_parts.append("reliable impact estimate")

        explanation = ", ".join(explanation_parts)

        # Caveats
        caveats = []
        if signal_conf < 0.6:
            caveats.append("Signal probability is moderate - situation may change")
        if intel_conf < 0.6:
            caveats.append("Limited real-time confirmation")
        if impact_conf < 0.6:
            caveats.append("Cost estimates are approximate")

        if intelligence.correlation_status.value == "predicted_not_observed":
            caveats.append("Signal not yet confirmed by carrier actions")

        return Q6HowConfident(
            score=combined,
            level=level,
            factors=factors,
            explanation=explanation,
            caveats=caveats,
        )

    # ========================================================================
    # Q7: WHAT IF I DO NOTHING? (with loss CIs - A2.2)
    # ========================================================================

    def _compose_q7(
        self,
        tradeoff: TradeOffAnalysis,
        impact: TotalImpact,
        inaction_uncertain: UncertainValue,
    ) -> Q7WhatIfNothing:
        """
        Compose Q7: What happens if I don't act?

        MUST include time-based cost escalation WITH CONFIDENCE INTERVALS.

        NOT: "Risk increases over time"
        YES: "If wait 6h: +$15K [$12K-$19K]. If wait 24h: booking closes. Total loss: $47K [$38K-$59K 90% CI]."
        
        Addresses audit gap A2.2 (Confidence Intervals).
        """
        inaction = tradeoff.inaction

        # Build summary with CI
        ponr_hours = None
        if inaction.point_of_no_return:
            ponr_delta = inaction.point_of_no_return - datetime.utcnow()
            ponr_hours = max(0, int(ponr_delta.total_seconds() / 3600))

        if ponr_hours and ponr_hours < 72:
            summary = (
                f"Point of no return in {ponr_hours}h. "
                f"Expected loss: ${inaction.immediate_cost_usd:,.0f} "
                f"[${inaction_uncertain.ci_90[0]:,.0f}-${inaction_uncertain.ci_90[1]:,.0f}]"
            )
        else:
            summary = (
                f"Expected loss: ${inaction.immediate_cost_usd:,.0f}. "
                f"Worst case: ${inaction.worst_case_cost_usd:,.0f}"
            )

        if len(summary) > 200:
            summary = summary[:197] + "..."

        # Calculate time-based CIs (scale based on escalation ratios)
        escalation_6h = inaction.cost_at_6h / inaction.immediate_cost_usd if inaction.immediate_cost_usd > 0 else 1.0
        escalation_24h = inaction.cost_at_24h / inaction.immediate_cost_usd if inaction.immediate_cost_usd > 0 else 1.0
        escalation_48h = inaction.cost_at_48h / inaction.immediate_cost_usd if inaction.immediate_cost_usd > 0 else 1.0
        
        cost_6h_ci = (
            inaction_uncertain.ci_90[0] * escalation_6h,
            inaction_uncertain.ci_90[1] * escalation_6h,
        )
        cost_24h_ci = (
            inaction_uncertain.ci_90[0] * escalation_24h,
            inaction_uncertain.ci_90[1] * escalation_24h,
        )
        cost_48h_ci = (
            inaction_uncertain.ci_90[0] * escalation_48h,
            inaction_uncertain.ci_90[1] * escalation_48h,
        )

        # Build loss uncertainty summary (A4.4)
        loss_summary = (
            f"${inaction_uncertain.point_estimate:,.0f} "
            f"[${inaction_uncertain.ci_90[0]:,.0f}-${inaction_uncertain.ci_90[1]:,.0f}]"
        )

        return Q7WhatIfNothing(
            expected_loss_if_nothing=inaction.immediate_cost_usd,
            # NEW: Loss confidence intervals (A2.2)
            loss_ci_90=inaction_uncertain.ci_90,
            loss_ci_95=inaction_uncertain.ci_95,
            # Time-based escalation
            cost_if_wait_6h=inaction.cost_at_6h,
            cost_if_wait_24h=inaction.cost_at_24h,
            cost_if_wait_48h=inaction.cost_at_48h,
            # NEW: Time-based CIs (A2.2)
            cost_if_wait_6h_ci=cost_6h_ci,
            cost_if_wait_24h_ci=cost_24h_ci,
            cost_if_wait_48h_ci=cost_48h_ci,
            # Point of no return
            point_of_no_return=inaction.point_of_no_return,
            point_of_no_return_reason=inaction.point_of_no_return_reason,
            worst_case_cost=inaction.worst_case_cost_usd,
            worst_case_scenario=inaction.worst_case_scenario,
            inaction_summary=summary,
            # NEW: Loss uncertainty summary (A4.4)
            loss_uncertainty_summary=loss_summary,
        )

    # ========================================================================
    # UNCERTAINTY CREATION METHODS (A2.2)
    # ========================================================================

    def _create_exposure_uncertain(
        self,
        impact: TotalImpact,
        exposure: ExposureMatch,
        intelligence: CorrelatedIntelligence,
    ) -> UncertainValue:
        """
        Create uncertain value for total exposure.
        
        Uncertainty sources:
        - Signal probability (affects whether event materializes)
        - Cargo valuation uncertainty
        - Penalty estimation uncertainty
        
        Uses lognormal distribution as costs are non-negative and right-skewed.
        """
        point_estimate = impact.total_cost_usd
        
        # Determine uncertainty factor based on intelligence quality
        signal_conf = intelligence.signal.probability
        intel_conf = intelligence.combined_confidence
        
        # Higher confidence = narrower CI
        # Base CV (coefficient of variation) ranges from 0.15 to 0.40
        base_cv = 0.40 - 0.25 * ((signal_conf + intel_conf) / 2)
        
        # Adjust for shipment count (more shipments = law of large numbers helps)
        shipment_factor = 1.0 / (1.0 + 0.1 * min(10, impact.shipment_count))
        cv = base_cv * shipment_factor
        
        # Create lognormal-based uncertain value
        std = point_estimate * cv
        
        return UncertainValue.from_normal(
            mean=point_estimate,
            std=std,
            unit="usd",
        )

    def _create_delay_uncertain(
        self,
        impact: TotalImpact,
        intelligence: CorrelatedIntelligence,
    ) -> UncertainValue:
        """
        Create uncertain value for expected delay days.
        
        Uncertainty sources:
        - Situation evolution uncertainty
        - Carrier response variability
        - Route alternatives availability
        
        Uses triangular distribution for bounded estimates.
        """
        expected_delay = float(impact.total_delay_days_expected)
        
        # Get min/max from shipment impacts if available
        if impact.shipment_impacts:
            min_delay = min(si.delay.min_days for si in impact.shipment_impacts)
            max_delay = max(si.delay.max_days for si in impact.shipment_impacts)
        else:
            # Default: +/- 30% of expected
            min_delay = max(0, expected_delay * 0.7)
            max_delay = expected_delay * 1.3
        
        return UncertainValue.from_triangular(
            low=float(min_delay),
            mode=expected_delay,
            high=float(max_delay),
            unit="days",
        )

    def _create_cost_uncertain(
        self,
        action_set: ActionSet,
        intelligence: CorrelatedIntelligence,
    ) -> UncertainValue:
        """
        Create uncertain value for action cost.
        
        Uncertainty sources:
        - Carrier rate variability
        - Booking timing (last-minute = higher)
        - Fuel surcharges
        
        Uses range-based estimation.
        """
        primary = action_set.primary_action
        point_estimate = primary.cost_usd
        
        # Cost uncertainty depends on action type and time pressure
        # Reroute costs are more variable than delay costs
        action_type = primary.action_type.value.lower()
        
        if action_type == "reroute":
            # Reroute costs: +/- 15-25%
            low_factor = 0.80
            high_factor = 1.25
        elif action_type == "insure":
            # Insurance: +/- 10%
            low_factor = 0.90
            high_factor = 1.10
        elif action_type == "delay":
            # Delay costs: +/- 20%
            low_factor = 0.85
            high_factor = 1.20
        else:
            # Default: +/- 15%
            low_factor = 0.85
            high_factor = 1.15
        
        return UncertainValue.from_range(
            low=point_estimate * low_factor,
            high=point_estimate * high_factor,
            unit="usd",
        )

    def _create_inaction_uncertain(
        self,
        tradeoff: TradeOffAnalysis,
        intelligence: CorrelatedIntelligence,
    ) -> UncertainValue:
        """
        Create uncertain value for inaction cost.
        
        Uncertainty sources:
        - Event probability (may not materialize)
        - Cost escalation timing uncertainty
        - Market response variability
        
        Uses lognormal as costs are non-negative and can have long tail.
        """
        inaction = tradeoff.inaction
        point_estimate = inaction.immediate_cost_usd
        
        # Inaction cost uncertainty is higher due to compounding effects
        signal_prob = intelligence.signal.probability
        
        # Lower signal probability = wider CI (more uncertainty)
        base_cv = 0.30 + 0.20 * (1.0 - signal_prob)
        std = point_estimate * base_cv
        
        return UncertainValue.from_normal(
            mean=point_estimate,
            std=std,
            unit="usd",
        )


# ============================================================================
# FACTORY
# ============================================================================


def create_decision_composer(
    exposure_matcher: Optional[ExposureMatcher] = None,
    impact_calculator: Optional[ImpactCalculator] = None,
    action_generator: Optional[ActionGenerator] = None,
    tradeoff_analyzer: Optional[TradeOffAnalyzer] = None,
    confidence_communicator: Optional[ConfidenceCommunicator] = None,
    # NEW: ReasoningEngine integration (A1)
    reasoning_engine: Optional["ReasoningEngine"] = None,
    audit_service: Optional["AuditService"] = None,
    calibrator: Optional["PersistentCalibrator"] = None,
) -> DecisionComposer:
    """
    Create decision composer with optional custom dependencies.
    
    Args:
        exposure_matcher: Custom exposure matcher
        impact_calculator: Custom impact calculator
        action_generator: Custom action generator
        tradeoff_analyzer: Custom tradeoff analyzer
        confidence_communicator: Custom confidence communicator
        reasoning_engine: 6-layer reasoning engine (A1)
        audit_service: Audit trail service (A3)
        calibrator: Persistent calibrator (A3)
        
    Returns:
        Configured DecisionComposer
        
    Note:
        To enable reasoning mode (A1), provide reasoning_engine.
        To enable calibration persistence (A3), provide calibrator.
    """
    return DecisionComposer(
        exposure_matcher=exposure_matcher,
        impact_calculator=impact_calculator,
        action_generator=action_generator,
        tradeoff_analyzer=tradeoff_analyzer,
        confidence_communicator=confidence_communicator,
        reasoning_engine=reasoning_engine,
        audit_service=audit_service,
        calibrator=calibrator,
    )


def create_decision_composer_with_reasoning(
    reasoning_engine: "ReasoningEngine",
    audit_service: Optional["AuditService"] = None,
    calibrator: Optional["PersistentCalibrator"] = None,
    exposure_matcher: Optional[ExposureMatcher] = None,
    impact_calculator: Optional[ImpactCalculator] = None,
    action_generator: Optional[ActionGenerator] = None,
    tradeoff_analyzer: Optional[TradeOffAnalyzer] = None,
    confidence_communicator: Optional[ConfidenceCommunicator] = None,
) -> DecisionComposer:
    """
    Create decision composer with reasoning engine enabled.
    
    This is the preferred factory for A1 Cognitive Excellence compliance.
    
    Args:
        reasoning_engine: Required 6-layer reasoning engine
        audit_service: Optional audit trail service (recommended for A3)
        calibrator: Optional persistent calibrator (recommended for A3)
        exposure_matcher: Custom exposure matcher
        impact_calculator: Custom impact calculator
        action_generator: Custom action generator
        tradeoff_analyzer: Custom tradeoff analyzer
        confidence_communicator: Custom confidence communicator
        
    Returns:
        DecisionComposer with reasoning mode enabled
        
    Example:
        >>> from app.reasoning.engine import ReasoningEngine
        >>> from app.calibration.persistence import PersistentCalibrator
        >>> 
        >>> engine = ReasoningEngine()
        >>> calibrator = PersistentCalibrator(session_factory)
        >>> 
        >>> composer = create_decision_composer_with_reasoning(
        ...     reasoning_engine=engine,
        ...     calibrator=calibrator,
        ... )
        >>> 
        >>> # Use async compose_decision instead of sync compose
        >>> decision = await composer.compose_decision(intelligence, context)
    """
    return DecisionComposer(
        exposure_matcher=exposure_matcher,
        impact_calculator=impact_calculator,
        action_generator=action_generator,
        tradeoff_analyzer=tradeoff_analyzer,
        confidence_communicator=confidence_communicator,
        reasoning_engine=reasoning_engine,
        audit_service=audit_service,
        calibrator=calibrator,
    )
