"""
OMEN API Client for RISKCAST.

This client connects to the OMEN Signal Intelligence service
to fetch predictive signals about supply chain disruptions.

Responsibilities:
- Fetch signals from OMEN REST API
- Subscribe to real-time updates via WebSocket
- Convert OMEN responses to internal OmenSignal schema
- Handle connection failures with retry + circuit breaker

OMEN API is a separate service - this is the client that consumes it.
"""

from typing import AsyncGenerator, Optional, Any
from datetime import datetime
import asyncio
import json

import httpx
import structlog
from pydantic import BaseModel, Field

from app.omen.schemas import (
    OmenSignal,
    SignalCategory,
    Chokepoint,
    EvidenceItem,
    GeographicScope,
    TemporalScope,
)
from app.common.resilience import (
    retry_with_backoff,
    CircuitBreaker,
    CircuitOpenError,
    with_timeout,
)
from app.core.config import settings

logger = structlog.get_logger(__name__)


# ============================================================================
# CONFIGURATION
# ============================================================================


class OmenClientConfig(BaseModel):
    """Configuration for OMEN client."""

    base_url: str = Field(
        default="http://localhost:8000",
        description="OMEN service base URL",
    )
    api_key: str = Field(
        default="dev-test-key",
        description="API key for OMEN authentication",
    )
    timeout_seconds: float = Field(
        default=30.0,
        description="HTTP request timeout",
    )
    max_retries: int = Field(
        default=3,
        description="Maximum retry attempts",
    )
    ws_url: Optional[str] = Field(
        default=None,
        description="WebSocket URL (derived from base_url if not set)",
    )
    ws_reconnect_delay: float = Field(
        default=5.0,
        description="Delay between WebSocket reconnection attempts",
    )
    ws_max_reconnect_attempts: int = Field(
        default=10,
        description="Maximum WebSocket reconnection attempts",
    )

    @property
    def websocket_url(self) -> str:
        """Get WebSocket URL."""
        if self.ws_url:
            return self.ws_url
        # Convert http(s) to ws(s)
        return self.base_url.replace("http://", "ws://").replace("https://", "wss://") + "/ws"


# ============================================================================
# RESPONSE MODELS
# ============================================================================


class OmenAPIMeta(BaseModel):
    """Metadata from OMEN API responses."""

    mode: str = "UNKNOWN"
    real_source_coverage: float = 0.0
    live_gate_status: str = "UNKNOWN"
    real_sources: list[str] = Field(default_factory=list)
    mock_sources: list[str] = Field(default_factory=list)
    timestamp: Optional[datetime] = None


class OmenAPIResponse(BaseModel):
    """Wrapper for OMEN API responses."""

    data: Any
    meta: OmenAPIMeta = Field(default_factory=OmenAPIMeta)


# ============================================================================
# OMEN CLIENT
# ============================================================================


class OmenClient:
    """
    Client for OMEN Signal Intelligence API.

    This is the primary interface for RISKCAST to get signals from OMEN.

    Usage:
        async with OmenClient() as client:
            # Get all active signals
            signals = await client.get_signals()

            # Get single signal
            signal = await client.get_signal("OMEN-RS2024-001")

            # Subscribe to real-time updates
            async for signal in client.subscribe():
                await process_signal(signal)

    Error Handling:
        - Automatic retries with exponential backoff
        - Circuit breaker prevents hammering failed service
        - Falls back gracefully when OMEN is unavailable
    """

    def __init__(self, config: Optional[OmenClientConfig] = None):
        """
        Initialize OMEN client.

        Args:
            config: Client configuration (uses defaults if not provided)
        """
        self.config = config or OmenClientConfig(
            base_url=getattr(settings, 'omen_api_url', 'http://localhost:8000'),
            api_key=getattr(settings, 'omen_api_key', 'dev-test-key'),
        )
        self._http_client: Optional[httpx.AsyncClient] = None
        self._circuit_breaker = CircuitBreaker(
            name="omen_api",
            failure_threshold=5,
            recovery_timeout=60.0,
        )
        self._ws_task: Optional[asyncio.Task] = None
        self._ws_running = False

    async def __aenter__(self) -> "OmenClient":
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()
        return False

    async def connect(self):
        """Initialize HTTP client."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                base_url=self.config.base_url,
                timeout=httpx.Timeout(self.config.timeout_seconds),
                headers={
                    "User-Agent": "RISKCAST/2.0",
                    "Accept": "application/json",
                    "X-API-Key": self.config.api_key,
                },
            )
            logger.info(
                "omen_client_connected",
                base_url=self.config.base_url,
            )

    async def disconnect(self):
        """Close HTTP client and WebSocket."""
        self._ws_running = False

        if self._ws_task and not self._ws_task.done():
            self._ws_task.cancel()
            try:
                await self._ws_task
            except asyncio.CancelledError:
                pass

        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
            logger.info("omen_client_disconnected")

    # ========================================================================
    # REST API METHODS
    # ========================================================================

    @retry_with_backoff(max_retries=3, base_delay=1.0)
    @with_timeout(30.0)
    async def get_signals(
        self,
        category: Optional[str] = None,
        status: str = "ACTIVE",
        chokepoint: Optional[str] = None,
        min_probability: float = 0.0,
        limit: int = 100,
    ) -> list[OmenSignal]:
        """
        Fetch signals from OMEN API.

        Args:
            category: Filter by signal category
            status: Filter by status (default: ACTIVE)
            chokepoint: Filter by chokepoint
            min_probability: Minimum probability threshold
            limit: Maximum number of signals to return

        Returns:
            List of OmenSignal objects

        Raises:
            CircuitOpenError: If circuit breaker is open
            httpx.HTTPError: On HTTP errors
        """
        await self._ensure_connected()

        async with self._circuit_breaker:
            # Build query parameters
            params = {
                "status": status,
                "limit": limit,
            }
            if category:
                params["category"] = category
            if chokepoint:
                params["chokepoint"] = chokepoint

            logger.debug(
                "fetching_signals",
                params=params,
            )

            response = await self._http_client.get(
                "/api/v1/signals/",
                params=params,
            )
            response.raise_for_status()

            data = response.json()
            api_response = self._parse_response(data)

            # Check data quality
            if not self._check_data_quality(api_response.meta):
                logger.warning(
                    "low_quality_data",
                    mode=api_response.meta.mode,
                    real_coverage=api_response.meta.real_source_coverage,
                )

            # Parse signals
            signals = []
            signal_data = api_response.data if isinstance(api_response.data, list) else [api_response.data]

            for item in signal_data:
                try:
                    signal = self._parse_signal(item)
                    if signal.probability >= min_probability:
                        signals.append(signal)
                except Exception as e:
                    logger.warning(
                        "signal_parse_error",
                        error=str(e),
                        signal_data=str(item)[:200],
                    )

            logger.info(
                "signals_fetched",
                count=len(signals),
                mode=api_response.meta.mode,
            )

            return signals

    @retry_with_backoff(max_retries=3)
    async def get_signal(self, signal_id: str) -> Optional[OmenSignal]:
        """
        Fetch single signal by ID.

        Args:
            signal_id: The signal ID to fetch

        Returns:
            OmenSignal or None if not found
        """
        await self._ensure_connected()

        async with self._circuit_breaker:
            try:
                response = await self._http_client.get(
                    f"/api/v1/signals/{signal_id}"
                )

                if response.status_code == 404:
                    return None

                response.raise_for_status()
                data = response.json()
                api_response = self._parse_response(data)

                return self._parse_signal(api_response.data)

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    return None
                raise

    async def refresh_signals(self) -> list[OmenSignal]:
        """
        Trigger OMEN to refresh from live sources.

        This is useful when you want fresh data rather than cached.

        Returns:
            List of refreshed signals
        """
        await self._ensure_connected()

        async with self._circuit_breaker:
            response = await self._http_client.post(
                "/api/v1/signals/refresh"
            )
            response.raise_for_status()

            data = response.json()
            api_response = self._parse_response(data)

            signals = []
            signal_data = api_response.data if isinstance(api_response.data, list) else [api_response.data]

            for item in signal_data:
                try:
                    signals.append(self._parse_signal(item))
                except Exception as e:
                    logger.warning("signal_parse_error", error=str(e))

            logger.info(
                "signals_refreshed",
                count=len(signals),
            )

            return signals

    async def get_multi_source_signals(self) -> list[OmenSignal]:
        """
        Get signals aggregated from all sources.

        Returns:
            List of signals from all sources
        """
        await self._ensure_connected()

        async with self._circuit_breaker:
            response = await self._http_client.get(
                "/api/v1/multi-source/signals"
            )
            response.raise_for_status()

            data = response.json()
            api_response = self._parse_response(data)

            signals = []
            signal_data = api_response.data if isinstance(api_response.data, list) else []

            for item in signal_data:
                try:
                    signals.append(self._parse_signal(item))
                except Exception:
                    pass

            return signals

    # ========================================================================
    # WEBSOCKET METHODS
    # ========================================================================

    async def subscribe(
        self,
        on_signal: Optional[callable] = None,
    ) -> AsyncGenerator[OmenSignal, None]:
        """
        Subscribe to real-time signal updates via WebSocket.

        Yields OmenSignal objects as they arrive from OMEN.
        Auto-reconnects on connection failure.

        Args:
            on_signal: Optional callback for each signal

        Yields:
            OmenSignal objects

        Usage:
            async for signal in client.subscribe():
                await process_signal(signal)
        """
        try:
            import websockets
        except ImportError:
            logger.error("websockets_not_installed")
            raise ImportError("websockets package required for subscription")

        self._ws_running = True
        reconnect_attempts = 0
        ws_url = self.config.websocket_url

        while self._ws_running and reconnect_attempts < self.config.ws_max_reconnect_attempts:
            try:
                async with websockets.connect(ws_url) as websocket:
                    logger.info(
                        "websocket_connected",
                        url=ws_url,
                    )
                    reconnect_attempts = 0  # Reset on successful connection

                    async for message in websocket:
                        try:
                            data = json.loads(message)
                            event_type = data.get("type", "unknown")

                            if event_type == "signal_emitted":
                                signal_data = data.get("data", {})
                                signal = self._parse_signal(signal_data)

                                if on_signal:
                                    await on_signal(signal)

                                yield signal

                            elif event_type == "signal_ingested":
                                # New signal added to OMEN
                                logger.debug(
                                    "signal_ingested",
                                    signal_id=data.get("signal_id"),
                                )

                        except json.JSONDecodeError:
                            logger.warning("invalid_ws_message", message=message[:100])
                        except Exception as e:
                            logger.warning("ws_message_error", error=str(e))

            except Exception as e:
                reconnect_attempts += 1
                logger.warning(
                    "websocket_disconnected",
                    error=str(e),
                    attempt=reconnect_attempts,
                    max_attempts=self.config.ws_max_reconnect_attempts,
                )

                if self._ws_running and reconnect_attempts < self.config.ws_max_reconnect_attempts:
                    await asyncio.sleep(self.config.ws_reconnect_delay)

        logger.info("websocket_subscription_ended")

    def stop_subscription(self):
        """Stop WebSocket subscription."""
        self._ws_running = False

    # ========================================================================
    # HELPER METHODS
    # ========================================================================

    async def _ensure_connected(self):
        """Ensure HTTP client is connected."""
        if self._http_client is None:
            await self.connect()

    def _parse_response(self, data: dict) -> OmenAPIResponse:
        """
        Parse OMEN API response wrapper.
        
        OMEN v6 wraps responses via ResponseWrapperMiddleware:
          { "data": { "signals": [...], ... }, "meta": { "mode": "LIVE", ... } }
        
        This method handles:
        1. Envelope format: { "data": ..., "meta": ... }
        2. Direct list: { "signals": [...] } (if middleware is bypassed)
        3. Raw dict (single signal or other)
        """
        if "data" in data and "meta" in data:
            # Full envelope from OMEN ResponseWrapperMiddleware
            inner = data["data"]
            meta = OmenAPIMeta(**data.get("meta", {}))
            
            # Inner data may be { "signals": [...] } or direct list/dict
            if isinstance(inner, dict) and "signals" in inner:
                return OmenAPIResponse(data=inner["signals"], meta=meta)
            return OmenAPIResponse(data=inner, meta=meta)
        
        if "data" in data:
            return OmenAPIResponse(
                data=data["data"],
                meta=OmenAPIMeta(**data.get("meta", {})),
            )
        
        # Direct format (no envelope) - signals list
        if "signals" in data:
            return OmenAPIResponse(data=data["signals"])
        
        # Some endpoints return data directly
        return OmenAPIResponse(data=data)

    def _parse_signal(self, data: dict) -> OmenSignal:
        """
        Convert OMEN API response to internal OmenSignal schema.

        Handles mapping between OMEN's schema and our internal schema.
        """
        # Map category
        category_str = data.get("category", "OTHER").upper()
        try:
            category = SignalCategory(category_str.lower())
        except ValueError:
            category = SignalCategory.OTHER

        # Map geographic scope
        geo_data = data.get("geographic", {})
        chokepoints_raw = geo_data.get("chokepoints", [])

        # Parse primary chokepoint
        primary_chokepoint = Chokepoint.RED_SEA  # Default
        if chokepoints_raw:
            cp_str = chokepoints_raw[0].lower().replace(" ", "_").replace("-", "_")
            # Map common names to enum values
            cp_mapping = {
                "suez_canal": Chokepoint.SUEZ,
                "suez": Chokepoint.SUEZ,
                "red_sea": Chokepoint.RED_SEA,
                "bab_el_mandeb": Chokepoint.RED_SEA,
                "panama_canal": Chokepoint.PANAMA,
                "panama": Chokepoint.PANAMA,
                "malacca_strait": Chokepoint.MALACCA,
                "malacca": Chokepoint.MALACCA,
                "strait_of_hormuz": Chokepoint.HORMUZ,
                "hormuz": Chokepoint.HORMUZ,
                "gibraltar": Chokepoint.GIBRALTAR,
            }
            primary_chokepoint = cp_mapping.get(cp_str, Chokepoint.RED_SEA)

        # Parse secondary chokepoints
        secondary_chokepoints = []
        for cp_str in chokepoints_raw[1:]:
            cp_normalized = cp_str.lower().replace(" ", "_").replace("-", "_")
            cp_mapping = {
                "suez_canal": Chokepoint.SUEZ,
                "suez": Chokepoint.SUEZ,
                "red_sea": Chokepoint.RED_SEA,
            }
            if cp_normalized in cp_mapping:
                secondary_chokepoints.append(cp_mapping[cp_normalized])

        geographic = GeographicScope(
            primary_chokepoint=primary_chokepoint,
            secondary_chokepoints=secondary_chokepoints,
            affected_regions=geo_data.get("regions", []),
            affected_ports=geo_data.get("ports", []),
        )

        # Map temporal scope
        temp_data = data.get("temporal", {})
        detected_at = self._parse_datetime(
            data.get("created_at")
            or data.get("generated_at")
            or data.get("observed_at")
            or temp_data.get("detected_at")
        )
        temporal = TemporalScope(
            detected_at=detected_at or datetime.utcnow(),
            earliest_impact=self._parse_datetime(temp_data.get("earliest_impact")),
            latest_resolution=self._parse_datetime(temp_data.get("resolution_date")),
            is_ongoing=data.get("status", "").upper() == "ACTIVE",
        )

        # Map evidence
        evidence = []
        for ev_data in data.get("evidence", []):
            evidence.append(
                EvidenceItem(
                    source=ev_data.get("source", "unknown"),
                    source_type=ev_data.get("source_type", "unknown"),
                    url=ev_data.get("url"),
                    title=ev_data.get("title", ""),
                    snippet=ev_data.get("snippet"),
                    published_at=self._parse_datetime(ev_data.get("published_at")),
                    collected_at=self._parse_datetime(ev_data.get("observed_at")) or datetime.utcnow(),
                    probability=ev_data.get("probability"),
                    sentiment_score=ev_data.get("sentiment_score"),
                )
            )

        return OmenSignal(
            signal_id=data.get("signal_id", f"OMEN-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"),
            title=data.get("title", "Unknown signal"),
            description=data.get("description", ""),
            category=category,
            probability=float(data.get("probability", 0.5)),
            confidence_score=float(data.get("confidence_score", 0.5)),
            geographic=geographic,
            temporal=temporal,
            evidence=evidence,
            # OMEN v6 uses 'generated_at', fallback to 'created_at' for compat
            created_at=self._parse_datetime(
                data.get("created_at") or data.get("generated_at")
            ) or datetime.utcnow(),
            updated_at=self._parse_datetime(
                data.get("updated_at") or data.get("generated_at")
            ) or datetime.utcnow(),
        )

    def _parse_datetime(self, value: Any) -> Optional[datetime]:
        """Parse datetime from various formats."""
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                # Try ISO format
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                try:
                    # Try common format
                    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S")
                except ValueError:
                    return None
        return None

    def _check_data_quality(self, meta: OmenAPIMeta) -> bool:
        """
        Check if data is from real sources.

        Returns True if data quality is acceptable.
        """
        # Accept LIVE mode with >50% real coverage
        if meta.mode == "LIVE" and meta.real_source_coverage > 0.5:
            return True
        # Accept if we have at least one real source
        if meta.real_sources:
            return True
        # In development, accept any data
        if getattr(settings, 'environment', 'development') == 'development':
            return True
        return False

    # ========================================================================
    # HEALTH CHECK
    # ========================================================================

    async def health_check(self) -> dict:
        """
        Check OMEN API health.

        Returns:
            Health status dict
        """
        try:
            await self._ensure_connected()

            response = await self._http_client.get("/health")
            is_healthy = response.status_code == 200

            return {
                "healthy": is_healthy,
                "status_code": response.status_code,
                "circuit_breaker": self._circuit_breaker.state.value,
            }
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e),
                "circuit_breaker": self._circuit_breaker.state.value,
            }


# ============================================================================
# FACTORY
# ============================================================================


_client_instance: Optional[OmenClient] = None


def get_omen_client() -> OmenClient:
    """Get OMEN client singleton."""
    global _client_instance
    if _client_instance is None:
        _client_instance = OmenClient()
    return _client_instance


async def create_omen_client(config: Optional[OmenClientConfig] = None) -> OmenClient:
    """Create and connect OMEN client."""
    client = OmenClient(config)
    await client.connect()
    return client
