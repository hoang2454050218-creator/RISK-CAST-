"""
OMEN Integration Service for RISKCAST.

This service provides a high-level interface for working with OMEN signals.
It manages the OMEN client lifecycle, caching, and signal processing.

Responsibilities:
- Manage OMEN client lifecycle
- Provide caching layer for signals
- Filter and process signals for RISKCAST
- Handle signal-to-intelligence conversion
- Maintain connection health metrics
"""

from typing import Optional, AsyncGenerator, Callable, TYPE_CHECKING
from datetime import datetime, timedelta
import asyncio

import structlog

from app.omen.client import OmenClient, OmenClientConfig, get_omen_client
from app.omen.schemas import OmenSignal, Chokepoint
from app.riskcast.constants import derive_chokepoints

if TYPE_CHECKING:
    from app.oracle.schemas import CorrelatedIntelligence, CorrelationStatus

logger = structlog.get_logger(__name__)


# ============================================================================
# SIMPLE CACHE
# ============================================================================


class SignalCache:
    """
    Simple in-memory cache for signals.

    For production, use Redis instead.
    """

    def __init__(self, ttl_seconds: int = 300):
        self._cache: dict[str, tuple[OmenSignal, datetime]] = {}
        self._list_cache: Optional[tuple[list[OmenSignal], datetime]] = None
        self._ttl = timedelta(seconds=ttl_seconds)

    def get(self, signal_id: str) -> Optional[OmenSignal]:
        """Get cached signal if not expired."""
        if signal_id in self._cache:
            signal, cached_at = self._cache[signal_id]
            if datetime.utcnow() - cached_at < self._ttl:
                return signal
            del self._cache[signal_id]
        return None

    def set(self, signal: OmenSignal):
        """Cache a signal."""
        self._cache[signal.signal_id] = (signal, datetime.utcnow())

    def get_all(self) -> Optional[list[OmenSignal]]:
        """Get cached signal list if not expired."""
        if self._list_cache:
            signals, cached_at = self._list_cache
            if datetime.utcnow() - cached_at < self._ttl:
                return signals
            self._list_cache = None
        return None

    def set_all(self, signals: list[OmenSignal]):
        """Cache signal list."""
        self._list_cache = (signals, datetime.utcnow())
        for signal in signals:
            self.set(signal)

    def invalidate(self):
        """Clear all cache."""
        self._cache.clear()
        self._list_cache = None


# ============================================================================
# OMEN SERVICE
# ============================================================================


class OmenService:
    """
    High-level service for OMEN integration.

    This is the primary interface that RISKCAST uses to get signals.
    It handles caching, filtering, and client management.

    Usage:
        service = OmenService()
        await service.start()

        # Get signals affecting Red Sea
        signals = await service.get_active_signals(
            chokepoints=["red_sea"],
            min_probability=0.5,
        )

        # Get signals for a specific route
        signals = await service.get_signals_for_route(
            origin="CNSHA",
            destination="NLRTM",
        )

        # Subscribe to real-time updates
        async for signal in service.stream_signals():
            await process_signal(signal)

        await service.stop()
    """

    def __init__(
        self,
        client: Optional[OmenClient] = None,
        cache_ttl_seconds: int = 300,
    ):
        """
        Initialize OMEN service.

        Args:
            client: OMEN client instance (creates default if not provided)
            cache_ttl_seconds: Cache TTL in seconds (default: 5 minutes)
        """
        self._client = client
        self._cache = SignalCache(ttl_seconds=cache_ttl_seconds)
        self._running = False
        self._background_task: Optional[asyncio.Task] = None

    async def start(self):
        """
        Start the service.

        Initializes the OMEN client and establishes connection.
        """
        if self._running:
            return

        if self._client is None:
            self._client = get_omen_client()

        await self._client.connect()
        self._running = True

        logger.info("omen_service_started")

    async def stop(self):
        """
        Stop the service.

        Gracefully closes connections and cancels background tasks.
        """
        self._running = False

        if self._background_task and not self._background_task.done():
            self._background_task.cancel()
            try:
                await self._background_task
            except asyncio.CancelledError:
                pass

        if self._client:
            await self._client.disconnect()

        logger.info("omen_service_stopped")

    # ========================================================================
    # SIGNAL RETRIEVAL
    # ========================================================================

    async def get_active_signals(
        self,
        chokepoints: Optional[list[str]] = None,
        min_probability: float = 0.3,
        use_cache: bool = True,
    ) -> list[OmenSignal]:
        """
        Get active signals, optionally filtered.

        Args:
            chokepoints: Filter by specific chokepoints (e.g., ["red_sea", "suez"])
            min_probability: Minimum probability threshold (default: 0.3)
            use_cache: Whether to use cached results (default: True)

        Returns:
            List of active OmenSignal objects
        """
        # Try cache first
        if use_cache:
            cached = self._cache.get_all()
            if cached:
                logger.debug("using_cached_signals", count=len(cached))
                return self._filter_signals(cached, chokepoints, min_probability)

        # Fetch from OMEN
        try:
            signals = await self._client.get_signals(
                status="ACTIVE",
                min_probability=min_probability,
            )

            # Cache the results
            self._cache.set_all(signals)

            # Filter and return
            return self._filter_signals(signals, chokepoints, min_probability)

        except Exception as e:
            logger.error(
                "failed_to_get_signals",
                error=str(e),
            )

            # Try to return cached data even if expired
            cached = self._cache.get_all()
            if cached:
                logger.warning("returning_stale_cache")
                return self._filter_signals(cached, chokepoints, min_probability)

            return []

    async def get_signal(self, signal_id: str) -> Optional[OmenSignal]:
        """
        Get a specific signal by ID.

        Args:
            signal_id: The signal ID

        Returns:
            OmenSignal or None if not found
        """
        # Check cache
        cached = self._cache.get(signal_id)
        if cached:
            return cached

        # Fetch from OMEN
        signal = await self._client.get_signal(signal_id)
        if signal:
            self._cache.set(signal)

        return signal

    async def get_signals_for_route(
        self,
        origin: str,
        destination: str,
        min_probability: float = 0.3,
    ) -> list[OmenSignal]:
        """
        Get signals affecting a specific route.

        Derives chokepoints from the origin/destination and returns
        signals that affect those chokepoints.

        Args:
            origin: Origin port code (e.g., "CNSHA")
            destination: Destination port code (e.g., "NLRTM")
            min_probability: Minimum probability threshold

        Returns:
            List of signals affecting the route
        """
        # Derive chokepoints for this route
        chokepoints = derive_chokepoints(origin, destination)

        if not chokepoints:
            logger.debug(
                "no_chokepoints_for_route",
                origin=origin,
                destination=destination,
            )
            return []

        # Get signals for these chokepoints
        signals = await self.get_active_signals(
            chokepoints=chokepoints,
            min_probability=min_probability,
        )

        logger.debug(
            "signals_for_route",
            origin=origin,
            destination=destination,
            chokepoints=chokepoints,
            signal_count=len(signals),
        )

        return signals

    async def get_signals_by_category(
        self,
        category: str,
        min_probability: float = 0.3,
    ) -> list[OmenSignal]:
        """
        Get signals by category.

        Args:
            category: Signal category (e.g., "geopolitical", "weather")
            min_probability: Minimum probability threshold

        Returns:
            List of signals in the category
        """
        signals = await self.get_active_signals(min_probability=min_probability)
        return [s for s in signals if s.category.value.lower() == category.lower()]

    # ========================================================================
    # REAL-TIME SUBSCRIPTION
    # ========================================================================

    async def stream_signals(
        self,
        chokepoints: Optional[list[str]] = None,
        min_probability: float = 0.3,
    ) -> AsyncGenerator[OmenSignal, None]:
        """
        Stream real-time signal updates.

        Subscribes to OMEN WebSocket and yields signals as they arrive.
        Optionally filters by chokepoint and probability.

        Args:
            chokepoints: Filter by chokepoints
            min_probability: Minimum probability threshold

        Yields:
            OmenSignal objects as they arrive
        """
        async for signal in self._client.subscribe():
            # Apply filters
            if min_probability and signal.probability < min_probability:
                continue

            if chokepoints:
                signal_chokepoints = [
                    signal.geographic.primary_chokepoint.value
                ] + [cp.value for cp in signal.geographic.secondary_chokepoints]

                if not any(cp in chokepoints for cp in signal_chokepoints):
                    continue

            # Cache the signal
            self._cache.set(signal)

            yield signal

    async def start_background_subscription(
        self,
        callback: Callable[[OmenSignal], None],
        chokepoints: Optional[list[str]] = None,
    ):
        """
        Start background subscription to OMEN.

        Calls the callback for each received signal.

        Args:
            callback: Function to call with each signal
            chokepoints: Optional chokepoint filter
        """
        async def _subscription_loop():
            async for signal in self.stream_signals(chokepoints=chokepoints):
                try:
                    result = callback(signal)
                    if asyncio.iscoroutine(result):
                        await result
                except Exception as e:
                    logger.error(
                        "signal_callback_error",
                        signal_id=signal.signal_id,
                        error=str(e),
                    )

        self._background_task = asyncio.create_task(_subscription_loop())
        logger.info("background_subscription_started")

    # ========================================================================
    # REFRESH
    # ========================================================================

    async def refresh(self) -> list[OmenSignal]:
        """
        Force refresh signals from OMEN.

        Invalidates cache and fetches fresh data.

        Returns:
            List of refreshed signals
        """
        self._cache.invalidate()

        signals = await self._client.refresh_signals()
        self._cache.set_all(signals)

        logger.info(
            "signals_refreshed",
            count=len(signals),
        )

        return signals

    # ========================================================================
    # HELPER METHODS
    # ========================================================================

    def _filter_signals(
        self,
        signals: list[OmenSignal],
        chokepoints: Optional[list[str]],
        min_probability: float,
    ) -> list[OmenSignal]:
        """Filter signals by chokepoint and probability."""
        filtered = []

        for signal in signals:
            # Check probability
            if signal.probability < min_probability:
                continue

            # Check chokepoints
            if chokepoints:
                signal_chokepoints = [
                    signal.geographic.primary_chokepoint.value
                ] + [cp.value for cp in signal.geographic.secondary_chokepoints]

                if not any(cp.lower() in [sc.lower() for sc in signal_chokepoints] for cp in chokepoints):
                    continue

            filtered.append(signal)

        return filtered

    # ========================================================================
    # HEALTH CHECK
    # ========================================================================

    async def health_check(self) -> dict:
        """
        Check service health.

        Returns:
            Health status dict
        """
        client_health = await self._client.health_check() if self._client else {"healthy": False}

        return {
            "service": "omen",
            "running": self._running,
            "client": client_health,
            "cache_size": len(self._cache._cache),
        }


# ============================================================================
# FACTORY
# ============================================================================


_service_instance: Optional[OmenService] = None


def get_omen_service() -> OmenService:
    """Get OMEN service singleton."""
    global _service_instance
    if _service_instance is None:
        _service_instance = OmenService()
    return _service_instance


async def create_omen_service() -> OmenService:
    """Create and start OMEN service."""
    service = OmenService()
    await service.start()
    return service
