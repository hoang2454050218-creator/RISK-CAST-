"""Exposure Matcher - Match signals to customer shipments.

The ExposureMatcher answers: "Which of this customer's shipments are affected?"

This is the first step in the RISKCAST pipeline:
1. MATCH EXPOSURE (this module)
2. Calculate impact
3. Generate actions
4. Analyze trade-offs
5. Compose decision
"""

from datetime import datetime, timedelta
from typing import Optional

import structlog
from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.oracle.schemas import CorrelatedIntelligence
from app.riskcast.constants import ShipmentStatus
from app.riskcast.schemas.customer import CustomerContext, Shipment

logger = structlog.get_logger(__name__)


# ============================================================================
# EXPOSURE MATCH MODEL
# ============================================================================


class ExposureMatch(BaseModel):
    """
    Result of matching intelligence to customer exposure.

    This is the foundation of personalized decisions.
    Without this match, we can only send generic alerts.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "customer_id": "cust_abc123",
                "signal_id": "OMEN-RS2024-001",
                "affected_shipments": [],
                "total_exposure_usd": 235000,
                "total_teu": 6.0,
                "chokepoint_matched": "red_sea",
                "match_confidence": 0.87,
            }
        }
    )

    # Identity
    customer_id: str = Field(description="Customer ID")
    signal_id: str = Field(description="Signal ID that caused this match")

    # Matched shipments
    affected_shipments: list[Shipment] = Field(
        default_factory=list,
        description="Shipments affected by this signal",
    )

    # Aggregate exposure
    total_exposure_usd: float = Field(
        default=0,
        ge=0,
        description="Total cargo value at risk (USD)",
    )
    total_teu: float = Field(
        default=0,
        ge=0,
        description="Total TEUs affected",
    )

    # Match details
    chokepoint_matched: str = Field(
        description="Which chokepoint triggered the match",
    )
    match_confidence: float = Field(
        ge=0,
        le=1,
        description="Confidence in the exposure match",
    )

    # Timing analysis
    earliest_impact: Optional[datetime] = Field(
        default=None,
        description="When the first shipment will be affected",
    )
    latest_eta: Optional[datetime] = Field(
        default=None,
        description="Latest ETA among affected shipments",
    )

    # Actionability
    actionable_shipments: int = Field(
        default=0,
        ge=0,
        description="Number of shipments we can still act on",
    )
    shipments_with_penalties: int = Field(
        default=0,
        ge=0,
        description="Number of shipments with delay penalties",
    )

    # Metadata
    matched_at: datetime = Field(default_factory=datetime.utcnow)

    @computed_field
    @property
    def has_exposure(self) -> bool:
        """Does customer have any exposure?"""
        return len(self.affected_shipments) > 0

    @computed_field
    @property
    def shipment_count(self) -> int:
        """Number of affected shipments."""
        return len(self.affected_shipments)

    @computed_field
    @property
    def all_shipments_actionable(self) -> bool:
        """Are all affected shipments still actionable?"""
        return self.actionable_shipments == self.shipment_count

    @computed_field
    @property
    def has_penalty_risk(self) -> bool:
        """Do any shipments have delay penalty clauses?"""
        return self.shipments_with_penalties > 0


# ============================================================================
# EXPOSURE MATCHER
# ============================================================================


class ExposureMatcher:
    """
    Matches intelligence signals to customer shipments.

    Logic:
    1. Get chokepoint from signal
    2. Find shipments transiting that chokepoint
    3. Filter by timing (is shipment in the event window?)
    4. Filter by status (not already delivered/cancelled)
    5. Calculate total exposure and confidence

    This is the FOUNDATION of personalized decisions.
    """

    def __init__(
        self,
        timing_buffer_days: int = 7,
        min_confidence: float = 0.3,
    ):
        """
        Initialize exposure matcher.

        Args:
            timing_buffer_days: Buffer days for timing overlap check
            min_confidence: Minimum confidence to include a match
        """
        self.timing_buffer_days = timing_buffer_days
        self.min_confidence = min_confidence

    def match(
        self,
        intelligence: CorrelatedIntelligence,
        context: CustomerContext,
    ) -> ExposureMatch:
        """
        Match intelligence to customer's exposed shipments.

        Args:
            intelligence: Correlated intelligence from ORACLE
            context: Customer context with profile and shipments

        Returns:
            ExposureMatch with affected shipments and metrics
        """
        # 1. Get affected chokepoint from signal
        chokepoint = intelligence.signal.geographic.primary_chokepoint.value

        logger.debug(
            "matching_exposure",
            customer_id=context.profile.customer_id,
            signal_id=intelligence.signal.signal_id,
            chokepoint=chokepoint,
            total_shipments=len(context.active_shipments),
        )

        # 2. Find affected shipments
        affected: list[Shipment] = []
        for shipment in context.active_shipments:
            if self._is_affected(shipment, chokepoint, intelligence):
                affected.append(shipment)

        # 3. Calculate aggregates
        total_value = sum(s.cargo_value_usd for s in affected)
        total_teu = sum(s.teu_count for s in affected)

        # 4. Count actionable shipments
        actionable = [s for s in affected if s.is_actionable]
        with_penalties = [s for s in affected if s.has_delay_penalty]

        # 5. Find timing bounds
        earliest_impact = None
        latest_eta = None
        if affected:
            # Find earliest impact time
            in_transit_or_booked = [
                s for s in affected
                if s.status in [ShipmentStatus.BOOKED, ShipmentStatus.IN_TRANSIT]
            ]
            if in_transit_or_booked:
                earliest_impact = min(s.eta for s in in_transit_or_booked)
                latest_eta = max(s.eta for s in in_transit_or_booked)

        # 6. Calculate match confidence
        confidence = self._compute_confidence(
            affected=affected,
            intelligence=intelligence,
            context=context,
        )

        match = ExposureMatch(
            customer_id=context.profile.customer_id,
            signal_id=intelligence.signal.signal_id,
            affected_shipments=affected,
            total_exposure_usd=total_value,
            total_teu=total_teu,
            chokepoint_matched=chokepoint,
            match_confidence=confidence,
            earliest_impact=earliest_impact,
            latest_eta=latest_eta,
            actionable_shipments=len(actionable),
            shipments_with_penalties=len(with_penalties),
        )

        logger.info(
            "exposure_matched",
            customer_id=context.profile.customer_id,
            signal_id=intelligence.signal.signal_id,
            chokepoint=chokepoint,
            has_exposure=match.has_exposure,
            affected_count=match.shipment_count,
            exposure_usd=match.total_exposure_usd,
            confidence=match.match_confidence,
        )

        return match

    def _is_affected(
        self,
        shipment: Shipment,
        chokepoint: str,
        intelligence: CorrelatedIntelligence,
    ) -> bool:
        """
        Check if a shipment is affected by the signal.

        Criteria:
        1. Shipment route includes the chokepoint
        2. Shipment is not already completed (delivered/cancelled)
        3. Shipment timing overlaps with event window

        Args:
            shipment: Shipment to check
            chokepoint: Chokepoint from signal
            intelligence: Full intelligence context

        Returns:
            True if shipment is affected
        """
        # Check 1: Route includes chokepoint
        if not shipment.has_chokepoint(chokepoint):
            return False

        # Check 2: Shipment not completed
        if shipment.is_completed:
            return False

        # Check 3: Timing overlap
        if not self._timing_overlaps(shipment, intelligence):
            return False

        return True

    def _timing_overlaps(
        self,
        shipment: Shipment,
        intelligence: CorrelatedIntelligence,
    ) -> bool:
        """
        Check if shipment timing overlaps with event window.

        We want to catch shipments that:
        - Are currently in transit through the affected area
        - Will be departing during the event
        - Will arrive during the event

        Args:
            shipment: Shipment to check
            intelligence: Intelligence with event timing

        Returns:
            True if timing overlaps
        """
        now = datetime.utcnow()
        buffer = timedelta(days=self.timing_buffer_days)

        # Get event window from signal
        event_start = intelligence.signal.temporal.earliest_impact
        event_end = intelligence.signal.temporal.latest_resolution

        # Default event window if not specified
        if event_start is None:
            event_start = now
        if event_end is None:
            # If no end specified, assume ongoing for 30 days
            event_end = now + timedelta(days=30)

        # Add buffer for uncertainty
        event_start_with_buffer = event_start - buffer
        event_end_with_buffer = event_end + buffer

        # Check overlap conditions:
        # 1. Shipment arrives AFTER event starts AND
        # 2. Shipment departs BEFORE event ends
        #
        # This catches:
        # - Shipments departing during event
        # - Shipments in transit during event
        # - Shipments arriving during event

        # If shipment arrives before event even starts (with buffer), not affected
        if shipment.eta < event_start_with_buffer:
            return False

        # If shipment departs after event ends (with buffer), not affected
        if shipment.etd > event_end_with_buffer:
            return False

        return True

    def _compute_confidence(
        self,
        affected: list[Shipment],
        intelligence: CorrelatedIntelligence,
        context: CustomerContext,
    ) -> float:
        """
        Compute confidence in exposure match.

        Higher confidence if:
        - We have detailed shipment info (carrier, booking reference)
        - Signal has high correlation with reality
        - Timing is clear and specific

        Args:
            affected: List of affected shipments
            intelligence: Intelligence context
            context: Customer context

        Returns:
            Confidence score 0-1
        """
        if not affected:
            return 0.0

        # Base: Intelligence combined confidence
        base_confidence = intelligence.combined_confidence

        # Factor 1: Shipment detail quality
        detail_scores = []
        for shipment in affected:
            score = 0.6  # Base for having the shipment
            if shipment.carrier_code:
                score += 0.15
            if shipment.booking_reference:
                score += 0.15
            if shipment.vessel_name:
                score += 0.10
            detail_scores.append(min(1.0, score))

        detail_avg = sum(detail_scores) / len(detail_scores)

        # Factor 2: Correlation status
        correlation_boost = {
            "confirmed": 0.15,
            "materializing": 0.10,
            "predicted_not_observed": 0.0,
            "surprise": 0.05,
            "normal": -0.10,
        }
        status_boost = correlation_boost.get(
            intelligence.correlation_status.value,
            0.0,
        )

        # Factor 3: Timing clarity
        timing_score = 0.5  # Base
        temporal = intelligence.signal.temporal
        if temporal.earliest_impact and temporal.latest_resolution:
            timing_score = 0.8  # Clear window
        elif temporal.earliest_impact:
            timing_score = 0.65  # Start known

        # Combine factors
        # 50% intelligence, 25% detail, 15% correlation, 10% timing
        combined = (
            0.50 * base_confidence +
            0.25 * detail_avg +
            0.15 * (0.5 + status_boost) +  # Normalize around 0.5
            0.10 * timing_score
        )

        # Clamp to valid range
        return round(max(0.0, min(0.99, combined)), 2)

    def match_multiple(
        self,
        intelligence: CorrelatedIntelligence,
        contexts: list[CustomerContext],
    ) -> list[ExposureMatch]:
        """
        Match intelligence against multiple customers.

        Args:
            intelligence: Intelligence signal
            contexts: List of customer contexts

        Returns:
            List of ExposureMatch for customers with exposure
        """
        matches = []
        for context in contexts:
            match = self.match(intelligence, context)
            if match.has_exposure:
                matches.append(match)

        logger.info(
            "batch_exposure_matching",
            signal_id=intelligence.signal.signal_id,
            customers_checked=len(contexts),
            customers_with_exposure=len(matches),
        )

        return matches


# ============================================================================
# FACTORY
# ============================================================================


def create_exposure_matcher() -> ExposureMatcher:
    """Create default exposure matcher instance."""
    return ExposureMatcher()
