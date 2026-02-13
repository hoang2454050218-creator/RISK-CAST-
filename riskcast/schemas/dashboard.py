"""
Dashboard API Schemas.

Every field traces to a real SQL query. Zero mock data.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class DailyCount(BaseModel):
    """A single data point in a time series."""
    date: str
    count: int


class DailyRiskLevel(BaseModel):
    """Daily average risk score."""
    date: str
    avg_risk_score: float
    signal_count: int


class TopRisk(BaseModel):
    """A top-risk item for the dashboard."""
    signal_id: str
    signal_type: str
    severity_score: float
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    summary: str


class RecentAction(BaseModel):
    """A recent action/event."""
    action_type: str
    description: str
    timestamp: str
    user_name: Optional[str] = None


class DataFreshness(BaseModel):
    """How fresh is the underlying data."""
    last_signal_at: Optional[str] = None
    last_order_at: Optional[str] = None
    last_payment_at: Optional[str] = None
    staleness_level: str = "fresh"  # "fresh" | "stale" | "outdated" | "no_data"


class DashboardSummary(BaseModel):
    """
    Dashboard summary — every field from a real SQL query.

    If the database is empty, all numbers are 0 with a helpful message.
    """
    period: str = "last_7_days"
    generated_at: str
    data_freshness: DataFreshness

    # Core metrics
    total_orders: int = 0
    active_signals: int = 0
    critical_signals: int = 0
    orders_at_risk: int = 0
    total_revenue: float = 0.0
    total_customers: int = 0

    # Trends
    signal_trend: list[DailyCount] = Field(default_factory=list)
    order_trend: list[DailyCount] = Field(default_factory=list)
    risk_trend: list[DailyRiskLevel] = Field(default_factory=list)

    # Actionable
    pending_decisions: int = 0
    top_risks: list[TopRisk] = Field(default_factory=list)
    recent_actions: list[RecentAction] = Field(default_factory=list)

    # Confidence
    data_completeness: float = 0.0
    known_gaps: list[str] = Field(default_factory=list)
    message: Optional[str] = None
