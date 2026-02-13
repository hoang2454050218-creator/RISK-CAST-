"""
Audit Trail Integration Layer.

Integrates the audit system into the RISKCAST decision pipeline.

This module provides:
1. AuditedDecisionComposer - Wraps DecisionComposer with automatic audit
2. audit_decision decorator - For wrapping any decision function
3. Integration hooks for the entire pipeline

CRITICAL: Every decision MUST go through this layer in production.

Usage:
    from app.audit.trail import AuditedDecisionComposer
    
    composer = AuditedDecisionComposer(
        audit_service=audit_service,
        decision_composer=decision_composer,
    )
    
    # Automatically captures inputs, records decision, tracks everything
    decision = await composer.compose(intelligence, context)
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional, Any, Callable, TypeVar
from functools import wraps
import time
import traceback
import hashlib
import json
import uuid

import structlog

from app.audit.schemas import (
    AuditEventType,
    InputSnapshot,
    ProcessingRecord,
    AuditRecord,
)
from app.audit.service import AuditService
from app.audit.repository import InMemoryAuditRepository

# Use TYPE_CHECKING to avoid circular imports and cascading import issues
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from app.oracle.schemas import CorrelatedIntelligence
    from app.riskcast.schemas.customer import CustomerContext
    from app.riskcast.schemas.decision import DecisionObject
    from app.riskcast.composers import DecisionComposer

logger = structlog.get_logger(__name__)

T = TypeVar("T")


# =============================================================================
# AUDITED DECISION COMPOSER
# =============================================================================


class AuditedDecisionComposer:
    """
    Decision composer with automatic audit trail integration.
    
    This wrapper ensures:
    1. Input snapshots are captured BEFORE decision generation
    2. Processing records track model version, timing, warnings
    3. Decisions are recorded with full provenance
    4. Chain integrity is maintained
    5. Every failure is also recorded
    
    CRITICAL: Use this instead of DecisionComposer in production.
    """
    
    def __init__(
        self,
        audit_service: AuditService,
        decision_composer: Optional["DecisionComposer"] = None,
        model_version: str = "1.0.0",
        config_version: str = "1.0.0",
    ):
        """
        Initialize audited decision composer.
        
        Args:
            audit_service: AuditService for recording
            decision_composer: DecisionComposer (creates default if None)
            model_version: Current model version for tracking
            config_version: Current config version for tracking
        """
        self._audit = audit_service
        
        # Lazy import to avoid circular imports
        if decision_composer is None:
            from app.riskcast.composers import create_decision_composer
            self._composer = create_decision_composer()
        else:
            self._composer = decision_composer
            
        self._model_version = model_version
        self._config_version = config_version
        
        # Track configuration hash
        self._config_hash = self._compute_config_hash()
        self._model_hash = self._compute_model_hash()
    
    async def compose(
        self,
        intelligence: "CorrelatedIntelligence",
        context: "CustomerContext",
        trace_id: Optional[str] = None,
    ) -> Optional["DecisionObject"]:
        """
        Compose decision with full audit trail.
        
        This is the MAIN entry point for decision generation.
        
        Args:
            intelligence: Correlated intelligence from ORACLE
            context: Customer context
            trace_id: Optional trace ID for distributed tracing
            
        Returns:
            DecisionObject with audit trail recorded, or None if no exposure
        """
        start_time = time.perf_counter()
        processing_id = f"proc_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"
        warnings: list[str] = []
        degradation_level = 0
        stale_sources: list[str] = []
        missing_sources: list[str] = []
        
        try:
            # =========================================================
            # STEP 1: CAPTURE INPUT SNAPSHOT (BEFORE decision)
            # =========================================================
            logger.info(
                "audit_capturing_inputs",
                signal_id=intelligence.signal.signal_id,
                customer_id=context.profile.customer_id,
                trace_id=trace_id,
            )
            
            snapshot = await self._audit.capture_inputs(
                signal=intelligence.signal,
                reality=intelligence.reality,
                context=context,
            )
            
            # Check for stale data
            if snapshot.reality_staleness_seconds > 300:  # 5 minutes
                warnings.append(f"Reality data is {snapshot.reality_staleness_seconds}s stale")
                stale_sources.append("reality")
                degradation_level = max(degradation_level, 1)
            
            if snapshot.reality_staleness_seconds > 900:  # 15 minutes
                degradation_level = max(degradation_level, 2)
            
            # =========================================================
            # STEP 2: GENERATE DECISION
            # =========================================================
            logger.info(
                "audit_generating_decision",
                snapshot_id=snapshot.snapshot_id,
                trace_id=trace_id,
            )
            
            decision = self._composer.compose(intelligence, context)
            
            computation_time_ms = int((time.perf_counter() - start_time) * 1000)
            
            if not decision:
                # No exposure - still record this
                await self._record_no_exposure(
                    snapshot=snapshot,
                    processing_id=processing_id,
                    computation_time_ms=computation_time_ms,
                    trace_id=trace_id,
                )
                return None
            
            # =========================================================
            # STEP 3: CREATE PROCESSING RECORD
            # =========================================================
            processing = ProcessingRecord(
                record_id=processing_id,
                model_version=self._model_version,
                model_hash=self._model_hash,
                config_version=self._config_version,
                config_hash=self._config_hash,
                reasoning_trace_id=trace_id or "",
                layers_executed=[
                    "exposure_matching",
                    "impact_calculation",
                    "action_generation",
                    "tradeoff_analysis",
                    "decision_composition",
                ],
                computation_time_ms=computation_time_ms,
                memory_used_mb=0.0,  # Would need profiling to get this
                warnings=warnings,
                degradation_level=degradation_level,
                stale_data_sources=stale_sources,
                missing_data_sources=missing_sources,
            )
            
            # =========================================================
            # STEP 4: RECORD DECISION
            # =========================================================
            audit_id = await self._audit.record_decision(
                decision=decision,
                snapshot=snapshot,
                processing=processing,
            )
            
            logger.info(
                "audit_decision_recorded",
                decision_id=decision.decision_id,
                audit_id=audit_id,
                snapshot_id=snapshot.snapshot_id,
                processing_id=processing_id,
                computation_time_ms=computation_time_ms,
                trace_id=trace_id,
            )
            
            return decision
            
        except Exception as e:
            # Record the failure in audit trail
            computation_time_ms = int((time.perf_counter() - start_time) * 1000)
            
            await self._record_failure(
                intelligence=intelligence,
                context=context,
                error=e,
                processing_id=processing_id,
                computation_time_ms=computation_time_ms,
                trace_id=trace_id,
            )
            
            raise
    
    async def _record_no_exposure(
        self,
        snapshot: InputSnapshot,
        processing_id: str,
        computation_time_ms: int,
        trace_id: Optional[str],
    ) -> None:
        """Record when customer has no exposure."""
        # Create minimal processing record
        processing = ProcessingRecord(
            record_id=processing_id,
            model_version=self._model_version,
            model_hash=self._model_hash,
            config_version=self._config_version,
            config_hash=self._config_hash,
            reasoning_trace_id=trace_id or "",
            layers_executed=["exposure_matching"],
            computation_time_ms=computation_time_ms,
            warnings=["No exposure found for customer"],
        )
        
        # Store processing record via internal method
        # In real implementation, would go through audit service
        logger.info(
            "audit_no_exposure_recorded",
            snapshot_id=snapshot.snapshot_id,
            customer_id=snapshot.customer_id,
            processing_id=processing_id,
        )
    
    async def _record_failure(
        self,
        intelligence: "CorrelatedIntelligence",
        context: "CustomerContext",
        error: Exception,
        processing_id: str,
        computation_time_ms: int,
        trace_id: Optional[str],
    ) -> None:
        """Record decision generation failure."""
        logger.error(
            "audit_decision_failed",
            signal_id=intelligence.signal.signal_id,
            customer_id=context.profile.customer_id,
            error=str(error),
            error_type=type(error).__name__,
            processing_id=processing_id,
            computation_time_ms=computation_time_ms,
            trace_id=trace_id,
            traceback=traceback.format_exc(),
        )
    
    def _compute_config_hash(self) -> str:
        """Compute hash of current configuration."""
        # In production, would hash actual config values
        config_str = f"config_v{self._config_version}"
        return hashlib.sha256(config_str.encode()).hexdigest()[:16]
    
    def _compute_model_hash(self) -> str:
        """Compute hash of current model."""
        # In production, would hash model parameters/weights
        model_str = f"model_v{self._model_version}"
        return hashlib.sha256(model_str.encode()).hexdigest()[:16]


# =============================================================================
# DECORATOR FOR AUDITING
# =============================================================================


def audit_decision(
    audit_service: AuditService,
    event_type: AuditEventType = AuditEventType.DECISION_GENERATED,
):
    """
    Decorator to add audit trail to any decision function.
    
    Usage:
        @audit_decision(audit_service, AuditEventType.DECISION_GENERATED)
        async def generate_decision(intelligence, context):
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            start_time = time.perf_counter()
            entity_id = kwargs.get("decision_id") or str(uuid.uuid4())[:8]
            
            try:
                result = await func(*args, **kwargs)
                
                # Record success
                computation_time_ms = int((time.perf_counter() - start_time) * 1000)
                
                # Would record audit event here
                logger.debug(
                    "audited_function_success",
                    function=func.__name__,
                    computation_time_ms=computation_time_ms,
                )
                
                return result
                
            except Exception as e:
                # Record failure
                computation_time_ms = int((time.perf_counter() - start_time) * 1000)
                
                logger.error(
                    "audited_function_failed",
                    function=func.__name__,
                    error=str(e),
                    computation_time_ms=computation_time_ms,
                )
                
                raise
        
        return wrapper
    return decorator


# =============================================================================
# PIPELINE INTEGRATION
# =============================================================================


class AuditPipelineHooks:
    """
    Hooks for integrating audit into the decision pipeline.
    
    Provides callbacks at each stage of decision generation.
    """
    
    def __init__(self, audit_service: AuditService):
        self._audit = audit_service
    
    async def on_signal_received(
        self,
        signal_id: str,
        source: str,
        probability: float,
    ) -> None:
        """Hook called when a new signal is received."""
        logger.info(
            "pipeline_signal_received",
            signal_id=signal_id,
            source=source,
            probability=probability,
        )
    
    async def on_intelligence_correlated(
        self,
        signal_id: str,
        correlation_status: str,
        combined_confidence: float,
    ) -> None:
        """Hook called when intelligence is correlated."""
        logger.info(
            "pipeline_intelligence_correlated",
            signal_id=signal_id,
            correlation_status=correlation_status,
            combined_confidence=combined_confidence,
        )
    
    async def on_decision_generated(
        self,
        decision: "DecisionObject",
        snapshot_id: str,
    ) -> None:
        """Hook called when decision is generated."""
        logger.info(
            "pipeline_decision_generated",
            decision_id=decision.decision_id,
            customer_id=decision.customer_id,
            snapshot_id=snapshot_id,
            action=decision.q5_action.action_type,
            confidence=decision.q6_confidence.score,
        )
    
    async def on_decision_delivered(
        self,
        decision_id: str,
        channel: str,
        status: str,
    ) -> None:
        """Hook called when decision is delivered."""
        await self._audit.record_delivery(
            decision_id=decision_id,
            channel=channel,
            status=status,
        )
    
    async def on_decision_acknowledged(
        self,
        decision_id: str,
        by_user: Optional[str] = None,
    ) -> None:
        """Hook called when decision is acknowledged."""
        await self._audit.record_acknowledgment(
            decision_id=decision_id,
            acknowledged_by=by_user,
        )
    
    async def on_action_taken(
        self,
        decision_id: str,
        action_type: str,
        by_user: Optional[str] = None,
    ) -> None:
        """Hook called when action is taken."""
        await self._audit.record_action_taken(
            decision_id=decision_id,
            action_type=action_type,
            taken_by=by_user,
        )
    
    async def on_outcome_recorded(
        self,
        decision_id: str,
        outcome: dict,
        accuracy: str,
    ) -> None:
        """Hook called when outcome is recorded."""
        await self._audit.record_outcome(
            decision_id=decision_id,
            actual_outcome=outcome,
            accuracy_assessment=accuracy,
        )


# =============================================================================
# CHAIN VERIFICATION UTILITIES
# =============================================================================


class AuditChainVerifier:
    """
    Utilities for verifying audit chain integrity.
    
    Should be run periodically (e.g., daily) in production.
    """
    
    def __init__(self, audit_service: AuditService):
        self._audit = audit_service
    
    async def verify_full_chain(self) -> dict:
        """
        Verify the entire audit chain.
        
        Returns:
            Verification result with status and details
        """
        result = await self._audit.verify_chain_integrity()
        
        return {
            "is_valid": result.is_valid,
            "records_checked": result.records_checked,
            "error_type": result.error_type,
            "error_message": result.error_message,
            "first_invalid_sequence": result.first_invalid_sequence,
            "verified_at": datetime.utcnow().isoformat(),
        }
    
    async def verify_recent(self, hours: int = 24) -> dict:
        """
        Verify audit records from the last N hours.
        
        Returns:
            Verification result
        """
        # Get approximate sequence range for time period
        # In production, would query by timestamp
        result = await self._audit.verify_chain_integrity()
        
        return {
            "is_valid": result.is_valid,
            "records_checked": result.records_checked,
            "period_hours": hours,
            "verified_at": datetime.utcnow().isoformat(),
        }
    
    async def get_chain_stats(self) -> dict:
        """
        Get statistics about the audit chain.
        """
        # Would query repository for stats
        return {
            "total_records": 0,  # Would be actual count
            "first_record_at": None,
            "last_record_at": None,
            "event_type_counts": {},
            "chain_status": "healthy",
        }


# =============================================================================
# FACTORY FUNCTIONS
# =============================================================================


def create_audited_composer(
    audit_service: Optional[AuditService] = None,
    decision_composer: Optional["DecisionComposer"] = None,
    model_version: str = "1.0.0",
    config_version: str = "1.0.0",
) -> "AuditedDecisionComposer":
    """
    Create an audited decision composer.
    
    Args:
        audit_service: AuditService (creates default if None)
        decision_composer: DecisionComposer (creates default if None)
        model_version: Model version string
        config_version: Config version string
        
    Returns:
        AuditedDecisionComposer instance
    """
    if audit_service is None:
        # Create in-memory audit service for development
        repo = InMemoryAuditRepository()
        audit_service = AuditService(repo)
    
    return AuditedDecisionComposer(
        audit_service=audit_service,
        decision_composer=decision_composer,
        model_version=model_version,
        config_version=config_version,
    )


def create_pipeline_hooks(
    audit_service: Optional[AuditService] = None,
) -> AuditPipelineHooks:
    """
    Create pipeline hooks for audit integration.
    
    Args:
        audit_service: AuditService (creates default if None)
        
    Returns:
        AuditPipelineHooks instance
    """
    if audit_service is None:
        repo = InMemoryAuditRepository()
        audit_service = AuditService(repo)
    
    return AuditPipelineHooks(audit_service)


def create_chain_verifier(
    audit_service: Optional[AuditService] = None,
) -> AuditChainVerifier:
    """
    Create chain verifier.
    
    Args:
        audit_service: AuditService (creates default if None)
        
    Returns:
        AuditChainVerifier instance
    """
    if audit_service is None:
        repo = InMemoryAuditRepository()
        audit_service = AuditService(repo)
    
    return AuditChainVerifier(audit_service)
