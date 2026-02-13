"""
Confidence Calibration Engine.

Implements:
- Platt Scaling (logistic regression on predicted vs. actual)
- Bucket-based calibration (empirical frequency in bins)
- Expected Calibration Error (ECE) metric
- Reliability diagram data

GOAL: When the system says "80% confident", the event should occur ~80% of the time.
"""

import math
from dataclasses import dataclass, field
from typing import Optional

import structlog

logger = structlog.get_logger(__name__)

# ── Configuration ─────────────────────────────────────────────────────────

N_CALIBRATION_BINS: int = 10     # Number of bins for ECE/reliability
MIN_SAMPLES_FOR_CALIBRATION: int = 30  # Minimum predictions to calibrate


@dataclass(frozen=True)
class CalibrationBin:
    """A single bin in a reliability diagram."""
    bin_lower: float
    bin_upper: float
    avg_predicted: float      # Average predicted probability in this bin
    avg_actual: float         # Average actual outcome frequency
    count: int                # Number of predictions in this bin
    gap: float                # |avg_predicted - avg_actual|


@dataclass(frozen=True)
class CalibrationReport:
    """Full calibration assessment."""
    ece: float                          # Expected Calibration Error (0=perfect)
    mce: float                          # Maximum Calibration Error
    brier_score: float                  # Brier score (lower=better)
    bins: list[CalibrationBin]          # Reliability diagram bins
    n_predictions: int
    is_calibrated: bool                 # ECE < 0.05
    overconfident: bool                 # System predicts too high
    underconfident: bool                # System predicts too low
    recommendation: str                 # Human-readable advice


@dataclass
class PlattScaler:
    """
    Platt Scaling — logistic calibration of predicted probabilities.

    Fits: P_calibrated = 1 / (1 + exp(A × logit(P_raw) + B))

    Uses gradient descent on log-loss to find optimal A, B.
    """
    a: float = 1.0   # Slope
    b: float = 0.0   # Intercept
    is_fitted: bool = False

    def fit(
        self,
        predicted: list[float],
        actual: list[int],
        learning_rate: float = 0.01,
        n_iterations: int = 100,
    ) -> None:
        """
        Fit Platt scaling parameters using gradient descent.

        Args:
            predicted: Raw predicted probabilities
            actual: Actual outcomes (0 or 1)
        """
        if len(predicted) < MIN_SAMPLES_FOR_CALIBRATION:
            logger.warning(
                "calibration_insufficient_data",
                n_samples=len(predicted),
                required=MIN_SAMPLES_FOR_CALIBRATION,
            )
            return

        a, b = 1.0, 0.0

        for _ in range(n_iterations):
            grad_a, grad_b = 0.0, 0.0
            n = len(predicted)

            for p, y in zip(predicted, actual):
                # Logit with clipping to avoid log(0)
                p_clipped = max(1e-7, min(1 - 1e-7, p))
                logit = math.log(p_clipped / (1 - p_clipped))

                z = a * logit + b
                sigmoid = 1.0 / (1.0 + math.exp(-z))

                error = sigmoid - y
                grad_a += error * logit / n
                grad_b += error / n

            a -= learning_rate * grad_a
            b -= learning_rate * grad_b

        self.a = a
        self.b = b
        self.is_fitted = True
        logger.info("platt_scaling_fitted", a=round(a, 4), b=round(b, 4))

    def calibrate(self, raw_probability: float) -> float:
        """Apply Platt scaling to a raw probability."""
        if not self.is_fitted:
            return raw_probability

        p_clipped = max(1e-7, min(1 - 1e-7, raw_probability))
        logit = math.log(p_clipped / (1 - p_clipped))
        z = self.a * logit + self.b
        return 1.0 / (1.0 + math.exp(-z))


class CalibrationEngine:
    """
    Assess and improve the calibration of predicted probabilities.
    """

    def __init__(self, n_bins: int = N_CALIBRATION_BINS):
        self.n_bins = n_bins
        self.scaler = PlattScaler()

    def assess(
        self,
        predicted: list[float],
        actual: list[int],
    ) -> CalibrationReport:
        """
        Compute calibration metrics.

        Args:
            predicted: Predicted probabilities (0-1)
            actual: Actual outcomes (0 or 1)

        Returns:
            CalibrationReport with ECE, MCE, Brier score, and bins.
        """
        n = len(predicted)
        if n == 0:
            return CalibrationReport(
                ece=0.0, mce=0.0, brier_score=0.0,
                bins=[], n_predictions=0,
                is_calibrated=False, overconfident=False, underconfident=False,
                recommendation="No predictions to calibrate.",
            )

        # Bin predictions
        bins: list[CalibrationBin] = []
        bin_width = 1.0 / self.n_bins
        ece = 0.0
        mce = 0.0
        total_over = 0.0
        total_under = 0.0

        for i in range(self.n_bins):
            lower = i * bin_width
            upper = (i + 1) * bin_width

            indices = [
                j for j in range(n)
                if lower <= predicted[j] < upper or (i == self.n_bins - 1 and predicted[j] == 1.0)
            ]

            if not indices:
                bins.append(CalibrationBin(
                    bin_lower=lower, bin_upper=upper,
                    avg_predicted=0.0, avg_actual=0.0, count=0, gap=0.0,
                ))
                continue

            avg_pred = sum(predicted[j] for j in indices) / len(indices)
            avg_act = sum(actual[j] for j in indices) / len(indices)
            gap = abs(avg_pred - avg_act)

            ece += gap * len(indices) / n
            mce = max(mce, gap)

            if avg_pred > avg_act:
                total_over += gap * len(indices)
            else:
                total_under += gap * len(indices)

            bins.append(CalibrationBin(
                bin_lower=round(lower, 2),
                bin_upper=round(upper, 2),
                avg_predicted=round(avg_pred, 4),
                avg_actual=round(avg_act, 4),
                count=len(indices),
                gap=round(gap, 4),
            ))

        # Brier score
        brier = sum((predicted[j] - actual[j]) ** 2 for j in range(n)) / n

        is_calibrated = ece < 0.05
        overconfident = total_over > total_under * 1.5
        underconfident = total_under > total_over * 1.5

        if is_calibrated:
            recommendation = "Predictions are well-calibrated. Continue monitoring."
        elif overconfident:
            recommendation = (
                f"System is overconfident (ECE={ece:.3f}). "
                "Consider applying Platt scaling to reduce confidence scores."
            )
        elif underconfident:
            recommendation = (
                f"System is underconfident (ECE={ece:.3f}). "
                "Consider recalibrating upward."
            )
        else:
            recommendation = (
                f"Calibration needs improvement (ECE={ece:.3f}). "
                "Collect more outcome data and retrain."
            )

        return CalibrationReport(
            ece=round(ece, 4),
            mce=round(mce, 4),
            brier_score=round(brier, 4),
            bins=bins,
            n_predictions=n,
            is_calibrated=is_calibrated,
            overconfident=overconfident,
            underconfident=underconfident,
            recommendation=recommendation,
        )

    def fit_scaler(self, predicted: list[float], actual: list[int]) -> None:
        """Train the Platt scaler on historical predictions."""
        self.scaler.fit(predicted, actual)

    def calibrate(self, raw_probability: float) -> float:
        """Apply learned calibration to a raw probability."""
        return self.scaler.calibrate(raw_probability)
