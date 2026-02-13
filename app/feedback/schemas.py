"""
Feedback Schemas for RISKCAST.

Data models for the feedback loop system that enables continuous improvement.

Key concepts:
- CustomerFeedback: Direct feedback from users about decisions
- OutcomeRecord: What actually happened (ground truth)
- ImprovementSignal: Actionable insights for system improvement
- AccuracyReport: Aggregate accuracy metrics over time
- CalibrationReport: Confidence score reliability analysis
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Any

from pydantic import BaseModel, ConfigDict, Field, computed_field


# =============================================================================
# ENUMS
# =============================================================================


class FeedbackType(str, Enum):
    """Type of feedback received."""
    
    ACTION_TAKEN = "action_taken"           # What action customer took
    SATISFACTION = "satisfaction"            # Customer satisfaction rating
    OUTCOME_REPORT = "outcome_report"        # Report of actual outcome
    CORRECTION = "correction"                # Correction to prediction
    SUGGESTION = "suggestion"                # Suggestion for improvement
    COMPLAINT = "complaint"                  # Complaint about service


class FeedbackSource(str, Enum):
    """Source of feedback."""
    
    CUSTOMER_MANUAL = "customer_manual"      # Customer submitted manually
    CUSTOMER_API = "customer_api"            # Via API integration
    SYSTEM_OBSERVED = "system_observed"      # System observed the outcome
    CARRIER_DATA = "carrier_data"            # Data from carrier APIs
    MARKET_DATA = "market_data"              # From market data sources
    INTERNAL_REVIEW = "internal_review"      # Internal team review


class SatisfactionLevel(int, Enum):
    """Customer satisfaction level (1-5)."""
    
    VERY_DISSATISFIED = 1
    DISSATISFIED = 2
    NEUTRAL = 3
    SATISFIED = 4
    VERY_SATISFIED = 5


class ActionFollowed(str, Enum):
    """Whether customer followed recommendation."""
    
    FOLLOWED_EXACTLY = "followed_exactly"    # Did exactly what we said
    FOLLOWED_PARTIALLY = "followed_partially" # Did some of it
    DIFFERENT_ACTION = "different_action"     # Did something else
    NO_ACTION = "no_action"                   # Did nothing
    UNKNOWN = "unknown"                       # Don't know


class ImprovementArea(str, Enum):
    """Area requiring improvement."""
    
    PROBABILITY_CALIBRATION = "probability_calibration"
    DELAY_ESTIMATION = "delay_estimation"
    COST_ESTIMATION = "cost_estimation"
    ACTION_RECOMMENDATION = "action_recommendation"
    URGENCY_ASSESSMENT = "urgency_assessment"
    CHOKEPOINT_DETECTION = "chokepoint_detection"
    TIMING_ACCURACY = "timing_accuracy"


# =============================================================================
# CUSTOMER FEEDBACK
# =============================================================================


class CustomerFeedbackCreate(BaseModel):
    """Request to create customer feedback."""
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "decision_id": "dec_20240205143022_cust_abc",
                "feedback_type": "action_taken",
                "action_followed": "followed_exactly",
                "satisfaction": 4,
                "notes": "Great advice, avoided 12-day delay",
            }
        }
    )
    
    decision_id: str = Field(description="Decision this feedback is for")
    
    feedback_type: FeedbackType = Field(
        default=FeedbackType.ACTION_TAKEN,
        description="Type of feedback"
    )
    
    # Action feedback
    action_followed: Optional[ActionFollowed] = Field(
        default=None,
        description="Whether recommendation was followed"
    )
    actual_action_taken: Optional[str] = Field(
        default=None,
        description="What action was actually taken"
    )
    
    # Satisfaction feedback
    satisfaction: Optional[SatisfactionLevel] = Field(
        default=None,
        description="Satisfaction rating (1-5)"
    )
    would_recommend: Optional[bool] = Field(
        default=None,
        description="Would customer recommend RISKCAST?"
    )
    
    # Outcome feedback
    actual_delay_days: Optional[int] = Field(
        default=None,
        ge=0,
        description="Actual delay experienced"
    )
    actual_cost_usd: Optional[float] = Field(
        default=None,
        ge=0,
        description="Actual cost incurred"
    )
    event_occurred: Optional[bool] = Field(
        default=None,
        description="Did the predicted event actually occur?"
    )
    
    # Qualitative feedback
    notes: Optional[str] = Field(
        default=None,
        max_length=2000,
        description="Free-form notes"
    )
    what_helped: Optional[str] = Field(
        default=None,
        max_length=500,
        description="What was most helpful about the decision"
    )
    what_could_improve: Optional[str] = Field(
        default=None,
        max_length=500,
        description="What could be improved"
    )
    
    # Metadata
    source: FeedbackSource = Field(
        default=FeedbackSource.CUSTOMER_MANUAL,
        description="Source of this feedback"
    )


class CustomerFeedback(CustomerFeedbackCreate):
    """Complete customer feedback record."""
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "feedback_id": "fb_abc123",
                "decision_id": "dec_20240205143022_cust_abc",
                "customer_id": "cust_abc123",
                "satisfaction": 4,
            }
        }
    )
    
    feedback_id: str = Field(description="Unique feedback ID")
    customer_id: str = Field(description="Customer who submitted feedback")
    
    # Timestamps
    submitted_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When feedback was submitted"
    )
    processed_at: Optional[datetime] = Field(
        default=None,
        description="When feedback was processed"
    )
    
    # Processing status
    is_processed: bool = Field(
        default=False,
        description="Has this feedback been processed?"
    )
    processing_notes: Optional[str] = Field(
        default=None,
        description="Notes from processing"
    )
    
    @computed_field
    @property
    def has_outcome_data(self) -> bool:
        """Does this feedback include outcome data?"""
        return any([
            self.actual_delay_days is not None,
            self.actual_cost_usd is not None,
            self.event_occurred is not None,
        ])
    
    @computed_field
    @property
    def is_positive(self) -> bool:
        """Is this positive feedback?"""
        if self.satisfaction:
            return self.satisfaction.value >= 4
        return False


# =============================================================================
# OUTCOME RECORDS
# =============================================================================


class OutcomeRecordCreate(BaseModel):
    """Request to create an outcome record."""
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "decision_id": "dec_20240205143022_cust_abc",
                "event_occurred": True,
                "actual_delay_days": 14,
                "actual_cost_usd": 45000,
            }
        }
    )
    
    decision_id: str = Field(description="Decision this outcome is for")
    
    # What actually happened
    event_occurred: bool = Field(description="Did the predicted event occur?")
    event_severity: Optional[str] = Field(
        default=None,
        description="Actual severity vs predicted"
    )
    
    # Actual impact
    actual_delay_days: Optional[int] = Field(
        default=None,
        ge=0,
        description="Actual delay in days"
    )
    actual_cost_usd: Optional[float] = Field(
        default=None,
        ge=0,
        description="Actual total cost in USD"
    )
    actual_rate_increase_pct: Optional[float] = Field(
        default=None,
        description="Actual rate increase percentage"
    )
    
    # Action taken
    action_taken: Optional[str] = Field(
        default=None,
        description="What action was actually taken"
    )
    action_cost_usd: Optional[float] = Field(
        default=None,
        ge=0,
        description="Cost of the action taken"
    )
    
    # Context
    source: FeedbackSource = Field(
        default=FeedbackSource.SYSTEM_OBSERVED,
        description="Source of this outcome data"
    )
    evidence_urls: list[str] = Field(
        default_factory=list,
        description="URLs to supporting evidence"
    )
    notes: Optional[str] = Field(
        default=None,
        max_length=2000,
        description="Additional notes"
    )


class OutcomeRecord(OutcomeRecordCreate):
    """Complete outcome record with predictions."""
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "outcome_id": "out_abc123",
                "decision_id": "dec_20240205143022_cust_abc",
                "event_occurred": True,
                "delay_error_days": 2,
                "cost_error_usd": 5000,
            }
        }
    )
    
    outcome_id: str = Field(description="Unique outcome ID")
    customer_id: str = Field(description="Customer ID")
    signal_id: str = Field(description="Original signal ID")
    
    # What was predicted
    predicted_event: bool = Field(description="Did we predict the event?")
    predicted_delay_days: Optional[int] = Field(description="Predicted delay")
    predicted_cost_usd: Optional[float] = Field(description="Predicted cost")
    predicted_confidence: float = Field(
        ge=0,
        le=1,
        description="Confidence in prediction"
    )
    recommended_action: str = Field(description="What we recommended")
    
    # Error calculations
    delay_error_days: Optional[int] = Field(
        default=None,
        description="Delay error (predicted - actual)"
    )
    cost_error_usd: Optional[float] = Field(
        default=None,
        description="Cost error (predicted - actual)"
    )
    cost_error_pct: Optional[float] = Field(
        default=None,
        description="Cost error percentage"
    )
    
    # Accuracy assessment
    prediction_correct: bool = Field(
        description="Was the main prediction correct?"
    )
    delay_accurate: Optional[bool] = Field(
        default=None,
        description="Was delay estimate accurate (within 30%)?"
    )
    cost_accurate: Optional[bool] = Field(
        default=None,
        description="Was cost estimate accurate (within 30%)?"
    )
    
    # Value delivered
    value_delivered_usd: Optional[float] = Field(
        default=None,
        description="Value delivered by following advice"
    )
    
    # Timestamps
    predicted_at: datetime = Field(description="When prediction was made")
    observed_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When outcome was observed"
    )
    
    @computed_field
    @property
    def delay_error_abs(self) -> Optional[int]:
        """Absolute delay error."""
        if self.delay_error_days is not None:
            return abs(self.delay_error_days)
        return None
    
    @computed_field
    @property
    def cost_error_abs(self) -> Optional[float]:
        """Absolute cost error."""
        if self.cost_error_usd is not None:
            return abs(self.cost_error_usd)
        return None
    
    @computed_field
    @property
    def was_overestimate(self) -> bool:
        """Did we predict worse than actual?"""
        if self.cost_error_usd is not None:
            return self.cost_error_usd > 0
        return False


# =============================================================================
# IMPROVEMENT SIGNALS
# =============================================================================


class ImprovementSignal(BaseModel):
    """Signal indicating area for improvement."""
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "signal_id": "imp_abc123",
                "area": "delay_estimation",
                "severity": "medium",
                "message": "Delay estimates off by 3+ days in 40% of Red Sea cases",
            }
        }
    )
    
    signal_id: str = Field(description="Unique signal ID")
    
    # What needs improvement
    area: ImprovementArea = Field(description="Area requiring improvement")
    severity: str = Field(
        description="Severity: low, medium, high, critical"
    )
    
    # Details
    message: str = Field(
        max_length=500,
        description="Human-readable description"
    )
    evidence: dict[str, Any] = Field(
        default_factory=dict,
        description="Supporting evidence"
    )
    
    # Context
    chokepoint: Optional[str] = Field(
        default=None,
        description="Specific chokepoint if applicable"
    )
    event_category: Optional[str] = Field(
        default=None,
        description="Specific event category if applicable"
    )
    confidence_bucket: Optional[str] = Field(
        default=None,
        description="Specific confidence bucket if applicable"
    )
    
    # Recommendations
    recommended_action: str = Field(
        max_length=500,
        description="Recommended action to improve"
    )
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    sample_count: int = Field(
        ge=1,
        description="Number of samples this is based on"
    )
    
    @computed_field
    @property
    def is_critical(self) -> bool:
        """Is this a critical issue?"""
        return self.severity == "critical"


# =============================================================================
# ACCURACY REPORTS
# =============================================================================


class AccuracyReport(BaseModel):
    """Accuracy metrics for a time period."""
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "report_id": "acc_2024_02",
                "overall_accuracy": 0.82,
                "precision": 0.85,
                "recall": 0.78,
            }
        }
    )
    
    report_id: str = Field(description="Unique report ID")
    
    # Time period
    period_start: datetime = Field(description="Start of period")
    period_end: datetime = Field(description="End of period")
    period_days: int = Field(ge=1, description="Number of days in period")
    
    # Sample sizes
    total_decisions: int = Field(ge=0, description="Total decisions made")
    decisions_with_outcome: int = Field(ge=0, description="Decisions with known outcome")
    
    # Overall accuracy
    overall_accuracy: float = Field(
        ge=0,
        le=1,
        description="Overall prediction accuracy"
    )
    precision: float = Field(
        ge=0,
        le=1,
        description="Precision (true positives / predicted positives)"
    )
    recall: float = Field(
        ge=0,
        le=1,
        description="Recall (true positives / actual positives)"
    )
    f1_score: float = Field(
        ge=0,
        le=1,
        description="F1 score (harmonic mean)"
    )
    
    # Component accuracy
    delay_accuracy_mean: Optional[float] = Field(
        default=None,
        description="Mean delay prediction accuracy"
    )
    delay_mae_days: Optional[float] = Field(
        default=None,
        description="Mean absolute delay error in days"
    )
    cost_accuracy_mean: Optional[float] = Field(
        default=None,
        description="Mean cost prediction accuracy"
    )
    cost_mae_usd: Optional[float] = Field(
        default=None,
        description="Mean absolute cost error in USD"
    )
    cost_mape: Optional[float] = Field(
        default=None,
        description="Mean absolute percentage error for cost"
    )
    
    # By category
    accuracy_by_chokepoint: dict[str, float] = Field(
        default_factory=dict,
        description="Accuracy by chokepoint"
    )
    accuracy_by_event_type: dict[str, float] = Field(
        default_factory=dict,
        description="Accuracy by event type"
    )
    accuracy_by_action: dict[str, float] = Field(
        default_factory=dict,
        description="Accuracy by recommended action"
    )
    
    # Customer metrics
    action_uptake_rate: float = Field(
        ge=0,
        le=1,
        description="Percentage of recommendations followed"
    )
    avg_satisfaction: Optional[float] = Field(
        default=None,
        description="Average satisfaction score"
    )
    nps_score: Optional[float] = Field(
        default=None,
        description="Net Promoter Score"
    )
    
    # Value metrics
    total_value_delivered_usd: float = Field(
        ge=0,
        description="Total value delivered"
    )
    avg_value_per_decision_usd: float = Field(
        ge=0,
        description="Average value per decision"
    )
    
    # Generated
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    
    @computed_field
    @property
    def coverage_rate(self) -> float:
        """What percentage of decisions have outcomes?"""
        if self.total_decisions == 0:
            return 0.0
        return self.decisions_with_outcome / self.total_decisions
    
    @computed_field
    @property
    def grade(self) -> str:
        """Letter grade based on accuracy."""
        if self.overall_accuracy >= 0.90:
            return "A+"
        elif self.overall_accuracy >= 0.85:
            return "A"
        elif self.overall_accuracy >= 0.80:
            return "B+"
        elif self.overall_accuracy >= 0.75:
            return "B"
        elif self.overall_accuracy >= 0.70:
            return "C+"
        elif self.overall_accuracy >= 0.65:
            return "C"
        elif self.overall_accuracy >= 0.60:
            return "D"
        else:
            return "F"


class CalibrationReport(BaseModel):
    """Confidence calibration analysis."""
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "report_id": "cal_2024_02",
                "brier_score": 0.12,
                "is_well_calibrated": True,
            }
        }
    )
    
    report_id: str = Field(description="Unique report ID")
    
    # Time period
    period_start: datetime = Field(description="Start of period")
    period_end: datetime = Field(description="End of period")
    
    # Overall calibration
    brier_score: float = Field(
        ge=0,
        le=1,
        description="Brier score (lower is better)"
    )
    log_loss: Optional[float] = Field(
        default=None,
        description="Log loss score"
    )
    
    # Bucket analysis
    buckets: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Calibration by confidence bucket"
    )
    
    # Issues found
    overconfident_buckets: list[str] = Field(
        default_factory=list,
        description="Buckets where we're overconfident"
    )
    underconfident_buckets: list[str] = Field(
        default_factory=list,
        description="Buckets where we're underconfident"
    )
    
    # Recommendations
    recommended_adjustments: dict[str, float] = Field(
        default_factory=dict,
        description="Recommended confidence adjustments by bucket"
    )
    
    # Metadata
    sample_count: int = Field(ge=0, description="Total samples analyzed")
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    
    @computed_field
    @property
    def is_well_calibrated(self) -> bool:
        """Is the system well-calibrated?"""
        return self.brier_score < 0.20
    
    @computed_field
    @property
    def needs_attention(self) -> bool:
        """Does calibration need attention?"""
        return len(self.overconfident_buckets) > 1 or self.brier_score > 0.25


class TrendAnalysis(BaseModel):
    """Accuracy trend over time."""
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "metric": "overall_accuracy",
                "trend": "improving",
                "change_pct": 5.2,
            }
        }
    )
    
    metric: str = Field(description="Metric being tracked")
    
    # Trend
    trend: str = Field(
        description="Trend direction: improving, stable, declining"
    )
    change_pct: float = Field(description="Percentage change")
    
    # Data points
    data_points: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Historical data points"
    )
    
    # Current vs historical
    current_value: float = Field(description="Current value")
    previous_value: float = Field(description="Previous period value")
    baseline_value: Optional[float] = Field(
        default=None,
        description="Long-term baseline"
    )
    
    # Statistical significance
    is_significant: bool = Field(
        default=False,
        description="Is the trend statistically significant?"
    )
    confidence_interval: Optional[tuple[float, float]] = Field(
        default=None,
        description="95% confidence interval"
    )
    
    # Period
    period_type: str = Field(
        default="weekly",
        description="Period type: daily, weekly, monthly"
    )
    periods_analyzed: int = Field(ge=2, description="Number of periods")
    
    @computed_field
    @property
    def is_improving(self) -> bool:
        """Is the trend positive?"""
        return self.trend == "improving"
    
    @computed_field
    @property
    def is_concerning(self) -> bool:
        """Is the trend concerning?"""
        return self.trend == "declining" and abs(self.change_pct) > 5
