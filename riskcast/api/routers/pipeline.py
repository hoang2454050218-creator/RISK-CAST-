"""
Pipeline Integrity API Endpoints.

POST /api/v1/pipeline/validate            — validate a signal before/after ingest
GET  /api/v1/pipeline/health              — pipeline health snapshot
GET  /api/v1/pipeline/integrity           — integrity check (ledger vs DB)
GET  /api/v1/pipeline/integrity/replay    — find signals needing replay
GET  /api/v1/pipeline/trace/{signal_id}   — trace a signal through the pipeline
GET  /api/v1/pipeline/trace/decision/{id} — trace a decision to source signals
GET  /api/v1/pipeline/coverage            — pipeline traceability coverage
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from riskcast.api.deps import get_company_id, get_db
from riskcast.pipeline.health import PipelineHealthMonitor
from riskcast.pipeline.integrity import IntegrityChecker
from riskcast.pipeline.traceability import TraceabilityEngine
from riskcast.pipeline.validator import SignalValidator
from riskcast.schemas.omen_signal import SignalEvent

router = APIRouter(prefix="/api/v1/pipeline", tags=["pipeline"])

_validator = SignalValidator()
_health = PipelineHealthMonitor()
_integrity = IntegrityChecker()
_traceability = TraceabilityEngine()


# ── Validate ───────────────────────────────────────────────────────────


@router.post("/validate")
async def validate_signal(event: SignalEvent):
    """
    Validate a signal without ingesting it.

    Returns validation result with quality score and issues.
    Useful for pre-flight checks before sending to /ingest.
    """
    result = _validator.validate(event)
    return result.to_dict()


# ── Health ─────────────────────────────────────────────────────────────


@router.get("/health")
async def pipeline_health(
    db: AsyncSession = Depends(get_db),
):
    """
    Get pipeline health snapshot.

    Checks signal freshness, ingest lag, volume, gaps, and error rates.
    """
    health = await _health.check_health(db)
    return health.to_dict()


# ── Integrity ──────────────────────────────────────────────────────────


@router.get("/integrity")
async def integrity_check(
    hours_back: int = Query(default=24, ge=1, le=168),
    db: AsyncSession = Depends(get_db),
):
    """
    Run integrity check: compare ledger against DB.

    Finds missing signals, orphaned records, and failed ingests.
    """
    report = await _integrity.check_integrity(db, hours_back)
    return report.to_dict()


@router.get("/integrity/replay")
async def signals_needing_replay(
    hours_back: int = Query(default=24, ge=1, le=168),
    db: AsyncSession = Depends(get_db),
):
    """
    Find signals that need to be replayed.

    These are signals in the ledger but not in the DB.
    """
    signal_ids = await _integrity.find_signals_needing_replay(db, hours_back)
    return {
        "signals_needing_replay": signal_ids,
        "count": len(signal_ids),
        "hours_checked": hours_back,
    }


# ── Traceability ──────────────────────────────────────────────────────


@router.get("/trace/{signal_id}")
async def trace_signal(
    signal_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Trace a signal through the entire pipeline.

    Shows: Ledger → Ingest → Processing status.
    """
    chain = await _traceability.trace_signal(db, signal_id)
    return chain.to_dict()


@router.get("/trace/decision/{decision_id}")
async def trace_decision(
    decision_id: str,
    db: AsyncSession = Depends(get_db),
    company_id: uuid.UUID = Depends(get_company_id),
):
    """
    Trace a decision back to its signals and forward to its outcome.
    """
    return await _traceability.trace_decision(db, decision_id, str(company_id))


@router.get("/coverage")
async def pipeline_coverage(
    hours_back: int = Query(default=24, ge=1, le=168),
    db: AsyncSession = Depends(get_db),
):
    """
    Get pipeline traceability coverage.

    Shows what % of signals have full trace chains.
    """
    return await _traceability.get_pipeline_coverage(db, hours_back)
