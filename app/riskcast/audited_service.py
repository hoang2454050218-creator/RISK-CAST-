"""Audited RISKCAST Service - Decision engine with full audit trail.

This module wraps the AsyncRiskCastService with cryptographic audit capabilities.

EVERY DECISION must have:
1. Input snapshot BEFORE processing
2. Processing record of HOW it was computed
3. Decision record for WHAT was decided
4. Delivery record for HOW it was communicated
5. Outcome record for WHAT actually happened

A decision without an audit trail is not defensible.
"""

from datetime import datetime
from typing import Optional, List
import time

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.oracle.schemas import CorrelatedIntelligence
from app.audit import AuditService, AuditRepository, InputSnapshot, ProcessingRecord
from app.riskcast.service import (
    AsyncRiskCastService,
    create_async_riskcast_service,
)
from app.riskcast.repos.customer import PostgresCustomerRepository
from app.riskcast.repos.decision import create_decision_repository
from app.riskcast.composers import create_decision_composer
from app.riskcast.schemas.customer import CustomerContext
from app.riskcast.schemas.decision import DecisionObject
from app.common.exceptions import NoExposureError

# Metrics
from app.common.metrics import DECISIONS_GENERATED, DECISION_LATENCY, TOTAL_EXPOSURE

# Tracing
from app.core.tracing import get_tracer, get_current_trace_id, SpanKind

logger = structlog.get_logger(__name__)

# Version tracking for audit
MODEL_VERSION = "riskcast-v2.0.0"
CONFIG_VERSION = "config-v1.0.0"


class AuditedRiskCastService:
    """
    RISKCAST service with cryptographic audit trail.
    
    This is the PRODUCTION service that should be used for all decisions.
    It wraps the core AsyncRiskCastService with audit capabilities.
    
    Every decision generated through this service will have:
    - Immutable input snapshot (reproducibility)
    - Processing record (transparency)
    - Cryptographic chain (tamper detection)
    - Legal defensibility documentation
    """
    
    def __init__(
        self,
        session: AsyncSession,
        audit_service: AuditService,
        use_cache: bool = True,
    ):
        """
        Initialize audited RISKCAST service.
        
        Args:
            session: Async database session
            audit_service: Audit service for recording events
            use_cache: Whether to use Redis caching for decisions
        """
        self._session = session
        self._audit = audit_service
        self._customer_repo = PostgresCustomerRepository(session)
        self._decision_repo = create_decision_repository(session, use_cache=use_cache)
        self._composer = create_decision_composer()
        self._use_cache = use_cache
        
        logger.info(
            "audited_riskcast_service_initialized",
            use_cache=use_cache,
            model_version=MODEL_VERSION,
            config_version=CONFIG_VERSION,
        )
    
    # ========================================================================
    # AUDITED DECISION GENERATION
    # ========================================================================
    
    async def generate_decision(
        self,
        intelligence: CorrelatedIntelligence,
        context: CustomerContext,
    ) -> DecisionObject:
        """
        Generate a decision with full audit trail.
        
        This method:
        1. Captures immutable input snapshot
        2. Records processing metadata
        3. Generates the decision
        4. Creates audit record with cryptographic chain
        
        Args:
            intelligence: Correlated intelligence from ORACLE
            context: Customer context with profile and shipments
            
        Returns:
            DecisionObject with audit trail
            
        Raises:
            NoExposureError: If customer has no exposure
        """
        signal_id = intelligence.signal.signal_id
        customer_id = context.profile.customer_id
        chokepoint = intelligence.signal.geographic.primary_chokepoint.value
        
        # Start timing
        start_time = time.perf_counter()
        start_ts = datetime.utcnow()
        tracer = get_tracer()
        trace_id = get_current_trace_id()
        
        logger.info(
            "generating_audited_decision",
            signal_id=signal_id,
            customer_id=customer_id,
            chokepoint=chokepoint,
            trace_id=trace_id,
        )
        
        # ====================================================================
        # STEP 1: CAPTURE INPUT SNAPSHOT (BEFORE any processing)
        # ====================================================================
        input_snapshot = await self._audit.capture_inputs(
            signal=intelligence.signal,
            reality=intelligence,
            customer_context=context,
        )
        
        logger.debug(
            "input_snapshot_captured",
            snapshot_id=input_snapshot.snapshot_id,
            combined_hash=input_snapshot.combined_hash,
            customer_id=customer_id,
        )
        
        # ====================================================================
        # STEP 2: GENERATE DECISION
        # ====================================================================
        warnings: List[str] = []
        stale_sources: List[str] = []
        missing_sources: List[str] = []
        
        try:
            async with tracer.start_span(
                "riskcast.audited_generate_decision",
                kind=SpanKind.INTERNAL,
                attributes={
                    "signal_id": signal_id,
                    "customer_id": customer_id,
                    "chokepoint": chokepoint,
                    "snapshot_id": input_snapshot.snapshot_id,
                },
            ) as span:
                # Use the composer directly
                decision = self._composer.compose(intelligence, context)
                
                if not decision:
                    span.set_attribute("decision.no_exposure", True)
                    
                    # Still record the "no exposure" event for audit
                    await self._audit.record_decision(
                        decision_id=f"no_exposure_{customer_id}_{signal_id[:8]}",
                        customer_id=customer_id,
                        signal_id=signal_id,
                        input_snapshot_id=input_snapshot.snapshot_id,
                        processing_record_id=None,
                        decision_data={
                            "result": "no_exposure",
                            "reason": "No affected shipments found",
                        },
                        recommended_action="none",
                        confidence_score=1.0,  # Highly confident there's no exposure
                    )
                    
                    raise NoExposureError(
                        customer_id=customer_id,
                        signal_id=signal_id,
                        reason="No affected shipments found",
                    )
                
                # Calculate timing
                computation_time_ms = int((time.perf_counter() - start_time) * 1000)
                
                # ============================================================
                # STEP 3: CREATE PROCESSING RECORD
                # ============================================================
                processing_record = ProcessingRecord(
                    model_version=MODEL_VERSION,
                    config_version=CONFIG_VERSION,
                    layers_executed=[
                        "exposure_matcher",
                        "impact_calculator",
                        "action_generator",
                        "tradeoff_analyzer",
                        "decision_composer",
                    ],
                    computation_time_ms=computation_time_ms,
                    warnings=warnings,
                    stale_data_sources=stale_sources,
                    missing_data_sources=missing_sources,
                )
                
                # Store processing record
                await self._audit._repository.store_processing_record(processing_record)
                
                # ============================================================
                # STEP 4: RECORD DECISION IN AUDIT TRAIL
                # ============================================================
                await self._audit.record_decision(
                    decision_id=decision.decision_id,
                    customer_id=customer_id,
                    signal_id=signal_id,
                    input_snapshot_id=input_snapshot.snapshot_id,
                    processing_record_id=processing_record.record_id,
                    decision_data={
                        "severity": decision.q3_severity.severity_level.value,
                        "urgency": decision.q2_when.urgency.value,
                        "exposure_usd": decision.q3_severity.total_exposure_usd,
                        "delay_days": decision.q3_severity.expected_delay_days,
                        "shipments_affected": decision.q3_severity.shipments_affected,
                        "expires_at": decision.expires_at.isoformat(),
                    },
                    recommended_action=decision.q5_action.action_type,
                    confidence_score=decision.q6_confidence.score,
                    alternative_actions=[
                        alt.get("action_type") for alt in decision.alternative_actions
                    ],
                )
                
                # ============================================================
                # STEP 5: PERSIST DECISION
                # ============================================================
                await self._decision_repo.save(decision)
                
                # Record span attributes
                span.set_attribute("decision.id", decision.decision_id)
                span.set_attribute("decision.severity", decision.q3_severity.severity_level.value)
                span.set_attribute("decision.exposure_usd", decision.q3_severity.total_exposure_usd)
                span.set_attribute("audit.snapshot_id", input_snapshot.snapshot_id)
                span.set_attribute("audit.processing_id", processing_record.record_id)
                
        except NoExposureError:
            raise
        except Exception as e:
            # Log error but still record in audit trail
            logger.error(
                "decision_generation_failed",
                signal_id=signal_id,
                customer_id=customer_id,
                error=str(e),
                trace_id=trace_id,
            )
            raise
        finally:
            # Record metrics
            duration_ms = (time.perf_counter() - start_time) * 1000
            DECISION_LATENCY.labels(chokepoint=chokepoint).observe(duration_ms / 1000)
        
        # Record success metrics
        DECISIONS_GENERATED.labels(
            chokepoint=chokepoint,
            severity=decision.q3_severity.severity_level.value,
            urgency=decision.q2_when.urgency.value,
        ).inc()
        
        TOTAL_EXPOSURE.labels(chokepoint=chokepoint).inc(
            decision.q3_severity.total_exposure_usd
        )
        
        logger.info(
            "audited_decision_generated",
            decision_id=decision.decision_id,
            customer_id=customer_id,
            signal_id=signal_id,
            snapshot_id=input_snapshot.snapshot_id,
            processing_id=processing_record.record_id,
            exposure_usd=decision.q3_severity.total_exposure_usd,
            duration_ms=duration_ms,
            trace_id=trace_id,
        )
        
        return decision
    
    # ========================================================================
    # BROADCAST MODE
    # ========================================================================
    
    async def process_signal_for_all(
        self,
        intelligence: CorrelatedIntelligence,
        chokepoint: Optional[str] = None,
    ) -> tuple[List[DecisionObject], List[str]]:
        """
        Process a signal for ALL affected customers with audit trail.
        
        Args:
            intelligence: Correlated intelligence from ORACLE
            chokepoint: Optional filter by chokepoint
            
        Returns:
            Tuple of (decisions, errors)
        """
        signal_id = intelligence.signal.signal_id
        target_chokepoint = (
            chokepoint or intelligence.signal.geographic.primary_chokepoint.value
        )
        
        logger.info(
            "processing_audited_signal_broadcast",
            signal_id=signal_id,
            chokepoint=target_chokepoint,
        )
        
        contexts = await self._customer_repo.get_customers_by_chokepoint(target_chokepoint)
        
        decisions: List[DecisionObject] = []
        errors: List[str] = []
        
        for context in contexts:
            try:
                decision = await self.generate_decision(intelligence, context)
                decisions.append(decision)
            except NoExposureError:
                # Expected - customer has no affected shipments
                pass
            except Exception as e:
                error_msg = f"{context.profile.customer_id}: {str(e)}"
                errors.append(error_msg)
                logger.error(
                    "audited_decision_generation_failed",
                    customer_id=context.profile.customer_id,
                    error=str(e),
                )
        
        logger.info(
            "audited_signal_broadcast_complete",
            signal_id=signal_id,
            customers_checked=len(contexts),
            decisions_generated=len(decisions),
            errors=len(errors),
        )
        
        return decisions, errors
    
    # ========================================================================
    # DELIVERY TRACKING
    # ========================================================================
    
    async def record_delivery(
        self,
        decision_id: str,
        channel: str,
        recipient: str,
        success: bool,
        message_id: Optional[str] = None,
        error: Optional[str] = None,
    ) -> None:
        """
        Record decision delivery in audit trail.
        
        Args:
            decision_id: The decision that was delivered
            channel: Delivery channel (whatsapp, email, etc.)
            recipient: Recipient identifier
            success: Whether delivery succeeded
            message_id: External message ID
            error: Error message if failed
        """
        await self._audit.record_delivery(
            decision_id=decision_id,
            channel=channel,
            recipient=recipient,
            success=success,
            external_message_id=message_id,
            error_message=error,
        )
        
        logger.info(
            "delivery_recorded",
            decision_id=decision_id,
            channel=channel,
            success=success,
        )
    
    # ========================================================================
    # HUMAN INTERACTION
    # ========================================================================
    
    async def record_override(
        self,
        decision_id: str,
        user_id: str,
        original_action: str,
        new_action: str,
        reason: str,
        new_action_details: Optional[dict] = None,
    ) -> str:
        """
        Record a human override of a decision.
        
        Args:
            decision_id: The overridden decision
            user_id: Who made the override
            original_action: The system's recommendation
            new_action: The human's chosen action
            reason: Why the override was made
            new_action_details: Additional details for the new action
            
        Returns:
            Override ID
        """
        override_id = await self._audit.record_human_override(
            decision_id=decision_id,
            user_id=user_id,
            original_action=original_action,
            new_action=new_action,
            reason=reason,
            new_action_details=new_action_details,
        )
        
        logger.info(
            "override_recorded",
            decision_id=decision_id,
            override_id=override_id,
            user_id=user_id,
            original_action=original_action,
            new_action=new_action,
        )
        
        return override_id
    
    async def record_feedback(
        self,
        decision_id: str,
        user_id: str,
        feedback_type: str,
        feedback_text: str,
        rating: Optional[int] = None,
    ) -> None:
        """
        Record user feedback on a decision.
        
        Args:
            decision_id: The decision receiving feedback
            user_id: Who provided feedback
            feedback_type: Type of feedback (helpful, unhelpful, incorrect, etc.)
            feedback_text: Free-text feedback
            rating: Optional rating (1-5)
        """
        await self._audit.record_feedback(
            decision_id=decision_id,
            user_id=user_id,
            feedback_type=feedback_type,
            feedback_text=feedback_text,
            rating=rating,
        )
        
        logger.info(
            "feedback_recorded",
            decision_id=decision_id,
            feedback_type=feedback_type,
            rating=rating,
        )
    
    # ========================================================================
    # OUTCOME TRACKING
    # ========================================================================
    
    async def record_outcome(
        self,
        decision_id: str,
        event_occurred: bool,
        actual_impact_usd: Optional[float] = None,
        actual_delay_days: Optional[int] = None,
        action_taken: Optional[str] = None,
        outcome_notes: Optional[str] = None,
    ) -> None:
        """
        Record the actual outcome of a decision.
        
        CRITICAL for learning and calibration.
        
        Args:
            decision_id: The decision
            event_occurred: Did the predicted event actually happen?
            actual_impact_usd: Actual financial impact
            actual_delay_days: Actual delay experienced
            action_taken: What action was actually taken
            outcome_notes: Additional notes
        """
        await self._audit.record_outcome(
            decision_id=decision_id,
            event_occurred=event_occurred,
            actual_impact_usd=actual_impact_usd,
            actual_delay_days=actual_delay_days,
            action_taken=action_taken,
            outcome_notes=outcome_notes,
        )
        
        logger.info(
            "outcome_recorded",
            decision_id=decision_id,
            event_occurred=event_occurred,
            actual_impact_usd=actual_impact_usd,
            actual_delay_days=actual_delay_days,
        )
    
    # ========================================================================
    # AUDIT TRAIL ACCESS
    # ========================================================================
    
    async def get_decision_audit_trail(self, decision_id: str) -> dict:
        """
        Get complete audit trail for a decision.
        
        Returns all audit records related to the decision including:
        - Input snapshot
        - Processing record
        - Decision record
        - Delivery records
        - Override records (if any)
        - Feedback records (if any)
        - Outcome records (if any)
        
        Args:
            decision_id: The decision ID
            
        Returns:
            Complete audit trail
        """
        return await self._audit.get_decision_audit_trail(decision_id)
    
    async def verify_audit_chain(
        self,
        start_sequence: int,
        end_sequence: int,
    ) -> dict:
        """
        Verify the cryptographic integrity of the audit chain.
        
        Args:
            start_sequence: Start of range to verify
            end_sequence: End of range to verify
            
        Returns:
            Verification result with details
        """
        return await self._audit.verify_chain_integrity(start_sequence, end_sequence)
    
    # ========================================================================
    # DECISION ACCESS (delegated to base service)
    # ========================================================================
    
    async def get_decision(self, decision_id: str) -> Optional[DecisionObject]:
        """Get decision by ID."""
        return await self._decision_repo.get(decision_id)
    
    async def get_customer_decisions(
        self,
        customer_id: str,
        include_expired: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[List[DecisionObject], int]:
        """Get all decisions for a customer."""
        return await self._decision_repo.get_by_customer(
            customer_id,
            include_expired=include_expired,
            limit=limit,
            offset=offset,
        )
    
    async def get_active_decisions(
        self,
        customer_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[List[DecisionObject], int]:
        """Get active (non-expired) decisions."""
        return await self._decision_repo.get_active(
            customer_id=customer_id, limit=limit, offset=offset
        )


# ============================================================================
# FACTORY FUNCTIONS
# ============================================================================


def create_audited_riskcast_service(
    session: AsyncSession,
    audit_service: Optional[AuditService] = None,
    use_cache: bool = True,
) -> AuditedRiskCastService:
    """
    Create an audited RISKCAST service.
    
    Args:
        session: Database session
        audit_service: Optional audit service (creates one if not provided)
        use_cache: Whether to use Redis caching
        
    Returns:
        AuditedRiskCastService instance
    """
    if audit_service is None:
        # Create audit service with repository
        audit_repo = AuditRepository(session)
        audit_service = AuditService(repository=audit_repo)
    
    return AuditedRiskCastService(
        session=session,
        audit_service=audit_service,
        use_cache=use_cache,
    )


async def get_audited_riskcast_service(
    session: AsyncSession,
    use_cache: bool = True,
) -> AuditedRiskCastService:
    """
    FastAPI dependency for audited RISKCAST service.
    
    Usage:
        @router.post("/decisions")
        async def create_decision(
            service: AuditedRiskCastService = Depends(get_audited_riskcast_service),
        ):
            ...
    """
    return create_audited_riskcast_service(session, use_cache=use_cache)
