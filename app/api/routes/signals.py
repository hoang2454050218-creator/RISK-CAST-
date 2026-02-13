"""Signal API Endpoints.

Query OMEN signals and ORACLE intelligence.
"""

from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.omen.schemas import OmenSignal, Chokepoint, SignalCategory
from app.omen.service import get_omen_service
from app.oracle.service import get_oracle_service
from app.oracle.schemas import CorrelatedIntelligence, CorrelationStatus

router = APIRouter()


# ============================================================================
# RESPONSE SCHEMAS
# ============================================================================


class SignalResponse(BaseModel):
    """Signal summary response."""

    signal_id: str
    title: str
    category: str
    source: str
    probability: float
    confidence_score: float
    chokepoint: str
    affected_regions: list[str]
    expected_start: Optional[datetime]
    expected_end: Optional[datetime]
    is_active: bool
    generated_at: datetime

    @classmethod
    def from_signal(cls, signal: OmenSignal) -> "SignalResponse":
        return cls(
            signal_id=signal.signal_id,
            title=signal.title,
            category=signal.category.value,
            source=signal.primary_source.value,
            probability=signal.probability,
            confidence_score=signal.confidence_score,
            chokepoint=signal.geographic.primary_chokepoint.value,
            affected_regions=signal.geographic.affected_regions,
            expected_start=signal.temporal.expected_start,
            expected_end=signal.temporal.expected_end,
            is_active=signal.is_active,
            generated_at=signal.generated_at,
        )


class SignalDetailResponse(BaseModel):
    """Full signal details."""

    signal_id: str
    title: str
    description: str
    category: str

    # Sources
    primary_source: str
    evidence_items: list[dict]

    # Probability
    probability: float
    confidence_score: float

    # Geographic
    chokepoint: str
    affected_regions: list[str]
    affected_ports: list[str]

    # Temporal
    expected_start: Optional[datetime]
    expected_end: Optional[datetime]
    expected_duration_hours: Optional[float]
    is_active: bool

    generated_at: datetime


class IntelligenceResponse(BaseModel):
    """Correlated intelligence response."""

    correlation_id: str
    signal_id: str
    signal_title: str
    chokepoint: str

    # Correlation
    correlation_status: str
    combined_confidence: float
    is_actionable: bool

    # Signal data
    signal_probability: float
    signal_confidence: float

    # Reality data
    rate_premium_pct: float
    rerouting_count: int
    average_delay_hours: float

    # Correlation factors
    correlation_factors: dict[str, float]

    correlated_at: datetime


class SignalListResponse(BaseModel):
    """List of signals."""

    items: list[SignalResponse]
    total: int


class IntelligenceListResponse(BaseModel):
    """List of intelligence items."""

    items: list[IntelligenceResponse]
    total: int
    actionable_count: int


# ============================================================================
# HELPERS
# ============================================================================


def intelligence_to_response(intel: CorrelatedIntelligence) -> IntelligenceResponse:
    """Convert CorrelatedIntelligence to response."""
    return IntelligenceResponse(
        correlation_id=intel.correlation_id,
        signal_id=intel.signal.signal_id,
        signal_title=intel.signal.title,
        chokepoint=intel.primary_chokepoint,
        correlation_status=intel.correlation_status.value,
        combined_confidence=intel.combined_confidence,
        is_actionable=intel.is_actionable,
        signal_probability=intel.signal.probability,
        signal_confidence=intel.signal.confidence_score,
        rate_premium_pct=intel.get_reality_rate_premium(),
        rerouting_count=intel.get_reality_rerouting_count(),
        average_delay_hours=intel.correlation_factors.get("average_delay_hours", 0),
        correlation_factors=intel.correlation_factors,
        correlated_at=intel.correlated_at,
    )


# ============================================================================
# ENDPOINTS
# ============================================================================


@router.get(
    "",
    response_model=SignalListResponse,
    summary="List signals",
    description="List all active signals from OMEN",
)
async def list_signals(
    chokepoint: Optional[str] = Query(default=None, description="Filter by chokepoint"),
    category: Optional[SignalCategory] = Query(default=None, description="Filter by category"),
    min_probability: float = Query(default=0.3, ge=0, le=1, description="Minimum probability"),
) -> SignalListResponse:
    """List active signals."""
    omen = get_omen_service()

    chokepoints = [chokepoint] if chokepoint else None

    signals = await omen.get_active_signals(
        chokepoints=chokepoints,
        min_probability=min_probability,
    )

    # Filter by category
    if category:
        signals = [s for s in signals if s.category == category]

    return SignalListResponse(
        items=[SignalResponse.from_signal(s) for s in signals],
        total=len(signals),
    )


@router.get(
    "/{signal_id}",
    response_model=SignalDetailResponse,
    summary="Get signal",
    description="Get detailed signal information",
)
async def get_signal(
    signal_id: str,
) -> SignalDetailResponse:
    """Get signal by ID."""
    omen = get_omen_service()
    signal = await omen.get_signal(signal_id)

    if not signal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Signal {signal_id} not found",
        )

    return SignalDetailResponse(
        signal_id=signal.signal_id,
        title=signal.title,
        description=signal.description,
        category=signal.category.value,
        primary_source=signal.primary_source.value,
        evidence_items=[e.model_dump() for e in signal.evidence],
        probability=signal.probability,
        confidence_score=signal.confidence_score,
        chokepoint=signal.geographic.primary_chokepoint.value,
        affected_regions=signal.geographic.affected_regions,
        affected_ports=signal.geographic.affected_ports,
        expected_start=signal.temporal.expected_start,
        expected_end=signal.temporal.expected_end,
        expected_duration_hours=signal.temporal.expected_duration_hours,
        is_active=signal.is_active,
        generated_at=signal.generated_at,
    )


@router.get(
    "/route/{origin}/{destination}",
    response_model=SignalListResponse,
    summary="Get signals for route",
    description="Get signals affecting a specific shipping route",
)
async def get_signals_for_route(
    origin: str,
    destination: str,
    min_probability: float = Query(default=0.3, ge=0, le=1),
) -> SignalListResponse:
    """Get signals for a shipping route."""
    omen = get_omen_service()

    signals = await omen.get_signals_for_route(
        origin=origin,
        destination=destination,
        min_probability=min_probability,
    )

    return SignalListResponse(
        items=[SignalResponse.from_signal(s) for s in signals],
        total=len(signals),
    )


@router.get(
    "/intelligence",
    response_model=IntelligenceListResponse,
    summary="Get correlated intelligence",
    description="Get OMEN signals correlated with ORACLE reality data",
)
async def get_intelligence(
    chokepoint: Optional[str] = Query(default=None, description="Filter by chokepoint"),
    min_probability: float = Query(default=0.3, ge=0, le=1),
    actionable_only: bool = Query(default=False, description="Only return actionable intelligence"),
) -> IntelligenceListResponse:
    """Get correlated intelligence."""
    oracle = get_oracle_service()

    if actionable_only:
        intel_list = await oracle.get_actionable_intelligence(
            chokepoints=[chokepoint] if chokepoint else None,
            min_probability=min_probability,
        )
    else:
        # Get all signals and correlate
        omen = get_omen_service()
        signals = await omen.get_active_signals(
            chokepoints=[chokepoint] if chokepoint else None,
            min_probability=min_probability,
        )

        intel_list = []
        for signal in signals:
            intel = await oracle.get_correlated_intelligence(signal)
            intel_list.append(intel)

    actionable_count = sum(1 for i in intel_list if i.is_actionable)

    return IntelligenceListResponse(
        items=[intelligence_to_response(i) for i in intel_list],
        total=len(intel_list),
        actionable_count=actionable_count,
    )


@router.get(
    "/intelligence/{correlation_id}",
    response_model=IntelligenceResponse,
    summary="Get intelligence by ID",
    description="Get specific correlated intelligence",
)
async def get_intelligence_by_id(
    correlation_id: str,
) -> IntelligenceResponse:
    """Get intelligence by correlation ID."""
    # In full implementation, this would fetch from a store
    # For now, we return 404
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Intelligence {correlation_id} not found. Try /signals/intelligence for live data.",
    )


@router.get(
    "/chokepoints",
    summary="List chokepoints",
    description="List all tracked chokepoints",
)
async def list_chokepoints() -> list[dict]:
    """List all tracked chokepoints."""
    return [
        {"code": cp.value, "name": cp.name.replace("_", " ").title()}
        for cp in Chokepoint
    ]


@router.get(
    "/chokepoints/{chokepoint}/status",
    summary="Get chokepoint status",
    description="Get current status and health of a chokepoint",
)
async def get_chokepoint_status(
    chokepoint: str,
) -> dict:
    """Get chokepoint status."""
    oracle = get_oracle_service()

    try:
        cp = Chokepoint(chokepoint.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown chokepoint: {chokepoint}",
        )

    health = await oracle.get_chokepoint_health(cp)

    return {
        "chokepoint": cp.value,
        "is_operational": health.is_operational,
        "disruption_level": health.disruption_level,
        "vessels_in_transit": health.vessels_in_transit,
        "vessels_waiting": health.vessels_waiting,
        "rerouting_count": health.rerouting_count,
        "current_rate_per_teu": health.current_rate_per_teu,
        "baseline_rate_per_teu": health.baseline_rate_per_teu,
        "rate_premium_pct": health.rate_premium_pct,
        "average_delay_hours": health.average_delay_hours,
        "congestion_ratio": health.congestion_ratio,
        "timestamp": health.timestamp.isoformat(),
    }
