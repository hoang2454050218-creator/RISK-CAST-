"""Decision API Endpoints.

Generate and retrieve RISKCAST decisions.

UPDATED: Now includes authentication, pagination, and multi-tenancy.
"""

from typing import Optional, Annotated
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status, BackgroundTasks, Header
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.auth import (
    AuthContext,
    get_auth_context,
    require_scope,
    require_customer_access,
    Scopes,
    check_idempotency,
    get_idempotency_store,
)
from app.riskcast.constants import Severity, Urgency, ActionType
from app.riskcast.schemas.decision import DecisionObject
from app.riskcast.service import create_async_riskcast_service, AsyncRiskCastService
from app.oracle.service import get_oracle_service
from app.riskcast.repos.customer import PostgresCustomerRepository
from app.common.exceptions import (
    DecisionNotFoundError,
    CustomerNotFoundError,
    NoExposureError,
)

router = APIRouter()


# ============================================================================
# REQUEST/RESPONSE SCHEMAS
# ============================================================================


class GenerateDecisionRequest(BaseModel):
    """Request to generate a decision for a customer."""

    customer_id: str = Field(description="Customer ID to generate decision for")
    signal_id: Optional[str] = Field(default=None, description="Specific signal to use")
    chokepoint: Optional[str] = Field(default=None, description="Filter by chokepoint")


class DecisionSummaryResponse(BaseModel):
    """Summary of a decision."""

    decision_id: str
    customer_id: str
    signal_id: Optional[str]
    chokepoint: str
    severity: str
    urgency: str
    recommended_action: str
    action_cost_usd: float
    exposure_usd: float
    potential_loss_usd: float
    potential_delay_days: float
    confidence_score: float
    valid_until: datetime
    created_at: datetime

    # Key message
    headline: str
    action_summary: str


class DecisionDetailResponse(BaseModel):
    """Full decision details including 7 Questions."""

    decision_id: str
    customer_id: str
    signal_id: Optional[str]
    chokepoint: str
    severity: str
    urgency: str

    # 7 Questions
    q1_what: dict
    q2_when: dict
    q3_severity: dict
    q4_why: dict
    q5_action: dict
    q6_confidence: dict
    q7_inaction: dict

    # Metrics
    exposure_usd: float
    potential_loss_usd: float
    potential_delay_days: float
    confidence_score: float

    # Action
    recommended_action: str
    action_cost_usd: float
    action_deadline: Optional[datetime]

    # Validity
    valid_until: datetime
    is_expired: bool

    # Timestamps
    created_at: datetime


class PaginationMeta(BaseModel):
    """Pagination metadata."""

    total: int = Field(description="Total number of items")
    limit: int = Field(description="Items per page")
    offset: int = Field(description="Current offset")
    has_more: bool = Field(description="Whether there are more items")


class DecisionListResponse(BaseModel):
    """List of decisions with pagination."""

    items: list[DecisionSummaryResponse]
    pagination: PaginationMeta


class GenerateAllResponse(BaseModel):
    """Response from bulk decision generation."""

    generated: int
    customer_decisions: dict[str, str]  # customer_id -> decision_id
    errors: list[str]


class FeedbackRequest(BaseModel):
    """Request to provide feedback on a decision."""

    feedback: str = Field(min_length=1, max_length=1000, description="User feedback")
    action_taken: Optional[ActionType] = Field(default=None, description="Action customer took")


# ============================================================================
# HELPERS
# ============================================================================


def decision_to_summary(decision: DecisionObject) -> DecisionSummaryResponse:
    """Convert DecisionObject to summary response."""
    return DecisionSummaryResponse(
        decision_id=decision.decision_id,
        customer_id=decision.customer_id,
        signal_id=decision.signal_id,
        chokepoint=decision.chokepoint,
        severity=decision.severity.value,
        urgency=decision.urgency.value,
        recommended_action=decision.q5_action.primary_action.action_type.value,
        action_cost_usd=decision.q5_action.primary_action.estimated_cost_usd,
        exposure_usd=decision.q3_severity.total_exposure_usd,
        potential_loss_usd=decision.q3_severity.potential_loss_usd,
        potential_delay_days=decision.q3_severity.potential_delay_days,
        confidence_score=decision.q6_confidence.confidence_score,
        valid_until=decision.valid_until,
        created_at=decision.created_at,
        headline=decision.q1_what.headline,
        action_summary=decision.q5_action.primary_action.description,
    )


def decision_to_detail(decision: DecisionObject) -> DecisionDetailResponse:
    """Convert DecisionObject to detail response."""
    return DecisionDetailResponse(
        decision_id=decision.decision_id,
        customer_id=decision.customer_id,
        signal_id=decision.signal_id,
        chokepoint=decision.chokepoint,
        severity=decision.severity.value,
        urgency=decision.urgency.value,
        q1_what=decision.q1_what.model_dump(),
        q2_when=decision.q2_when.model_dump(),
        q3_severity=decision.q3_severity.model_dump(),
        q4_why=decision.q4_why.model_dump(),
        q5_action=decision.q5_action.model_dump(),
        q6_confidence=decision.q6_confidence.model_dump(),
        q7_inaction=decision.q7_inaction.model_dump(),
        exposure_usd=decision.q3_severity.total_exposure_usd,
        potential_loss_usd=decision.q3_severity.potential_loss_usd,
        potential_delay_days=decision.q3_severity.potential_delay_days,
        confidence_score=decision.q6_confidence.confidence_score,
        recommended_action=decision.q5_action.primary_action.action_type.value,
        action_cost_usd=decision.q5_action.primary_action.estimated_cost_usd,
        action_deadline=decision.q5_action.primary_action.deadline,
        valid_until=decision.valid_until,
        is_expired=decision.is_expired,
        created_at=decision.created_at,
    )


# ============================================================================
# DEPENDENCY: Get RiskCast Service
# ============================================================================


async def get_riskcast(
    session: AsyncSession = Depends(get_db_session),
) -> AsyncRiskCastService:
    """Get RISKCAST service with database session."""
    return create_async_riskcast_service(session, use_cache=True)


# ============================================================================
# ENDPOINTS
# ============================================================================


@router.post(
    "/generate",
    response_model=DecisionDetailResponse,
    summary="Generate decision",
    description="Generate a decision for a specific customer based on current intelligence",
)
async def generate_decision(
    request: GenerateDecisionRequest,
    auth: Annotated[AuthContext, Depends(require_scope(Scopes.WRITE_DECISIONS))],
    session: AsyncSession = Depends(get_db_session),
    idempotency_key: Optional[str] = Depends(check_idempotency),
) -> DecisionDetailResponse:
    """
    Generate a decision for a customer.

    Uses current OMEN signals correlated with ORACLE reality data.

    Requires: decisions:write scope

    Headers:
        X-API-Key: API key (required)
        X-Idempotency-Key: Idempotency key (optional, prevents duplicate generation)
    """
    # Check customer access (unless admin)
    if not auth.is_admin and request.customer_id != auth.customer_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Cannot generate decision for customer {request.customer_id}",
        )

    repo = PostgresCustomerRepository(session)
    riskcast = create_async_riskcast_service(session, use_cache=True)

    # Get customer context
    context = await repo.get_context(request.customer_id)
    if not context:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer {request.customer_id} not found",
        )

    if not context.active_shipments:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Customer has no active shipments",
        )

    # Get intelligence from ORACLE
    oracle = get_oracle_service()

    if request.signal_id:
        # Use specific signal
        from app.omen.service import get_omen_service
        omen = get_omen_service()
        signal = await omen.get_signal(request.signal_id)

        if not signal:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Signal {request.signal_id} not found",
            )

        intelligence = await oracle.get_correlated_intelligence(signal)
        intel_list = [intelligence]
    else:
        # Get actionable intelligence
        intel_list = await oracle.get_actionable_intelligence(
            chokepoints=[request.chokepoint] if request.chokepoint else None,
        )

    if not intel_list:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No actionable intelligence available",
        )

    # Use the highest confidence intelligence
    intelligence = max(intel_list, key=lambda x: x.combined_confidence)

    # Generate decision
    try:
        decision = await riskcast.generate_decision(intelligence, context)
    except NoExposureError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )

    # Store idempotency response
    if idempotency_key:
        store = get_idempotency_store()
        store.set_response(
            idempotency_key,
            auth.customer_id,
            decision_to_detail(decision).model_dump(mode="json"),
        )

    return decision_to_detail(decision)


@router.post(
    "/generate-all",
    response_model=GenerateAllResponse,
    summary="Generate decisions for all affected customers",
    description="Bulk generate decisions for all customers affected by current signals",
)
async def generate_all_decisions(
    auth: Annotated[AuthContext, Depends(require_scope(Scopes.ADMIN, Scopes.WRITE_DECISIONS))],
    chokepoint: Optional[str] = Query(default=None, description="Filter by chokepoint"),
    background_tasks: BackgroundTasks = None,
    session: AsyncSession = Depends(get_db_session),
) -> GenerateAllResponse:
    """
    Generate decisions for all affected customers.

    This is typically called when a new signal is detected.

    Requires: admin or decisions:write scope
    """
    riskcast = create_async_riskcast_service(session, use_cache=True)
    oracle = get_oracle_service()

    # Get actionable intelligence
    intel_list = await oracle.get_actionable_intelligence(
        chokepoints=[chokepoint] if chokepoint else None,
    )

    if not intel_list:
        return GenerateAllResponse(
            generated=0,
            customer_decisions={},
            errors=["No actionable intelligence available"],
        )

    # Use highest priority intelligence
    intelligence = intel_list[0]

    # Process for all affected customers
    decisions, errors = await riskcast.process_signal_for_all(
        intelligence, chokepoint=chokepoint
    )

    customer_decisions = {d.customer_id: d.decision_id for d in decisions}

    return GenerateAllResponse(
        generated=len(decisions),
        customer_decisions=customer_decisions,
        errors=errors,
    )


@router.get(
    "/{decision_id}",
    response_model=DecisionDetailResponse,
    summary="Get decision",
    description="Get decision by ID",
)
async def get_decision(
    decision_id: str,
    auth: Annotated[AuthContext, Depends(require_scope(Scopes.READ_DECISIONS))],
    session: AsyncSession = Depends(get_db_session),
) -> DecisionDetailResponse:
    """
    Get decision by ID.

    Requires: decisions:read scope

    Note: Non-admin users can only access their own decisions.
    """
    riskcast = create_async_riskcast_service(session, use_cache=True)
    decision = await riskcast.get_decision(decision_id)

    if not decision:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Decision {decision_id} not found",
        )

    # Check access - non-admin can only see own decisions
    if not auth.is_admin and decision.customer_id != auth.customer_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot access this decision",
        )

    return decision_to_detail(decision)


@router.get(
    "/customer/{customer_id}",
    response_model=DecisionListResponse,
    summary="List customer decisions",
    description="List all decisions for a customer with pagination",
)
async def list_customer_decisions(
    customer_id: str,
    auth: Annotated[AuthContext, Depends(require_customer_access())],
    session: AsyncSession = Depends(get_db_session),
    include_expired: bool = Query(default=False, description="Include expired decisions"),
    limit: int = Query(default=20, ge=1, le=100, description="Items per page"),
    offset: int = Query(default=0, ge=0, description="Number of items to skip"),
) -> DecisionListResponse:
    """
    List decisions for a customer with pagination.

    Requires: decisions:read scope

    Non-admin users can only access their own decisions.
    """
    riskcast = create_async_riskcast_service(session, use_cache=True)
    decisions, total = await riskcast.get_customer_decisions(
        customer_id,
        include_expired=include_expired,
        limit=limit,
        offset=offset,
    )

    return DecisionListResponse(
        items=[decision_to_summary(d) for d in decisions],
        pagination=PaginationMeta(
            total=total,
            limit=limit,
            offset=offset,
            has_more=(offset + limit) < total,
        ),
    )


@router.get(
    "/active",
    response_model=DecisionListResponse,
    summary="List active decisions",
    description="List all active (non-expired) decisions",
)
async def list_active_decisions(
    auth: Annotated[AuthContext, Depends(require_scope(Scopes.READ_DECISIONS))],
    session: AsyncSession = Depends(get_db_session),
    chokepoint: Optional[str] = Query(default=None, description="Filter by chokepoint"),
    severity: Optional[Severity] = Query(default=None, description="Filter by severity"),
    limit: int = Query(default=20, ge=1, le=100, description="Items per page"),
    offset: int = Query(default=0, ge=0, description="Number of items to skip"),
) -> DecisionListResponse:
    """
    List all active decisions.

    Requires: decisions:read scope

    Non-admin users only see their own decisions.
    """
    riskcast = create_async_riskcast_service(session, use_cache=True)

    # Non-admin users can only see their own decisions
    customer_id = None if auth.is_admin else auth.customer_id

    decisions, total = await riskcast.get_active_decisions(
        customer_id=customer_id,
        limit=limit,
        offset=offset,
    )

    # Apply additional filters (in-memory for now, should be in DB query)
    if chokepoint:
        decisions = [d for d in decisions if d.chokepoint == chokepoint.lower()]
        total = len(decisions)
    if severity:
        decisions = [d for d in decisions if d.severity == severity]
        total = len(decisions)

    return DecisionListResponse(
        items=[decision_to_summary(d) for d in decisions],
        pagination=PaginationMeta(
            total=total,
            limit=limit,
            offset=offset,
            has_more=(offset + limit) < total,
        ),
    )


@router.post(
    "/{decision_id}/acknowledge",
    response_model=DecisionDetailResponse,
    summary="Acknowledge decision",
    description="Mark a decision as acknowledged by the customer",
)
async def acknowledge_decision(
    decision_id: str,
    auth: Annotated[AuthContext, Depends(require_scope(Scopes.WRITE_DECISIONS))],
    session: AsyncSession = Depends(get_db_session),
    action_taken: Optional[ActionType] = Query(default=None, description="Action customer took"),
) -> DecisionDetailResponse:
    """
    Acknowledge a decision.

    Requires: decisions:write scope

    Non-admin users can only acknowledge their own decisions.
    """
    riskcast = create_async_riskcast_service(session, use_cache=True)

    # First get the decision to check ownership
    decision = await riskcast.get_decision(decision_id)

    if not decision:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Decision {decision_id} not found",
        )

    # Check access
    if not auth.is_admin and decision.customer_id != auth.customer_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot acknowledge this decision",
        )

    # Acknowledge
    updated = await riskcast.acknowledge_decision(
        decision_id,
        action_taken=action_taken.value if action_taken else None,
    )

    return decision_to_detail(updated)


@router.post(
    "/{decision_id}/feedback",
    response_model=DecisionDetailResponse,
    summary="Provide feedback",
    description="Provide feedback on a decision",
)
async def provide_feedback(
    decision_id: str,
    request: FeedbackRequest,
    auth: Annotated[AuthContext, Depends(require_scope(Scopes.WRITE_DECISIONS))],
    session: AsyncSession = Depends(get_db_session),
) -> DecisionDetailResponse:
    """
    Provide feedback on a decision.

    Requires: decisions:write scope

    Non-admin users can only provide feedback on their own decisions.
    """
    riskcast = create_async_riskcast_service(session, use_cache=True)

    # First get the decision to check ownership
    decision = await riskcast.get_decision(decision_id)

    if not decision:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Decision {decision_id} not found",
        )

    # Check access
    if not auth.is_admin and decision.customer_id != auth.customer_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot provide feedback on this decision",
        )

    # Record feedback
    updated = await riskcast.record_feedback(decision_id, request.feedback)

    # If action taken was provided, also record that
    if request.action_taken:
        updated = await riskcast.acknowledge_decision(
            decision_id,
            action_taken=request.action_taken.value,
        )

    return decision_to_detail(updated)


@router.get(
    "/summary",
    summary="Get decision summary",
    description="Get summary statistics for decisions",
)
async def get_summary(
    auth: Annotated[AuthContext, Depends(require_scope(Scopes.READ_DECISIONS))],
    session: AsyncSession = Depends(get_db_session),
    customer_id: Optional[str] = Query(default=None, description="Filter by customer (admin only)"),
) -> dict:
    """
    Get summary statistics for decisions.

    Requires: decisions:read scope

    Non-admin users only see their own summary.
    """
    riskcast = create_async_riskcast_service(session, use_cache=True)

    # Non-admin users can only see their own summary
    if not auth.is_admin:
        customer_id = auth.customer_id
    elif customer_id is None:
        # Admin without filter sees all
        pass

    return await riskcast.get_summary(customer_id)


# ============================================================================
# JUSTIFICATION ENDPOINTS
# ============================================================================


@router.get(
    "/{decision_id}/justification",
    summary="Get decision justification",
    description="Generate justification document for a decision at specified level",
)
async def get_justification(
    decision_id: str,
    auth: Annotated[AuthContext, Depends(require_scope(Scopes.READ_DECISIONS))],
    session: AsyncSession = Depends(get_db_session),
    level: str = Query(
        default="detailed",
        description="Justification level: executive, detailed, audit, legal",
    ),
    audience: str = Query(
        default="analyst",
        description="Target audience: executive, analyst, auditor, legal, regulator",
    ),
    language: str = Query(default="en", description="Language: en, vi"),
):
    """
    Generate justification document for a decision.

    Levels:
    - EXECUTIVE: One paragraph summary (fastest)
    - DETAILED: Full 7 Questions format (text)
    - AUDIT: Technical trace with calculations (JSON)
    - LEGAL: Court-admissible document with full provenance (JSON)

    Legal level requires 'decisions:legal' scope.

    Requires: decisions:read scope
    """
    from app.audit import (
        JustificationLevel,
        Audience as JustificationAudience,
        create_justification_generator,
        AuditService,
        AuditRepository,
    )

    # Validate level
    try:
        justification_level = JustificationLevel(level.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid level: {level}. Valid values: executive, detailed, audit, legal",
        )

    # Validate audience
    try:
        justification_audience = JustificationAudience(audience.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid audience: {audience}. Valid values: executive, analyst, auditor, legal, regulator",
        )

    # Legal level requires special scope
    if justification_level == JustificationLevel.LEGAL:
        if not auth.is_admin and Scopes.LEGAL_DECISIONS not in auth.scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Legal justification requires 'decisions:legal' scope",
            )

    # Get the decision
    riskcast = create_async_riskcast_service(session, use_cache=True)
    decision = await riskcast.get_decision(decision_id)

    if not decision:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Decision {decision_id} not found",
        )

    # Check access - non-admin can only see own decisions
    if not auth.is_admin and decision.customer_id != auth.customer_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot access this decision",
        )

    # Create audit service and justification generator
    audit_repo = AuditRepository(session)
    audit_service = AuditService(repository=audit_repo)
    await audit_service.initialize()
    generator = create_justification_generator(audit_service)

    # Generate justification
    result = await generator.generate(
        decision=decision,
        level=justification_level,
        audience=justification_audience,
        language=language,
    )

    # Return appropriate format
    if justification_level in [JustificationLevel.EXECUTIVE, JustificationLevel.DETAILED]:
        return {"justification": result, "level": level, "decision_id": decision_id}
    else:
        # AUDIT and LEGAL levels return full object
        return result.model_dump() if hasattr(result, 'model_dump') else result


@router.get(
    "/{decision_id}/audit-trail",
    summary="Get decision audit trail",
    description="Get the complete cryptographic audit trail for a decision",
)
async def get_audit_trail(
    decision_id: str,
    auth: Annotated[AuthContext, Depends(require_scope(Scopes.READ_DECISIONS))],
    session: AsyncSession = Depends(get_db_session),
):
    """
    Get complete audit trail for a decision.

    Returns:
    - Input snapshot (what data was available)
    - Processing record (how decision was computed)
    - All audit events (decision, delivery, feedback, etc.)
    - Chain verification status

    Requires: decisions:read scope (admin or own decisions)
    """
    from app.audit import AuditService, AuditRepository

    # Get the decision first to check access
    riskcast = create_async_riskcast_service(session, use_cache=True)
    decision = await riskcast.get_decision(decision_id)

    if not decision:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Decision {decision_id} not found",
        )

    # Check access
    if not auth.is_admin and decision.customer_id != auth.customer_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot access this decision's audit trail",
        )

    # Create audit service
    audit_repo = AuditRepository(session)
    audit_service = AuditService(repository=audit_repo)
    await audit_service.initialize()

    # Get audit trail
    trail = await audit_service.get_decision_audit_trail(decision_id)

    return trail


@router.get(
    "/{decision_id}/reasoning-trace",
    summary="Get decision reasoning trace",
    description="Get the complete 6-layer reasoning trace for a decision",
)
async def get_reasoning_trace(
    decision_id: str,
    auth: Annotated[AuthContext, Depends(require_scope(Scopes.READ_DECISIONS))],
    session: AsyncSession = Depends(get_db_session),
):
    """
    Get the complete reasoning trace for a decision.

    The reasoning trace shows how the decision was made through 6 layers:
    1. FACTUAL - What facts were verified
    2. TEMPORAL - Timeline and deadline analysis
    3. CAUSAL - Root causes and causal chain
    4. COUNTERFACTUAL - What-if scenario analysis
    5. STRATEGIC - Customer strategy alignment
    6. META - Decision to decide or escalate

    Returns the full ReasoningTrace including:
    - Each layer's output with confidence scores
    - Execution timing for each layer
    - Warnings and quality flags
    - Final decision or escalation reason

    Requires: decisions:read scope (admin or own decisions)
    """
    from app.audit import AuditService, AuditRepository
    from app.reasoning import ReasoningTrace

    # Get the decision first to check access
    riskcast = create_async_riskcast_service(session, use_cache=True)
    decision = await riskcast.get_decision(decision_id)

    if not decision:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Decision {decision_id} not found",
        )

    # Check access
    if not auth.is_admin and decision.customer_id != auth.customer_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot access this decision's reasoning trace",
        )

    # Get audit trail to find reasoning trace ID
    audit_repo = AuditRepository(session)
    audit_service = AuditService(repository=audit_repo)
    await audit_service.initialize()

    trail = await audit_service.get_decision_audit_trail(decision_id)

    # Extract reasoning trace info from processing record
    reasoning_info = {
        "decision_id": decision_id,
        "trace_available": False,
        "message": "Reasoning trace retrieval requires trace storage implementation",
    }

    if trail.processing_record:
        reasoning_info.update({
            "trace_available": True,
            "trace_id": trail.processing_record.reasoning_trace_id or f"trace_{decision_id}",
            "model_version": trail.processing_record.model_version,
            "config_version": trail.processing_record.config_version,
            "computation_time_ms": trail.processing_record.computation_time_ms,
            "layers_executed": trail.processing_record.layers_executed or [
                "factual", "temporal", "causal", "counterfactual", "strategic", "meta"
            ],
            "warnings": trail.processing_record.warnings,
            "degradation_level": trail.processing_record.degradation_level,
            "stale_data_sources": trail.processing_record.stale_data_sources,
            "missing_data_sources": trail.processing_record.missing_data_sources,
        })

    # Include layer summary from decision Q6 (confidence)
    if hasattr(decision, 'q6_confidence') and decision.q6_confidence:
        q6 = decision.q6_confidence
        if hasattr(q6, 'factors'):
            reasoning_info["confidence_factors"] = q6.factors if isinstance(q6.factors, dict) else {}
        if hasattr(q6, 'caveats'):
            reasoning_info["confidence_caveats"] = q6.caveats if isinstance(q6.caveats, list) else []

    return reasoning_info


@router.get(
    "/{decision_id}/sensitivity",
    summary="Get decision sensitivity analysis",
    description="Analyze how sensitive the decision is to changes in input parameters",
)
async def get_sensitivity_analysis(
    decision_id: str,
    auth: Annotated[AuthContext, Depends(require_scope(Scopes.READ_DECISIONS))],
    session: AsyncSession = Depends(get_db_session),
):
    """
    Get sensitivity analysis for a decision.

    This analysis shows:
    - Decision robustness score (0=fragile, 1=robust)
    - Key drivers that most affect the decision
    - Fragile factors (headroom < 20%)
    - Decision boundaries for each input
    - Recommendations for human review

    A "fragile" decision is one where small changes in inputs could
    flip the recommendation. These decisions should receive human review.

    Requires: decisions:read scope (admin or own decisions)
    """
    from app.analysis import (
        SensitivityAnalyzer,
        DecisionRobustness,
        create_sensitivity_analyzer,
    )

    # Get the decision first to check access
    riskcast = create_async_riskcast_service(session, use_cache=True)
    decision = await riskcast.get_decision(decision_id)

    if not decision:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Decision {decision_id} not found",
        )

    # Check access
    if not auth.is_admin and decision.customer_id != auth.customer_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot access this decision's sensitivity analysis",
        )

    # Extract key metrics from decision for sensitivity analysis
    base_inputs = {
        "probability": decision.q6_confidence.confidence_score,
        "exposure_usd": decision.q3_severity.total_exposure_usd,
        "delay_days": decision.q3_severity.potential_delay_days,
        "action_cost_usd": decision.q5_action.primary_action.estimated_cost_usd,
    }

    # Define input ranges
    input_ranges = {
        "probability": (0.0, 1.0),
        "exposure_usd": (0.0, base_inputs["exposure_usd"] * 3),
        "delay_days": (0, base_inputs["delay_days"] * 2 if base_inputs["delay_days"] > 0 else 30),
        "action_cost_usd": (0.0, base_inputs["action_cost_usd"] * 3 if base_inputs["action_cost_usd"] > 0 else 50000),
    }

    # Create decision function that returns (action, utility)
    async def decision_function(inputs: dict) -> tuple[str, float]:
        """Simplified decision function for sensitivity analysis."""
        prob = inputs.get("probability", 0.5)
        exposure = inputs.get("exposure_usd", 0)
        delay = inputs.get("delay_days", 0)
        cost = inputs.get("action_cost_usd", 0)

        # Calculate expected loss without action
        expected_loss = prob * exposure

        # Calculate utility of action (mitigated risk minus cost)
        # Assume action mitigates 70% of risk
        mitigation_rate = 0.70
        utility_with_action = expected_loss * mitigation_rate - cost

        # Decision thresholds based on current RISKCAST logic
        # REROUTE if high probability + high exposure
        # HEDGE if medium exposure
        # MONITOR if low
        if prob > 0.6 and exposure > 25000:
            return "reroute", utility_with_action
        elif prob > 0.5 and exposure > 10000:
            return "hedge", utility_with_action * 0.8
        else:
            return "monitor", expected_loss * 0.1

    # Create analyzer and run analysis
    analyzer = create_sensitivity_analyzer(
        decision_function=decision_function,
        is_async=True,
    )

    robustness = await analyzer.analyze(
        base_inputs=base_inputs,
        input_ranges=input_ranges,
    )

    # Build response
    response = {
        "decision_id": decision_id,
        "robustness_score": robustness.robustness_score,
        "base_decision": robustness.base_decision,
        "current_action": decision.q5_action.primary_action.action_type.value,
        "base_utility": robustness.base_utility,
        "is_fragile": robustness.robustness_score < 0.3,
        "requires_review": len(robustness.fragile_factors) > 0,
        "recommendation": robustness.recommendation,
        "key_drivers": [
            {
                "factor": f.factor_name,
                "current_value": f.current_value,
                "decision_boundary": f.decision_boundary,
                "headroom_pct": f.headroom if f.headroom != float('inf') else None,
                "direction": f.direction,
                "rank": f.importance_rank,
                "is_fragile": f.is_fragile,
            }
            for f in robustness.key_drivers
        ],
        "fragile_factors": [
            {
                "factor": f.factor_name,
                "current_value": f.current_value,
                "decision_boundary": f.decision_boundary,
                "headroom_pct": f.headroom,
                "direction": f.direction,
            }
            for f in robustness.fragile_factors
        ],
        "decision_boundaries": robustness.decision_boundaries,
        "analysis_confidence": robustness.confidence_in_analysis,
    }

    return response
