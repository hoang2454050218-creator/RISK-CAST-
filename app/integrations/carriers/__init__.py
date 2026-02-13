"""
Carrier Integrations Module.

Integrates with shipping carriers to verify and execute actions:
- Check available capacity
- Get current rates
- Create bookings
- Cancel bookings

This makes RISKCAST recommendations actionable.
"""

from app.integrations.carriers.base import (
    BookingStatus,
    CarrierCapacity,
    BookingRequest,
    BookingResponse,
    CarrierIntegration,
    ActionabilityService,
    get_actionability_service,
)

from app.integrations.carriers.maersk import MaerskIntegration
from app.integrations.carriers.msc import MSCIntegration

__all__ = [
    "BookingStatus",
    "CarrierCapacity",
    "BookingRequest",
    "BookingResponse",
    "CarrierIntegration",
    "ActionabilityService",
    "get_actionability_service",
    "MaerskIntegration",
    "MSCIntegration",
]
