"""
Outcome Recorder — Record what ACTUALLY happened after a decision.

Records actual outcomes, computes prediction error, and stores
immutable outcome records for calibration and ROI tracking.
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from riskcast.db.models import Outcome
from riskcast.outcomes.schemas import OutcomeRecord, OutcomeRecordRequest, OutcomeType

logger = structlog.get_logger(__name__)

# Prediction accuracy threshold (predictions within 15% of actual are "accurate")
ACCURACY_THRESHOLD: float = 0.15


class OutcomeRecorder:
    """
    Records actual outcomes for decisions.

    Computes prediction error, accuracy, and value generated.
    All records are immutable once written.
    """

    def __init__(self, accuracy_threshold: float = ACCURACY_THRESHOLD):
        self.accuracy_threshold = accuracy_threshold

    async def record_outcome(
        self,
        session: AsyncSession,
        company_id: str,
        request: OutcomeRecordRequest,
        predicted_risk_score: float,
        predicted_confidence: float,
        predicted_loss_usd: float,
        predicted_action: str,
        entity_type: str,
        entity_id: str,
        recorded_by: Optional[str] = None,
    ) -> OutcomeRecord:
        """
        Record an actual outcome for a decision.

        Args:
            session: Database session
            company_id: Tenant company ID
            request: Outcome details from the user
            predicted_risk_score: Original predicted risk score (0-100)
            predicted_confidence: Original confidence (0-1)
            predicted_loss_usd: Original predicted loss
            predicted_action: Recommended action type
            entity_type: Entity type (order, customer, route)
            entity_id: Entity identifier
            recorded_by: User who recorded the outcome

        Returns:
            OutcomeRecord with computed accuracy metrics
        """
        outcome_id = f"out_{uuid.uuid4().hex[:16]}"
        now = datetime.utcnow()

        # ── Compute accuracy metrics ──────────────────────────────────
        risk_materialized = request.outcome_type in (
            OutcomeType.LOSS_OCCURRED,
            OutcomeType.DELAY_OCCURRED,
            OutcomeType.PARTIAL_IMPACT,
        )

        prediction_error = self._compute_prediction_error(
            predicted_risk_score=predicted_risk_score,
            risk_materialized=risk_materialized,
            predicted_loss_usd=predicted_loss_usd,
            actual_loss_usd=request.actual_loss_usd,
        )

        was_accurate = prediction_error <= self.accuracy_threshold

        # Value generated: loss avoided minus action cost
        value_generated = self._compute_value_generated(
            predicted_loss_usd=predicted_loss_usd,
            actual_loss_usd=request.actual_loss_usd,
            action_followed=request.action_followed_recommendation,
            risk_materialized=risk_materialized,
        )

        # ── Persist to database ───────────────────────────────────────
        outcome_model = Outcome(
            id=uuid.uuid4(),
            decision_id=request.decision_id,
            company_id=company_id,
            entity_type=entity_type,
            entity_id=entity_id,
            predicted_risk_score=Decimal(str(round(predicted_risk_score, 2))),
            predicted_confidence=Decimal(str(round(predicted_confidence, 4))),
            predicted_loss_usd=Decimal(str(round(predicted_loss_usd, 2))),
            predicted_action=predicted_action,
            outcome_type=request.outcome_type.value,
            actual_loss_usd=Decimal(str(round(request.actual_loss_usd, 2))),
            actual_delay_days=Decimal(str(round(request.actual_delay_days, 2))),
            action_taken=request.action_taken,
            action_followed_recommendation=request.action_followed_recommendation,
            risk_materialized=risk_materialized,
            prediction_error=Decimal(str(round(prediction_error, 4))),
            was_accurate=was_accurate,
            value_generated_usd=Decimal(str(round(value_generated, 2))),
            recorded_at=now,
            recorded_by=recorded_by,
            notes=request.notes,
        )
        session.add(outcome_model)
        await session.flush()

        logger.info(
            "outcome_recorded",
            outcome_id=outcome_id,
            decision_id=request.decision_id,
            outcome_type=request.outcome_type.value,
            risk_materialized=risk_materialized,
            prediction_error=round(prediction_error, 4),
            was_accurate=was_accurate,
            value_generated=round(value_generated, 2),
        )

        return OutcomeRecord(
            outcome_id=outcome_id,
            decision_id=request.decision_id,
            company_id=company_id,
            entity_type=entity_type,
            entity_id=entity_id,
            predicted_risk_score=predicted_risk_score,
            predicted_confidence=predicted_confidence,
            predicted_loss_usd=predicted_loss_usd,
            predicted_action=predicted_action,
            outcome_type=request.outcome_type,
            actual_loss_usd=request.actual_loss_usd,
            actual_delay_days=request.actual_delay_days,
            action_taken=request.action_taken,
            action_followed_recommendation=request.action_followed_recommendation,
            risk_materialized=risk_materialized,
            prediction_error=round(prediction_error, 4),
            was_accurate=was_accurate,
            value_generated_usd=round(value_generated, 2),
            recorded_at=now.isoformat(),
            recorded_by=recorded_by,
            notes=request.notes,
        )

    async def get_outcomes(
        self,
        session: AsyncSession,
        company_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> list[OutcomeRecord]:
        """Get recorded outcomes for a company."""
        result = await session.execute(
            select(Outcome)
            .where(Outcome.company_id == company_id)
            .order_by(Outcome.recorded_at.desc())
            .limit(limit)
            .offset(offset)
        )
        rows = result.scalars().all()
        return [self._model_to_record(row) for row in rows]

    async def get_outcome_by_decision(
        self,
        session: AsyncSession,
        company_id: str,
        decision_id: str,
    ) -> Optional[OutcomeRecord]:
        """Get outcome for a specific decision."""
        result = await session.execute(
            select(Outcome).where(
                Outcome.company_id == company_id,
                Outcome.decision_id == decision_id,
            )
        )
        row = result.scalar_one_or_none()
        return self._model_to_record(row) if row else None

    def _compute_prediction_error(
        self,
        predicted_risk_score: float,
        risk_materialized: bool,
        predicted_loss_usd: float,
        actual_loss_usd: float,
    ) -> float:
        """
        Compute prediction error as normalized absolute error.

        Combines:
        1. Risk direction error (did we predict the right direction?)
        2. Loss magnitude error (how far off was our loss estimate?)
        """
        # Binary direction error (0 or 1)
        predicted_risk_binary = 1.0 if predicted_risk_score >= 50.0 else 0.0
        actual_risk_binary = 1.0 if risk_materialized else 0.0
        direction_error = abs(predicted_risk_binary - actual_risk_binary)

        # Magnitude error (normalized)
        max_loss = max(predicted_loss_usd, actual_loss_usd, 1.0)
        magnitude_error = abs(predicted_loss_usd - actual_loss_usd) / max_loss

        # Weighted combination: 60% direction, 40% magnitude
        return 0.6 * direction_error + 0.4 * magnitude_error

    def _compute_value_generated(
        self,
        predicted_loss_usd: float,
        actual_loss_usd: float,
        action_followed: bool,
        risk_materialized: bool,
    ) -> float:
        """
        Compute value generated by the decision.

        Value = loss_avoided when action was followed.
        If action was NOT followed and loss occurred, value is negative (opportunity cost).
        """
        if action_followed:
            if risk_materialized:
                # Action taken but risk still materialized — value is reduced loss
                return max(predicted_loss_usd - actual_loss_usd, 0.0)
            else:
                # Action taken and risk didn't materialize — full value
                return predicted_loss_usd
        else:
            if risk_materialized:
                # Action not taken and risk materialized — negative value (missed opportunity)
                return -actual_loss_usd
            else:
                # Action not taken and nothing happened — no value either way
                return 0.0

    def _model_to_record(self, model: Outcome) -> OutcomeRecord:
        """Convert ORM model to Pydantic schema."""
        return OutcomeRecord(
            outcome_id=f"out_{str(model.id)[:16]}",
            decision_id=model.decision_id,
            company_id=str(model.company_id),
            entity_type=model.entity_type,
            entity_id=model.entity_id,
            predicted_risk_score=float(model.predicted_risk_score),
            predicted_confidence=float(model.predicted_confidence),
            predicted_loss_usd=float(model.predicted_loss_usd),
            predicted_action=model.predicted_action,
            outcome_type=OutcomeType(model.outcome_type),
            actual_loss_usd=float(model.actual_loss_usd),
            actual_delay_days=float(model.actual_delay_days),
            action_taken=model.action_taken,
            action_followed_recommendation=model.action_followed_recommendation,
            risk_materialized=model.risk_materialized,
            prediction_error=float(model.prediction_error),
            was_accurate=model.was_accurate,
            value_generated_usd=float(model.value_generated_usd),
            recorded_at=model.recorded_at.isoformat() if model.recorded_at else "",
            recorded_by=model.recorded_by,
            notes=model.notes,
        )
