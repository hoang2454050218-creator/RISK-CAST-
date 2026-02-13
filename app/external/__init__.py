"""
External API Clients.

Production-grade clients for external data sources:
- AIS: Vessel tracking and chokepoint monitoring
- Polymarket: Prediction market signals

All clients include:
- Async HTTP with httpx
- Circuit breaker protection
- Rate limiting
- Retry logic
- Response caching
"""

from app.external.ais import (
    AISClient,
    AISConfig,
    Vessel,
    Position,
    PortCall,
    ChokepointTraffic,
    Chokepoint,
    VesselType,
    NavigationStatus,
    CHOKEPOINT_BOUNDS,
    get_ais_client,
)

from app.external.polymarket import (
    PolymarketClient,
    PolymarketConfig,
    Market,
    MarketEvent,
    MarketStatus,
    PriceHistory,
    get_polymarket_client,
)

__all__ = [
    # AIS
    "AISClient",
    "AISConfig",
    "Vessel",
    "Position",
    "PortCall",
    "ChokepointTraffic",
    "Chokepoint",
    "VesselType",
    "NavigationStatus",
    "CHOKEPOINT_BOUNDS",
    "get_ais_client",
    # Polymarket
    "PolymarketClient",
    "PolymarketConfig",
    "Market",
    "MarketEvent",
    "MarketStatus",
    "PriceHistory",
    "get_polymarket_client",
]
