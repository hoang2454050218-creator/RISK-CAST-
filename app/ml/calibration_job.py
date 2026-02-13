"""
Automatic Calibration Recalibration Job.

Implements A3.3 Probability Calibration requirements:
- Scheduled recalibration of confidence models
- ECE (Expected Calibration Error) monitoring
- Brier score tracking
- Automatic model updates when calibration degrades

A3 COMPLIANCE: Add automatic calibration recalibration job.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import structlog

logger = structlog.get_logger(__name__)


# ============================================================================
# CALIBRATION METRICS
# ============================================================================


class CalibrationQuality(str, Enum):
    """Calibration quality levels."""
    EXCELLENT = "excellent"   # ECE < 0.02
    GOOD = "good"             # ECE < 0.05
    ACCEPTABLE = "acceptable"  # ECE < 0.10
    POOR = "poor"             # ECE < 0.15
    CRITICAL = "critical"     # ECE >= 0.15


@dataclass
class CalibrationMetrics:
    """Calibration metrics for a model."""
    
    model_name: str
    timestamp: datetime
    
    # Core metrics
    ece: float  # Expected Calibration Error
    mce: float  # Maximum Calibration Error
    brier_score: float
    
    # Reliability diagram data
    bin_accuracies: List[float] = field(default_factory=list)
    bin_confidences: List[float] = field(default_factory=list)
    bin_counts: List[int] = field(default_factory=list)
    
    # Sample info
    sample_count: int = 0
    
    @property
    def quality(self) -> CalibrationQuality:
        """Assess calibration quality."""
        if self.ece < 0.02:
            return CalibrationQuality.EXCELLENT
        elif self.ece < 0.05:
            return CalibrationQuality.GOOD
        elif self.ece < 0.10:
            return CalibrationQuality.ACCEPTABLE
        elif self.ece < 0.15:
            return CalibrationQuality.POOR
        else:
            return CalibrationQuality.CRITICAL
    
    @property
    def needs_recalibration(self) -> bool:
        """Check if recalibration is needed."""
        return self.ece >= 0.10 or self.brier_score >= 0.25


# ============================================================================
# CALIBRATION CALCULATOR
# ============================================================================


class CalibrationCalculator:
    """
    Calculate calibration metrics.
    
    Uses reliability diagrams and proper scoring rules
    to assess probability calibration quality.
    """
    
    def __init__(self, n_bins: int = 10):
        self.n_bins = n_bins
    
    def calculate_metrics(
        self,
        predictions: List[float],
        actuals: List[int],
        model_name: str,
    ) -> CalibrationMetrics:
        """
        Calculate full calibration metrics.
        
        Args:
            predictions: Predicted probabilities [0, 1]
            actuals: Actual outcomes (0 or 1)
            model_name: Name of the model
            
        Returns:
            CalibrationMetrics with all metrics
        """
        if len(predictions) == 0:
            return CalibrationMetrics(
                model_name=model_name,
                timestamp=datetime.utcnow(),
                ece=0.0,
                mce=0.0,
                brier_score=0.0,
                sample_count=0,
            )
        
        predictions = np.array(predictions)
        actuals = np.array(actuals)
        
        # Calculate ECE and reliability diagram
        ece, mce, bin_accs, bin_confs, bin_counts = self._calculate_ece(
            predictions, actuals
        )
        
        # Calculate Brier score
        brier = self._calculate_brier(predictions, actuals)
        
        return CalibrationMetrics(
            model_name=model_name,
            timestamp=datetime.utcnow(),
            ece=float(ece),
            mce=float(mce),
            brier_score=float(brier),
            bin_accuracies=bin_accs.tolist() if hasattr(bin_accs, 'tolist') else list(bin_accs),
            bin_confidences=bin_confs.tolist() if hasattr(bin_confs, 'tolist') else list(bin_confs),
            bin_counts=bin_counts.tolist() if hasattr(bin_counts, 'tolist') else list(bin_counts),
            sample_count=len(predictions),
        )
    
    def _calculate_ece(
        self,
        predictions: np.ndarray,
        actuals: np.ndarray,
    ) -> Tuple[float, float, np.ndarray, np.ndarray, np.ndarray]:
        """
        Calculate Expected Calibration Error.
        
        Returns:
            (ece, mce, bin_accuracies, bin_confidences, bin_counts)
        """
        bin_boundaries = np.linspace(0, 1, self.n_bins + 1)
        bin_accuracies = np.zeros(self.n_bins)
        bin_confidences = np.zeros(self.n_bins)
        bin_counts = np.zeros(self.n_bins, dtype=int)
        
        for i in range(self.n_bins):
            in_bin = (predictions > bin_boundaries[i]) & (predictions <= bin_boundaries[i + 1])
            bin_counts[i] = np.sum(in_bin)
            
            if bin_counts[i] > 0:
                bin_accuracies[i] = np.mean(actuals[in_bin])
                bin_confidences[i] = np.mean(predictions[in_bin])
        
        # ECE: weighted average of |accuracy - confidence|
        total_samples = np.sum(bin_counts)
        if total_samples == 0:
            return 0.0, 0.0, bin_accuracies, bin_confidences, bin_counts
        
        weights = bin_counts / total_samples
        calibration_errors = np.abs(bin_accuracies - bin_confidences)
        
        ece = np.sum(weights * calibration_errors)
        mce = np.max(calibration_errors[bin_counts > 0]) if np.any(bin_counts > 0) else 0.0
        
        return ece, mce, bin_accuracies, bin_confidences, bin_counts
    
    def _calculate_brier(
        self,
        predictions: np.ndarray,
        actuals: np.ndarray,
    ) -> float:
        """Calculate Brier score (mean squared error)."""
        return float(np.mean((predictions - actuals) ** 2))


# ============================================================================
# CALIBRATOR
# ============================================================================


class ProbabilityCalibrator:
    """
    Calibrate probability predictions.
    
    Supports multiple calibration methods:
    - Platt scaling (logistic regression)
    - Isotonic regression
    - Temperature scaling
    """
    
    def __init__(self, method: str = "isotonic"):
        """
        Initialize calibrator.
        
        Args:
            method: Calibration method ("platt", "isotonic", "temperature")
        """
        self.method = method
        self._model = None
        self._fitted = False
    
    def fit(
        self,
        predictions: List[float],
        actuals: List[int],
    ) -> "ProbabilityCalibrator":
        """
        Fit calibrator to data.
        
        Args:
            predictions: Uncalibrated predictions
            actuals: Actual outcomes
            
        Returns:
            self
        """
        predictions = np.array(predictions).reshape(-1, 1)
        actuals = np.array(actuals)
        
        if self.method == "platt":
            from sklearn.linear_model import LogisticRegression
            self._model = LogisticRegression()
            self._model.fit(predictions, actuals)
            
        elif self.method == "isotonic":
            from sklearn.isotonic import IsotonicRegression
            self._model = IsotonicRegression(out_of_bounds="clip")
            self._model.fit(predictions.ravel(), actuals)
            
        elif self.method == "temperature":
            # Temperature scaling - find optimal temperature
            self._model = self._fit_temperature(predictions.ravel(), actuals)
            
        self._fitted = True
        logger.info(
            "calibrator_fitted",
            method=self.method,
            samples=len(actuals),
        )
        
        return self
    
    def calibrate(self, predictions: List[float]) -> List[float]:
        """
        Calibrate predictions.
        
        Args:
            predictions: Uncalibrated predictions
            
        Returns:
            Calibrated predictions
        """
        if not self._fitted:
            return predictions
        
        predictions = np.array(predictions)
        
        if self.method == "platt":
            calibrated = self._model.predict_proba(predictions.reshape(-1, 1))[:, 1]
        elif self.method == "isotonic":
            calibrated = self._model.predict(predictions)
        elif self.method == "temperature":
            calibrated = self._apply_temperature(predictions, self._model)
        else:
            calibrated = predictions
        
        return calibrated.tolist()
    
    def _fit_temperature(
        self,
        predictions: np.ndarray,
        actuals: np.ndarray,
    ) -> float:
        """Fit temperature scaling parameter."""
        from scipy.optimize import minimize_scalar
        
        def nll_loss(temperature):
            scaled = self._apply_temperature(predictions, temperature)
            # Add small epsilon for numerical stability
            eps = 1e-10
            scaled = np.clip(scaled, eps, 1 - eps)
            return -np.mean(
                actuals * np.log(scaled) + (1 - actuals) * np.log(1 - scaled)
            )
        
        result = minimize_scalar(nll_loss, bounds=(0.1, 10.0), method="bounded")
        return result.x
    
    def _apply_temperature(
        self,
        predictions: np.ndarray,
        temperature: float,
    ) -> np.ndarray:
        """Apply temperature scaling."""
        # Convert to logits, scale, convert back
        eps = 1e-10
        predictions = np.clip(predictions, eps, 1 - eps)
        logits = np.log(predictions / (1 - predictions))
        scaled_logits = logits / temperature
        return 1 / (1 + np.exp(-scaled_logits))


# ============================================================================
# CALIBRATION HISTORY
# ============================================================================


@dataclass
class CalibrationHistory:
    """Track calibration history for a model."""
    
    model_name: str
    history: List[CalibrationMetrics] = field(default_factory=list)
    max_history: int = 100
    
    def add(self, metrics: CalibrationMetrics):
        """Add metrics to history."""
        self.history.append(metrics)
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]
    
    def get_trend(self, metric: str = "ece", window: int = 10) -> List[float]:
        """Get trend for a metric."""
        values = [getattr(m, metric) for m in self.history[-window:]]
        return values
    
    def is_degrading(self, window: int = 5) -> bool:
        """Check if calibration is degrading over time."""
        if len(self.history) < window:
            return False
        
        recent_ece = np.mean([m.ece for m in self.history[-window:]])
        previous_ece = np.mean([m.ece for m in self.history[-2*window:-window]])
        
        # Degrading if recent ECE is significantly worse
        return recent_ece > previous_ece * 1.2


# ============================================================================
# CALIBRATION RECALIBRATION JOB
# ============================================================================


class CalibrationRecalibrationJob:
    """
    Scheduled job for automatic calibration recalibration.
    
    Monitors calibration quality and triggers recalibration when needed.
    """
    
    def __init__(
        self,
        outcome_repository=None,
        model_serving=None,
        run_interval_hours: int = 6,
        min_samples: int = 100,
    ):
        """
        Initialize recalibration job.
        
        Args:
            outcome_repository: Repository for decision outcomes
            model_serving: Model serving service
            run_interval_hours: How often to check calibration
            min_samples: Minimum samples needed for recalibration
        """
        self._outcome_repo = outcome_repository
        self._model_serving = model_serving
        self._interval = timedelta(hours=run_interval_hours)
        self._min_samples = min_samples
        
        self._calculator = CalibrationCalculator()
        self._histories: Dict[str, CalibrationHistory] = {}
        self._calibrators: Dict[str, ProbabilityCalibrator] = {}
        
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._last_run: Optional[datetime] = None
    
    async def start(self):
        """Start the recalibration job."""
        if self._running:
            return
        
        self._running = True
        self._task = asyncio.create_task(
            self._run_loop(),
            name="calibration_recalibration"
        )
        logger.info(
            "calibration_job_started",
            interval_hours=self._interval.total_seconds() / 3600,
        )
    
    async def stop(self):
        """Stop the recalibration job."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("calibration_job_stopped")
    
    async def _run_loop(self):
        """Main recalibration loop."""
        while self._running:
            try:
                await self.run_check()
            except Exception as e:
                logger.error("calibration_check_error", error=str(e))
            
            await asyncio.sleep(self._interval.total_seconds())
    
    async def run_check(self) -> Dict[str, CalibrationMetrics]:
        """
        Run calibration check for all models.
        
        Returns:
            Dict of model name to calibration metrics
        """
        logger.info("calibration_check_started")
        
        results = {}
        models_to_check = ["delay_predictor", "cost_predictor", "confidence_model"]
        
        for model_name in models_to_check:
            try:
                metrics = await self._check_model(model_name)
                results[model_name] = metrics
                
                # Check if recalibration needed
                if metrics and metrics.needs_recalibration:
                    logger.warning(
                        "recalibration_needed",
                        model=model_name,
                        ece=metrics.ece,
                        quality=metrics.quality.value,
                    )
                    await self._trigger_recalibration(model_name)
                    
            except Exception as e:
                logger.error(
                    "model_calibration_check_failed",
                    model=model_name,
                    error=str(e),
                )
        
        self._last_run = datetime.utcnow()
        logger.info(
            "calibration_check_completed",
            models_checked=len(results),
        )
        
        return results
    
    async def _check_model(self, model_name: str) -> Optional[CalibrationMetrics]:
        """Check calibration for a specific model."""
        # Get recent predictions and outcomes
        if not self._outcome_repo:
            logger.warning("no_outcome_repo_skipping_calibration", model=model_name)
            return None
        
        outcomes = await self._outcome_repo.get_recent(days=30)
        
        if len(outcomes) < self._min_samples:
            logger.info(
                "insufficient_samples_for_calibration",
                model=model_name,
                samples=len(outcomes),
                required=self._min_samples,
            )
            return None
        
        # Extract predictions and actuals based on model type
        predictions, actuals = self._extract_predictions_actuals(
            outcomes, model_name
        )
        
        if len(predictions) == 0:
            return None
        
        # Calculate metrics
        metrics = self._calculator.calculate_metrics(
            predictions, actuals, model_name
        )
        
        # Update history
        if model_name not in self._histories:
            self._histories[model_name] = CalibrationHistory(model_name)
        self._histories[model_name].add(metrics)
        
        logger.info(
            "calibration_metrics_calculated",
            model=model_name,
            ece=metrics.ece,
            brier=metrics.brier_score,
            quality=metrics.quality.value,
            samples=metrics.sample_count,
        )
        
        return metrics
    
    def _extract_predictions_actuals(
        self,
        outcomes: List[Any],
        model_name: str,
    ) -> Tuple[List[float], List[int]]:
        """Extract predictions and actuals from outcomes."""
        predictions = []
        actuals = []
        
        for outcome in outcomes:
            if hasattr(outcome, 'confidence_score') and hasattr(outcome, 'was_accurate'):
                if model_name == "confidence_model":
                    # Confidence model: confidence vs accuracy
                    predictions.append(outcome.confidence_score)
                    actuals.append(1 if outcome.was_accurate else 0)
                elif model_name == "delay_predictor":
                    # Delay predictor: check if delay prediction was in range
                    if hasattr(outcome, 'predicted_delay') and hasattr(outcome, 'actual_delay'):
                        if outcome.predicted_delay is not None and outcome.actual_delay is not None:
                            # Convert to binary: was delay prediction accurate within 20%?
                            error = abs(outcome.predicted_delay - outcome.actual_delay)
                            threshold = max(1, outcome.predicted_delay * 0.2)
                            accurate = 1 if error <= threshold else 0
                            predictions.append(outcome.confidence_score)
                            actuals.append(accurate)
        
        return predictions, actuals
    
    async def _trigger_recalibration(self, model_name: str):
        """Trigger recalibration for a model."""
        if not self._outcome_repo:
            return
        
        logger.info("recalibration_triggered", model=model_name)
        
        # Get training data
        outcomes = await self._outcome_repo.get_recent(days=90)
        predictions, actuals = self._extract_predictions_actuals(outcomes, model_name)
        
        if len(predictions) < self._min_samples:
            logger.warning(
                "insufficient_data_for_recalibration",
                model=model_name,
                samples=len(predictions),
            )
            return
        
        # Train new calibrator
        calibrator = ProbabilityCalibrator(method="isotonic")
        calibrator.fit(predictions, actuals)
        
        self._calibrators[model_name] = calibrator
        
        # Verify improvement
        calibrated = calibrator.calibrate(predictions)
        new_metrics = self._calculator.calculate_metrics(
            calibrated, actuals, f"{model_name}_calibrated"
        )
        
        logger.info(
            "recalibration_completed",
            model=model_name,
            new_ece=new_metrics.ece,
            new_quality=new_metrics.quality.value,
        )
    
    def get_calibrator(self, model_name: str) -> Optional[ProbabilityCalibrator]:
        """Get calibrator for a model."""
        return self._calibrators.get(model_name)
    
    def get_history(self, model_name: str) -> Optional[CalibrationHistory]:
        """Get calibration history for a model."""
        return self._histories.get(model_name)
    
    async def run_now(self) -> Dict[str, CalibrationMetrics]:
        """Run calibration check immediately."""
        return await self.run_check()


# ============================================================================
# SINGLETON
# ============================================================================


_calibration_job: Optional[CalibrationRecalibrationJob] = None


def get_calibration_job(
    outcome_repository=None,
    model_serving=None,
) -> CalibrationRecalibrationJob:
    """Get global calibration job."""
    global _calibration_job
    if _calibration_job is None:
        _calibration_job = CalibrationRecalibrationJob(
            outcome_repository=outcome_repository,
            model_serving=model_serving,
        )
    return _calibration_job
