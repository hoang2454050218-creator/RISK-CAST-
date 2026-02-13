"""Customer Context Schemas - THE MOAT of RISKCAST.

This is what makes decisions PERSONAL.
Without customer context, we're just another notification system.

Customer data includes:
- Company profile and preferences
- Active shipments with routes
- Contract terms and penalty clauses
- Risk tolerance settings

The MOAT is not algorithms - it's CUSTOMER DATA.
"""

import re
from datetime import datetime
from typing import Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    computed_field,
    field_validator,
    model_validator,
)

from app.riskcast.constants import (
    RiskTolerance,
    ShipmentStatus,
    TEU_CONVERSION,
    derive_chokepoints,
)


# ============================================================================
# CUSTOMER PROFILE
# ============================================================================


class CustomerProfile(BaseModel):
    """
    Core customer profile - the foundation of personalization.

    Collected during onboarding via WhatsApp.
    Updated as we learn more about the customer.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "customer_id": "cust_abc123",
                "company_name": "Vietnam Exports Co",
                "primary_routes": ["VNHCM-NLRTM", "VNHCM-DEHAM"],
                "relevant_chokepoints": ["red_sea", "suez", "malacca"],
                "risk_tolerance": "balanced",
                "max_reroute_premium_pct": 0.5,
                "primary_phone": "+84901234567",
                "language": "vi",
                "timezone": "Asia/Ho_Chi_Minh",
            }
        }
    )

    # Identity
    customer_id: str = Field(description="Unique customer ID")
    company_name: str = Field(min_length=1, max_length=200, description="Company name")

    # Routes (critical for exposure matching)
    primary_routes: list[str] = Field(
        default_factory=list,
        description="Trade lanes in format 'ORIGIN-DEST'",
        examples=[["CNSHA-NLRTM", "VNHCM-DEHAM"]],
    )

    # Chokepoints (derived from routes)
    relevant_chokepoints: list[str] = Field(
        default_factory=list,
        description="Chokepoints on customer's routes",
    )

    # Risk preferences
    risk_tolerance: RiskTolerance = Field(
        default=RiskTolerance.BALANCED,
        description="How customer balances cost vs risk",
    )
    max_reroute_premium_pct: float = Field(
        default=0.5,
        ge=0,
        le=2.0,
        description="Max premium customer will pay for rerouting (0.5 = 50%)",
    )

    # Contact information
    primary_phone: str = Field(
        description="WhatsApp number in E.164 format",
        examples=["+84901234567", "+1234567890"],
    )
    secondary_phone: Optional[str] = Field(
        default=None,
        description="Backup phone number",
    )
    email: Optional[str] = Field(default=None, description="Email address")

    # Localization
    language: str = Field(
        default="en",
        description="Preferred language code",
        examples=["en", "vi", "zh"],
    )
    timezone: str = Field(
        default="UTC",
        description="Timezone for notifications",
        examples=["UTC", "Asia/Ho_Chi_Minh", "Europe/Amsterdam"],
    )

    # Status
    onboarding_complete: bool = Field(default=False)
    is_active: bool = Field(default=True)

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_alert_at: Optional[datetime] = Field(default=None)

    @field_validator("primary_phone", "secondary_phone", mode="before")
    @classmethod
    def validate_phone(cls, v: str | None) -> str | None:
        """Validate phone number is in E.164 format."""
        if v is None:
            return None
        v = v.strip()
        # E.164: + followed by 1-15 digits
        if not re.match(r"^\+[1-9]\d{1,14}$", v):
            raise ValueError(
                f"Phone number must be in E.164 format (e.g., +84901234567), got: {v}"
            )
        return v

    @field_validator("primary_routes", mode="after")
    @classmethod
    def validate_routes(cls, v: list[str]) -> list[str]:
        """Validate route format (ORIGIN-DEST)."""
        validated = []
        for route in v:
            route = route.upper().strip()
            if "-" not in route:
                raise ValueError(f"Route must be in 'ORIGIN-DEST' format, got: {route}")
            parts = route.split("-")
            if len(parts) != 2 or len(parts[0]) != 5 or len(parts[1]) != 5:
                raise ValueError(
                    f"Route must be in 'XXXXX-XXXXX' format (5-char port codes), got: {route}"
                )
            validated.append(route)
        return validated

    @model_validator(mode="after")
    def derive_chokepoints_from_routes(self) -> "CustomerProfile":
        """Auto-derive chokepoints from routes if not provided."""
        if not self.relevant_chokepoints and self.primary_routes:
            chokepoints = set()
            for route in self.primary_routes:
                origin, dest = route.split("-")
                route_chokepoints = derive_chokepoints(origin, dest)
                chokepoints.update(route_chokepoints)
            self.relevant_chokepoints = list(chokepoints)
        return self

    def has_chokepoint_exposure(self, chokepoint: str) -> bool:
        """Check if customer has exposure to a chokepoint."""
        return chokepoint.lower() in [c.lower() for c in self.relevant_chokepoints]


# ============================================================================
# SHIPMENT
# ============================================================================


class Shipment(BaseModel):
    """
    Active shipment that can be affected by disruptions.

    This is what makes decisions PERSONAL.
    Without shipments, we can only give generic alerts.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "shipment_id": "PO-4521",
                "customer_id": "cust_abc123",
                "origin_port": "VNHCM",
                "destination_port": "NLRTM",
                "cargo_value_usd": 150000,
                "container_count": 3,
                "container_type": "40HC",
                "etd": "2024-02-10T00:00:00Z",
                "eta": "2024-03-15T00:00:00Z",
            }
        }
    )

    # Identity
    shipment_id: str = Field(
        description="Customer's reference (e.g., PO number)",
        examples=["PO-4521", "INV-2024-001"],
    )
    customer_id: str = Field(description="Owner customer ID")

    # Route (critical for exposure matching)
    origin_port: str = Field(
        min_length=5,
        max_length=5,
        description="Origin port code (UN/LOCODE)",
        examples=["CNSHA", "VNHCM", "KRPUS"],
    )
    destination_port: str = Field(
        min_length=5,
        max_length=5,
        description="Destination port code (UN/LOCODE)",
        examples=["NLRTM", "DEHAM", "USLAX"],
    )
    route_chokepoints: list[str] = Field(
        default_factory=list,
        description="Chokepoints this shipment transits",
    )

    # Timing (critical for impact calculation)
    etd: datetime = Field(description="Estimated Time of Departure")
    eta: datetime = Field(description="Estimated Time of Arrival")

    # Cargo (critical for $ exposure)
    cargo_value_usd: float = Field(
        ge=0,
        description="Total cargo value in USD",
    )
    cargo_description: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Brief cargo description",
    )

    # Container info
    container_count: int = Field(default=1, ge=1, description="Number of containers")
    container_type: str = Field(
        default="40HC",
        description="Container type code",
        examples=["20GP", "40GP", "40HC", "45HC"],
    )

    # Carrier
    carrier_code: Optional[str] = Field(
        default=None,
        description="Carrier SCAC code",
        examples=["MSCU", "MAEU", "CMDU"],
    )
    booking_reference: Optional[str] = Field(
        default=None,
        description="Carrier booking reference",
    )
    vessel_name: Optional[str] = Field(default=None)
    voyage_number: Optional[str] = Field(default=None)

    # Contract terms (for penalty calculation)
    has_delay_penalty: bool = Field(
        default=False,
        description="Does contract have delay penalties?",
    )
    delay_penalty_per_day_usd: float = Field(
        default=0,
        ge=0,
        description="Penalty per day of delay in USD",
    )
    penalty_free_days: int = Field(
        default=0,
        ge=0,
        description="Days of delay before penalties start",
    )

    # Status
    status: ShipmentStatus = Field(default=ShipmentStatus.BOOKED)

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    notes: Optional[str] = Field(default=None, max_length=1000)

    @field_validator("origin_port", "destination_port", mode="before")
    @classmethod
    def normalize_port_code(cls, v: str) -> str:
        """Normalize port code to uppercase."""
        return v.upper().strip()

    @field_validator("container_type", mode="before")
    @classmethod
    def normalize_container_type(cls, v: str) -> str:
        """Normalize container type."""
        return v.upper().strip()

    @model_validator(mode="after")
    def derive_route_chokepoints(self) -> "Shipment":
        """Auto-derive chokepoints from origin/destination."""
        if not self.route_chokepoints:
            self.route_chokepoints = derive_chokepoints(
                self.origin_port,
                self.destination_port,
            )
        return self

    @model_validator(mode="after")
    def validate_dates(self) -> "Shipment":
        """Validate ETD is before ETA."""
        if self.etd >= self.eta:
            raise ValueError("ETD must be before ETA")
        return self

    @computed_field
    @property
    def teu_count(self) -> float:
        """Calculate TEU from container info."""
        multiplier = TEU_CONVERSION.get(self.container_type.upper(), 2.0)
        return self.container_count * multiplier

    @computed_field
    @property
    def route_code(self) -> str:
        """Route code in ORIGIN-DEST format."""
        return f"{self.origin_port}-{self.destination_port}"

    @computed_field
    @property
    def is_actionable(self) -> bool:
        """Can we still take action on this shipment?"""
        return self.status in [ShipmentStatus.BOOKED, ShipmentStatus.AT_PORT]

    @computed_field
    @property
    def is_in_transit(self) -> bool:
        """Is shipment currently moving?"""
        return self.status == ShipmentStatus.IN_TRANSIT

    @computed_field
    @property
    def is_completed(self) -> bool:
        """Is shipment delivered or cancelled?"""
        return self.status in [ShipmentStatus.DELIVERED, ShipmentStatus.CANCELLED]

    @computed_field
    @property
    def transit_days(self) -> int:
        """Expected transit time in days."""
        delta = self.eta - self.etd
        return max(1, delta.days)

    @computed_field
    @property
    def has_carrier_info(self) -> bool:
        """Whether we have detailed carrier information."""
        return bool(self.carrier_code and self.booking_reference)

    @computed_field
    @property
    def customer_reference(self) -> str:
        """Customer's reference for this shipment (same as shipment_id)."""
        return self.shipment_id

    @computed_field
    @property
    def daily_penalty_usd(self) -> float:
        """Daily penalty amount (alias for delay_penalty_per_day_usd)."""
        return self.delay_penalty_per_day_usd

    @computed_field
    @property
    def penalty_deadline(self) -> Optional[datetime]:
        """
        Deadline after which penalties start.

        Returns ETA + penalty_free_days, or None if no penalty clause.
        """
        if not self.has_delay_penalty:
            return None
        from datetime import timedelta
        return self.eta + timedelta(days=self.penalty_free_days)

    def has_chokepoint(self, chokepoint: str) -> bool:
        """Check if shipment route includes a chokepoint."""
        return chokepoint.lower() in [c.lower() for c in self.route_chokepoints]

    def calculate_penalty(self, delay_days: int) -> float:
        """Calculate penalty for a given delay."""
        if not self.has_delay_penalty or delay_days <= self.penalty_free_days:
            return 0.0
        penalty_days = delay_days - self.penalty_free_days
        return penalty_days * self.delay_penalty_per_day_usd


# ============================================================================
# CUSTOMER CONTEXT
# ============================================================================


class CustomerContext(BaseModel):
    """
    Full context for decision-making.

    Assembled fresh for each decision by combining:
    - Customer profile
    - Active shipments
    - Computed exposure
    - Alert preferences

    This is THE INPUT to RISKCAST decision engine.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "profile": {"customer_id": "cust_abc123", "company_name": "Vietnam Exports"},
                "active_shipments": [],
                "alert_preferences": {"channels": ["whatsapp"], "min_probability": 0.5},
                "total_cargo_value_usd": 450000,
                "total_teu": 9.0,
            }
        }
    )

    # Core data
    profile: CustomerProfile = Field(description="Customer profile")
    active_shipments: list[Shipment] = Field(
        default_factory=list,
        description="Active (non-completed) shipments",
    )
    
    # Alert preferences (optional - uses defaults if not provided)
    alert_preferences: Optional["AlertPreferences"] = Field(
        default=None,
        description="Customer alert preferences",
    )

    # Computed totals (set by model_validator)
    total_cargo_value_usd: float = Field(
        default=0,
        ge=0,
        description="Sum of all active shipment values",
    )
    total_teu: float = Field(
        default=0,
        ge=0,
        description="Sum of all active shipment TEUs",
    )

    # Context metadata
    assembled_at: datetime = Field(default_factory=datetime.utcnow)

    @model_validator(mode="after")
    def compute_totals(self) -> "CustomerContext":
        """Compute totals from active shipments."""
        self.total_cargo_value_usd = sum(
            s.cargo_value_usd for s in self.active_shipments
        )
        self.total_teu = sum(s.teu_count for s in self.active_shipments)
        return self

    @computed_field
    @property
    def shipment_count(self) -> int:
        """Number of active shipments."""
        return len(self.active_shipments)

    @computed_field
    @property
    def actionable_shipments(self) -> list[Shipment]:
        """Shipments that can still be acted upon."""
        return [s for s in self.active_shipments if s.is_actionable]

    @computed_field
    @property
    def actionable_count(self) -> int:
        """Number of actionable shipments."""
        return len(self.actionable_shipments)

    def get_shipments_by_chokepoint(self, chokepoint: str) -> list[Shipment]:
        """Get shipments that transit a specific chokepoint."""
        return [s for s in self.active_shipments if s.has_chokepoint(chokepoint)]

    def get_exposure_by_chokepoint(self, chokepoint: str) -> float:
        """Get total cargo value exposed to a chokepoint."""
        return sum(
            s.cargo_value_usd
            for s in self.active_shipments
            if s.has_chokepoint(chokepoint)
        )

    def has_exposure_to(self, chokepoint: str) -> bool:
        """Check if customer has any shipments through a chokepoint."""
        return any(s.has_chokepoint(chokepoint) for s in self.active_shipments)


# ============================================================================
# ALERT PREFERENCES
# ============================================================================


class AlertPreferences(BaseModel):
    """
    Customer alert preferences for notifications.
    
    Configures how and when to alert the customer about decisions.
    """
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "channels": ["whatsapp"],
                "min_probability": 0.5,
                "chokepoints_of_interest": ["red_sea", "suez"],
            }
        }
    )
    
    # Notification channels
    channels: list[str] = Field(
        default_factory=lambda: ["whatsapp"],
        description="Preferred notification channels",
        examples=[["whatsapp", "email", "sms"]],
    )
    
    # Filtering thresholds
    min_probability: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Minimum probability to trigger alert",
    )
    
    min_exposure_usd: float = Field(
        default=0.0,
        ge=0.0,
        description="Minimum exposure in USD to trigger alert",
    )
    
    # Chokepoint preferences
    chokepoints_of_interest: list[str] = Field(
        default_factory=list,
        description="Specific chokepoints to monitor (empty = all)",
    )
    
    # Timing preferences
    quiet_hours_start: Optional[int] = Field(
        default=None,
        ge=0,
        le=23,
        description="Start of quiet hours (hour in local timezone)",
    )
    quiet_hours_end: Optional[int] = Field(
        default=None,
        ge=0,
        le=23,
        description="End of quiet hours (hour in local timezone)",
    )
    
    # Alert frequency limits
    max_alerts_per_day: int = Field(
        default=10,
        ge=1,
        description="Maximum alerts per day",
    )
    
    # Feature flags
    include_inaction_cost: bool = Field(
        default=True,
        description="Include Q7 inaction cost in alerts",
    )
    include_confidence: bool = Field(
        default=True,
        description="Include Q6 confidence level in alerts",
    )
    
    def should_alert(self, probability: float, exposure_usd: float) -> bool:
        """Check if alert should be sent based on thresholds."""
        if probability < self.min_probability:
            return False
        if exposure_usd < self.min_exposure_usd:
            return False
        return True
    
    def is_chokepoint_relevant(self, chokepoint: str) -> bool:
        """Check if chokepoint is relevant to customer."""
        if not self.chokepoints_of_interest:
            return True  # Empty list = all chokepoints
        return chokepoint.lower() in [c.lower() for c in self.chokepoints_of_interest]
