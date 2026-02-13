"""
OMEN Signal Ingest Schemas.

Exact match with OMEN's SignalEvent output format.
These schemas are the contract between OMEN and RiskCast.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ── Nested signal components ─────────────────────────────────────────────


class GeographicInfo(BaseModel):
    """Geographic scope of the signal."""

    regions: list[str] = Field(default_factory=list)
    chokepoints: list[str] = Field(default_factory=list)


class TemporalInfo(BaseModel):
    """Temporal scope — when the event is expected."""

    event_horizon: Optional[str] = None
    resolution_date: Optional[str] = None


class EvidenceItem(BaseModel):
    """Single evidence source backing the signal."""

    source: str
    source_type: str
    url: Optional[str] = None
    raw_text: Optional[str] = None
    retrieved_at: Optional[str] = None


class OmenSignalPayload(BaseModel):
    """
    The inner `signal` object inside a SignalEvent.

    This is what OMEN's pipeline produces after validation + quality scoring.
    """

    signal_id: str
    source_event_id: Optional[str] = None
    title: str
    description: Optional[str] = None
    probability: float = Field(ge=0.0, le=1.0)
    probability_source: Optional[str] = None
    confidence_score: float = Field(ge=0.0, le=1.0)
    confidence_level: Optional[str] = None  # HIGH / MEDIUM / LOW
    category: str  # GEOPOLITICAL, ECONOMIC, WEATHER, etc.
    tags: list[str] = Field(default_factory=list)
    geographic: Optional[GeographicInfo] = None
    temporal: Optional[TemporalInfo] = None
    evidence: list[EvidenceItem] = Field(default_factory=list)
    trace_id: Optional[str] = None
    ruleset_version: Optional[str] = None
    generated_at: datetime


# ── Top-level SignalEvent (the HTTP request body) ────────────────────────


class SignalEvent(BaseModel):
    """
    Top-level envelope that OMEN POSTs to /api/v1/signals/ingest.

    Contains metadata (schema_version, trace, hash) wrapping the inner signal.
    """

    schema_version: str = Field(default="1.0.0")
    signal_id: str = Field(description="Unique signal ID, e.g. OMEN-LIVE2C94D4C2")
    deterministic_trace_id: Optional[str] = None
    input_event_hash: Optional[str] = None
    source_event_id: Optional[str] = None
    ruleset_version: Optional[str] = None
    observed_at: Optional[datetime] = None
    emitted_at: Optional[datetime] = None
    signal: OmenSignalPayload


# ── Response schemas ─────────────────────────────────────────────────────


class IngestAck(BaseModel):
    """Successful ingest acknowledgement."""

    ack_id: str
    duplicate: bool = False


class ReconcileRequest(BaseModel):
    """Request body for POST /reconcile/run."""

    since_days: int = Field(default=7, ge=1, le=90, description="Reconcile signals from last N days")


class ReconcileResult(BaseModel):
    """Result of a reconcile run."""

    reconcile_id: str
    date: str
    total_in_ledger: int
    total_in_db: int
    missing_count: int
    replayed_count: int
    failed_count: int
    status: str  # completed, partial, failed
    started_at: datetime
    completed_at: Optional[datetime] = None


class ReconcileStatusResponse(BaseModel):
    """Status of reconciliation for a given date."""

    date: str
    last_run: Optional[ReconcileResult] = None
    is_consistent: bool


class ReconcileHistoryResponse(BaseModel):
    """History of reconciliation runs for a date."""

    date: str
    runs: list[ReconcileResult]
