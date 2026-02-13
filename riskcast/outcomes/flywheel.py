"""
Flywheel Learning Loop — Feed outcomes back to improve models.

The flywheel:
1. Collects outcomes (predictions vs actuals)
2. Recomputes Bayesian priors per entity based on historical accuracy
3. Detects calibration drift and flags when recalibration is needed
4. Generates "learning signals" — synthetic priors that improve future predictions

This is the core of RiskCast's irreplaceability:
the more you use it, the better it gets.
"""

import math
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

import structlog
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from riskcast.db.models import Outcome
from riskcast.engine.bayesian import BayesianRiskEngine, BetaPosterior

logger = structlog.get_logger(__name__)

# Flywheel configuration
MIN_OUTCOMES_FOR_LEARNING: int = 5      # Need ≥5 outcomes to start learning
DRIFT_THRESHOLD: float = 0.15           # Trigger recalibration if drift > 15%
LEARNING_RATE: float = 0.3              # How much new data shifts the prior (0-1)
MAX_PRIOR_SHIFT: float = 5.0            # Max shift per update to prevent instability


class FlywheelState:
    """State of the flywheel for a specific entity or entity type."""

    def __init__(
        self,
        entity_key: str,
        n_outcomes: int,
        n_materialized: int,
        n_not_materialized: int,
        avg_prediction_error: float,
        calibration_drift: float,
        updated_alpha: float,
        updated_beta: float,
        prior_alpha: float,
        prior_beta: float,
        needs_recalibration: bool,
        last_updated: str,
    ):
        self.entity_key = entity_key
        self.n_outcomes = n_outcomes
        self.n_materialized = n_materialized
        self.n_not_materialized = n_not_materialized
        self.avg_prediction_error = avg_prediction_error
        self.calibration_drift = calibration_drift
        self.updated_alpha = updated_alpha
        self.updated_beta = updated_beta
        self.prior_alpha = prior_alpha
        self.prior_beta = prior_beta
        self.needs_recalibration = needs_recalibration
        self.last_updated = last_updated

    def to_dict(self) -> dict:
        """Serialize to dict for API response / audit trail."""
        return {
            "entity_key": self.entity_key,
            "n_outcomes": self.n_outcomes,
            "n_materialized": self.n_materialized,
            "n_not_materialized": self.n_not_materialized,
            "avg_prediction_error": round(self.avg_prediction_error, 4),
            "calibration_drift": round(self.calibration_drift, 4),
            "updated_prior": {
                "alpha": round(self.updated_alpha, 4),
                "beta": round(self.updated_beta, 4),
            },
            "original_prior": {
                "alpha": round(self.prior_alpha, 4),
                "beta": round(self.prior_beta, 4),
            },
            "needs_recalibration": self.needs_recalibration,
            "last_updated": self.last_updated,
        }


class FlywheelEngine:
    """
    The learning flywheel — continuously improves predictions from outcomes.

    Pipeline:
    1. Aggregate outcomes by entity type
    2. Compute observed risk rates (actual frequency)
    3. Update Bayesian priors using outcome data
    4. Detect calibration drift
    5. Return updated priors for the risk engine

    The flywheel is conservative: it shifts slowly (LEARNING_RATE)
    and caps maximum shift (MAX_PRIOR_SHIFT) to prevent instability.
    """

    def __init__(
        self,
        learning_rate: float = LEARNING_RATE,
        max_shift: float = MAX_PRIOR_SHIFT,
        drift_threshold: float = DRIFT_THRESHOLD,
        min_outcomes: int = MIN_OUTCOMES_FOR_LEARNING,
    ):
        self.learning_rate = learning_rate
        self.max_shift = max_shift
        self.drift_threshold = drift_threshold
        self.min_outcomes = min_outcomes
        self.bayesian = BayesianRiskEngine()

    async def compute_updated_priors(
        self,
        session: AsyncSession,
        company_id: str,
        entity_type: str,
        default_alpha: float = 2.0,
        default_beta: float = 5.0,
        days_back: int = 90,
    ) -> FlywheelState:
        """
        Compute updated Bayesian priors based on outcome history.

        Args:
            session: Database session
            company_id: Tenant company ID
            entity_type: Entity type to compute priors for
            default_alpha: Default prior alpha (pseudo-successes)
            default_beta: Default prior beta (pseudo-failures)
            days_back: Historical window in days

        Returns:
            FlywheelState with updated priors and diagnostics
        """
        now = datetime.utcnow()
        entity_key = f"{company_id}/{entity_type}"

        # ── 1. Fetch outcome history ──────────────────────────────────
        outcomes = await self._fetch_outcomes(session, company_id, entity_type, days_back)
        n_outcomes = len(outcomes)

        if n_outcomes < self.min_outcomes:
            return FlywheelState(
                entity_key=entity_key,
                n_outcomes=n_outcomes,
                n_materialized=0,
                n_not_materialized=0,
                avg_prediction_error=0.0,
                calibration_drift=0.0,
                updated_alpha=default_alpha,
                updated_beta=default_beta,
                prior_alpha=default_alpha,
                prior_beta=default_beta,
                needs_recalibration=False,
                last_updated=now.isoformat(),
            )

        # ── 2. Compute observed rates ──────────────────────────────────
        n_materialized = sum(1 for o in outcomes if o.risk_materialized)
        n_not_materialized = n_outcomes - n_materialized

        # ── 3. Bayesian prior update ──────────────────────────────────
        # Use observed rates to shift priors, weighted by learning rate
        observed_rate = n_materialized / n_outcomes
        prior_rate = default_alpha / (default_alpha + default_beta)

        # How much to shift
        shift_magnitude = (observed_rate - prior_rate) * self.learning_rate * n_outcomes
        shift_magnitude = max(-self.max_shift, min(self.max_shift, shift_magnitude))

        # Apply shift to alpha (risk rate), keeping alpha + beta roughly constant
        updated_alpha = max(0.5, default_alpha + shift_magnitude)
        updated_beta = max(0.5, default_beta - shift_magnitude * 0.5)

        # ── 4. Calibration drift ──────────────────────────────────────
        avg_predicted_rate = sum(
            float(o.predicted_risk_score) / 100.0 for o in outcomes
        ) / n_outcomes
        calibration_drift = abs(avg_predicted_rate - observed_rate)

        # ── 5. Average prediction error ───────────────────────────────
        avg_prediction_error = sum(
            float(o.prediction_error) for o in outcomes
        ) / n_outcomes

        needs_recalibration = calibration_drift > self.drift_threshold

        state = FlywheelState(
            entity_key=entity_key,
            n_outcomes=n_outcomes,
            n_materialized=n_materialized,
            n_not_materialized=n_not_materialized,
            avg_prediction_error=avg_prediction_error,
            calibration_drift=calibration_drift,
            updated_alpha=updated_alpha,
            updated_beta=updated_beta,
            prior_alpha=default_alpha,
            prior_beta=default_beta,
            needs_recalibration=needs_recalibration,
            last_updated=now.isoformat(),
        )

        logger.info(
            "flywheel_priors_updated",
            entity_key=entity_key,
            n_outcomes=n_outcomes,
            observed_rate=round(observed_rate, 4),
            prior_rate=round(prior_rate, 4),
            drift=round(calibration_drift, 4),
            needs_recalibration=needs_recalibration,
            updated_alpha=round(updated_alpha, 4),
            updated_beta=round(updated_beta, 4),
        )

        return state

    async def compute_all_priors(
        self,
        session: AsyncSession,
        company_id: str,
        days_back: int = 90,
    ) -> list[FlywheelState]:
        """Compute updated priors for all entity types with outcomes."""
        # Get distinct entity types with outcomes
        result = await session.execute(
            select(Outcome.entity_type)
            .where(Outcome.company_id == company_id)
            .group_by(Outcome.entity_type)
        )
        entity_types = [row[0] for row in result.all()]

        states: list[FlywheelState] = []
        for et in entity_types:
            state = await self.compute_updated_priors(
                session, company_id, et, days_back=days_back
            )
            states.append(state)

        return states

    async def get_learning_summary(
        self,
        session: AsyncSession,
        company_id: str,
    ) -> dict:
        """
        Get a summary of the flywheel's learning progress.

        Returns total outcomes, accuracy trends, and recalibration status.
        """
        # Total outcomes
        result = await session.execute(
            select(func.count(Outcome.id)).where(
                Outcome.company_id == company_id,
            )
        )
        total_outcomes = result.scalar_one() or 0

        # Accuracy over time: last 7 days vs previous 7 days
        now = datetime.utcnow()
        recent_cutoff = now - timedelta(days=7)
        older_cutoff = now - timedelta(days=14)

        recent_result = await session.execute(
            select(
                func.avg(Outcome.prediction_error),
                func.count(Outcome.id),
            ).where(
                Outcome.company_id == company_id,
                Outcome.recorded_at >= recent_cutoff,
            )
        )
        recent_row = recent_result.one()
        recent_error = float(recent_row[0]) if recent_row[0] else 0.0
        recent_count = recent_row[1] or 0

        older_result = await session.execute(
            select(
                func.avg(Outcome.prediction_error),
                func.count(Outcome.id),
            ).where(
                Outcome.company_id == company_id,
                Outcome.recorded_at >= older_cutoff,
                Outcome.recorded_at < recent_cutoff,
            )
        )
        older_row = older_result.one()
        older_error = float(older_row[0]) if older_row[0] else 0.0
        older_count = older_row[1] or 0

        # Improvement trend
        if older_error > 0 and recent_error > 0:
            improvement = (older_error - recent_error) / older_error
        else:
            improvement = 0.0

        # All entity states
        states = await self.compute_all_priors(session, company_id)
        needs_recalibration = [s for s in states if s.needs_recalibration]

        return {
            "total_outcomes": total_outcomes,
            "recent_outcomes": recent_count,
            "previous_period_outcomes": older_count,
            "recent_avg_error": round(recent_error, 4),
            "previous_avg_error": round(older_error, 4),
            "improvement_rate": round(improvement, 4),
            "improving": improvement > 0,
            "entity_states": [s.to_dict() for s in states],
            "entities_needing_recalibration": len(needs_recalibration),
            "flywheel_status": (
                "learning" if total_outcomes >= self.min_outcomes
                else "collecting_data"
            ),
        }

    async def _fetch_outcomes(
        self,
        session: AsyncSession,
        company_id: str,
        entity_type: str,
        days_back: int,
    ) -> list[Outcome]:
        """Fetch outcomes for a specific entity type within the lookback window."""
        cutoff = datetime.utcnow() - timedelta(days=days_back)
        result = await session.execute(
            select(Outcome).where(
                Outcome.company_id == company_id,
                Outcome.entity_type == entity_type,
                Outcome.recorded_at >= cutoff,
            )
        )
        return list(result.scalars().all())
