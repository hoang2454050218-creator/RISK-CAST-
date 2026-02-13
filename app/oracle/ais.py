"""
AIS (Automatic Identification System) Data Client.

Provides vessel tracking data from AIS feeds.
In production, this connects to AIS providers like:
- MarineTraffic
- VesselFinder
- AIS Hub
- FleetMon

For development, provides mock data with realistic patterns.
"""

from typing import Optional
from datetime import datetime, timedelta
from enum import Enum
import asyncio
import random

import httpx
import structlog

from app.common.resilience import retry_with_backoff, CircuitBreaker
from app.oracle.schemas import VesselMovement
from app.omen.schemas import Chokepoint
from app.core.config import settings

logger = structlog.get_logger(__name__)


# ============================================================================
# CONFIGURATION
# ============================================================================


class AISProvider(str, Enum):
    """Supported AIS data providers."""

    MARINE_TRAFFIC = "marine_traffic"
    VESSEL_FINDER = "vessel_finder"
    AIS_HUB = "ais_hub"
    MOCK = "mock"


class AISConfig:
    """AIS client configuration."""

    def __init__(
        self,
        provider: AISProvider = AISProvider.MOCK,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout_seconds: float = 30.0,
    ):
        self.provider = provider
        self.api_key = api_key or getattr(settings, 'ais_api_key', None)
        self.base_url = base_url
        self.timeout_seconds = timeout_seconds

        # Provider-specific URLs
        self.provider_urls = {
            AISProvider.MARINE_TRAFFIC: "https://services.marinetraffic.com/api",
            AISProvider.VESSEL_FINDER: "https://api.vesselfinder.com/vessels",
            AISProvider.AIS_HUB: "https://data.aishub.net/ws.php",
        }


# ============================================================================
# CHOKEPOINT COORDINATES
# ============================================================================

# Bounding boxes for major chokepoints
CHOKEPOINT_BOUNDS = {
    Chokepoint.RED_SEA: {
        "lat_min": 12.5,
        "lat_max": 15.5,
        "lon_min": 42.5,
        "lon_max": 44.5,
        "name": "Bab el-Mandeb / Red Sea Southern Approach",
    },
    Chokepoint.SUEZ: {
        "lat_min": 29.8,
        "lat_max": 31.5,
        "lon_min": 32.0,
        "lon_max": 33.0,
        "name": "Suez Canal",
    },
    Chokepoint.PANAMA: {
        "lat_min": 8.5,
        "lat_max": 9.5,
        "lon_min": -80.0,
        "lon_max": -79.0,
        "name": "Panama Canal",
    },
    Chokepoint.MALACCA: {
        "lat_min": 1.0,
        "lat_max": 2.5,
        "lon_min": 102.0,
        "lon_max": 104.5,
        "name": "Strait of Malacca",
    },
    Chokepoint.HORMUZ: {
        "lat_min": 26.0,
        "lat_max": 27.0,
        "lon_min": 55.5,
        "lon_max": 57.0,
        "name": "Strait of Hormuz",
    },
}

# Cape of Good Hope coordinates (for rerouting detection)
CAPE_ROUTE_BOUNDS = {
    "lat_min": -35.0,
    "lat_max": -33.0,
    "lon_min": 17.5,
    "lon_max": 20.5,
}


# ============================================================================
# AIS CLIENT
# ============================================================================


class AISClient:
    """
    Client for AIS vessel tracking data.

    Provides vessel positions, movements, and route changes.
    In development, returns realistic mock data.

    Usage:
        async with AISClient() as client:
            # Get vessels in chokepoint
            vessels = await client.get_vessels_in_chokepoint(Chokepoint.RED_SEA)

            # Check if vessels are rerouting
            rerouting = await client.get_rerouting_vessels()

            # Get specific vessel
            vessel = await client.get_vessel("9776171")  # IMO number
    """

    def __init__(self, config: Optional[AISConfig] = None):
        self.config = config or AISConfig()
        self._http_client: Optional[httpx.AsyncClient] = None
        self._circuit_breaker = CircuitBreaker(
            name="ais_api",
            failure_threshold=5,
            recovery_timeout=60.0,
        )

    async def __aenter__(self) -> "AISClient":
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()
        return False

    async def connect(self):
        """Initialize HTTP client."""
        if self._http_client is None:
            base_url = (
                self.config.base_url or
                self.config.provider_urls.get(self.config.provider, "")
            )

            headers = {"Accept": "application/json"}
            if self.config.api_key:
                headers["Authorization"] = f"Bearer {self.config.api_key}"

            self._http_client = httpx.AsyncClient(
                base_url=base_url,
                timeout=httpx.Timeout(self.config.timeout_seconds),
                headers=headers,
            )
            logger.info(
                "ais_client_connected",
                provider=self.config.provider.value,
            )

    async def disconnect(self):
        """Close HTTP client."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
            logger.info("ais_client_disconnected")

    # ========================================================================
    # VESSEL QUERIES
    # ========================================================================

    async def get_vessels_in_chokepoint(
        self,
        chokepoint: Chokepoint,
        vessel_types: Optional[list[str]] = None,
    ) -> list[VesselMovement]:
        """
        Get vessels currently in a chokepoint area.

        Args:
            chokepoint: The chokepoint to query
            vessel_types: Filter by vessel types (e.g., ["container", "tanker"])

        Returns:
            List of VesselMovement objects
        """
        if self.config.provider == AISProvider.MOCK:
            return await self._mock_vessels_in_chokepoint(chokepoint)

        bounds = CHOKEPOINT_BOUNDS.get(chokepoint)
        if not bounds:
            return []

        return await self._query_vessels_in_area(
            lat_min=bounds["lat_min"],
            lat_max=bounds["lat_max"],
            lon_min=bounds["lon_min"],
            lon_max=bounds["lon_max"],
            vessel_types=vessel_types,
        )

    async def get_rerouting_vessels(
        self,
        original_chokepoint: Optional[Chokepoint] = None,
    ) -> list[VesselMovement]:
        """
        Get vessels that appear to be rerouting.

        Detects rerouting by:
        1. Vessels on Asia-Europe route but heading toward Cape
        2. Vessels with route changes in AIS data
        3. Vessels waiting unusually long at staging areas

        Args:
            original_chokepoint: Filter by original intended chokepoint

        Returns:
            List of rerouting vessels
        """
        if self.config.provider == AISProvider.MOCK:
            return await self._mock_rerouting_vessels(original_chokepoint)

        # Query vessels in Cape of Good Hope area
        cape_vessels = await self._query_vessels_in_area(
            lat_min=CAPE_ROUTE_BOUNDS["lat_min"],
            lat_max=CAPE_ROUTE_BOUNDS["lat_max"],
            lon_min=CAPE_ROUTE_BOUNDS["lon_min"],
            lon_max=CAPE_ROUTE_BOUNDS["lon_max"],
        )

        # Filter for those likely rerouting (container ships on atypical route)
        rerouting = []
        for vessel in cape_vessels:
            # Container ships heading to Europe via Cape = likely rerouting
            if vessel.vessel_type.lower() == "container":
                dest = vessel.destination_port or ""
                if any(p in dest.upper() for p in ["RTM", "HAM", "ANT", "FEL"]):
                    vessel.is_rerouting = True
                    vessel.original_route = "Via Suez Canal"
                    rerouting.append(vessel)

        return rerouting

    async def get_vessel(self, imo: str) -> Optional[VesselMovement]:
        """
        Get vessel by IMO number.

        Args:
            imo: IMO number (7 digits)

        Returns:
            VesselMovement or None
        """
        if self.config.provider == AISProvider.MOCK:
            return await self._mock_single_vessel(imo)

        async with self._circuit_breaker:
            try:
                response = await self._http_client.get(
                    f"/vessels/{imo}"
                )
                response.raise_for_status()
                data = response.json()
                return self._parse_vessel(data)
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    return None
                raise

    async def get_vessels_waiting(
        self,
        chokepoint: Chokepoint,
        min_wait_hours: float = 24.0,
    ) -> list[VesselMovement]:
        """
        Get vessels waiting/anchored near a chokepoint.

        Args:
            chokepoint: The chokepoint
            min_wait_hours: Minimum hours stationary to count as waiting

        Returns:
            List of waiting vessels
        """
        if self.config.provider == AISProvider.MOCK:
            return await self._mock_waiting_vessels(chokepoint)

        # Get vessels with very low speed near chokepoint
        vessels = await self.get_vessels_in_chokepoint(chokepoint)
        return [v for v in vessels if v.speed_knots < 0.5]

    # ========================================================================
    # INTERNAL METHODS
    # ========================================================================

    @retry_with_backoff(max_retries=3)
    async def _query_vessels_in_area(
        self,
        lat_min: float,
        lat_max: float,
        lon_min: float,
        lon_max: float,
        vessel_types: Optional[list[str]] = None,
    ) -> list[VesselMovement]:
        """Query vessels in a geographic area."""
        async with self._circuit_breaker:
            params = {
                "latmin": lat_min,
                "latmax": lat_max,
                "lonmin": lon_min,
                "lonmax": lon_max,
            }
            if vessel_types:
                params["vessel_type"] = ",".join(vessel_types)

            response = await self._http_client.get("/area", params=params)
            response.raise_for_status()

            data = response.json()
            vessels = []

            for item in data.get("vessels", []):
                try:
                    vessels.append(self._parse_vessel(item))
                except Exception as e:
                    logger.warning("vessel_parse_error", error=str(e))

            return vessels

    def _parse_vessel(self, data: dict) -> VesselMovement:
        """Parse vessel data from API response."""
        return VesselMovement(
            imo=data.get("imo", data.get("mmsi", "unknown")),
            vessel_name=data.get("name", "Unknown Vessel"),
            vessel_type=data.get("type", data.get("ship_type", "cargo")),
            flag=data.get("flag", "unknown"),
            latitude=float(data.get("lat", data.get("latitude", 0))),
            longitude=float(data.get("lon", data.get("longitude", 0))),
            heading=float(data.get("heading", data.get("course", 0))),
            speed_knots=float(data.get("speed", data.get("sog", 0))),
            origin_port=data.get("origin", data.get("departure_port")),
            destination_port=data.get("destination", data.get("destination_port")),
            eta=self._parse_datetime(data.get("eta")),
            is_rerouting=data.get("is_rerouting", False),
            original_route=data.get("original_route"),
            timestamp=self._parse_datetime(data.get("timestamp")) or datetime.utcnow(),
        )

    def _parse_datetime(self, value) -> Optional[datetime]:
        """Parse datetime from various formats."""
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                return None
        return None

    # ========================================================================
    # MOCK DATA (Development)
    # ========================================================================

    async def _mock_vessels_in_chokepoint(
        self,
        chokepoint: Chokepoint,
    ) -> list[VesselMovement]:
        """Generate mock vessel data for a chokepoint."""
        await asyncio.sleep(0.1)  # Simulate API latency

        bounds = CHOKEPOINT_BOUNDS.get(chokepoint)
        if not bounds:
            return []

        # Generate realistic vessel count based on chokepoint
        vessel_counts = {
            Chokepoint.RED_SEA: (15, 40),
            Chokepoint.SUEZ: (20, 50),
            Chokepoint.PANAMA: (10, 30),
            Chokepoint.MALACCA: (30, 70),
            Chokepoint.HORMUZ: (15, 35),
        }
        min_count, max_count = vessel_counts.get(chokepoint, (10, 30))
        count = random.randint(min_count, max_count)

        vessels = []
        for i in range(count):
            vessel = VesselMovement(
                imo=f"97{random.randint(10000, 99999)}",
                vessel_name=self._random_vessel_name(),
                vessel_type=random.choice(["container", "tanker", "bulk carrier"]),
                flag=random.choice(["PA", "LR", "MH", "MT", "SG", "HK"]),
                latitude=random.uniform(bounds["lat_min"], bounds["lat_max"]),
                longitude=random.uniform(bounds["lon_min"], bounds["lon_max"]),
                heading=random.uniform(0, 360),
                speed_knots=random.uniform(0, 18),
                destination_port=random.choice(["NLRTM", "DEHAM", "CNSHA", "SGSIN"]),
                timestamp=datetime.utcnow(),
            )
            vessels.append(vessel)

        return vessels

    async def _mock_rerouting_vessels(
        self,
        original_chokepoint: Optional[Chokepoint],
    ) -> list[VesselMovement]:
        """Generate mock rerouting vessel data."""
        await asyncio.sleep(0.1)

        # Simulate some vessels rerouting around Cape
        count = random.randint(5, 20)
        vessels = []

        for i in range(count):
            vessel = VesselMovement(
                imo=f"97{random.randint(10000, 99999)}",
                vessel_name=self._random_vessel_name(),
                vessel_type="container",
                flag=random.choice(["PA", "LR", "MH"]),
                latitude=random.uniform(-35.0, -33.0),  # Cape area
                longitude=random.uniform(17.5, 20.5),
                heading=random.uniform(270, 360),  # Heading west/north
                speed_knots=random.uniform(12, 18),
                origin_port=random.choice(["CNSHA", "CNNGB", "VNHCM"]),
                destination_port=random.choice(["NLRTM", "DEHAM"]),
                is_rerouting=True,
                original_route="Via Suez Canal",
                timestamp=datetime.utcnow(),
            )
            vessels.append(vessel)

        return vessels

    async def _mock_waiting_vessels(
        self,
        chokepoint: Chokepoint,
    ) -> list[VesselMovement]:
        """Generate mock waiting vessel data."""
        await asyncio.sleep(0.1)

        bounds = CHOKEPOINT_BOUNDS.get(chokepoint)
        if not bounds:
            return []

        # Fewer waiting vessels
        count = random.randint(2, 10)
        vessels = []

        for i in range(count):
            vessel = VesselMovement(
                imo=f"97{random.randint(10000, 99999)}",
                vessel_name=self._random_vessel_name(),
                vessel_type="container",
                flag=random.choice(["PA", "LR"]),
                latitude=random.uniform(bounds["lat_min"], bounds["lat_max"]),
                longitude=random.uniform(bounds["lon_min"], bounds["lon_max"]),
                heading=random.uniform(0, 360),
                speed_knots=0.0,  # Stationary
                destination_port=random.choice(["NLRTM", "DEHAM"]),
                timestamp=datetime.utcnow(),
            )
            vessels.append(vessel)

        return vessels

    async def _mock_single_vessel(self, imo: str) -> Optional[VesselMovement]:
        """Generate mock single vessel data."""
        await asyncio.sleep(0.05)

        return VesselMovement(
            imo=imo,
            vessel_name=self._random_vessel_name(),
            vessel_type="container",
            flag="PA",
            latitude=random.uniform(-10, 40),
            longitude=random.uniform(30, 120),
            heading=random.uniform(0, 360),
            speed_knots=random.uniform(10, 18),
            destination_port="NLRTM",
            timestamp=datetime.utcnow(),
        )

    def _random_vessel_name(self) -> str:
        """Generate a random vessel name."""
        prefixes = ["MSC", "CMA CGM", "COSCO", "Maersk", "Ever", "ONE"]
        names = ["Harmony", "Fortune", "Excellence", "Pride", "Spirit", "Victory"]
        return f"{random.choice(prefixes)} {random.choice(names)}"


# ============================================================================
# FACTORY
# ============================================================================


_client_instance: Optional[AISClient] = None


def get_ais_client() -> AISClient:
    """Get AIS client singleton."""
    global _client_instance
    if _client_instance is None:
        _client_instance = AISClient()
    return _client_instance
