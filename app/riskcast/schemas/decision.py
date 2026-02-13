"""Decision Schemas - The 7 Questions format for RISKCAST.

THE FINAL OUTPUT OF RISKCAST.

Every decision MUST answer all 7 questions. No exceptions.
This is what makes RISKCAST a DECISION system, not a NOTIFICATION system.

Q1: What is happening?       → Personalized event summary
Q2: When?                    → Timeline + urgency
Q3: How bad?                 → $ exposure + delay days + CONFIDENCE INTERVALS
Q4: Why?                     → Causal chain + evidence
Q5: What to do?              → Specific action + cost + deadline + CONFIDENCE INTERVALS
Q6: How confident?           → Score + factors + caveats + CALIBRATED SCORE
Q7: What if I do nothing?    → Inaction cost + point of no return + CONFIDENCE INTERVALS

This version addresses audit gaps:
- A2.2: All numeric outputs have 90% and 95% confidence intervals
- A4.4: ConfidenceGuidance provides actionable uncertainty information
"""

from datetime import datetime, timedelta
from typing import Optional, Tuple, TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.riskcast.constants import ConfidenceLevel, Severity, Urgency

if TYPE_CHECKING:
    from app.uncertainty.communication import ConfidenceGuidance


# ============================================================================
# Q1: WHAT IS HAPPENING?
# ============================================================================


class Q1WhatIsHappening(BaseModel):
    """
    Q1: What is happening?

    NOT: "Red Sea disruption detected"
    YES: "Red Sea disruption affecting YOUR route Shanghai→Rotterdam"

    Must be personalized to the customer's specific shipments.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "event_type": "DISRUPTION",
                "event_summary": "Red Sea disruption affecting your Shanghai→Rotterdam route",
                "affected_chokepoint": "red_sea",
                "affected_routes": ["CNSHA-NLRTM"],
                "affected_shipments": ["PO-4521", "PO-4522"],
            }
        }
    )

    event_type: str = Field(
        description="Type of event",
        examples=["DISRUPTION", "CONGESTION", "RATE_SPIKE", "WEATHER"],
    )
    event_summary: str = Field(
        max_length=150,
        description="One-line personalized summary",
    )
    affected_chokepoint: str = Field(description="Primary chokepoint affected")
    affected_routes: list[str] = Field(
        default_factory=list,
        description="Customer's routes that are affected",
    )
    affected_shipments: list[str] = Field(
        default_factory=list,
        description="Customer's shipment IDs that are affected",
    )

    @computed_field
    @property
    def shipment_count(self) -> int:
        """Number of affected shipments."""
        return len(self.affected_shipments)


# ============================================================================
# Q2: WHEN WILL IT HAPPEN?
# ============================================================================


class Q2WhenWillItHappen(BaseModel):
    """
    Q2: When will it happen / is it happening?

    NOT: "Ongoing situation"
    YES: "Impact starts in 3-5 days for your shipment PO-4521"

    Must include urgency level and reason.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "CONFIRMED",
                "impact_timeline": "Impact starts in 3 days for your earliest shipment",
                "urgency": "immediate",
                "urgency_reason": "Disruption confirmed, act now",
            }
        }
    )

    status: str = Field(
        description="PREDICTED / MATERIALIZING / CONFIRMED / ONGOING",
    )
    impact_timeline: str = Field(
        max_length=150,
        description="When customer will feel the impact",
    )
    earliest_impact: Optional[datetime] = Field(
        default=None,
        description="Earliest expected impact time",
    )
    latest_resolution: Optional[datetime] = Field(
        default=None,
        description="Expected resolution time",
    )
    urgency: Urgency = Field(description="Urgency level")
    urgency_reason: str = Field(
        max_length=100,
        description="Why this urgency level",
    )

    @computed_field
    @property
    def days_until_impact(self) -> Optional[int]:
        """Days until earliest impact."""
        if self.earliest_impact:
            delta = self.earliest_impact - datetime.utcnow()
            return max(0, delta.days)
        return None


# ============================================================================
# Q3: HOW BAD IS IT?
# ============================================================================


class Q3HowBadIsIt(BaseModel):
    """
    Q3: How severe is this?

    NOT: "Significant impact expected"
    YES: "Your exposure: $235K across 5 containers. Expected delay: 10-14 days."

    Must include specific dollar amounts and day counts WITH CONFIDENCE INTERVALS.
    
    Addresses audit gap A2.2 (Confidence Intervals).
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total_exposure_usd": 235000,
                "expected_delay_days": 12,
                "delay_range": "10-14 days",
                "severity": "high",
                "exposure_ci_90": (188000, 294000),
                "exposure_ci_95": (176000, 320000),
                "delay_ci_90": (9, 15),
            }
        }
    )

    # Exposure in dollars
    total_exposure_usd: float = Field(
        ge=0,
        description="Total $ at risk (point estimate)",
    )
    exposure_breakdown: dict[str, float] = Field(
        default_factory=dict,
        description="Breakdown by category (cargo, penalties, etc.)",
    )
    
    # NEW: Exposure confidence intervals (A2.2)
    exposure_ci_90: Tuple[float, float] = Field(
        default=(0.0, 0.0),
        description="90% confidence interval for total exposure",
    )
    exposure_ci_95: Tuple[float, float] = Field(
        default=(0.0, 0.0),
        description="95% confidence interval for total exposure",
    )
    
    # NEW: Risk metrics (A2.2)
    exposure_var_95: float = Field(
        default=0.0,
        ge=0,
        description="Value at Risk 95% - worst case exposure at 95% confidence",
    )
    exposure_cvar_95: float = Field(
        default=0.0,
        ge=0,
        description="Conditional VaR - expected exposure in worst 5% scenarios",
    )

    # Delay
    expected_delay_days: int = Field(
        ge=0,
        description="Expected delay in days (point estimate)",
    )
    delay_range: str = Field(
        description="Delay range as string",
        examples=["10-14 days", "7 days"],
    )
    
    # NEW: Delay confidence interval (A2.2)
    delay_ci_90: Tuple[float, float] = Field(
        default=(0.0, 0.0),
        description="90% confidence interval for delay in days",
    )

    # Shipment impact
    shipments_affected: int = Field(
        ge=0,
        description="Number of shipments affected",
    )
    shipments_with_penalties: int = Field(
        default=0,
        ge=0,
        description="Shipments that will trigger penalties",
    )

    # Severity label
    severity: Severity = Field(description="Impact severity level")
    
    # NEW: Uncertainty summary string (A4.4)
    exposure_uncertainty_summary: str = Field(
        default="",
        description="Plain language uncertainty summary, e.g., '$235K [188K-294K] (90% CI)'",
    )

    @computed_field
    @property
    def has_penalty_risk(self) -> bool:
        """Are any shipments at risk of penalties?"""
        return self.shipments_with_penalties > 0

    @computed_field
    @property
    def exposure_str(self) -> str:
        """Formatted exposure string."""
        return f"${self.total_exposure_usd:,.0f}"
    
    @computed_field
    @property
    def exposure_range_str(self) -> str:
        """Formatted exposure with range."""
        if self.exposure_ci_90[0] > 0:
            return f"${self.total_exposure_usd:,.0f} [${self.exposure_ci_90[0]:,.0f}-${self.exposure_ci_90[1]:,.0f}]"
        return self.exposure_str
    
    @computed_field
    @property
    def is_highly_uncertain(self) -> bool:
        """Flag if exposure uncertainty is > 50% of point estimate."""
        if self.total_exposure_usd == 0 or self.exposure_ci_90 == (0.0, 0.0):
            return False
        ci_width = self.exposure_ci_90[1] - self.exposure_ci_90[0]
        return ci_width / self.total_exposure_usd > 0.5


# ============================================================================
# Q4: WHY IS THIS HAPPENING?
# ============================================================================


class Q4WhyIsThisHappening(BaseModel):
    """
    Q4: Why is this happening?

    NOT: "Geopolitical tensions"
    YES: "Houthi attacks on vessels → carriers avoiding Suez → 10-14 day longer route"

    Must include causal chain that users can understand.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "root_cause": "Houthi attacks on commercial vessels",
                "causal_chain": [
                    "Houthi attacks",
                    "Carriers avoiding Red Sea",
                    "Rerouting via Cape",
                    "10-14 day additional transit",
                ],
                "evidence_summary": "78% market probability | 47 vessels rerouting",
                "sources": ["Polymarket", "MarineTraffic"],
            }
        }
    )

    root_cause: str = Field(
        max_length=150,
        description="Root cause in plain language",
    )
    causal_chain: list[str] = Field(
        min_length=1,
        description="Step-by-step cause → effect chain",
    )
    evidence_summary: str = Field(
        max_length=200,
        description="Summary of supporting evidence",
    )
    sources: list[str] = Field(
        default_factory=list,
        description="Data sources used",
    )

    @computed_field
    @property
    def chain_str(self) -> str:
        """Causal chain as arrow-separated string."""
        return " → ".join(self.causal_chain[:4])


# ============================================================================
# Q5: WHAT TO DO NOW?
# ============================================================================


class Q5WhatToDoNow(BaseModel):
    """
    Q5: What should I do RIGHT NOW?

    NOT: "Consider alternative routes"
    YES: "REROUTE shipment PO-4521 via Cape with MSC. Cost: $8,500 [$7,200-$10,100 90% CI]. Book by 6PM today."

    Must be specific, actionable, with cost, CI, and deadline.
    
    Addresses audit gap A2.2 (Confidence Intervals).
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "action_type": "REROUTE",
                "action_summary": "Reroute 2 shipments via Cape with MSC",
                "estimated_cost_usd": 8500,
                "deadline": "2024-02-05T18:00:00Z",
                "cost_ci_90": (7200, 10100),
                "expected_utility": 145000,
            }
        }
    )

    action_type: str = Field(
        description="REROUTE / DELAY / INSURE / MONITOR / DO_NOTHING",
    )
    action_summary: str = Field(
        max_length=150,
        description="Specific action in one line",
    )

    # Specifics
    affected_shipments: list[str] = Field(
        default_factory=list,
        description="Shipments this action applies to",
    )
    recommended_carrier: Optional[str] = Field(
        default=None,
        description="Recommended carrier code",
    )
    estimated_cost_usd: float = Field(
        ge=0,
        description="Total cost to execute this action (point estimate)",
    )
    
    # NEW: Cost confidence intervals (A2.2)
    cost_ci_90: Tuple[float, float] = Field(
        default=(0.0, 0.0),
        description="90% confidence interval for action cost",
    )
    cost_ci_95: Tuple[float, float] = Field(
        default=(0.0, 0.0),
        description="95% confidence interval for action cost",
    )

    # Execution
    execution_steps: list[str] = Field(
        default_factory=list,
        description="Step-by-step execution guide",
    )
    deadline: datetime = Field(description="When this action must be executed by")
    deadline_reason: str = Field(
        max_length=150,
        description="Why this deadline matters",
    )

    # Contact
    who_to_contact: Optional[str] = Field(
        default=None,
        description="Who to contact for this action",
    )
    contact_info: Optional[str] = Field(
        default=None,
        description="Contact details",
    )
    
    # NEW: Utility with uncertainty (A2.2)
    expected_utility: float = Field(
        default=0.0,
        description="Expected utility (benefit - cost) of taking action",
    )
    utility_ci_90: Tuple[float, float] = Field(
        default=(0.0, 0.0),
        description="90% confidence interval for utility",
    )
    
    # NEW: Success probability (A2.2)
    success_probability: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Probability that action achieves desired outcome",
    )
    success_probability_ci: Tuple[float, float] = Field(
        default=(0.6, 0.95),
        description="90% confidence interval for success probability",
    )
    
    # NEW: Cost uncertainty summary (A4.4)
    cost_uncertainty_summary: str = Field(
        default="",
        description="Plain language cost uncertainty, e.g., '$8,500 [$7,200-$10,100]'",
    )

    @computed_field
    @property
    def cost_str(self) -> str:
        """Formatted cost string."""
        return f"${self.estimated_cost_usd:,.0f}"
    
    @computed_field
    @property
    def cost_with_range_str(self) -> str:
        """Formatted cost with CI range."""
        if self.cost_ci_90[0] > 0:
            return f"${self.estimated_cost_usd:,.0f} [${self.cost_ci_90[0]:,.0f}-${self.cost_ci_90[1]:,.0f}]"
        return self.cost_str

    @computed_field
    @property
    def deadline_str(self) -> str:
        """Formatted deadline string."""
        return self.deadline.strftime("%b %d, %H:%M UTC")

    @computed_field
    @property
    def hours_until_deadline(self) -> float:
        """Hours until deadline."""
        delta = self.deadline - datetime.utcnow()
        return max(0, delta.total_seconds() / 3600)


# ============================================================================
# Q6: HOW CONFIDENT?
# ============================================================================


class Q6HowConfident(BaseModel):
    """
    Q6: How confident are we in this recommendation?

    NOT: "High confidence"
    YES: "87% confidence based on: Polymarket (78%), 47 vessels already rerouting, rates up 35%"

    Must include factors that explain the confidence.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "score": 0.87,
                "level": "high",
                "explanation": "87% confidence based on: Market probability 78%, 47 vessels confirming",
            }
        }
    )

    score: float = Field(
        ge=0,
        le=1,
        description="Confidence score 0-1",
    )
    level: ConfidenceLevel = Field(description="Confidence level")

    # Factors
    factors: dict[str, float] = Field(
        default_factory=dict,
        description="Confidence factor breakdown",
    )

    # Explanation
    explanation: str = Field(
        max_length=250,
        description="Human-readable confidence explanation",
    )

    # Caveats
    caveats: list[str] = Field(
        default_factory=list,
        description="Things that could change the assessment",
    )

    @computed_field
    @property
    def score_pct(self) -> str:
        """Confidence score as percentage string."""
        return f"{int(self.score * 100)}%"

    @computed_field
    @property
    def is_actionable(self) -> bool:
        """Is confidence high enough to act?"""
        return self.level in [ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM]


# ============================================================================
# Q7: WHAT IF I DO NOTHING?
# ============================================================================


class Q7WhatIfNothing(BaseModel):
    """
    Q7: What happens if I don't act?

    NOT: "Risk increases over time"
    YES: "If wait 6h: cost +$15K [$12K-$19K]. If wait 24h: booking window closes.
          Total expected loss if no action: $47K [$38K-$59K 90% CI]."

    Must include time-based cost escalation WITH CONFIDENCE INTERVALS.
    
    Addresses audit gap A2.2 (Confidence Intervals).
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "expected_loss_if_nothing": 47000,
                "cost_if_wait_6h": 52000,
                "cost_if_wait_24h": 61000,
                "cost_if_wait_48h": 70000,
                "inaction_summary": "Point of no return in 48h. Expected loss: $47,000",
                "loss_ci_90": (38000, 59000),
                "cost_if_wait_6h_ci": (42000, 64000),
            }
        }
    )

    # Immediate cost
    expected_loss_if_nothing: float = Field(
        ge=0,
        description="$ loss if no action taken (point estimate)",
    )
    
    # NEW: Loss confidence intervals (A2.2)
    loss_ci_90: Tuple[float, float] = Field(
        default=(0.0, 0.0),
        description="90% confidence interval for expected loss",
    )
    loss_ci_95: Tuple[float, float] = Field(
        default=(0.0, 0.0),
        description="95% confidence interval for expected loss",
    )

    # Time-based escalation
    cost_if_wait_6h: float = Field(
        ge=0,
        description="Cost if wait 6 hours (point estimate)",
    )
    cost_if_wait_24h: float = Field(
        ge=0,
        description="Cost if wait 24 hours (point estimate)",
    )
    cost_if_wait_48h: float = Field(
        ge=0,
        description="Cost if wait 48 hours (point estimate)",
    )
    
    # NEW: Time decay confidence intervals (A2.2)
    cost_if_wait_6h_ci: Tuple[float, float] = Field(
        default=(0.0, 0.0),
        description="90% CI for cost if wait 6 hours",
    )
    cost_if_wait_24h_ci: Tuple[float, float] = Field(
        default=(0.0, 0.0),
        description="90% CI for cost if wait 24 hours",
    )
    cost_if_wait_48h_ci: Tuple[float, float] = Field(
        default=(0.0, 0.0),
        description="90% CI for cost if wait 48 hours",
    )

    # Point of no return
    point_of_no_return: Optional[datetime] = Field(
        default=None,
        description="After this, options become severely limited",
    )
    point_of_no_return_reason: Optional[str] = Field(
        default=None,
        max_length=150,
        description="Why this is the point of no return",
    )

    # Worst case
    worst_case_cost: float = Field(
        ge=0,
        description="Worst case total cost (95th percentile)",
    )
    worst_case_scenario: str = Field(
        max_length=200,
        description="Description of worst case",
    )

    # Summary
    inaction_summary: str = Field(
        max_length=200,
        description="One-line summary of inaction consequences",
    )
    
    # NEW: Loss uncertainty summary (A4.4)
    loss_uncertainty_summary: str = Field(
        default="",
        description="Plain language loss uncertainty, e.g., '$47K [$38K-$59K]'",
    )

    @computed_field
    @property
    def expected_loss_str(self) -> str:
        """Formatted expected loss."""
        return f"${self.expected_loss_if_nothing:,.0f}"
    
    @computed_field
    @property
    def expected_loss_with_range_str(self) -> str:
        """Formatted expected loss with CI range."""
        if self.loss_ci_90[0] > 0:
            return f"${self.expected_loss_if_nothing:,.0f} [${self.loss_ci_90[0]:,.0f}-${self.loss_ci_90[1]:,.0f}]"
        return self.expected_loss_str

    @computed_field
    @property
    def cost_escalation_6h(self) -> float:
        """Cost increase percentage at 6 hours."""
        if self.expected_loss_if_nothing == 0:
            return 0.0
        return ((self.cost_if_wait_6h - self.expected_loss_if_nothing) / self.expected_loss_if_nothing) * 100

    @computed_field
    @property
    def cost_escalation_24h(self) -> float:
        """Cost increase percentage at 24 hours."""
        if self.expected_loss_if_nothing == 0:
            return 0.0
        return ((self.cost_if_wait_24h - self.expected_loss_if_nothing) / self.expected_loss_if_nothing) * 100

    @computed_field
    @property
    def hours_until_no_return(self) -> Optional[float]:
        """Hours until point of no return."""
        if self.point_of_no_return:
            delta = self.point_of_no_return - datetime.utcnow()
            return max(0, delta.total_seconds() / 3600)
        return None


# ============================================================================
# DECISION OBJECT (COMPLETE OUTPUT)
# ============================================================================


class DecisionObject(BaseModel):
    """
    THE FINAL OUTPUT OF RISKCAST.

    Every field is MANDATORY. No optional questions.
    This is the contract with the user.

    A DecisionObject transforms INFORMATION into ACTION.
    
    This version addresses audit gaps:
    - A2.2: Q3, Q5, Q7 include confidence intervals
    - A4.4: confidence_guidance provides actionable uncertainty information
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "decision_id": "dec_20240205143022_cust_abc",
                "customer_id": "cust_abc123",
                "signal_id": "OMEN-RS-2024-001",
                "q1_what": {"event_type": "DISRUPTION"},
                "q2_when": {"status": "CONFIRMED", "urgency": "immediate"},
                "q3_severity": {"total_exposure_usd": 235000, "severity": "high", "exposure_ci_90": (188000, 294000)},
                "q4_why": {"root_cause": "Houthi attacks"},
                "q5_action": {"action_type": "REROUTE", "estimated_cost_usd": 8500, "cost_ci_90": (7200, 10100)},
                "q6_confidence": {"score": 0.87, "level": "high"},
                "q7_inaction": {"expected_loss_if_nothing": 47000, "loss_ci_90": (38000, 59000)},
            }
        }
    )

    # Metadata
    decision_id: str = Field(description="Unique decision ID")
    customer_id: str = Field(description="Customer this decision is for")
    signal_id: str = Field(description="Signal that triggered this decision")
    
    # Schema versioning (for backward compatibility)
    schema_version: str = Field(
        default="2.1.0",  # Bumped for CI fields
        description="Schema version for backward compatibility",
    )
    
    # Audit fields
    created_by: Optional[str] = Field(
        default="system",
        description="Who/what created this decision (system, api, etc.)",
    )
    ml_model_version: Optional[str] = Field(
        default=None,
        description="ML model version used for predictions",
    )

    # 7 MANDATORY QUESTIONS
    q1_what: Q1WhatIsHappening = Field(description="Q1: What is happening?")
    q2_when: Q2WhenWillItHappen = Field(description="Q2: When?")
    q3_severity: Q3HowBadIsIt = Field(description="Q3: How bad? (with confidence intervals)")
    q4_why: Q4WhyIsThisHappening = Field(description="Q4: Why?")
    q5_action: Q5WhatToDoNow = Field(description="Q5: What to do? (with cost CIs)")
    q6_confidence: Q6HowConfident = Field(description="Q6: How confident?")
    q7_inaction: Q7WhatIfNothing = Field(description="Q7: What if nothing? (with loss CIs)")
    
    # NEW: Confidence guidance (addresses A4.4)
    confidence_guidance: Optional["ConfidenceGuidance"] = Field(
        default=None,
        description="Actionable guidance based on confidence levels (A4.4)",
    )

    # Alternative actions (for advanced users)
    alternative_actions: list[dict] = Field(
        default_factory=list,
        description="Other viable options (top 3)",
    )

    # Timestamps
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime = Field(description="When this decision becomes stale")

    # Tracking
    was_acted_upon: Optional[bool] = Field(
        default=None,
        description="Did user take action?",
    )
    user_feedback: Optional[str] = Field(
        default=None,
        description="User feedback on decision",
    )

    @computed_field
    @property
    def is_expired(self) -> bool:
        """Is this decision expired?"""
        return datetime.utcnow() > self.expires_at

    @computed_field
    @property
    def hours_until_expiry(self) -> float:
        """Hours until decision expires."""
        delta = self.expires_at - datetime.utcnow()
        return max(0, delta.total_seconds() / 3600)

    @computed_field
    @property
    def primary_action_type(self) -> str:
        """Primary action type for quick access."""
        return self.q5_action.action_type

    @computed_field
    @property
    def is_actionable(self) -> bool:
        """Should user take action (not monitor/do_nothing)?"""
        return self.q5_action.action_type not in ["DO_NOTHING", "MONITOR"]

    def get_summary(self) -> str:
        """Get one-line decision summary."""
        return (
            f"{self.q5_action.action_type}: {self.q5_action.action_summary} "
            f"(Cost: {self.q5_action.cost_str}, Deadline: {self.q5_action.deadline_str})"
        )

    def get_inaction_warning(self) -> str:
        """Get inaction warning for display."""
        return (
            f"If no action: {self.q7_inaction.expected_loss_str} expected loss. "
            f"If wait 24h: ${self.q7_inaction.cost_if_wait_24h:,.0f}"
        )
    
    def get_summary_with_uncertainty(self) -> str:
        """Get decision summary including uncertainty ranges."""
        cost_str = self.q5_action.cost_with_range_str
        return (
            f"{self.q5_action.action_type}: {self.q5_action.action_summary} "
            f"(Cost: {cost_str}, Deadline: {self.q5_action.deadline_str})"
        )
    
    def get_inaction_warning_with_uncertainty(self) -> str:
        """Get inaction warning with uncertainty ranges."""
        return (
            f"If no action: {self.q7_inaction.expected_loss_with_range_str} expected loss. "
            f"If wait 24h: ${self.q7_inaction.cost_if_wait_24h:,.0f}"
        )


# Resolve forward reference for ConfidenceGuidance
# This is needed because ConfidenceGuidance is defined in app.uncertainty.communication
# and we use TYPE_CHECKING to avoid circular imports
def _rebuild_models():
    """Rebuild models to resolve forward references."""
    try:
        from app.uncertainty.communication import ConfidenceGuidance
        DecisionObject.model_rebuild()
    except ImportError:
        # ConfidenceGuidance not available yet (e.g., during initial import)
        pass

_rebuild_models()
