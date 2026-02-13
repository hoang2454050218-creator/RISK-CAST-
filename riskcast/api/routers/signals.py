"""
Signal API Endpoints.

Provides:
- GET /signals — list active signals (paginated)
- GET /signals/{signal_id} — get single signal
- POST /signals/scan — trigger on-demand scan for current tenant
- GET /signals/summary — signal counts by type
"""

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from riskcast.analyzers.order_risk import OrderRiskScorer
from riskcast.analyzers.payment_risk import PaymentRiskAnalyzer
from riskcast.analyzers.route_disruption import RouteDisruptionAnalyzer
from riskcast.api.deps import get_company_id, get_db
from riskcast.config import settings
from riskcast.db.models import Signal
from riskcast.schemas.signal import SignalListResponse, SignalResponse, TriggerScanResponse
from riskcast.services.omen_client import OmenClient
from riskcast.services.scheduler import AnalyzerDbAdapter
from riskcast.services.signal_service import SignalService

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/v1/signals", tags=["signals"])


@router.get("", response_model=SignalListResponse)
async def list_signals(
    active_only: bool = Query(default=True),
    signal_type: str | None = Query(default=None),
    entity_type: str | None = Query(default=None),
    min_severity: float = Query(default=0, ge=0, le=100),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    company_id: uuid.UUID = Depends(get_company_id),
):
    """List signals for the current tenant. RLS filters automatically."""
    stmt = select(Signal)

    if active_only:
        stmt = stmt.where(Signal.is_active == True)  # noqa: E712
    if signal_type:
        stmt = stmt.where(Signal.signal_type == signal_type)
    if entity_type:
        stmt = stmt.where(Signal.entity_type == entity_type)
    if min_severity > 0:
        stmt = stmt.where(Signal.severity_score >= min_severity)

    # Count
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar_one()

    # Fetch
    stmt = stmt.order_by(Signal.severity_score.desc().nullslast()).offset(offset).limit(limit)
    result = await db.execute(stmt)
    signals = result.scalars().all()

    return SignalListResponse(
        signals=[SignalResponse.model_validate(s) for s in signals],
        total=total,
    )


@router.get("/summary")
async def signals_summary(
    db: AsyncSession = Depends(get_db),
    company_id: uuid.UUID = Depends(get_company_id),
):
    """Get signal counts grouped by type and severity."""
    result = await db.execute(
        select(
            Signal.signal_type,
            func.count().label("count"),
            func.avg(Signal.severity_score).label("avg_severity"),
            func.max(Signal.severity_score).label("max_severity"),
        )
        .where(Signal.is_active == True)  # noqa: E712
        .group_by(Signal.signal_type)
    )
    rows = result.all()

    return {
        "by_type": [
            {
                "signal_type": row.signal_type,
                "count": row.count,
                "avg_severity": round(float(row.avg_severity or 0), 1),
                "max_severity": round(float(row.max_severity or 0), 1),
            }
            for row in rows
        ],
        "total_active": sum(row.count for row in rows),
    }


@router.get("/{signal_id}", response_model=SignalResponse)
async def get_signal(
    signal_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    company_id: uuid.UUID = Depends(get_company_id),
):
    """Get a single signal by ID."""
    result = await db.execute(
        select(Signal).where(Signal.id == signal_id)
    )
    signal = result.scalar_one_or_none()
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")
    return signal


@router.post("/scan", response_model=TriggerScanResponse)
async def trigger_scan(
    db: AsyncSession = Depends(get_db),
    company_id: uuid.UUID = Depends(get_company_id),
):
    """
    Trigger an on-demand signal scan for the current tenant.

    Runs all analyzers and upserts results immediately.
    """
    cid = str(company_id)
    omen_client = OmenClient(base_url=settings.omen_url)
    db_adapter = AnalyzerDbAdapter(db)

    analyzers = [
        PaymentRiskAnalyzer(db_adapter),
        RouteDisruptionAnalyzer(db_adapter, omen_client),
        OrderRiskScorer(db_adapter),
    ]

    all_signals = []
    for analyzer in analyzers:
        try:
            signals = await analyzer.analyze(cid)
            all_signals.extend(signals)
        except Exception as e:
            logger.error(
                "on_demand_analyzer_failed",
                analyzer=type(analyzer).__name__,
                company_id=cid,
                error=str(e),
            )

    signal_service = SignalService()
    upserted = await signal_service.upsert_signals(db, cid, all_signals)

    logger.info("on_demand_scan_completed", company_id=cid, signals=upserted)

    return TriggerScanResponse(
        status="completed",
        company_id=cid,
        signals_upserted=upserted,
    )
