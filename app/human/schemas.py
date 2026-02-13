"""
Human-AI collaboration schemas.

These schemas define the data structures for:
- Override requests and results
- Escalation requests and resolutions
- Feedback submissions

All schemas support audit trail integration.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator
from enum import Enum


# ============================================================================
# OVERRIDE SCHEMAS
# ============================================================================


class OverrideReason(str, Enum):
    """Standard reasons for overriding a decision."""
    BETTER_INFORMATION = "better_information"    # Human has info system doesn't
    CUSTOMER_REQUEST = "customer_request"        # Customer wants different action
    MARKET_CHANGE = "market_change"              # Conditions changed since decision
    SYSTEM_ERROR = "system_error"                # System made obvious error
    RISK_TOLERANCE = "risk_tolerance"            # Customer risk tolerance differs
    STRATEGIC = "strategic"                      # Strategic business reason
    RELATIONSHIP = "relationship"                # Carrier/customer relationship
    TIMING = "timing"                            # Timing considerations
    OTHER = "other"                              # Other reason (must explain)


class OverrideRequest(BaseModel):
    """
    Request to override a decision.
    
    MUST include detailed reason for audit trail.
    """
    decision_id: str = Field(description="ID of decision to override")
    new_action_type: str = Field(
        description="New action type (e.g., 'reroute', 'delay', 'monitor')"
    )
    new_action_details: Optional[dict] = Field(
        default=None,
        description="Additional details for the new action",
    )
    reason: OverrideReason = Field(
        description="Categorized reason for override"
    )
    reason_details: str = Field(
        min_length=20,
        description="Detailed explanation (minimum 20 characters)",
    )
    supporting_evidence: Optional[List[str]] = Field(
        default=None,
        description="Supporting evidence or references",
    )
    
    @field_validator('reason_details')
    @classmethod
    def validate_reason_details(cls, v: str) -> str:
        """Ensure reason details are meaningful."""
        if len(v.strip()) < 20:
            raise ValueError("Reason details must be at least 20 characters")
        return v.strip()


class OverrideResult(BaseModel):
    """Result of override operation."""
    override_id: str = Field(description="Unique override identifier")
    decision_id: str = Field(description="ID of overridden decision")
    original_action: str = Field(description="Original recommended action")
    new_action: str = Field(description="New action after override")
    overridden_by: str = Field(description="User ID who made the override")
    overridden_at: datetime = Field(description="When override was made")
    reason: OverrideReason = Field(description="Categorized reason")
    reason_details: str = Field(description="Detailed explanation")
    audit_record_id: str = Field(description="ID of audit record for this override")


# ============================================================================
# ESCALATION SCHEMAS
# ============================================================================


class EscalationTrigger(str, Enum):
    """Reasons for escalating to human review."""
    LOW_CONFIDENCE = "low_confidence"            # Confidence below threshold
    HIGH_VALUE = "high_value"                    # Exposure above threshold
    NOVEL_SITUATION = "novel_situation"          # No similar historical cases
    CONFLICTING_SIGNALS = "conflicting_signals"  # Signals contradict each other
    CUSTOMER_FLAG = "customer_flag"              # Customer flagged for manual review
    SYSTEM_DEGRADED = "system_degraded"          # System in degraded mode
    MANUAL_REQUEST = "manual_request"            # User requested escalation
    MULTIPLE_ACTIONS = "multiple_actions"        # Multiple equally good actions
    TIME_CRITICAL = "time_critical"              # Very tight deadline
    REGULATORY = "regulatory"                    # Regulatory compliance concern


class EscalationRequest(BaseModel):
    """Decision escalated to human review."""
    escalation_id: str = Field(description="Unique escalation identifier")
    decision_id: str = Field(description="ID of decision being escalated")
    customer_id: str = Field(description="Customer ID")
    
    # Trigger info
    trigger: EscalationTrigger = Field(description="What triggered escalation")
    trigger_details: str = Field(description="Detailed explanation of trigger")
    
    # Decision context
    confidence_at_escalation: float = Field(
        ge=0.0, le=1.0,
        description="Confidence score at time of escalation"
    )
    exposure_usd: Optional[float] = Field(
        default=None,
        ge=0,
        description="Total exposure in USD"
    )
    
    # System recommendation
    recommended_action: str = Field(description="What system would have recommended")
    alternative_actions: List[str] = Field(
        default_factory=list,
        description="Other actions considered"
    )
    
    # Routing
    escalated_to: List[str] = Field(
        default_factory=list,
        description="User IDs to notify"
    )
    deadline: datetime = Field(description="When decision is needed")
    
    # Timestamps
    escalated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When escalation was created"
    )
    
    # Status
    status: str = Field(default="pending", description="pending, resolved, expired")


class EscalationResolution(BaseModel):
    """Resolution of an escalated decision."""
    escalation_id: str = Field(description="ID of resolved escalation")
    resolved_by: str = Field(description="User ID who resolved")
    resolved_at: datetime = Field(description="When resolution was made")
    
    # Resolution details
    resolution: str = Field(
        description="Resolution type: APPROVE, MODIFY, REJECT"
    )
    final_action: str = Field(description="Final action to take")
    resolution_reason: str = Field(description="Explanation of resolution")
    
    # Metrics
    time_to_resolution_minutes: int = Field(
        ge=0,
        description="Minutes from escalation to resolution"
    )
    
    @field_validator('resolution')
    @classmethod
    def validate_resolution(cls, v: str) -> str:
        """Ensure resolution is valid."""
        valid = ["APPROVE", "MODIFY", "REJECT"]
        if v.upper() not in valid:
            raise ValueError(f"Resolution must be one of: {valid}")
        return v.upper()


# ============================================================================
# FEEDBACK SCHEMAS
# ============================================================================


class FeedbackType(str, Enum):
    """Types of feedback."""
    DECISION_QUALITY = "decision_quality"        # Overall decision quality
    TIMING = "timing"                            # Was timing advice accurate?
    COST_ACCURACY = "cost_accuracy"              # Were cost estimates accurate?
    DELAY_ACCURACY = "delay_accuracy"            # Were delay estimates accurate?
    COMMUNICATION = "communication"              # How well was it communicated?
    ACTIONABILITY = "actionability"              # Could action be taken?
    GENERAL = "general"                          # General feedback


class FeedbackSubmission(BaseModel):
    """
    User feedback on a decision.
    
    Used for:
    - Tracking decision quality
    - Improving calibration
    - Training ML models
    """
    decision_id: str = Field(description="ID of decision receiving feedback")
    
    # Rating
    feedback_type: FeedbackType = Field(description="Category of feedback")
    rating: int = Field(
        ge=1, le=5,
        description="Rating from 1 (poor) to 5 (excellent)"
    )
    
    # Qualitative feedback
    comment: str = Field(
        min_length=0,
        max_length=2000,
        description="Free-text feedback"
    )
    
    # Follow-up indicators
    would_follow_again: bool = Field(
        description="Would user follow similar advice in future?"
    )
    
    # Actual outcome (for calibration)
    actual_outcome: Optional[dict] = Field(
        default=None,
        description="What actually happened (if known)"
    )
    
    # Optional detailed outcome fields
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


# ============================================================================
# TRUST METRICS SCHEMAS
# ============================================================================


# ============================================================================
# CHALLENGE SCHEMAS (C2.2: Challenge Handling)
# ============================================================================


class ChallengeReason(str, Enum):
    """Standard reasons for challenging a decision."""
    INCORRECT_DATA = "incorrect_data"              # Data used was incorrect
    INCOMPLETE_ANALYSIS = "incomplete_analysis"    # Analysis missed factors
    CALCULATION_ERROR = "calculation_error"        # Mathematical/calculation error
    METHODOLOGY_FLAW = "methodology_flaw"          # Flawed reasoning methodology
    CHANGED_CIRCUMSTANCES = "changed_circumstances"  # Circumstances changed
    CUSTOMER_DISAGREEMENT = "customer_disagreement"  # Customer disagrees with assessment
    OUTCOME_DIFFERENT = "outcome_different"        # Actual outcome differed from prediction
    LEGAL_COMPLIANCE = "legal_compliance"          # Legal/compliance concerns
    OTHER = "other"                                # Other reason (must explain)


class ChallengeStatus(str, Enum):
    """Status of a decision challenge."""
    SUBMITTED = "submitted"           # Challenge submitted, pending review
    UNDER_REVIEW = "under_review"     # Being actively reviewed
    NEEDS_INFO = "needs_info"         # Reviewer needs more information
    UPHELD = "upheld"                 # Original decision upheld
    PARTIALLY_UPHELD = "partially_upheld"  # Partially upheld
    OVERTURNED = "overturned"         # Decision overturned
    WITHDRAWN = "withdrawn"           # Challenger withdrew


class ChallengeRequest(BaseModel):
    """
    Request to challenge/dispute a decision.
    
    Used when customer or user believes a decision was:
    - Based on incorrect data
    - Calculated incorrectly
    - Using flawed methodology
    - Led to unexpected/negative outcome
    
    This is CRITICAL for legal defensibility (C2.2).
    All challenges create immutable audit records.
    """
    decision_id: str = Field(description="ID of decision being challenged")
    challenger_id: str = Field(description="User ID of challenger")
    challenger_role: str = Field(
        description="Role: customer, operator, manager, auditor",
    )
    
    # Challenge details
    reason: ChallengeReason = Field(description="Categorized reason for challenge")
    reason_details: str = Field(
        min_length=50,
        description="Detailed explanation of challenge (minimum 50 characters)",
    )
    
    # Evidence of issue
    evidence: List[str] = Field(
        default_factory=list,
        description="Supporting evidence for the challenge",
    )
    
    # Impact claim
    claimed_impact_usd: Optional[float] = Field(
        default=None,
        ge=0,
        description="Claimed financial impact due to following the decision",
    )
    claimed_delay_days: Optional[int] = Field(
        default=None,
        ge=0,
        description="Claimed delay days due to following the decision",
    )
    
    # What challenger wants
    requested_remedy: str = Field(
        description="What remedy/action the challenger is requesting",
    )
    
    # Urgency
    is_urgent: bool = Field(
        default=False,
        description="Whether this challenge requires urgent attention",
    )
    
    @field_validator('reason_details')
    @classmethod
    def validate_reason_details(cls, v: str) -> str:
        """Ensure reason details are meaningful."""
        if len(v.strip()) < 50:
            raise ValueError("Challenge reason details must be at least 50 characters")
        return v.strip()


class ChallengeRecord(BaseModel):
    """Complete record of a decision challenge."""
    challenge_id: str = Field(description="Unique challenge identifier")
    decision_id: str = Field(description="ID of challenged decision")
    customer_id: str = Field(description="Customer ID associated with decision")
    
    # Challenger info
    challenger_id: str = Field(description="User ID of challenger")
    challenger_role: str = Field(description="Role of challenger")
    challenged_at: datetime = Field(description="When challenge was submitted")
    
    # Challenge details
    reason: ChallengeReason = Field(description="Categorized reason")
    reason_details: str = Field(description="Detailed explanation")
    evidence: List[str] = Field(default_factory=list)
    claimed_impact_usd: Optional[float] = None
    claimed_delay_days: Optional[int] = None
    requested_remedy: str = Field(description="Requested remedy")
    
    # Status tracking
    status: ChallengeStatus = Field(description="Current status")
    assigned_to: Optional[str] = Field(
        default=None,
        description="User ID of assigned reviewer",
    )
    assigned_at: Optional[datetime] = Field(
        default=None,
        description="When assigned for review",
    )
    
    # Priority
    priority: str = Field(
        default="normal",
        description="Priority: low, normal, high, critical",
    )
    sla_deadline: Optional[datetime] = Field(
        default=None,
        description="SLA deadline for resolution",
    )
    
    # Resolution (populated when resolved)
    resolution: Optional["ChallengeResolution"] = Field(
        default=None,
        description="Resolution details if resolved",
    )
    
    # Audit
    audit_trail_ids: List[str] = Field(
        default_factory=list,
        description="IDs of audit records for this challenge",
    )


class ChallengeResolution(BaseModel):
    """Resolution of a decision challenge."""
    challenge_id: str = Field(description="ID of resolved challenge")
    
    # Resolution details
    status: ChallengeStatus = Field(
        description="Final status: upheld, partially_upheld, overturned, withdrawn"
    )
    resolved_by: str = Field(description="User ID who resolved")
    resolved_at: datetime = Field(description="When resolved")
    
    # Analysis
    review_summary: str = Field(
        min_length=50,
        description="Summary of the review conducted",
    )
    findings: List[str] = Field(
        description="Key findings from the review",
    )
    
    # Data validity assessment
    original_data_valid: bool = Field(
        description="Was the original data used valid?",
    )
    methodology_valid: bool = Field(
        description="Was the methodology applied correctly?",
    )
    calculations_valid: bool = Field(
        description="Were calculations correct?",
    )
    
    # For overturned/partially upheld
    corrected_action: Optional[str] = Field(
        default=None,
        description="What action should have been recommended",
    )
    corrected_exposure_usd: Optional[float] = Field(
        default=None,
        description="Corrected exposure amount",
    )
    
    # Remedy
    remedy_provided: str = Field(
        description="What remedy was provided to challenger",
    )
    compensation_usd: Optional[float] = Field(
        default=None,
        ge=0,
        description="Any financial compensation provided",
    )
    
    # Systemic improvement
    improvement_actions: List[str] = Field(
        default_factory=list,
        description="Actions to prevent similar issues",
    )
    model_update_required: bool = Field(
        default=False,
        description="Whether this requires model/algorithm updates",
    )
    
    # Metrics
    time_to_resolution_hours: int = Field(
        ge=0,
        description="Hours from challenge to resolution",
    )
    
    @field_validator('status')
    @classmethod
    def validate_status(cls, v: ChallengeStatus) -> ChallengeStatus:
        """Ensure status is a resolution status."""
        valid = [
            ChallengeStatus.UPHELD,
            ChallengeStatus.PARTIALLY_UPHELD,
            ChallengeStatus.OVERTURNED,
            ChallengeStatus.WITHDRAWN,
        ]
        if v not in valid:
            raise ValueError(f"Resolution status must be one of: {[s.value for s in valid]}")
        return v


# ============================================================================
# TRUST METRICS SCHEMAS
# ============================================================================


class TrustMetrics(BaseModel):
    """
    Human-AI trust metrics.
    
    These metrics help understand:
    - How much users trust the system
    - Where the system needs improvement
    - Calibration accuracy
    """
    period_days: int = Field(description="Metric calculation period")
    
    # Decision counts
    total_decisions: int = Field(description="Total decisions in period")
    decisions_followed: int = Field(description="Decisions user followed")
    decisions_overridden: int = Field(description="Decisions overridden")
    decisions_escalated: int = Field(description="Decisions escalated")
    
    # Rates
    follow_rate: float = Field(
        ge=0.0, le=1.0,
        description="% of decisions followed"
    )
    override_rate: float = Field(
        ge=0.0, le=1.0,
        description="% of decisions overridden"
    )
    escalation_rate: float = Field(
        ge=0.0, le=1.0,
        description="% of decisions escalated"
    )
    
    # Feedback metrics
    feedback_count: int = Field(description="Number of feedback submissions")
    average_rating: Optional[float] = Field(
        default=None,
        ge=1.0, le=5.0,
        description="Average feedback rating"
    )
    would_follow_again_rate: Optional[float] = Field(
        default=None,
        ge=0.0, le=1.0,
        description="% who would follow again"
    )
    
    # Calibration metrics
    calibration_accuracy: Optional[float] = Field(
        default=None,
        ge=0.0, le=1.0,
        description="How well predictions matched outcomes"
    )
    
    # Override patterns
    top_override_reasons: List[dict] = Field(
        default_factory=list,
        description="Most common override reasons"
    )
    
    # Escalation patterns
    top_escalation_triggers: List[dict] = Field(
        default_factory=list,
        description="Most common escalation triggers"
    )
