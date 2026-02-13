"""
Risk Assessment API Endpoints.

GET /api/v1/risk/assess/order/{order_id}     — assess order risk
GET /api/v1/risk/assess/customer/{cust_id}   — assess customer risk
GET /api/v1/risk/assess/route/{route_id}     — assess route risk
GET /api/v1/risk/calibration                 — calibration report
"""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from riskcast.api.deps import get_company_id, get_db
from riskcast.engine.risk_engine import RiskEngine

router = APIRouter(prefix="/api/v1/risk", tags=["risk-engine"])

_engine = RiskEngine()


@router.get("/assess/order/{order_id}")
async def assess_order_risk(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    company_id: uuid.UUID = Depends(get_company_id),
):
    """Full risk assessment for an order. Every field is traceable."""
    result = await _engine.assess_order(db, str(company_id), str(order_id))
    return result


@router.get("/assess/customer/{customer_id}")
async def assess_customer_risk(
    customer_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    company_id: uuid.UUID = Depends(get_company_id),
):
    """Full risk assessment for a customer."""
    result = await _engine.assess_customer(db, str(company_id), str(customer_id))
    return result


@router.get("/assess/route/{route_id}")
async def assess_route_risk(
    route_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    company_id: uuid.UUID = Depends(get_company_id),
):
    """Full risk assessment for a route."""
    result = await _engine.assess_route(db, str(company_id), str(route_id))
    return result
