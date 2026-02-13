"""
Alert & Early Warning Schemas.

Defines alert rules, alert records, channels, and early warning signals.
"""

from datetime import datetime
from enum import StrEnum
from typing import Optional

from pydantic import BaseModel, Field


# ── Enums ──────────────────────────────────────────────────────────────


class AlertSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    HIGH = "high"
    CRITICAL = "critical"


class AlertChannel(StrEnum):
    WEBHOOK = "webhook"
    EMAIL = "email"
    IN_APP = "in_app"


class AlertStatus(StrEnum):
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    SUPPRESSED = "suppressed"       # Deduplicated / cooldown


class RuleOperator(StrEnum):
    GT = "gt"           # greater than
    GTE = "gte"         # greater than or equal
    LT = "lt"           # less than
    LTE = "lte"         # less than or equal
    EQ = "eq"           # equal
    NEQ = "neq"         # not equal
    CONTAINS = "contains"


class TrendDirection(StrEnum):
    RISING = "rising"
    FALLING = "falling"
    STABLE = "stable"
    ACCELERATING = "accelerating"   # Rising faster than linear


# ── Alert Rule ─────────────────────────────────────────────────────────


class AlertRule(BaseModel):
    """
    A configurable alert rule.

    Defines WHEN an alert fires based on metric conditions.
    """
    rule_id: str
    rule_name: str
    description: str
    company_id: str
    is_active: bool = True

    # Condition
    metric: str                     # e.g. "risk_score", "confidence", "exposure_usd"
    operator: RuleOperator
    threshold: float
    entity_type: Optional[str] = None   # Filter by entity type (None = all)

    # Alert config
    severity: AlertSeverity = AlertSeverity.WARNING
    channels: list[AlertChannel] = Field(default_factory=lambda: [AlertChannel.IN_APP])
    cooldown_minutes: int = 30      # Min time between repeated alerts
    max_per_day: int = 10           # Max alerts of this rule per day

    # Metadata
    created_at: str = ""
    updated_at: str = ""


class AlertRuleCreateRequest(BaseModel):
    """Request to create a new alert rule."""
    rule_name: str
    description: str = ""
    metric: str
    operator: RuleOperator
    threshold: float
    entity_type: Optional[str] = None
    severity: AlertSeverity = AlertSeverity.WARNING
    channels: list[AlertChannel] = Field(default_factory=lambda: [AlertChannel.IN_APP])
    cooldown_minutes: int = 30
    max_per_day: int = 10


# ── Alert Record ───────────────────────────────────────────────────────


class AlertRecord(BaseModel):
    """
    A fired alert — immutable record of what was triggered and sent.
    """
    alert_id: str
    rule_id: str
    rule_name: str
    company_id: str
    severity: AlertSeverity
    status: AlertStatus

    # What triggered it
    metric: str
    metric_value: float
    threshold: float
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None

    # Message
    title: str
    message: str

    # Delivery
    channels: list[AlertChannel] = Field(default_factory=list)
    delivery_results: dict = Field(default_factory=dict)

    # Timing
    triggered_at: str = ""
    sent_at: Optional[str] = None
    acknowledged_at: Optional[str] = None
    acknowledged_by: Optional[str] = None


class AlertListResponse(BaseModel):
    alerts: list[AlertRecord]
    total: int


# ── Early Warning ──────────────────────────────────────────────────────


class EarlyWarning(BaseModel):
    """
    An early warning signal — detected trend that may cross a threshold.

    Not an alert yet, but a prediction that one will fire soon.
    """
    warning_id: str
    company_id: str
    metric: str
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None

    # Current state
    current_value: float
    threshold: float
    distance_to_threshold: float    # How far from threshold

    # Trend
    trend_direction: TrendDirection
    trend_slope: float              # Rate of change per day
    predicted_crossing_hours: Optional[float] = None  # Hours until threshold crossed

    # Confidence
    confidence: float = 0.0         # 0-1: how confident we are in the prediction
    data_points_used: int = 0

    # Advice
    recommendation: str = ""
    urgency: AlertSeverity = AlertSeverity.INFO
    generated_at: str = ""


class EarlyWarningListResponse(BaseModel):
    warnings: list[EarlyWarning]
    total: int
