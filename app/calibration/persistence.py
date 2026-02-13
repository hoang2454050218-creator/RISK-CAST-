"""
Calibration Data Persistence to PostgreSQL.

CRITICAL: In-memory calibration loses data on restart.
This module persists all calibration data for continuous improvement.

Components:
- CalibrationPersistence: Low-level persistence operations
- PersistentCalibrator: High-level calibrator with persistence

Addresses audit gap A3: "Calibration data persistence - in-memory storage loses data"
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple, Any
from dataclasses import dataclass

from sqlalchemy import select, func, and_, update
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
import structlog

from app.calibration.models import (
    CalibrationBucketModel,
    PredictionRecordModel,
    CalibrationMetricsModel,
    CICoverageRecordModel,
)

logger = structlog.get_logger(__name__)


# =============================================================================
# DATA CLASSES
# =============================================================================


class CalibrationResult(BaseModel):
    """Result of a calibration operation."""
    
    original_confidence: float = Field(ge=0, le=1)
    calibrated_confidence: float = Field(ge=0, le=1)
    adjustment: float
    reason: str
    bucket: str
    bucket_total: int
    bucket_accuracy: float


class CalibrationSnapshot(BaseModel):
    """Snapshot of calibration state."""
    
    timestamp: datetime
    ece: float = Field(ge=0, description="Expected Calibration Error")
    brier_score: float = Field(ge=0, description="Brier Score")
    mace: float = Field(ge=0, description="Mean Absolute Calibration Error")
    total_predictions: int
    predictions_with_outcomes: int
    buckets: List[Dict[str, Any]]
    is_well_calibrated: bool
    recommendations: List[str]


# =============================================================================
# CALIBRATION PERSISTENCE
# =============================================================================


class CalibrationPersistence:
    """
    Persists calibration data to PostgreSQL.
    
    Data stored:
    1. Prediction records: (decision_id, confidence, predicted, actual)
    2. Calibration buckets: (bucket, count, correct, accuracy)
    3. Calibration metrics: (ECE, Brier score, timestamp)
    4. CI coverage records: (CI bounds, actual value, is_covered)
    
    All operations are async for non-blocking I/O.
    """
    
    # Bucket boundaries (0-10%, 10-20%, ..., 90-100%)
    BUCKET_BOUNDS = [
        (0.0, 0.1, "0-10%"),
        (0.1, 0.2, "10-20%"),
        (0.2, 0.3, "20-30%"),
        (0.3, 0.4, "30-40%"),
        (0.4, 0.5, "40-50%"),
        (0.5, 0.6, "50-60%"),
        (0.6, 0.7, "60-70%"),
        (0.7, 0.8, "70-80%"),
        (0.8, 0.9, "80-90%"),
        (0.9, 1.0, "90-100%"),
    ]
    
    def __init__(self, session_factory):
        """
        Initialize with async session factory.
        
        Args:
            session_factory: Callable that returns AsyncSession
        """
        self._session_factory = session_factory
    
    # =========================================================================
    # PREDICTION RECORDING
    # =========================================================================
    
    async def record_prediction(
        self,
        decision_id: str,
        customer_id: str,
        confidence: float,
        predicted_outcome: bool,
        predicted_action: Optional[str] = None,
        predicted_exposure_usd: Optional[float] = None,
        predicted_exposure_ci: Optional[Tuple[float, float]] = None,
        predicted_delay_days: Optional[float] = None,
        predicted_delay_ci: Optional[Tuple[float, float]] = None,
        chokepoint: Optional[str] = None,
        event_type: Optional[str] = None,
    ) -> int:
        """
        Record a prediction for later calibration.
        
        Called immediately after decision generation.
        
        Returns:
            ID of the created prediction record
        """
        async with self._session_factory() as session:
            record = PredictionRecordModel(
                decision_id=decision_id,
                customer_id=customer_id,
                predicted_confidence=confidence,
                predicted_outcome=predicted_outcome,
                predicted_action=predicted_action,
                predicted_exposure_usd=predicted_exposure_usd,
                predicted_exposure_ci_low=predicted_exposure_ci[0] if predicted_exposure_ci else None,
                predicted_exposure_ci_high=predicted_exposure_ci[1] if predicted_exposure_ci else None,
                predicted_delay_days=predicted_delay_days,
                predicted_delay_ci_low=predicted_delay_ci[0] if predicted_delay_ci else None,
                predicted_delay_ci_high=predicted_delay_ci[1] if predicted_delay_ci else None,
                chokepoint=chokepoint,
                event_type=event_type,
                recorded_at=datetime.utcnow(),
            )
            session.add(record)
            await session.commit()
            await session.refresh(record)
            
            logger.debug(
                "prediction_recorded",
                decision_id=decision_id,
                confidence=confidence,
                prediction_id=record.id,
            )
            
            return record.id
    
    async def record_outcome(
        self,
        decision_id: str,
        actual_outcome: bool,
        actual_exposure_usd: Optional[float] = None,
        actual_delay_days: Optional[float] = None,
        action_was_followed: Optional[bool] = None,
    ) -> bool:
        """
        Record actual outcome for a prediction.
        
        Called when we learn what actually happened.
        Updates the prediction record and recalculates bucket statistics.
        
        Returns:
            True if record was found and updated, False otherwise
        """
        async with self._session_factory() as session:
            # Find the prediction record
            result = await session.execute(
                select(PredictionRecordModel).where(
                    PredictionRecordModel.decision_id == decision_id
                )
            )
            record = result.scalar_one_or_none()
            
            if not record:
                logger.warning("prediction_not_found", decision_id=decision_id)
                return False
            
            # Update with actual outcome
            record.actual_outcome = actual_outcome
            record.actual_exposure_usd = actual_exposure_usd
            record.actual_delay_days = actual_delay_days
            record.action_was_followed = action_was_followed
            record.resolved_at = datetime.utcnow()
            
            await session.commit()
            
            # Update calibration buckets
            await self._update_bucket(session, record)
            
            # Update CI coverage records if we have actual values
            if actual_exposure_usd is not None or actual_delay_days is not None:
                await self._update_ci_coverage(session, record)
            
            logger.info(
                "outcome_recorded",
                decision_id=decision_id,
                predicted_confidence=record.predicted_confidence,
                predicted_outcome=record.predicted_outcome,
                actual_outcome=actual_outcome,
                was_correct=record.predicted_outcome == actual_outcome,
            )
            
            return True
    
    async def _update_bucket(
        self,
        session: AsyncSession,
        record: PredictionRecordModel,
    ) -> None:
        """Update calibration bucket with new outcome."""
        bucket_name = self._get_bucket_name(record.predicted_confidence)
        
        # Get or create bucket
        result = await session.execute(
            select(CalibrationBucketModel).where(
                CalibrationBucketModel.bucket_name == bucket_name
            )
        )
        bucket = result.scalar_one_or_none()
        
        if not bucket:
            # Create bucket
            for start, end, name in self.BUCKET_BOUNDS:
                if name == bucket_name:
                    bucket = CalibrationBucketModel(
                        bucket_start=start,
                        bucket_end=end,
                        bucket_name=name,
                        expected_accuracy=(start + end) / 2,
                        total_count=0,
                        correct_count=0,
                    )
                    session.add(bucket)
                    break
        
        # Update counts
        bucket.total_count += 1
        if record.predicted_outcome == record.actual_outcome:
            bucket.correct_count += 1
        
        # Recalculate derived values
        bucket.observed_accuracy = bucket.correct_count / bucket.total_count
        bucket.calibration_error = bucket.observed_accuracy - bucket.expected_accuracy
        bucket.last_updated = datetime.utcnow()
        
        await session.commit()
    
    async def _update_ci_coverage(
        self,
        session: AsyncSession,
        record: PredictionRecordModel,
    ) -> None:
        """Update CI coverage records with actual values."""
        # Update exposure CI coverage
        if (record.actual_exposure_usd is not None and 
            record.predicted_exposure_ci_low is not None):
            
            result = await session.execute(
                select(CICoverageRecordModel).where(
                    and_(
                        CICoverageRecordModel.prediction_id == record.id,
                        CICoverageRecordModel.metric_type == "exposure",
                    )
                )
            )
            coverage_record = result.scalar_one_or_none()
            
            if coverage_record:
                coverage_record.actual_value = record.actual_exposure_usd
                coverage_record.is_covered = (
                    coverage_record.ci_low <= record.actual_exposure_usd <= coverage_record.ci_high
                )
                coverage_record.resolved_at = datetime.utcnow()
        
        # Update delay CI coverage
        if (record.actual_delay_days is not None and 
            record.predicted_delay_ci_low is not None):
            
            result = await session.execute(
                select(CICoverageRecordModel).where(
                    and_(
                        CICoverageRecordModel.prediction_id == record.id,
                        CICoverageRecordModel.metric_type == "delay",
                    )
                )
            )
            coverage_record = result.scalar_one_or_none()
            
            if coverage_record:
                coverage_record.actual_value = record.actual_delay_days
                coverage_record.is_covered = (
                    coverage_record.ci_low <= record.actual_delay_days <= coverage_record.ci_high
                )
                coverage_record.resolved_at = datetime.utcnow()
        
        await session.commit()
    
    def _get_bucket_name(self, confidence: float) -> str:
        """Get bucket name for a confidence value."""
        for start, end, name in self.BUCKET_BOUNDS:
            if start <= confidence < end:
                return name
            if confidence == 1.0 and end == 1.0:
                return name
        return "90-100%"  # Fallback
    
    # =========================================================================
    # CI COVERAGE RECORDING
    # =========================================================================
    
    async def record_ci(
        self,
        prediction_id: int,
        metric_type: str,
        ci_level: str,
        ci_low: float,
        ci_high: float,
        point_estimate: float,
        chokepoint: Optional[str] = None,
        event_type: Optional[str] = None,
    ) -> int:
        """
        Record a confidence interval for later coverage validation.
        
        Args:
            prediction_id: ID of the prediction record
            metric_type: Type of metric (exposure, delay, cost, inaction)
            ci_level: CI level (90% or 95%)
            ci_low: Lower bound
            ci_high: Upper bound
            point_estimate: Point estimate
            
        Returns:
            ID of created CI coverage record
        """
        async with self._session_factory() as session:
            record = CICoverageRecordModel(
                prediction_id=prediction_id,
                metric_type=metric_type,
                ci_level=ci_level,
                ci_low=ci_low,
                ci_high=ci_high,
                point_estimate=point_estimate,
                chokepoint=chokepoint,
                event_type=event_type,
                recorded_at=datetime.utcnow(),
            )
            session.add(record)
            await session.commit()
            await session.refresh(record)
            
            return record.id
    
    # =========================================================================
    # METRICS CALCULATION
    # =========================================================================
    
    async def get_calibration_buckets(self) -> List[Dict[str, Any]]:
        """Get all calibration buckets with statistics."""
        async with self._session_factory() as session:
            result = await session.execute(
                select(CalibrationBucketModel).order_by(
                    CalibrationBucketModel.bucket_start
                )
            )
            buckets = result.scalars().all()
            
            return [
                {
                    "bucket_name": b.bucket_name,
                    "bucket_start": b.bucket_start,
                    "bucket_end": b.bucket_end,
                    "total_count": b.total_count,
                    "correct_count": b.correct_count,
                    "observed_accuracy": b.observed_accuracy,
                    "expected_accuracy": b.expected_accuracy,
                    "calibration_error": b.calibration_error,
                    "last_updated": b.last_updated.isoformat() if b.last_updated else None,
                }
                for b in buckets
            ]
    
    async def calculate_ece(self) -> float:
        """
        Calculate Expected Calibration Error.
        
        ECE = Σ (weight_i × |observed_accuracy_i - expected_accuracy_i|)
        where weight_i = n_i / N
        
        Lower is better. < 0.05 is well-calibrated.
        """
        buckets = await self.get_calibration_buckets()
        
        if not buckets:
            return 0.0
        
        total_samples = sum(b["total_count"] for b in buckets)
        if total_samples == 0:
            return 0.0
        
        ece = sum(
            (b["total_count"] / total_samples) * abs(b["calibration_error"])
            for b in buckets
            if b["total_count"] > 0
        )
        
        return round(ece, 4)
    
    async def calculate_brier_score(self, days: int = 90) -> float:
        """
        Calculate Brier score for recent predictions.
        
        Brier = mean((predicted_probability - actual_outcome)^2)
        
        Lower is better. 0 is perfect.
        
        Args:
            days: Number of days to look back
        """
        async with self._session_factory() as session:
            cutoff = datetime.utcnow() - timedelta(days=days)
            
            result = await session.execute(
                select(PredictionRecordModel).where(
                    and_(
                        PredictionRecordModel.resolved_at.isnot(None),
                        PredictionRecordModel.resolved_at >= cutoff,
                    )
                )
            )
            records = result.scalars().all()
            
            if not records:
                return 0.0
            
            # Brier = mean((predicted - actual)^2)
            brier = sum(
                (r.predicted_confidence - (1.0 if r.actual_outcome else 0.0)) ** 2
                for r in records
            ) / len(records)
            
            return round(brier, 4)
    
    async def calculate_mace(self) -> float:
        """
        Calculate Mean Absolute Calibration Error.
        
        MACE = mean(|observed_accuracy_i - expected_accuracy_i|) for all buckets
        """
        buckets = await self.get_calibration_buckets()
        
        if not buckets:
            return 0.0
        
        non_empty = [b for b in buckets if b["total_count"] > 0]
        if not non_empty:
            return 0.0
        
        mace = sum(abs(b["calibration_error"]) for b in non_empty) / len(non_empty)
        return round(mace, 4)
    
    async def get_calibration_snapshot(self) -> CalibrationSnapshot:
        """Get a complete calibration snapshot."""
        ece = await self.calculate_ece()
        brier = await self.calculate_brier_score()
        mace = await self.calculate_mace()
        buckets = await self.get_calibration_buckets()
        
        # Count predictions
        async with self._session_factory() as session:
            total_result = await session.execute(
                select(func.count(PredictionRecordModel.id))
            )
            total_predictions = total_result.scalar() or 0
            
            resolved_result = await session.execute(
                select(func.count(PredictionRecordModel.id)).where(
                    PredictionRecordModel.resolved_at.isnot(None)
                )
            )
            predictions_with_outcomes = resolved_result.scalar() or 0
        
        # Generate recommendations
        recommendations = self._generate_recommendations(buckets, ece, brier)
        
        return CalibrationSnapshot(
            timestamp=datetime.utcnow(),
            ece=ece,
            brier_score=brier,
            mace=mace,
            total_predictions=total_predictions,
            predictions_with_outcomes=predictions_with_outcomes,
            buckets=buckets,
            is_well_calibrated=ece < 0.05 and brier < 0.15,
            recommendations=recommendations,
        )
    
    def _generate_recommendations(
        self,
        buckets: List[Dict],
        ece: float,
        brier: float,
    ) -> List[str]:
        """Generate calibration improvement recommendations."""
        recommendations = []
        
        # Check ECE
        if ece > 0.10:
            recommendations.append(
                f"High ECE ({ece:.2%}). Consider using more data sources "
                "or adjusting confidence weights."
            )
        
        # Check for systematic over/underconfidence
        overconfident = [
            b for b in buckets
            if b["total_count"] >= 10 and b["calibration_error"] < -0.1
        ]
        underconfident = [
            b for b in buckets
            if b["total_count"] >= 10 and b["calibration_error"] > 0.1
        ]
        
        if len(overconfident) >= 2:
            buckets_str = ", ".join(b["bucket_name"] for b in overconfident)
            recommendations.append(
                f"Overconfidence detected in buckets: {buckets_str}. "
                "Consider reducing base confidence scores."
            )
        
        if len(underconfident) >= 2:
            buckets_str = ", ".join(b["bucket_name"] for b in underconfident)
            recommendations.append(
                f"Underconfidence detected in buckets: {buckets_str}. "
                "Predictions are more accurate than confidence suggests."
            )
        
        # Check for sparse buckets
        sparse = [b for b in buckets if b["total_count"] < 10]
        if len(sparse) > 3:
            recommendations.append(
                f"Insufficient data in {len(sparse)} buckets. "
                "Need more historical outcomes for accurate calibration."
            )
        
        # Check Brier score
        if brier > 0.25:
            recommendations.append(
                f"High Brier score ({brier:.3f}). "
                "Overall prediction quality needs improvement."
            )
        
        return recommendations
    
    # =========================================================================
    # METRICS PERSISTENCE
    # =========================================================================
    
    async def persist_metrics_snapshot(self) -> CalibrationMetricsModel:
        """
        Persist current calibration metrics as a historical snapshot.
        
        Call this periodically (e.g., daily) to track calibration health.
        """
        snapshot = await self.get_calibration_snapshot()
        
        async with self._session_factory() as session:
            metrics = CalibrationMetricsModel(
                timestamp=snapshot.timestamp,
                ece=snapshot.ece,
                brier_score=snapshot.brier_score,
                mace=snapshot.mace,
                total_predictions=snapshot.total_predictions,
                predictions_with_outcomes=snapshot.predictions_with_outcomes,
                bucket_data=snapshot.buckets,
                recommendations=snapshot.recommendations,
            )
            session.add(metrics)
            await session.commit()
            await session.refresh(metrics)
            
            logger.info(
                "calibration_metrics_persisted",
                ece=snapshot.ece,
                brier_score=snapshot.brier_score,
                total_predictions=snapshot.total_predictions,
            )
            
            return metrics
    
    async def get_metrics_history(
        self,
        days: int = 30,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get historical calibration metrics."""
        async with self._session_factory() as session:
            cutoff = datetime.utcnow() - timedelta(days=days)
            
            result = await session.execute(
                select(CalibrationMetricsModel)
                .where(CalibrationMetricsModel.timestamp >= cutoff)
                .order_by(CalibrationMetricsModel.timestamp.desc())
                .limit(limit)
            )
            metrics = result.scalars().all()
            
            return [
                {
                    "timestamp": m.timestamp.isoformat(),
                    "ece": m.ece,
                    "brier_score": m.brier_score,
                    "mace": m.mace,
                    "total_predictions": m.total_predictions,
                    "predictions_with_outcomes": m.predictions_with_outcomes,
                }
                for m in metrics
            ]


# =============================================================================
# PERSISTENT CALIBRATOR
# =============================================================================


class PersistentCalibrator:
    """
    High-level calibrator with PostgreSQL persistence.
    
    Wraps CalibrationPersistence with a calibration-focused API.
    Replaces the in-memory ConfidenceCalibrator.
    """
    
    MAX_ADJUSTMENT = 0.15  # Maximum calibration adjustment
    MIN_SAMPLES = 10  # Minimum samples for calibration
    
    def __init__(self, persistence: CalibrationPersistence):
        self._persistence = persistence
    
    async def calibrate(self, raw_confidence: float) -> CalibrationResult:
        """
        Apply calibration to a raw confidence score.
        
        Uses isotonic regression-style adjustment based on
        observed accuracy in each bucket.
        
        Args:
            raw_confidence: Raw confidence score (0-1)
            
        Returns:
            CalibrationResult with adjusted confidence
        """
        buckets = await self._persistence.get_calibration_buckets()
        
        # Find matching bucket
        bucket = self._find_bucket(buckets, raw_confidence)
        
        if not bucket or bucket["total_count"] < self.MIN_SAMPLES:
            return CalibrationResult(
                original_confidence=raw_confidence,
                calibrated_confidence=raw_confidence,
                adjustment=0.0,
                reason="Insufficient historical data",
                bucket=bucket["bucket_name"] if bucket else "unknown",
                bucket_total=bucket["total_count"] if bucket else 0,
                bucket_accuracy=bucket["observed_accuracy"] if bucket else 0.0,
            )
        
        # Calculate adjustment based on calibration error
        # If overconfident (observed < expected), reduce confidence
        # If underconfident (observed > expected), increase confidence
        calibration_error = bucket["calibration_error"]
        
        # Limit adjustment
        adjustment = max(
            -self.MAX_ADJUSTMENT,
            min(self.MAX_ADJUSTMENT, calibration_error)
        )
        
        calibrated = max(0.0, min(1.0, raw_confidence + adjustment))
        
        # Determine reason
        if abs(calibration_error) < 0.05:
            reason = "Well calibrated"
        elif calibration_error < 0:
            reason = "Historically overconfident - reducing"
        else:
            reason = "Historically underconfident - increasing"
        
        return CalibrationResult(
            original_confidence=raw_confidence,
            calibrated_confidence=calibrated,
            adjustment=adjustment,
            reason=reason,
            bucket=bucket["bucket_name"],
            bucket_total=bucket["total_count"],
            bucket_accuracy=bucket["observed_accuracy"],
        )
    
    async def calibrate_and_persist(
        self,
        decision_id: str,
        customer_id: str,
        raw_confidence: float,
        predicted_outcome: bool = True,
        predicted_action: Optional[str] = None,
        predicted_exposure_usd: Optional[float] = None,
        predicted_exposure_ci: Optional[Tuple[float, float]] = None,
        predicted_delay_days: Optional[float] = None,
        predicted_delay_ci: Optional[Tuple[float, float]] = None,
        chokepoint: Optional[str] = None,
        event_type: Optional[str] = None,
    ) -> CalibrationResult:
        """
        Calibrate confidence and persist prediction for later validation.
        
        This is the main method to call during decision composition.
        """
        # Calibrate
        result = await self.calibrate(raw_confidence)
        
        # Persist prediction
        prediction_id = await self._persistence.record_prediction(
            decision_id=decision_id,
            customer_id=customer_id,
            confidence=raw_confidence,
            predicted_outcome=predicted_outcome,
            predicted_action=predicted_action,
            predicted_exposure_usd=predicted_exposure_usd,
            predicted_exposure_ci=predicted_exposure_ci,
            predicted_delay_days=predicted_delay_days,
            predicted_delay_ci=predicted_delay_ci,
            chokepoint=chokepoint,
            event_type=event_type,
        )
        
        # Record CI coverage entries if CIs provided
        if predicted_exposure_ci:
            await self._persistence.record_ci(
                prediction_id=prediction_id,
                metric_type="exposure",
                ci_level="90%",
                ci_low=predicted_exposure_ci[0],
                ci_high=predicted_exposure_ci[1],
                point_estimate=predicted_exposure_usd or 0,
                chokepoint=chokepoint,
                event_type=event_type,
            )
        
        if predicted_delay_ci:
            await self._persistence.record_ci(
                prediction_id=prediction_id,
                metric_type="delay",
                ci_level="90%",
                ci_low=predicted_delay_ci[0],
                ci_high=predicted_delay_ci[1],
                point_estimate=predicted_delay_days or 0,
                chokepoint=chokepoint,
                event_type=event_type,
            )
        
        logger.debug(
            "calibration_applied",
            decision_id=decision_id,
            raw_confidence=raw_confidence,
            calibrated_confidence=result.calibrated_confidence,
            adjustment=result.adjustment,
        )
        
        return result
    
    def _find_bucket(
        self,
        buckets: List[Dict],
        confidence: float,
    ) -> Optional[Dict]:
        """Find the bucket for a confidence value."""
        for bucket in buckets:
            if bucket["bucket_start"] <= confidence < bucket["bucket_end"]:
                return bucket
            if confidence == 1.0 and bucket["bucket_end"] == 1.0:
                return bucket
        return None
    
    async def get_report(self) -> CalibrationSnapshot:
        """Get full calibration report."""
        return await self._persistence.get_calibration_snapshot()
