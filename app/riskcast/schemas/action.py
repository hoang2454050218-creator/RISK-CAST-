"""Action Schemas - Action models for RISKCAST decisions.

The Action Generator answers: "What are the possible actions?"

NOT vague recommendations like "consider alternatives".
MUST be specific: "Reroute shipment #4521 via Cape with MSC. Cost: $8,500. Book by 6PM today."
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, computed_field


class ActionType(str, Enum):
    """Types of actions RISKCAST can recommend."""

    # Proactive interventions
    REROUTE = "reroute"  # Change route to avoid disruption
    DELAY = "delay"  # Hold shipment at origin
    SPLIT = "split"  # Split across multiple routes (Phase 2)
    EXPEDITE = "expedite"  # Speed up if possible (Phase 2)

    # Risk transfer
    INSURE = "insure"  # Buy additional insurance

    # Monitoring
    MONITOR = "monitor"  # Watch but don't act yet

    # Baseline
    DO_NOTHING = "do_nothing"  # Accept the risk


class ActionFeasibility(str, Enum):
    """How feasible is this action?"""

    HIGH = "high"  # Can definitely do this
    MEDIUM = "medium"  # Probably can do this
    LOW = "low"  # Might be difficult
    IMPOSSIBLE = "impossible"  # Cannot do this


class Action(BaseModel):
    """
    A concrete, executable action.

    Every action must be specific enough that the user
    can execute it without additional research.

    NOT: "Consider rerouting"
    YES: "Reroute via Cape with MSC. Cost: $8,500. Book by Feb 5, 6PM UTC."
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "action_id": "act_reroute_abc123",
                "action_type": "reroute",
                "summary": "Reroute 2 shipments via Cape with MSC",
                "cost_usd": 8500,
                "risk_mitigated_usd": 47000,
                "feasibility": "high",
            }
        }
    )

    # Identity
    action_id: str = Field(description="Unique action ID")
    action_type: ActionType = Field(description="Type of action")

    # Summary (one line - fits on phone)
    summary: str = Field(
        max_length=100,
        description="One-line action summary",
    )

    # Detailed description
    description: str = Field(
        max_length=500,
        description="Detailed explanation of the action",
    )

    # Execution steps
    steps: list[str] = Field(
        min_length=1,
        description="Step-by-step execution guide",
    )

    # Deadline
    deadline: datetime = Field(
        description="When this action must be executed by",
    )
    deadline_reason: str = Field(
        description="Why this deadline matters",
    )

    # Cost
    cost_usd: float = Field(
        ge=0,
        description="Total cost to execute this action (USD)",
    )
    cost_breakdown: dict[str, float] = Field(
        default_factory=dict,
        description="Itemized cost breakdown",
    )

    # Benefit
    risk_mitigated_usd: float = Field(
        ge=0,
        description="How much risk does this reduce (USD)",
    )
    delay_avoided_days: int = Field(
        default=0,
        ge=0,
        description="Days of delay avoided",
    )

    # Feasibility
    feasibility: ActionFeasibility = Field(description="How feasible is this action")
    feasibility_notes: Optional[str] = Field(
        default=None,
        description="Notes on feasibility",
    )

    # Provider information
    recommended_carrier: Optional[str] = Field(
        default=None,
        description="Recommended carrier code (e.g., MSCU, MAEU)",
    )
    carrier_name: Optional[str] = Field(
        default=None,
        description="Carrier name for display",
    )
    booking_link: Optional[str] = Field(
        default=None,
        description="Link to book this action",
    )
    contact_info: Optional[str] = Field(
        default=None,
        description="Contact information",
    )

    # Affected shipments
    affected_shipment_ids: list[str] = Field(
        default_factory=list,
        description="Shipment IDs this action applies to",
    )

    # Scoring (used for ranking)
    utility_score: float = Field(
        default=0.0,
        ge=0,
        le=1,
        description="Overall utility score (0-1)",
    )

    @computed_field
    @property
    def net_benefit_usd(self) -> float:
        """Net benefit of taking this action (benefit - cost)."""
        return self.risk_mitigated_usd - self.cost_usd

    @computed_field
    @property
    def is_profitable(self) -> bool:
        """Does this action have positive net benefit?"""
        return self.net_benefit_usd > 0

    @computed_field
    @property
    def hours_until_deadline(self) -> float:
        """Hours until deadline."""
        delta = self.deadline - datetime.utcnow()
        return max(0, delta.total_seconds() / 3600)

    @computed_field
    @property
    def is_urgent(self) -> bool:
        """Is deadline within 24 hours?"""
        return self.hours_until_deadline <= 24


class ActionSet(BaseModel):
    """
    Set of possible actions for a decision.

    Always includes DO_NOTHING as baseline for comparison.
    Actions are sorted by utility_score (highest first).
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "customer_id": "cust_abc123",
                "signal_id": "OMEN-RS-2024-001",
                "do_nothing_cost": 47000,
                "primary_action": {"action_type": "reroute"},
            }
        }
    )

    # Identity
    customer_id: str = Field(description="Customer ID")
    signal_id: str = Field(description="Signal ID")

    # All actions (sorted by utility_score descending)
    actions: list[Action] = Field(
        default_factory=list,
        description="All generated actions",
    )

    # Recommendations
    primary_action: Action = Field(description="Top recommended action")
    alternatives: list[Action] = Field(
        default_factory=list,
        description="Alternative viable options (top 3)",
    )

    # Baseline
    do_nothing_cost: float = Field(
        ge=0,
        description="Expected cost if no action taken (USD)",
    )

    # Metadata
    generated_at: datetime = Field(default_factory=datetime.utcnow)

    @computed_field
    @property
    def action_count(self) -> int:
        """Total number of actions generated."""
        return len(self.actions)

    @computed_field
    @property
    def has_profitable_action(self) -> bool:
        """Is there at least one action with positive net benefit?"""
        return any(a.is_profitable for a in self.actions)

    @computed_field
    @property
    def best_net_benefit(self) -> float:
        """Best net benefit among all actions."""
        if not self.actions:
            return 0.0
        return max(a.net_benefit_usd for a in self.actions)

    def get_actions_by_type(self, action_type: ActionType) -> list[Action]:
        """Get all actions of a specific type."""
        return [a for a in self.actions if a.action_type == action_type]

    def get_feasible_actions(self) -> list[Action]:
        """Get all feasible actions (excluding IMPOSSIBLE)."""
        return [
            a for a in self.actions if a.feasibility != ActionFeasibility.IMPOSSIBLE
        ]


class TimePoint(BaseModel):
    """A point in time with associated costs for trade-off analysis."""

    hours_from_now: int = Field(description="Hours from now")
    timestamp: datetime = Field(description="Actual timestamp")
    description: str = Field(description="What this time point represents")

    # Costs at this time
    do_nothing_cost: float = Field(
        ge=0,
        description="Cost if no action by this time (USD)",
    )
    reroute_cost: float = Field(
        default=0,
        ge=0,
        description="Cost to reroute at this time (USD)",
    )

    # What changes
    what_changes: str = Field(description="What happens at this time")

    # Is this a deadline?
    is_deadline: bool = Field(default=False)
    deadline_type: Optional[str] = Field(
        default=None,
        description="Type of deadline: booking_closes, penalty_starts, etc.",
    )


class InactionConsequence(BaseModel):
    """
    What happens if customer does nothing.

    This is the answer to Q7: "What if I don't act?"

    NOT: "Risk increases over time"
    YES: "If wait 6h: +$15K. If wait 24h: booking closes. Total loss: $47K."
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "immediate_cost_usd": 47000,
                "cost_at_24h": 61000,
                "worst_case_cost_usd": 94000,
            }
        }
    )

    # Immediate cost (current expected loss)
    immediate_cost_usd: float = Field(
        ge=0,
        description="Current expected loss if no action (USD)",
    )

    # Time-based cost escalation
    cost_at_6h: float = Field(ge=0, description="Cost if wait 6 hours (USD)")
    cost_at_24h: float = Field(ge=0, description="Cost if wait 24 hours (USD)")
    cost_at_48h: float = Field(ge=0, description="Cost if wait 48 hours (USD)")

    # Key deadlines
    deadlines: list[TimePoint] = Field(
        default_factory=list,
        description="Key deadlines and their consequences",
    )

    # Point of no return
    point_of_no_return: Optional[datetime] = Field(
        default=None,
        description="After this, options severely limited",
    )
    point_of_no_return_reason: Optional[str] = Field(
        default=None,
        description="Why this is the point of no return",
    )

    # Worst case
    worst_case_cost_usd: float = Field(
        ge=0,
        description="Worst case total cost (USD)",
    )
    worst_case_scenario: str = Field(
        max_length=200,
        description="Description of worst case scenario",
    )

    @computed_field
    @property
    def cost_increase_6h(self) -> float:
        """Cost increase if wait 6 hours."""
        return self.cost_at_6h - self.immediate_cost_usd

    @computed_field
    @property
    def cost_increase_24h(self) -> float:
        """Cost increase if wait 24 hours."""
        return self.cost_at_24h - self.immediate_cost_usd

    @computed_field
    @property
    def cost_increase_pct_24h(self) -> float:
        """Percentage cost increase at 24h."""
        if self.immediate_cost_usd == 0:
            return 0.0
        return (self.cost_increase_24h / self.immediate_cost_usd) * 100

    @computed_field
    @property
    def has_point_of_no_return(self) -> bool:
        """Is there a point of no return?"""
        return self.point_of_no_return is not None

    @computed_field
    @property
    def hours_until_no_return(self) -> Optional[float]:
        """Hours until point of no return."""
        if self.point_of_no_return is None:
            return None
        delta = self.point_of_no_return - datetime.utcnow()
        return max(0, delta.total_seconds() / 3600)


class TradeOffAnalysis(BaseModel):
    """
    Complete trade-off analysis for decision-making.

    Compares all actions and analyzes consequences of waiting.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "recommended_action": "act_reroute_abc123",
                "urgency": "URGENT",
                "time_to_decide_hours": 12,
            }
        }
    )

    # Identity
    customer_id: str = Field(description="Customer ID")
    signal_id: str = Field(description="Signal ID")

    # Actions compared
    actions_compared: list[str] = Field(
        default_factory=list,
        description="Action IDs that were compared",
    )

    # Recommendation
    recommended_action: str = Field(description="Recommended action ID")
    recommended_reason: str = Field(
        max_length=300,
        description="Why this action is recommended",
    )

    # Inaction analysis
    inaction: InactionConsequence = Field(
        description="Consequences of not acting",
    )

    # Urgency
    urgency: str = Field(
        description="Urgency level: IMMEDIATE, HOURS, DAYS, WEEKS",
    )
    time_to_decide: timedelta = Field(
        description="Time available to make decision",
    )

    # Confidence
    analysis_confidence: float = Field(
        ge=0,
        le=1,
        description="Confidence in this analysis",
    )

    # Metadata
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)

    @computed_field
    @property
    def time_to_decide_hours(self) -> float:
        """Time to decide in hours."""
        return self.time_to_decide.total_seconds() / 3600

    @computed_field
    @property
    def is_immediate(self) -> bool:
        """Is this an immediate decision (< 6 hours)?"""
        return self.urgency == "IMMEDIATE"
