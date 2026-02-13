"""
Reconciliation API Endpoints.

POST  /reconcile/run            — trigger reconciliation
GET   /reconcile/status/{date}  — check status for a date
GET   /reconcile/history/{date} — full run history for a date

Reconcile compares the immutable Ledger against the ingest DB,
finds any missing signals, and replays them automatically.

ALL endpoints require X-API-Key authentication (enforced by TenantMiddleware).
"""

import uuid
from datetime import date

import structlog
from fastapi import APIRouter, Request

from riskcast.db.engine import get_db_session
from riskcast.schemas.omen_signal import (
    ReconcileHistoryResponse,
    ReconcileRequest,
    ReconcileResult,
    ReconcileStatusResponse,
)
from riskcast.services.reconcile import ReconcileService

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/reconcile", tags=["reconcile"])

_reconcile_service = ReconcileService()


@router.post(
    "/run",
    response_model=ReconcileResult,
    summary="Run reconciliation",
    description="Compare ledger vs DB, replay any missing signals. Requires API key auth.",
)
async def run_reconcile(body: ReconcileRequest):
    """Trigger a reconciliation run for the last N days."""
    async with get_db_session() as session:
        try:
            result = await _reconcile_service.run(session, body.since_days)
            return result
        except Exception:
            error_id = str(uuid.uuid4())
            logger.error("reconcile_endpoint_error", error_id=error_id, exc_info=True)
            from fastapi import HTTPException
            raise HTTPException(
                status_code=500,
                detail={"error": "Reconciliation failed", "error_id": error_id},
            )


@router.get(
    "/status/{target_date}",
    response_model=ReconcileStatusResponse,
    summary="Reconciliation status",
    description="Get the latest reconciliation status for a specific date.",
)
async def reconcile_status(target_date: date):
    """Get reconciliation status for a date (YYYY-MM-DD)."""
    async with get_db_session() as session:
        return await _reconcile_service.get_status(session, target_date)


@router.get(
    "/history/{target_date}",
    response_model=ReconcileHistoryResponse,
    summary="Reconciliation history",
    description="Get all reconciliation runs for a specific date.",
)
async def reconcile_history(target_date: date):
    """Get full reconciliation history for a date (YYYY-MM-DD)."""
    async with get_db_session() as session:
        return await _reconcile_service.get_history(session, target_date)
