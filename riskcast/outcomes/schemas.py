"""
Outcome Tracking Schemas.

Records what ACTUALLY happened after a decision was made.
Used for model calibration, ROI tracking, and the learning flywheel.
"""

from datetime import datetime
from enum import StrEnum
from typing import Optional

from pydantic import BaseModel, Field


class OutcomeType(StrEnum):
    LOSS_OCCURRED = "loss_occurred"
    LOSS_AVOIDED = "loss_avoided"
    DELAY_OCCURRED = "delay_occurred"
    DELAY_AVOIDED = "delay_avoided"
    NO_IMPACT = "no_impact"
    PARTIAL_IMPACT = "partial_impact"


class OutcomeRecord(BaseModel):
    """What actually happened after a decision."""
    outcome_id: str
    decision_id: str
    company_id: str
    entity_type: str
    entity_id: str

    # Predicted values (from the decision)
    predicted_risk_score: float
    predicted_confidence: float
    predicted_loss_usd: float
    predicted_action: str

    # Actual values
    outcome_type: OutcomeType
    actual_loss_usd: float = 0.0
    actual_delay_days: float = 0.0
    action_taken: str = ""
    action_followed_recommendation: bool = False

    # Accuracy
    risk_materialized: bool = False
    prediction_error: float = 0.0       # |predicted - actual| / max(predicted, 1)
    was_accurate: bool = False           # error < threshold
    value_generated_usd: float = 0.0    # loss_avoided - action_cost

    recorded_at: str = ""
    recorded_by: Optional[str] = None
    notes: Optional[str] = None


class OutcomeRecordRequest(BaseModel):
    """Request to record an outcome."""
    decision_id: str
    outcome_type: OutcomeType
    actual_loss_usd: float = 0.0
    actual_delay_days: float = 0.0
    action_taken: str = ""
    action_followed_recommendation: bool = False
    notes: Optional[str] = None


class AccuracyReport(BaseModel):
    """Prediction accuracy over a period."""
    period: str
    generated_at: str
    total_decisions: int
    total_outcomes: int
    coverage: float                     # outcomes / decisions

    # Accuracy metrics
    brier_score: float                  # Lower = better (0 = perfect)
    mean_absolute_error: float
    accuracy_rate: float                # % of decisions within threshold
    calibration_drift: float            # How far off current calibration is

    # Breakdown
    true_positives: int                 # Predicted risk, risk happened
    true_negatives: int                 # Predicted safe, stayed safe
    false_positives: int                # Predicted risk, nothing happened
    false_negatives: int                # Predicted safe, risk happened

    precision: float
    recall: float
    f1_score: float

    recommendation: str


class ROIReport(BaseModel):
    """Return on Investment from RiskCast decisions."""
    period: str
    generated_at: str
    total_decisions: int
    decisions_with_outcomes: int

    # Financial
    total_predicted_loss_usd: float
    total_actual_loss_usd: float
    total_loss_avoided_usd: float
    total_action_cost_usd: float
    net_value_generated_usd: float      # loss_avoided - action_cost
    roi_ratio: float                    # net_value / action_cost

    # Effectiveness
    recommendation_follow_rate: float   # % of decisions where action matched recommendation
    actions_that_helped: int
    actions_that_didnt_help: int

    recommendation: str
