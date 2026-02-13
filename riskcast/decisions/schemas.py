"""
Decision Support Schemas — fully typed, auditable decision objects.

Every decision answers 7 questions:
1. What is happening?
2. How bad is it?
3. What should we do?
4. What are the alternatives?
5. What's the cost/benefit?
6. How confident are we?
7. What if we do nothing?
"""

from datetime import datetime
from enum import StrEnum
from typing import Optional

from pydantic import BaseModel, Field


class ActionType(StrEnum):
    REROUTE = "reroute"
    INSURE = "insure"
    DELAY = "delay_shipment"
    HEDGE = "hedge_exposure"
    SPLIT = "split_shipment"
    MONITOR = "monitor_only"
    ESCALATE = "escalate_to_human"


class DecisionStatus(StrEnum):
    PENDING = "pending"
    RECOMMENDED = "recommended"
    ACKNOWLEDGED = "acknowledged"
    ACTED_UPON = "acted_upon"
    OVERRIDDEN = "overridden"
    ESCALATED = "escalated"
    EXPIRED = "expired"


class SeverityLevel(StrEnum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class Action(BaseModel):
    """A concrete action that can be taken."""
    action_type: ActionType
    description: str
    estimated_cost_usd: float = 0.0
    estimated_benefit_usd: float = 0.0
    net_value: float = 0.0               # benefit - cost
    success_probability: float = 0.0     # 0-1
    time_to_execute_hours: float = 0.0
    deadline: Optional[str] = None
    requirements: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)


class TradeoffAnalysis(BaseModel):
    """Cost/benefit analysis comparing actions."""
    recommended_action: ActionType
    recommendation_reason: str
    actions: list[Action]
    do_nothing_cost: float = 0.0
    best_net_value: float = 0.0
    confidence: float = 0.0


class CounterfactualScenario(BaseModel):
    """What-if scenario analysis."""
    scenario_name: str
    description: str
    probability: float           # 0-1
    impact_if_occurs: float      # 0-100
    expected_loss: float         # probability × impact
    mitigation_available: bool


class EscalationRule(BaseModel):
    """Why a decision was escalated to a human."""
    rule_name: str
    triggered: bool
    reason: str
    threshold: Optional[float] = None
    actual_value: Optional[float] = None


class Decision(BaseModel):
    """
    A complete decision object — fully auditable.

    Every field traces to a computation or data source.
    """
    decision_id: str
    entity_type: str
    entity_id: str
    company_id: str
    status: DecisionStatus = DecisionStatus.RECOMMENDED
    severity: SeverityLevel

    # What is happening?
    situation_summary: str
    risk_score: float
    confidence: float
    ci_lower: float
    ci_upper: float

    # What should we do?
    recommended_action: Action
    alternative_actions: list[Action] = Field(default_factory=list)

    # Cost/benefit
    tradeoff: TradeoffAnalysis

    # What if we do nothing?
    inaction_cost: float = 0.0
    inaction_risk: str = ""
    counterfactuals: list[CounterfactualScenario] = Field(default_factory=list)

    # Human-in-the-loop
    needs_human_review: bool = False
    escalation_rules: list[EscalationRule] = Field(default_factory=list)
    escalation_reason: Optional[str] = None

    # Audit
    algorithm_trace: dict = Field(default_factory=dict)
    data_sources: list[str] = Field(default_factory=list)
    generated_at: str = ""
    valid_until: Optional[str] = None

    # Metadata
    n_signals_used: int = 0
    is_reliable: bool = False
    data_freshness: str = "unknown"


class DecisionListResponse(BaseModel):
    decisions: list[Decision]
    total: int


class DecisionOverrideRequest(BaseModel):
    decision_id: str
    override_action: ActionType
    reason: str
    user_id: str
