"""
ORACLE Service - Reality Engine.

ORACLE is the Reality Engine of the NEXUS platform.
It provides ground truth about what IS happening:
- AIS vessel tracking
- Freight rates
- Port congestion
- Chokepoint health

And correlates OMEN predictions with reality.

This is the main entry point for reality data in RISKCAST.
"""

from __future__ import annotations

from typing import Optional, TYPE_CHECKING, Any
from datetime import datetime
import asyncio

import structlog

from app.omen.schemas import OmenSignal, Chokepoint
from app.oracle.schemas import (
    CorrelatedIntelligence,
    CorrelationStatus,
    RealitySnapshot,
    ChokepointHealth,
)
from app.oracle.ais import AISClient, get_ais_client
from app.oracle.freight import FreightRateClient, FreightRateSnapshot, get_freight_client
from app.oracle.port import PortDataClient, PortSnapshot, get_port_client
from app.oracle.correlator import SignalCorrelator, get_correlator

if TYPE_CHECKING:
    from app.omen.service import OmenService

logger = structlog.get_logger(__name__)


def _get_omen_service() -> Any:
    """Lazy import to avoid circular dependency."""
    from app.omen.service import get_omen_service
    return get_omen_service()


# ============================================================================
# ORACLE SERVICE
# ============================================================================


class OracleService:
    """
    Main ORACLE service - Reality Engine.

    Provides:
    1. Reality data (AIS, rates, ports)
    2. Chokepoint health status
    3. Signal-reality correlation
    4. Correlated intelligence for RISKCAST

    Usage:
        service = OracleService()
        await service.start()

        # Get reality snapshot
        reality = await service.get_reality_snapshot()

        # Get chokepoint health
        health = await service.get_chokepoint_health(Chokepoint.RED_SEA)

        # Get correlated intelligence (signal + reality)
        intel = await service.get_correlated_intelligence(signal)

        # Get all actionable intelligence
        intel_list = await service.get_actionable_intelligence()

        await service.stop()
    """

    def __init__(
        self,
        omen_service: Optional[OmenService] = None,
        ais_client: Optional[AISClient] = None,
        freight_client: Optional[FreightRateClient] = None,
        port_client: Optional[PortDataClient] = None,
        correlator: Optional[SignalCorrelator] = None,
    ):
        """
        Initialize ORACLE service.

        Args:
            omen_service: OMEN service for signals
            ais_client: AIS vessel tracking client
            freight_client: Freight rate client
            port_client: Port data client
            correlator: Signal-reality correlator
        """
        self._omen = omen_service
        self._ais = ais_client
        self._freight = freight_client
        self._port = port_client
        self._correlator = correlator
        self._running = False
        self._last_snapshot: Optional[RealitySnapshot] = None
        self._snapshot_cache_seconds = 60

    async def start(self):
        """Start the ORACLE service and all components."""
        if self._running:
            return

        # Initialize components
        if self._omen is None:
            self._omen = _get_omen_service()
        if self._ais is None:
            self._ais = get_ais_client()
        if self._freight is None:
            self._freight = get_freight_client()
        if self._port is None:
            self._port = get_port_client()
        if self._correlator is None:
            self._correlator = get_correlator()

        # Start all services
        await asyncio.gather(
            self._omen.start(),
            self._ais.connect(),
            self._freight.connect(),
            self._port.connect(),
            self._correlator.start(),
        )

        self._running = True
        logger.info("oracle_service_started")

    async def stop(self):
        """Stop the ORACLE service."""
        self._running = False

        await asyncio.gather(
            self._omen.stop() if self._omen else asyncio.sleep(0),
            self._ais.disconnect() if self._ais else asyncio.sleep(0),
            self._freight.disconnect() if self._freight else asyncio.sleep(0),
            self._port.disconnect() if self._port else asyncio.sleep(0),
            self._correlator.stop() if self._correlator else asyncio.sleep(0),
        )

        logger.info("oracle_service_stopped")

    # ========================================================================
    # REALITY DATA
    # ========================================================================

    async def get_reality_snapshot(
        self,
        chokepoint: Optional[Chokepoint] = None,
        use_cache: bool = True,
    ) -> RealitySnapshot:
        """
        Get current reality snapshot.

        Args:
            chokepoint: Optional chokepoint to focus on
            use_cache: Whether to use cached snapshot

        Returns:
            RealitySnapshot with current data
        """
        # Check cache
        if use_cache and self._last_snapshot:
            age = (datetime.utcnow() - self._last_snapshot.generated_at).total_seconds()
            if age < self._snapshot_cache_seconds:
                return self._last_snapshot

        snapshot = await self._correlator.get_reality_snapshot(chokepoint)
        self._last_snapshot = snapshot

        return snapshot

    async def get_chokepoint_health(
        self,
        chokepoint: Chokepoint,
    ) -> ChokepointHealth:
        """
        Get health metrics for a specific chokepoint.

        Args:
            chokepoint: The chokepoint to check

        Returns:
            ChokepointHealth with current metrics
        """
        snapshot = await self.get_reality_snapshot(chokepoint)
        health = snapshot.get_chokepoint_health(chokepoint)

        if health is None:
            # Return default healthy state
            health = ChokepointHealth(
                chokepoint=chokepoint,
                vessels_in_transit=0,
                vessels_waiting=0,
                rerouting_count=0,
                current_rate_per_teu=1500.0,
                baseline_rate_per_teu=1500.0,
                average_delay_hours=0.0,
                max_delay_hours=0.0,
            )

        return health

    async def get_freight_rates(self) -> FreightRateSnapshot:
        """
        Get current freight rates.

        Returns:
            FreightRateSnapshot with all route rates
        """
        return await self._freight.get_rate_snapshot()

    async def get_port_status(
        self,
        port_codes: Optional[list[str]] = None,
    ) -> PortSnapshot:
        """
        Get port congestion status.

        Args:
            port_codes: Specific ports to check (all if None)

        Returns:
            PortSnapshot with port data
        """
        return await self._port.get_port_snapshot(port_codes)

    # ========================================================================
    # CORRELATED INTELLIGENCE
    # ========================================================================

    async def get_correlated_intelligence(
        self,
        signal: OmenSignal,
    ) -> CorrelatedIntelligence:
        """
        Get correlated intelligence for a signal.

        This is the primary method for RISKCAST to get intelligence.

        Args:
            signal: OMEN signal to correlate

        Returns:
            CorrelatedIntelligence with signal + reality
        """
        return await self._correlator.correlate(signal)

    async def get_actionable_intelligence(
        self,
        chokepoints: Optional[list[str]] = None,
        min_probability: float = 0.3,
    ) -> list[CorrelatedIntelligence]:
        """
        Get all actionable intelligence.

        Fetches active signals from OMEN, correlates with reality,
        and returns intelligence that warrants action.

        Args:
            chokepoints: Filter by chokepoints
            min_probability: Minimum probability threshold

        Returns:
            List of actionable CorrelatedIntelligence
        """
        # Get active signals
        signals = await self._omen.get_active_signals(
            chokepoints=chokepoints,
            min_probability=min_probability,
        )

        if not signals:
            return []

        # Correlate all signals with reality
        intelligence_list = await self._correlator.correlate_batch(signals)

        # Filter for actionable (confirmed or materializing)
        actionable = [
            intel for intel in intelligence_list
            if intel.is_actionable
        ]

        logger.info(
            "actionable_intelligence",
            total_signals=len(signals),
            actionable_count=len(actionable),
        )

        return actionable

    async def get_intelligence_for_route(
        self,
        origin: str,
        destination: str,
        min_probability: float = 0.3,
    ) -> list[CorrelatedIntelligence]:
        """
        Get intelligence for a specific route.

        Args:
            origin: Origin port code
            destination: Destination port code
            min_probability: Minimum probability threshold

        Returns:
            List of CorrelatedIntelligence affecting the route
        """
        # Get signals for route
        signals = await self._omen.get_signals_for_route(
            origin=origin,
            destination=destination,
            min_probability=min_probability,
        )

        if not signals:
            return []

        # Correlate with reality
        return await self._correlator.correlate_batch(signals)

    # ========================================================================
    # MONITORING
    # ========================================================================

    async def get_disruption_level(
        self,
        chokepoint: Chokepoint,
    ) -> str:
        """
        Get current disruption level for a chokepoint.

        Returns:
            Disruption level: normal, elevated, severe, critical
        """
        health = await self.get_chokepoint_health(chokepoint)
        return health.disruption_level

    async def is_chokepoint_affected(
        self,
        chokepoint: Chokepoint,
    ) -> bool:
        """
        Check if a chokepoint is currently affected.

        Returns:
            True if disruption level is elevated or worse
        """
        level = await self.get_disruption_level(chokepoint)
        return level in ["elevated", "severe", "critical"]

    # ========================================================================
    # HEALTH CHECK
    # ========================================================================

    async def health_check(self) -> dict:
        """
        Check service health.

        Returns:
            Health status dict
        """
        omen_health = await self._omen.health_check() if self._omen else {"healthy": False}
        ais_health = {"healthy": self._ais is not None}
        freight_health = {"healthy": self._freight is not None}
        port_health = {"healthy": self._port is not None}

        return {
            "service": "oracle",
            "running": self._running,
            "components": {
                "omen": omen_health,
                "ais": ais_health,
                "freight": freight_health,
                "port": port_health,
            },
        }


# ============================================================================
# FACTORY
# ============================================================================


_service_instance: Optional[OracleService] = None


def get_oracle_service() -> OracleService:
    """Get ORACLE service singleton."""
    global _service_instance
    if _service_instance is None:
        _service_instance = OracleService()
    return _service_instance


async def create_oracle_service() -> OracleService:
    """Create and start ORACLE service."""
    service = OracleService()
    await service.start()
    return service
