"""
Audit Service - The BRAIN of Accountability.

This service is the central point for all audit operations in RISKCAST.
EVERY decision MUST go through this service.

Usage:
    audit = AuditService(repository)
    
    # Before decision generation
    snapshot = await audit.capture_inputs(signal, reality, context)
    
    # After decision generation
    await audit.record_decision(decision, snapshot, processing)
    
    # On delivery
    await audit.record_delivery(decision_id, channel, status)
    
    # On outcome
    await audit.record_outcome(decision_id, outcome)
    
    # Verify integrity
    verification = await audit.verify_chain_integrity()
"""

from datetime import datetime, timedelta
from typing import Optional, Any
import structlog
import asyncio

from app.audit.schemas import (
    AuditEventType,
    AuditRecord,
    InputSnapshot,
    ProcessingRecord,
    AuditChainVerification,
    DecisionAuditTrail,
)

logger = structlog.get_logger(__name__)


class AuditService:
    """
    Central service for all audit operations.
    
    CRITICAL: This service MUST be called for:
    1. Before decision generation (capture inputs)
    2. After decision generation (record decision)
    3. On every delivery attempt
    4. On every user interaction
    5. On every outcome record
    
    The audit service maintains chain integrity by:
    - Tracking sequence numbers monotonically
    - Linking each record to the previous via hash
    - Detecting tampering through verification
    
    Thread Safety:
    - Uses asyncio locks for sequence number generation
    - Safe for concurrent use in async context
    """
    
    def __init__(self, repository: "AuditRepository"):
        """
        Initialize audit service.
        
        Args:
            repository: Repository for persistent storage
        """
        self._repo = repository
        self._last_sequence: int = 0
        self._last_hash: str = "genesis"
        self._lock = asyncio.Lock()
        self._initialized = False
    
    async def initialize(self) -> None:
        """
        Initialize from existing chain.
        
        MUST be called before using the service.
        Loads the last sequence number and hash from storage.
        """
        async with self._lock:
            if self._initialized:
                return
            
            last_record = await self._repo.get_last_record()
            if last_record:
                self._last_sequence = last_record.sequence_number
                self._last_hash = last_record.record_hash
                logger.info(
                    "audit_service_initialized",
                    last_sequence=self._last_sequence,
                    has_existing_records=True,
                )
            else:
                logger.info(
                    "audit_service_initialized",
                    last_sequence=0,
                    has_existing_records=False,
                )
            
            self._initialized = True
    
    # =========================================================================
    # INPUT CAPTURE - BEFORE DECISION GENERATION
    # =========================================================================
    
    async def capture_inputs(
        self,
        signal: Any,
        reality: Any,
        context: Any,
    ) -> InputSnapshot:
        """
        Capture immutable snapshot of all inputs BEFORE decision generation.
        
        This is CRITICAL for:
        - Reproducibility: Can re-run decision with same inputs
        - Legal defense: Prove what data was available
        - Debugging: Understand why decision was made
        - Calibration: Compare predictions to outcomes
        
        Args:
            signal: OmenSignal triggering this decision
            reality: RealitySnapshot from Oracle
            context: CustomerContext
            
        Returns:
            InputSnapshot with all data hashed for integrity
        """
        await self._ensure_initialized()
        
        # Create snapshot
        snapshot = InputSnapshot.capture(
            signal=signal,
            reality=reality,
            context=context,
        )
        
        # Store snapshot
        await self._repo.store_snapshot(snapshot)
        
        # Record audit event
        await self._record_event(
            event_type=AuditEventType.DECISION_INPUT_CAPTURED,
            entity_type="snapshot",
            entity_id=snapshot.snapshot_id,
            actor_type="system",
            payload={
                "signal_id": snapshot.signal_id,
                "customer_id": snapshot.customer_id,
                "combined_hash": snapshot.combined_hash,
                "reality_staleness_seconds": snapshot.reality_staleness_seconds,
                "signal_hash": snapshot.signal_hash[:16] + "...",  # Truncated for logging
            },
        )
        
        logger.info(
            "inputs_captured",
            snapshot_id=snapshot.snapshot_id,
            signal_id=snapshot.signal_id,
            customer_id=snapshot.customer_id,
            reality_staleness_seconds=snapshot.reality_staleness_seconds,
        )
        
        return snapshot
    
    # =========================================================================
    # DECISION RECORDING
    # =========================================================================
    
    async def record_decision(
        self,
        decision: Any,  # DecisionObject
        snapshot: InputSnapshot,
        processing: ProcessingRecord,
    ) -> str:
        """
        Record a generated decision with full provenance.
        
        Args:
            decision: The generated DecisionObject
            snapshot: Input snapshot captured before generation
            processing: Processing record with model/config info
            
        Returns:
            Audit record ID
        """
        await self._ensure_initialized()
        
        # Store processing record
        await self._repo.store_processing_record(processing)
        
        # Extract decision info
        decision_dict = decision.model_dump(mode="json") if hasattr(decision, "model_dump") else dict(decision)
        decision_id = decision_dict.get("decision_id", "unknown")
        
        # Compute decision hash (immutable parts only)
        decision_hash = self._hash_decision(decision_dict)
        
        # Record audit event
        audit_id = await self._record_event(
            event_type=AuditEventType.DECISION_GENERATED,
            entity_type="decision",
            entity_id=decision_id,
            actor_type="system",
            payload={
                "snapshot_id": snapshot.snapshot_id,
                "processing_record_id": processing.record_id,
                "model_version": processing.model_version,
                "action_type": decision_dict.get("q5_action", {}).get("action_type", "unknown"),
                "confidence": decision_dict.get("q6_confidence", {}).get("score", 0),
                "exposure_usd": decision_dict.get("q3_severity", {}).get("total_exposure_usd", 0),
                "decision_hash": decision_hash,
                "computation_time_ms": processing.computation_time_ms,
                "warnings": processing.warnings,
            },
        )
        
        logger.info(
            "decision_recorded",
            decision_id=decision_id,
            snapshot_id=snapshot.snapshot_id,
            model_version=processing.model_version,
            computation_time_ms=processing.computation_time_ms,
        )
        
        return audit_id
    
    # =========================================================================
    # DELIVERY RECORDING
    # =========================================================================
    
    async def record_delivery(
        self,
        decision_id: str,
        channel: str,
        status: str,
        message_id: Optional[str] = None,
        recipient: Optional[str] = None,
        error: Optional[str] = None,
    ) -> str:
        """
        Record a delivery attempt.
        
        Args:
            decision_id: ID of the decision being delivered
            channel: Delivery channel (whatsapp, email, sms)
            status: Delivery status (sent, delivered, failed)
            message_id: External message ID if available
            recipient: Recipient identifier (masked for privacy)
            error: Error message if delivery failed
            
        Returns:
            Audit record ID
        """
        await self._ensure_initialized()
        
        audit_id = await self._record_event(
            event_type=AuditEventType.DECISION_DELIVERED,
            entity_type="decision",
            entity_id=decision_id,
            actor_type="system",
            payload={
                "channel": channel,
                "status": status,
                "message_id": message_id,
                "recipient": self._mask_recipient(recipient) if recipient else None,
                "error": error,
            },
        )
        
        log_level = "info" if status != "failed" else "warning"
        getattr(logger, log_level)(
            "delivery_recorded",
            decision_id=decision_id,
            channel=channel,
            status=status,
        )
        
        return audit_id
    
    async def record_acknowledgment(
        self,
        decision_id: str,
        acknowledged_by: Optional[str] = None,
    ) -> str:
        """Record when a decision is acknowledged by the customer."""
        await self._ensure_initialized()
        
        return await self._record_event(
            event_type=AuditEventType.DECISION_ACKNOWLEDGED,
            entity_type="decision",
            entity_id=decision_id,
            actor_type="user" if acknowledged_by else "system",
            actor_id=acknowledged_by,
            payload={
                "acknowledged_at": datetime.utcnow().isoformat(),
            },
        )
    
    async def record_action_taken(
        self,
        decision_id: str,
        action_type: str,
        action_details: Optional[dict] = None,
        taken_by: Optional[str] = None,
    ) -> str:
        """Record when customer takes action on a decision."""
        await self._ensure_initialized()
        
        return await self._record_event(
            event_type=AuditEventType.DECISION_ACTED_UPON,
            entity_type="decision",
            entity_id=decision_id,
            actor_type="user" if taken_by else "system",
            actor_id=taken_by,
            payload={
                "action_type": action_type,
                "action_details": action_details or {},
                "acted_at": datetime.utcnow().isoformat(),
            },
        )
    
    # =========================================================================
    # HUMAN INTERACTION RECORDING
    # =========================================================================
    
    async def record_human_override(
        self,
        decision_id: str,
        user_id: str,
        original_action: str,
        new_action: str,
        reason: str,
        reason_category: Optional[str] = None,
    ) -> str:
        """
        Record when a human overrides a decision.
        
        CRITICAL: This is logged as a WARNING because overrides
        may indicate system issues or calibration problems.
        """
        await self._ensure_initialized()
        
        audit_id = await self._record_event(
            event_type=AuditEventType.HUMAN_OVERRIDE,
            entity_type="decision",
            entity_id=decision_id,
            actor_type="user",
            actor_id=user_id,
            payload={
                "original_action": original_action,
                "new_action": new_action,
                "reason": reason,
                "reason_category": reason_category,
                "overridden_at": datetime.utcnow().isoformat(),
            },
        )
        
        logger.warning(
            "human_override_recorded",
            decision_id=decision_id,
            user_id=user_id,
            original_action=original_action,
            new_action=new_action,
            reason_category=reason_category,
        )
        
        return audit_id
    
    async def record_escalation(
        self,
        decision_id: str,
        trigger: str,
        reason: str,
        escalated_to: list[str],
        confidence_at_escalation: float,
        exposure_usd: Optional[float] = None,
    ) -> str:
        """Record when a decision is escalated to human review."""
        await self._ensure_initialized()
        
        return await self._record_event(
            event_type=AuditEventType.HUMAN_ESCALATION,
            entity_type="decision",
            entity_id=decision_id,
            actor_type="system",
            payload={
                "trigger": trigger,
                "reason": reason,
                "escalated_to": escalated_to,
                "confidence_at_escalation": confidence_at_escalation,
                "exposure_usd": exposure_usd,
                "escalated_at": datetime.utcnow().isoformat(),
            },
        )
    
    async def record_escalation_resolution(
        self,
        escalation_id: str,
        decision_id: str,
        resolved_by: str,
        resolution: str,
        final_action: str,
        resolution_reason: str,
    ) -> str:
        """Record resolution of an escalation."""
        await self._ensure_initialized()
        
        return await self._record_event(
            event_type=AuditEventType.HUMAN_ESCALATION_RESOLVED,
            entity_type="decision",
            entity_id=decision_id,
            actor_type="user",
            actor_id=resolved_by,
            payload={
                "escalation_id": escalation_id,
                "resolution": resolution,
                "final_action": final_action,
                "resolution_reason": resolution_reason,
                "resolved_at": datetime.utcnow().isoformat(),
            },
        )
    
    async def record_feedback(
        self,
        decision_id: str,
        user_id: str,
        feedback_type: str,
        rating: int,
        comment: Optional[str] = None,
        would_follow_again: Optional[bool] = None,
    ) -> str:
        """Record user feedback on a decision."""
        await self._ensure_initialized()
        
        return await self._record_event(
            event_type=AuditEventType.HUMAN_FEEDBACK,
            entity_type="decision",
            entity_id=decision_id,
            actor_type="user",
            actor_id=user_id,
            payload={
                "feedback_type": feedback_type,
                "rating": rating,
                "comment": comment,
                "would_follow_again": would_follow_again,
            },
        )
    
    # =========================================================================
    # OUTCOME RECORDING
    # =========================================================================
    
    async def record_outcome(
        self,
        decision_id: str,
        actual_outcome: dict,
        accuracy_assessment: str,
        prediction_result: Optional[str] = None,
    ) -> str:
        """
        Record actual outcome for decision validation.
        
        This is critical for calibration and continuous improvement.
        """
        await self._ensure_initialized()
        
        return await self._record_event(
            event_type=AuditEventType.DECISION_OUTCOME_RECORDED,
            entity_type="decision",
            entity_id=decision_id,
            actor_type="system",
            payload={
                "actual_outcome": actual_outcome,
                "accuracy_assessment": accuracy_assessment,
                "prediction_result": prediction_result,
                "recorded_at": datetime.utcnow().isoformat(),
            },
        )
    
    # =========================================================================
    # CHAIN VERIFICATION
    # =========================================================================
    
    async def verify_chain_integrity(
        self,
        start_sequence: int = 0,
        end_sequence: Optional[int] = None,
    ) -> AuditChainVerification:
        """
        Verify cryptographic integrity of audit chain.
        
        Checks:
        1. Each record's hash matches its contents
        2. Each record links to the previous via previous_hash
        3. Sequence numbers are contiguous
        
        Args:
            start_sequence: Starting sequence number (default: beginning)
            end_sequence: Ending sequence number (default: all)
            
        Returns:
            AuditChainVerification with results
        """
        await self._ensure_initialized()
        
        records = await self._repo.get_records_range(start_sequence, end_sequence)
        
        if not records:
            return AuditChainVerification(
                is_valid=True,
                records_checked=0,
            )
        
        expected_hash = "genesis" if start_sequence == 0 else None
        expected_sequence = start_sequence
        
        for i, record in enumerate(records):
            # Check sequence continuity
            if record.sequence_number != expected_sequence:
                return AuditChainVerification(
                    is_valid=False,
                    records_checked=i,
                    first_invalid_sequence=record.sequence_number,
                    error_type="sequence_gap",
                    error_message=f"Expected sequence {expected_sequence}, got {record.sequence_number}",
                )
            
            # Check chain linkage
            if expected_hash and record.previous_hash != expected_hash:
                return AuditChainVerification(
                    is_valid=False,
                    records_checked=i,
                    first_invalid_sequence=record.sequence_number,
                    error_type="chain_broken",
                    error_message=f"Chain broken at sequence {record.sequence_number}: expected previous_hash {expected_hash[:16]}..., got {record.previous_hash[:16]}...",
                )
            
            # Verify record integrity
            if not record.verify_integrity():
                return AuditChainVerification(
                    is_valid=False,
                    records_checked=i,
                    first_invalid_sequence=record.sequence_number,
                    error_type="record_tampered",
                    error_message=f"Record tampered at sequence {record.sequence_number}",
                )
            
            expected_hash = record.record_hash
            expected_sequence += 1
        
        logger.info(
            "chain_verification_complete",
            records_checked=len(records),
            is_valid=True,
        )
        
        return AuditChainVerification(
            is_valid=True,
            records_checked=len(records),
        )
    
    # =========================================================================
    # RETRIEVAL METHODS
    # =========================================================================
    
    async def get_decision_audit_trail(
        self,
        decision_id: str,
    ) -> DecisionAuditTrail:
        """
        Get complete audit trail for a decision.
        
        Includes input snapshot, processing record, and all audit events.
        """
        await self._ensure_initialized()
        
        # Get all audit events for this decision
        events = await self._repo.get_records_for_entity("decision", decision_id)
        
        # Find snapshot and processing record IDs from events
        snapshot_id = None
        processing_id = None
        customer_id = None
        created_at = None
        delivered_at = None
        acknowledged_at = None
        outcome_at = None
        
        for event in events:
            if event.event_type == AuditEventType.DECISION_GENERATED:
                snapshot_id = event.payload.get("snapshot_id")
                processing_id = event.payload.get("processing_record_id")
                created_at = event.timestamp
            elif event.event_type == AuditEventType.DECISION_DELIVERED:
                if event.payload.get("status") == "delivered":
                    delivered_at = event.timestamp
            elif event.event_type == AuditEventType.DECISION_ACKNOWLEDGED:
                acknowledged_at = event.timestamp
            elif event.event_type == AuditEventType.DECISION_OUTCOME_RECORDED:
                outcome_at = event.timestamp
            
            # Extract customer_id from input capture event
            if event.event_type == AuditEventType.DECISION_INPUT_CAPTURED:
                customer_id = event.payload.get("customer_id")
        
        # Load snapshot and processing record
        snapshot = await self._repo.get_snapshot(snapshot_id) if snapshot_id else None
        processing = await self._repo.get_processing_record(processing_id) if processing_id else None
        
        if snapshot:
            customer_id = snapshot.customer_id
        
        return DecisionAuditTrail(
            decision_id=decision_id,
            customer_id=customer_id or "unknown",
            input_snapshot=snapshot,
            processing_record=processing,
            audit_events=events,
            created_at=created_at,
            delivered_at=delivered_at,
            acknowledged_at=acknowledged_at,
            outcome_recorded_at=outcome_at,
        )
    
    async def get_snapshot(self, snapshot_id: str) -> Optional[InputSnapshot]:
        """Get an input snapshot by ID."""
        return await self._repo.get_snapshot(snapshot_id)
    
    async def get_snapshot_for_decision(self, decision_id: str) -> Optional[InputSnapshot]:
        """Get the input snapshot for a decision."""
        # Find the DECISION_GENERATED event
        events = await self._repo.get_records_for_entity("decision", decision_id)
        for event in events:
            if event.event_type == AuditEventType.DECISION_GENERATED:
                snapshot_id = event.payload.get("snapshot_id")
                if snapshot_id:
                    return await self._repo.get_snapshot(snapshot_id)
        return None
    
    # =========================================================================
    # INTERNAL METHODS
    # =========================================================================
    
    async def _ensure_initialized(self) -> None:
        """Ensure service is initialized."""
        if not self._initialized:
            await self.initialize()
    
    async def _record_event(
        self,
        event_type: AuditEventType,
        entity_type: str,
        entity_id: str,
        actor_type: str,
        payload: dict,
        actor_id: Optional[str] = None,
    ) -> str:
        """
        Record an audit event with chain integrity.
        
        Thread-safe via asyncio lock.
        """
        async with self._lock:
            self._last_sequence += 1
            
            record = AuditRecord(
                event_type=event_type,
                entity_type=entity_type,
                entity_id=entity_id,
                actor_type=actor_type,
                actor_id=actor_id,
                payload=payload,
                sequence_number=self._last_sequence,
                previous_hash=self._last_hash,
            ).finalize()
            
            await self._repo.store_record(record)
            self._last_hash = record.record_hash
            
            logger.debug(
                "audit_event_recorded",
                event_type=event_type.value,
                entity_id=entity_id,
                sequence=self._last_sequence,
            )
            
            return record.audit_id
    
    @staticmethod
    def _hash_decision(decision_dict: dict) -> str:
        """
        Hash decision for integrity verification.
        
        Only hashes immutable parts (not feedback, not acted_upon).
        """
        import hashlib
        import json
        
        immutable_parts = {
            "decision_id": decision_dict.get("decision_id"),
            "customer_id": decision_dict.get("customer_id"),
            "signal_id": decision_dict.get("signal_id"),
            "q1_what": decision_dict.get("q1_what"),
            "q2_when": decision_dict.get("q2_when"),
            "q3_severity": decision_dict.get("q3_severity"),
            "q4_why": decision_dict.get("q4_why"),
            "q5_action": decision_dict.get("q5_action"),
            "q6_confidence": decision_dict.get("q6_confidence"),
            "q7_inaction": decision_dict.get("q7_inaction"),
        }
        
        json_str = json.dumps(immutable_parts, sort_keys=True, default=str)
        return hashlib.sha256(json_str.encode()).hexdigest()
    
    @staticmethod
    def _mask_recipient(recipient: str) -> str:
        """
        Mask recipient for privacy in audit logs.
        
        Examples:
        - +84123456789 -> +84***6789
        - email@domain.com -> em***@domain.com
        """
        if not recipient:
            return ""
        
        if recipient.startswith("+"):
            # Phone number
            if len(recipient) > 6:
                return recipient[:3] + "***" + recipient[-4:]
            return "***"
        elif "@" in recipient:
            # Email
            parts = recipient.split("@")
            if len(parts[0]) > 2:
                return parts[0][:2] + "***@" + parts[1]
            return "***@" + parts[1]
        else:
            # Unknown format
            if len(recipient) > 4:
                return recipient[:2] + "***" + recipient[-2:]
            return "***"
