"""
Feedback API — Records user decisions on AI suggestions.

POST /feedback/suggestions/{id}          — Accept/reject a suggestion
POST /feedback/suggestions/{id}/outcome  — Record actual outcome
GET  /feedback/stats                     — Feedback statistics
"""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from riskcast.api.deps import get_company_id, get_db, get_user_id
from riskcast.db.models import SuggestionFeedback
from riskcast.schemas.feedback import FeedbackRequest, OutcomeRequest
from riskcast.services.feedback_loop import FeedbackProcessor

router = APIRouter(prefix="/api/v1/feedback", tags=["feedback"])
_processor = FeedbackProcessor()


@router.post("/suggestions/{suggestion_id}")
async def submit_feedback(
    suggestion_id: uuid.UUID,
    body: FeedbackRequest,
    db: AsyncSession = Depends(get_db),
    company_id: uuid.UUID = Depends(get_company_id),
    user_id: uuid.UUID = Depends(get_user_id),
):
    """Record user feedback on a suggestion (accept/reject/defer)."""
    await _processor.record_feedback(
        session=db,
        suggestion_id=str(suggestion_id),
        user_id=str(user_id),
        company_id=str(company_id),
        decision=body.decision,
        reason_code=body.reason_code,
        reason_text=body.reason_text,
    )
    return {"status": "recorded"}


@router.post("/suggestions/{suggestion_id}/outcome")
async def record_outcome(
    suggestion_id: uuid.UUID,
    body: OutcomeRequest,
    db: AsyncSession = Depends(get_db),
    company_id: uuid.UUID = Depends(get_company_id),
):
    """Record the actual outcome of a suggestion."""
    await _processor.record_outcome(
        session=db,
        suggestion_id=str(suggestion_id),
        outcome=body.outcome,
    )
    return {"status": "recorded"}


@router.get("/stats")
async def feedback_stats(
    db: AsyncSession = Depends(get_db),
    company_id: uuid.UUID = Depends(get_company_id),
):
    """Get feedback statistics for the current tenant."""
    result = await db.execute(
        select(
            SuggestionFeedback.decision,
            func.count().label("count"),
        )
        .where(SuggestionFeedback.company_id == company_id)
        .group_by(SuggestionFeedback.decision)
    )
    rows = result.all()

    total = sum(r.count for r in rows)
    by_decision = {r.decision: r.count for r in rows}

    return {
        "total": total,
        "by_decision": by_decision,
        "acceptance_rate": round(
            by_decision.get("accepted", 0) / max(total, 1), 2
        ),
    }
