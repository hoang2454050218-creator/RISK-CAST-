"""Impact Calculator - Calculate financial and time impact.

The ImpactCalculator answers: "How much will this cost in DOLLARS and DAYS?"

NOT vague descriptions like "significant impact" or "major delays".
MUST output specific numbers: "$47,500 expected loss" and "10-14 days delay".

Logic:
1. For each affected shipment:
   - Estimate delay based on chokepoint params
   - Calculate holding cost (0.1% cargo value per day)
   - Calculate reroute cost ($2500/TEU for Red Sea)
   - Check if penalties triggered
2. Aggregate totals
3. Compute severity (LOW <$5K, MEDIUM <$25K, HIGH <$100K, CRITICAL)
"""

from datetime import datetime, timedelta
from typing import Optional

import structlog
from pydantic import BaseModel

from app.oracle.schemas import CorrelatedIntelligence
from app.riskcast.constants import (
    INACTION_ESCALATION,
    Severity,
    get_chokepoint_params,
    get_severity,
)
from app.riskcast.matchers.exposure import ExposureMatch
from app.riskcast.schemas.customer import CustomerContext, Shipment
from app.riskcast.schemas.impact import (
    CostBreakdown,
    DelayEstimate,
    ShipmentImpact,
    TotalImpact,
)

logger = structlog.get_logger(__name__)


# ============================================================================
# IMPACT CALCULATOR
# ============================================================================


class ImpactCalculator:
    """
    Calculates financial and time impact for exposed shipments.

    This is where we turn exposure into DOLLARS and DAYS.

    NOT: "Your shipment may be delayed"
    YES: "Shipment #4521 faces 10-14 day delay, costing $47,500"
    """

    def __init__(
        self,
        default_holding_cost_pct: float = 0.001,  # 0.1% per day
        confidence_discount_factor: float = 0.1,
    ):
        """
        Initialize impact calculator.

        Args:
            default_holding_cost_pct: Default daily holding cost as % of value
            confidence_discount_factor: How much to discount impact for low confidence
        """
        self.default_holding_cost_pct = default_holding_cost_pct
        self.confidence_discount_factor = confidence_discount_factor

    def calculate(
        self,
        exposure: ExposureMatch,
        intelligence: CorrelatedIntelligence,
        context: CustomerContext,
    ) -> TotalImpact:
        """
        Calculate total impact across all affected shipments.

        Args:
            exposure: Exposure match result
            intelligence: Correlated intelligence from ORACLE
            context: Customer context

        Returns:
            TotalImpact with detailed breakdown per shipment
        """
        logger.debug(
            "calculating_impact",
            customer_id=exposure.customer_id,
            signal_id=exposure.signal_id,
            affected_shipments=len(exposure.affected_shipments),
        )

        if not exposure.has_exposure:
            return self._create_empty_impact(exposure)

        # Get chokepoint parameters for cost calculation
        chokepoint = exposure.chokepoint_matched
        params = get_chokepoint_params(chokepoint)

        # Calculate impact per shipment
        shipment_impacts: list[ShipmentImpact] = []
        total_cost = 0.0
        total_penalties = 0.0
        penalty_count = 0

        for shipment in exposure.affected_shipments:
            impact = self._calculate_shipment_impact(
                shipment=shipment,
                chokepoint=chokepoint,
                params=params,
                intelligence=intelligence,
            )
            shipment_impacts.append(impact)
            total_cost += impact.total_impact_usd
            if impact.triggers_penalty:
                penalty_count += 1
                total_penalties += impact.penalty_amount_usd

        # Calculate average expected delay
        if shipment_impacts:
            avg_delay = sum(si.delay.expected_days for si in shipment_impacts) // len(
                shipment_impacts
            )
        else:
            avg_delay = 0

        # Determine overall severity
        severity = get_severity(total_cost)

        # Calculate confidence in assessment
        confidence = self._calculate_confidence(
            exposure=exposure,
            intelligence=intelligence,
            shipment_impacts=shipment_impacts,
        )

        total_impact = TotalImpact(
            customer_id=exposure.customer_id,
            signal_id=exposure.signal_id,
            shipment_impacts=shipment_impacts,
            total_cost_usd=round(total_cost, 2),
            total_delay_days_expected=avg_delay,
            shipments_with_penalties=penalty_count,
            total_penalty_usd=round(total_penalties, 2),
            overall_severity=severity,
            confidence=confidence,
        )

        logger.info(
            "impact_calculated",
            customer_id=exposure.customer_id,
            signal_id=exposure.signal_id,
            total_cost_usd=total_impact.total_cost_usd,
            severity=severity.value,
            affected_shipments=len(shipment_impacts),
            penalty_count=penalty_count,
        )

        return total_impact

    def _calculate_shipment_impact(
        self,
        shipment: Shipment,
        chokepoint: str,
        params: dict,
        intelligence: CorrelatedIntelligence,
    ) -> ShipmentImpact:
        """
        Calculate impact for a single shipment.

        Steps:
        1. Estimate delay (min/max/expected days)
        2. Calculate holding cost
        3. Calculate reroute premium (if applicable)
        4. Check for penalty triggers
        5. Determine severity

        Args:
            shipment: The affected shipment
            chokepoint: Which chokepoint is affected
            params: Chokepoint-specific parameters
            intelligence: Intelligence context

        Returns:
            ShipmentImpact with detailed breakdown
        """
        # 1. DELAY ESTIMATION
        delay = self._estimate_delay(shipment, chokepoint, params, intelligence)

        # 2. COST CALCULATION
        cost = self._calculate_costs(shipment, delay, params)

        # 3. PENALTY ANALYSIS
        triggers_penalty, days_until, penalty_amount = self._analyze_penalty(
            shipment, delay
        )

        # If penalty triggered, add to cost breakdown
        if triggers_penalty:
            cost = CostBreakdown(
                delay_holding_cost_usd=cost.delay_holding_cost_usd,
                reroute_premium_usd=cost.reroute_premium_usd,
                rate_increase_usd=cost.rate_increase_usd,
                penalty_cost_usd=penalty_amount,
            )

        # 4. NEW ETA CALCULATION
        new_eta = shipment.eta + timedelta(days=delay.expected_days)

        # 5. SEVERITY
        severity = get_severity(cost.total_usd)

        return ShipmentImpact(
            shipment_id=shipment.shipment_id,
            shipment_ref=shipment.customer_reference or shipment.shipment_id,
            delay=delay,
            original_eta=shipment.eta,
            new_eta_expected=new_eta,
            cost=cost,
            triggers_penalty=triggers_penalty,
            days_until_penalty=days_until,
            penalty_amount_usd=penalty_amount,
            impact_severity=severity,
        )

    def _estimate_delay(
        self,
        shipment: Shipment,
        chokepoint: str,
        params: dict,
        intelligence: CorrelatedIntelligence,
    ) -> DelayEstimate:
        """
        Estimate delay for a shipment based on chokepoint and signal severity.

        Args:
            shipment: The shipment
            chokepoint: Affected chokepoint
            params: Chokepoint parameters
            intelligence: Intelligence signal

        Returns:
            DelayEstimate with range
        """
        # Get base delay from chokepoint params
        min_delay, max_delay = params.get("reroute_delay_days", (7, 14))

        # Adjust based on signal probability
        signal_prob = intelligence.signal.probability
        # Higher probability = closer to max delay
        # probability 0.9 = 90% towards max, 0.5 = 50% towards max
        expected_days = int(
            min_delay + (max_delay - min_delay) * signal_prob
        )
        expected_days = max(min_delay, min(max_delay, expected_days))

        # Confidence in estimate based on correlation status
        confidence_map = {
            "confirmed": 0.90,
            "materializing": 0.80,
            "predicted_not_observed": 0.60,
            "surprise": 0.50,
            "normal": 0.40,
        }
        confidence = confidence_map.get(
            intelligence.correlation_status.value, 0.60
        )

        return DelayEstimate(
            min_days=min_delay,
            max_days=max_delay,
            expected_days=expected_days,
            confidence=confidence,
        )

    def _calculate_costs(
        self,
        shipment: Shipment,
        delay: DelayEstimate,
        params: dict,
    ) -> CostBreakdown:
        """
        Calculate all costs for a shipment delay.

        Components:
        1. Holding cost = 0.1% of cargo value per day
        2. Reroute premium = cost per TEU * TEU count
        3. Rate increase = market rate increases during delay (future enhancement)

        Args:
            shipment: The shipment
            delay: Estimated delay
            params: Chokepoint parameters

        Returns:
            CostBreakdown with itemized costs
        """
        cargo_value = shipment.cargo_value_usd

        # 1. HOLDING COST
        # 0.1% of cargo value per day of delay
        holding_pct = params.get("holding_cost_per_day_pct", self.default_holding_cost_pct)
        holding_cost = cargo_value * holding_pct * delay.expected_days

        # 2. REROUTE PREMIUM
        # Cost per TEU * number of TEUs
        reroute_per_teu = params.get("reroute_cost_per_teu", 2500.0)
        reroute_cost = reroute_per_teu * shipment.teu_count

        # 3. RATE INCREASE (simplified for MVP)
        # During disruptions, spot rates typically increase 20-50%
        # We estimate this as 10% of reroute cost
        rate_increase = reroute_cost * 0.10

        return CostBreakdown(
            delay_holding_cost_usd=round(holding_cost, 2),
            reroute_premium_usd=round(reroute_cost, 2),
            rate_increase_usd=round(rate_increase, 2),
            penalty_cost_usd=0,  # Set separately if triggered
        )

    def _analyze_penalty(
        self,
        shipment: Shipment,
        delay: DelayEstimate,
    ) -> tuple[bool, Optional[int], float]:
        """
        Analyze if delay triggers contract penalties.

        Args:
            shipment: The shipment
            delay: Estimated delay

        Returns:
            Tuple of (triggers_penalty, days_until_penalty, penalty_amount)
        """
        if not shipment.has_delay_penalty:
            return False, None, 0.0

        # Check if delay exceeds grace period
        # Assume penalty triggers after deadline + grace
        # Penalty amount is in shipment schema
        penalty_deadline = shipment.penalty_deadline
        if penalty_deadline is None:
            return False, None, 0.0

        # How many days until penalty deadline
        now = datetime.utcnow()
        days_until = (penalty_deadline - now).days

        # Will the delay cause us to miss the deadline?
        new_arrival = shipment.eta + timedelta(days=delay.expected_days)
        triggers_penalty = new_arrival > penalty_deadline

        # Calculate penalty amount using shipment's penalty calculation
        if triggers_penalty:
            days_late = (new_arrival - penalty_deadline).days
            # Use shipment's penalty rate
            penalty_per_day = shipment.daily_penalty_usd
            penalty_amount = penalty_per_day * days_late
            # Cap at cargo value (usually contracts cap penalties)
            penalty_amount = min(penalty_amount, shipment.cargo_value_usd * 0.25)
        else:
            penalty_amount = 0.0

        return triggers_penalty, days_until if days_until > 0 else None, round(penalty_amount, 2)

    def _calculate_confidence(
        self,
        exposure: ExposureMatch,
        intelligence: CorrelatedIntelligence,
        shipment_impacts: list[ShipmentImpact],
    ) -> float:
        """
        Calculate confidence in impact assessment.

        Based on:
        - Exposure match confidence
        - Intelligence confidence
        - Delay estimate confidence

        Args:
            exposure: Exposure match
            intelligence: Intelligence context
            shipment_impacts: Calculated impacts

        Returns:
            Confidence score 0-1
        """
        # Start with exposure match confidence
        base = exposure.match_confidence

        # Factor in intelligence confidence
        intel_conf = intelligence.combined_confidence

        # Factor in average delay confidence
        if shipment_impacts:
            delay_conf = sum(si.delay.confidence for si in shipment_impacts) / len(
                shipment_impacts
            )
        else:
            delay_conf = 0.5

        # Weighted average
        # 40% exposure, 40% intelligence, 20% delay estimate
        combined = 0.40 * base + 0.40 * intel_conf + 0.20 * delay_conf

        return round(max(0.0, min(0.99, combined)), 2)

    def _create_empty_impact(self, exposure: ExposureMatch) -> TotalImpact:
        """Create empty impact when no exposure."""
        return TotalImpact(
            customer_id=exposure.customer_id,
            signal_id=exposure.signal_id,
            shipment_impacts=[],
            total_cost_usd=0,
            total_delay_days_expected=0,
            overall_severity=Severity.LOW,
            confidence=0.0,
        )

    def calculate_escalated_costs(
        self,
        base_impact: TotalImpact,
        hours_waited: int,
    ) -> float:
        """
        Calculate escalated cost if customer waits.

        Used for inaction analysis (Q7).

        Args:
            base_impact: Base impact calculation
            hours_waited: Hours of waiting

        Returns:
            Escalated cost in USD
        """
        base_cost = base_impact.total_cost_usd

        # Find applicable escalation factor
        escalation_factor = 1.0
        for hours, factor in sorted(INACTION_ESCALATION.items()):
            if hours_waited >= hours:
                escalation_factor = factor

        return round(base_cost * escalation_factor, 2)


# ============================================================================
# FACTORY
# ============================================================================


def create_impact_calculator() -> ImpactCalculator:
    """Create default impact calculator instance."""
    return ImpactCalculator()
