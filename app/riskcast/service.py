"""RISKCAST Service - Main entry point for the decision engine.

The RiskCastService is the HIGH-LEVEL API for RISKCAST.

It provides:
1. Process a signal for ALL affected customers (broadcast mode)
2. Process a signal for ONE specific customer (targeted mode)
3. Get decision by ID
4. Mark decision as acted upon / provide feedback

This is what the FastAPI endpoints will call.

UPDATED: Now uses PostgreSQL for persistence with optional Redis caching.
UPDATED: Integrated with metrics, tracing, and circuit breakers.
UPDATED: Full audit trail integration for accountability & trust.
"""

from datetime import datetime
from typing import Optional, List
from contextlib import asynccontextmanager
import time

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.oracle.schemas import CorrelatedIntelligence
from app.riskcast.composers import DecisionComposer, create_decision_composer
from app.riskcast.repos.customer import (
    CustomerRepositoryInterface,
    PostgresCustomerRepository,
    create_customer_repository,
)
from app.riskcast.repos.decision import (
    DecisionRepositoryInterface,
    PostgresDecisionRepository,
    CachedDecisionRepository,
    create_decision_repository,
    DecisionNotFoundError,
)
from app.riskcast.schemas.customer import CustomerContext
from app.riskcast.schemas.decision import DecisionObject
from app.common.exceptions import (
    CustomerNotFoundError,
    NoExposureError,
    InsufficientDataError,
)
from app.core.database import get_db_context

# Import metrics for tracking
from app.common.metrics import (
    DECISIONS_GENERATED,
    DECISION_LATENCY,
    ACTIVE_DECISIONS,
    TOTAL_EXPOSURE,
)

# Import tracing for observability
from app.core.tracing import get_tracer, get_current_trace_id, SpanKind

# Import audit trail for accountability
from app.audit.service import AuditService
from app.audit.repository import InMemoryAuditRepository, AuditRepository
from app.audit.trail import AuditedDecisionComposer, AuditPipelineHooks
from app.audit.snapshots import SnapshotManager, SnapshotValidationResult

logger = structlog.get_logger(__name__)


# ============================================================================
# ASYNC RISKCAST SERVICE (Production)
# ============================================================================


class AsyncRiskCastService:
    """
    Async RISKCAST decision engine service with PostgreSQL persistence.

    This is the production-ready service that:
    1. Uses PostgreSQL for persistent storage
    2. Supports Redis caching for performance
    3. Properly handles database transactions
    4. Supports multi-tenancy isolation
    5. Full audit trail for accountability & trust
    """

    def __init__(
        self,
        session: AsyncSession,
        use_cache: bool = True,
        audit_service: Optional[AuditService] = None,
        enable_audit: bool = True,
        model_version: str = "1.0.0",
        config_version: str = "1.0.0",
    ):
        """
        Initialize async RISKCAST service.

        Args:
            session: Async database session
            use_cache: Whether to use Redis caching
            audit_service: Optional AuditService for audit trail
            enable_audit: Whether to enable audit trail (default True)
            model_version: Current model version for audit records
            config_version: Current config version for audit records
        """
        self._session = session
        self._customer_repo = PostgresCustomerRepository(session)
        self._decision_repo = create_decision_repository(session, use_cache=use_cache)
        
        # Setup audit trail
        self._enable_audit = enable_audit
        self._audit_service = audit_service
        self._snapshot_manager = SnapshotManager() if enable_audit else None
        self._pipeline_hooks: Optional[AuditPipelineHooks] = None
        
        if enable_audit:
            # Create default audit service if not provided
            if self._audit_service is None:
                self._audit_service = AuditService(InMemoryAuditRepository())
            
            # Create audited decision composer
            base_composer = create_decision_composer()
            self._composer = AuditedDecisionComposer(
                audit_service=self._audit_service,
                decision_composer=base_composer,
                model_version=model_version,
                config_version=config_version,
            )
            
            # Create pipeline hooks for delivery tracking
            self._pipeline_hooks = AuditPipelineHooks(self._audit_service)
            
            logger.info(
                "audit_trail_enabled",
                model_version=model_version,
                config_version=config_version,
            )
        else:
            self._composer = create_decision_composer()
            logger.warning("audit_trail_disabled")

    # ========================================================================
    # DECISION GENERATION
    # ========================================================================

    async def generate_decision(
        self,
        intelligence: CorrelatedIntelligence,
        context: CustomerContext,
    ) -> DecisionObject:
        """
        Generate a decision for a customer based on intelligence.

        With audit trail enabled, this:
        1. Captures input snapshot BEFORE decision generation
        2. Records full processing details
        3. Creates cryptographic chain for integrity

        Args:
            intelligence: Correlated intelligence from ORACLE
            context: Customer context with profile and shipments

        Returns:
            Generated DecisionObject

        Raises:
            NoExposureError: If customer has no exposure
            InsufficientDataError: If missing required data
        """
        signal_id = intelligence.signal.signal_id
        customer_id = context.profile.customer_id
        chokepoint = intelligence.signal.geographic.primary_chokepoint.value
        
        # Start timing for metrics
        start_time = time.perf_counter()
        
        # Get tracer for distributed tracing
        tracer = get_tracer()
        trace_id = get_current_trace_id()

        logger.info(
            "generating_decision",
            signal_id=signal_id,
            customer_id=customer_id,
            trace_id=trace_id,
            audit_enabled=self._enable_audit,
        )

        try:
            async with tracer.start_span(
                "riskcast.generate_decision",
                kind=SpanKind.INTERNAL,
                attributes={
                    "signal_id": signal_id,
                    "customer_id": customer_id,
                    "chokepoint": chokepoint,
                    "audit.enabled": self._enable_audit,
                },
            ) as span:
                # Generate decision using composer (audited or regular)
                if self._enable_audit and isinstance(self._composer, AuditedDecisionComposer):
                    # Use audited composer - captures snapshots automatically
                    decision = await self._composer.compose(
                        intelligence=intelligence,
                        context=context,
                        trace_id=trace_id,
                    )
                else:
                    # Use regular composer
                    decision = self._composer.compose(intelligence, context)

                if not decision:
                    span.set_attribute("decision.no_exposure", True)
                    raise NoExposureError(
                        customer_id=customer_id,
                        signal_id=signal_id,
                        reason="No affected shipments found",
                    )

                # Persist to database
                await self._decision_repo.save(decision)
                
                # Record span attributes
                span.set_attribute("decision.id", decision.decision_id)
                span.set_attribute("decision.severity", decision.q3_severity.severity_level.value)
                span.set_attribute("decision.exposure_usd", decision.q3_severity.total_exposure_usd)

        finally:
            # Record metrics regardless of outcome
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
            "decision_generated",
            decision_id=decision.decision_id,
            customer_id=customer_id,
            signal_id=signal_id,
            exposure_usd=decision.q3_severity.total_exposure_usd,
            duration_ms=duration_ms,
            trace_id=trace_id,
            audit_enabled=self._enable_audit,
        )

        return decision

    async def process_signal_for_all(
        self,
        intelligence: CorrelatedIntelligence,
        chokepoint: Optional[str] = None,
    ) -> tuple[List[DecisionObject], List[str]]:
        """
        Process a signal for ALL affected customers.

        Broadcast mode: Called when a new signal arrives.

        Args:
            intelligence: Correlated intelligence from ORACLE
            chokepoint: Optional filter by chokepoint

        Returns:
            Tuple of (decisions, errors)
        """
        signal_id = intelligence.signal.signal_id
        target_chokepoint = chokepoint or intelligence.signal.geographic.primary_chokepoint.value

        logger.info(
            "processing_signal_broadcast",
            signal_id=signal_id,
            chokepoint=target_chokepoint,
        )

        # Get affected customers
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
                    "decision_generation_failed",
                    customer_id=context.profile.customer_id,
                    error=str(e),
                )

        logger.info(
            "signal_broadcast_complete",
            signal_id=signal_id,
            customers_checked=len(contexts),
            decisions_generated=len(decisions),
            errors=len(errors),
        )

        return decisions, errors

    # ========================================================================
    # DECISION RETRIEVAL
    # ========================================================================

    async def get_decision(self, decision_id: str) -> Optional[DecisionObject]:
        """Get a decision by ID."""
        return await self._decision_repo.get(decision_id)

    async def get_decision_or_raise(self, decision_id: str) -> DecisionObject:
        """Get a decision by ID or raise NotFoundError."""
        from app.common.exceptions import DecisionNotFoundError as HTTPDecisionNotFoundError

        decision = await self._decision_repo.get(decision_id)
        if not decision:
            raise HTTPDecisionNotFoundError(decision_id)
        return decision

    async def get_customer_decisions(
        self,
        customer_id: str,
        include_expired: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[List[DecisionObject], int]:
        """
        Get all decisions for a customer with pagination.

        Args:
            customer_id: Customer ID
            include_expired: Include expired decisions
            limit: Max results
            offset: Skip first N results

        Returns:
            Tuple of (decisions, total_count)
        """
        return await self._decision_repo.get_by_customer(
            customer_id,
            include_expired=include_expired,
            limit=limit,
            offset=offset,
        )

    async def get_signal_decisions(
        self,
        signal_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[List[DecisionObject], int]:
        """Get all decisions for a signal with pagination."""
        return await self._decision_repo.get_by_signal(
            signal_id, limit=limit, offset=offset
        )

    async def get_active_decisions(
        self,
        customer_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[List[DecisionObject], int]:
        """Get active (non-expired) decisions with pagination."""
        return await self._decision_repo.get_active(
            customer_id=customer_id, limit=limit, offset=offset
        )

    # ========================================================================
    # FEEDBACK & TRACKING (with audit trail)
    # ========================================================================

    async def record_delivery(
        self,
        decision_id: str,
        channel: str,
        status: str,
    ) -> None:
        """
        Record that a decision was delivered to customer.

        Args:
            decision_id: Decision ID
            channel: Delivery channel (whatsapp, email, sms, etc.)
            status: Delivery status (sent, delivered, failed, etc.)
        """
        # Record to audit trail
        if self._enable_audit and self._pipeline_hooks:
            await self._pipeline_hooks.on_decision_delivered(
                decision_id=decision_id,
                channel=channel,
                status=status,
            )
        
        logger.info(
            "decision_delivered",
            decision_id=decision_id,
            channel=channel,
            status=status,
        )

    async def acknowledge_decision(
        self,
        decision_id: str,
        action_taken: Optional[str] = None,
        by_user: Optional[str] = None,
    ) -> DecisionObject:
        """
        Acknowledge a decision and optionally record action taken.

        With audit trail enabled, records acknowledgment and action
        to the immutable audit chain.

        Args:
            decision_id: Decision ID
            action_taken: Action the customer took
            by_user: User who acknowledged (for audit trail)

        Returns:
            Updated decision
        """
        decision = await self._decision_repo.update(
            decision_id,
            was_acted_upon=True if action_taken else None,
            user_feedback=action_taken,
        )

        if not decision:
            from app.common.exceptions import DecisionNotFoundError as HTTPDecisionNotFoundError
            raise HTTPDecisionNotFoundError(decision_id)

        # Record to audit trail
        if self._enable_audit and self._pipeline_hooks:
            await self._pipeline_hooks.on_decision_acknowledged(
                decision_id=decision_id,
                by_user=by_user,
            )
            
            if action_taken:
                await self._pipeline_hooks.on_action_taken(
                    decision_id=decision_id,
                    action_type=action_taken,
                    by_user=by_user,
                )

        logger.info(
            "decision_acknowledged",
            decision_id=decision_id,
            customer_id=decision.customer_id,
            action_taken=action_taken,
            by_user=by_user,
            audit_recorded=self._enable_audit,
        )

        return decision

    async def record_feedback(
        self,
        decision_id: str,
        feedback: str,
    ) -> DecisionObject:
        """Record user feedback on a decision."""
        decision = await self._decision_repo.update(
            decision_id, user_feedback=feedback
        )

        if not decision:
            from app.common.exceptions import DecisionNotFoundError as HTTPDecisionNotFoundError
            raise HTTPDecisionNotFoundError(decision_id)

        logger.info(
            "feedback_recorded",
            decision_id=decision_id,
            customer_id=decision.customer_id,
            feedback_length=len(feedback),
        )

        return decision

    async def record_outcome(
        self,
        decision_id: str,
        actual_outcome: dict,
        accuracy_assessment: str,
    ) -> None:
        """
        Record the actual outcome of a decision for calibration.

        CRITICAL for self-improving system: Links prediction to reality.

        Args:
            decision_id: Decision ID
            actual_outcome: What actually happened
            accuracy_assessment: How accurate was our prediction (accurate, partial, inaccurate)
        """
        # Record to audit trail
        if self._enable_audit and self._pipeline_hooks:
            await self._pipeline_hooks.on_outcome_recorded(
                decision_id=decision_id,
                outcome=actual_outcome,
                accuracy=accuracy_assessment,
            )
        
        logger.info(
            "outcome_recorded",
            decision_id=decision_id,
            accuracy=accuracy_assessment,
            outcome_keys=list(actual_outcome.keys()),
        )

    # ========================================================================
    # MAINTENANCE
    # ========================================================================

    async def cleanup_expired(self) -> int:
        """Clean up expired decisions."""
        count = await self._decision_repo.delete_expired()
        if count > 0:
            logger.info("expired_decisions_cleaned", count=count)
        return count

    # ========================================================================
    # AUDIT TRAIL OPERATIONS
    # ========================================================================

    async def verify_audit_chain(self) -> dict:
        """
        Verify the integrity of the audit chain.

        Should be run periodically (e.g., daily) in production.

        Returns:
            Verification result with status and details
        """
        if not self._enable_audit or not self._audit_service:
            return {
                "is_valid": None,
                "message": "Audit trail not enabled",
            }
        
        result = await self._audit_service.verify_chain_integrity()
        
        verification_result = {
            "is_valid": result.is_valid,
            "records_checked": result.records_checked,
            "error_type": result.error_type,
            "error_message": result.error_message,
            "first_invalid_sequence": result.first_invalid_sequence,
        }
        
        if not result.is_valid:
            logger.error(
                "audit_chain_verification_failed",
                **verification_result,
            )
        else:
            logger.info(
                "audit_chain_verified",
                records_checked=result.records_checked,
            )
        
        return verification_result

    async def get_audit_status(self) -> dict:
        """
        Get current audit trail status.

        Returns:
            Status including enabled state, record counts, last verification
        """
        if not self._enable_audit:
            return {
                "enabled": False,
                "message": "Audit trail not enabled",
            }
        
        return {
            "enabled": True,
            "audit_service_type": type(self._audit_service).__name__ if self._audit_service else None,
            "snapshot_manager": self._snapshot_manager is not None,
            "pipeline_hooks": self._pipeline_hooks is not None,
        }

    def get_audit_service(self) -> Optional[AuditService]:
        """
        Get the audit service for advanced operations.

        Returns:
            AuditService if enabled, None otherwise
        """
        return self._audit_service if self._enable_audit else None

    # ========================================================================
    # STATISTICS
    # ========================================================================

    async def get_summary(
        self,
        customer_id: Optional[str] = None,
    ) -> dict:
        """Get summary statistics."""
        if hasattr(self._decision_repo, "get_summary"):
            # Use optimized database query
            return await self._decision_repo.get_summary(customer_id)

        # Fallback to manual calculation
        decisions, total = await self.get_customer_decisions(
            customer_id, include_expired=True, limit=1000
        ) if customer_id else await self.get_active_decisions(limit=1000)

        active = [d for d in decisions if not d.is_expired]
        expired = [d for d in decisions if d.is_expired]
        acted_upon = [d for d in decisions if d.was_acted_upon]

        return {
            "total_decisions": total,
            "active_decisions": len(active),
            "expired_decisions": len(expired),
            "acted_upon": len(acted_upon),
            "total_exposure_usd": sum(
                d.q3_severity.total_exposure_usd for d in active
            ),
        }


# ============================================================================
# IN-MEMORY DECISION STORE
# ============================================================================


class InMemoryDecisionStore:
    """
    In-memory decision store for testing and development.
    
    NOT for production use - decisions are lost on restart.
    """
    
    def __init__(self):
        self._decisions: dict[str, DecisionObject] = {}
        self._by_customer: dict[str, list[str]] = {}
        self._by_signal: dict[str, list[str]] = {}
    
    def save(self, decision: DecisionObject) -> None:
        """Save a decision."""
        self._decisions[decision.decision_id] = decision
        
        # Index by customer
        if decision.customer_id not in self._by_customer:
            self._by_customer[decision.customer_id] = []
        if decision.decision_id not in self._by_customer[decision.customer_id]:
            self._by_customer[decision.customer_id].append(decision.decision_id)
        
        # Index by signal
        if decision.signal_id not in self._by_signal:
            self._by_signal[decision.signal_id] = []
        if decision.decision_id not in self._by_signal[decision.signal_id]:
            self._by_signal[decision.signal_id].append(decision.decision_id)
    
    def get(self, decision_id: str) -> Optional[DecisionObject]:
        """Get a decision by ID."""
        return self._decisions.get(decision_id)
    
    def get_by_customer(
        self,
        customer_id: str,
        include_expired: bool = False,
    ) -> list[DecisionObject]:
        """Get decisions for a customer."""
        ids = self._by_customer.get(customer_id, [])
        decisions = [self._decisions[d] for d in ids if d in self._decisions]
        if not include_expired:
            decisions = [d for d in decisions if not d.is_expired]
        return sorted(decisions, key=lambda d: d.generated_at, reverse=True)
    
    def get_by_signal(self, signal_id: str) -> list[DecisionObject]:
        """Get decisions for a signal."""
        ids = self._by_signal.get(signal_id, [])
        return [self._decisions[d] for d in ids if d in self._decisions]
    
    def get_active(
        self,
        customer_id: Optional[str] = None,
    ) -> list[DecisionObject]:
        """Get active (non-expired) decisions."""
        if customer_id:
            return self.get_by_customer(customer_id, include_expired=False)
        return [d for d in self._decisions.values() if not d.is_expired]
    
    def update(
        self,
        decision_id: str,
        was_acted_upon: Optional[bool] = None,
        user_feedback: Optional[str] = None,
    ) -> Optional[DecisionObject]:
        """Update a decision (returns updated decision or None)."""
        decision = self._decisions.get(decision_id)
        if not decision:
            return None
        
        # Create updated copy
        updates = {}
        if was_acted_upon is not None:
            updates["was_acted_upon"] = was_acted_upon
        if user_feedback is not None:
            updates["user_feedback"] = user_feedback
        
        if updates:
            # Pydantic models are immutable, so create new instance
            updated = decision.model_copy(update=updates)
            self._decisions[decision_id] = updated
            return updated
        
        return decision
    
    def delete(self, decision_id: str) -> bool:
        """Delete a decision."""
        if decision_id not in self._decisions:
            return False
        
        decision = self._decisions.pop(decision_id)
        
        # Remove from indexes
        if decision.customer_id in self._by_customer:
            self._by_customer[decision.customer_id] = [
                d for d in self._by_customer[decision.customer_id] if d != decision_id
            ]
        if decision.signal_id in self._by_signal:
            self._by_signal[decision.signal_id] = [
                d for d in self._by_signal[decision.signal_id] if d != decision_id
            ]
        
        return True
    
    def clear(self) -> None:
        """Clear all decisions."""
        self._decisions.clear()
        self._by_customer.clear()
        self._by_signal.clear()
    
    def count(self) -> int:
        """Get total number of decisions."""
        return len(self._decisions)


# ============================================================================
# SYNC RISKCAST SERVICE (Legacy compatibility)
# ============================================================================


class RiskCastService:
    """
    Synchronous RISKCAST service for legacy compatibility.

    DEPRECATED: Use AsyncRiskCastService for new code.

    This wraps the async service for sync contexts.
    """

    def __init__(
        self,
        customer_repository: Optional[CustomerRepositoryInterface] = None,
        decision_composer: Optional[DecisionComposer] = None,
    ):
        """Initialize sync service."""
        self._customer_repo = customer_repository or create_customer_repository()
        self._composer = decision_composer or create_decision_composer()
        self._decisions: dict[str, DecisionObject] = {}
        self._by_customer: dict[str, list[str]] = {}
        self._by_signal: dict[str, list[str]] = {}

    def process_signal(
        self,
        intelligence: CorrelatedIntelligence,
    ) -> list[DecisionObject]:
        """Process signal for all customers (sync)."""
        contexts = self._customer_repo.get_all_contexts_sync()
        decisions: list[DecisionObject] = []

        for context in contexts:
            decision = self._composer.compose(intelligence, context)
            if decision:
                self._save_decision(decision)
                decisions.append(decision)

        return decisions

    def _save_decision(self, decision: DecisionObject) -> None:
        """Save decision to in-memory store."""
        self._decisions[decision.decision_id] = decision

        if decision.customer_id not in self._by_customer:
            self._by_customer[decision.customer_id] = []
        self._by_customer[decision.customer_id].append(decision.decision_id)

        if decision.signal_id not in self._by_signal:
            self._by_signal[decision.signal_id] = []
        self._by_signal[decision.signal_id].append(decision.decision_id)

    def get_decision(self, decision_id: str) -> Optional[DecisionObject]:
        """Get decision by ID."""
        return self._decisions.get(decision_id)

    def get_decisions_for_customer(
        self,
        customer_id: str,
        include_expired: bool = False,
    ) -> list[DecisionObject]:
        """Get decisions for customer."""
        ids = self._by_customer.get(customer_id, [])
        decisions = [self._decisions[d] for d in ids if d in self._decisions]
        if not include_expired:
            decisions = [d for d in decisions if not d.is_expired]
        return sorted(decisions, key=lambda d: d.generated_at, reverse=True)

    def get_active_decisions(
        self,
        customer_id: Optional[str] = None,
    ) -> list[DecisionObject]:
        """Get active decisions."""
        if customer_id:
            return self.get_decisions_for_customer(customer_id, False)
        return [d for d in self._decisions.values() if not d.is_expired]

    def get_summary(self, customer_id: Optional[str] = None) -> dict:
        """Get summary statistics."""
        if customer_id:
            decisions = self.get_decisions_for_customer(customer_id, True)
        else:
            decisions = list(self._decisions.values())

        active = [d for d in decisions if not d.is_expired]

        return {
            "total_decisions": len(decisions),
            "active_decisions": len(active),
            "expired_decisions": len(decisions) - len(active),
            "acted_upon": len([d for d in decisions if d.was_acted_upon]),
            "total_exposure_usd": sum(d.q3_severity.total_exposure_usd for d in active),
        }


# ============================================================================
# FACTORY FUNCTIONS
# ============================================================================


def create_async_riskcast_service(
    session: AsyncSession,
    use_cache: bool = True,
    audit_service: Optional[AuditService] = None,
    enable_audit: bool = True,
    model_version: str = "1.0.0",
    config_version: str = "1.0.0",
) -> AsyncRiskCastService:
    """
    Create async RISKCAST service.

    Args:
        session: Database session
        use_cache: Whether to use Redis caching
        audit_service: Optional AuditService for audit trail
        enable_audit: Whether to enable audit trail (default True)
        model_version: Current model version for audit records
        config_version: Current config version for audit records

    Returns:
        AsyncRiskCastService instance with full audit trail
    """
    return AsyncRiskCastService(
        session=session,
        use_cache=use_cache,
        audit_service=audit_service,
        enable_audit=enable_audit,
        model_version=model_version,
        config_version=config_version,
    )


def create_riskcast_service(
    customer_repository: Optional[CustomerRepositoryInterface] = None,
    decision_composer: Optional[DecisionComposer] = None,
) -> RiskCastService:
    """Create sync RISKCAST service (legacy)."""
    return RiskCastService(
        customer_repository=customer_repository,
        decision_composer=decision_composer,
    )


# ============================================================================
# FASTAPI DEPENDENCY INJECTION
# ============================================================================


async def get_async_riskcast_service(
    session: AsyncSession,
    use_cache: bool = True,
    enable_audit: bool = True,
) -> AsyncRiskCastService:
    """
    FastAPI dependency for async RISKCAST service.

    Usage:
        @router.get("/decisions")
        async def get_decisions(
            service: AsyncRiskCastService = Depends(get_async_riskcast_service),
        ):
            ...
    """
    return create_async_riskcast_service(
        session=session,
        use_cache=use_cache,
        enable_audit=enable_audit,
    )


@asynccontextmanager
async def riskcast_service_context(
    use_cache: bool = True,
    enable_audit: bool = True,
    audit_service: Optional[AuditService] = None,
):
    """
    Context manager for RISKCAST service with database session.

    Usage:
        async with riskcast_service_context() as service:
            decision = await service.get_decision(decision_id)
            
        # With custom audit service
        async with riskcast_service_context(audit_service=my_audit) as service:
            decision = await service.generate_decision(intelligence, context)
    """
    async with get_db_context() as session:
        yield create_async_riskcast_service(
            session=session,
            use_cache=use_cache,
            enable_audit=enable_audit,
            audit_service=audit_service,
        )


# Legacy singleton for backwards compatibility
_sync_service_instance: Optional[RiskCastService] = None


def get_riskcast_service() -> RiskCastService:
    """Get sync RISKCAST service singleton (legacy)."""
    global _sync_service_instance
    if _sync_service_instance is None:
        _sync_service_instance = create_riskcast_service()
    return _sync_service_instance
