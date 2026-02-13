"""
Analytics API Endpoints — Real aggregated analytics.

GET /api/v1/analytics/risk-over-time
GET /api/v1/analytics/risk-by-category
GET /api/v1/analytics/risk-by-route
GET /api/v1/analytics/top-risk-factors
"""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from riskcast.api.deps import get_company_id, get_db
from riskcast.schemas.analytics import (
    RiskByCategoryResponse,
    RiskByRouteResponse,
    RiskOverTimeResponse,
    TopRiskFactorsResponse,
)
from riskcast.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])

_service = AnalyticsService()


@router.get("/risk-over-time", response_model=RiskOverTimeResponse)
async def risk_over_time(
    days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    company_id: uuid.UUID = Depends(get_company_id),
):
    """Average risk score per day. Reports data sufficiency."""
    return await _service.risk_over_time(db, str(company_id), days)


@router.get("/risk-by-category", response_model=RiskByCategoryResponse)
async def risk_by_category(
    db: AsyncSession = Depends(get_db),
    company_id: uuid.UUID = Depends(get_company_id),
):
    """Risk breakdown by signal type/category."""
    return await _service.risk_by_category(db, str(company_id))


@router.get("/risk-by-route", response_model=RiskByRouteResponse)
async def risk_by_route(
    db: AsyncSession = Depends(get_db),
    company_id: uuid.UUID = Depends(get_company_id),
):
    """Risk metrics per route."""
    return await _service.risk_by_route(db, str(company_id))


@router.get("/top-risk-factors", response_model=TopRiskFactorsResponse)
async def top_risk_factors(
    db: AsyncSession = Depends(get_db),
    company_id: uuid.UUID = Depends(get_company_id),
):
    """Most impactful risk factors across all active signals."""
    return await _service.top_risk_factors(db, str(company_id))
