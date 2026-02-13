"""OMEN Schemas - Signal Engine Data Models.

OMEN is a SIGNAL ENGINE ONLY.
Outputs: signals, evidence, confidence (data quality), context.
NEVER outputs: risk_status, overall_risk, RiskLevel, decisions.

Note: confidence_score = DATA QUALITY, not event probability.
      probability comes from source (e.g., Polymarket).
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator


class SignalCategory(str, Enum):
    """Categories of supply chain signals."""

    GEOPOLITICAL = "geopolitical"  # Conflicts, sanctions, political instability
    WEATHER = "weather"  # Storms, floods, extreme weather
    INFRASTRUCTURE = "infrastructure"  # Port closures, canal issues
    LABOR = "labor"  # Strikes, workforce issues
    ECONOMIC = "economic"  # Currency, trade policy changes
    SECURITY = "security"  # Piracy, terrorism threats
    OTHER = "other"


class Chokepoint(str, Enum):
    """Major maritime chokepoints."""

    RED_SEA = "red_sea"
    SUEZ = "suez"
    PANAMA = "panama"
    MALACCA = "malacca"
    HORMUZ = "hormuz"
    GIBRALTAR = "gibraltar"
    DOVER = "dover"
    BOSPHORUS = "bosphorus"


class EvidenceSource(str, Enum):
    """Types of evidence sources for signals."""
    
    PREDICTION_MARKET = "prediction_market"  # Polymarket, Metaculus
    NEWS = "news"  # Reuters, Bloomberg
    OFFICIAL = "official"  # Government, regulatory bodies
    SOCIAL_MEDIA = "social_media"  # Twitter, Reddit
    SHIPPING_DATA = "shipping_data"  # AIS, port authorities
    WEATHER = "weather"  # Weather services
    FINANCIAL = "financial"  # Freight rates, commodities
    ANALYST = "analyst"  # Expert analysis


class EvidenceItem(BaseModel):
    """A piece of evidence supporting a signal."""

    model_config = ConfigDict(frozen=True)

    source: str = Field(description="Source name (e.g., 'Polymarket', 'Reuters')")
    source_type: str = Field(
        description="Type of source",
        examples=["prediction_market", "news", "official", "social_media"],
    )
    url: Optional[str] = Field(default=None, description="Source URL if available")
    title: str = Field(description="Evidence title/headline")
    snippet: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Relevant excerpt",
    )
    published_at: Optional[datetime] = Field(default=None)
    collected_at: datetime = Field(default_factory=datetime.utcnow)

    # Source-specific data
    probability: Optional[float] = Field(
        default=None,
        ge=0,
        le=1,
        description="Probability from prediction market (0-1)",
    )
    sentiment_score: Optional[float] = Field(
        default=None,
        ge=-1,
        le=1,
        description="Sentiment score (-1 to 1)",
    )


class GeographicScope(BaseModel):
    """Geographic context of a signal."""

    primary_chokepoint: Chokepoint = Field(description="Main affected chokepoint")
    secondary_chokepoints: list[Chokepoint] = Field(
        default_factory=list,
        description="Other affected chokepoints",
    )
    affected_regions: list[str] = Field(
        default_factory=list,
        description="Affected regions/countries",
        examples=[["Middle East", "Red Sea", "Gulf of Aden"]],
    )
    affected_ports: list[str] = Field(
        default_factory=list,
        description="Affected port codes",
        examples=[["AEAUH", "SAJED", "EGPSD"]],
    )

    @computed_field
    @property
    def all_chokepoints(self) -> list[str]:
        """All affected chokepoints as strings."""
        chokepoints = [self.primary_chokepoint.value]
        chokepoints.extend(c.value for c in self.secondary_chokepoints)
        return chokepoints


class TemporalScope(BaseModel):
    """Temporal context of a signal."""

    detected_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When signal was first detected",
    )
    earliest_impact: Optional[datetime] = Field(
        default=None,
        description="Earliest expected impact time",
    )
    latest_resolution: Optional[datetime] = Field(
        default=None,
        description="Latest expected resolution time",
    )
    is_ongoing: bool = Field(
        default=False,
        description="Is the event currently active?",
    )

    @computed_field
    @property
    def duration_estimate_days(self) -> Optional[int]:
        """Estimated duration in days."""
        if self.earliest_impact and self.latest_resolution:
            delta = self.latest_resolution - self.earliest_impact
            return max(1, delta.days)
        return None


class OmenSignal(BaseModel):
    """
    OMEN Signal - A validated predictive signal.

    This is the output of OMEN and input to ORACLE/RISKCAST.

    IMPORTANT:
    - confidence_score = DATA QUALITY (how reliable is this information?)
    - probability = EVENT LIKELIHOOD (from prediction markets like Polymarket)

    These are DIFFERENT concepts:
    - High confidence + Low probability = "We're sure it probably won't happen"
    - Low confidence + High probability = "Unreliable data says it will happen"
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "signal_id": "OMEN-RS2024-001",
                "title": "Red Sea shipping disruption - Houthi attacks",
                "category": "geopolitical",
                "probability": 0.78,
                "confidence_score": 0.85,
            }
        }
    )

    # Identity
    signal_id: str = Field(description="Unique signal identifier")
    title: str = Field(max_length=200, description="Signal title")
    description: str = Field(max_length=2000, description="Detailed description")
    
    @field_validator("signal_id")
    @classmethod
    def validate_signal_id(cls, v: str) -> str:
        """Validate signal ID format."""
        if not v or len(v) < 3:
            raise ValueError("signal_id must be at least 3 characters")
        if not v.replace("-", "").replace("_", "").isalnum():
            raise ValueError("signal_id must contain only alphanumeric characters, hyphens, and underscores")
        return v
    
    @field_validator("probability", "confidence_score")
    @classmethod
    def validate_score_range(cls, v: float) -> float:
        """Validate score is in valid range."""
        if v < 0.0 or v > 1.0:
            raise ValueError("Score must be between 0 and 1")
        return v

    # Classification
    category: SignalCategory = Field(description="Signal category")

    # Probability & Confidence (DIFFERENT CONCEPTS!)
    probability: float = Field(
        ge=0,
        le=1,
        description="Event probability from prediction market (0-1)",
    )
    confidence_score: float = Field(
        ge=0,
        le=1,
        description="Data quality/reliability score (0-1)",
    )

    # Context
    geographic: GeographicScope = Field(description="Geographic scope")
    temporal: TemporalScope = Field(description="Temporal scope")

    # Evidence
    evidence: list[EvidenceItem] = Field(
        default_factory=list,
        description="Supporting evidence",
    )

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    source_signal_ids: list[str] = Field(
        default_factory=list,
        description="IDs of source signals if aggregated",
    )

    @computed_field
    @property
    def evidence_count(self) -> int:
        """Number of evidence items."""
        return len(self.evidence)

    @computed_field
    @property
    def has_prediction_market_data(self) -> bool:
        """Whether signal has prediction market evidence."""
        return any(
            e.source_type == "prediction_market" and e.probability is not None
            for e in self.evidence
        )

    def get_polymarket_probability(self) -> Optional[float]:
        """Get probability from Polymarket evidence if available."""
        for evidence in self.evidence:
            if evidence.source.lower() == "polymarket" and evidence.probability is not None:
                return evidence.probability
        return None
