"""ORACLE Schemas - Reality Engine Data Models.

ORACLE provides ground truth about what IS happening:
- AIS vessel tracking data
- Freight rate data
- Port congestion metrics
- Chokepoint health status

ORACLE correlates OMEN predictions with reality.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.omen.schemas import Chokepoint, OmenSignal


class CorrelationStatus(str, Enum):
    """Status of signal-reality correlation."""

    CONFIRMED = "confirmed"  # Signal matches reality
    MATERIALIZING = "materializing"  # Signs of signal appearing in reality
    PREDICTED_NOT_OBSERVED = "predicted_not_observed"  # Signal predicted but not yet seen
    SURPRISE = "surprise"  # Reality event without prior signal
    NORMAL = "normal"  # No significant activity


class ChokepointHealth(BaseModel):
    """Health metrics for a maritime chokepoint."""

    model_config = ConfigDict(frozen=True)

    chokepoint: Chokepoint
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Vessel metrics
    vessels_in_transit: int = Field(ge=0, description="Vessels currently transiting")
    vessels_waiting: int = Field(ge=0, description="Vessels waiting to transit")
    rerouting_count: int = Field(ge=0, description="Vessels that have rerouted")

    # Rate metrics
    current_rate_per_teu: float = Field(
        ge=0,
        description="Current freight rate per TEU (USD)",
    )
    baseline_rate_per_teu: float = Field(
        ge=0,
        description="Normal/baseline rate per TEU (USD)",
    )

    # Delay metrics
    average_delay_hours: float = Field(ge=0, description="Average transit delay in hours")
    max_delay_hours: float = Field(ge=0, description="Maximum observed delay in hours")

    # Status
    is_operational: bool = Field(default=True, description="Is chokepoint operational?")
    disruption_level: str = Field(
        default="normal",
        description="Disruption level: normal, elevated, severe, critical",
    )

    @computed_field
    @property
    def rate_premium_pct(self) -> float:
        """Rate premium as percentage above baseline."""
        if self.baseline_rate_per_teu <= 0:
            return 0.0
        premium = (self.current_rate_per_teu - self.baseline_rate_per_teu) / self.baseline_rate_per_teu
        return round(max(0, premium), 4)

    @computed_field
    @property
    def congestion_ratio(self) -> float:
        """Ratio of waiting vessels to transiting vessels."""
        if self.vessels_in_transit <= 0:
            return 0.0
        return round(self.vessels_waiting / self.vessels_in_transit, 2)


class VesselMovement(BaseModel):
    """Vessel movement data from AIS."""

    imo: str = Field(description="IMO number")
    vessel_name: str
    vessel_type: str
    flag: str

    # Position
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    heading: float = Field(ge=0, le=360)
    speed_knots: float = Field(ge=0)

    # Route
    origin_port: Optional[str] = None
    destination_port: Optional[str] = None
    eta: Optional[datetime] = None

    # Status
    is_rerouting: bool = Field(default=False, description="Has vessel changed route?")
    original_route: Optional[str] = Field(
        default=None,
        description="Original route if rerouted",
    )

    timestamp: datetime = Field(default_factory=datetime.utcnow)


class RealitySnapshot(BaseModel):
    """
    Snapshot of current reality from ORACLE.

    Contains real-time data about:
    - Chokepoint health
    - Vessel movements
    - Freight rates
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "snapshot_id": "ORACLE-2024-001",
                "generated_at": "2024-02-05T10:00:00Z",
            }
        }
    )

    snapshot_id: str = Field(description="Unique snapshot identifier")
    generated_at: datetime = Field(default_factory=datetime.utcnow)

    # Chokepoint health
    chokepoint_health: dict[str, ChokepointHealth] = Field(
        default_factory=dict,
        description="Health metrics by chokepoint",
    )

    # Vessel data
    vessels_rerouting: list[VesselMovement] = Field(
        default_factory=list,
        description="Vessels that have changed route",
    )
    total_vessels_tracked: int = Field(default=0)

    # Aggregate metrics
    global_disruption_score: float = Field(
        default=0,
        ge=0,
        le=1,
        description="Overall disruption level (0-1)",
    )

    def get_chokepoint_health(self, chokepoint: Chokepoint) -> Optional[ChokepointHealth]:
        """Get health for a specific chokepoint."""
        return self.chokepoint_health.get(chokepoint.value)

    def get_rerouting_count(self, chokepoint: Chokepoint) -> int:
        """Get number of vessels rerouting around a chokepoint."""
        health = self.get_chokepoint_health(chokepoint)
        return health.rerouting_count if health else 0


class CorrelatedIntelligence(BaseModel):
    """
    Combined intelligence from OMEN signal + ORACLE reality.

    This is the PRIMARY INPUT to RISKCAST.

    Correlation status indicates how well prediction matches reality:
    - CONFIRMED: Signal is happening (high probability + reality confirms)
    - MATERIALIZING: Early signs appearing (reality starting to match)
    - PREDICTED_NOT_OBSERVED: Signal exists but reality normal
    - SURPRISE: Reality disruption without prior signal
    - NORMAL: No significant signal or disruption
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "correlation_id": "CORR-2024-001",
                "correlation_status": "confirmed",
                "combined_confidence": 0.87,
            }
        }
    )

    # Identity
    correlation_id: str = Field(description="Unique correlation identifier")

    # Signal (from OMEN)
    signal: OmenSignal = Field(description="OMEN signal")

    # Reality (from ORACLE)
    reality: Optional[RealitySnapshot] = Field(
        default=None,
        description="ORACLE reality snapshot",
    )

    # Correlation
    correlation_status: CorrelationStatus = Field(
        description="How signal correlates with reality",
    )
    correlation_factors: dict[str, float] = Field(
        default_factory=dict,
        description="Factors contributing to correlation",
    )

    # Combined metrics
    combined_confidence: float = Field(
        ge=0,
        le=1,
        description="Combined confidence from signal + reality",
    )

    # Timestamps
    correlated_at: datetime = Field(default_factory=datetime.utcnow)

    @computed_field
    @property
    def is_actionable(self) -> bool:
        """Whether this intelligence warrants action."""
        return self.correlation_status in [
            CorrelationStatus.CONFIRMED,
            CorrelationStatus.MATERIALIZING,
        ]

    @computed_field
    @property
    def primary_chokepoint(self) -> str:
        """Get primary chokepoint from signal."""
        return self.signal.geographic.primary_chokepoint.value

    def get_reality_rerouting_count(self) -> int:
        """Get rerouting count from reality if available."""
        if self.reality:
            return self.reality.get_rerouting_count(
                self.signal.geographic.primary_chokepoint
            )
        return 0

    def get_reality_rate_premium(self) -> float:
        """Get rate premium from reality if available."""
        if self.reality:
            health = self.reality.get_chokepoint_health(
                self.signal.geographic.primary_chokepoint
            )
            return health.rate_premium_pct if health else 0.0
        return 0.0
