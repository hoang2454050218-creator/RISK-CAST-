"""
MSC (Mediterranean Shipping Company) Carrier Integration.

Integrates with MSC systems for:
- Capacity checking
- Rate lookup
- Booking management

Note: This is a mock implementation for MVP.
Production implementation would use MSC's actual APIs.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import random

import structlog

from app.integrations.carriers.base import (
    CarrierIntegration,
    CarrierCapacity,
    BookingRequest,
    BookingResponse,
    BookingStatus,
    RouteType,
)

logger = structlog.get_logger(__name__)


class MSCIntegration(CarrierIntegration):
    """
    MSC (Mediterranean Shipping Company) integration.
    
    MSC is the world's largest container shipping company.
    They have robust digital systems but less public API documentation.
    
    Services covered:
    - Dragon (Asia-Europe)
    - Silk (Asia-Mediterranean)
    - Jaguar (Americas)
    - Albatross (Africa)
    """
    
    # MSC services for common routes
    SERVICES = {
        "asia_europe": ["Dragon", "Griffin", "Albatross", "Swan"],
        "asia_europe_cape": ["Dragon-Cape", "Albatross-Cape"],  # Cape alternatives
        "transpacific": ["Eagle", "Mustang", "Santana"],
        "asia_mediterranean": ["Silk", "Tiger", "Phoenix"],
    }
    
    # Average transit times (days)
    TRANSIT_TIMES = {
        "Dragon": 34,
        "Dragon-Cape": 48,  # +14 days for Cape
        "Griffin": 36,
        "Albatross": 38,
        "Albatross-Cape": 52,
        "Eagle": 13,
        "Mustang": 15,
        "Silk": 28,
    }
    
    # Base rates per TEU (USD) - MSC typically 5-10% lower than Maersk
    BASE_RATES = {
        "asia_europe": (2300, 4200),
        "asia_europe_cape": (3700, 6000),
        "transpacific": (1600, 3200),
        "asia_mediterranean": (2000, 3700),
    }
    
    # MSC has more capacity due to larger fleet
    CAPACITY_RANGE = (12000, 24000)
    
    def __init__(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None,
        sandbox: bool = True,
    ):
        """
        Initialize MSC integration.
        
        Args:
            username: MSC portal username
            password: MSC portal password
            sandbox: Use sandbox environment
        """
        self._username = username
        self._password = password
        self._sandbox = sandbox
        self._base_url = (
            "https://sandbox.msc.com/api"
            if sandbox
            else "https://www.msc.com/api"
        )
        
        logger.info(
            "msc_integration_initialized",
            sandbox=sandbox,
            configured=bool(username),
        )
    
    @property
    def carrier_name(self) -> str:
        return "MSC"
    
    @property
    def carrier_code(self) -> str:
        return "MSCU"
    
    @property
    def is_available(self) -> bool:
        """Check if integration is configured and available."""
        # In mock mode, always available
        if self._sandbox and not self._username:
            return True
        return bool(self._username and self._password)
    
    async def check_capacity(
        self,
        route: str,
        departure_window_start: datetime,
        departure_window_end: datetime,
        teu_needed: int,
    ) -> List[CarrierCapacity]:
        """
        Check MSC capacity for a route.
        
        MSC has the largest fleet, so typically more capacity available.
        """
        logger.info(
            "msc_check_capacity",
            route=route,
            start=departure_window_start.isoformat(),
            end=departure_window_end.isoformat(),
            teu_needed=teu_needed,
        )
        
        capacities = []
        
        # Determine route type and services
        is_cape_route = "cape" in route.lower() or "alternative" in route.lower()
        route_type = RouteType.ALTERNATIVE if is_cape_route else RouteType.DIRECT
        
        if "asia" in route.lower() and "europe" in route.lower():
            if is_cape_route:
                services = self.SERVICES["asia_europe_cape"]
                rate_range = self.BASE_RATES["asia_europe_cape"]
            else:
                services = self.SERVICES["asia_europe"]
                rate_range = self.BASE_RATES["asia_europe"]
        elif "pacific" in route.lower() or "transpacific" in route.lower():
            services = self.SERVICES["transpacific"]
            rate_range = self.BASE_RATES["transpacific"]
        elif "med" in route.lower():
            services = self.SERVICES["asia_mediterranean"]
            rate_range = self.BASE_RATES["asia_mediterranean"]
        else:
            services = self.SERVICES["asia_europe"]
            rate_range = self.BASE_RATES["asia_europe"]
        
        # MSC vessels
        vessels = [
            "MSC Irina", "MSC Loreto", "MSC Tina", "MSC Mia",
            "MSC Isabella", "MSC Gulsun", "MSC Sixin", "MSC Anna"
        ]
        
        # Generate sailings
        current = departure_window_start
        while current <= departure_window_end:
            for service in services[:3]:
                transit_days = self.TRANSIT_TIMES.get(
                    service,
                    44 if is_cape_route else 34
                )
                
                # MSC has larger vessels
                total_capacity = random.randint(*self.CAPACITY_RANGE)
                # MSC often has more availability
                utilization = random.uniform(0.45, 0.90)
                available_teu = int(total_capacity * (1 - utilization))
                
                if available_teu >= teu_needed:
                    status = BookingStatus.AVAILABLE
                elif available_teu > 0:
                    status = BookingStatus.LIMITED
                else:
                    status = BookingStatus.SOLD_OUT
                
                # MSC rates typically slightly lower
                base_rate = random.uniform(rate_range[0], rate_range[1])
                surcharges = {
                    "BAF": base_rate * 0.07,  # Slightly lower BAF
                    "THC": 230,
                    "DOC": 50,
                }
                if is_cape_route:
                    surcharges["WRS"] = 450
                    surcharges["ERS"] = 300
                    surcharges["CAC"] = 200  # Cape additional charge
                
                total_rate = base_rate + sum(surcharges.values())
                
                capacities.append(CarrierCapacity(
                    carrier="MSC",
                    service=service,
                    route=route,
                    vessel=random.choice(vessels),
                    voyage=f"M{random.randint(201, 252)}",
                    departure_date=current,
                    arrival_date=current + timedelta(days=transit_days),
                    booking_deadline=current - timedelta(days=4),  # MSC has shorter cutoffs
                    available_teu=available_teu,
                    total_capacity_teu=total_capacity,
                    status=status,
                    base_rate_per_teu=base_rate,
                    surcharges=surcharges,
                    total_rate_per_teu=total_rate,
                    transit_days=transit_days,
                    reliability_score=random.uniform(0.82, 0.92),  # Slightly lower than Maersk
                    route_type=route_type,
                    data_source="msc_mock",
                ))
            
            current += timedelta(days=7)
        
        logger.info(
            "msc_capacity_found",
            route=route,
            sailings=len(capacities),
            available=[c.available_teu for c in capacities if c.status == BookingStatus.AVAILABLE],
        )
        
        return capacities
    
    async def get_rates(
        self,
        origin: str,
        destination: str,
        teu_count: int,
        departure_date: datetime,
    ) -> Dict[str, float]:
        """Get current MSC rates."""
        logger.info(
            "msc_get_rates",
            origin=origin,
            destination=destination,
            teu_count=teu_count,
        )
        
        # Determine route
        if any(p in origin.upper() for p in ["SHA", "NGB", "YNT"]):
            if any(p in destination.upper() for p in ["RTM", "ANR", "HAM"]):
                rate_range = self.BASE_RATES["asia_europe"]
            elif any(p in destination.upper() for p in ["GEN", "BAR", "VAL"]):
                rate_range = self.BASE_RATES["asia_mediterranean"]
            else:
                rate_range = self.BASE_RATES["transpacific"]
        else:
            rate_range = self.BASE_RATES["asia_europe"]
        
        base_rate = random.uniform(rate_range[0], rate_range[1])
        
        surcharges = {
            "BAF": base_rate * 0.07,
            "THC_origin": 160,
            "THC_destination": 200,
            "documentation": 60,
        }
        
        total_per_teu = base_rate + sum(surcharges.values())
        
        return {
            "base_rate_per_teu": base_rate,
            "surcharges": surcharges,
            "total_per_teu": total_per_teu,
            "total_cost": total_per_teu * teu_count,
            "currency": "USD",
            "valid_until": (datetime.utcnow() + timedelta(hours=24)).isoformat(),
        }
    
    async def create_booking(
        self,
        request: BookingRequest,
        sailing: Optional[CarrierCapacity] = None,
    ) -> BookingResponse:
        """Create an MSC booking."""
        logger.info(
            "msc_create_booking",
            customer=request.customer_id,
            route=request.route,
            teu=request.teu_count,
        )
        
        if sailing:
            departure = sailing.departure_date
            arrival = sailing.arrival_date
            transit = sailing.transit_days
            rate = sailing.total_rate_per_teu
            service = sailing.service
        else:
            capacities = await self.check_capacity(
                route=request.route,
                departure_window_start=request.departure_window_start,
                departure_window_end=request.departure_window_end,
                teu_needed=request.teu_count,
            )
            available = [c for c in capacities if c.status == BookingStatus.AVAILABLE]
            
            if not available:
                return BookingResponse(
                    success=False,
                    error_message="No available capacity found",
                    error_code="NO_CAPACITY",
                    carrier="MSC",
                    route=request.route,
                    departure_date=request.preferred_departure,
                    estimated_arrival=request.preferred_departure + timedelta(days=34),
                    transit_days=34,
                    confirmed_teu=0,
                    rate_per_teu=0,
                    total_cost=0,
                )
            
            best = available[0]
            departure = best.departure_date
            arrival = best.arrival_date
            transit = best.transit_days
            rate = best.total_rate_per_teu
            service = best.service
        
        booking_ref = f"MSCU{random.randint(1000000, 9999999)}"
        
        vessels = ["MSC Irina", "MSC Loreto", "MSC Tina", "MSC Gulsun"]
        
        return BookingResponse(
            success=True,
            booking_reference=booking_ref,
            confirmation_number=f"MSC{booking_ref}",
            carrier="MSC",
            service=service,
            vessel=random.choice(vessels),
            voyage=f"M{random.randint(201, 252)}",
            route=request.route,
            origin_port=request.origin_port,
            destination_port=request.destination_port,
            departure_date=departure,
            estimated_arrival=arrival,
            transit_days=transit,
            confirmed_teu=request.teu_count,
            container_type=request.container_type,
            rate_per_teu=rate,
            total_cost=rate * request.teu_count,
            surcharges={
                "BAF": rate * 0.07 * request.teu_count,
                "THC": 230 * request.teu_count,
            },
            payment_deadline=departure - timedelta(days=5),
            si_cutoff=departure - timedelta(days=4),
            vgm_cutoff=departure - timedelta(days=3),
            valid_until=datetime.utcnow() + timedelta(hours=24),
        )
    
    async def cancel_booking(
        self,
        booking_reference: str,
    ) -> bool:
        """Cancel an MSC booking."""
        logger.info("msc_cancel_booking", reference=booking_reference)
        return True
    
    async def get_schedule(
        self,
        route: str,
        start_date: datetime,
        end_date: datetime,
    ) -> List[Dict[str, Any]]:
        """Get MSC sailing schedule."""
        schedules = []
        vessels = ["MSC Irina", "MSC Loreto", "MSC Tina", "MSC Gulsun"]
        
        current = start_date
        while current <= end_date:
            for service in self.SERVICES.get("asia_europe", ["Dragon"])[:2]:
                schedules.append({
                    "carrier": "MSC",
                    "service": service,
                    "vessel": random.choice(vessels),
                    "departure": current.isoformat(),
                    "transit_days": self.TRANSIT_TIMES.get(service, 34),
                })
            current += timedelta(days=7)
        
        return schedules


# ============================================================================
# CARRIER FACTORY
# ============================================================================


def get_configured_carriers(sandbox: bool = True) -> List[CarrierIntegration]:
    """
    Get list of configured carrier integrations.
    
    In production, this would load API keys from config/secrets.
    """
    return [
        MaerskIntegration(sandbox=sandbox),
        MSCIntegration(sandbox=sandbox),
    ]
