"""
SQLAlchemy ORM Models.

Database models for RISKCAST entities:
- Customers
- Shipments
- Decisions
- Alerts

Uses async SQLAlchemy 2.0 patterns.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SQLEnum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    JSON,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.riskcast.constants import (
    ActionType,
    RiskTolerance,
    ShipmentStatus,
    Severity,
    Urgency,
)


# ============================================================================
# CUSTOMER MODEL
# ============================================================================


class CustomerModel(Base):
    """
    Customer entity.

    Represents a company/customer using RISKCAST.
    """

    __tablename__ = "customers"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    customer_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)

    # Company info
    company_name: Mapped[str] = mapped_column(String(200), nullable=False)
    industry: Mapped[Optional[str]] = mapped_column(String(100))

    # Contact
    primary_phone: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    secondary_phone: Mapped[Optional[str]] = mapped_column(String(20))
    email: Mapped[Optional[str]] = mapped_column(String(100))

    # Preferences
    risk_tolerance: Mapped[str] = mapped_column(
        String(20),
        default=RiskTolerance.BALANCED.value,
        nullable=False,
    )
    notification_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    whatsapp_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    email_enabled: Mapped[bool] = mapped_column(Boolean, default=False)

    # Routes (stored as JSON array)
    primary_routes: Mapped[list] = mapped_column(JSON, default=list)
    relevant_chokepoints: Mapped[list] = mapped_column(JSON, default=list)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    tier: Mapped[str] = mapped_column(String(20), default="standard")

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    shipments: Mapped[list["ShipmentModel"]] = relationship(
        "ShipmentModel",
        back_populates="customer",
        cascade="all, delete-orphan",
    )
    decisions: Mapped[list["DecisionModel"]] = relationship(
        "DecisionModel",
        back_populates="customer",
        cascade="all, delete-orphan",
    )
    alerts: Mapped[list["AlertModel"]] = relationship(
        "AlertModel",
        back_populates="customer",
        cascade="all, delete-orphan",
    )

    # Indexes
    __table_args__ = (
        Index("ix_customers_phone", "primary_phone"),
        Index("ix_customers_active", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<Customer {self.customer_id}: {self.company_name}>"


# ============================================================================
# SHIPMENT MODEL
# ============================================================================


class ShipmentModel(Base):
    """
    Shipment entity.

    Represents an active or historical shipment.
    """

    __tablename__ = "shipments"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    shipment_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)

    # Foreign key
    customer_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("customers.customer_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Route information
    origin_port: Mapped[str] = mapped_column(String(10), nullable=False)
    destination_port: Mapped[str] = mapped_column(String(10), nullable=False)
    route_code: Mapped[Optional[str]] = mapped_column(String(50))
    route_chokepoints: Mapped[list] = mapped_column(JSON, default=list)

    # Cargo details
    cargo_value_usd: Mapped[float] = mapped_column(Float, nullable=False)
    cargo_description: Mapped[Optional[str]] = mapped_column(Text)
    container_count: Mapped[int] = mapped_column(Integer, default=1)
    container_type: Mapped[str] = mapped_column(String(10), default="40HC")
    hs_code: Mapped[Optional[str]] = mapped_column(String(20))

    # Carrier information
    carrier_code: Mapped[Optional[str]] = mapped_column(String(10))
    carrier_name: Mapped[Optional[str]] = mapped_column(String(100))
    booking_reference: Mapped[Optional[str]] = mapped_column(String(50))
    bill_of_lading: Mapped[Optional[str]] = mapped_column(String(50))

    # Timeline
    etd: Mapped[Optional[datetime]] = mapped_column(DateTime)  # Estimated Time of Departure
    eta: Mapped[Optional[datetime]] = mapped_column(DateTime)  # Estimated Time of Arrival
    actual_departure: Mapped[Optional[datetime]] = mapped_column(DateTime)
    actual_arrival: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Status
    status: Mapped[str] = mapped_column(
        String(20),
        default=ShipmentStatus.BOOKED.value,
        nullable=False,
        index=True,
    )

    # Insurance
    is_insured: Mapped[bool] = mapped_column(Boolean, default=False)
    insurance_value_usd: Mapped[Optional[float]] = mapped_column(Float)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    customer: Mapped["CustomerModel"] = relationship(
        "CustomerModel",
        back_populates="shipments",
    )

    # Indexes
    __table_args__ = (
        Index("ix_shipments_customer", "customer_id"),
        Index("ix_shipments_status", "status"),
        Index("ix_shipments_etd", "etd"),
        Index("ix_shipments_route", "origin_port", "destination_port"),
    )

    def __repr__(self) -> str:
        return f"<Shipment {self.shipment_id}: {self.origin_port} -> {self.destination_port}>"


# ============================================================================
# DECISION MODEL
# ============================================================================


class DecisionModel(Base):
    """
    Decision entity.

    Stores generated decisions for auditing and learning.
    """

    __tablename__ = "decisions"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    decision_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)

    # Foreign keys
    customer_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("customers.customer_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    shipment_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        ForeignKey("shipments.shipment_id", ondelete="SET NULL"),
        index=True,
    )
    signal_id: Mapped[Optional[str]] = mapped_column(String(100), index=True)

    # Decision metadata
    chokepoint: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    urgency: Mapped[str] = mapped_column(String(20), nullable=False)

    # 7 Questions (Q1-Q7) stored as JSON
    q1_what: Mapped[dict] = mapped_column(JSON, nullable=False)
    q2_when: Mapped[dict] = mapped_column(JSON, nullable=False)
    q3_severity: Mapped[dict] = mapped_column(JSON, nullable=False)
    q4_why: Mapped[dict] = mapped_column(JSON, nullable=False)
    q5_action: Mapped[dict] = mapped_column(JSON, nullable=False)
    q6_confidence: Mapped[dict] = mapped_column(JSON, nullable=False)
    q7_inaction: Mapped[dict] = mapped_column(JSON, nullable=False)

    # Impact metrics
    exposure_usd: Mapped[float] = mapped_column(Float, nullable=False)
    potential_loss_usd: Mapped[float] = mapped_column(Float, default=0)
    potential_delay_days: Mapped[float] = mapped_column(Float, default=0)

    # Recommended action
    recommended_action: Mapped[str] = mapped_column(String(50), nullable=False)
    action_cost_usd: Mapped[float] = mapped_column(Float, default=0)
    action_deadline: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Confidence
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)

    # Alternative actions (JSON array)
    alternative_actions: Mapped[list] = mapped_column(JSON, default=list)

    # Status
    is_delivered: Mapped[bool] = mapped_column(Boolean, default=False)
    is_acknowledged: Mapped[bool] = mapped_column(Boolean, default=False)
    is_acted_upon: Mapped[bool] = mapped_column(Boolean, default=False)
    customer_action: Mapped[Optional[str]] = mapped_column(String(50))

    # Validity
    valid_until: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    is_expired: Mapped[bool] = mapped_column(Boolean, default=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False, index=True
    )
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Relationships
    customer: Mapped["CustomerModel"] = relationship(
        "CustomerModel",
        back_populates="decisions",
    )

    # Indexes
    __table_args__ = (
        Index("ix_decisions_customer", "customer_id"),
        Index("ix_decisions_created", "created_at"),
        Index("ix_decisions_chokepoint", "chokepoint"),
        Index("ix_decisions_validity", "valid_until", "is_expired"),
    )

    def __repr__(self) -> str:
        return f"<Decision {self.decision_id}: {self.recommended_action}>"


# ============================================================================
# ALERT MODEL
# ============================================================================


class AlertModel(Base):
    """
    Alert/Notification entity.

    Tracks sent alerts and their delivery status.
    """

    __tablename__ = "alerts"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    alert_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)

    # Foreign keys
    customer_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("customers.customer_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    decision_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        ForeignKey("decisions.decision_id", ondelete="SET NULL"),
        index=True,
    )

    # Alert details
    channel: Mapped[str] = mapped_column(String(20), nullable=False)  # whatsapp, email, sms
    recipient: Mapped[str] = mapped_column(String(100), nullable=False)
    template_name: Mapped[str] = mapped_column(String(100), nullable=False)
    message_content: Mapped[Text] = mapped_column(Text)
    message_hash: Mapped[Optional[str]] = mapped_column(String(64))  # For dedup

    # External IDs
    external_message_id: Mapped[Optional[str]] = mapped_column(String(100))  # Twilio SID, etc.

    # Status
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False, index=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Relationships
    customer: Mapped["CustomerModel"] = relationship(
        "CustomerModel",
        back_populates="alerts",
    )

    # Indexes
    __table_args__ = (
        Index("ix_alerts_customer", "customer_id"),
        Index("ix_alerts_status", "status"),
        Index("ix_alerts_created", "created_at"),
        UniqueConstraint("customer_id", "message_hash", name="uq_alerts_dedup"),
    )

    def __repr__(self) -> str:
        return f"<Alert {self.alert_id}: {self.channel} -> {self.recipient}>"


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def customer_to_model(profile: "CustomerProfile") -> CustomerModel:
    """Convert CustomerProfile Pydantic model to SQLAlchemy model."""
    from app.riskcast.schemas.customer import CustomerProfile

    return CustomerModel(
        customer_id=profile.customer_id,
        company_name=profile.company_name,
        industry=profile.industry,
        primary_phone=profile.primary_phone,
        secondary_phone=profile.secondary_phone,
        email=profile.email,
        risk_tolerance=profile.risk_tolerance.value,
        notification_enabled=profile.notification_enabled,
        whatsapp_enabled=profile.whatsapp_enabled,
        email_enabled=profile.email_enabled,
        primary_routes=profile.primary_routes,
        relevant_chokepoints=profile.relevant_chokepoints,
        is_active=profile.is_active,
        tier=profile.tier,
    )


def shipment_to_model(shipment: "Shipment") -> ShipmentModel:
    """Convert Shipment Pydantic model to SQLAlchemy model."""
    from app.riskcast.schemas.customer import Shipment

    return ShipmentModel(
        shipment_id=shipment.shipment_id,
        customer_id=shipment.customer_id,
        origin_port=shipment.origin_port,
        destination_port=shipment.destination_port,
        route_code=shipment.route_code,
        route_chokepoints=shipment.route_chokepoints,
        cargo_value_usd=shipment.cargo_value_usd,
        cargo_description=shipment.cargo_description,
        container_count=shipment.container_count,
        container_type=shipment.container_type,
        hs_code=shipment.hs_code,
        carrier_code=shipment.carrier_code,
        carrier_name=shipment.carrier_name,
        booking_reference=shipment.booking_reference,
        bill_of_lading=shipment.bill_of_lading,
        etd=shipment.etd,
        eta=shipment.eta,
        actual_departure=shipment.actual_departure,
        actual_arrival=shipment.actual_arrival,
        status=shipment.status.value,
        is_insured=shipment.is_insured,
        insurance_value_usd=shipment.insurance_value_usd,
    )


# ============================================================================
# AUDIT LOG MODEL (CRYPTOGRAPHIC CHAIN)
# ============================================================================


class AuditLogModel(Base):
    """
    Audit log with cryptographic chain integrity.
    
    Records are IMMUTABLE once created - no updates or deletes.
    Each record links to the previous via hash, forming a chain
    that detects tampering.
    """
    
    __tablename__ = "audit_logs"
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    
    # Event classification
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    
    # Entity reference
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    entity_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    
    # Actor information
    actor_type: Mapped[str] = mapped_column(String(50), nullable=False)
    actor_id: Mapped[Optional[str]] = mapped_column(String(255))
    
    # Event payload
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    payload_hash: Mapped[Optional[str]] = mapped_column(String(64))
    
    # Cryptographic chain fields
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False, unique=True, index=True)
    previous_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    record_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    
    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False, index=True
    )
    
    # Indexes for efficient queries
    __table_args__ = (
        Index("ix_audit_logs_entity", "entity_type", "entity_id"),
        Index("ix_audit_logs_event_time", "event_type", "created_at"),
        Index("ix_audit_logs_sequence", "sequence_number"),
    )
    
    def __repr__(self) -> str:
        return f"<AuditLog {self.event_id}: {self.event_type}>"


# ============================================================================
# INPUT SNAPSHOT MODEL
# ============================================================================


class InputSnapshotModel(Base):
    """
    Immutable snapshot of all inputs at decision time.
    
    CRITICAL for:
    - Reproducibility: Re-run decision with same inputs
    - Legal defense: Prove what data was available
    - Debugging: Understand why decision was made
    """
    
    __tablename__ = "input_snapshots"
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    snapshot_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    
    # Signal data (from OMEN)
    signal_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    signal_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    signal_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    
    # Reality data (from ORACLE)
    reality_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    reality_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    reality_staleness_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Customer context
    customer_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    customer_context_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    customer_context_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    customer_context_version: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Combined integrity hash
    combined_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    
    # Timestamp
    captured_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    
    # Indexes
    __table_args__ = (
        Index("ix_input_snapshots_customer", "customer_id"),
        Index("ix_input_snapshots_signal", "signal_id"),
        Index("ix_input_snapshots_captured", "captured_at"),
    )
    
    def __repr__(self) -> str:
        return f"<InputSnapshot {self.snapshot_id}: customer={self.customer_id}>"


# ============================================================================
# PROCESSING RECORD MODEL
# ============================================================================


class ProcessingRecordModel(Base):
    """
    Record of HOW a decision was computed.
    
    Captures model version, configuration, timing, and any warnings.
    """
    
    __tablename__ = "processing_records"
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    record_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    
    # Model information
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    model_hash: Mapped[Optional[str]] = mapped_column(String(64))
    
    # Configuration
    config_version: Mapped[str] = mapped_column(String(50), nullable=False)
    config_hash: Mapped[Optional[str]] = mapped_column(String(64))
    
    # Reasoning trace
    reasoning_trace_id: Mapped[Optional[str]] = mapped_column(String(100))
    layers_executed: Mapped[list] = mapped_column(JSON, default=list)
    
    # Performance metrics
    computation_time_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    memory_used_mb: Mapped[Optional[float]] = mapped_column(Float)
    
    # Warnings and flags
    warnings: Mapped[list] = mapped_column(JSON, default=list)
    degradation_level: Mapped[int] = mapped_column(Integer, default=0)
    
    # Data quality flags
    stale_data_sources: Mapped[list] = mapped_column(JSON, default=list)
    missing_data_sources: Mapped[list] = mapped_column(JSON, default=list)
    
    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    
    def __repr__(self) -> str:
        return f"<ProcessingRecord {self.record_id}: {self.model_version}>"


# ============================================================================
# HUMAN OVERRIDE MODEL
# ============================================================================


class HumanOverrideModel(Base):
    """
    Record of human overrides on decisions.
    
    Tracks when and why humans override system decisions.
    """
    
    __tablename__ = "human_overrides"
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    override_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    
    # Decision reference
    decision_id: Mapped[str] = mapped_column(
        String(100),
        ForeignKey("decisions.decision_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Override details
    original_action: Mapped[str] = mapped_column(String(50), nullable=False)
    new_action: Mapped[str] = mapped_column(String(50), nullable=False)
    new_action_details: Mapped[Optional[dict]] = mapped_column(JSON)
    
    # Reason
    reason_category: Mapped[str] = mapped_column(String(50), nullable=False)
    reason_details: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Actor
    overridden_by: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False, index=True
    )
    
    # Indexes
    __table_args__ = (
        Index("ix_human_overrides_decision", "decision_id"),
        Index("ix_human_overrides_user", "overridden_by"),
    )
    
    def __repr__(self) -> str:
        return f"<HumanOverride {self.override_id}: {self.original_action} -> {self.new_action}>"


# ============================================================================
# ESCALATION MODEL
# ============================================================================


class EscalationModel(Base):
    """
    Record of decisions escalated to human review.
    """
    
    __tablename__ = "escalations"
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    escalation_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    
    # Decision reference
    decision_id: Mapped[str] = mapped_column(
        String(100),
        ForeignKey("decisions.decision_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    customer_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    
    # Escalation details
    trigger: Mapped[str] = mapped_column(String(50), nullable=False)
    trigger_details: Mapped[str] = mapped_column(Text, nullable=False)
    confidence_at_escalation: Mapped[float] = mapped_column(Float, nullable=False)
    exposure_usd: Mapped[Optional[float]] = mapped_column(Float)
    
    # System recommendation
    recommended_action: Mapped[str] = mapped_column(String(50), nullable=False)
    alternative_actions: Mapped[list] = mapped_column(JSON, default=list)
    
    # Routing
    escalated_to: Mapped[list] = mapped_column(JSON, default=list)
    deadline: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    
    # Resolution
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False, index=True)
    resolved_by: Mapped[Optional[str]] = mapped_column(String(255))
    resolution: Mapped[Optional[str]] = mapped_column(String(20))
    final_action: Mapped[Optional[str]] = mapped_column(String(50))
    resolution_reason: Mapped[Optional[str]] = mapped_column(Text)
    
    # Timestamps
    escalated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False, index=True
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    # Indexes
    __table_args__ = (
        Index("ix_escalations_status", "status"),
        Index("ix_escalations_customer", "customer_id"),
    )
    
    def __repr__(self) -> str:
        return f"<Escalation {self.escalation_id}: {self.trigger} -> {self.status}>"


# ============================================================================
# DECISION OUTCOME MODEL (E2 Compliance - Flywheel Persistence)
# ============================================================================


class DecisionOutcomeModel(Base):
    """
    Outcome record for flywheel learning loop.
    
    E2 COMPLIANCE: Persists outcome data to PostgreSQL instead of in-memory.
    
    This model stores:
    - What was predicted (from decision)
    - What actually happened (from outcome tracking)
    - Error metrics (for model improvement)
    - Training data quality flags
    """
    
    __tablename__ = "decision_outcomes"
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    outcome_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    
    # Foreign keys
    decision_id: Mapped[str] = mapped_column(
        String(100),
        ForeignKey("decisions.decision_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    customer_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    
    # === PREDICTIONS (what we said would happen) ===
    predicted_delay_days: Mapped[float] = mapped_column(Float, nullable=False)
    predicted_exposure_usd: Mapped[float] = mapped_column(Float, nullable=False)
    predicted_action_cost_usd: Mapped[float] = mapped_column(Float, nullable=False)
    predicted_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    predicted_action: Mapped[str] = mapped_column(String(50), nullable=False)
    
    # === ACTUALS (what actually happened) ===
    actual_delay_days: Mapped[Optional[float]] = mapped_column(Float)
    actual_loss_usd: Mapped[Optional[float]] = mapped_column(Float)
    actual_action_cost_usd: Mapped[Optional[float]] = mapped_column(Float)
    
    # Action tracking
    action_taken: Mapped[Optional[str]] = mapped_column(String(50))
    action_followed_recommendation: Mapped[Optional[bool]] = mapped_column(Boolean)
    action_success: Mapped[Optional[bool]] = mapped_column(Boolean)
    
    # === ERROR METRICS (for model improvement) ===
    delay_error: Mapped[Optional[float]] = mapped_column(Float)
    delay_error_pct: Mapped[Optional[float]] = mapped_column(Float)
    exposure_error: Mapped[Optional[float]] = mapped_column(Float)
    exposure_error_pct: Mapped[Optional[float]] = mapped_column(Float)
    
    # Accuracy flags
    was_delay_accurate: Mapped[Optional[bool]] = mapped_column(Boolean)  # Within 20%
    was_cost_accurate: Mapped[Optional[bool]] = mapped_column(Boolean)   # Within 30%
    overall_accuracy: Mapped[Optional[str]] = mapped_column(String(20))  # accurate, partially, inaccurate
    
    # === TRAINING DATA FLAGS ===
    is_valid_for_training: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    training_data_quality: Mapped[Optional[str]] = mapped_column(String(20))  # high, medium, low
    included_in_training: Mapped[bool] = mapped_column(Boolean, default=False)
    training_job_id: Mapped[Optional[str]] = mapped_column(String(100))
    
    # === METADATA ===
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="manual")
    notes: Mapped[Optional[str]] = mapped_column(Text)
    
    # Timestamps
    decision_created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    outcome_recorded_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    last_updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    
    # Indexes for flywheel queries
    __table_args__ = (
        Index("ix_outcomes_customer", "customer_id"),
        Index("ix_outcomes_recorded", "outcome_recorded_at"),
        Index("ix_outcomes_training", "is_valid_for_training", "included_in_training"),
        Index("ix_outcomes_accuracy", "was_delay_accurate", "was_cost_accurate"),
    )
    
    def __repr__(self) -> str:
        return f"<DecisionOutcome {self.outcome_id}: decision={self.decision_id}>"
    
    def calculate_errors(self) -> None:
        """Calculate error metrics from predictions vs actuals."""
        # Delay error
        if self.actual_delay_days is not None:
            self.delay_error = self.actual_delay_days - self.predicted_delay_days
            if self.predicted_delay_days > 0:
                self.delay_error_pct = (self.delay_error / self.predicted_delay_days) * 100
            self.was_delay_accurate = abs(self.delay_error_pct or 0) <= 20
        
        # Exposure error
        if self.actual_loss_usd is not None:
            self.exposure_error = self.actual_loss_usd - self.predicted_exposure_usd
            if self.predicted_exposure_usd > 0:
                self.exposure_error_pct = (self.exposure_error / self.predicted_exposure_usd) * 100
            self.was_cost_accurate = abs(self.exposure_error_pct or 0) <= 30
        
        # Overall accuracy
        if self.was_delay_accurate is not None and self.was_cost_accurate is not None:
            if self.was_delay_accurate and self.was_cost_accurate:
                self.overall_accuracy = "accurate"
            elif self.was_delay_accurate or self.was_cost_accurate:
                self.overall_accuracy = "partially"
            else:
                self.overall_accuracy = "inaccurate"
        
        # Training data validity
        self.is_valid_for_training = (
            self.actual_delay_days is not None and
            self.overall_accuracy is not None
        )
        
        # Data quality assessment
        if self.is_valid_for_training:
            if (abs(self.delay_error_pct or 100) < 50 and 
                abs(self.exposure_error_pct or 100) < 50):
                self.training_data_quality = "high"
            elif (abs(self.delay_error_pct or 100) < 100 and 
                  abs(self.exposure_error_pct or 100) < 100):
                self.training_data_quality = "medium"
            else:
                self.training_data_quality = "low"


# ============================================================================
# NETWORK EFFECTS METRICS MODEL (E2.4 Compliance)
# ============================================================================


class NetworkEffectsMetricModel(Base):
    """
    Track network effects metrics over time.
    
    E2.4 COMPLIANCE: Measures how accuracy improves with more customers/decisions.
    
    Key insight: The more customers use RISKCAST, the better it gets.
    This table tracks that relationship.
    """
    
    __tablename__ = "network_effects_metrics"
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Time bucket
    period_start: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    period_end: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    period_type: Mapped[str] = mapped_column(String(20), nullable=False)  # daily, weekly, monthly
    
    # Volume metrics
    active_customers: Mapped[int] = mapped_column(Integer, nullable=False)
    total_decisions: Mapped[int] = mapped_column(Integer, nullable=False)
    decisions_with_outcomes: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Accuracy metrics
    delay_accuracy_rate: Mapped[float] = mapped_column(Float, nullable=False)
    cost_accuracy_rate: Mapped[float] = mapped_column(Float, nullable=False)
    overall_accuracy_rate: Mapped[float] = mapped_column(Float, nullable=False)
    
    # Error metrics
    mean_delay_error_days: Mapped[float] = mapped_column(Float, nullable=False)
    mean_cost_error_pct: Mapped[float] = mapped_column(Float, nullable=False)
    
    # Calibration
    calibration_error: Mapped[float] = mapped_column(Float, nullable=False)
    
    # Model info
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    training_data_size: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Flywheel health
    outcome_coverage_rate: Mapped[float] = mapped_column(Float, nullable=False)
    feedback_rate: Mapped[float] = mapped_column(Float, nullable=False)
    
    # Computed network effect score
    network_effect_score: Mapped[float] = mapped_column(Float, nullable=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    
    # Indexes
    __table_args__ = (
        Index("ix_network_effects_period", "period_start", "period_type"),
        UniqueConstraint("period_start", "period_type", name="uq_network_effects_period"),
    )
    
    def __repr__(self) -> str:
        return f"<NetworkEffects {self.period_type}: {self.period_start} - accuracy={self.overall_accuracy_rate:.2f}>"
