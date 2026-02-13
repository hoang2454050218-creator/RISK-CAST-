"""
Audit API Routes.

Provides endpoints for:
- Chain integrity verification
- Audit trail retrieval
- Input snapshot access
- Justification document generation

IMPORTANT: These endpoints are for audit and compliance purposes.
"""

from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, Path
from pydantic import BaseModel, Field

from app.audit import (
    AuditService,
    AuditRepository,
    AuditChainVerification,
    AuditRecord,
    InputSnapshot,
    DecisionAuditTrail,
    AuditEventType,
    JustificationLevel,
    Audience,
    JustificationGenerator,
    create_justification_generator,
)
from app.audit.trail import AuditChainVerifier, create_chain_verifier
from app.core.database import get_db_session

import structlog

logger = structlog.get_logger(__name__)

router = APIRouter()


# ============================================================================
# DEPENDENCY INJECTION
# ============================================================================


async def get_audit_service(session=Depends(get_db_session)) -> AuditService:
    """Get audit service with database session."""
    repository = AuditRepository(session)
    service = AuditService(repository)
    await service.initialize()
    return service


async def get_chain_verifier(
    audit_service: AuditService = Depends(get_audit_service),
) -> AuditChainVerifier:
    """Get chain verifier."""
    return AuditChainVerifier(audit_service)


async def get_justification_generator(
    audit_service: AuditService = Depends(get_audit_service),
) -> JustificationGenerator:
    """Get justification generator."""
    return create_justification_generator(audit_service)


# ============================================================================
# RESPONSE MODELS
# ============================================================================


class ChainVerificationResponse(BaseModel):
    """Response for chain verification."""
    is_valid: bool
    records_checked: int
    first_invalid_sequence: Optional[int] = None
    error_type: Optional[str] = None
    error_message: Optional[str] = None
    verified_at: datetime


class ChainStatsResponse(BaseModel):
    """Response for chain statistics."""
    total_records: int
    first_record_at: Optional[datetime] = None
    last_record_at: Optional[datetime] = None
    event_type_counts: dict
    chain_status: str


class AuditRecordResponse(BaseModel):
    """Response for single audit record."""
    audit_id: str
    event_type: str
    timestamp: datetime
    entity_type: str
    entity_id: str
    actor_type: str
    actor_id: Optional[str]
    payload: dict
    sequence_number: int
    record_hash: str


class AuditTrailResponse(BaseModel):
    """Response for decision audit trail."""
    decision_id: str
    customer_id: str
    is_complete: bool
    event_count: int
    has_input_snapshot: bool
    has_processing_record: bool
    created_at: Optional[datetime]
    delivered_at: Optional[datetime]
    acknowledged_at: Optional[datetime]
    events: List[AuditRecordResponse]


class InputSnapshotResponse(BaseModel):
    """Response for input snapshot."""
    snapshot_id: str
    captured_at: datetime
    signal_id: str
    signal_hash: str
    reality_hash: str
    reality_staleness_seconds: int
    customer_id: str
    customer_context_hash: str
    combined_hash: str
    is_valid: bool


class JustificationRequest(BaseModel):
    """Request for justification generation."""
    level: JustificationLevel = Field(
        default=JustificationLevel.DETAILED,
        description="Level of detail (executive, detailed, audit, legal)",
    )
    audience: Audience = Field(
        default=Audience.ANALYST,
        description="Target audience",
    )
    language: str = Field(
        default="en",
        description="Language code (en, vi)",
    )


class JustificationResponse(BaseModel):
    """Response for justification document."""
    decision_id: str
    level: str
    audience: str
    content: str  # For executive/detailed levels
    document_id: Optional[str] = None  # For legal level
    verification_hash: Optional[str] = None


# ============================================================================
# CHAIN VERIFICATION ENDPOINTS
# ============================================================================


@router.get(
    "/chain/verify",
    response_model=ChainVerificationResponse,
    summary="Verify audit chain integrity",
    description="Verify cryptographic integrity of the entire audit chain. "
                "Detects tampering, chain breaks, and sequence gaps.",
)
async def verify_chain(
    start_sequence: int = Query(
        default=0,
        ge=0,
        description="Starting sequence number",
    ),
    end_sequence: Optional[int] = Query(
        default=None,
        ge=0,
        description="Ending sequence number (default: all)",
    ),
    audit_service: AuditService = Depends(get_audit_service),
) -> ChainVerificationResponse:
    """Verify audit chain integrity."""
    logger.info(
        "chain_verification_requested",
        start_sequence=start_sequence,
        end_sequence=end_sequence,
    )
    
    result = await audit_service.verify_chain_integrity(
        start_sequence=start_sequence,
        end_sequence=end_sequence,
    )
    
    return ChainVerificationResponse(
        is_valid=result.is_valid,
        records_checked=result.records_checked,
        first_invalid_sequence=result.first_invalid_sequence,
        error_type=result.error_type,
        error_message=result.error_message,
        verified_at=result.verified_at,
    )


@router.get(
    "/chain/verify/recent",
    response_model=ChainVerificationResponse,
    summary="Verify recent audit records",
    description="Verify integrity of audit records from the last N hours.",
)
async def verify_recent_chain(
    hours: int = Query(
        default=24,
        ge=1,
        le=720,  # Max 30 days
        description="Number of hours to verify",
    ),
    verifier: AuditChainVerifier = Depends(get_chain_verifier),
) -> ChainVerificationResponse:
    """Verify recent audit records."""
    result = await verifier.verify_recent(hours=hours)
    
    return ChainVerificationResponse(
        is_valid=result["is_valid"],
        records_checked=result["records_checked"],
        verified_at=datetime.fromisoformat(result["verified_at"]),
    )


@router.get(
    "/chain/stats",
    response_model=ChainStatsResponse,
    summary="Get audit chain statistics",
    description="Get statistics about the audit chain including record counts and health.",
)
async def get_chain_stats(
    verifier: AuditChainVerifier = Depends(get_chain_verifier),
) -> ChainStatsResponse:
    """Get audit chain statistics."""
    stats = await verifier.get_chain_stats()
    
    return ChainStatsResponse(
        total_records=stats["total_records"],
        first_record_at=stats.get("first_record_at"),
        last_record_at=stats.get("last_record_at"),
        event_type_counts=stats.get("event_type_counts", {}),
        chain_status=stats["chain_status"],
    )


# ============================================================================
# AUDIT TRAIL ENDPOINTS
# ============================================================================


@router.get(
    "/trail/{decision_id}",
    response_model=AuditTrailResponse,
    summary="Get decision audit trail",
    description="Get complete audit trail for a decision including all events, "
                "input snapshot, and processing record.",
)
async def get_decision_audit_trail(
    decision_id: str = Path(description="Decision ID"),
    audit_service: AuditService = Depends(get_audit_service),
) -> AuditTrailResponse:
    """Get complete audit trail for a decision."""
    logger.info("audit_trail_requested", decision_id=decision_id)
    
    trail = await audit_service.get_decision_audit_trail(decision_id)
    
    if not trail.audit_events:
        raise HTTPException(
            status_code=404,
            detail=f"No audit trail found for decision {decision_id}",
        )
    
    return AuditTrailResponse(
        decision_id=trail.decision_id,
        customer_id=trail.customer_id,
        is_complete=trail.is_complete,
        event_count=trail.event_count,
        has_input_snapshot=trail.input_snapshot is not None,
        has_processing_record=trail.processing_record is not None,
        created_at=trail.created_at,
        delivered_at=trail.delivered_at,
        acknowledged_at=trail.acknowledged_at,
        events=[
            AuditRecordResponse(
                audit_id=e.audit_id,
                event_type=e.event_type.value,
                timestamp=e.timestamp,
                entity_type=e.entity_type,
                entity_id=e.entity_id,
                actor_type=e.actor_type,
                actor_id=e.actor_id,
                payload=e.payload,
                sequence_number=e.sequence_number,
                record_hash=e.record_hash,
            )
            for e in trail.audit_events
        ],
    )


@router.get(
    "/records",
    response_model=List[AuditRecordResponse],
    summary="List audit records",
    description="List audit records with optional filtering by event type and time range.",
)
async def list_audit_records(
    event_type: Optional[str] = Query(
        default=None,
        description="Filter by event type (e.g., decision.generated)",
    ),
    entity_type: Optional[str] = Query(
        default=None,
        description="Filter by entity type (e.g., decision)",
    ),
    entity_id: Optional[str] = Query(
        default=None,
        description="Filter by entity ID",
    ),
    start_time: Optional[datetime] = Query(
        default=None,
        description="Start of time range",
    ),
    end_time: Optional[datetime] = Query(
        default=None,
        description="End of time range",
    ),
    limit: int = Query(
        default=100,
        ge=1,
        le=1000,
        description="Maximum records to return",
    ),
    audit_service: AuditService = Depends(get_audit_service),
) -> List[AuditRecordResponse]:
    """List audit records with filtering."""
    # Get records based on filters
    if entity_type and entity_id:
        records = await audit_service._repo.get_records_for_entity(
            entity_type=entity_type,
            entity_id=entity_id,
            limit=limit,
        )
    elif event_type:
        try:
            event_type_enum = AuditEventType(event_type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid event type: {event_type}",
            )
        records = await audit_service._repo.get_records_by_event_type(
            event_type=event_type_enum,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
        )
    else:
        # Get recent records
        records = await audit_service._repo.get_records_range(
            start_sequence=0,
            limit=limit,
        )
    
    return [
        AuditRecordResponse(
            audit_id=r.audit_id,
            event_type=r.event_type.value,
            timestamp=r.timestamp,
            entity_type=r.entity_type,
            entity_id=r.entity_id,
            actor_type=r.actor_type,
            actor_id=r.actor_id,
            payload=r.payload,
            sequence_number=r.sequence_number,
            record_hash=r.record_hash,
        )
        for r in records
    ]


# ============================================================================
# SNAPSHOT ENDPOINTS
# ============================================================================


@router.get(
    "/snapshots/{snapshot_id}",
    response_model=InputSnapshotResponse,
    summary="Get input snapshot",
    description="Get an input snapshot by ID with integrity verification.",
)
async def get_snapshot(
    snapshot_id: str = Path(description="Snapshot ID"),
    verify: bool = Query(
        default=True,
        description="Verify snapshot integrity",
    ),
    audit_service: AuditService = Depends(get_audit_service),
) -> InputSnapshotResponse:
    """Get input snapshot by ID."""
    snapshot = await audit_service.get_snapshot(snapshot_id)
    
    if not snapshot:
        raise HTTPException(
            status_code=404,
            detail=f"Snapshot not found: {snapshot_id}",
        )
    
    is_valid = snapshot.verify_integrity() if verify else True
    
    return InputSnapshotResponse(
        snapshot_id=snapshot.snapshot_id,
        captured_at=snapshot.captured_at,
        signal_id=snapshot.signal_id,
        signal_hash=snapshot.signal_hash,
        reality_hash=snapshot.reality_hash,
        reality_staleness_seconds=snapshot.reality_staleness_seconds,
        customer_id=snapshot.customer_id,
        customer_context_hash=snapshot.customer_context_hash,
        combined_hash=snapshot.combined_hash,
        is_valid=is_valid,
    )


@router.get(
    "/snapshots/{snapshot_id}/full",
    summary="Get full input snapshot data",
    description="Get complete input snapshot including all data (signal, reality, context). "
                "Use with caution as this may contain sensitive data.",
)
async def get_snapshot_full(
    snapshot_id: str = Path(description="Snapshot ID"),
    audit_service: AuditService = Depends(get_audit_service),
) -> dict:
    """Get full snapshot data for debugging/audit."""
    snapshot = await audit_service.get_snapshot(snapshot_id)
    
    if not snapshot:
        raise HTTPException(
            status_code=404,
            detail=f"Snapshot not found: {snapshot_id}",
        )
    
    return {
        "snapshot_id": snapshot.snapshot_id,
        "captured_at": snapshot.captured_at.isoformat(),
        "signal_id": snapshot.signal_id,
        "signal_data": snapshot.signal_data,
        "signal_hash": snapshot.signal_hash,
        "reality_data": snapshot.reality_data,
        "reality_hash": snapshot.reality_hash,
        "reality_staleness_seconds": snapshot.reality_staleness_seconds,
        "customer_id": snapshot.customer_id,
        "customer_context_data": snapshot.customer_context_data,
        "customer_context_hash": snapshot.customer_context_hash,
        "combined_hash": snapshot.combined_hash,
        "integrity_verified": snapshot.verify_integrity(),
    }


@router.get(
    "/decisions/{decision_id}/snapshot",
    response_model=InputSnapshotResponse,
    summary="Get snapshot for decision",
    description="Get the input snapshot that was captured for a specific decision.",
)
async def get_decision_snapshot(
    decision_id: str = Path(description="Decision ID"),
    audit_service: AuditService = Depends(get_audit_service),
) -> InputSnapshotResponse:
    """Get the input snapshot for a decision."""
    snapshot = await audit_service.get_snapshot_for_decision(decision_id)
    
    if not snapshot:
        raise HTTPException(
            status_code=404,
            detail=f"No snapshot found for decision: {decision_id}",
        )
    
    return InputSnapshotResponse(
        snapshot_id=snapshot.snapshot_id,
        captured_at=snapshot.captured_at,
        signal_id=snapshot.signal_id,
        signal_hash=snapshot.signal_hash,
        reality_hash=snapshot.reality_hash,
        reality_staleness_seconds=snapshot.reality_staleness_seconds,
        customer_id=snapshot.customer_id,
        customer_context_hash=snapshot.customer_context_hash,
        combined_hash=snapshot.combined_hash,
        is_valid=snapshot.verify_integrity(),
    )


# ============================================================================
# JUSTIFICATION ENDPOINTS
# ============================================================================


@router.post(
    "/decisions/{decision_id}/justification",
    response_model=JustificationResponse,
    summary="Generate decision justification",
    description="Generate a justification document for a decision at various detail levels. "
                "EXECUTIVE: One paragraph summary. "
                "DETAILED: Full 7 Questions format. "
                "AUDIT: Technical trace with calculations. "
                "LEGAL: Court-admissible document with full provenance.",
)
async def generate_justification(
    decision_id: str = Path(description="Decision ID"),
    request: JustificationRequest = JustificationRequest(),
    audit_service: AuditService = Depends(get_audit_service),
) -> JustificationResponse:
    """Generate justification document for a decision."""
    # This would normally fetch the decision from the decisions service
    # For now, return a placeholder or fetch from audit trail
    logger.info(
        "justification_requested",
        decision_id=decision_id,
        level=request.level.value,
        audience=request.audience.value,
    )
    
    # Get audit trail to verify decision exists
    trail = await audit_service.get_decision_audit_trail(decision_id)
    
    if not trail.audit_events:
        raise HTTPException(
            status_code=404,
            detail=f"No audit trail found for decision {decision_id}",
        )
    
    # For executive/detailed levels, we can generate from audit data
    if request.level in [JustificationLevel.EXECUTIVE, JustificationLevel.DETAILED]:
        # Extract info from audit events
        decision_event = next(
            (e for e in trail.audit_events if e.event_type == AuditEventType.DECISION_GENERATED),
            None,
        )
        
        if not decision_event:
            raise HTTPException(
                status_code=404,
                detail="Decision generation event not found in audit trail",
            )
        
        # Generate summary from audit data
        payload = decision_event.payload
        content = f"""
RISKCAST DECISION SUMMARY
Decision ID: {decision_id}
Customer ID: {trail.customer_id}
Generated: {decision_event.timestamp.isoformat()}

Action Type: {payload.get('action_type', 'Unknown')}
Confidence: {payload.get('confidence', 0):.0%}
Exposure: ${payload.get('exposure_usd', 0):,.0f}
Model Version: {payload.get('model_version', 'Unknown')}

Audit Trail:
- Snapshot ID: {payload.get('snapshot_id', 'N/A')}
- Processing ID: {payload.get('processing_record_id', 'N/A')}
- Events in Trail: {len(trail.audit_events)}
        """.strip()
        
        return JustificationResponse(
            decision_id=decision_id,
            level=request.level.value,
            audience=request.audience.value,
            content=content,
        )
    
    # For audit/legal levels, would need full decision object
    # This is a placeholder - in production would fetch decision from DB
    return JustificationResponse(
        decision_id=decision_id,
        level=request.level.value,
        audience=request.audience.value,
        content=f"Full {request.level.value} justification for {decision_id} - requires decision service integration",
        document_id=f"just_{decision_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
    )


# ============================================================================
# HUMAN OVERRIDE AUDIT
# ============================================================================


@router.get(
    "/overrides",
    summary="List human overrides",
    description="List all human override events for audit purposes.",
)
async def list_overrides(
    start_time: Optional[datetime] = Query(
        default=None,
        description="Start of time range",
    ),
    end_time: Optional[datetime] = Query(
        default=None,
        description="End of time range",
    ),
    user_id: Optional[str] = Query(
        default=None,
        description="Filter by user who made the override",
    ),
    limit: int = Query(
        default=100,
        ge=1,
        le=1000,
        description="Maximum records to return",
    ),
    audit_service: AuditService = Depends(get_audit_service),
) -> List[AuditRecordResponse]:
    """List human override events."""
    records = await audit_service._repo.get_records_by_event_type(
        event_type=AuditEventType.HUMAN_OVERRIDE,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
    )
    
    # Filter by user if specified
    if user_id:
        records = [r for r in records if r.actor_id == user_id]
    
    return [
        AuditRecordResponse(
            audit_id=r.audit_id,
            event_type=r.event_type.value,
            timestamp=r.timestamp,
            entity_type=r.entity_type,
            entity_id=r.entity_id,
            actor_type=r.actor_type,
            actor_id=r.actor_id,
            payload=r.payload,
            sequence_number=r.sequence_number,
            record_hash=r.record_hash,
        )
        for r in records
    ]


@router.get(
    "/decisions/{decision_id}/overrides",
    summary="Get overrides for decision",
    description="Get all human override events for a specific decision.",
)
async def get_decision_overrides(
    decision_id: str = Path(description="Decision ID"),
    audit_service: AuditService = Depends(get_audit_service),
) -> List[AuditRecordResponse]:
    """Get overrides for a specific decision."""
    trail = await audit_service.get_decision_audit_trail(decision_id)
    
    override_events = [
        e for e in trail.audit_events
        if e.event_type == AuditEventType.HUMAN_OVERRIDE
    ]
    
    return [
        AuditRecordResponse(
            audit_id=r.audit_id,
            event_type=r.event_type.value,
            timestamp=r.timestamp,
            entity_type=r.entity_type,
            entity_id=r.entity_id,
            actor_type=r.actor_type,
            actor_id=r.actor_id,
            payload=r.payload,
            sequence_number=r.sequence_number,
            record_hash=r.record_hash,
        )
        for r in override_events
    ]
