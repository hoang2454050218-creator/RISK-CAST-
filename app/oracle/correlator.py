"""
Signal-Reality Correlator.

The CORRELATOR is the brain of ORACLE. It takes:
- OMEN signals (predictions)
- Reality data (AIS, freight rates, port congestion)

And produces:
- CorrelatedIntelligence (signal + reality confirmation)

The correlation status indicates how well prediction matches reality:
- CONFIRMED: Signal is happening (high probability + reality confirms)
- MATERIALIZING: Early signs appearing in reality
- PREDICTED_NOT_OBSERVED: Signal exists but reality still normal
- SURPRISE: Reality disruption without prior signal
- NORMAL: No significant signal or disruption
"""

from typing import Optional
from datetime import datetime
import asyncio

import structlog

from app.omen.schemas import OmenSignal, Chokepoint
from app.oracle.schemas import (
    CorrelatedIntelligence,
    CorrelationStatus,
    RealitySnapshot,
    ChokepointHealth,
    VesselMovement,
)
from app.oracle.ais import AISClient, get_ais_client
from app.oracle.freight import FreightRateClient, FreightRoute, get_freight_client
from app.oracle.port import PortDataClient, get_port_client

logger = structlog.get_logger(__name__)


# ============================================================================
# CORRELATION THRESHOLDS
# ============================================================================

# Thresholds for determining correlation status
CORRELATION_THRESHOLDS = {
    # Rate premium above which we consider rates elevated
    "rate_premium_elevated": 0.20,  # 20% above baseline
    "rate_premium_severe": 0.50,  # 50% above baseline

    # Rerouting vessels indicating disruption
    "rerouting_count_elevated": 10,
    "rerouting_count_severe": 30,

    # Wait time above which port is congested
    "port_wait_elevated": 24,  # hours
    "port_wait_severe": 72,  # hours

    # Signal probability thresholds
    "signal_probability_high": 0.70,
    "signal_probability_medium": 0.50,

    # Combined confidence calculation weights
    "weight_signal": 0.4,
    "weight_rates": 0.25,
    "weight_rerouting": 0.2,
    "weight_congestion": 0.15,
}


# ============================================================================
# CORRELATOR
# ============================================================================


class SignalCorrelator:
    """
    Correlates OMEN signals with reality data.

    The correlator answers: "Is this predicted signal actually happening?"

    Usage:
        correlator = SignalCorrelator()
        await correlator.start()

        # Correlate a signal with reality
        intelligence = await correlator.correlate(signal)

        # Get correlation for multiple signals
        intel_list = await correlator.correlate_batch(signals)

        await correlator.stop()
    """

    def __init__(
        self,
        ais_client: Optional[AISClient] = None,
        freight_client: Optional[FreightRateClient] = None,
        port_client: Optional[PortDataClient] = None,
    ):
        """
        Initialize correlator with data clients.

        Args:
            ais_client: AIS vessel tracking client
            freight_client: Freight rate client
            port_client: Port data client
        """
        self._ais = ais_client
        self._freight = freight_client
        self._port = port_client
        self._running = False

    async def start(self):
        """Start the correlator and connect clients."""
        if self._running:
            return

        # Initialize clients
        if self._ais is None:
            self._ais = get_ais_client()
        if self._freight is None:
            self._freight = get_freight_client()
        if self._port is None:
            self._port = get_port_client()

        # Connect all clients
        await asyncio.gather(
            self._ais.connect(),
            self._freight.connect(),
            self._port.connect(),
        )

        self._running = True
        logger.info("correlator_started")

    async def stop(self):
        """Stop the correlator and disconnect clients."""
        self._running = False

        await asyncio.gather(
            self._ais.disconnect() if self._ais else asyncio.sleep(0),
            self._freight.disconnect() if self._freight else asyncio.sleep(0),
            self._port.disconnect() if self._port else asyncio.sleep(0),
        )

        logger.info("correlator_stopped")

    # ========================================================================
    # CORRELATION
    # ========================================================================

    async def correlate(
        self,
        signal: OmenSignal,
    ) -> CorrelatedIntelligence:
        """
        Correlate a signal with reality data.

        This is the main method that produces intelligence for RISKCAST.

        Args:
            signal: OMEN signal to correlate

        Returns:
            CorrelatedIntelligence with correlation status
        """
        chokepoint = signal.geographic.primary_chokepoint

        # Fetch reality data in parallel
        reality_task = self._build_reality_snapshot(chokepoint)
        reality = await reality_task

        # Calculate correlation factors
        factors = self._calculate_correlation_factors(signal, reality)

        # Determine correlation status
        status = self._determine_correlation_status(signal, factors)

        # Calculate combined confidence
        combined_confidence = self._calculate_combined_confidence(signal, factors)

        # Create correlated intelligence
        correlation_id = f"CORR-{signal.signal_id}-{datetime.utcnow().strftime('%H%M%S')}"

        intelligence = CorrelatedIntelligence(
            correlation_id=correlation_id,
            signal=signal,
            reality=reality,
            correlation_status=status,
            correlation_factors=factors,
            combined_confidence=combined_confidence,
        )

        logger.info(
            "signal_correlated",
            signal_id=signal.signal_id,
            correlation_status=status.value,
            combined_confidence=round(combined_confidence, 3),
            factors=factors,
        )

        return intelligence

    async def correlate_batch(
        self,
        signals: list[OmenSignal],
    ) -> list[CorrelatedIntelligence]:
        """
        Correlate multiple signals with reality.

        Args:
            signals: List of OMEN signals

        Returns:
            List of CorrelatedIntelligence
        """
        # Process in parallel
        tasks = [self.correlate(signal) for signal in signals]
        return await asyncio.gather(*tasks)

    async def get_reality_snapshot(
        self,
        chokepoint: Optional[Chokepoint] = None,
    ) -> RealitySnapshot:
        """
        Get current reality snapshot.

        Args:
            chokepoint: Optional chokepoint to focus on

        Returns:
            RealitySnapshot with current data
        """
        if chokepoint:
            return await self._build_reality_snapshot(chokepoint)

        # Get snapshot for all chokepoints
        snapshot_id = f"ORACLE-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        all_health = {}

        for cp in [Chokepoint.RED_SEA, Chokepoint.SUEZ, Chokepoint.PANAMA, Chokepoint.MALACCA]:
            health = await self._get_chokepoint_health(cp)
            all_health[cp.value] = health

        # Get global rerouting vessels
        rerouting = await self._ais.get_rerouting_vessels()

        # Calculate global disruption
        avg_premium = sum(h.rate_premium_pct for h in all_health.values()) / len(all_health)
        avg_rerouting = sum(h.rerouting_count for h in all_health.values())

        global_disruption = min(1.0, avg_premium + (avg_rerouting / 100))

        return RealitySnapshot(
            snapshot_id=snapshot_id,
            chokepoint_health=all_health,
            vessels_rerouting=rerouting,
            total_vessels_tracked=len(rerouting) * 10,  # Approximate
            global_disruption_score=round(global_disruption, 3),
        )

    # ========================================================================
    # INTERNAL METHODS
    # ========================================================================

    async def _build_reality_snapshot(
        self,
        chokepoint: Chokepoint,
    ) -> RealitySnapshot:
        """Build reality snapshot for a specific chokepoint."""
        snapshot_id = f"ORACLE-{chokepoint.value}-{datetime.utcnow().strftime('%H%M%S')}"

        # Get chokepoint health
        health = await self._get_chokepoint_health(chokepoint)

        # Get rerouting vessels
        rerouting = await self._ais.get_rerouting_vessels(chokepoint)

        # Calculate disruption score
        rate_factor = min(1.0, health.rate_premium_pct)
        reroute_factor = min(1.0, health.rerouting_count / 50)
        delay_factor = min(1.0, health.average_delay_hours / 168)  # 7 days max

        disruption = (rate_factor * 0.4 + reroute_factor * 0.35 + delay_factor * 0.25)

        return RealitySnapshot(
            snapshot_id=snapshot_id,
            chokepoint_health={chokepoint.value: health},
            vessels_rerouting=rerouting,
            total_vessels_tracked=len(rerouting) + health.vessels_in_transit,
            global_disruption_score=round(disruption, 3),
        )

    async def _get_chokepoint_health(
        self,
        chokepoint: Chokepoint,
    ) -> ChokepointHealth:
        """Get health metrics for a chokepoint."""
        # Get data in parallel
        vessels_task = self._ais.get_vessels_in_chokepoint(chokepoint)
        waiting_task = self._ais.get_vessels_waiting(chokepoint)
        rerouting_task = self._ais.get_rerouting_vessels(chokepoint)
        rates_task = self._freight.get_rates_for_chokepoint(chokepoint)
        ports_task = self._port.get_ports_for_chokepoint(chokepoint)

        vessels, waiting, rerouting, rates, ports = await asyncio.gather(
            vessels_task, waiting_task, rerouting_task, rates_task, ports_task
        )

        # Calculate rate metrics
        if rates:
            current_rate = sum(r.current_rate_usd for r in rates) / len(rates) / 2  # Per TEU
            baseline_rate = sum(r.baseline_rate_usd for r in rates) / len(rates) / 2
        else:
            current_rate = 1500.0
            baseline_rate = 1500.0

        # Calculate delay from port congestion
        avg_wait = 0.0
        if ports:
            avg_wait = sum(p.average_wait_hours for p in ports) / len(ports)

        # Determine disruption level
        rate_premium = (current_rate - baseline_rate) / baseline_rate if baseline_rate > 0 else 0
        if rate_premium > 0.5 or len(rerouting) > 30:
            disruption_level = "critical"
        elif rate_premium > 0.3 or len(rerouting) > 15:
            disruption_level = "severe"
        elif rate_premium > 0.15 or len(rerouting) > 5:
            disruption_level = "elevated"
        else:
            disruption_level = "normal"

        return ChokepointHealth(
            chokepoint=chokepoint,
            vessels_in_transit=len(vessels),
            vessels_waiting=len(waiting),
            rerouting_count=len(rerouting),
            current_rate_per_teu=round(current_rate, 2),
            baseline_rate_per_teu=round(baseline_rate, 2),
            average_delay_hours=round(avg_wait, 1),
            max_delay_hours=round(avg_wait * 1.5, 1),
            is_operational=(disruption_level != "critical"),
            disruption_level=disruption_level,
        )

    def _calculate_correlation_factors(
        self,
        signal: OmenSignal,
        reality: RealitySnapshot,
    ) -> dict[str, float]:
        """Calculate correlation factors between signal and reality."""
        chokepoint = signal.geographic.primary_chokepoint
        health = reality.get_chokepoint_health(chokepoint)

        factors = {}

        # Signal factors
        factors["signal_probability"] = signal.probability
        factors["signal_confidence"] = signal.confidence_score

        if health:
            # Rate correlation
            rate_premium = health.rate_premium_pct
            factors["rate_premium"] = rate_premium
            factors["rate_elevated"] = 1.0 if rate_premium > CORRELATION_THRESHOLDS["rate_premium_elevated"] else 0.0

            # Rerouting correlation
            rerouting = health.rerouting_count
            factors["rerouting_count"] = rerouting
            factors["rerouting_elevated"] = 1.0 if rerouting > CORRELATION_THRESHOLDS["rerouting_count_elevated"] else 0.0

            # Delay correlation
            factors["average_delay_hours"] = health.average_delay_hours
            factors["delay_elevated"] = 1.0 if health.average_delay_hours > CORRELATION_THRESHOLDS["port_wait_elevated"] else 0.0

            # Congestion
            factors["congestion_ratio"] = health.congestion_ratio
        else:
            factors["rate_premium"] = 0.0
            factors["rate_elevated"] = 0.0
            factors["rerouting_count"] = 0
            factors["rerouting_elevated"] = 0.0
            factors["average_delay_hours"] = 0.0
            factors["delay_elevated"] = 0.0
            factors["congestion_ratio"] = 0.0

        # Reality confirmation score (0-1)
        reality_score = (
            factors.get("rate_elevated", 0) * 0.4 +
            factors.get("rerouting_elevated", 0) * 0.35 +
            factors.get("delay_elevated", 0) * 0.25
        )
        factors["reality_confirmation"] = round(reality_score, 3)

        return factors

    def _determine_correlation_status(
        self,
        signal: OmenSignal,
        factors: dict[str, float],
    ) -> CorrelationStatus:
        """Determine correlation status from factors."""
        signal_prob = factors.get("signal_probability", 0)
        reality_confirmation = factors.get("reality_confirmation", 0)

        # High signal + high reality = CONFIRMED
        if signal_prob >= 0.7 and reality_confirmation >= 0.6:
            return CorrelationStatus.CONFIRMED

        # High signal + medium reality = MATERIALIZING
        if signal_prob >= 0.5 and reality_confirmation >= 0.3:
            return CorrelationStatus.MATERIALIZING

        # High signal + low reality = PREDICTED_NOT_OBSERVED
        if signal_prob >= 0.5 and reality_confirmation < 0.3:
            return CorrelationStatus.PREDICTED_NOT_OBSERVED

        # Low signal + high reality = SURPRISE
        if signal_prob < 0.3 and reality_confirmation >= 0.5:
            return CorrelationStatus.SURPRISE

        # Default = NORMAL
        return CorrelationStatus.NORMAL

    def _calculate_combined_confidence(
        self,
        signal: OmenSignal,
        factors: dict[str, float],
    ) -> float:
        """Calculate combined confidence score."""
        weights = CORRELATION_THRESHOLDS

        # Component scores
        signal_score = (signal.probability + signal.confidence_score) / 2
        rate_score = min(1.0, factors.get("rate_premium", 0) / 0.5)
        rerouting_score = min(1.0, factors.get("rerouting_count", 0) / 30)
        congestion_score = factors.get("congestion_ratio", 0)

        # Weighted combination
        combined = (
            signal_score * weights["weight_signal"] +
            rate_score * weights["weight_rates"] +
            rerouting_score * weights["weight_rerouting"] +
            congestion_score * weights["weight_congestion"]
        )

        return round(min(1.0, combined), 3)


# ============================================================================
# FACTORY
# ============================================================================


_correlator_instance: Optional[SignalCorrelator] = None


def get_correlator() -> SignalCorrelator:
    """Get correlator singleton."""
    global _correlator_instance
    if _correlator_instance is None:
        _correlator_instance = SignalCorrelator()
    return _correlator_instance


async def create_correlator() -> SignalCorrelator:
    """Create and start correlator."""
    correlator = SignalCorrelator()
    await correlator.start()
    return correlator
