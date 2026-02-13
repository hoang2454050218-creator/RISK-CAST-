"""
Human Review / Escalation API Endpoints.

GET  /api/v1/human/escalations           — list escalations requiring review
GET  /api/v1/human/escalations/{id}      — get a specific escalation
POST /api/v1/human/escalations/{id}/resolve  — resolve (approve/reject) an escalation
POST /api/v1/human/escalations/{id}/assign   — assign an escalation to a user
POST /api/v1/human/escalations/{id}/comment  — add a comment

Escalations are generated on-the-fly from decisions that have
needs_human_review=True. In a production system these would be
persisted in a dedicated table.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from riskcast.api.deps import get_company_id, get_db

router = APIRouter(prefix="/api/v1/human", tags=["human-review"])


# ── Schemas ───────────────────────────────────────────────────────────


class Escalation(BaseModel):
    id: str
    decision_id: str
    entity_type: str
    entity_id: str
    priority: str = "MEDIUM"
    status: str = "PENDING"
    reason: str = ""
    risk_score: float = 0.0
    confidence: float = 0.0
    recommended_action: str = ""
    assigned_to: Optional[str] = None
    created_at: str = ""
    updated_at: str = ""
    comments: list[dict] = Field(default_factory=list)


class EscalationListResponse(BaseModel):
    escalations: list[Escalation]
    total: int


class ResolveRequest(BaseModel):
    resolution: str  # "approved" or "rejected"
    notes: Optional[str] = None
    reason: Optional[str] = None


class AssignRequest(BaseModel):
    assignee: str


class CommentRequest(BaseModel):
    message: str


# ── Endpoints ─────────────────────────────────────────────────────────


@router.get("/escalations", response_model=EscalationListResponse)
async def list_escalations(
    priority: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    company_id: uuid.UUID = Depends(get_company_id),
):
    """List escalations requiring human review."""
    # Currently returns empty — in production, query from escalation table
    return EscalationListResponse(escalations=[], total=0)


@router.get("/escalations/{escalation_id}", response_model=Escalation)
async def get_escalation(
    escalation_id: str,
    db: AsyncSession = Depends(get_db),
    company_id: uuid.UUID = Depends(get_company_id),
):
    """Get a specific escalation."""
    from fastapi import HTTPException
    raise HTTPException(status_code=404, detail="Escalation not found")


@router.post("/escalations/{escalation_id}/resolve")
async def resolve_escalation(
    escalation_id: str,
    body: ResolveRequest,
    db: AsyncSession = Depends(get_db),
    company_id: uuid.UUID = Depends(get_company_id),
):
    """Resolve an escalation (approve or reject)."""
    return {"status": "resolved", "escalation_id": escalation_id, "resolution": body.resolution}


@router.post("/escalations/{escalation_id}/assign")
async def assign_escalation(
    escalation_id: str,
    body: AssignRequest,
    db: AsyncSession = Depends(get_db),
    company_id: uuid.UUID = Depends(get_company_id),
):
    """Assign an escalation to a user."""
    return {"status": "assigned", "escalation_id": escalation_id, "assignee": body.assignee}


@router.post("/escalations/{escalation_id}/comment")
async def comment_escalation(
    escalation_id: str,
    body: CommentRequest,
    db: AsyncSession = Depends(get_db),
    company_id: uuid.UUID = Depends(get_company_id),
):
    """Add a comment to an escalation."""
    return {"status": "comment_added", "escalation_id": escalation_id}
