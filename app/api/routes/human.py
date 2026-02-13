"""Human-AI Collaboration API Endpoints.

Endpoints for human override, escalation, and feedback on decisions.

These endpoints enable:
- Override: Humans can override system recommendations
- Escalation: View and resolve escalated decisions
- Feedback: Submit feedback to improve system accuracy
- Trust Metrics: View human-AI collaboration metrics
"""

from typing import Optional, Annotated, List
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.auth import (
    AuthContext,
    get_auth_context,
    require_scope,
    Scopes,
)
from app.human.schemas import (
    OverrideReason,
    OverrideRequest,
    OverrideResult,
    EscalationTrigger,
    EscalationRequest,
    EscalationResolution,
    FeedbackType,
    FeedbackSubmission,
    TrustMetrics,
)
from app.human.service import (
    HumanCollaborationService,
    create_human_collaboration_service,
)
from app.audit.service import AuditService
from app.audit.repository import AuditRepository


router = APIRouter()


# ============================================================================
# REQUEST/RESPONSE SCHEMAS
# ============================================================================


class OverrideSubmitRequest(BaseModel):
    """Request to override a decision."""
    
    decision_id: str = Field(description="ID of decision to override")
    new_action_type: str = Field(
        description="New action type (e.g., 'reroute', 'delay', 'monitor')"
    )
    new_action_details: Optional[dict] = Field(
        default=None,
        description="Additional details for the new action",
    )
    reason: OverrideReason = Field(description="Categorized reason for override")
    reason_details: str = Field(
        min_length=20,
        description="Detailed explanation (minimum 20 characters)",
    )
    supporting_evidence: Optional[List[str]] = Field(
        default=None,
        description="Supporting evidence or references",
    )


class EscalationResolutionRequest(BaseModel):
    """Request to resolve an escalation."""
    
    resolution: str = Field(
        description="Resolution type: APPROVE, MODIFY, REJECT"
    )
    final_action: str = Field(description="Final action to take")
    resolution_reason: str = Field(
        min_length=10,
        description="Explanation of resolution (minimum 10 characters)",
    )


class FeedbackSubmitRequest(BaseModel):
    """Request to submit feedback."""
    
    decision_id: str = Field(description="ID of decision receiving feedback")
    feedback_type: FeedbackType = Field(description="Category of feedback")
    rating: int = Field(ge=1, le=5, description="Rating from 1 (poor) to 5 (excellent)")
    comment: str = Field(
        default="",
        max_length=2000,
        description="Free-text feedback",
    )
    would_follow_again: bool = Field(
        description="Would user follow similar advice in future?"
    )
    actual_delay_days: Optional[int] = Field(
        default=None,
        ge=0,
        description="Actual delay experienced (for calibration)",
    )
    actual_cost_usd: Optional[float] = Field(
        default=None,
        ge=0,
        description="Actual cost incurred (for calibration)",
    )
    event_occurred: Optional[bool] = Field(
        default=None,
        description="Did the predicted event actually occur?",
    )


class EscalationListResponse(BaseModel):
    """List of escalations."""
    
    items: List[EscalationRequest]
    total: int


class FeedbackListResponse(BaseModel):
    """List of feedback submissions."""
    
    items: List[dict]
    total: int


# ============================================================================
# DEPENDENCY: Get Human Collaboration Service
# ============================================================================


async def get_human_service(
    session: AsyncSession = Depends(get_db_session),
) -> HumanCollaborationService:
    """Get Human Collaboration service with dependencies."""
    # Create audit service
    audit_repo = AuditRepository(session)
    audit_service = AuditService(repository=audit_repo)
    await audit_service.initialize()
    
    # Create human collaboration service
    return create_human_collaboration_service(
        audit_service=audit_service,
        decision_repository=None,  # Would inject real repo in production
    )


# ============================================================================
# OVERRIDE ENDPOINTS
# ============================================================================


@router.post(
    "/override",
    response_model=OverrideResult,
    summary="Override a decision",
    description="Override a system decision with human judgment",
    status_code=status.HTTP_201_CREATED,
)
async def override_decision(
    request: OverrideSubmitRequest,
    auth: Annotated[AuthContext, Depends(require_scope(Scopes.WRITE_DECISIONS))],
    service: HumanCollaborationService = Depends(get_human_service),
) -> OverrideResult:
    """
    Override a system decision with human judgment.
    
    Creates an immutable audit record showing:
    - What the system recommended
    - What the human decided instead
    - Why the override was made
    
    Requires: decisions:write scope
    
    IMPORTANT: Overrides are logged as warnings because they may indicate
    system issues or calibration problems that need investigation.
    """
    # Create internal override request
    override_request = OverrideRequest(
        decision_id=request.decision_id,
        new_action_type=request.new_action_type,
        new_action_details=request.new_action_details,
        reason=request.reason,
        reason_details=request.reason_details,
        supporting_evidence=request.supporting_evidence,
    )
    
    try:
        result = await service.override_decision(
            user_id=auth.user_id or auth.api_key_id,
            request=override_request,
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get(
    "/override/reasons",
    summary="List override reasons",
    description="Get all valid override reason categories",
)
async def list_override_reasons(
    auth: Annotated[AuthContext, Depends(require_scope(Scopes.READ_DECISIONS))],
) -> List[dict]:
    """
    Get all valid override reason categories.
    
    Useful for building UI dropdowns.
    """
    return [
        {
            "value": reason.value,
            "name": reason.name,
            "description": _get_reason_description(reason),
        }
        for reason in OverrideReason
    ]


def _get_reason_description(reason: OverrideReason) -> str:
    """Get human-readable description for override reason."""
    descriptions = {
        OverrideReason.BETTER_INFORMATION: "Human has information the system doesn't have",
        OverrideReason.CUSTOMER_REQUEST: "Customer explicitly requested different action",
        OverrideReason.MARKET_CHANGE: "Market conditions changed since decision was made",
        OverrideReason.SYSTEM_ERROR: "System made an obvious error",
        OverrideReason.RISK_TOLERANCE: "Customer's risk tolerance differs from default",
        OverrideReason.STRATEGIC: "Strategic business reason not captured by system",
        OverrideReason.RELATIONSHIP: "Carrier or customer relationship considerations",
        OverrideReason.TIMING: "Timing considerations not captured by system",
        OverrideReason.OTHER: "Other reason (must explain in detail)",
    }
    return descriptions.get(reason, "")


# ============================================================================
# ESCALATION ENDPOINTS
# ============================================================================


@router.get(
    "/escalations",
    response_model=EscalationListResponse,
    summary="List escalations",
    description="List escalated decisions pending human review",
)
async def list_escalations(
    auth: Annotated[AuthContext, Depends(require_scope(Scopes.READ_DECISIONS))],
    service: HumanCollaborationService = Depends(get_human_service),
    status_filter: str = Query(default="pending", description="Status filter: pending, resolved, all"),
    limit: int = Query(default=20, ge=1, le=100, description="Items per page"),
    offset: int = Query(default=0, ge=0, description="Number of items to skip"),
) -> EscalationListResponse:
    """
    List escalated decisions.
    
    Escalations are decisions that the system was not confident enough
    to act on automatically and require human review.
    
    Filter by status:
    - pending: Awaiting resolution
    - resolved: Already resolved
    - all: All escalations
    
    Requires: decisions:read scope
    
    Non-admin users only see escalations assigned to them.
    """
    # Get user_id for filtering (non-admin)
    user_id = None if auth.is_admin else (auth.user_id or auth.api_key_id)
    
    # Get pending escalations
    escalations = await service.get_pending_escalations(user_id=user_id)
    
    # Apply status filter
    if status_filter == "pending":
        escalations = [e for e in escalations if e.status == "pending"]
    elif status_filter == "resolved":
        escalations = [e for e in escalations if e.status == "resolved"]
    # else: all
    
    total = len(escalations)
    
    # Apply pagination
    escalations = escalations[offset:offset + limit]
    
    return EscalationListResponse(
        items=escalations,
        total=total,
    )


@router.get(
    "/escalations/{escalation_id}",
    response_model=EscalationRequest,
    summary="Get escalation",
    description="Get details of a specific escalation",
)
async def get_escalation(
    escalation_id: str,
    auth: Annotated[AuthContext, Depends(require_scope(Scopes.READ_DECISIONS))],
    service: HumanCollaborationService = Depends(get_human_service),
) -> EscalationRequest:
    """
    Get details of a specific escalation.
    
    Requires: decisions:read scope
    """
    escalation = await service.get_escalation(escalation_id)
    
    if not escalation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Escalation {escalation_id} not found",
        )
    
    # Check access for non-admin
    if not auth.is_admin:
        user_id = auth.user_id or auth.api_key_id
        if user_id not in escalation.escalated_to:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view this escalation",
            )
    
    return escalation


@router.post(
    "/escalations/{escalation_id}/resolve",
    response_model=EscalationResolution,
    summary="Resolve escalation",
    description="Resolve a pending escalation with a decision",
)
async def resolve_escalation(
    escalation_id: str,
    request: EscalationResolutionRequest,
    auth: Annotated[AuthContext, Depends(require_scope(Scopes.WRITE_DECISIONS))],
    service: HumanCollaborationService = Depends(get_human_service),
) -> EscalationResolution:
    """
    Resolve a pending escalation.
    
    Resolution types:
    - APPROVE: Accept system recommendation as-is
    - MODIFY: Accept with modifications
    - REJECT: Reject system recommendation entirely
    
    Creates an immutable audit record of the resolution.
    
    Requires: decisions:write scope
    """
    try:
        resolution = await service.resolve_escalation(
            user_id=auth.user_id or auth.api_key_id,
            escalation_id=escalation_id,
            resolution=request.resolution,
            final_action=request.final_action,
            resolution_reason=request.resolution_reason,
        )
        return resolution
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get(
    "/escalation/triggers",
    summary="List escalation triggers",
    description="Get all possible escalation triggers",
)
async def list_escalation_triggers(
    auth: Annotated[AuthContext, Depends(require_scope(Scopes.READ_DECISIONS))],
) -> List[dict]:
    """
    Get all possible escalation triggers.
    
    Useful for understanding why decisions are escalated.
    """
    descriptions = {
        EscalationTrigger.LOW_CONFIDENCE: "System confidence is below threshold",
        EscalationTrigger.HIGH_VALUE: "Exposure is above threshold requiring human review",
        EscalationTrigger.NOVEL_SITUATION: "No similar historical cases to learn from",
        EscalationTrigger.CONFLICTING_SIGNALS: "Multiple signals contradict each other",
        EscalationTrigger.CUSTOMER_FLAG: "Customer is flagged for manual review",
        EscalationTrigger.SYSTEM_DEGRADED: "System operating in degraded mode",
        EscalationTrigger.MANUAL_REQUEST: "User explicitly requested escalation",
        EscalationTrigger.MULTIPLE_ACTIONS: "Multiple equally good actions possible",
        EscalationTrigger.TIME_CRITICAL: "Very tight deadline requires human judgment",
        EscalationTrigger.REGULATORY: "Regulatory compliance concern",
    }
    
    return [
        {
            "value": trigger.value,
            "name": trigger.name,
            "description": descriptions.get(trigger, ""),
        }
        for trigger in EscalationTrigger
    ]


# ============================================================================
# FEEDBACK ENDPOINTS
# ============================================================================


@router.post(
    "/feedback",
    summary="Submit feedback",
    description="Submit feedback on a decision for system improvement",
    status_code=status.HTTP_201_CREATED,
)
async def submit_feedback(
    request: FeedbackSubmitRequest,
    auth: Annotated[AuthContext, Depends(require_scope(Scopes.WRITE_DECISIONS))],
    service: HumanCollaborationService = Depends(get_human_service),
) -> dict:
    """
    Submit feedback on a decision.
    
    Feedback is used for:
    - Calibration: Improving prediction accuracy
    - Quality tracking: Identifying problem areas
    - Training data: ML model improvement
    
    Creates an immutable audit record of the feedback.
    
    Requires: decisions:write scope
    """
    # Create feedback submission
    feedback = FeedbackSubmission(
        decision_id=request.decision_id,
        feedback_type=request.feedback_type,
        rating=request.rating,
        comment=request.comment,
        would_follow_again=request.would_follow_again,
        actual_delay_days=request.actual_delay_days,
        actual_cost_usd=request.actual_cost_usd,
        event_occurred=request.event_occurred,
    )
    
    feedback_id = await service.submit_feedback(
        user_id=auth.user_id or auth.api_key_id,
        feedback=feedback,
    )
    
    return {
        "feedback_id": feedback_id,
        "decision_id": request.decision_id,
        "message": "Feedback submitted successfully",
    }


@router.get(
    "/feedback/{decision_id}",
    response_model=FeedbackListResponse,
    summary="Get feedback for decision",
    description="Get all feedback submitted for a decision",
)
async def get_decision_feedback(
    decision_id: str,
    auth: Annotated[AuthContext, Depends(require_scope(Scopes.READ_DECISIONS))],
    service: HumanCollaborationService = Depends(get_human_service),
) -> FeedbackListResponse:
    """
    Get all feedback for a specific decision.
    
    Requires: decisions:read scope
    """
    feedbacks = await service.get_feedback_for_decision(decision_id)
    
    return FeedbackListResponse(
        items=feedbacks,
        total=len(feedbacks),
    )


@router.get(
    "/feedback/types",
    summary="List feedback types",
    description="Get all valid feedback type categories",
)
async def list_feedback_types(
    auth: Annotated[AuthContext, Depends(require_scope(Scopes.READ_DECISIONS))],
) -> List[dict]:
    """
    Get all valid feedback type categories.
    
    Useful for building UI dropdowns.
    """
    descriptions = {
        FeedbackType.DECISION_QUALITY: "Overall quality of the decision",
        FeedbackType.TIMING: "Accuracy of timing advice",
        FeedbackType.COST_ACCURACY: "Accuracy of cost estimates",
        FeedbackType.DELAY_ACCURACY: "Accuracy of delay estimates",
        FeedbackType.COMMUNICATION: "How well the decision was communicated",
        FeedbackType.ACTIONABILITY: "Whether the action could actually be taken",
        FeedbackType.GENERAL: "General feedback",
    }
    
    return [
        {
            "value": ft.value,
            "name": ft.name,
            "description": descriptions.get(ft, ""),
        }
        for ft in FeedbackType
    ]


# ============================================================================
# TRUST METRICS ENDPOINTS
# ============================================================================


@router.get(
    "/metrics/trust",
    response_model=TrustMetrics,
    summary="Get trust metrics",
    description="Get human-AI collaboration trust metrics",
)
async def get_trust_metrics(
    auth: Annotated[AuthContext, Depends(require_scope(Scopes.READ_DECISIONS))],
    service: HumanCollaborationService = Depends(get_human_service),
    period_days: int = Query(default=30, ge=1, le=365, description="Period in days"),
    customer_id: Optional[str] = Query(default=None, description="Filter by customer (admin only)"),
) -> TrustMetrics:
    """
    Get human-AI collaboration trust metrics.
    
    These metrics help understand:
    - How much users trust the system
    - Where improvements are needed
    - Calibration accuracy
    
    Includes:
    - Follow/override/escalation rates
    - Average feedback ratings
    - Top override reasons
    - Top escalation triggers
    
    Requires: decisions:read scope
    
    Non-admin users only see their own metrics.
    """
    # Non-admin users can only see their own metrics
    if not auth.is_admin:
        customer_id = auth.customer_id
    
    metrics = await service.calculate_trust_metrics(
        period_days=period_days,
        customer_id=customer_id,
    )
    
    return metrics


@router.post(
    "/escalate/{decision_id}",
    response_model=EscalationRequest,
    summary="Manually escalate decision",
    description="Manually escalate a decision for human review",
    status_code=status.HTTP_201_CREATED,
)
async def manually_escalate(
    decision_id: str,
    auth: Annotated[AuthContext, Depends(require_scope(Scopes.WRITE_DECISIONS))],
    service: HumanCollaborationService = Depends(get_human_service),
    session: AsyncSession = Depends(get_db_session),
    reason: str = Query(description="Reason for manual escalation"),
    escalate_to: Optional[List[str]] = Query(default=None, description="User IDs to escalate to"),
) -> EscalationRequest:
    """
    Manually escalate a decision for human review.
    
    Use this when you want a second opinion on a decision,
    even if the system didn't automatically escalate it.
    
    Requires: decisions:write scope
    """
    from app.riskcast.service import create_async_riskcast_service
    
    # Get the decision
    riskcast = create_async_riskcast_service(session, use_cache=True)
    decision = await riskcast.get_decision(decision_id)
    
    if not decision:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Decision {decision_id} not found",
        )
    
    # Check access for non-admin
    if not auth.is_admin and decision.customer_id != auth.customer_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot escalate this decision",
        )
    
    # Escalate
    escalation = await service.escalate_decision(
        decision=decision,
        trigger=EscalationTrigger.MANUAL_REQUEST,
        trigger_details=f"Manual escalation by {auth.user_id or auth.api_key_id}: {reason}",
        escalated_to=escalate_to or [],
    )
    
    return escalation
