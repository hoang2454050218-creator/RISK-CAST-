"""
Morning Brief API.

GET  /api/v1/briefs/today     — Get today's brief (generate if missing)
GET  /api/v1/briefs/{date}    — Get brief for a specific date
POST /api/v1/briefs/{id}/read — Mark brief as read by current user
"""

import uuid
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from riskcast.api.deps import get_company_id, get_db, get_user_id
from riskcast.db import queries as db_queries
from riskcast.db.models import MorningBrief
from riskcast.services.llm_gateway import LLMGateway
from riskcast.services.morning_brief import MorningBriefGenerator
from riskcast.services.sse_manager import sse_manager

router = APIRouter(prefix="/api/v1/briefs", tags=["briefs"])


@router.get("/today")
async def get_today_brief(
    db: AsyncSession = Depends(get_db),
    company_id: uuid.UUID = Depends(get_company_id),
):
    """
    Get today's morning brief. Generates on-demand if not yet created.
    """
    cid = str(company_id)

    # Try existing
    brief = await db_queries.get_today_brief(db, cid)
    if brief:
        return brief

    # Generate on-demand
    llm = LLMGateway()
    generator = MorningBriefGenerator(llm=llm, sse_manager=sse_manager)
    brief = await generator.generate(db, cid)

    if not brief:
        raise HTTPException(
            status_code=503,
            detail="Unable to generate brief. Please try again later.",
        )

    return brief


@router.get("/{brief_date}")
async def get_brief_by_date(
    brief_date: date,
    db: AsyncSession = Depends(get_db),
    company_id: uuid.UUID = Depends(get_company_id),
):
    """Get a morning brief for a specific date."""
    result = await db.execute(
        select(MorningBrief).where(
            and_(
                MorningBrief.company_id == company_id,
                MorningBrief.brief_date == brief_date,
            )
        )
    )
    brief = result.scalar_one_or_none()
    if not brief:
        raise HTTPException(status_code=404, detail="Brief not found for this date")

    return {
        "id": str(brief.id),
        "brief_date": str(brief.brief_date),
        "content": brief.content,
        "priority_items": brief.priority_items,
        "created_at": str(brief.created_at),
    }


@router.post("/{brief_id}/read")
async def mark_brief_read(
    brief_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    company_id: uuid.UUID = Depends(get_company_id),
    user_id: uuid.UUID = Depends(get_user_id),
):
    """Mark a brief as read by the current user."""
    result = await db.execute(
        select(MorningBrief).where(
            and_(MorningBrief.id == brief_id, MorningBrief.company_id == company_id)
        )
    )
    brief = result.scalar_one_or_none()
    if brief:
        read_list = list(brief.read_by or [])
        uid_str = str(user_id)
        if uid_str not in read_list:
            read_list.append(uid_str)
            brief.read_by = read_list
            await db.flush()
    return {"status": "marked_read"}
