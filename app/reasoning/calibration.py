"""
Calibration scheduler for automated probability recalibration.

This module implements GAP A2.1: Automated recalibration missing.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple
import asyncio
import structlog

logger = structlog.get_logger(__name__)


class CalibrationStatus(str, Enum):
    """Status of a calibration run."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class CalibrationResult:
    """Result of a calibration run."""
    calibration_id: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: CalibrationStatus = CalibrationStatus.PENDING
    predictions_evaluated: int = 0
    accuracy_before: float = 0.0
    accuracy_after: float = 0.0
    brier_score_before: float = 0.0
    brier_score_after: float = 0.0
    calibration_error_before: float = 0.0
    calibration_error_after: float = 0.0
    adjustments_made: Dict[str, float] = field(default_factory=dict)
    error_message: Optional[str] = None
    
    @property
    def improvement_pct(self) -> float:
        """Calculate improvement percentage in calibration error."""
        if self.calibration_error_before == 0:
            return 0.0
        return (
            (self.calibration_error_before - self.calibration_error_after)
            / self.calibration_error_before
            * 100
        )


@dataclass
class CalibrationConfig:
    """Configuration for calibration scheduler."""
    # Schedule settings
    interval_hours: int = 24
    min_samples_required: int = 100
    lookback_days: int = 30
    
    # Calibration thresholds
    recalibration_threshold: float = 0.05  # Trigger if error > 5%
    max_adjustment_per_run: float = 0.1    # Max 10% adjustment
    
    # Performance
    batch_size: int = 1000
    max_concurrent_tasks: int = 3
    
    # Alerting
    alert_on_degradation: bool = True
    degradation_threshold: float = 0.02


class PlattScaling:
    """Platt scaling for probability calibration."""
    
    def __init__(self):
        self._a: float = 1.0  # Scale parameter
        self._b: float = 0.0  # Shift parameter
        self._fitted: bool = False
    
    def fit(
        self,
        predicted_probs: List[float],
        actual_outcomes: List[int],
        learning_rate: float = 0.01,
        max_iterations: int = 1000,
        tolerance: float = 1e-6,
    ) -> None:
        """
        Fit Platt scaling parameters using gradient descent.
        
        Args:
            predicted_probs: List of predicted probabilities
            actual_outcomes: List of actual outcomes (0 or 1)
            learning_rate: Gradient descent learning rate
            max_iterations: Maximum iterations
            tolerance: Convergence tolerance
        """
        import math
        
        if len(predicted_probs) != len(actual_outcomes):
            raise ValueError("Predictions and outcomes must have same length")
        
        if len(predicted_probs) < 10:
            raise ValueError("Need at least 10 samples for calibration")
        
        # Initialize parameters
        a, b = 1.0, 0.0
        
        for iteration in range(max_iterations):
            # Compute gradients
            grad_a, grad_b = 0.0, 0.0
            total_loss = 0.0
            
            for p, y in zip(predicted_probs, actual_outcomes):
                # Avoid log(0)
                p = max(min(p, 0.9999), 0.0001)
                
                # Calibrated probability
                logit = math.log(p / (1 - p))
                z = a * logit + b
                
                # Sigmoid
                if z > 700:
                    q = 1.0
                elif z < -700:
                    q = 0.0
                else:
                    q = 1.0 / (1.0 + math.exp(-z))
                
                # Loss
                if y == 1:
                    total_loss -= math.log(max(q, 1e-10))
                else:
                    total_loss -= math.log(max(1 - q, 1e-10))
                
                # Gradients
                error = q - y
                grad_a += error * logit
                grad_b += error
            
            n = len(predicted_probs)
            grad_a /= n
            grad_b /= n
            total_loss /= n
            
            # Update parameters
            a_new = a - learning_rate * grad_a
            b_new = b - learning_rate * grad_b
            
            # Check convergence
            if abs(a_new - a) < tolerance and abs(b_new - b) < tolerance:
                break
            
            a, b = a_new, b_new
        
        self._a = a
        self._b = b
        self._fitted = True
        
        logger.info(
            "platt_scaling_fitted",
            a=a,
            b=b,
            iterations=iteration + 1,
            final_loss=total_loss,
        )
    
    def calibrate(self, prob: float) -> float:
        """Apply Platt scaling to a probability."""
        import math
        
        if not self._fitted:
            return prob
        
        prob = max(min(prob, 0.9999), 0.0001)
        logit = math.log(prob / (1 - prob))
        z = self._a * logit + self._b
        
        if z > 700:
            return 1.0
        elif z < -700:
            return 0.0
        return 1.0 / (1.0 + math.exp(-z))
    
    @property
    def parameters(self) -> Tuple[float, float]:
        """Get scaling parameters."""
        return self._a, self._b


class IsotonicRegression:
    """Isotonic regression for probability calibration."""
    
    def __init__(self):
        self._thresholds: List[float] = []
        self._values: List[float] = []
        self._fitted: bool = False
    
    def fit(
        self,
        predicted_probs: List[float],
        actual_outcomes: List[int],
    ) -> None:
        """
        Fit isotonic regression.
        
        Uses Pool Adjacent Violators Algorithm (PAVA).
        """
        if len(predicted_probs) != len(actual_outcomes):
            raise ValueError("Predictions and outcomes must have same length")
        
        if len(predicted_probs) < 10:
            raise ValueError("Need at least 10 samples for calibration")
        
        # Sort by predicted probability
        paired = sorted(zip(predicted_probs, actual_outcomes))
        probs = [p for p, _ in paired]
        outcomes = [y for _, y in paired]
        
        # PAVA algorithm
        n = len(probs)
        weights = [1.0] * n
        values = [float(y) for y in outcomes]
        
        # Merge adjacent violators
        i = 0
        while i < n - 1:
            if values[i] > values[i + 1]:
                # Merge with weighted average
                w = weights[i] + weights[i + 1]
                v = (weights[i] * values[i] + weights[i + 1] * values[i + 1]) / w
                
                values[i] = v
                weights[i] = w
                del values[i + 1]
                del weights[i + 1]
                del probs[i + 1]
                n -= 1
                
                # Check backwards
                if i > 0:
                    i -= 1
            else:
                i += 1
        
        self._thresholds = probs
        self._values = values
        self._fitted = True
        
        logger.info(
            "isotonic_regression_fitted",
            num_bins=len(self._thresholds),
        )
    
    def calibrate(self, prob: float) -> float:
        """Apply isotonic regression to a probability."""
        if not self._fitted or not self._thresholds:
            return prob
        
        # Binary search for the right bin
        left, right = 0, len(self._thresholds) - 1
        
        while left < right:
            mid = (left + right + 1) // 2
            if self._thresholds[mid] <= prob:
                left = mid
            else:
                right = mid - 1
        
        return self._values[left]


def calculate_calibration_error(
    predicted_probs: List[float],
    actual_outcomes: List[int],
    num_bins: int = 10,
) -> Tuple[float, List[Dict[str, float]]]:
    """
    Calculate Expected Calibration Error (ECE).
    
    Args:
        predicted_probs: List of predicted probabilities
        actual_outcomes: List of actual outcomes (0 or 1)
        num_bins: Number of bins for calibration
        
    Returns:
        Tuple of (ECE, list of bin statistics)
    """
    if len(predicted_probs) != len(actual_outcomes):
        raise ValueError("Predictions and outcomes must have same length")
    
    n = len(predicted_probs)
    if n == 0:
        return 0.0, []
    
    # Create bins
    bins = [[] for _ in range(num_bins)]
    
    for prob, outcome in zip(predicted_probs, actual_outcomes):
        bin_idx = min(int(prob * num_bins), num_bins - 1)
        bins[bin_idx].append((prob, outcome))
    
    # Calculate ECE
    ece = 0.0
    bin_stats = []
    
    for i, bin_data in enumerate(bins):
        if not bin_data:
            continue
        
        probs_in_bin = [p for p, _ in bin_data]
        outcomes_in_bin = [y for _, y in bin_data]
        
        avg_confidence = sum(probs_in_bin) / len(probs_in_bin)
        accuracy = sum(outcomes_in_bin) / len(outcomes_in_bin)
        
        bin_weight = len(bin_data) / n
        ece += bin_weight * abs(accuracy - avg_confidence)
        
        bin_stats.append({
            "bin_index": i,
            "bin_range": (i / num_bins, (i + 1) / num_bins),
            "count": len(bin_data),
            "avg_confidence": avg_confidence,
            "accuracy": accuracy,
            "calibration_gap": abs(accuracy - avg_confidence),
        })
    
    return ece, bin_stats


def calculate_brier_score(
    predicted_probs: List[float],
    actual_outcomes: List[int],
) -> float:
    """Calculate Brier score (lower is better)."""
    if len(predicted_probs) != len(actual_outcomes):
        raise ValueError("Predictions and outcomes must have same length")
    
    if not predicted_probs:
        return 0.0
    
    brier = sum(
        (p - y) ** 2
        for p, y in zip(predicted_probs, actual_outcomes)
    ) / len(predicted_probs)
    
    return brier


class CalibrationScheduler:
    """
    Automated calibration scheduler.
    
    Periodically evaluates and recalibrates probability predictions
    to maintain accuracy over time.
    """
    
    def __init__(
        self,
        config: Optional[CalibrationConfig] = None,
        prediction_store: Optional[Any] = None,
        outcome_store: Optional[Any] = None,
    ):
        self.config = config or CalibrationConfig()
        self._prediction_store = prediction_store
        self._outcome_store = outcome_store
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._calibrators: Dict[str, Any] = {}
        self._last_run: Optional[datetime] = None
        self._history: List[CalibrationResult] = []
        
        # Default calibrator
        self._platt = PlattScaling()
        self._isotonic = IsotonicRegression()
    
    async def start(self) -> None:
        """Start the calibration scheduler."""
        if self._running:
            logger.warning("calibration_scheduler_already_running")
            return
        
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info(
            "calibration_scheduler_started",
            interval_hours=self.config.interval_hours,
        )
    
    async def stop(self) -> None:
        """Stop the calibration scheduler."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("calibration_scheduler_stopped")
    
    async def _run_loop(self) -> None:
        """Main scheduler loop."""
        while self._running:
            try:
                # Check if it's time to run
                if self._should_run():
                    await self.run_calibration()
                
                # Sleep until next check
                await asyncio.sleep(60 * 60)  # Check every hour
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("calibration_loop_error", error=str(e))
                await asyncio.sleep(60 * 5)  # Wait 5 min on error
    
    def _should_run(self) -> bool:
        """Check if calibration should run now."""
        if self._last_run is None:
            return True
        
        next_run = self._last_run + timedelta(hours=self.config.interval_hours)
        return datetime.utcnow() >= next_run
    
    async def run_calibration(
        self,
        force: bool = False,
    ) -> CalibrationResult:
        """
        Run a calibration cycle.
        
        Args:
            force: Run even if threshold not met
            
        Returns:
            CalibrationResult with metrics
        """
        import uuid
        
        result = CalibrationResult(
            calibration_id=f"cal_{uuid.uuid4().hex[:16]}",
            started_at=datetime.utcnow(),
            status=CalibrationStatus.RUNNING,
        )
        
        try:
            # Fetch historical predictions and outcomes
            predictions, outcomes = await self._fetch_calibration_data()
            
            if len(predictions) < self.config.min_samples_required:
                result.status = CalibrationStatus.SKIPPED
                result.error_message = (
                    f"Insufficient samples: {len(predictions)} < "
                    f"{self.config.min_samples_required}"
                )
                logger.warning(
                    "calibration_skipped_insufficient_data",
                    samples=len(predictions),
                    required=self.config.min_samples_required,
                )
                return result
            
            result.predictions_evaluated = len(predictions)
            
            # Calculate pre-calibration metrics
            ece_before, _ = calculate_calibration_error(predictions, outcomes)
            brier_before = calculate_brier_score(predictions, outcomes)
            
            result.calibration_error_before = ece_before
            result.brier_score_before = brier_before
            
            # Check if recalibration is needed
            if not force and ece_before < self.config.recalibration_threshold:
                result.status = CalibrationStatus.SKIPPED
                result.error_message = (
                    f"Calibration error {ece_before:.4f} below threshold "
                    f"{self.config.recalibration_threshold}"
                )
                logger.info(
                    "calibration_skipped_below_threshold",
                    ece=ece_before,
                    threshold=self.config.recalibration_threshold,
                )
                return result
            
            # Fit calibrators
            self._platt.fit(predictions, outcomes)
            self._isotonic.fit(predictions, outcomes)
            
            # Apply best calibrator
            calibrated = [self._platt.calibrate(p) for p in predictions]
            
            # Calculate post-calibration metrics
            ece_after, _ = calculate_calibration_error(calibrated, outcomes)
            brier_after = calculate_brier_score(calibrated, outcomes)
            
            result.calibration_error_after = ece_after
            result.brier_score_after = brier_after
            
            # Record adjustments
            result.adjustments_made = {
                "platt_a": self._platt.parameters[0],
                "platt_b": self._platt.parameters[1],
            }
            
            # Check for degradation
            if ece_after > ece_before + self.config.degradation_threshold:
                logger.warning(
                    "calibration_degradation_detected",
                    ece_before=ece_before,
                    ece_after=ece_after,
                )
            
            result.status = CalibrationStatus.COMPLETED
            result.completed_at = datetime.utcnow()
            
            logger.info(
                "calibration_completed",
                calibration_id=result.calibration_id,
                predictions_evaluated=result.predictions_evaluated,
                ece_before=ece_before,
                ece_after=ece_after,
                improvement_pct=result.improvement_pct,
            )
            
        except Exception as e:
            result.status = CalibrationStatus.FAILED
            result.error_message = str(e)
            result.completed_at = datetime.utcnow()
            logger.error(
                "calibration_failed",
                calibration_id=result.calibration_id,
                error=str(e),
            )
        
        self._last_run = datetime.utcnow()
        self._history.append(result)
        return result
    
    async def _fetch_calibration_data(
        self,
    ) -> Tuple[List[float], List[int]]:
        """
        Fetch historical predictions and their outcomes.
        
        Returns:
            Tuple of (predicted probabilities, actual outcomes)
        """
        # In production, this fetches from prediction_store and outcome_store
        # For now, return empty lists (to be integrated with actual stores)
        
        if self._prediction_store is None or self._outcome_store is None:
            logger.warning("calibration_stores_not_configured")
            return [], []
        
        # Fetch predictions from lookback period
        cutoff = datetime.utcnow() - timedelta(days=self.config.lookback_days)
        
        predictions = []
        outcomes = []
        
        # This would be implemented based on actual store interfaces
        # predictions = await self._prediction_store.get_predictions_since(cutoff)
        # outcomes = await self._outcome_store.get_outcomes_for(predictions)
        
        return predictions, outcomes
    
    def calibrate_probability(self, prob: float, method: str = "platt") -> float:
        """
        Calibrate a single probability using fitted calibrator.
        
        Args:
            prob: Raw probability to calibrate
            method: "platt" or "isotonic"
            
        Returns:
            Calibrated probability
        """
        if method == "platt":
            return self._platt.calibrate(prob)
        elif method == "isotonic":
            return self._isotonic.calibrate(prob)
        else:
            return prob
    
    def get_calibration_history(
        self,
        limit: int = 10,
    ) -> List[CalibrationResult]:
        """Get recent calibration history."""
        return self._history[-limit:]
    
    @property
    def is_running(self) -> bool:
        """Check if scheduler is running."""
        return self._running
