"""
Calibration Database Models.

SQLAlchemy models for persistent calibration data storage.

Tables:
- prediction_records: Individual predictions with outcomes
- calibration_buckets: Aggregated bucket statistics
- calibration_metrics: Historical ECE, Brier scores
- ci_coverage_records: Confidence interval coverage tracking
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column,
    String,
    Float,
    Integer,
    DateTime,
    Boolean,
    JSON,
    Index,
    ForeignKey,
    Enum as SQLEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_model import Base


class PredictionRecordModel(Base):
    """
    Stores individual predictions for calibration tracking.
    
    Every decision's confidence prediction is recorded here.
    When the actual outcome is known, it's updated to enable
    calibration analysis.
    
    Addresses audit gap A3: "Calibration data persistence"
    """
    __tablename__ = "prediction_records"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Decision reference
    decision_id: Mapped[str] = mapped_column(
        String(100), 
        unique=True, 
        index=True,
        nullable=False,
        doc="Reference to the decision",
    )
    customer_id: Mapped[str] = mapped_column(
        String(100),
        index=True,
        nullable=False,
        doc="Customer who received the decision",
    )
    
    # Prediction details
    predicted_confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        doc="Confidence score (0-1) from decision",
    )
    predicted_outcome: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        doc="Whether we predicted disruption (True) or no disruption (False)",
    )
    predicted_action: Mapped[str] = mapped_column(
        String(50),
        nullable=True,
        doc="Action type recommended (REROUTE, DELAY, etc.)",
    )
    
    # Numeric predictions with CIs
    predicted_exposure_usd: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="Predicted exposure in USD (point estimate)",
    )
    predicted_exposure_ci_low: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="90% CI lower bound for exposure",
    )
    predicted_exposure_ci_high: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="90% CI upper bound for exposure",
    )
    predicted_delay_days: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="Predicted delay in days (point estimate)",
    )
    predicted_delay_ci_low: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="90% CI lower bound for delay",
    )
    predicted_delay_ci_high: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="90% CI upper bound for delay",
    )
    
    # Actual outcomes (populated later)
    actual_outcome: Mapped[Optional[bool]] = mapped_column(
        Boolean,
        nullable=True,
        doc="Did the disruption actually occur?",
    )
    actual_exposure_usd: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="Actual exposure in USD",
    )
    actual_delay_days: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="Actual delay in days",
    )
    action_was_followed: Mapped[Optional[bool]] = mapped_column(
        Boolean,
        nullable=True,
        doc="Did customer follow our recommendation?",
    )
    
    # Context for segmented analysis
    chokepoint: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        index=True,
        doc="Chokepoint involved",
    )
    event_type: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        index=True,
        doc="Type of event (DISRUPTION, WEATHER, etc.)",
    )
    
    # Timestamps
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        doc="When prediction was recorded",
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        doc="When actual outcome was recorded",
    )
    
    # Indexes for efficient queries
    __table_args__ = (
        Index("ix_prediction_records_confidence", "predicted_confidence"),
        Index("ix_prediction_records_resolved", "resolved_at"),
        Index("ix_prediction_records_chokepoint_type", "chokepoint", "event_type"),
    )


class CalibrationBucketModel(Base):
    """
    Aggregated statistics for each confidence bucket.
    
    Buckets: 0-10%, 10-20%, ..., 90-100%
    Tracks total predictions and correct predictions per bucket
    to calculate calibration error.
    """
    __tablename__ = "calibration_buckets"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Bucket bounds
    bucket_start: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        doc="Lower bound of bucket (e.g., 0.8)",
    )
    bucket_end: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        doc="Upper bound of bucket (e.g., 0.9)",
    )
    bucket_name: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        unique=True,
        index=True,
        doc="Human-readable bucket name (e.g., '80-90%')",
    )
    
    # Statistics
    total_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        doc="Total predictions in this bucket",
    )
    correct_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        doc="Correct predictions in this bucket",
    )
    observed_accuracy: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        doc="Observed accuracy (correct_count / total_count)",
    )
    
    # Calibration metrics
    expected_accuracy: Mapped[float] = mapped_column(
        Float,
        doc="Expected accuracy (midpoint of bucket)",
    )
    calibration_error: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        doc="observed - expected accuracy",
    )
    
    # Timestamps
    last_updated: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=True,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )


class CalibrationMetricsModel(Base):
    """
    Historical calibration metrics for trend tracking.
    
    Stores periodic snapshots of ECE, Brier score, etc.
    for monitoring calibration health over time.
    """
    __tablename__ = "calibration_metrics"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Timestamp
    timestamp: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        index=True,
        default=datetime.utcnow,
    )
    
    # Metrics
    ece: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        doc="Expected Calibration Error (lower is better)",
    )
    brier_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        doc="Brier Score (lower is better, 0 is perfect)",
    )
    mace: Mapped[float] = mapped_column(
        Float,
        nullable=True,
        doc="Mean Absolute Calibration Error",
    )
    
    # Sample info
    total_predictions: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        doc="Total predictions at time of calculation",
    )
    predictions_with_outcomes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        doc="Predictions with known outcomes",
    )
    
    # Detailed bucket data (JSON)
    bucket_data: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        doc="Full bucket breakdown at this timestamp",
    )
    
    # Recommendations
    recommendations: Mapped[Optional[list]] = mapped_column(
        JSON,
        nullable=True,
        doc="Auto-generated calibration recommendations",
    )


class CICoverageRecordModel(Base):
    """
    Tracks confidence interval coverage validation.
    
    For validating that 90% CIs actually contain the true value
    approximately 90% of the time.
    
    Addresses audit gap A2.2: CI coverage validation
    """
    __tablename__ = "ci_coverage_records"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Link to prediction
    prediction_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("prediction_records.id"),
        nullable=False,
        index=True,
    )
    
    # Metric type (exposure, delay, cost, inaction)
    metric_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        doc="Type of metric being tracked",
    )
    
    # CI level
    ci_level: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        doc="CI level (90% or 95%)",
    )
    
    # Predicted CI
    ci_low: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        doc="Lower bound of CI",
    )
    ci_high: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        doc="Upper bound of CI",
    )
    point_estimate: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        doc="Point estimate",
    )
    
    # Actual value (filled when outcome known)
    actual_value: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="Actual observed value",
    )
    
    # Coverage result
    is_covered: Mapped[Optional[bool]] = mapped_column(
        Boolean,
        nullable=True,
        doc="Did CI contain the actual value?",
    )
    
    # Context
    chokepoint: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        index=True,
    )
    event_type: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        index=True,
    )
    
    # Timestamps
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
    )
    
    __table_args__ = (
        Index("ix_ci_coverage_metric_level", "metric_type", "ci_level"),
    )
