"""
Outcome Tracking API Endpoints.

POST /api/v1/outcomes/record               — record an actual outcome
GET  /api/v1/outcomes                      — list recorded outcomes
GET  /api/v1/outcomes/accuracy             — accuracy report (Brier, F1, ECE)
GET  /api/v1/outcomes/roi                  — ROI report
GET  /api/v1/outcomes/flywheel             — flywheel learning status
GET  /api/v1/outcomes/flywheel/priors      — updated Bayesian priors
GET  /api/v1/outcomes/{decision_id}        — get outcome for a decision
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from riskcast.api.deps import get_company_id, get_db, get_user_id
from riskcast.outcomes.accuracy import AccuracyCalculator
from riskcast.outcomes.flywheel import FlywheelEngine
from riskcast.outcomes.recorder import OutcomeRecorder
from riskcast.outcomes.roi import ROICalculator
from riskcast.outcomes.schemas import (
    AccuracyReport,
    OutcomeRecord,
    OutcomeRecordRequest,
    ROIReport,
)

router = APIRouter(prefix="/api/v1/outcomes", tags=["outcomes"])

_recorder = OutcomeRecorder()
_accuracy = AccuracyCalculator()
_roi = ROICalculator()
_flywheel = FlywheelEngine()


class RecordOutcomeBody(BaseModel):
    """Full request body for recording an outcome."""
    outcome: OutcomeRecordRequest
    # Decision snapshot (normally would come from DB lookup)
    predicted_risk_score: float
    predicted_confidence: float
    predicted_loss_usd: float
    predicted_action: str
    entity_type: str
    entity_id: str


class OutcomeListResponse(BaseModel):
    outcomes: list[OutcomeRecord]
    total: int


@router.post("/record", response_model=OutcomeRecord)
async def record_outcome(
    body: RecordOutcomeBody,
    db: AsyncSession = Depends(get_db),
    company_id: uuid.UUID = Depends(get_company_id),
    user_id: uuid.UUID = Depends(get_user_id),
):
    """
    Record an actual outcome for a decision.

    This is the critical feedback loop — every recorded outcome
    improves future predictions via the flywheel.
    """
    result = await _recorder.record_outcome(
        session=db,
        company_id=str(company_id),
        request=body.outcome,
        predicted_risk_score=body.predicted_risk_score,
        predicted_confidence=body.predicted_confidence,
        predicted_loss_usd=body.predicted_loss_usd,
        predicted_action=body.predicted_action,
        entity_type=body.entity_type,
        entity_id=body.entity_id,
        recorded_by=str(user_id),
    )
    await db.commit()
    return result


@router.get("", response_model=OutcomeListResponse)
async def list_outcomes(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    company_id: uuid.UUID = Depends(get_company_id),
):
    """List all recorded outcomes for the company."""
    outcomes = await _recorder.get_outcomes(db, str(company_id), limit, offset)
    return OutcomeListResponse(outcomes=outcomes, total=len(outcomes))


@router.get("/accuracy", response_model=AccuracyReport)
async def accuracy_report(
    period: str = Query(default="last_30_days"),
    days_back: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    company_id: uuid.UUID = Depends(get_company_id),
):
    """
    Get prediction accuracy report.

    Includes Brier score, MAE, calibration drift, precision, recall, F1.
    """
    return await _accuracy.generate_report(
        db, str(company_id), period, days_back
    )


@router.get("/roi", response_model=ROIReport)
async def roi_report(
    period: str = Query(default="last_30_days"),
    days_back: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    company_id: uuid.UUID = Depends(get_company_id),
):
    """
    Get ROI report.

    Shows total value generated, loss avoided, action costs, and ROI ratio.
    """
    return await _roi.generate_report(
        db, str(company_id), period, days_back
    )


@router.get("/flywheel")
async def flywheel_status(
    db: AsyncSession = Depends(get_db),
    company_id: uuid.UUID = Depends(get_company_id),
):
    """
    Get flywheel learning status.

    Shows:
    - Total outcomes and learning progress
    - Accuracy improvement trend
    - Entities needing recalibration
    - Updated priors per entity type
    """
    return await _flywheel.get_learning_summary(db, str(company_id))


@router.get("/flywheel/priors")
async def flywheel_priors(
    entity_type: str = Query(default="order"),
    days_back: int = Query(default=90, ge=7, le=365),
    db: AsyncSession = Depends(get_db),
    company_id: uuid.UUID = Depends(get_company_id),
):
    """
    Get updated Bayesian priors for a specific entity type.

    The flywheel computes these from outcome history:
    if the model is over- or under-predicting, priors shift to compensate.
    """
    state = await _flywheel.compute_updated_priors(
        db, str(company_id), entity_type, days_back=days_back
    )
    return state.to_dict()


@router.get("/{decision_id}", response_model=OutcomeRecord)
async def get_outcome_for_decision(
    decision_id: str,
    db: AsyncSession = Depends(get_db),
    company_id: uuid.UUID = Depends(get_company_id),
):
    """Get the recorded outcome for a specific decision."""
    outcome = await _recorder.get_outcome_by_decision(
        db, str(company_id), decision_id
    )
    if outcome is None:
        raise HTTPException(
            status_code=404,
            detail=f"No outcome recorded for decision '{decision_id}'."
        )
    return outcome
