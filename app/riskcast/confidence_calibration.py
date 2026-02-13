"""
Confidence Calibration Module.

Production-grade confidence calibration with:
- Bayesian calibration
- Historical accuracy tracking
- Confidence bucket analysis
- Real-time calibration adjustments
"""

from typing import Optional, Dict, List, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import math

from pydantic import BaseModel, Field
import structlog

from app.core.metrics import RECORDER

logger = structlog.get_logger(__name__)


# ============================================================================
# CONFIGURATION
# ============================================================================


@dataclass
class CalibrationConfig:
    """Configuration for confidence calibration."""
    
    # Bucket boundaries for calibration analysis
    buckets: List[Tuple[float, float]] = field(default_factory=lambda: [
        (0.0, 0.2),
        (0.2, 0.4),
        (0.4, 0.6),
        (0.6, 0.8),
        (0.8, 1.0),
    ])
    
    # Minimum samples required for calibration
    min_samples_per_bucket: int = 10
    
    # Recalibration frequency
    recalibrate_every_n_decisions: int = 100
    
    # Maximum calibration adjustment
    max_adjustment: float = 0.15


# ============================================================================
# MODELS
# ============================================================================


class CalibrationBucket(BaseModel):
    """Statistics for a confidence bucket."""
    
    bucket_name: str
    lower_bound: float
    upper_bound: float
    total_predictions: int = 0
    accurate_predictions: int = 0
    observed_accuracy: float = 0.0
    calibration_error: float = 0.0
    
    def expected_accuracy(self) -> float:
        """Get expected accuracy (midpoint of bucket)."""
        return (self.lower_bound + self.upper_bound) / 2
    
    def update_observed(self) -> None:
        """Update observed accuracy."""
        if self.total_predictions > 0:
            self.observed_accuracy = self.accurate_predictions / self.total_predictions
            expected = self.expected_accuracy()
            self.calibration_error = self.observed_accuracy - expected


class CalibrationReport(BaseModel):
    """Full calibration report."""
    
    buckets: List[CalibrationBucket]
    total_predictions: int
    overall_accuracy: float
    expected_calibration_error: float
    mean_absolute_calibration_error: float
    brier_score: float
    calibrated_at: datetime = Field(default_factory=datetime.utcnow)
    
    def is_well_calibrated(self, threshold: float = 0.1) -> bool:
        """Check if predictions are well-calibrated."""
        return self.mean_absolute_calibration_error <= threshold


class CalibrationAdjustment(BaseModel):
    """Adjustment to apply to confidence scores."""
    
    original_confidence: float
    adjusted_confidence: float
    adjustment_factor: float
    reason: str


# ============================================================================
# CALIBRATION ENGINE
# ============================================================================


class ConfidenceCalibrator:
    """
    Calibrates confidence scores based on historical accuracy.
    
    Implements isotonic regression style calibration:
    1. Track predictions and outcomes in confidence buckets
    2. Calculate observed accuracy per bucket
    3. Apply calibration adjustment to new predictions
    
    This ensures that when we say "80% confident", we're actually
    correct about 80% of the time.
    """
    
    def __init__(
        self,
        config: Optional[CalibrationConfig] = None,
    ):
        self.config = config or CalibrationConfig()
        self._buckets: Dict[str, CalibrationBucket] = {}
        self._prediction_count = 0
        self._last_calibration: Optional[datetime] = None
        
        # Initialize buckets
        for i, (lower, upper) in enumerate(self.config.buckets):
            bucket_name = f"{int(lower*100)}-{int(upper*100)}"
            self._buckets[bucket_name] = CalibrationBucket(
                bucket_name=bucket_name,
                lower_bound=lower,
                upper_bound=upper,
            )
    
    def _get_bucket(self, confidence: float) -> CalibrationBucket:
        """Get the bucket for a confidence score."""
        for bucket in self._buckets.values():
            if bucket.lower_bound <= confidence < bucket.upper_bound:
                return bucket
            # Handle edge case for 1.0
            if confidence == 1.0 and bucket.upper_bound == 1.0:
                return bucket
        
        # Fallback to last bucket
        return list(self._buckets.values())[-1]
    
    def record_prediction(
        self,
        confidence: float,
        was_accurate: bool,
    ) -> None:
        """
        Record a prediction and its outcome.
        
        Args:
            confidence: Original confidence score (0-1)
            was_accurate: Whether the prediction was accurate
        """
        bucket = self._get_bucket(confidence)
        bucket.total_predictions += 1
        if was_accurate:
            bucket.accurate_predictions += 1
        bucket.update_observed()
        
        self._prediction_count += 1
        
        # Update metrics
        RECORDER.update_confidence_calibration(
            bucket=bucket.bucket_name,
            score=bucket.observed_accuracy * 100,
        )
        
        logger.debug(
            "prediction_recorded",
            confidence=confidence,
            bucket=bucket.bucket_name,
            was_accurate=was_accurate,
            bucket_accuracy=bucket.observed_accuracy,
        )
    
    def calibrate(self, confidence: float) -> CalibrationAdjustment:
        """
        Apply calibration to a confidence score.
        
        Uses isotonic regression style adjustment based on
        observed accuracy in each bucket.
        
        Args:
            confidence: Raw confidence score (0-1)
        
        Returns:
            Calibrated confidence with adjustment details
        """
        bucket = self._get_bucket(confidence)
        
        # If not enough data, return unadjusted
        if bucket.total_predictions < self.config.min_samples_per_bucket:
            return CalibrationAdjustment(
                original_confidence=confidence,
                adjusted_confidence=confidence,
                adjustment_factor=0.0,
                reason="Insufficient historical data",
            )
        
        # Calculate adjustment
        # If we're overconfident (saying 80% but only 60% accurate),
        # we should lower our confidence
        calibration_error = bucket.calibration_error
        
        # Limit adjustment to prevent wild swings
        adjustment = max(
            -self.config.max_adjustment,
            min(self.config.max_adjustment, calibration_error),
        )
        
        # Apply adjustment
        # If calibration_error is negative (we're overconfident),
        # we reduce confidence
        adjusted = confidence + adjustment
        adjusted = max(0.0, min(1.0, adjusted))
        
        reason = "Well calibrated" if abs(calibration_error) < 0.05 else (
            "Historically overconfident" if calibration_error < 0 
            else "Historically underconfident"
        )
        
        return CalibrationAdjustment(
            original_confidence=confidence,
            adjusted_confidence=adjusted,
            adjustment_factor=adjustment,
            reason=reason,
        )
    
    def get_report(self) -> CalibrationReport:
        """Generate a calibration report."""
        buckets = list(self._buckets.values())
        
        total_predictions = sum(b.total_predictions for b in buckets)
        total_accurate = sum(b.accurate_predictions for b in buckets)
        
        overall_accuracy = (
            total_accurate / total_predictions if total_predictions > 0 else 0.0
        )
        
        # Expected Calibration Error (ECE)
        ece = 0.0
        for bucket in buckets:
            if bucket.total_predictions > 0:
                weight = bucket.total_predictions / total_predictions
                ece += weight * abs(bucket.calibration_error)
        
        # Mean Absolute Calibration Error (MACE)
        mace = sum(abs(b.calibration_error) for b in buckets) / len(buckets)
        
        # Brier Score (measures both calibration and sharpness)
        # Lower is better, 0 is perfect
        brier_score = self._calculate_brier_score(buckets)
        
        return CalibrationReport(
            buckets=buckets,
            total_predictions=total_predictions,
            overall_accuracy=overall_accuracy,
            expected_calibration_error=ece,
            mean_absolute_calibration_error=mace,
            brier_score=brier_score,
        )
    
    def _calculate_brier_score(
        self,
        buckets: List[CalibrationBucket],
    ) -> float:
        """
        Calculate Brier score.
        
        Brier score = mean((predicted - actual)^2)
        Lower is better.
        """
        total_score = 0.0
        total_predictions = 0
        
        for bucket in buckets:
            if bucket.total_predictions > 0:
                # Use bucket midpoint as predicted probability
                predicted = bucket.expected_accuracy()
                
                # Calculate squared errors for this bucket
                # For accurate predictions: (predicted - 1)^2
                # For inaccurate predictions: (predicted - 0)^2
                accurate_error = bucket.accurate_predictions * ((predicted - 1) ** 2)
                inaccurate_error = (
                    (bucket.total_predictions - bucket.accurate_predictions) * 
                    (predicted ** 2)
                )
                
                total_score += accurate_error + inaccurate_error
                total_predictions += bucket.total_predictions
        
        return total_score / total_predictions if total_predictions > 0 else 0.0
    
    def suggest_improvements(self) -> List[str]:
        """Suggest improvements based on calibration analysis."""
        suggestions = []
        
        report = self.get_report()
        
        if report.mean_absolute_calibration_error > 0.15:
            suggestions.append(
                "High calibration error detected. Consider using more data sources "
                "or adjusting signal weights."
            )
        
        # Check for systematic over/underconfidence
        overconfident_buckets = [
            b for b in report.buckets
            if b.total_predictions >= self.config.min_samples_per_bucket
            and b.calibration_error < -0.1
        ]
        
        if len(overconfident_buckets) > 2:
            suggestions.append(
                "Systematic overconfidence detected in high confidence predictions. "
                "Consider reducing base confidence or adding more caveats."
            )
        
        underconfident_buckets = [
            b for b in report.buckets
            if b.total_predictions >= self.config.min_samples_per_bucket
            and b.calibration_error > 0.1
        ]
        
        if len(underconfident_buckets) > 2:
            suggestions.append(
                "Systematic underconfidence detected. "
                "Predictions are more accurate than confidence suggests."
            )
        
        # Check for data sparsity
        sparse_buckets = [
            b for b in report.buckets
            if b.total_predictions < self.config.min_samples_per_bucket
        ]
        
        if len(sparse_buckets) > 2:
            suggestions.append(
                f"Insufficient data in {len(sparse_buckets)} buckets. "
                "More historical outcomes needed for accurate calibration."
            )
        
        return suggestions


# ============================================================================
# MULTI-FACTOR CONFIDENCE CALCULATOR
# ============================================================================


class ConfidenceFactors(BaseModel):
    """Factors contributing to confidence score."""
    
    # Signal quality factors
    signal_source_reliability: float = Field(ge=0, le=1)
    signal_corroboration: float = Field(ge=0, le=1)  # Multiple sources agree
    signal_recency: float = Field(ge=0, le=1)  # How recent the signal is
    
    # Historical factors
    historical_accuracy: float = Field(ge=0, le=1)  # Past prediction accuracy
    similar_event_accuracy: float = Field(ge=0, le=1)  # Accuracy for similar events
    
    # Data quality factors
    data_completeness: float = Field(ge=0, le=1)
    data_freshness: float = Field(ge=0, le=1)
    
    # Model factors
    model_agreement: float = Field(ge=0, le=1)  # Different models agree


class MultiFactorConfidenceCalculator:
    """
    Calculates confidence scores from multiple factors.
    
    Uses weighted combination with penalties for:
    - Low corroboration
    - Stale data
    - Model disagreement
    """
    
    def __init__(
        self,
        weights: Optional[Dict[str, float]] = None,
    ):
        self.weights = weights or {
            "signal_source_reliability": 0.20,
            "signal_corroboration": 0.15,
            "signal_recency": 0.10,
            "historical_accuracy": 0.20,
            "similar_event_accuracy": 0.10,
            "data_completeness": 0.10,
            "data_freshness": 0.05,
            "model_agreement": 0.10,
        }
    
    def calculate(
        self,
        factors: ConfidenceFactors,
        calibrator: Optional[ConfidenceCalibrator] = None,
    ) -> Tuple[float, Dict[str, float]]:
        """
        Calculate confidence score from factors.
        
        Args:
            factors: Input factors
            calibrator: Optional calibrator for adjustment
        
        Returns:
            Tuple of (confidence_score, factor_contributions)
        """
        contributions = {}
        total = 0.0
        
        for factor_name, weight in self.weights.items():
            value = getattr(factors, factor_name)
            contribution = value * weight
            contributions[factor_name] = contribution
            total += contribution
        
        # Apply penalties
        penalties = []
        
        # Low corroboration penalty
        if factors.signal_corroboration < 0.3:
            penalty = 0.10
            total -= penalty
            penalties.append(("low_corroboration", penalty))
        
        # Stale data penalty
        if factors.data_freshness < 0.5:
            penalty = 0.05
            total -= penalty
            penalties.append(("stale_data", penalty))
        
        # Model disagreement penalty
        if factors.model_agreement < 0.5:
            penalty = 0.10
            total -= penalty
            penalties.append(("model_disagreement", penalty))
        
        # Ensure bounds
        confidence = max(0.0, min(1.0, total))
        
        # Apply calibration if available
        if calibrator:
            adjustment = calibrator.calibrate(confidence)
            confidence = adjustment.adjusted_confidence
        
        logger.info(
            "confidence_calculated",
            raw_confidence=total,
            final_confidence=confidence,
            penalties=penalties,
        )
        
        return confidence, contributions


# ============================================================================
# GLOBAL INSTANCE
# ============================================================================

_calibrator: Optional[ConfidenceCalibrator] = None


def get_calibrator() -> ConfidenceCalibrator:
    """Get the global confidence calibrator."""
    global _calibrator
    if _calibrator is None:
        _calibrator = ConfidenceCalibrator()
    return _calibrator
