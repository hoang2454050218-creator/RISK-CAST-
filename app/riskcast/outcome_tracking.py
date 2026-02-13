"""
Outcome Tracking Module.

Production-grade outcome tracking with:
- Decision outcome recording
- Prediction accuracy measurement
- Confidence calibration
- Self-improvement data collection
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from enum import Enum

from sqlalchemy import select, update, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
import structlog

from app.core.metrics import METRICS, RECORDER
from app.db.models import Base
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, JSON, Float, Text, ForeignKey
)
from sqlalchemy.orm import Mapped, mapped_column

logger = structlog.get_logger(__name__)


# ============================================================================
# ENUMS
# ============================================================================


class OutcomeStatus(str, Enum):
    """Status of decision outcome."""
    
    PENDING = "pending"  # Waiting for outcome
    ACTED_UPON = "acted_upon"  # Customer took recommended action
    DIFFERENT_ACTION = "different_action"  # Customer took different action
    NO_ACTION = "no_action"  # Customer did nothing
    UNKNOWN = "unknown"  # Couldn't determine outcome


class PredictionResult(str, Enum):
    """Result of prediction accuracy."""
    
    ACCURATE = "accurate"  # Prediction was correct
    INACCURATE = "inaccurate"  # Prediction was wrong
    PARTIALLY_ACCURATE = "partially_accurate"  # Partially correct
    INCONCLUSIVE = "inconclusive"  # Couldn't determine


# ============================================================================
# DATABASE MODEL
# ============================================================================


class DecisionOutcomeModel(Base):
    """SQLAlchemy model for decision outcomes."""
    
    __tablename__ = "decision_outcomes"
    __table_args__ = {"extend_existing": True}
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    decision_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    customer_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    
    # Original prediction
    predicted_severity: Mapped[str] = mapped_column(String(20), nullable=False)
    predicted_impact_usd: Mapped[float] = mapped_column(Float, nullable=False)
    predicted_delay_days: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    recommended_action: Mapped[str] = mapped_column(String(50), nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    
    # Actual outcome
    outcome_status: Mapped[str] = mapped_column(
        String(20), 
        nullable=False, 
        default=OutcomeStatus.PENDING.value
    )
    actual_action_taken: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    actual_impact_usd: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    actual_delay_days: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Accuracy assessment
    prediction_result: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    impact_accuracy_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    delay_accuracy_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Metadata
    feedback_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, 
        nullable=False, 
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )


# ============================================================================
# DOMAIN MODELS
# ============================================================================


class RecordOutcomeRequest(BaseModel):
    """Request to record a decision outcome."""
    
    decision_id: str
    actual_action_taken: Optional[str] = None
    actual_impact_usd: Optional[float] = None
    actual_delay_days: Optional[float] = None
    feedback_notes: Optional[str] = None
    metadata: dict = Field(default_factory=dict)


class OutcomeRecord(BaseModel):
    """Full outcome record."""
    
    decision_id: str
    customer_id: str
    
    # Prediction
    predicted_severity: str
    predicted_impact_usd: float
    predicted_delay_days: Optional[float]
    recommended_action: str
    confidence_score: float
    
    # Outcome
    outcome_status: OutcomeStatus
    actual_action_taken: Optional[str]
    actual_impact_usd: Optional[float]
    actual_delay_days: Optional[float]
    
    # Accuracy
    prediction_result: Optional[PredictionResult]
    impact_accuracy_pct: Optional[float]
    delay_accuracy_pct: Optional[float]
    
    # Metadata
    feedback_notes: Optional[str]
    created_at: datetime
    resolved_at: Optional[datetime]


class AccuracyMetrics(BaseModel):
    """Aggregated accuracy metrics."""
    
    total_decisions: int
    resolved_decisions: int
    
    # Action accuracy
    action_followed_rate: float
    
    # Impact accuracy
    mean_impact_accuracy_pct: Optional[float]
    median_impact_accuracy_pct: Optional[float]
    
    # Delay accuracy
    mean_delay_accuracy_pct: Optional[float]
    
    # Prediction accuracy
    accurate_predictions: int
    inaccurate_predictions: int
    accuracy_rate: float
    
    # Confidence calibration
    calibration_by_bucket: Dict[str, float]
    
    # Time window
    window_start: datetime
    window_end: datetime


# ============================================================================
# OUTCOME TRACKER
# ============================================================================


class OutcomeTracker:
    """
    Tracks decision outcomes for accuracy measurement and model improvement.
    
    This is the key to the self-improving system mentioned in the audit.
    """
    
    def __init__(self, session: AsyncSession):
        self._session = session
    
    async def record_decision(
        self,
        decision_id: str,
        customer_id: str,
        predicted_severity: str,
        predicted_impact_usd: float,
        recommended_action: str,
        confidence_score: float,
        predicted_delay_days: Optional[float] = None,
        metadata: Optional[dict] = None,
    ) -> None:
        """Record a new decision for outcome tracking."""
        outcome = DecisionOutcomeModel(
            decision_id=decision_id,
            customer_id=customer_id,
            predicted_severity=predicted_severity,
            predicted_impact_usd=predicted_impact_usd,
            predicted_delay_days=predicted_delay_days,
            recommended_action=recommended_action,
            confidence_score=confidence_score,
            outcome_status=OutcomeStatus.PENDING.value,
            metadata_json=metadata or {},
        )
        
        self._session.add(outcome)
        await self._session.flush()
        
        logger.info(
            "decision_recorded_for_tracking",
            decision_id=decision_id,
            customer_id=customer_id,
            confidence=confidence_score,
        )
    
    async def record_outcome(
        self,
        request: RecordOutcomeRequest,
    ) -> OutcomeRecord:
        """Record the actual outcome of a decision."""
        # Get the decision outcome record
        result = await self._session.execute(
            select(DecisionOutcomeModel)
            .where(DecisionOutcomeModel.decision_id == request.decision_id)
        )
        outcome = result.scalar_one_or_none()
        
        if not outcome:
            raise ValueError(f"Decision {request.decision_id} not found")
        
        # Determine outcome status
        if request.actual_action_taken:
            if request.actual_action_taken == outcome.recommended_action:
                status = OutcomeStatus.ACTED_UPON
            else:
                status = OutcomeStatus.DIFFERENT_ACTION
        else:
            status = OutcomeStatus.NO_ACTION
        
        # Calculate accuracy metrics
        impact_accuracy = None
        if request.actual_impact_usd is not None and outcome.predicted_impact_usd > 0:
            impact_accuracy = 1 - abs(
                request.actual_impact_usd - outcome.predicted_impact_usd
            ) / outcome.predicted_impact_usd
            impact_accuracy = max(0, min(1, impact_accuracy)) * 100
        
        delay_accuracy = None
        if (
            request.actual_delay_days is not None 
            and outcome.predicted_delay_days 
            and outcome.predicted_delay_days > 0
        ):
            delay_accuracy = 1 - abs(
                request.actual_delay_days - outcome.predicted_delay_days
            ) / outcome.predicted_delay_days
            delay_accuracy = max(0, min(1, delay_accuracy)) * 100
        
        # Determine prediction result
        prediction_result = self._assess_prediction(
            outcome, request, impact_accuracy, delay_accuracy
        )
        
        # Update the record
        outcome.outcome_status = status.value
        outcome.actual_action_taken = request.actual_action_taken
        outcome.actual_impact_usd = request.actual_impact_usd
        outcome.actual_delay_days = request.actual_delay_days
        outcome.prediction_result = prediction_result.value if prediction_result else None
        outcome.impact_accuracy_pct = impact_accuracy
        outcome.delay_accuracy_pct = delay_accuracy
        outcome.feedback_notes = request.feedback_notes
        outcome.resolved_at = datetime.utcnow()
        
        if request.metadata:
            outcome.metadata_json.update(request.metadata)
        
        await self._session.flush()
        
        # Update metrics
        METRICS.decisions_acted_upon.labels(
            recommended_action=outcome.recommended_action,
            actual_action=request.actual_action_taken or "none",
        ).inc()
        
        if prediction_result == PredictionResult.ACCURATE:
            RECORDER.update_prediction_accuracy(
                metric_type="decision",
                accuracy=1.0,
                window="rolling",
            )
        
        logger.info(
            "outcome_recorded",
            decision_id=request.decision_id,
            status=status.value,
            prediction_result=prediction_result.value if prediction_result else None,
            impact_accuracy=impact_accuracy,
        )
        
        return self._model_to_record(outcome)
    
    def _assess_prediction(
        self,
        outcome: DecisionOutcomeModel,
        request: RecordOutcomeRequest,
        impact_accuracy: Optional[float],
        delay_accuracy: Optional[float],
    ) -> Optional[PredictionResult]:
        """Assess the accuracy of the prediction."""
        if request.actual_impact_usd is None:
            return PredictionResult.INCONCLUSIVE
        
        accuracies = []
        if impact_accuracy is not None:
            accuracies.append(impact_accuracy)
        if delay_accuracy is not None:
            accuracies.append(delay_accuracy)
        
        if not accuracies:
            return PredictionResult.INCONCLUSIVE
        
        avg_accuracy = sum(accuracies) / len(accuracies)
        
        if avg_accuracy >= 80:
            return PredictionResult.ACCURATE
        elif avg_accuracy >= 50:
            return PredictionResult.PARTIALLY_ACCURATE
        else:
            return PredictionResult.INACCURATE
    
    def _model_to_record(self, model: DecisionOutcomeModel) -> OutcomeRecord:
        """Convert database model to domain record."""
        return OutcomeRecord(
            decision_id=model.decision_id,
            customer_id=model.customer_id,
            predicted_severity=model.predicted_severity,
            predicted_impact_usd=model.predicted_impact_usd,
            predicted_delay_days=model.predicted_delay_days,
            recommended_action=model.recommended_action,
            confidence_score=model.confidence_score,
            outcome_status=OutcomeStatus(model.outcome_status),
            actual_action_taken=model.actual_action_taken,
            actual_impact_usd=model.actual_impact_usd,
            actual_delay_days=model.actual_delay_days,
            prediction_result=PredictionResult(model.prediction_result) if model.prediction_result else None,
            impact_accuracy_pct=model.impact_accuracy_pct,
            delay_accuracy_pct=model.delay_accuracy_pct,
            feedback_notes=model.feedback_notes,
            created_at=model.created_at,
            resolved_at=model.resolved_at,
        )
    
    async def get_accuracy_metrics(
        self,
        customer_id: Optional[str] = None,
        window_days: int = 30,
    ) -> AccuracyMetrics:
        """Get aggregated accuracy metrics."""
        window_start = datetime.utcnow() - timedelta(days=window_days)
        window_end = datetime.utcnow()
        
        # Base query
        base_filter = DecisionOutcomeModel.created_at >= window_start
        if customer_id:
            base_filter = and_(base_filter, DecisionOutcomeModel.customer_id == customer_id)
        
        # Total decisions
        total_result = await self._session.execute(
            select(func.count(DecisionOutcomeModel.id))
            .where(base_filter)
        )
        total_decisions = total_result.scalar() or 0
        
        # Resolved decisions
        resolved_filter = and_(
            base_filter,
            DecisionOutcomeModel.outcome_status != OutcomeStatus.PENDING.value
        )
        resolved_result = await self._session.execute(
            select(func.count(DecisionOutcomeModel.id))
            .where(resolved_filter)
        )
        resolved_decisions = resolved_result.scalar() or 0
        
        # Action followed rate
        acted_filter = and_(
            base_filter,
            DecisionOutcomeModel.outcome_status == OutcomeStatus.ACTED_UPON.value
        )
        acted_result = await self._session.execute(
            select(func.count(DecisionOutcomeModel.id))
            .where(acted_filter)
        )
        acted_count = acted_result.scalar() or 0
        action_followed_rate = (acted_count / resolved_decisions * 100) if resolved_decisions > 0 else 0.0
        
        # Impact accuracy
        impact_result = await self._session.execute(
            select(
                func.avg(DecisionOutcomeModel.impact_accuracy_pct),
            )
            .where(and_(
                base_filter,
                DecisionOutcomeModel.impact_accuracy_pct.isnot(None)
            ))
        )
        mean_impact = impact_result.scalar()
        
        # Delay accuracy
        delay_result = await self._session.execute(
            select(func.avg(DecisionOutcomeModel.delay_accuracy_pct))
            .where(and_(
                base_filter,
                DecisionOutcomeModel.delay_accuracy_pct.isnot(None)
            ))
        )
        mean_delay = delay_result.scalar()
        
        # Prediction accuracy counts
        accurate_result = await self._session.execute(
            select(func.count(DecisionOutcomeModel.id))
            .where(and_(
                base_filter,
                DecisionOutcomeModel.prediction_result == PredictionResult.ACCURATE.value
            ))
        )
        accurate_count = accurate_result.scalar() or 0
        
        inaccurate_result = await self._session.execute(
            select(func.count(DecisionOutcomeModel.id))
            .where(and_(
                base_filter,
                DecisionOutcomeModel.prediction_result == PredictionResult.INACCURATE.value
            ))
        )
        inaccurate_count = inaccurate_result.scalar() or 0
        
        total_assessed = accurate_count + inaccurate_count
        accuracy_rate = (accurate_count / total_assessed * 100) if total_assessed > 0 else 0.0
        
        # Confidence calibration
        calibration = await self._calculate_calibration(base_filter)
        
        return AccuracyMetrics(
            total_decisions=total_decisions,
            resolved_decisions=resolved_decisions,
            action_followed_rate=action_followed_rate,
            mean_impact_accuracy_pct=mean_impact,
            median_impact_accuracy_pct=None,  # Would need different query
            mean_delay_accuracy_pct=mean_delay,
            accurate_predictions=accurate_count,
            inaccurate_predictions=inaccurate_count,
            accuracy_rate=accuracy_rate,
            calibration_by_bucket=calibration,
            window_start=window_start,
            window_end=window_end,
        )
    
    async def _calculate_calibration(
        self,
        base_filter,
    ) -> Dict[str, float]:
        """
        Calculate confidence calibration by bucket.
        
        For each confidence bucket (0-20, 20-40, etc.), calculate
        what percentage of predictions were actually accurate.
        
        Perfect calibration: 70% confidence = 70% accuracy
        """
        buckets = {
            "0-20": (0, 0.2),
            "20-40": (0.2, 0.4),
            "40-60": (0.4, 0.6),
            "60-80": (0.6, 0.8),
            "80-100": (0.8, 1.0),
        }
        
        calibration = {}
        
        for bucket_name, (low, high) in buckets.items():
            # Get decisions in this confidence bucket
            bucket_filter = and_(
                base_filter,
                DecisionOutcomeModel.confidence_score >= low,
                DecisionOutcomeModel.confidence_score < high,
                DecisionOutcomeModel.prediction_result.isnot(None),
            )
            
            total_result = await self._session.execute(
                select(func.count(DecisionOutcomeModel.id))
                .where(bucket_filter)
            )
            total_in_bucket = total_result.scalar() or 0
            
            if total_in_bucket == 0:
                calibration[bucket_name] = 0.0
                continue
            
            accurate_result = await self._session.execute(
                select(func.count(DecisionOutcomeModel.id))
                .where(and_(
                    bucket_filter,
                    DecisionOutcomeModel.prediction_result == PredictionResult.ACCURATE.value
                ))
            )
            accurate_in_bucket = accurate_result.scalar() or 0
            
            calibration[bucket_name] = accurate_in_bucket / total_in_bucket * 100
            
            # Update metrics
            RECORDER.update_confidence_calibration(
                bucket=bucket_name,
                score=calibration[bucket_name],
            )
        
        return calibration
    
    async def get_pending_outcomes(
        self,
        older_than_days: int = 7,
    ) -> List[OutcomeRecord]:
        """Get decisions awaiting outcome feedback."""
        cutoff = datetime.utcnow() - timedelta(days=older_than_days)
        
        result = await self._session.execute(
            select(DecisionOutcomeModel)
            .where(and_(
                DecisionOutcomeModel.outcome_status == OutcomeStatus.PENDING.value,
                DecisionOutcomeModel.created_at <= cutoff,
            ))
            .order_by(DecisionOutcomeModel.created_at.asc())
        )
        
        models = result.scalars().all()
        return [self._model_to_record(m) for m in models]
