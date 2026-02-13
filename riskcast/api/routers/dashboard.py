"""
Dashboard API Endpoint — Real aggregated metrics.

GET /api/v1/dashboard/summary — full dashboard with real SQL data.
"""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from riskcast.api.deps import get_company_id, get_db
from riskcast.schemas.dashboard import DashboardSummary
from riskcast.services.dashboard_service import DashboardService

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])

_service = DashboardService()


@router.get("/summary", response_model=DashboardSummary)
async def dashboard_summary(
    period_days: int = Query(default=7, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
    company_id: uuid.UUID = Depends(get_company_id),
):
    """Get the full dashboard summary. Every field traces to a real query."""
    return await _service.get_summary(db, str(company_id), period_days)
