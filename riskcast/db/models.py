"""
RiskCast V2 SQLAlchemy Models.

All 12+ tables. Uses compatibility types for SQLite (dev) + PostgreSQL (prod).
RLS policies are applied at the database level via migration (PostgreSQL only).
"""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from riskcast.db.compat import GUID, JSONType
from riskcast.db.engine import Base


def _genuuid():
    return uuid.uuid4()


# ──────────────────────────────────────────────────────────────────────────────
# 1.1 Tenant & Auth
# ──────────────────────────────────────────────────────────────────────────────


class APIKey(Base):
    """API keys for service-to-service authentication (e.g. OMEN → RiskCast)."""

    __tablename__ = "v2_api_keys"
    __table_args__ = (
        Index("ix_api_keys_key_hash", "key_hash"),
        Index("ix_api_keys_company_id", "company_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=_genuuid)
    company_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("v2_companies.id"), nullable=False)
    key_name: Mapped[str] = mapped_column(String(100), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    key_prefix: Mapped[str] = mapped_column(String(20), nullable=False)
    scopes: Mapped[list] = mapped_column(JSONType(), nullable=False, default=list)
    rate_limit_per_minute: Mapped[int] = mapped_column(Integer, default=1000)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(GUID())
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class SecurityAuditLog(Base):
    """
    Immutable, append-only audit log for ALL security-relevant events.

    CRITICAL: NO UPDATE, NO DELETE on this table. Ever.
    Chain hash: each entry includes hash of previous entry for tamper detection.
    """

    __tablename__ = "v2_security_audit_log"
    __table_args__ = (
        Index("ix_security_audit_timestamp", "timestamp"),
        Index("ix_security_audit_company", "company_id"),
        Index("ix_security_audit_action", "action"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=_genuuid)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    company_id: Mapped[Optional[uuid.UUID]] = mapped_column(GUID())
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(GUID())
    api_key_prefix: Mapped[Optional[str]] = mapped_column(String(20))

    # What happened
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_type: Mapped[Optional[str]] = mapped_column(String(100))
    resource_id: Mapped[Optional[str]] = mapped_column(String(128))

    # Context
    ip_address: Mapped[Optional[str]] = mapped_column(String(50))
    user_agent: Mapped[Optional[str]] = mapped_column(String(500))
    request_method: Mapped[Optional[str]] = mapped_column(String(10))
    request_path: Mapped[Optional[str]] = mapped_column(String(500))

    # Outcome
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="success")
    details: Mapped[Optional[dict]] = mapped_column(JSONType())

    # Tamper detection
    previous_hash: Mapped[Optional[str]] = mapped_column(String(128))
    entry_hash: Mapped[Optional[str]] = mapped_column(String(128))


class Company(Base):
    __tablename__ = "v2_companies"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=_genuuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    industry: Mapped[Optional[str]] = mapped_column(String(100))
    timezone: Mapped[str] = mapped_column(String(50), default="Asia/Ho_Chi_Minh")
    plan: Mapped[str] = mapped_column(String(50), default="starter")
    settings: Mapped[dict] = mapped_column(JSONType(), default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    users: Mapped[list["User"]] = relationship(back_populates="company", cascade="all, delete-orphan")
    customers: Mapped[list["Customer"]] = relationship(back_populates="company", cascade="all, delete-orphan")
    routes: Mapped[list["Route"]] = relationship(back_populates="company", cascade="all, delete-orphan")
    orders: Mapped[list["Order"]] = relationship(back_populates="company", cascade="all, delete-orphan")
    payments: Mapped[list["Payment"]] = relationship(back_populates="company", cascade="all, delete-orphan")
    incidents: Mapped[list["Incident"]] = relationship(back_populates="company", cascade="all, delete-orphan")
    signals: Mapped[list["Signal"]] = relationship(back_populates="company", cascade="all, delete-orphan")


class User(Base):
    __tablename__ = "v2_users"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=_genuuid)
    company_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("v2_companies.id"), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), default="member")
    preferences: Mapped[dict] = mapped_column(JSONType(), default=dict)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    company: Mapped["Company"] = relationship(back_populates="users")


# ──────────────────────────────────────────────────────────────────────────────
# 1.2 Company Operational Data
# ──────────────────────────────────────────────────────────────────────────────


class Customer(Base):
    __tablename__ = "v2_customers"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=_genuuid)
    company_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("v2_companies.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[Optional[str]] = mapped_column(String(50))
    tier: Mapped[str] = mapped_column(String(50), default="standard")
    contact_email: Mapped[Optional[str]] = mapped_column(String(255))
    contact_phone: Mapped[Optional[str]] = mapped_column(String(50))
    payment_terms: Mapped[int] = mapped_column(Integer, default=30)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONType(), default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    company: Mapped["Company"] = relationship(back_populates="customers")
    orders: Mapped[list["Order"]] = relationship(back_populates="customer")
    payments: Mapped[list["Payment"]] = relationship(back_populates="customer")
    incidents: Mapped[list["Incident"]] = relationship(back_populates="customer")


class Route(Base):
    __tablename__ = "v2_routes"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=_genuuid)
    company_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("v2_companies.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    origin: Mapped[str] = mapped_column(String(255), nullable=False)
    destination: Mapped[str] = mapped_column(String(255), nullable=False)
    transport_mode: Mapped[Optional[str]] = mapped_column(String(50))
    avg_duration_days: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 1))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONType(), default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    company: Mapped["Company"] = relationship(back_populates="routes")
    orders: Mapped[list["Order"]] = relationship(back_populates="route")
    incidents: Mapped[list["Incident"]] = relationship(back_populates="route")


class Order(Base):
    __tablename__ = "v2_orders"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=_genuuid)
    company_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("v2_companies.id"), nullable=False, index=True)
    customer_id: Mapped[Optional[uuid.UUID]] = mapped_column(GUID(), ForeignKey("v2_customers.id"))
    route_id: Mapped[Optional[uuid.UUID]] = mapped_column(GUID(), ForeignKey("v2_routes.id"))
    order_number: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    total_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    currency: Mapped[str] = mapped_column(String(3), default="VND")
    origin: Mapped[Optional[str]] = mapped_column(String(255))
    destination: Mapped[Optional[str]] = mapped_column(String(255))
    expected_date: Mapped[Optional[date]] = mapped_column(Date)
    actual_date: Mapped[Optional[date]] = mapped_column(Date)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONType(), default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    company: Mapped["Company"] = relationship(back_populates="orders")
    customer: Mapped[Optional["Customer"]] = relationship(back_populates="orders")
    route: Mapped[Optional["Route"]] = relationship(back_populates="orders")
    payments: Mapped[list["Payment"]] = relationship(back_populates="order")
    incidents: Mapped[list["Incident"]] = relationship(back_populates="order")


class Payment(Base):
    __tablename__ = "v2_payments"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=_genuuid)
    company_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("v2_companies.id"), nullable=False)
    order_id: Mapped[Optional[uuid.UUID]] = mapped_column(GUID(), ForeignKey("v2_orders.id"))
    customer_id: Mapped[Optional[uuid.UUID]] = mapped_column(GUID(), ForeignKey("v2_customers.id"))
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="VND")
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    paid_date: Mapped[Optional[date]] = mapped_column(Date)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONType(), default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    company: Mapped["Company"] = relationship(back_populates="payments")
    order: Mapped[Optional["Order"]] = relationship(back_populates="payments")
    customer: Mapped[Optional["Customer"]] = relationship(back_populates="payments")


class Incident(Base):
    __tablename__ = "v2_incidents"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=_genuuid)
    company_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("v2_companies.id"), nullable=False, index=True)
    order_id: Mapped[Optional[uuid.UUID]] = mapped_column(GUID(), ForeignKey("v2_orders.id"))
    route_id: Mapped[Optional[uuid.UUID]] = mapped_column(GUID(), ForeignKey("v2_routes.id"))
    customer_id: Mapped[Optional[uuid.UUID]] = mapped_column(GUID(), ForeignKey("v2_customers.id"))
    type: Mapped[str] = mapped_column(String(100), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    resolution: Mapped[Optional[str]] = mapped_column(Text)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONType(), default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    company: Mapped["Company"] = relationship(back_populates="incidents")
    order: Mapped[Optional["Order"]] = relationship(back_populates="incidents")
    route: Mapped[Optional["Route"]] = relationship(back_populates="incidents")
    customer: Mapped[Optional["Customer"]] = relationship(back_populates="incidents")


# ──────────────────────────────────────────────────────────────────────────────
# 1.3 Signals
# ──────────────────────────────────────────────────────────────────────────────


class Signal(Base):
    __tablename__ = "v2_signals"
    __table_args__ = (
        UniqueConstraint(
            "company_id", "source", "signal_type", "entity_type", "entity_id",
            name="uq_v2_signals_composite",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=_genuuid)
    company_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("v2_companies.id"), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    signal_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[Optional[str]] = mapped_column(String(50))
    entity_id: Mapped[Optional[uuid.UUID]] = mapped_column(GUID())
    confidence: Mapped[Decimal] = mapped_column(Numeric(3, 2), nullable=False)
    severity_score: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    evidence: Mapped[dict] = mapped_column(JSONType(), nullable=False)
    context: Mapped[dict] = mapped_column(JSONType(), default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    company: Mapped["Company"] = relationship(back_populates="signals")


# ──────────────────────────────────────────────────────────────────────────────
# 1.4 AI Interaction
# ──────────────────────────────────────────────────────────────────────────────


class ChatSession(Base):
    __tablename__ = "v2_chat_sessions"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=_genuuid)
    company_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("v2_companies.id"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("v2_users.id"), nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    messages: Mapped[list["ChatMessage"]] = relationship(back_populates="session", cascade="all, delete-orphan")


class ChatMessage(Base):
    __tablename__ = "v2_chat_messages"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=_genuuid)
    session_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("v2_chat_sessions.id"), nullable=False, index=True)
    company_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("v2_companies.id"), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    context_used: Mapped[dict] = mapped_column(JSONType(), default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    session: Mapped["ChatSession"] = relationship(back_populates="messages")


class MorningBrief(Base):
    __tablename__ = "v2_morning_briefs"
    __table_args__ = (
        UniqueConstraint("company_id", "brief_date", name="uq_v2_briefs_company_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=_genuuid)
    company_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("v2_companies.id"), nullable=False)
    brief_date: Mapped[date] = mapped_column(Date, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    signals_used: Mapped[dict] = mapped_column(JSONType(), nullable=False)
    priority_items: Mapped[dict] = mapped_column(JSONType(), nullable=False)
    read_by: Mapped[dict] = mapped_column(JSONType(), default=list)  # JSON array instead of ARRAY
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ──────────────────────────────────────────────────────────────────────────────
# 1.5 Feedback Loop
# ──────────────────────────────────────────────────────────────────────────────


class AiSuggestion(Base):
    __tablename__ = "v2_ai_suggestions"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=_genuuid)
    company_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("v2_companies.id"), nullable=False)
    message_id: Mapped[Optional[uuid.UUID]] = mapped_column(GUID(), ForeignKey("v2_chat_messages.id"))
    signal_id: Mapped[Optional[uuid.UUID]] = mapped_column(GUID(), ForeignKey("v2_signals.id"))
    suggestion_type: Mapped[str] = mapped_column(String(100), nullable=False)
    suggestion_text: Mapped[str] = mapped_column(Text, nullable=False)
    entity_type: Mapped[Optional[str]] = mapped_column(String(50))
    entity_id: Mapped[Optional[uuid.UUID]] = mapped_column(GUID())
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class SuggestionFeedback(Base):
    __tablename__ = "v2_suggestion_feedback"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=_genuuid)
    suggestion_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("v2_ai_suggestions.id"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("v2_users.id"), nullable=False)
    company_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("v2_companies.id"), nullable=False, index=True)
    decision: Mapped[str] = mapped_column(String(20), nullable=False)
    reason_code: Mapped[Optional[str]] = mapped_column(String(100))
    reason_text: Mapped[Optional[str]] = mapped_column(Text)
    outcome: Mapped[Optional[str]] = mapped_column(String(50))
    outcome_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class RiskAppetiteProfile(Base):
    __tablename__ = "v2_risk_appetite_profiles"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=_genuuid)
    company_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("v2_companies.id"), unique=True, nullable=False)
    profile: Mapped[dict] = mapped_column(JSONType(), nullable=False, default=dict)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ═══════════════════════════════════════════════════════════════════════════
# OMEN Integration Models — Signal Ingest, Ledger, Reconciliation
# ═══════════════════════════════════════════════════════════════════════════


class OmenIngestSignal(Base):
    """
    Signals received from OMEN via POST /api/v1/signals/ingest.

    This is the primary store for ingested signals.
    Uses signal_id as the idempotency key (unique).
    """

    __tablename__ = "v2_omen_signals"
    __table_args__ = (
        Index("ix_omen_signals_category", "category"),
        Index("ix_omen_signals_ingested_at", "ingested_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=_genuuid)
    signal_id: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    ack_id: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)

    # Envelope metadata
    schema_version: Mapped[str] = mapped_column(String(20), nullable=False, default="1.0.0")
    deterministic_trace_id: Mapped[Optional[str]] = mapped_column(String(256))
    input_event_hash: Mapped[Optional[str]] = mapped_column(String(256))
    source_event_id: Mapped[Optional[str]] = mapped_column(String(256))
    ruleset_version: Mapped[Optional[str]] = mapped_column(String(50))
    observed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    emitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Signal core fields
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    probability: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    confidence_score: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    confidence_level: Mapped[Optional[str]] = mapped_column(String(20))
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    tags: Mapped[dict] = mapped_column(JSONType(), default=list)

    # Nested JSON blobs
    geographic: Mapped[Optional[dict]] = mapped_column(JSONType())
    temporal: Mapped[Optional[dict]] = mapped_column(JSONType())
    evidence: Mapped[dict] = mapped_column(JSONType(), default=list)

    # Full original payload for auditability
    raw_payload: Mapped[dict] = mapped_column(JSONType(), nullable=False)

    # Lifecycle
    ingested_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    processed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)


class SignalLedger(Base):
    """
    Immutable ledger — every signal from OMEN is recorded here FIRST.

    Even if the DB insert fails, the ledger entry survives.
    Reconcile reads the ledger to replay missed signals.
    """

    __tablename__ = "v2_signal_ledger"
    __table_args__ = (
        Index("ix_signal_ledger_recorded_at", "recorded_at"),
        Index("ix_signal_ledger_signal_id", "signal_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=_genuuid)
    signal_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    ack_id: Mapped[Optional[str]] = mapped_column(String(128))

    # Full payload snapshot (immutable)
    payload: Mapped[dict] = mapped_column(JSONType(), nullable=False)

    # Status tracking
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="received")
    # received → ingested → failed
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    ingested_at: Mapped[Optional[datetime]] = mapped_column(DateTime)


class ReconcileLog(Base):
    """
    Log of reconciliation runs.

    Tracks each reconcile execution: how many signals were in the ledger,
    how many in the DB, how many were replayed.
    """

    __tablename__ = "v2_reconcile_log"
    __table_args__ = (
        Index("ix_reconcile_log_target_date", "target_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=_genuuid)
    reconcile_id: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    target_date: Mapped[date] = mapped_column(Date, nullable=False)

    total_in_ledger: Mapped[int] = mapped_column(Integer, default=0)
    total_in_db: Mapped[int] = mapped_column(Integer, default=0)
    missing_count: Mapped[int] = mapped_column(Integer, default=0)
    replayed_count: Mapped[int] = mapped_column(Integer, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, default=0)

    status: Mapped[str] = mapped_column(String(20), nullable=False, default="running")
    # running → completed → partial → failed
    error_message: Mapped[Optional[str]] = mapped_column(Text)

    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)


# ──────────────────────────────────────────────────────────────────────────────
# 2.1 Outcome Tracking (Phase 5)
# ──────────────────────────────────────────────────────────────────────────────


class Outcome(Base):
    """
    Records what ACTUALLY happened after a decision was made.

    Immutable once recorded. Used for:
    - Model calibration (Brier score, calibration drift)
    - ROI tracking (value generated)
    - Flywheel learning (prior updates)
    - Prediction accuracy reporting
    """

    __tablename__ = "v2_outcomes"
    __table_args__ = (
        Index("ix_outcomes_company_id", "company_id"),
        Index("ix_outcomes_decision_id", "decision_id"),
        Index("ix_outcomes_recorded_at", "recorded_at"),
        Index("ix_outcomes_entity", "entity_type", "entity_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=_genuuid)
    decision_id: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    company_id: Mapped[uuid.UUID] = mapped_column(GUID(), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(128), nullable=False)

    # Predicted values (snapshot from the decision)
    predicted_risk_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    predicted_confidence: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    predicted_loss_usd: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    predicted_action: Mapped[str] = mapped_column(String(50), nullable=False)

    # Actual values
    outcome_type: Mapped[str] = mapped_column(String(50), nullable=False)
    actual_loss_usd: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=0)
    actual_delay_days: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False, default=0)
    action_taken: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    action_followed_recommendation: Mapped[bool] = mapped_column(Boolean, default=False)

    # Computed accuracy
    risk_materialized: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    prediction_error: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False, default=0)
    was_accurate: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    value_generated_usd: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False, default=0)

    # Metadata
    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    recorded_by: Mapped[Optional[str]] = mapped_column(String(128))
    notes: Mapped[Optional[str]] = mapped_column(Text)


# ──────────────────────────────────────────────────────────────────────────────
# 2.2 Alerting & Early Warning (Phase 6)
# ──────────────────────────────────────────────────────────────────────────────


class AlertRuleModel(Base):
    """
    Configurable alert rules per company.

    Defines WHEN alerts fire based on metric conditions.
    """

    __tablename__ = "v2_alert_rules"
    __table_args__ = (
        Index("ix_alert_rules_company_id", "company_id"),
        Index("ix_alert_rules_metric", "metric"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=_genuuid)
    rule_id: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    company_id: Mapped[uuid.UUID] = mapped_column(GUID(), nullable=False)
    rule_name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Condition
    metric: Mapped[str] = mapped_column(String(100), nullable=False)
    operator: Mapped[str] = mapped_column(String(20), nullable=False)
    threshold: Mapped[Decimal] = mapped_column(Numeric(15, 4), nullable=False)
    entity_type: Mapped[Optional[str]] = mapped_column(String(50))

    # Config
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="warning")
    channels: Mapped[list] = mapped_column(JSONType(), nullable=False, default=list)
    cooldown_minutes: Mapped[int] = mapped_column(Integer, default=30)
    max_per_day: Mapped[int] = mapped_column(Integer, default=10)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Alert(Base):
    """
    Fired alert record — immutable log of triggered alerts.
    """

    __tablename__ = "v2_alerts"
    __table_args__ = (
        Index("ix_alerts_company_id", "company_id"),
        Index("ix_alerts_rule_id", "rule_id"),
        Index("ix_alerts_triggered_at", "triggered_at"),
        Index("ix_alerts_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=_genuuid)
    alert_id: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    rule_id: Mapped[str] = mapped_column(String(128), nullable=False)
    rule_name: Mapped[str] = mapped_column(String(255), nullable=False)
    company_id: Mapped[uuid.UUID] = mapped_column(GUID(), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")

    # What triggered it
    metric: Mapped[str] = mapped_column(String(100), nullable=False)
    metric_value: Mapped[Decimal] = mapped_column(Numeric(15, 4), nullable=False)
    threshold: Mapped[Decimal] = mapped_column(Numeric(15, 4), nullable=False)
    entity_type: Mapped[Optional[str]] = mapped_column(String(50))
    entity_id: Mapped[Optional[str]] = mapped_column(String(128))

    # Message
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)

    # Delivery
    channels: Mapped[list] = mapped_column(JSONType(), nullable=False, default=list)
    delivery_results: Mapped[dict] = mapped_column(JSONType(), default=dict)

    # Timing
    triggered_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    acknowledged_by: Mapped[Optional[str]] = mapped_column(String(128))
