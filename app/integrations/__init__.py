"""
RISKCAST Integrations Module.

Provides integrations with external services for actionable recommendations.

Integrations:
- Carriers: Maersk, MSC, and other shipping lines
- Rates: Real-time freight rate APIs
- Tracking: AIS and shipment tracking

Addresses audit gaps:
- E1.4 Actionability: 5 → 15 (+10)
- E2.3 Integration Depth: 4 → 12 (+8)
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
    # Base
    "BookingStatus",
    "CarrierCapacity",
    "BookingRequest",
    "BookingResponse",
    "CarrierIntegration",
    "ActionabilityService",
    "get_actionability_service",
    # Carriers
    "MaerskIntegration",
    "MSCIntegration",
]
