"""
Freight Rate Data Client.

Provides container freight rate data from:
- Freightos Baltic Index (FBX)
- Drewry World Container Index
- Xeneta
- Shanghai Shipping Exchange

For development, provides mock data with realistic rate patterns.
"""

from typing import Optional
from datetime import datetime, timedelta
from enum import Enum
import asyncio
import random

import httpx
import structlog
from pydantic import BaseModel, Field

from app.common.resilience import retry_with_backoff, CircuitBreaker
from app.omen.schemas import Chokepoint
from app.core.config import settings

logger = structlog.get_logger(__name__)


# ============================================================================
# MODELS
# ============================================================================


class FreightRoute(str, Enum):
    """Major freight route identifiers."""

    ASIA_NORTH_EUROPE = "asia_north_europe"  # FBX01
    ASIA_MEDITERRANEAN = "asia_med"  # FBX02
    ASIA_US_EAST = "asia_us_east"  # FBX03
    ASIA_US_WEST = "asia_us_west"  # FBX04
    EUROPE_US_EAST = "europe_us_east"  # FBX11


class FreightRateData(BaseModel):
    """Container freight rate data point."""

    route: FreightRoute
    route_name: str = Field(description="Human-readable route name")
    current_rate_usd: float = Field(ge=0, description="Current rate per FEU (USD)")
    previous_rate_usd: float = Field(ge=0, description="Previous rate")
    baseline_rate_usd: float = Field(ge=0, description="6-month average baseline")
    rate_change_pct: float = Field(description="Change from previous")
    premium_pct: float = Field(description="Premium above baseline")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Index info
    index_name: str = Field(default="FBX", description="Source index name")
    index_code: Optional[str] = Field(default=None, description="Index code")


class FreightRateSnapshot(BaseModel):
    """Snapshot of freight rates across routes."""

    snapshot_id: str
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    rates: dict[str, FreightRateData] = Field(default_factory=dict)
    global_average_rate: float = Field(default=0, description="Global average rate")
    global_premium_pct: float = Field(default=0, description="Global premium vs baseline")


# ============================================================================
# BASELINE RATES (6-month averages in normal conditions)
# ============================================================================

BASELINE_RATES = {
    FreightRoute.ASIA_NORTH_EUROPE: {
        "baseline": 1500.0,  # Per FEU
        "low_range": 1200.0,
        "high_range": 2500.0,
        "crisis_rate": 8000.0,  # During Red Sea crisis
        "index_code": "FBX01",
        "name": "Asia - North Europe (via Suez)",
    },
    FreightRoute.ASIA_MEDITERRANEAN: {
        "baseline": 1600.0,
        "low_range": 1300.0,
        "high_range": 2700.0,
        "crisis_rate": 7500.0,
        "index_code": "FBX02",
        "name": "Asia - Mediterranean",
    },
    FreightRoute.ASIA_US_EAST: {
        "baseline": 2500.0,
        "low_range": 2000.0,
        "high_range": 4000.0,
        "crisis_rate": 9000.0,
        "index_code": "FBX03",
        "name": "Asia - US East Coast",
    },
    FreightRoute.ASIA_US_WEST: {
        "baseline": 1800.0,
        "low_range": 1400.0,
        "high_range": 3000.0,
        "crisis_rate": 5000.0,
        "index_code": "FBX04",
        "name": "Asia - US West Coast",
    },
    FreightRoute.EUROPE_US_EAST: {
        "baseline": 1200.0,
        "low_range": 900.0,
        "high_range": 2000.0,
        "crisis_rate": 4000.0,
        "index_code": "FBX11",
        "name": "North Europe - US East Coast",
    },
}


# ============================================================================
# FREIGHT CLIENT
# ============================================================================


class FreightRateClient:
    """
    Client for container freight rate data.

    Provides current freight rates from major indices.
    In development mode, returns realistic mock data.

    Usage:
        async with FreightRateClient() as client:
            # Get all rates
            snapshot = await client.get_rate_snapshot()

            # Get specific route
            rate = await client.get_route_rate(FreightRoute.ASIA_NORTH_EUROPE)

            # Get rates affected by chokepoint
            rates = await client.get_rates_for_chokepoint(Chokepoint.RED_SEA)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.freightos.com",
        mock_mode: bool = True,
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.mock_mode = mock_mode
        self._http_client: Optional[httpx.AsyncClient] = None
        self._circuit_breaker = CircuitBreaker(
            name="freight_api",
            failure_threshold=5,
            recovery_timeout=60.0,
        )
        self._cache: dict[str, tuple[FreightRateData, datetime]] = {}
        self._cache_ttl = timedelta(minutes=15)

    async def __aenter__(self) -> "FreightRateClient":
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()
        return False

    async def connect(self):
        """Initialize HTTP client."""
        if self._http_client is None:
            headers = {"Accept": "application/json"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            self._http_client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(30.0),
                headers=headers,
            )
            logger.info("freight_client_connected")

    async def disconnect(self):
        """Close HTTP client."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
            logger.info("freight_client_disconnected")

    # ========================================================================
    # RATE QUERIES
    # ========================================================================

    async def get_rate_snapshot(
        self,
        disruption_factor: float = 0.0,
    ) -> FreightRateSnapshot:
        """
        Get current freight rates for all routes.

        Args:
            disruption_factor: Factor to simulate disruption (0.0-1.0)
                              Higher value = more rate increase

        Returns:
            FreightRateSnapshot with all route rates
        """
        rates = {}

        for route in FreightRoute:
            rate = await self.get_route_rate(route, disruption_factor)
            rates[route.value] = rate

        # Calculate global averages
        all_rates = list(rates.values())
        avg_rate = sum(r.current_rate_usd for r in all_rates) / len(all_rates)
        avg_premium = sum(r.premium_pct for r in all_rates) / len(all_rates)

        snapshot = FreightRateSnapshot(
            snapshot_id=f"FRT-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            rates=rates,
            global_average_rate=round(avg_rate, 2),
            global_premium_pct=round(avg_premium, 4),
        )

        logger.debug(
            "freight_snapshot_generated",
            routes=len(rates),
            avg_rate=avg_rate,
        )

        return snapshot

    async def get_route_rate(
        self,
        route: FreightRoute,
        disruption_factor: float = 0.0,
    ) -> FreightRateData:
        """
        Get current freight rate for a specific route.

        Args:
            route: The freight route
            disruption_factor: Factor to simulate disruption

        Returns:
            FreightRateData for the route
        """
        # Check cache
        cache_key = f"{route.value}:{disruption_factor:.2f}"
        if cache_key in self._cache:
            cached_rate, cached_at = self._cache[cache_key]
            if datetime.utcnow() - cached_at < self._cache_ttl:
                return cached_rate

        if self.mock_mode:
            rate = await self._mock_route_rate(route, disruption_factor)
        else:
            rate = await self._fetch_route_rate(route)

        # Cache result
        self._cache[cache_key] = (rate, datetime.utcnow())

        return rate

    async def get_rates_for_chokepoint(
        self,
        chokepoint: Chokepoint,
        disruption_factor: float = 0.0,
    ) -> list[FreightRateData]:
        """
        Get freight rates for routes affected by a chokepoint.

        Args:
            chokepoint: The chokepoint
            disruption_factor: Disruption factor

        Returns:
            List of affected route rates
        """
        # Map chokepoints to affected routes
        chokepoint_routes = {
            Chokepoint.RED_SEA: [
                FreightRoute.ASIA_NORTH_EUROPE,
                FreightRoute.ASIA_MEDITERRANEAN,
                FreightRoute.ASIA_US_EAST,
            ],
            Chokepoint.SUEZ: [
                FreightRoute.ASIA_NORTH_EUROPE,
                FreightRoute.ASIA_MEDITERRANEAN,
                FreightRoute.ASIA_US_EAST,
            ],
            Chokepoint.PANAMA: [
                FreightRoute.ASIA_US_EAST,
            ],
            Chokepoint.MALACCA: [
                FreightRoute.ASIA_NORTH_EUROPE,
                FreightRoute.ASIA_MEDITERRANEAN,
                FreightRoute.ASIA_US_WEST,
            ],
        }

        affected_routes = chokepoint_routes.get(chokepoint, [])
        rates = []

        for route in affected_routes:
            rate = await self.get_route_rate(route, disruption_factor)
            rates.append(rate)

        return rates

    async def get_rate_per_teu(
        self,
        route: FreightRoute,
        disruption_factor: float = 0.0,
    ) -> float:
        """
        Get rate per TEU (half of FEU rate).

        Most rates are quoted per FEU (40ft container).
        This converts to TEU (20ft equivalent).
        """
        rate = await self.get_route_rate(route, disruption_factor)
        return rate.current_rate_usd / 2

    # ========================================================================
    # INTERNAL METHODS
    # ========================================================================

    @retry_with_backoff(max_retries=3)
    async def _fetch_route_rate(self, route: FreightRoute) -> FreightRateData:
        """Fetch rate from real API."""
        async with self._circuit_breaker:
            route_info = BASELINE_RATES[route]

            response = await self._http_client.get(
                f"/fbx/{route_info['index_code']}"
            )
            response.raise_for_status()

            data = response.json()

            current = float(data.get("rate", route_info["baseline"]))
            previous = float(data.get("previous_rate", current * 0.98))
            baseline = route_info["baseline"]

            return FreightRateData(
                route=route,
                route_name=route_info["name"],
                current_rate_usd=current,
                previous_rate_usd=previous,
                baseline_rate_usd=baseline,
                rate_change_pct=round((current - previous) / previous, 4) if previous else 0,
                premium_pct=round((current - baseline) / baseline, 4) if baseline else 0,
                index_name="FBX",
                index_code=route_info["index_code"],
            )

    async def _mock_route_rate(
        self,
        route: FreightRoute,
        disruption_factor: float,
    ) -> FreightRateData:
        """Generate mock rate data."""
        await asyncio.sleep(0.05)  # Simulate latency

        route_info = BASELINE_RATES[route]
        baseline = route_info["baseline"]
        low = route_info["low_range"]
        high = route_info["high_range"]
        crisis = route_info["crisis_rate"]

        # Calculate current rate based on disruption
        if disruption_factor > 0.8:
            # Crisis level - rates spike toward crisis levels
            current = baseline + (crisis - baseline) * disruption_factor
        elif disruption_factor > 0.5:
            # High disruption - above normal range
            current = high + (crisis - high) * (disruption_factor - 0.5) * 2
        elif disruption_factor > 0.2:
            # Moderate disruption - in upper range
            current = baseline + (high - baseline) * disruption_factor * 2
        else:
            # Normal conditions - slight random variation
            current = baseline * (1 + random.uniform(-0.1, 0.15))

        # Add some randomness
        current = current * (1 + random.uniform(-0.02, 0.02))
        current = round(current, 2)

        # Previous rate (slightly different)
        previous = current * (1 + random.uniform(-0.05, 0.05))
        previous = round(previous, 2)

        return FreightRateData(
            route=route,
            route_name=route_info["name"],
            current_rate_usd=current,
            previous_rate_usd=previous,
            baseline_rate_usd=baseline,
            rate_change_pct=round((current - previous) / previous, 4) if previous else 0,
            premium_pct=round((current - baseline) / baseline, 4) if baseline else 0,
            index_name="FBX (Mock)",
            index_code=route_info["index_code"],
        )


# ============================================================================
# FACTORY
# ============================================================================


_client_instance: Optional[FreightRateClient] = None


def get_freight_client() -> FreightRateClient:
    """Get freight rate client singleton."""
    global _client_instance
    if _client_instance is None:
        _client_instance = FreightRateClient()
    return _client_instance
