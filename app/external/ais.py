"""
AIS (Automatic Identification System) API Client.

Production-grade client for vessel tracking with:
- Real-time vessel positions
- Port calls and ETA
- Route tracking
- Chokepoint monitoring
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import asyncio

import httpx
from pydantic import BaseModel, Field
import structlog

from app.core.config import settings
from app.core.resilience import (
    CircuitBreakerRegistry,
    ResilientCall,
    RetryConfig,
)
from app.core.metrics import RECORDER
from app.core.rate_limiting import rate_limit_context

logger = structlog.get_logger(__name__)


# ============================================================================
# CONFIGURATION
# ============================================================================


@dataclass
class AISConfig:
    """AIS API configuration."""
    
    # Using Marine Traffic API as example
    base_url: str = "https://services.marinetraffic.com/api"
    api_key: Optional[str] = None
    timeout_seconds: float = 30.0
    max_retries: int = 3
    cache_ttl_seconds: int = 60  # 1 minute for real-time data
    rate_limit_per_minute: int = 60


# ============================================================================
# MODELS
# ============================================================================


class VesselType(str, Enum):
    """Vessel types."""
    
    CONTAINER = "container"
    TANKER = "tanker"
    BULK_CARRIER = "bulk_carrier"
    CARGO = "cargo"
    PASSENGER = "passenger"
    OTHER = "other"


class NavigationStatus(str, Enum):
    """AIS navigation status."""
    
    UNDERWAY_ENGINE = "underway_engine"
    AT_ANCHOR = "at_anchor"
    NOT_UNDER_COMMAND = "not_under_command"
    RESTRICTED_MANEUVERABILITY = "restricted_maneuverability"
    MOORED = "moored"
    AGROUND = "aground"
    FISHING = "fishing"
    UNDERWAY_SAILING = "underway_sailing"
    UNKNOWN = "unknown"


class Position(BaseModel):
    """Vessel position."""
    
    latitude: float
    longitude: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    course: Optional[float] = None  # Degrees
    speed: Optional[float] = None  # Knots
    heading: Optional[float] = None  # Degrees


class Vessel(BaseModel):
    """Vessel information."""
    
    mmsi: str  # Maritime Mobile Service Identity
    imo: Optional[str] = None  # IMO number
    name: str
    vessel_type: VesselType = VesselType.OTHER
    flag: Optional[str] = None
    
    # Dimensions
    length: Optional[float] = None
    width: Optional[float] = None
    draught: Optional[float] = None
    
    # Current status
    position: Optional[Position] = None
    navigation_status: NavigationStatus = NavigationStatus.UNKNOWN
    destination: Optional[str] = None
    eta: Optional[datetime] = None
    
    # Metadata
    last_update: Optional[datetime] = None


class PortCall(BaseModel):
    """Vessel port call."""
    
    port_id: str
    port_name: str
    country: str
    arrival: Optional[datetime] = None
    departure: Optional[datetime] = None
    status: str = "unknown"


class Chokepoint(str, Enum):
    """Major maritime chokepoints."""
    
    RED_SEA = "red_sea"
    SUEZ_CANAL = "suez_canal"
    BAB_EL_MANDEB = "bab_el_mandeb"
    STRAIT_OF_HORMUZ = "strait_of_hormuz"
    MALACCA_STRAIT = "malacca_strait"
    PANAMA_CANAL = "panama_canal"
    GIBRALTAR = "gibraltar"
    DOVER = "dover"


# Chokepoint bounding boxes (approximate)
CHOKEPOINT_BOUNDS = {
    Chokepoint.RED_SEA: {
        "min_lat": 12.5,
        "max_lat": 30.0,
        "min_lon": 32.5,
        "max_lon": 44.0,
    },
    Chokepoint.SUEZ_CANAL: {
        "min_lat": 29.8,
        "max_lat": 31.3,
        "min_lon": 32.2,
        "max_lon": 32.6,
    },
    Chokepoint.BAB_EL_MANDEB: {
        "min_lat": 12.0,
        "max_lat": 13.0,
        "min_lon": 43.0,
        "max_lon": 44.0,
    },
    Chokepoint.STRAIT_OF_HORMUZ: {
        "min_lat": 25.5,
        "max_lat": 27.0,
        "min_lon": 55.5,
        "max_lon": 57.0,
    },
    Chokepoint.MALACCA_STRAIT: {
        "min_lat": 0.5,
        "max_lat": 4.0,
        "min_lon": 99.0,
        "max_lon": 104.0,
    },
    Chokepoint.PANAMA_CANAL: {
        "min_lat": 8.8,
        "max_lat": 9.4,
        "min_lon": -79.9,
        "max_lon": -79.4,
    },
}


class ChokepointTraffic(BaseModel):
    """Traffic at a chokepoint."""
    
    chokepoint: Chokepoint
    vessel_count: int
    container_ships: int = 0
    tankers: int = 0
    other: int = 0
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    average_wait_hours: Optional[float] = None
    vessels: List[Vessel] = Field(default_factory=list)


# ============================================================================
# CLIENT
# ============================================================================


class AISClient:
    """
    Async client for AIS vessel tracking.
    
    Features:
    - Circuit breaker for fault tolerance
    - Automatic retries
    - Response caching
    - Chokepoint monitoring
    """
    
    def __init__(
        self,
        config: Optional[AISConfig] = None,
    ):
        self.config = config or AISConfig()
        self._client: Optional[httpx.AsyncClient] = None
        self._cache: Dict[str, tuple[Any, datetime]] = {}
        self._circuit_breaker = CircuitBreakerRegistry.get_or_create("ais")
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.config.base_url,
                timeout=self.config.timeout_seconds,
                headers={
                    "Accept": "application/json",
                    "User-Agent": "RISKCAST/1.0",
                },
            )
        return self._client
    
    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
    
    def _get_cached(self, key: str) -> Optional[Any]:
        """Get cached value if not expired."""
        if key in self._cache:
            value, cached_at = self._cache[key]
            if datetime.utcnow() - cached_at < timedelta(seconds=self.config.cache_ttl_seconds):
                return value
            del self._cache[key]
        return None
    
    def _set_cached(self, key: str, value: Any) -> None:
        """Set cached value."""
        self._cache[key] = (value, datetime.utcnow())
    
    async def _request(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        """Make an API request with resilience patterns."""
        cache_key = f"{endpoint}:{params}"
        
        # Check cache
        if use_cache:
            cached = self._get_cached(cache_key)
            if cached is not None:
                logger.debug("ais_cache_hit", endpoint=endpoint)
                return cached
        
        async def do_request() -> Dict[str, Any]:
            client = await self._get_client()
            
            # Add API key to params
            request_params = params or {}
            if self.config.api_key:
                request_params["apikey"] = self.config.api_key
            
            start = datetime.utcnow()
            response = await client.get(endpoint, params=request_params)
            response.raise_for_status()
            
            # Record metrics
            latency = (datetime.utcnow() - start).total_seconds()
            RECORDER.record_api_call(
                service="ais",
                endpoint=endpoint,
                status=str(response.status_code),
                latency_seconds=latency,
            )
            
            return response.json()
        
        # Apply rate limiting
        async with rate_limit_context(
            f"ais:api",
            limit=self.config.rate_limit_per_minute,
            window_seconds=60,
        ):
            # Execute with resilience
            result = await (
                ResilientCall(do_request)
                .with_circuit_breaker(self._circuit_breaker)
                .with_retry(RetryConfig(
                    max_attempts=self.config.max_retries,
                    retryable_exceptions=(httpx.HTTPError, httpx.TimeoutException),
                ))
                .with_timeout(self.config.timeout_seconds)
                .execute()
            )
        
        # Cache successful responses
        if use_cache:
            self._set_cached(cache_key, result)
        
        return result
    
    # ========================================================================
    # PUBLIC METHODS
    # ========================================================================
    
    async def get_vessel(self, mmsi: str) -> Optional[Vessel]:
        """
        Get vessel information by MMSI.
        
        Args:
            mmsi: Maritime Mobile Service Identity
        
        Returns:
            Vessel if found, None otherwise
        """
        try:
            data = await self._request(f"/exportvessel/v:5/{mmsi}")
            if not data:
                return None
            return self._parse_vessel(data[0] if isinstance(data, list) else data)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise
    
    async def search_vessels(
        self,
        name: Optional[str] = None,
        imo: Optional[str] = None,
        vessel_type: Optional[VesselType] = None,
        flag: Optional[str] = None,
    ) -> List[Vessel]:
        """
        Search for vessels by criteria.
        
        Args:
            name: Vessel name (partial match)
            imo: IMO number
            vessel_type: Type of vessel
            flag: Flag state
        
        Returns:
            List of matching vessels
        """
        params = {}
        if name:
            params["name"] = name
        if imo:
            params["imo"] = imo
        if vessel_type:
            params["type"] = vessel_type.value
        if flag:
            params["flag"] = flag
        
        data = await self._request("/exportvessels/v:8", params=params)
        return [self._parse_vessel(v) for v in data.get("DATA", [])]
    
    async def get_vessels_in_area(
        self,
        min_lat: float,
        max_lat: float,
        min_lon: float,
        max_lon: float,
    ) -> List[Vessel]:
        """
        Get vessels in a geographic bounding box.
        
        Args:
            min_lat: Minimum latitude
            max_lat: Maximum latitude
            min_lon: Minimum longitude
            max_lon: Maximum longitude
        
        Returns:
            List of vessels in the area
        """
        params = {
            "MINLAT": min_lat,
            "MAXLAT": max_lat,
            "MINLON": min_lon,
            "MAXLON": max_lon,
        }
        
        data = await self._request("/exportvessels/v:8", params=params)
        return [self._parse_vessel(v) for v in data.get("DATA", [])]
    
    async def get_chokepoint_traffic(
        self,
        chokepoint: Chokepoint,
    ) -> ChokepointTraffic:
        """
        Get current vessel traffic at a chokepoint.
        
        Args:
            chokepoint: The chokepoint to check
        
        Returns:
            Traffic information at the chokepoint
        """
        bounds = CHOKEPOINT_BOUNDS.get(chokepoint)
        if not bounds:
            raise ValueError(f"Unknown chokepoint: {chokepoint}")
        
        vessels = await self.get_vessels_in_area(**bounds)
        
        # Count by type
        container_ships = sum(1 for v in vessels if v.vessel_type == VesselType.CONTAINER)
        tankers = sum(1 for v in vessels if v.vessel_type == VesselType.TANKER)
        other = len(vessels) - container_ships - tankers
        
        traffic = ChokepointTraffic(
            chokepoint=chokepoint,
            vessel_count=len(vessels),
            container_ships=container_ships,
            tankers=tankers,
            other=other,
            vessels=vessels[:50],  # Limit returned vessels
        )
        
        logger.info(
            "ais_chokepoint_traffic",
            chokepoint=chokepoint.value,
            vessel_count=traffic.vessel_count,
        )
        
        return traffic
    
    async def get_vessel_route(
        self,
        mmsi: str,
        days_back: int = 7,
    ) -> List[Position]:
        """
        Get historical route for a vessel.
        
        Args:
            mmsi: Vessel MMSI
            days_back: Number of days of history
        
        Returns:
            List of historical positions
        """
        from_date = datetime.utcnow() - timedelta(days=days_back)
        
        params = {
            "mmsi": mmsi,
            "fromdate": from_date.strftime("%Y-%m-%d"),
            "todate": datetime.utcnow().strftime("%Y-%m-%d"),
        }
        
        data = await self._request("/exportroute/v:2", params=params)
        
        positions = []
        for point in data.get("DATA", []):
            positions.append(Position(
                latitude=float(point.get("LAT", 0)),
                longitude=float(point.get("LON", 0)),
                timestamp=self._parse_datetime(point.get("TIMESTAMP")),
                course=float(point.get("COURSE")) if point.get("COURSE") else None,
                speed=float(point.get("SPEED")) if point.get("SPEED") else None,
            ))
        
        return positions
    
    async def get_port_calls(
        self,
        mmsi: str,
        limit: int = 10,
    ) -> List[PortCall]:
        """
        Get port call history for a vessel.
        
        Args:
            mmsi: Vessel MMSI
            limit: Maximum port calls to return
        
        Returns:
            List of port calls
        """
        params = {
            "mmsi": mmsi,
            "limit": limit,
        }
        
        data = await self._request("/portcalls/v:3", params=params)
        
        calls = []
        for call in data.get("DATA", []):
            calls.append(PortCall(
                port_id=call.get("PORT_ID", ""),
                port_name=call.get("PORT_NAME", ""),
                country=call.get("COUNTRY", ""),
                arrival=self._parse_datetime(call.get("ARRIVAL")),
                departure=self._parse_datetime(call.get("DEPARTURE")),
                status=call.get("STATUS", "unknown"),
            ))
        
        return calls
    
    async def is_vessel_at_chokepoint(
        self,
        mmsi: str,
        chokepoint: Chokepoint,
    ) -> bool:
        """
        Check if a vessel is currently at a chokepoint.
        
        Args:
            mmsi: Vessel MMSI
            chokepoint: Chokepoint to check
        
        Returns:
            True if vessel is at the chokepoint
        """
        vessel = await self.get_vessel(mmsi)
        if not vessel or not vessel.position:
            return False
        
        bounds = CHOKEPOINT_BOUNDS.get(chokepoint)
        if not bounds:
            return False
        
        lat = vessel.position.latitude
        lon = vessel.position.longitude
        
        return (
            bounds["min_lat"] <= lat <= bounds["max_lat"] and
            bounds["min_lon"] <= lon <= bounds["max_lon"]
        )
    
    def _parse_vessel(self, data: Dict[str, Any]) -> Vessel:
        """Parse vessel data from API response."""
        position = None
        if data.get("LAT") and data.get("LON"):
            position = Position(
                latitude=float(data["LAT"]),
                longitude=float(data["LON"]),
                course=float(data.get("COURSE", 0)) or None,
                speed=float(data.get("SPEED", 0)) or None,
                heading=float(data.get("HEADING", 0)) or None,
                timestamp=self._parse_datetime(data.get("TIMESTAMP")),
            )
        
        return Vessel(
            mmsi=str(data.get("MMSI", "")),
            imo=str(data.get("IMO")) if data.get("IMO") else None,
            name=data.get("SHIPNAME", data.get("NAME", "Unknown")),
            vessel_type=self._parse_vessel_type(data.get("SHIP_TYPE", data.get("TYPE"))),
            flag=data.get("FLAG"),
            length=float(data.get("LENGTH")) if data.get("LENGTH") else None,
            width=float(data.get("WIDTH")) if data.get("WIDTH") else None,
            draught=float(data.get("DRAUGHT")) if data.get("DRAUGHT") else None,
            position=position,
            navigation_status=NavigationStatus.UNKNOWN,
            destination=data.get("DESTINATION"),
            eta=self._parse_datetime(data.get("ETA")),
            last_update=self._parse_datetime(data.get("TIMESTAMP")),
        )
    
    def _parse_vessel_type(self, type_code: Any) -> VesselType:
        """Parse vessel type from API code."""
        if not type_code:
            return VesselType.OTHER
        
        type_str = str(type_code).lower()
        if "container" in type_str:
            return VesselType.CONTAINER
        elif "tanker" in type_str:
            return VesselType.TANKER
        elif "bulk" in type_str:
            return VesselType.BULK_CARRIER
        elif "cargo" in type_str:
            return VesselType.CARGO
        elif "passenger" in type_str:
            return VesselType.PASSENGER
        
        return VesselType.OTHER
    
    def _parse_datetime(self, value: Any) -> Optional[datetime]:
        """Parse datetime from API response."""
        if not value:
            return None
        try:
            if isinstance(value, str):
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            return datetime.utcfromtimestamp(int(value))
        except (ValueError, TypeError):
            return None


# ============================================================================
# FACTORY
# ============================================================================

_client: Optional[AISClient] = None


def get_ais_client() -> AISClient:
    """Get the global AIS client instance."""
    global _client
    if _client is None:
        _client = AISClient()
    return _client


async def close_ais_client() -> None:
    """Close the global AIS client."""
    global _client
    if _client:
        await _client.close()
        _client = None
