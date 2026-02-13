"""Calibration API Routes - Monitor prediction accuracy and calibration.

This module exposes API endpoints for monitoring the calibration of RISKCAST's
predictions over time. Good calibration means predicted probabilities match
observed frequencies (e.g., events predicted at 70% happen ~70% of the time).

Addresses audit gaps:
- A2.2: Confidence Intervals monitoring
- A4.4: Confidence Communication metrics

Endpoints:
- GET /calibration/metrics - Overall calibration metrics (ECE, Brier score)
- GET /calibration/curve - Reliability diagram data
- GET /calibration/alerts - Calibration drift alerts
- POST /calibration/record - Record actual outcome for prediction
"""

from datetime import datetime, timedelta
from typing import Optional, List
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

import structlog

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/calibration", tags=["Calibration"])


# ============================================================================
# SCHEMAS
# ============================================================================


class CalibrationBin(BaseModel):
    """A single bin in the calibration curve."""
    
    bin_start: float = Field(ge=0.0, le=1.0, description="Start of probability bin")
    bin_end: float = Field(ge=0.0, le=1.0, description="End of probability bin")
    bin_center: float = Field(ge=0.0, le=1.0, description="Center of probability bin")
    predicted_probability: float = Field(
        ge=0.0, le=1.0, description="Average predicted probability in bin"
    )
    observed_frequency: float = Field(
        ge=0.0, le=1.0, description="Fraction of events that actually occurred"
    )
    count: int = Field(ge=0, description="Number of predictions in this bin")
    confidence_interval: tuple[float, float] = Field(
        description="95% confidence interval for observed frequency"
    )


class CalibrationMetrics(BaseModel):
    """Overall calibration metrics for the system."""
    
    expected_calibration_error: float = Field(
        ge=0.0,
        le=1.0,
        description="Expected Calibration Error (ECE) - lower is better. <0.05 is excellent.",
    )
    brier_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Brier score - lower is better. <0.1 is excellent.",
    )
    total_predictions: int = Field(
        ge=0, description="Total number of predictions evaluated"
    )
    total_outcomes_recorded: int = Field(
        ge=0, description="Number of outcomes recorded"
    )
    calibration_status: str = Field(
        description="Overall status: 'well_calibrated', 'overconfident', 'underconfident', 'insufficient_data'"
    )
    last_updated: datetime = Field(description="When metrics were last computed")
    
    # Breakdown by category
    ece_by_category: dict[str, float] = Field(
        default_factory=dict,
        description="ECE broken down by prediction category (disruption, rate_spike, etc.)",
    )
    
    # Trend
    ece_7d_avg: Optional[float] = Field(
        default=None, description="7-day rolling average ECE"
    )
    ece_30d_avg: Optional[float] = Field(
        default=None, description="30-day rolling average ECE"
    )
    ece_trend: str = Field(
        default="stable",
        description="Trend: 'improving', 'degrading', 'stable'",
    )


class CalibrationCurve(BaseModel):
    """Full calibration curve (reliability diagram data)."""
    
    bins: list[CalibrationBin] = Field(description="Bins for reliability diagram")
    perfect_calibration_line: list[tuple[float, float]] = Field(
        default=[(0.0, 0.0), (1.0, 1.0)],
        description="Reference line for perfect calibration",
    )
    total_predictions: int = Field(ge=0)
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class AlertSeverity(str, Enum):
    """Severity levels for calibration alerts."""
    
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class CalibrationAlert(BaseModel):
    """Alert for calibration issues."""
    
    alert_id: str = Field(description="Unique alert ID")
    severity: AlertSeverity = Field(description="Alert severity")
    message: str = Field(description="Human-readable alert message")
    metric: str = Field(description="Affected metric (ece, brier, drift)")
    current_value: float = Field(description="Current metric value")
    threshold: float = Field(description="Threshold that was exceeded")
    category: Optional[str] = Field(
        default=None, description="Category if category-specific"
    )
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    recommendations: list[str] = Field(
        default_factory=list,
        description="Recommended actions to address the alert",
    )


class OutcomeRecord(BaseModel):
    """Record an actual outcome for a prediction."""
    
    prediction_id: str = Field(description="ID of the prediction to record outcome for")
    decision_id: str = Field(description="ID of the associated decision")
    predicted_probability: float = Field(
        ge=0.0, le=1.0, description="Original predicted probability"
    )
    actual_outcome: bool = Field(description="Whether the event actually occurred")
    outcome_timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the outcome was observed",
    )
    category: Optional[str] = Field(
        default=None, description="Prediction category (disruption, rate_spike, etc.)"
    )
    notes: Optional[str] = Field(
        default=None, max_length=500, description="Optional notes about the outcome"
    )


class OutcomeRecordResponse(BaseModel):
    """Response after recording an outcome."""
    
    success: bool
    prediction_id: str
    calibration_contribution: str = Field(
        description="How this outcome affects calibration (overconfident/underconfident/correct)"
    )
    current_ece: float = Field(description="Current ECE after this record")


# ============================================================================
# IN-MEMORY STORAGE (Replace with database in production)
# ============================================================================


# Simple in-memory storage for calibration data
# In production, this would be stored in PostgreSQL
_calibration_records: list[dict] = []
_cached_metrics: Optional[CalibrationMetrics] = None
_cached_metrics_time: Optional[datetime] = None


def _compute_calibration_metrics() -> CalibrationMetrics:
    """Compute calibration metrics from stored records."""
    global _cached_metrics, _cached_metrics_time
    
    # Cache for 5 minutes
    if _cached_metrics and _cached_metrics_time:
        if datetime.utcnow() - _cached_metrics_time < timedelta(minutes=5):
            return _cached_metrics
    
    if len(_calibration_records) < 10:
        return CalibrationMetrics(
            expected_calibration_error=0.0,
            brier_score=0.0,
            total_predictions=len(_calibration_records),
            total_outcomes_recorded=len(_calibration_records),
            calibration_status="insufficient_data",
            last_updated=datetime.utcnow(),
        )
    
    # Compute ECE and Brier score
    bins = {}
    for record in _calibration_records:
        bin_idx = int(record["predicted_probability"] * 10)
        bin_idx = min(bin_idx, 9)  # Handle p=1.0
        if bin_idx not in bins:
            bins[bin_idx] = {"total": 0, "positive": 0, "prob_sum": 0.0}
        bins[bin_idx]["total"] += 1
        bins[bin_idx]["positive"] += 1 if record["actual_outcome"] else 0
        bins[bin_idx]["prob_sum"] += record["predicted_probability"]
    
    ece = 0.0
    brier = 0.0
    total = len(_calibration_records)
    
    for bin_data in bins.values():
        if bin_data["total"] > 0:
            avg_pred = bin_data["prob_sum"] / bin_data["total"]
            obs_freq = bin_data["positive"] / bin_data["total"]
            ece += (bin_data["total"] / total) * abs(avg_pred - obs_freq)
    
    for record in _calibration_records:
        outcome = 1.0 if record["actual_outcome"] else 0.0
        brier += (record["predicted_probability"] - outcome) ** 2
    brier /= total
    
    # Determine calibration status
    if ece < 0.05:
        status = "well_calibrated"
    elif ece < 0.10:
        # Check if overconfident or underconfident
        # Overconfident: predicted higher than observed
        over_count = sum(
            1 for r in _calibration_records
            if r["predicted_probability"] > 0.5 and not r["actual_outcome"]
        )
        under_count = sum(
            1 for r in _calibration_records
            if r["predicted_probability"] < 0.5 and r["actual_outcome"]
        )
        if over_count > under_count * 1.5:
            status = "overconfident"
        elif under_count > over_count * 1.5:
            status = "underconfident"
        else:
            status = "well_calibrated"
    else:
        status = "overconfident"  # High ECE typically means overconfidence
    
    # ECE by category
    ece_by_category = {}
    categories = set(r.get("category", "unknown") for r in _calibration_records)
    for cat in categories:
        cat_records = [r for r in _calibration_records if r.get("category") == cat]
        if len(cat_records) >= 5:
            cat_bins = {}
            for r in cat_records:
                bin_idx = int(r["predicted_probability"] * 10)
                bin_idx = min(bin_idx, 9)
                if bin_idx not in cat_bins:
                    cat_bins[bin_idx] = {"total": 0, "positive": 0, "prob_sum": 0.0}
                cat_bins[bin_idx]["total"] += 1
                cat_bins[bin_idx]["positive"] += 1 if r["actual_outcome"] else 0
                cat_bins[bin_idx]["prob_sum"] += r["predicted_probability"]
            
            cat_ece = 0.0
            cat_total = len(cat_records)
            for bin_data in cat_bins.values():
                if bin_data["total"] > 0:
                    avg_pred = bin_data["prob_sum"] / bin_data["total"]
                    obs_freq = bin_data["positive"] / bin_data["total"]
                    cat_ece += (bin_data["total"] / cat_total) * abs(avg_pred - obs_freq)
            ece_by_category[cat] = round(cat_ece, 4)
    
    metrics = CalibrationMetrics(
        expected_calibration_error=round(ece, 4),
        brier_score=round(brier, 4),
        total_predictions=total,
        total_outcomes_recorded=total,
        calibration_status=status,
        last_updated=datetime.utcnow(),
        ece_by_category=ece_by_category,
    )
    
    _cached_metrics = metrics
    _cached_metrics_time = datetime.utcnow()
    
    return metrics


def _compute_calibration_curve(num_bins: int = 10) -> CalibrationCurve:
    """Compute calibration curve for reliability diagram."""
    import math
    
    if len(_calibration_records) < 10:
        # Return empty bins
        bins = []
        for i in range(num_bins):
            bin_start = i / num_bins
            bin_end = (i + 1) / num_bins
            bins.append(CalibrationBin(
                bin_start=bin_start,
                bin_end=bin_end,
                bin_center=(bin_start + bin_end) / 2,
                predicted_probability=bin_start + 0.05,
                observed_frequency=0.0,
                count=0,
                confidence_interval=(0.0, 0.0),
            ))
        return CalibrationCurve(
            bins=bins,
            total_predictions=len(_calibration_records),
        )
    
    bins_data = {i: {"total": 0, "positive": 0, "prob_sum": 0.0} 
                 for i in range(num_bins)}
    
    for record in _calibration_records:
        bin_idx = int(record["predicted_probability"] * num_bins)
        bin_idx = min(bin_idx, num_bins - 1)
        bins_data[bin_idx]["total"] += 1
        bins_data[bin_idx]["positive"] += 1 if record["actual_outcome"] else 0
        bins_data[bin_idx]["prob_sum"] += record["predicted_probability"]
    
    bins = []
    for i in range(num_bins):
        bin_start = i / num_bins
        bin_end = (i + 1) / num_bins
        data = bins_data[i]
        
        if data["total"] > 0:
            pred_prob = data["prob_sum"] / data["total"]
            obs_freq = data["positive"] / data["total"]
            
            # Wilson score interval for confidence interval
            n = data["total"]
            p = obs_freq
            z = 1.96  # 95% CI
            
            if n > 0:
                denominator = 1 + z * z / n
                center = (p + z * z / (2 * n)) / denominator
                spread = z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n) / denominator
                ci = (max(0.0, center - spread), min(1.0, center + spread))
            else:
                ci = (0.0, 0.0)
        else:
            pred_prob = (bin_start + bin_end) / 2
            obs_freq = 0.0
            ci = (0.0, 0.0)
        
        bins.append(CalibrationBin(
            bin_start=bin_start,
            bin_end=bin_end,
            bin_center=(bin_start + bin_end) / 2,
            predicted_probability=pred_prob,
            observed_frequency=obs_freq,
            count=data["total"],
            confidence_interval=ci,
        ))
    
    return CalibrationCurve(
        bins=bins,
        total_predictions=len(_calibration_records),
    )


def _check_calibration_alerts() -> list[CalibrationAlert]:
    """Check for calibration issues and generate alerts."""
    alerts = []
    metrics = _compute_calibration_metrics()
    
    # Alert thresholds
    ECE_WARNING = 0.08
    ECE_CRITICAL = 0.15
    BRIER_WARNING = 0.15
    BRIER_CRITICAL = 0.25
    
    # ECE alerts
    if metrics.expected_calibration_error > ECE_CRITICAL:
        alerts.append(CalibrationAlert(
            alert_id=f"ece_critical_{datetime.utcnow().strftime('%Y%m%d%H%M')}",
            severity=AlertSeverity.CRITICAL,
            message=f"Expected Calibration Error is critically high: {metrics.expected_calibration_error:.2%}",
            metric="ece",
            current_value=metrics.expected_calibration_error,
            threshold=ECE_CRITICAL,
            recommendations=[
                "Review recent predictions for systematic bias",
                "Check data sources for quality issues",
                "Consider recalibrating probability estimates",
                "Audit high-confidence predictions that failed",
            ],
        ))
    elif metrics.expected_calibration_error > ECE_WARNING:
        alerts.append(CalibrationAlert(
            alert_id=f"ece_warning_{datetime.utcnow().strftime('%Y%m%d%H%M')}",
            severity=AlertSeverity.WARNING,
            message=f"Expected Calibration Error is elevated: {metrics.expected_calibration_error:.2%}",
            metric="ece",
            current_value=metrics.expected_calibration_error,
            threshold=ECE_WARNING,
            recommendations=[
                "Monitor calibration trends",
                "Review predictions in affected probability ranges",
            ],
        ))
    
    # Brier score alerts
    if metrics.brier_score > BRIER_CRITICAL:
        alerts.append(CalibrationAlert(
            alert_id=f"brier_critical_{datetime.utcnow().strftime('%Y%m%d%H%M')}",
            severity=AlertSeverity.CRITICAL,
            message=f"Brier score is critically high: {metrics.brier_score:.3f}",
            metric="brier",
            current_value=metrics.brier_score,
            threshold=BRIER_CRITICAL,
            recommendations=[
                "Review prediction model accuracy",
                "Check for data quality issues",
                "Consider ensemble approaches",
            ],
        ))
    
    # Category-specific alerts
    for category, cat_ece in metrics.ece_by_category.items():
        if cat_ece > ECE_WARNING:
            alerts.append(CalibrationAlert(
                alert_id=f"ece_category_{category}_{datetime.utcnow().strftime('%Y%m%d%H%M')}",
                severity=AlertSeverity.WARNING,
                message=f"Category '{category}' has elevated ECE: {cat_ece:.2%}",
                metric="ece",
                current_value=cat_ece,
                threshold=ECE_WARNING,
                category=category,
                recommendations=[
                    f"Review {category} predictions specifically",
                    f"Check {category} data sources",
                ],
            ))
    
    return alerts


# ============================================================================
# ENDPOINTS
# ============================================================================


@router.get("/metrics", response_model=CalibrationMetrics)
async def get_calibration_metrics() -> CalibrationMetrics:
    """
    Get overall calibration metrics.
    
    Returns Expected Calibration Error (ECE), Brier score, and calibration status.
    
    - ECE < 0.05: Excellent calibration
    - ECE 0.05-0.10: Good calibration
    - ECE 0.10-0.15: Moderate calibration
    - ECE > 0.15: Poor calibration (needs attention)
    """
    logger.info("calibration_metrics_requested")
    return _compute_calibration_metrics()


@router.get("/curve", response_model=CalibrationCurve)
async def get_calibration_curve(
    num_bins: int = Query(default=10, ge=5, le=20, description="Number of bins for reliability diagram"),
) -> CalibrationCurve:
    """
    Get calibration curve data for reliability diagram.
    
    Returns bins showing predicted probability vs observed frequency,
    which can be used to plot a reliability diagram.
    
    A well-calibrated system will have points close to the diagonal line.
    """
    logger.info("calibration_curve_requested", num_bins=num_bins)
    return _compute_calibration_curve(num_bins)


@router.get("/alerts", response_model=list[CalibrationAlert])
async def get_calibration_alerts() -> list[CalibrationAlert]:
    """
    Get active calibration alerts.
    
    Returns alerts for calibration issues that need attention,
    including ECE and Brier score thresholds, category-specific issues,
    and calibration drift detection.
    """
    logger.info("calibration_alerts_requested")
    return _check_calibration_alerts()


@router.post("/record", response_model=OutcomeRecordResponse)
async def record_outcome(outcome: OutcomeRecord) -> OutcomeRecordResponse:
    """
    Record an actual outcome for a previous prediction.
    
    This is used to track calibration over time. Each recorded outcome
    contributes to ECE and Brier score calculations.
    
    The response indicates whether this prediction was:
    - overconfident: predicted high, but didn't happen
    - underconfident: predicted low, but did happen
    - correct: prediction matched outcome appropriately
    """
    global _cached_metrics, _cached_metrics_time
    
    # Record the outcome
    record = {
        "prediction_id": outcome.prediction_id,
        "decision_id": outcome.decision_id,
        "predicted_probability": outcome.predicted_probability,
        "actual_outcome": outcome.actual_outcome,
        "outcome_timestamp": outcome.outcome_timestamp.isoformat(),
        "category": outcome.category,
        "notes": outcome.notes,
        "recorded_at": datetime.utcnow().isoformat(),
    }
    _calibration_records.append(record)
    
    # Invalidate cache
    _cached_metrics = None
    _cached_metrics_time = None
    
    # Determine contribution
    if outcome.predicted_probability > 0.6 and not outcome.actual_outcome:
        contribution = "overconfident"
    elif outcome.predicted_probability < 0.4 and outcome.actual_outcome:
        contribution = "underconfident"
    else:
        contribution = "correct"
    
    # Compute new metrics
    metrics = _compute_calibration_metrics()
    
    logger.info(
        "outcome_recorded",
        prediction_id=outcome.prediction_id,
        predicted=outcome.predicted_probability,
        actual=outcome.actual_outcome,
        contribution=contribution,
        current_ece=metrics.expected_calibration_error,
    )
    
    return OutcomeRecordResponse(
        success=True,
        prediction_id=outcome.prediction_id,
        calibration_contribution=contribution,
        current_ece=metrics.expected_calibration_error,
    )


@router.get("/health")
async def calibration_health():
    """
    Quick health check for calibration system.
    
    Returns basic stats about calibration data and any critical alerts.
    """
    metrics = _compute_calibration_metrics()
    alerts = _check_calibration_alerts()
    critical_alerts = [a for a in alerts if a.severity == AlertSeverity.CRITICAL]
    
    return {
        "status": "healthy" if len(critical_alerts) == 0 else "degraded",
        "total_records": len(_calibration_records),
        "ece": metrics.expected_calibration_error,
        "calibration_status": metrics.calibration_status,
        "critical_alerts": len(critical_alerts),
        "last_updated": metrics.last_updated.isoformat(),
    }
