"""
Carrier Integration Base - For actionable recommendations.

Provides abstract base class and common functionality for carrier integrations.

Addresses audit gaps:
- E1.4 Actionability (5/25): Verify that recommended actions are executable
- E2.3 Integration Depth (4/25): Deep integration with carrier systems
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from enum import Enum

import structlog
from pydantic import BaseModel, Field, computed_field

logger = structlog.get_logger(__name__)


# ============================================================================
# ENUMS
# ============================================================================


class BookingStatus(str, Enum):
    """Booking availability status."""
    AVAILABLE = "available"     # Space available
    LIMITED = "limited"         # Limited availability
    SOLD_OUT = "sold_out"      # No space
    UNKNOWN = "unknown"        # Cannot determine


class CarrierCode(str, Enum):
    """Standard carrier codes (SCAC)."""
    MAERSK = "MAEU"
    MSC = "MSCU"
    CMA_CGM = "CMDU"
    COSCO = "COSU"
    EVERGREEN = "EGLV"
    HAPAG_LLOYD = "HLCU"
    ONE = "ONEY"
    YANG_MING = "YMLU"


class RouteType(str, Enum):
    """Type of route."""
    DIRECT = "direct"
    TRANSSHIPMENT = "transshipment"
    ALTERNATIVE = "alternative"  # Reroute (e.g., Cape route)


# ============================================================================
# SCHEMAS
# ============================================================================


class CarrierCapacity(BaseModel):
    """Carrier capacity information for a specific sailing."""
    
    # Identity
    carrier: str = Field(description="Carrier name/code")
    service: str = Field(description="Service name (e.g., 'AE1')")
    route: str = Field(description="Route identifier")
    vessel: Optional[str] = Field(default=None, description="Vessel name")
    voyage: Optional[str] = Field(default=None, description="Voyage number")
    
    # Timing
    departure_date: datetime = Field(description="Scheduled departure")
    arrival_date: datetime = Field(description="Estimated arrival")
    booking_deadline: datetime = Field(description="Last booking date")
    
    # Capacity
    available_teu: int = Field(ge=0, description="Available TEU capacity")
    total_capacity_teu: int = Field(ge=0, description="Total vessel TEU capacity")
    status: BookingStatus = Field(default=BookingStatus.UNKNOWN)
    
    # Pricing
    base_rate_per_teu: float = Field(ge=0, description="Base rate per TEU")
    surcharges: Dict[str, float] = Field(default_factory=dict, description="Surcharge breakdown")
    total_rate_per_teu: float = Field(ge=0, description="Total rate per TEU")
    currency: str = Field(default="USD")
    
    # Quality metrics
    transit_days: int = Field(ge=0, description="Transit time in days")
    reliability_score: float = Field(ge=0, le=1, description="On-time performance")
    route_type: RouteType = Field(default=RouteType.DIRECT)
    
    # Data freshness
    data_timestamp: datetime = Field(default_factory=datetime.utcnow)
    data_source: str = Field(default="api", description="Data source")
    
    @computed_field
    @property
    def capacity_utilization(self) -> float:
        """Current capacity utilization."""
        if self.total_capacity_teu == 0:
            return 1.0
        return 1 - (self.available_teu / self.total_capacity_teu)
    
    @computed_field
    @property
    def is_bookable(self) -> bool:
        """Can this sailing be booked?"""
        return (
            self.status == BookingStatus.AVAILABLE and
            self.booking_deadline > datetime.utcnow()
        )
    
    @computed_field
    @property
    def urgency_factor(self) -> float:
        """Urgency based on booking deadline proximity."""
        hours_until_deadline = (self.booking_deadline - datetime.utcnow()).total_seconds() / 3600
        if hours_until_deadline < 24:
            return 1.0  # Critical
        elif hours_until_deadline < 72:
            return 0.7  # High
        elif hours_until_deadline < 168:
            return 0.4  # Medium
        return 0.2  # Low


class BookingRequest(BaseModel):
    """Request to book carrier capacity."""
    
    # Customer
    customer_id: str = Field(description="Customer identifier")
    customer_name: Optional[str] = None
    
    # Route
    origin_port: str = Field(description="Origin port code")
    destination_port: str = Field(description="Destination port code")
    route: str = Field(description="Route identifier")
    
    # Cargo
    teu_count: int = Field(gt=0, description="Number of TEUs")
    container_type: str = Field(default="40HC", description="Container type")
    cargo_description: Optional[str] = None
    hazmat: bool = Field(default=False)
    
    # Timing
    preferred_departure: datetime = Field(description="Preferred departure date")
    flexibility_days: int = Field(default=3, ge=0, description="Date flexibility")
    latest_arrival: Optional[datetime] = Field(default=None, description="Latest acceptable arrival")
    
    # Budget
    max_rate_per_teu: Optional[float] = Field(default=None, description="Max acceptable rate")
    
    # Preferences
    preferred_carriers: List[str] = Field(default_factory=list)
    excluded_carriers: List[str] = Field(default_factory=list)
    
    @computed_field
    @property
    def departure_window_start(self) -> datetime:
        """Start of departure window."""
        return self.preferred_departure - timedelta(days=self.flexibility_days)
    
    @computed_field
    @property
    def departure_window_end(self) -> datetime:
        """End of departure window."""
        return self.preferred_departure + timedelta(days=self.flexibility_days)


class BookingResponse(BaseModel):
    """Response from carrier booking attempt."""
    
    # Status
    success: bool = Field(description="Whether booking succeeded")
    error_message: Optional[str] = None
    error_code: Optional[str] = None
    
    # Booking details (if successful)
    booking_reference: Optional[str] = None
    confirmation_number: Optional[str] = None
    
    # Carrier info
    carrier: str = Field(description="Carrier name")
    service: Optional[str] = None
    vessel: Optional[str] = None
    voyage: Optional[str] = None
    
    # Route
    route: str
    origin_port: Optional[str] = None
    destination_port: Optional[str] = None
    
    # Timing
    departure_date: datetime
    estimated_arrival: datetime
    transit_days: int
    
    # Cargo
    confirmed_teu: int = Field(ge=0)
    container_type: str = Field(default="40HC")
    
    # Pricing
    rate_per_teu: float = Field(ge=0)
    total_cost: float = Field(ge=0)
    surcharges: Dict[str, float] = Field(default_factory=dict)
    currency: str = Field(default="USD")
    
    # Deadlines
    payment_deadline: Optional[datetime] = None
    si_cutoff: Optional[datetime] = None  # Shipping instructions
    vgm_cutoff: Optional[datetime] = None  # Verified gross mass
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    valid_until: Optional[datetime] = None


# ============================================================================
# FEASIBILITY CHECK
# ============================================================================


class ActionFeasibility(BaseModel):
    """Result of checking action feasibility."""
    
    # Overall
    feasible: bool = Field(description="Is the action feasible?")
    reason: Optional[str] = Field(default=None, description="Why (not) feasible")
    
    # Component checks
    capacity_available: bool = Field(default=False)
    price_acceptable: bool = Field(default=False)
    timing_feasible: bool = Field(default=False)
    route_viable: bool = Field(default=False)
    
    # Options found
    best_options: List[CarrierCapacity] = Field(default_factory=list)
    alternative_options: List[CarrierCapacity] = Field(default_factory=list)
    
    # Metrics
    lowest_rate: Optional[float] = None
    fastest_transit: Optional[int] = None
    soonest_departure: Optional[datetime] = None
    
    # Recommendations
    recommended_carrier: Optional[str] = None
    recommended_sailing: Optional[str] = None
    recommendation_reason: Optional[str] = None
    
    # Warnings
    warnings: List[str] = Field(default_factory=list)


# ============================================================================
# ABSTRACT BASE CLASS
# ============================================================================


class CarrierIntegration(ABC):
    """
    Abstract base class for carrier integrations.
    
    Each carrier (Maersk, MSC, etc.) implements this interface.
    """
    
    @property
    @abstractmethod
    def carrier_name(self) -> str:
        """Carrier display name."""
        pass
    
    @property
    @abstractmethod
    def carrier_code(self) -> str:
        """Carrier SCAC code."""
        pass
    
    @property
    def is_available(self) -> bool:
        """Whether integration is available/configured."""
        return True
    
    @abstractmethod
    async def check_capacity(
        self,
        route: str,
        departure_window_start: datetime,
        departure_window_end: datetime,
        teu_needed: int,
    ) -> List[CarrierCapacity]:
        """
        Check available capacity for a route.
        
        Args:
            route: Route identifier
            departure_window_start: Earliest departure
            departure_window_end: Latest departure
            teu_needed: Number of TEUs needed
            
        Returns:
            List of available sailings with capacity
        """
        pass
    
    @abstractmethod
    async def get_rates(
        self,
        origin: str,
        destination: str,
        teu_count: int,
        departure_date: datetime,
    ) -> Dict[str, float]:
        """
        Get current rates for a route.
        
        Args:
            origin: Origin port code
            destination: Destination port code
            teu_count: Number of TEUs
            departure_date: Departure date
            
        Returns:
            Dict with base rate, surcharges, total
        """
        pass
    
    @abstractmethod
    async def create_booking(
        self,
        request: BookingRequest,
        sailing: Optional[CarrierCapacity] = None,
    ) -> BookingResponse:
        """
        Create a booking.
        
        Args:
            request: Booking request details
            sailing: Specific sailing to book (optional)
            
        Returns:
            BookingResponse with result
        """
        pass
    
    @abstractmethod
    async def cancel_booking(
        self,
        booking_reference: str,
    ) -> bool:
        """
        Cancel a booking.
        
        Args:
            booking_reference: Booking reference number
            
        Returns:
            True if cancelled successfully
        """
        pass
    
    async def get_schedule(
        self,
        route: str,
        start_date: datetime,
        end_date: datetime,
    ) -> List[Dict[str, Any]]:
        """
        Get sailing schedule for a route.
        
        Default implementation returns empty list.
        Override for carriers that support schedule lookup.
        """
        return []


# ============================================================================
# ACTIONABILITY SERVICE
# ============================================================================


class ActionabilityService:
    """
    Makes RISKCAST recommendations actionable.
    
    Verifies that recommended actions are actually executable:
    - Carrier capacity available
    - Pricing within budget
    - Timing feasible
    - Route viable
    
    This is crucial for E1.4 Actionability score.
    """
    
    def __init__(self, carriers: Optional[List[CarrierIntegration]] = None):
        """
        Initialize with carrier integrations.
        
        Args:
            carriers: List of carrier integrations
        """
        self._carriers: Dict[str, CarrierIntegration] = {}
        
        if carriers:
            for carrier in carriers:
                self._carriers[carrier.carrier_code] = carrier
    
    def register_carrier(self, carrier: CarrierIntegration) -> None:
        """Register a carrier integration."""
        self._carriers[carrier.carrier_code] = carrier
        logger.info("carrier_registered", carrier=carrier.carrier_name)
    
    def list_carriers(self) -> List[str]:
        """List registered carrier codes."""
        return list(self._carriers.keys())
    
    async def verify_action_feasibility(
        self,
        action_type: str,
        route: str,
        teu_count: int,
        departure_start: datetime,
        departure_end: datetime,
        max_rate: Optional[float] = None,
        preferred_carriers: Optional[List[str]] = None,
    ) -> ActionFeasibility:
        """
        Verify if a recommended action is feasible.
        
        Args:
            action_type: Type of action (reroute, expedite, etc.)
            route: Route identifier
            teu_count: Number of TEUs
            departure_start: Earliest departure
            departure_end: Latest departure
            max_rate: Maximum acceptable rate per TEU
            preferred_carriers: Preferred carrier codes
            
        Returns:
            ActionFeasibility with result and options
        """
        if action_type in ["monitor", "do_nothing"]:
            # These are always feasible
            return ActionFeasibility(
                feasible=True,
                reason="No action required",
                capacity_available=True,
                price_acceptable=True,
                timing_feasible=True,
                route_viable=True,
            )
        
        if action_type in ["reroute", "expedite"]:
            return await self._verify_shipping_action(
                route=route,
                teu_count=teu_count,
                departure_start=departure_start,
                departure_end=departure_end,
                max_rate=max_rate,
                preferred_carriers=preferred_carriers,
            )
        
        # Default: assume feasible for unknown action types
        return ActionFeasibility(
            feasible=True,
            reason=f"Action type '{action_type}' assumed feasible",
            warnings=[f"Unknown action type: {action_type}"],
        )
    
    async def _verify_shipping_action(
        self,
        route: str,
        teu_count: int,
        departure_start: datetime,
        departure_end: datetime,
        max_rate: Optional[float],
        preferred_carriers: Optional[List[str]],
    ) -> ActionFeasibility:
        """Verify shipping action (reroute/expedite) feasibility."""
        all_capacities: List[CarrierCapacity] = []
        warnings: List[str] = []
        
        # Check each carrier
        carriers_to_check = (
            [self._carriers[c] for c in preferred_carriers if c in self._carriers]
            if preferred_carriers
            else list(self._carriers.values())
        )
        
        if not carriers_to_check:
            return ActionFeasibility(
                feasible=False,
                reason="No carrier integrations available",
                warnings=["Configure carrier integrations to verify feasibility"],
            )
        
        for carrier in carriers_to_check:
            try:
                capacities = await carrier.check_capacity(
                    route=route,
                    departure_window_start=departure_start,
                    departure_window_end=departure_end,
                    teu_needed=teu_count,
                )
                all_capacities.extend(capacities)
            except Exception as e:
                logger.warning(
                    "carrier_check_failed",
                    carrier=carrier.carrier_name,
                    error=str(e),
                )
                warnings.append(f"Failed to check {carrier.carrier_name}: {str(e)}")
        
        if not all_capacities:
            return ActionFeasibility(
                feasible=False,
                reason="No capacity available from any carrier",
                capacity_available=False,
                warnings=warnings,
            )
        
        # Filter by availability
        available = [c for c in all_capacities if c.status == BookingStatus.AVAILABLE]
        
        if not available:
            return ActionFeasibility(
                feasible=False,
                reason="All sailings are fully booked",
                capacity_available=False,
                alternative_options=all_capacities[:3],
                warnings=warnings,
            )
        
        # Filter by price
        if max_rate:
            affordable = [c for c in available if c.total_rate_per_teu <= max_rate]
        else:
            affordable = available
        
        price_acceptable = len(affordable) > 0
        
        # Sort by best value (reliability + cost)
        def value_score(c: CarrierCapacity) -> float:
            # Prefer reliable, affordable, fast
            return (
                c.reliability_score * 100 -
                c.total_rate_per_teu / 100 -
                c.transit_days
            )
        
        best_options = sorted(affordable or available, key=value_score, reverse=True)[:5]
        
        # Recommendations
        if best_options:
            best = best_options[0]
            recommended_carrier = best.carrier
            recommended_sailing = f"{best.service or 'Direct'} - {best.departure_date.strftime('%Y-%m-%d')}"
            reason = f"Best value: {best.reliability_score:.0%} reliability, ${best.total_rate_per_teu:,.0f}/TEU, {best.transit_days}d transit"
        else:
            recommended_carrier = None
            recommended_sailing = None
            reason = None
        
        return ActionFeasibility(
            feasible=bool(best_options),
            reason=reason if best_options else "No affordable options found",
            capacity_available=True,
            price_acceptable=price_acceptable,
            timing_feasible=True,
            route_viable=True,
            best_options=best_options,
            alternative_options=[c for c in available if c not in best_options][:3],
            lowest_rate=min(c.total_rate_per_teu for c in best_options) if best_options else None,
            fastest_transit=min(c.transit_days for c in best_options) if best_options else None,
            soonest_departure=min(c.departure_date for c in best_options) if best_options else None,
            recommended_carrier=recommended_carrier,
            recommended_sailing=recommended_sailing,
            recommendation_reason=reason,
            warnings=warnings,
        )
    
    async def get_best_option(
        self,
        route: str,
        teu_count: int,
        departure_start: datetime,
        departure_end: datetime,
        optimize_for: str = "value",  # "value", "speed", "cost", "reliability"
    ) -> Optional[CarrierCapacity]:
        """
        Get the best shipping option for given criteria.
        
        Args:
            route: Route identifier
            teu_count: Number of TEUs
            departure_start: Earliest departure
            departure_end: Latest departure
            optimize_for: Optimization criteria
            
        Returns:
            Best CarrierCapacity option, or None if unavailable
        """
        feasibility = await self.verify_action_feasibility(
            action_type="reroute",
            route=route,
            teu_count=teu_count,
            departure_start=departure_start,
            departure_end=departure_end,
        )
        
        if not feasibility.best_options:
            return None
        
        options = feasibility.best_options
        
        if optimize_for == "speed":
            return min(options, key=lambda c: c.transit_days)
        elif optimize_for == "cost":
            return min(options, key=lambda c: c.total_rate_per_teu)
        elif optimize_for == "reliability":
            return max(options, key=lambda c: c.reliability_score)
        else:  # value (default)
            return options[0]  # Already sorted by value


# ============================================================================
# SINGLETON
# ============================================================================


_actionability_service: Optional[ActionabilityService] = None


def get_actionability_service() -> ActionabilityService:
    """Get global actionability service instance."""
    global _actionability_service
    if _actionability_service is None:
        _actionability_service = ActionabilityService()
    return _actionability_service
