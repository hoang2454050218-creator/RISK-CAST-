"""
Decision API Endpoints.

GET  /api/v1/decisions/active                   — list all active/recent decisions
POST /api/v1/decisions/generate                 — generate decision for one entity
POST /api/v1/decisions/generate-all             — generate decisions for all at-risk entities
GET  /api/v1/decisions/{decision_id}            — get a decision (future: from DB)
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from riskcast.api.deps import get_company_id, get_db
from riskcast.decisions.engine import DecisionEngine
from riskcast.decisions.schemas import Decision, DecisionListResponse

router = APIRouter(prefix="/api/v1/decisions", tags=["decisions"])

_engine = DecisionEngine()


@router.get("/active", response_model=DecisionListResponse)
async def list_active_decisions(
    status: Optional[str] = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    company_id: uuid.UUID = Depends(get_company_id),
):
    """List active/recent decisions for the current company."""
    # Generate decisions on-the-fly for at-risk entities (no DB persistence yet)
    try:
        result = await _engine.generate_decisions_for_company(
            db, str(company_id), "order", 30.0, limit
        )
        return result
    except Exception:
        # Return empty list if no data available
        return DecisionListResponse(decisions=[], total=0)


@router.post("/generate", response_model=Decision)
async def generate_decision(
    entity_type: str = Query(default="order"),
    entity_id: str = Query(...),
    exposure_usd: Optional[float] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    company_id: uuid.UUID = Depends(get_company_id),
):
    """Generate a decision for a specific entity. Fully auditable."""
    return await _engine.generate_decision(
        db, str(company_id), entity_type, entity_id, exposure_usd
    )


@router.post("/generate-all", response_model=DecisionListResponse)
async def generate_all_decisions(
    entity_type: str = Query(default="order"),
    min_severity: float = Query(default=30.0, ge=0, le=100),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    company_id: uuid.UUID = Depends(get_company_id),
):
    """Generate decisions for all at-risk entities."""
    return await _engine.generate_decisions_for_company(
        db, str(company_id), entity_type, min_severity, limit
    )
