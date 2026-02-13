"""
Port Data Client.

Provides port congestion, wait times, and operational status from:
- Port authorities
- Terminal operators
- Shipping line APIs

For development, provides mock data with realistic patterns.
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

logger = structlog.get_logger(__name__)


# ============================================================================
# MODELS
# ============================================================================


class PortStatus(str, Enum):
    """Port operational status."""

    NORMAL = "normal"
    CONGESTED = "congested"
    SEVERE_CONGESTION = "severe_congestion"
    RESTRICTED = "restricted"
    CLOSED = "closed"


class PortData(BaseModel):
    """Port operational data."""

    port_code: str = Field(description="UN/LOCODE port code")
    port_name: str
    country: str
    region: str

    # Congestion metrics
    status: PortStatus = PortStatus.NORMAL
    average_wait_hours: float = Field(ge=0, description="Average anchor wait time")
    vessels_at_anchor: int = Field(ge=0, description="Vessels waiting at anchor")
    vessels_at_berth: int = Field(ge=0, description="Vessels at berth")
    berth_utilization_pct: float = Field(ge=0, le=1, description="Berth utilization")

    # Performance
    avg_turnaround_hours: float = Field(ge=0, description="Average port turnaround")
    congestion_index: float = Field(ge=0, le=1, description="0=clear, 1=severe")

    # Chokepoints this port is associated with
    associated_chokepoints: list[str] = Field(default_factory=list)

    timestamp: datetime = Field(default_factory=datetime.utcnow)


class PortSnapshot(BaseModel):
    """Snapshot of port data for multiple ports."""

    snapshot_id: str
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    ports: dict[str, PortData] = Field(default_factory=dict)
    average_congestion_index: float = Field(default=0)


# ============================================================================
# PORT DATABASE
# ============================================================================

# Major ports with baseline data
PORT_INFO = {
    "NLRTM": {
        "name": "Rotterdam",
        "country": "Netherlands",
        "region": "North Europe",
        "normal_wait": 4,
        "normal_turnaround": 24,
        "chokepoints": ["suez", "red_sea"],
    },
    "DEHAM": {
        "name": "Hamburg",
        "country": "Germany",
        "region": "North Europe",
        "normal_wait": 6,
        "normal_turnaround": 28,
        "chokepoints": ["suez", "red_sea"],
    },
    "BEANR": {
        "name": "Antwerp",
        "country": "Belgium",
        "region": "North Europe",
        "normal_wait": 5,
        "normal_turnaround": 26,
        "chokepoints": ["suez", "red_sea"],
    },
    "GBFXT": {
        "name": "Felixstowe",
        "country": "United Kingdom",
        "region": "North Europe",
        "normal_wait": 3,
        "normal_turnaround": 20,
        "chokepoints": ["suez", "red_sea"],
    },
    "CNSHA": {
        "name": "Shanghai",
        "country": "China",
        "region": "East Asia",
        "normal_wait": 8,
        "normal_turnaround": 18,
        "chokepoints": ["malacca"],
    },
    "CNNGB": {
        "name": "Ningbo-Zhoushan",
        "country": "China",
        "region": "East Asia",
        "normal_wait": 6,
        "normal_turnaround": 16,
        "chokepoints": ["malacca"],
    },
    "SGSIN": {
        "name": "Singapore",
        "country": "Singapore",
        "region": "Southeast Asia",
        "normal_wait": 2,
        "normal_turnaround": 12,
        "chokepoints": ["malacca"],
    },
    "SAJED": {
        "name": "Jeddah",
        "country": "Saudi Arabia",
        "region": "Middle East",
        "normal_wait": 4,
        "normal_turnaround": 20,
        "chokepoints": ["red_sea", "suez"],
    },
    "AEJEA": {
        "name": "Jebel Ali",
        "country": "UAE",
        "region": "Middle East",
        "normal_wait": 3,
        "normal_turnaround": 16,
        "chokepoints": ["hormuz"],
    },
    "EGPSD": {
        "name": "Port Said",
        "country": "Egypt",
        "region": "Mediterranean",
        "normal_wait": 12,
        "normal_turnaround": 8,
        "chokepoints": ["suez", "red_sea"],
    },
    "USNYC": {
        "name": "New York/New Jersey",
        "country": "USA",
        "region": "US East Coast",
        "normal_wait": 6,
        "normal_turnaround": 24,
        "chokepoints": ["suez", "panama"],
    },
    "USLAX": {
        "name": "Los Angeles",
        "country": "USA",
        "region": "US West Coast",
        "normal_wait": 8,
        "normal_turnaround": 28,
        "chokepoints": [],
    },
}


# ============================================================================
# PORT CLIENT
# ============================================================================


class PortDataClient:
    """
    Client for port congestion and operational data.

    Provides real-time port metrics and congestion levels.
    In development mode, returns realistic mock data.

    Usage:
        async with PortDataClient() as client:
            # Get port data
            port = await client.get_port("NLRTM")

            # Get ports affected by chokepoint
            ports = await client.get_ports_for_chokepoint(Chokepoint.RED_SEA)

            # Get global snapshot
            snapshot = await client.get_port_snapshot()
    """

    def __init__(
        self,
        mock_mode: bool = True,
        base_url: str = "https://api.portdata.example.com",
    ):
        self.mock_mode = mock_mode
        self.base_url = base_url
        self._http_client: Optional[httpx.AsyncClient] = None
        self._circuit_breaker = CircuitBreaker(
            name="port_api",
            failure_threshold=5,
            recovery_timeout=60.0,
        )
        self._cache: dict[str, tuple[PortData, datetime]] = {}
        self._cache_ttl = timedelta(minutes=30)

    async def __aenter__(self) -> "PortDataClient":
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()
        return False

    async def connect(self):
        """Initialize HTTP client."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(30.0),
            )
            logger.info("port_client_connected")

    async def disconnect(self):
        """Close HTTP client."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
            logger.info("port_client_disconnected")

    # ========================================================================
    # PORT QUERIES
    # ========================================================================

    async def get_port(
        self,
        port_code: str,
        disruption_factor: float = 0.0,
    ) -> Optional[PortData]:
        """
        Get data for a specific port.

        Args:
            port_code: UN/LOCODE port code
            disruption_factor: Factor to simulate disruption

        Returns:
            PortData or None if not found
        """
        # Check cache
        cache_key = f"{port_code}:{disruption_factor:.2f}"
        if cache_key in self._cache:
            cached, cached_at = self._cache[cache_key]
            if datetime.utcnow() - cached_at < self._cache_ttl:
                return cached

        if self.mock_mode:
            port = await self._mock_port_data(port_code, disruption_factor)
        else:
            port = await self._fetch_port_data(port_code)

        if port:
            self._cache[cache_key] = (port, datetime.utcnow())

        return port

    async def get_port_snapshot(
        self,
        port_codes: Optional[list[str]] = None,
        disruption_factor: float = 0.0,
    ) -> PortSnapshot:
        """
        Get snapshot of multiple ports.

        Args:
            port_codes: Specific ports to include (all if None)
            disruption_factor: Disruption simulation factor

        Returns:
            PortSnapshot with port data
        """
        codes = port_codes or list(PORT_INFO.keys())
        ports = {}

        for code in codes:
            port = await self.get_port(code, disruption_factor)
            if port:
                ports[code] = port

        # Calculate average congestion
        avg_congestion = 0.0
        if ports:
            avg_congestion = sum(p.congestion_index for p in ports.values()) / len(ports)

        return PortSnapshot(
            snapshot_id=f"PRT-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            ports=ports,
            average_congestion_index=round(avg_congestion, 3),
        )

    async def get_ports_for_chokepoint(
        self,
        chokepoint: Chokepoint,
        disruption_factor: float = 0.0,
    ) -> list[PortData]:
        """
        Get ports affected by a chokepoint.

        Args:
            chokepoint: The chokepoint
            disruption_factor: Disruption factor

        Returns:
            List of affected ports
        """
        affected_ports = []

        for code, info in PORT_INFO.items():
            if chokepoint.value in info.get("chokepoints", []):
                port = await self.get_port(code, disruption_factor)
                if port:
                    affected_ports.append(port)

        return affected_ports

    async def get_congestion_level(
        self,
        port_code: str,
        disruption_factor: float = 0.0,
    ) -> float:
        """
        Get congestion index for a port.

        Returns:
            Congestion index (0.0-1.0)
        """
        port = await self.get_port(port_code, disruption_factor)
        return port.congestion_index if port else 0.0

    # ========================================================================
    # INTERNAL METHODS
    # ========================================================================

    @retry_with_backoff(max_retries=3)
    async def _fetch_port_data(self, port_code: str) -> Optional[PortData]:
        """Fetch port data from real API."""
        async with self._circuit_breaker:
            try:
                response = await self._http_client.get(f"/ports/{port_code}")
                if response.status_code == 404:
                    return None
                response.raise_for_status()

                data = response.json()
                info = PORT_INFO.get(port_code, {})

                return PortData(
                    port_code=port_code,
                    port_name=data.get("name", info.get("name", port_code)),
                    country=data.get("country", info.get("country", "Unknown")),
                    region=data.get("region", info.get("region", "Unknown")),
                    status=PortStatus(data.get("status", "normal")),
                    average_wait_hours=data.get("wait_hours", 0),
                    vessels_at_anchor=data.get("anchored", 0),
                    vessels_at_berth=data.get("at_berth", 0),
                    berth_utilization_pct=data.get("utilization", 0.7),
                    avg_turnaround_hours=data.get("turnaround", 24),
                    congestion_index=data.get("congestion_index", 0.3),
                    associated_chokepoints=info.get("chokepoints", []),
                )
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    return None
                raise

    async def _mock_port_data(
        self,
        port_code: str,
        disruption_factor: float,
    ) -> Optional[PortData]:
        """Generate mock port data."""
        await asyncio.sleep(0.05)  # Simulate latency

        info = PORT_INFO.get(port_code)
        if not info:
            return None

        normal_wait = info.get("normal_wait", 6)
        normal_turnaround = info.get("normal_turnaround", 24)

        # Calculate disrupted values
        wait_multiplier = 1 + disruption_factor * 3  # Up to 4x wait time
        wait_hours = normal_wait * wait_multiplier * (1 + random.uniform(-0.1, 0.1))

        # Calculate congestion
        congestion_base = 0.3 + disruption_factor * 0.5
        congestion = min(1.0, congestion_base + random.uniform(-0.05, 0.1))

        # Determine status
        if congestion > 0.8:
            status = PortStatus.SEVERE_CONGESTION
        elif congestion > 0.6:
            status = PortStatus.CONGESTED
        elif disruption_factor > 0.9:
            status = PortStatus.RESTRICTED
        else:
            status = PortStatus.NORMAL

        # Vessel counts
        vessels_at_anchor = int(5 + disruption_factor * 30 + random.randint(0, 10))
        vessels_at_berth = int(10 + random.randint(0, 15))
        utilization = min(1.0, 0.65 + disruption_factor * 0.3 + random.uniform(0, 0.1))

        return PortData(
            port_code=port_code,
            port_name=info["name"],
            country=info["country"],
            region=info["region"],
            status=status,
            average_wait_hours=round(wait_hours, 1),
            vessels_at_anchor=vessels_at_anchor,
            vessels_at_berth=vessels_at_berth,
            berth_utilization_pct=round(utilization, 3),
            avg_turnaround_hours=round(normal_turnaround * (1 + disruption_factor * 0.5), 1),
            congestion_index=round(congestion, 3),
            associated_chokepoints=info.get("chokepoints", []),
        )


# ============================================================================
# FACTORY
# ============================================================================


_client_instance: Optional[PortDataClient] = None


def get_port_client() -> PortDataClient:
    """Get port data client singleton."""
    global _client_instance
    if _client_instance is None:
        _client_instance = PortDataClient()
    return _client_instance
