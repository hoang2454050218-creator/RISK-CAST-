"""Impact Schemas - Financial and time impact models.

The Impact Calculator answers: "How much will this cost in DOLLARS and DAYS?"

NOT vague descriptions like "significant impact" or "major delays".
MUST output specific numbers: "$47,500 expected loss" and "10-14 days delay".
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.riskcast.constants import Severity, get_severity


class CostBreakdown(BaseModel):
    """
    Itemized cost breakdown.

    User can see exactly where the money goes.
    All amounts in USD - NO PERCENTAGES.
    """

    model_config = ConfigDict(frozen=True)

    delay_holding_cost_usd: float = Field(
        default=0,
        ge=0,
        description="Cost of cargo sitting in delay (inventory cost)",
    )
    reroute_premium_usd: float = Field(
        default=0,
        ge=0,
        description="Extra freight cost for alternative route",
    )
    rate_increase_usd: float = Field(
        default=0,
        ge=0,
        description="Cost from current rate spike",
    )
    penalty_cost_usd: float = Field(
        default=0,
        ge=0,
        description="Contract delay penalties",
    )

    @computed_field
    @property
    def total_usd(self) -> float:
        """Total cost in USD."""
        return (
            self.delay_holding_cost_usd
            + self.reroute_premium_usd
            + self.rate_increase_usd
            + self.penalty_cost_usd
        )

    def to_breakdown_dict(self) -> dict[str, float]:
        """Convert to dict for display."""
        return {
            "delay_holding": self.delay_holding_cost_usd,
            "reroute_premium": self.reroute_premium_usd,
            "rate_increase": self.rate_increase_usd,
            "penalties": self.penalty_cost_usd,
            "total": self.total_usd,
        }


class DelayEstimate(BaseModel):
    """
    Delay estimation with range.

    NOT "significant delay expected".
    YES "10-14 days delay, expected 12 days".
    """

    model_config = ConfigDict(frozen=True)

    min_days: int = Field(ge=0, description="Best case delay in days")
    max_days: int = Field(ge=0, description="Worst case delay in days")
    expected_days: int = Field(ge=0, description="Most likely delay in days")
    confidence: float = Field(
        ge=0,
        le=1,
        description="Confidence in this estimate",
    )

    @computed_field
    @property
    def range_str(self) -> str:
        """Human-readable range string."""
        if self.min_days == self.max_days:
            return f"{self.min_days} days"
        return f"{self.min_days}-{self.max_days} days"

    @computed_field
    @property
    def is_significant(self) -> bool:
        """Is this a significant delay (>3 days)?"""
        return self.expected_days > 3


class ShipmentImpact(BaseModel):
    """
    Impact assessment for a single shipment.

    Every shipment gets its own detailed impact analysis.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "shipment_id": "PO-4521",
                "shipment_ref": "PO-4521",
                "delay": {"min_days": 7, "max_days": 14, "expected_days": 10},
                "cost": {"total_usd": 15000},
                "impact_severity": "HIGH",
            }
        }
    )

    # Identity
    shipment_id: str = Field(description="Internal shipment ID")
    shipment_ref: str = Field(description="Customer's reference (PO number)")

    # Delay analysis
    delay: DelayEstimate = Field(description="Delay estimation")
    original_eta: datetime = Field(description="Original ETA")
    new_eta_expected: datetime = Field(description="Expected new ETA")

    # Cost analysis
    cost: CostBreakdown = Field(description="Cost breakdown")

    # Penalty specifics
    triggers_penalty: bool = Field(
        default=False,
        description="Will this delay trigger contract penalties?",
    )
    days_until_penalty: Optional[int] = Field(
        default=None,
        description="Days before penalties start (if applicable)",
    )
    penalty_amount_usd: float = Field(
        default=0,
        ge=0,
        description="Total penalty amount if delay occurs",
    )

    # Severity
    impact_severity: Severity = Field(description="Impact severity level")

    @computed_field
    @property
    def total_impact_usd(self) -> float:
        """Total impact in USD for this shipment."""
        return self.cost.total_usd

    @computed_field
    @property
    def delay_days(self) -> int:
        """Expected delay in days."""
        return self.delay.expected_days


class TotalImpact(BaseModel):
    """
    Aggregated impact across all affected shipments.

    This is the answer to Q3: "How bad is it?"
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "customer_id": "cust_abc123",
                "signal_id": "OMEN-RS-2024-001",
                "total_cost_usd": 47500,
                "total_delay_days_expected": 10,
                "overall_severity": "HIGH",
            }
        }
    )

    # Identity
    customer_id: str = Field(description="Customer ID")
    signal_id: str = Field(description="Signal that caused this impact")

    # Per-shipment impacts
    shipment_impacts: list[ShipmentImpact] = Field(
        default_factory=list,
        description="Impact for each affected shipment",
    )

    # Aggregate totals
    total_cost_usd: float = Field(
        ge=0,
        description="Total cost across all shipments (USD)",
    )
    total_delay_days_expected: int = Field(
        ge=0,
        description="Average expected delay (days)",
    )

    # Penalty summary
    shipments_with_penalties: int = Field(
        default=0,
        ge=0,
        description="Number of shipments that will trigger penalties",
    )
    total_penalty_usd: float = Field(
        default=0,
        ge=0,
        description="Total penalty amount across all shipments",
    )

    # Overall severity
    overall_severity: Severity = Field(description="Overall impact severity")

    # Metadata
    calculated_at: datetime = Field(default_factory=datetime.utcnow)
    confidence: float = Field(
        ge=0,
        le=1,
        description="Confidence in this impact assessment",
    )

    @computed_field
    @property
    def shipment_count(self) -> int:
        """Number of affected shipments."""
        return len(self.shipment_impacts)

    @computed_field
    @property
    def has_critical_exposure(self) -> bool:
        """Does this represent critical exposure (>$100K)?"""
        return self.overall_severity == Severity.CRITICAL

    @computed_field
    @property
    def has_penalty_risk(self) -> bool:
        """Are any shipments at risk of penalties?"""
        return self.shipments_with_penalties > 0

    def get_cost_breakdown(self) -> dict[str, float]:
        """Get aggregated cost breakdown."""
        breakdown = {
            "delay_holding": sum(
                si.cost.delay_holding_cost_usd for si in self.shipment_impacts
            ),
            "reroute_premium": sum(
                si.cost.reroute_premium_usd for si in self.shipment_impacts
            ),
            "rate_increase": sum(
                si.cost.rate_increase_usd for si in self.shipment_impacts
            ),
            "penalties": sum(si.cost.penalty_cost_usd for si in self.shipment_impacts),
        }
        breakdown["total"] = sum(breakdown.values())
        return breakdown

    def get_shipment_refs(self) -> list[str]:
        """Get list of affected shipment references."""
        return [si.shipment_ref for si in self.shipment_impacts]
