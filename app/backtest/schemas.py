"""
Backtesting Schemas for RISKCAST Decision Validation.

Validates decision quality against historical events with known outcomes.

Key concepts:
- BacktestEvent: A historical event with KNOWN outcome (what actually happened)
- BacktestResult: RISKCAST decision vs actual outcome for one event
- BacktestSummary: Aggregate metrics across all events

The goal is to answer: "Would RISKCAST have given good advice?"
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Any

from pydantic import BaseModel, ConfigDict, Field, computed_field


# =============================================================================
# ENUMS
# =============================================================================


class EventOutcome(str, Enum):
    """What actually happened with the event."""
    
    MATERIALIZED = "materialized"          # Event happened as predicted
    PARTIALLY_MATERIALIZED = "partially"   # Event happened but less severe
    DID_NOT_MATERIALIZE = "did_not"        # Event didn't happen
    ONGOING = "ongoing"                    # Still unfolding (can't evaluate yet)


class ActionTaken(str, Enum):
    """What action the customer actually took."""
    
    FOLLOWED_RECOMMENDATION = "followed"   # Did what RISKCAST suggested
    PARTIAL_ACTION = "partial"             # Took some but not all actions
    DIFFERENT_ACTION = "different"         # Took a different action
    NO_ACTION = "no_action"                # Did nothing
    UNKNOWN = "unknown"                    # No feedback


class DecisionQuality(str, Enum):
    """How good was the decision in hindsight."""
    
    EXCELLENT = "excellent"    # Saved significant money/time
    GOOD = "good"              # Decision was helpful
    NEUTRAL = "neutral"        # Decision didn't make much difference
    POOR = "poor"              # Decision was wrong or costly
    HARMFUL = "harmful"        # Decision caused unnecessary loss


# =============================================================================
# HISTORICAL EVENT
# =============================================================================


class ActualImpact(BaseModel):
    """What actually happened - the ground truth."""
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "actual_delay_days": 12,
                "actual_cost_usd": 45000,
                "actual_rate_increase_pct": 35,
            }
        }
    )
    
    # What happened
    event_occurred: bool = Field(
        description="Did the predicted event actually occur?"
    )
    severity_vs_prediction: str = Field(
        default="as_predicted",
        description="worse_than_predicted / as_predicted / less_than_predicted / did_not_occur"
    )
    
    # Actual costs (ground truth)
    actual_delay_days: int = Field(
        default=0,
        ge=0,
        description="Actual delay that occurred (days)"
    )
    actual_cost_usd: float = Field(
        default=0,
        ge=0,
        description="Actual financial impact (USD)"
    )
    actual_rate_increase_pct: Optional[float] = Field(
        default=None,
        description="Actual rate increase percentage"
    )
    
    # Disruption metrics
    vessels_affected: int = Field(
        default=0,
        ge=0,
        description="Number of vessels actually affected"
    )
    ports_disrupted: list[str] = Field(
        default_factory=list,
        description="Ports that were actually disrupted"
    )
    
    # Timeline
    impact_started_at: Optional[datetime] = Field(
        default=None,
        description="When the impact actually started"
    )
    impact_ended_at: Optional[datetime] = Field(
        default=None,
        description="When the impact ended"
    )
    
    @computed_field
    @property
    def actual_duration_days(self) -> Optional[int]:
        """How long did the impact actually last."""
        if self.impact_started_at and self.impact_ended_at:
            return (self.impact_ended_at - self.impact_started_at).days
        return None


class BacktestEvent(BaseModel):
    """
    A historical event with KNOWN outcome for backtesting.
    
    This is the "answer key" that we compare RISKCAST decisions against.
    
    Example:
        - Event: "Red Sea disruption January 2024"
        - Signal: What OMEN detected at the time
        - Outcome: What actually happened (12 days delay, $45K cost per shipment)
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "event_id": "RS2024-001",
                "event_name": "Red Sea Disruption Jan 2024",
                "event_date": "2024-01-15T00:00:00Z",
                "chokepoint": "red_sea",
                "category": "geopolitical",
                "outcome": "materialized",
            }
        }
    )
    
    # Identity
    event_id: str = Field(description="Unique event identifier")
    event_name: str = Field(max_length=200, description="Human-readable name")
    event_date: datetime = Field(description="When the event occurred/started")
    
    # Classification
    chokepoint: str = Field(description="Primary chokepoint affected")
    secondary_chokepoints: list[str] = Field(
        default_factory=list,
        description="Secondary chokepoints affected"
    )
    category: str = Field(
        description="Event category",
        examples=["geopolitical", "weather", "infrastructure", "labor"]
    )
    
    # What OMEN would have detected (simulated signal)
    signal_probability: float = Field(
        ge=0,
        le=1,
        description="What probability OMEN/Polymarket showed at the time"
    )
    signal_confidence: float = Field(
        ge=0,
        le=1,
        description="What confidence score the signal had"
    )
    detection_lead_time_hours: float = Field(
        ge=0,
        description="How many hours before impact was signal detected"
    )
    
    # Ground truth outcome
    outcome: EventOutcome = Field(description="What actually happened")
    actual_impact: ActualImpact = Field(description="Detailed actual impact")
    
    # Context at the time
    market_conditions: dict[str, Any] = Field(
        default_factory=dict,
        description="Market conditions at the time (rates, congestion, etc.)"
    )
    
    # Notes
    notes: Optional[str] = Field(
        default=None,
        description="Additional context about this event"
    )
    source_url: Optional[str] = Field(
        default=None,
        description="URL to news/documentation about this event"
    )
    
    @computed_field
    @property
    def was_actionable_signal(self) -> bool:
        """Did signal probability justify action?"""
        return self.signal_probability >= 0.5 and self.signal_confidence >= 0.5
    
    @computed_field
    @property
    def prediction_was_correct(self) -> bool:
        """Was the prediction (probability >= 50%) correct?"""
        predicted = self.signal_probability >= 0.5
        happened = self.outcome in [EventOutcome.MATERIALIZED, EventOutcome.PARTIALLY_MATERIALIZED]
        return predicted == happened


# =============================================================================
# BACKTEST RESULT (Single Event)
# =============================================================================


class PredictionVsActual(BaseModel):
    """Comparison of predicted vs actual values."""
    
    # Probability calibration
    predicted_probability: float = Field(
        ge=0,
        le=1,
        description="What RISKCAST predicted"
    )
    actual_occurred: bool = Field(description="Did it actually happen?")
    
    # Delay prediction
    predicted_delay_days: int = Field(
        ge=0,
        description="Predicted delay"
    )
    actual_delay_days: int = Field(
        ge=0,
        description="Actual delay"
    )
    delay_error_days: int = Field(
        description="Prediction error (predicted - actual)"
    )
    
    # Cost prediction
    predicted_cost_usd: float = Field(
        ge=0,
        description="Predicted cost"
    )
    actual_cost_usd: float = Field(
        ge=0,
        description="Actual cost"
    )
    cost_error_usd: float = Field(
        description="Prediction error (predicted - actual)"
    )
    cost_error_pct: float = Field(
        description="Percentage error"
    )
    
    @computed_field
    @property
    def delay_error_abs(self) -> int:
        """Absolute delay error."""
        return abs(self.delay_error_days)
    
    @computed_field
    @property
    def cost_error_abs(self) -> float:
        """Absolute cost error."""
        return abs(self.cost_error_usd)
    
    @computed_field
    @property
    def was_conservative(self) -> bool:
        """Did we predict worse than actual? (conservative bias)"""
        return self.predicted_cost_usd > self.actual_cost_usd


class ValueAnalysis(BaseModel):
    """Economic value analysis of the decision."""
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "action_cost_usd": 8500,
                "value_protected_usd": 45000,
                "net_value_usd": 36500,
            }
        }
    )
    
    # What the recommended action would have cost
    action_cost_usd: float = Field(
        ge=0,
        description="Cost of taking the recommended action"
    )
    
    # What would have been lost without action
    loss_if_no_action_usd: float = Field(
        ge=0,
        description="Actual loss that would have occurred without action"
    )
    
    # Value protected by taking action
    value_protected_usd: float = Field(
        ge=0,
        description="Value protected by following recommendation"
    )
    
    # Net value (was the action worth it?)
    net_value_usd: float = Field(
        description="Net value = value_protected - action_cost"
    )
    
    # What actually happened (if they followed vs didn't)
    actual_outcome_followed: Optional[float] = Field(
        default=None,
        description="What it actually cost if they followed advice"
    )
    actual_outcome_not_followed: Optional[float] = Field(
        default=None,
        description="What it actually cost if they didn't follow advice"
    )
    
    @computed_field
    @property
    def roi(self) -> float:
        """Return on investment for taking action."""
        if self.action_cost_usd == 0:
            return 0.0
        return (self.value_protected_usd - self.action_cost_usd) / self.action_cost_usd
    
    @computed_field
    @property
    def was_good_advice(self) -> bool:
        """Was the advice economically beneficial?"""
        return self.net_value_usd > 0


class BacktestResult(BaseModel):
    """
    Result of backtesting RISKCAST against ONE historical event.
    
    Compares what RISKCAST recommended vs what actually happened.
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "event_id": "RS2024-001",
                "decision_id": "dec_backtest_001",
                "quality": "excellent",
                "value_captured_usd": 36500,
            }
        }
    )
    
    # Identity
    result_id: str = Field(description="Unique result identifier")
    event_id: str = Field(description="Event that was tested")
    decision_id: str = Field(description="Decision that was generated")
    
    # Timing
    backtest_run_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When this backtest was run"
    )
    
    # What RISKCAST recommended
    recommended_action: str = Field(
        description="What action RISKCAST recommended"
    )
    action_deadline: datetime = Field(
        description="Deadline RISKCAST gave"
    )
    estimated_cost_usd: float = Field(
        ge=0,
        description="Cost RISKCAST estimated"
    )
    
    # Confidence
    decision_confidence: float = Field(
        ge=0,
        le=1,
        description="Confidence score in the decision"
    )
    
    # Prediction accuracy
    prediction_accuracy: PredictionVsActual = Field(
        description="Detailed prediction vs actual comparison"
    )
    
    # Value analysis
    value_analysis: ValueAnalysis = Field(
        description="Economic value analysis"
    )
    
    # Quality assessment
    quality: DecisionQuality = Field(
        description="Overall decision quality"
    )
    quality_reasons: list[str] = Field(
        default_factory=list,
        description="Reasons for quality assessment"
    )
    
    # Customer action (if known)
    customer_action: ActionTaken = Field(
        default=ActionTaken.UNKNOWN,
        description="What the customer actually did"
    )
    customer_feedback: Optional[str] = Field(
        default=None,
        description="Customer feedback if available"
    )
    
    @computed_field
    @property
    def was_correct_call(self) -> bool:
        """Was the overall decision correct?"""
        return self.quality in [DecisionQuality.EXCELLENT, DecisionQuality.GOOD]
    
    @computed_field
    @property
    def value_captured_usd(self) -> float:
        """Total value captured by following recommendation."""
        return max(0, self.value_analysis.net_value_usd)


# =============================================================================
# CALIBRATION ANALYSIS
# =============================================================================


class CalibrationBucket(BaseModel):
    """
    Calibration bucket for Brier score calculation.
    
    Groups predictions by confidence level and calculates accuracy.
    Example: Of predictions with 70-80% confidence, what % were correct?
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "bucket_min": 0.7,
                "bucket_max": 0.8,
                "predicted_probability": 0.75,
                "actual_frequency": 0.73,
                "sample_count": 25,
            }
        }
    )
    
    # Bucket range
    bucket_min: float = Field(ge=0, le=1, description="Bucket minimum")
    bucket_max: float = Field(ge=0, le=1, description="Bucket maximum")
    
    # Calibration metrics
    predicted_probability: float = Field(
        ge=0,
        le=1,
        description="Average predicted probability in bucket"
    )
    actual_frequency: float = Field(
        ge=0,
        le=1,
        description="Actual occurrence frequency in bucket"
    )
    
    # Counts
    sample_count: int = Field(ge=0, description="Number of events in bucket")
    correct_count: int = Field(ge=0, description="Number of correct predictions")
    
    @computed_field
    @property
    def calibration_error(self) -> float:
        """How far off is this bucket from perfect calibration."""
        return abs(self.predicted_probability - self.actual_frequency)
    
    @computed_field
    @property
    def is_well_calibrated(self) -> bool:
        """Is error within 10%?"""
        return self.calibration_error <= 0.10
    
    @computed_field
    @property
    def bucket_label(self) -> str:
        """Human-readable bucket label."""
        return f"{int(self.bucket_min * 100)}-{int(self.bucket_max * 100)}%"


# =============================================================================
# ACCURACY BY CATEGORY
# =============================================================================


class AccuracyByCategory(BaseModel):
    """Accuracy metrics broken down by category (chokepoint, event type, etc.)."""
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "category_name": "red_sea",
                "category_type": "chokepoint",
                "total_events": 25,
                "accuracy": 0.84,
                "avg_value_captured_usd": 28500,
            }
        }
    )
    
    category_name: str = Field(description="Category value")
    category_type: str = Field(
        description="Type of category",
        examples=["chokepoint", "event_type", "severity", "action_type"]
    )
    
    # Counts
    total_events: int = Field(ge=0, description="Total events in category")
    correct_predictions: int = Field(ge=0, description="Correct predictions")
    
    # Accuracy
    accuracy: float = Field(
        ge=0,
        le=1,
        description="Prediction accuracy for this category"
    )
    
    # Value metrics
    total_value_captured_usd: float = Field(
        ge=0,
        description="Total value captured in category"
    )
    avg_value_captured_usd: float = Field(
        ge=0,
        description="Average value per event"
    )
    
    # Quality distribution
    quality_distribution: dict[str, int] = Field(
        default_factory=dict,
        description="Count of each quality rating"
    )
    
    @computed_field
    @property
    def is_high_performer(self) -> bool:
        """Is accuracy above 80%?"""
        return self.accuracy >= 0.80


# =============================================================================
# BACKTEST SUMMARY (All Events)
# =============================================================================


class BacktestSummary(BaseModel):
    """
    Summary of backtesting across ALL historical events.
    
    This is the final report card for RISKCAST quality.
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total_events": 100,
                "accuracy": 0.82,
                "brier_score": 0.15,
                "total_value_captured_usd": 2850000,
                "avg_value_per_event_usd": 28500,
            }
        }
    )
    
    # Run metadata
    summary_id: str = Field(description="Unique summary identifier")
    run_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When backtest was run"
    )
    
    # Event coverage
    total_events: int = Field(ge=0, description="Total events tested")
    date_range_start: datetime = Field(description="Earliest event date")
    date_range_end: datetime = Field(description="Latest event date")
    
    # Filter applied
    filters_applied: dict[str, Any] = Field(
        default_factory=dict,
        description="Filters used in this backtest"
    )
    
    # Overall accuracy metrics
    accuracy: float = Field(
        ge=0,
        le=1,
        description="Overall prediction accuracy"
    )
    precision: float = Field(
        ge=0,
        le=1,
        description="Precision (true positives / all positives)"
    )
    recall: float = Field(
        ge=0,
        le=1,
        description="Recall (true positives / actual positives)"
    )
    f1_score: float = Field(
        ge=0,
        le=1,
        description="F1 score (harmonic mean of precision and recall)"
    )
    
    # Calibration
    brier_score: float = Field(
        ge=0,
        le=1,
        description="Brier score (lower is better, 0 is perfect)"
    )
    calibration_buckets: list[CalibrationBucket] = Field(
        default_factory=list,
        description="Calibration by confidence bucket"
    )
    
    # Prediction error metrics
    mean_delay_error_days: float = Field(
        description="Mean absolute delay prediction error"
    )
    mean_cost_error_pct: float = Field(
        description="Mean absolute cost prediction error (%)"
    )
    
    # Value metrics (THE MOAT)
    total_value_captured_usd: float = Field(
        ge=0,
        description="Total value captured across all events"
    )
    avg_value_per_event_usd: float = Field(
        ge=0,
        description="Average value per event"
    )
    total_action_cost_usd: float = Field(
        ge=0,
        description="Total cost of recommended actions"
    )
    net_value_usd: float = Field(
        description="Net value = total_value_captured - total_action_cost"
    )
    roi: float = Field(
        description="Return on investment"
    )
    
    # Quality distribution
    quality_distribution: dict[str, int] = Field(
        default_factory=dict,
        description="Count of each quality rating"
    )
    
    # Breakdown by category
    accuracy_by_chokepoint: list[AccuracyByCategory] = Field(
        default_factory=list,
        description="Accuracy by chokepoint"
    )
    accuracy_by_event_type: list[AccuracyByCategory] = Field(
        default_factory=list,
        description="Accuracy by event type"
    )
    accuracy_by_action_type: list[AccuracyByCategory] = Field(
        default_factory=list,
        description="Accuracy by action type"
    )
    
    # Individual results
    results: list[BacktestResult] = Field(
        default_factory=list,
        description="Individual event results"
    )
    
    # Recommendations for improvement
    weak_areas: list[str] = Field(
        default_factory=list,
        description="Areas needing improvement"
    )
    strong_areas: list[str] = Field(
        default_factory=list,
        description="Areas performing well"
    )
    
    @computed_field
    @property
    def excellent_count(self) -> int:
        """Count of excellent decisions."""
        return self.quality_distribution.get("excellent", 0)
    
    @computed_field
    @property
    def good_count(self) -> int:
        """Count of good decisions."""
        return self.quality_distribution.get("good", 0)
    
    @computed_field
    @property
    def poor_or_harmful_count(self) -> int:
        """Count of poor or harmful decisions."""
        return (
            self.quality_distribution.get("poor", 0) +
            self.quality_distribution.get("harmful", 0)
        )
    
    @computed_field
    @property
    def is_well_calibrated(self) -> bool:
        """Is Brier score below 0.20?"""
        return self.brier_score < 0.20
    
    @computed_field
    @property
    def is_valuable(self) -> bool:
        """Is ROI positive?"""
        return self.roi > 0
    
    @computed_field
    @property
    def grade(self) -> str:
        """Overall grade based on accuracy and value."""
        if self.accuracy >= 0.85 and self.is_valuable and self.is_well_calibrated:
            return "A"
        elif self.accuracy >= 0.75 and self.is_valuable:
            return "B"
        elif self.accuracy >= 0.65:
            return "C"
        elif self.accuracy >= 0.50:
            return "D"
        else:
            return "F"
    
    def get_summary_text(self) -> str:
        """Get human-readable summary."""
        return (
            f"Backtest Summary (Grade: {self.grade})\n"
            f"Events: {self.total_events} | Accuracy: {self.accuracy:.0%}\n"
            f"Value Captured: ${self.total_value_captured_usd:,.0f} | ROI: {self.roi:.1%}\n"
            f"Brier Score: {self.brier_score:.3f} | Calibration: {'Good' if self.is_well_calibrated else 'Needs Work'}\n"
            f"Quality: {self.excellent_count} excellent, {self.good_count} good, "
            f"{self.poor_or_harmful_count} poor/harmful"
        )
