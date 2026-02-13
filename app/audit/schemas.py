"""
Audit Trail Schemas for Cryptographic Integrity.

These schemas ensure EVERY decision can be:
1. Reproduced with the same inputs
2. Traced to its data sources
3. Verified for tampering
4. Defended in legal/regulatory contexts

CRITICAL: Audit records are IMMUTABLE once created.
The cryptographic chain detects any tampering.
"""

from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field, computed_field
from enum import Enum
import hashlib
import json
import uuid


# ============================================================================
# AUDIT EVENT TYPES
# ============================================================================


class AuditEventType(str, Enum):
    """
    Types of auditable events.
    
    Every significant action in RISKCAST must have an event type.
    """
    
    # Decision lifecycle events
    DECISION_INPUT_CAPTURED = "decision.input.captured"
    DECISION_GENERATED = "decision.generated"
    DECISION_DELIVERED = "decision.delivered"
    DECISION_ACKNOWLEDGED = "decision.acknowledged"
    DECISION_ACTED_UPON = "decision.acted_upon"
    DECISION_OUTCOME_RECORDED = "decision.outcome.recorded"
    DECISION_EXPIRED = "decision.expired"
    
    # Human interaction events
    HUMAN_OVERRIDE = "human.override"
    HUMAN_ESCALATION = "human.escalation"
    HUMAN_ESCALATION_RESOLVED = "human.escalation.resolved"
    HUMAN_FEEDBACK = "human.feedback"
    
    # System events
    MODEL_VERSION_CHANGED = "system.model.changed"
    CONFIG_CHANGED = "system.config.changed"
    DEGRADATION_LEVEL_CHANGED = "system.degradation.changed"
    CIRCUIT_BREAKER_TRIPPED = "system.circuit_breaker.tripped"
    
    # Security events
    API_KEY_CREATED = "security.api_key.created"
    API_KEY_REVOKED = "security.api_key.revoked"
    UNAUTHORIZED_ACCESS = "security.unauthorized_access"
    
    # Customer events
    CUSTOMER_CREATED = "customer.created"
    CUSTOMER_UPDATED = "customer.updated"
    SHIPMENT_CREATED = "shipment.created"
    SHIPMENT_UPDATED = "shipment.updated"


# ============================================================================
# INPUT SNAPSHOT - CRITICAL FOR REPRODUCIBILITY
# ============================================================================


class SignalSnapshot(BaseModel):
    """Snapshot of signal data at decision time."""
    
    signal_id: str
    probability: float
    confidence: float
    category: str
    chokepoint: str
    source_timestamps: dict[str, str] = Field(
        default_factory=dict,
        description="Timestamp of each data source",
    )
    raw_data: dict = Field(
        default_factory=dict,
        description="Complete signal data",
    )


class RealitySnapshot(BaseModel):
    """Snapshot of reality data at decision time."""
    
    snapshot_time: datetime
    staleness_seconds: int
    chokepoint_health: dict = Field(default_factory=dict)
    vessel_data: dict = Field(default_factory=dict)
    freight_rates: dict = Field(default_factory=dict)
    raw_data: dict = Field(default_factory=dict)


class CustomerContextSnapshot(BaseModel):
    """Snapshot of customer context at decision time."""
    
    customer_id: str
    context_version: int
    profile_hash: str
    active_shipments: list[dict] = Field(default_factory=list)
    risk_tolerance: str
    raw_data: dict = Field(default_factory=dict)


class InputSnapshot(BaseModel):
    """
    Immutable snapshot of ALL inputs at decision time.
    
    This is CRITICAL for:
    - Reproducibility: Can re-run decision with exact same inputs
    - Legal defense: Prove what data was available at decision time
    - Debugging: Understand why a specific decision was made
    - Calibration: Compare predictions to actual outcomes
    
    MUST be captured BEFORE decision generation begins.
    """
    
    model_config = {"frozen": True}  # Immutable after creation
    
    # Identity
    snapshot_id: str = Field(
        default_factory=lambda: f"snap_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}",
        description="Unique snapshot identifier",
    )
    captured_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this snapshot was captured",
    )
    
    # Signal data (from OMEN)
    signal_data: dict = Field(
        description="Complete signal data as dictionary",
    )
    signal_hash: str = Field(
        description="SHA-256 hash of signal data",
    )
    signal_id: str = Field(
        description="Signal identifier for reference",
    )
    
    # Reality data (from ORACLE)  
    reality_data: dict = Field(
        description="Complete reality snapshot as dictionary",
    )
    reality_hash: str = Field(
        description="SHA-256 hash of reality data",
    )
    reality_staleness_seconds: int = Field(
        ge=0,
        description="How old the reality data was at capture time",
    )
    
    # Customer context
    customer_context_data: dict = Field(
        description="Complete customer context as dictionary",
    )
    customer_context_hash: str = Field(
        description="SHA-256 hash of customer context",
    )
    customer_id: str = Field(
        description="Customer identifier",
    )
    customer_context_version: int = Field(
        ge=0,
        description="Version of customer context at capture time",
    )
    
    # Combined integrity hash
    combined_hash: str = Field(
        description="SHA-256 hash of all input hashes combined",
    )
    
    @classmethod
    def capture(
        cls,
        signal: Any,  # OmenSignal
        reality: Any,  # RealitySnapshot from Oracle
        context: Any,  # CustomerContext
    ) -> "InputSnapshot":
        """
        Capture immutable snapshot of all inputs.
        
        MUST be called BEFORE decision generation begins.
        
        Args:
            signal: The OMEN signal triggering this decision
            reality: The ORACLE reality snapshot
            context: The customer context
            
        Returns:
            InputSnapshot with all data hashed for integrity
        """
        # Convert to dictionaries
        signal_dict = signal.model_dump(mode="json") if hasattr(signal, "model_dump") else dict(signal)
        reality_dict = reality.model_dump(mode="json") if hasattr(reality, "model_dump") else dict(reality)
        context_dict = context.model_dump(mode="json") if hasattr(context, "model_dump") else dict(context)
        
        # Compute individual hashes
        signal_hash = cls._hash_dict(signal_dict)
        reality_hash = cls._hash_dict(reality_dict)
        context_hash = cls._hash_dict(context_dict)
        
        # Compute combined hash
        combined = f"{signal_hash}:{reality_hash}:{context_hash}"
        combined_hash = hashlib.sha256(combined.encode()).hexdigest()
        
        # Calculate staleness
        reality_timestamp = reality_dict.get("timestamp") or reality_dict.get("captured_at")
        if isinstance(reality_timestamp, str):
            try:
                reality_timestamp = datetime.fromisoformat(reality_timestamp.replace("Z", "+00:00"))
            except:
                reality_timestamp = datetime.utcnow()
        staleness = int((datetime.utcnow() - reality_timestamp).total_seconds()) if reality_timestamp else 0
        
        # Extract identifiers
        signal_id = signal_dict.get("signal_id", "unknown")
        customer_id = context_dict.get("profile", {}).get("customer_id") or context_dict.get("customer_id", "unknown")
        context_version = context_dict.get("version", 0)
        
        return cls(
            signal_data=signal_dict,
            signal_hash=signal_hash,
            signal_id=signal_id,
            reality_data=reality_dict,
            reality_hash=reality_hash,
            reality_staleness_seconds=max(0, staleness),
            customer_context_data=context_dict,
            customer_context_hash=context_hash,
            customer_id=customer_id,
            customer_context_version=context_version,
            combined_hash=combined_hash,
        )
    
    @staticmethod
    def _hash_dict(d: dict) -> str:
        """
        Compute deterministic SHA-256 hash of dictionary.
        
        Uses sorted keys to ensure consistent hashing.
        """
        json_str = json.dumps(d, sort_keys=True, default=str)
        return hashlib.sha256(json_str.encode()).hexdigest()
    
    def verify_integrity(self) -> bool:
        """
        Verify that snapshot data has not been tampered with.
        
        Returns:
            True if all hashes match, False if tampering detected.
        """
        # Verify individual hashes
        if self._hash_dict(self.signal_data) != self.signal_hash:
            return False
        if self._hash_dict(self.reality_data) != self.reality_hash:
            return False
        if self._hash_dict(self.customer_context_data) != self.customer_context_hash:
            return False
        
        # Verify combined hash
        combined = f"{self.signal_hash}:{self.reality_hash}:{self.customer_context_hash}"
        expected_combined = hashlib.sha256(combined.encode()).hexdigest()
        if expected_combined != self.combined_hash:
            return False
        
        return True


# ============================================================================
# PROCESSING RECORD - HOW THE DECISION WAS COMPUTED
# ============================================================================


class ProcessingRecord(BaseModel):
    """
    Record of HOW a decision was computed.
    
    Captures:
    - Model version used
    - Configuration active at the time
    - Reasoning trace reference
    - Performance metrics
    - Any warnings or degradation
    """
    
    # Identity
    record_id: str = Field(
        default_factory=lambda: f"proc_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}",
        description="Unique processing record ID",
    )
    
    # Model information
    model_version: str = Field(
        description="Version of decision model, e.g., riskcast-v2.3.1",
    )
    model_hash: str = Field(
        default="",
        description="Hash of model parameters/weights",
    )
    
    # Configuration
    config_version: str = Field(
        description="Version of configuration, e.g., config-2024-02-05",
    )
    config_hash: str = Field(
        default="",
        description="Hash of active configuration",
    )
    
    # Reasoning trace
    reasoning_trace_id: str = Field(
        default="",
        description="Link to detailed reasoning trace (if multi-layer reasoning enabled)",
    )
    layers_executed: list[str] = Field(
        default_factory=list,
        description="Which reasoning layers were executed",
    )
    
    # Performance metrics
    computation_time_ms: int = Field(
        ge=0,
        description="Time to generate decision in milliseconds",
    )
    memory_used_mb: float = Field(
        ge=0,
        default=0.0,
        description="Memory used during computation",
    )
    
    # Warnings and flags
    warnings: list[str] = Field(
        default_factory=list,
        description="Any warnings generated during processing",
    )
    degradation_level: int = Field(
        default=0,
        ge=0,
        le=4,
        description="System degradation level: 0=full, 1-4=degraded",
    )
    
    # Data quality flags
    stale_data_sources: list[str] = Field(
        default_factory=list,
        description="Data sources that were stale",
    )
    missing_data_sources: list[str] = Field(
        default_factory=list,
        description="Data sources that were unavailable",
    )
    
    @computed_field
    @property
    def has_warnings(self) -> bool:
        """Check if any warnings were generated."""
        return len(self.warnings) > 0
    
    @computed_field
    @property
    def is_degraded(self) -> bool:
        """Check if system was in degraded mode."""
        return self.degradation_level > 0


# ============================================================================
# AUDIT RECORD - SINGLE IMMUTABLE RECORD WITH CHAIN
# ============================================================================


class AuditRecord(BaseModel):
    """
    Single immutable audit record with cryptographic chain.
    
    Records are chained like a blockchain:
    record_n.previous_hash = record_(n-1).record_hash
    
    This allows detection of:
    - Tampered records (hash mismatch)
    - Deleted records (chain broken)
    - Inserted records (sequence mismatch)
    """
    
    # Identity
    audit_id: str = Field(
        default_factory=lambda: f"aud_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}",
        description="Unique audit record ID",
    )
    event_type: AuditEventType = Field(
        description="Type of event being audited",
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this event occurred",
    )
    
    # Entity reference (what this audit is about)
    entity_type: str = Field(
        description="Type of entity: decision, customer, signal, etc.",
    )
    entity_id: str = Field(
        description="ID of the entity",
    )
    
    # Actor (who/what triggered this event)
    actor_type: str = Field(
        description="Type of actor: system, user, admin, scheduler, api",
    )
    actor_id: Optional[str] = Field(
        default=None,
        description="User/API key ID if human or API-triggered",
    )
    
    # Event payload
    payload: dict = Field(
        default_factory=dict,
        description="Event-specific data",
    )
    payload_hash: str = Field(
        default="",
        description="SHA-256 hash of payload",
    )
    
    # Chain integrity fields
    sequence_number: int = Field(
        ge=0,
        description="Monotonically increasing sequence number",
    )
    previous_hash: str = Field(
        description="Hash of previous record in chain",
    )
    record_hash: str = Field(
        default="",
        description="Hash of this record (computed after creation)",
    )
    
    def compute_hash(self) -> str:
        """
        Compute SHA-256 hash of this record.
        
        Excludes record_hash field to avoid circular dependency.
        """
        data = self.model_dump(exclude={"record_hash"})
        json_str = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(json_str.encode()).hexdigest()
    
    def finalize(self) -> "AuditRecord":
        """
        Finalize the record by computing its hash.
        
        Also computes payload hash if not set.
        
        Returns self for chaining.
        """
        if not self.payload_hash:
            self.payload_hash = hashlib.sha256(
                json.dumps(self.payload, sort_keys=True, default=str).encode()
            ).hexdigest()
        
        self.record_hash = self.compute_hash()
        return self
    
    def verify_integrity(self) -> bool:
        """
        Verify that this record has not been tampered with.
        """
        # Verify payload hash
        expected_payload_hash = hashlib.sha256(
            json.dumps(self.payload, sort_keys=True, default=str).encode()
        ).hexdigest()
        if expected_payload_hash != self.payload_hash:
            return False
        
        # Verify record hash
        expected_record_hash = self.compute_hash()
        if expected_record_hash != self.record_hash:
            return False
        
        return True


# ============================================================================
# CHAIN VERIFICATION RESULT
# ============================================================================


class AuditChainVerification(BaseModel):
    """
    Result of verifying the integrity of an audit chain.
    
    Used for compliance checks and tamper detection.
    """
    
    is_valid: bool = Field(
        description="Whether the chain integrity is intact",
    )
    records_checked: int = Field(
        ge=0,
        description="Number of records verified",
    )
    first_invalid_sequence: Optional[int] = Field(
        default=None,
        description="Sequence number of first invalid record (if any)",
    )
    error_type: Optional[str] = Field(
        default=None,
        description="Type of error: chain_broken, record_tampered, sequence_gap",
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Detailed error message",
    )
    verified_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When verification was performed",
    )
    
    @computed_field
    @property
    def summary(self) -> str:
        """Human-readable summary of verification result."""
        if self.is_valid:
            return f"Chain integrity verified: {self.records_checked} records checked"
        else:
            return f"Chain integrity FAILED at sequence {self.first_invalid_sequence}: {self.error_type}"


# ============================================================================
# DECISION AUDIT TRAIL - COMPLETE AUDIT FOR A DECISION
# ============================================================================


class DecisionAuditTrail(BaseModel):
    """
    Complete audit trail for a single decision.
    
    Combines all audit information for legal/regulatory defense.
    """
    
    decision_id: str
    customer_id: str
    
    # Input snapshot
    input_snapshot: Optional[InputSnapshot] = None
    
    # Processing record
    processing_record: Optional[ProcessingRecord] = None
    
    # All audit events for this decision
    audit_events: list[AuditRecord] = Field(default_factory=list)
    
    # Verification status
    chain_verification: Optional[AuditChainVerification] = None
    
    # Timeline
    created_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None
    outcome_recorded_at: Optional[datetime] = None
    
    @computed_field
    @property
    def is_complete(self) -> bool:
        """Check if audit trail has all required components."""
        return (
            self.input_snapshot is not None and
            self.processing_record is not None and
            len(self.audit_events) > 0
        )
    
    @computed_field
    @property
    def event_count(self) -> int:
        """Number of audit events."""
        return len(self.audit_events)
