"""Action Generator - Generate concrete, executable actions.

The ActionGenerator answers: "What are the possible actions?"

NOT vague recommendations like "consider alternatives".
MUST be specific: "Reroute shipment #4521 via Cape with MSC. Cost: $8,500. Book by 6PM today."

Types of actions (MVP):
- REROUTE: Change route to avoid disruption
- DELAY: Hold shipment at origin
- INSURE: Buy additional insurance
- MONITOR: Watch but don't act yet
- DO_NOTHING: Accept the risk (baseline)
"""

from datetime import datetime, timedelta
from typing import Optional
import uuid

import structlog

from app.oracle.schemas import CorrelatedIntelligence
from app.riskcast.constants import (
    BOOKING_DEADLINE_HOURS,
    INSURANCE_COVERAGE_PCT,
    INSURANCE_PREMIUM_RATE,
    ActionType,
    RiskTolerance,
    get_best_reroute_carrier,
    get_carrier_info,
    get_chokepoint_params,
)
from app.riskcast.matchers.exposure import ExposureMatch
from app.riskcast.schemas.action import (
    Action,
    ActionFeasibility,
    ActionSet,
)
from app.riskcast.schemas.customer import CustomerContext, Shipment
from app.riskcast.schemas.impact import TotalImpact

logger = structlog.get_logger(__name__)


# ============================================================================
# ACTION GENERATOR
# ============================================================================


class ActionGenerator:
    """
    Generates concrete, executable actions for a decision.

    Every action must be specific enough that the user can
    execute it without additional research.

    NOT: "Consider rerouting"
    YES: "Reroute via Cape with MSC. Cost: $8,500. Book by Feb 5, 6PM UTC."
    """

    def __init__(
        self,
        max_actions: int = 5,
        min_net_benefit: float = -5000,  # Allow some negative-benefit actions
    ):
        """
        Initialize action generator.

        Args:
            max_actions: Maximum number of actions to generate
            min_net_benefit: Minimum net benefit to include action
        """
        self.max_actions = max_actions
        self.min_net_benefit = min_net_benefit

    def generate(
        self,
        exposure: ExposureMatch,
        impact: TotalImpact,
        intelligence: CorrelatedIntelligence,
        context: CustomerContext,
    ) -> ActionSet:
        """
        Generate all possible actions for a decision.

        Args:
            exposure: Exposure match result
            impact: Calculated impact
            intelligence: Intelligence context
            context: Customer context

        Returns:
            ActionSet with ranked actions
        """
        logger.debug(
            "generating_actions",
            customer_id=exposure.customer_id,
            signal_id=exposure.signal_id,
            impact_usd=impact.total_cost_usd,
        )

        actions: list[Action] = []

        # 1. DO_NOTHING (always include as baseline)
        do_nothing = self._generate_do_nothing(exposure, impact)
        actions.append(do_nothing)

        # 2. REROUTE (if feasible)
        reroute = self._generate_reroute(exposure, impact, intelligence, context)
        if reroute:
            actions.append(reroute)

        # 3. DELAY (if feasible)
        delay = self._generate_delay(exposure, impact, intelligence, context)
        if delay:
            actions.append(delay)

        # 4. INSURE (if feasible)
        insure = self._generate_insurance(exposure, impact, context)
        if insure:
            actions.append(insure)

        # 5. MONITOR (if situation is uncertain)
        monitor = self._generate_monitor(exposure, impact, intelligence)
        if monitor:
            actions.append(monitor)

        # Score and rank actions
        actions = self._score_actions(actions, context)
        actions.sort(key=lambda a: a.utility_score, reverse=True)

        # Select primary and alternatives
        primary = actions[0]
        alternatives = actions[1:4]  # Top 3 alternatives

        action_set = ActionSet(
            customer_id=exposure.customer_id,
            signal_id=exposure.signal_id,
            actions=actions,
            primary_action=primary,
            alternatives=alternatives,
            do_nothing_cost=impact.total_cost_usd,
        )

        logger.info(
            "actions_generated",
            customer_id=exposure.customer_id,
            signal_id=exposure.signal_id,
            total_actions=len(actions),
            primary_action=primary.action_type.value,
            primary_cost=primary.cost_usd,
            primary_benefit=primary.risk_mitigated_usd,
        )

        return action_set

    # ========================================================================
    # ACTION GENERATORS
    # ========================================================================

    def _generate_do_nothing(
        self,
        exposure: ExposureMatch,
        impact: TotalImpact,
    ) -> Action:
        """
        Generate DO_NOTHING action as baseline.

        This is the "accept the risk" option that all others
        are compared against.
        """
        return Action(
            action_id=f"act_dn_{uuid.uuid4().hex[:8]}",
            action_type=ActionType.DO_NOTHING,
            summary="Accept the risk and do nothing",
            description=(
                f"Accept potential ${impact.total_cost_usd:,.0f} loss from "
                f"{impact.total_delay_days_expected} day delay affecting "
                f"{impact.shipment_count} shipment(s)."
            ),
            steps=[
                "Monitor signal development",
                "Wait for disruption resolution",
                "Absorb resulting delays and costs",
            ],
            deadline=datetime.utcnow() + timedelta(hours=168),  # 7 days
            deadline_reason="No action required",
            cost_usd=0,
            cost_breakdown={},
            risk_mitigated_usd=0,
            delay_avoided_days=0,
            feasibility=ActionFeasibility.HIGH,
            affected_shipment_ids=[
                si.shipment_id for si in impact.shipment_impacts
            ],
            utility_score=0.1,  # Low baseline score
        )

    def _generate_reroute(
        self,
        exposure: ExposureMatch,
        impact: TotalImpact,
        intelligence: CorrelatedIntelligence,
        context: CustomerContext,
    ) -> Optional[Action]:
        """
        Generate REROUTE action.

        Reroute avoids the disruption by taking an alternative route.
        """
        if not exposure.has_exposure:
            return None

        chokepoint = exposure.chokepoint_matched
        params = get_chokepoint_params(chokepoint)
        alternative_route = params.get("alternative_route", "alternative route")

        # Get best carrier for rerouting
        carrier = get_best_reroute_carrier(chokepoint)

        # Calculate reroute cost
        reroute_per_teu = params.get("reroute_cost_per_teu", 2500.0)
        total_teu = exposure.total_teu
        base_reroute_cost = reroute_per_teu * total_teu

        # Add carrier premium
        carrier_premium = base_reroute_cost * carrier["premium_pct"]
        total_cost = base_reroute_cost + carrier_premium

        # Calculate benefit (risk mitigated)
        # If we reroute, we avoid most of the delay cost
        # But we still pay the reroute premium
        risk_mitigated = impact.total_cost_usd - total_cost
        delay_avoided = impact.total_delay_days_expected

        # Determine deadline (booking window)
        # Use earliest departure minus booking deadline
        if exposure.earliest_impact:
            deadline = exposure.earliest_impact - timedelta(hours=BOOKING_DEADLINE_HOURS)
        else:
            deadline = datetime.utcnow() + timedelta(hours=BOOKING_DEADLINE_HOURS)

        # Check feasibility
        hours_until = (deadline - datetime.utcnow()).total_seconds() / 3600
        if hours_until < 6:
            feasibility = ActionFeasibility.LOW
            feasibility_notes = "Very tight booking window"
        elif hours_until < 24:
            feasibility = ActionFeasibility.MEDIUM
            feasibility_notes = "Limited booking window"
        else:
            feasibility = ActionFeasibility.HIGH
            feasibility_notes = None

        # Build steps
        shipment_refs = impact.get_shipment_refs()
        steps = [
            f"Contact {carrier['name']} ({carrier['contact']}) for capacity",
            f"Request reroute via {alternative_route} for: {', '.join(shipment_refs[:3])}",
            f"Confirm booking by {deadline.strftime('%b %d, %H:%M UTC')}",
            "Update customers on new ETAs",
            "Monitor new route for any issues",
        ]

        return Action(
            action_id=f"act_rr_{uuid.uuid4().hex[:8]}",
            action_type=ActionType.REROUTE,
            summary=f"Reroute {impact.shipment_count} shipment(s) via {alternative_route}",
            description=(
                f"Reroute affected shipments via {alternative_route} with {carrier['name']}. "
                f"Cost: ${total_cost:,.0f}. Avoids {delay_avoided} day delay. "
                f"Book by {deadline.strftime('%b %d, %H:%M UTC')}."
            ),
            steps=steps,
            deadline=deadline,
            deadline_reason=f"Booking window closes {BOOKING_DEADLINE_HOURS}h before departure",
            cost_usd=round(total_cost, 2),
            cost_breakdown={
                "base_reroute": round(base_reroute_cost, 2),
                "carrier_premium": round(carrier_premium, 2),
            },
            risk_mitigated_usd=round(max(0, risk_mitigated), 2),
            delay_avoided_days=delay_avoided,
            feasibility=feasibility,
            feasibility_notes=feasibility_notes,
            recommended_carrier=carrier["code"],
            carrier_name=carrier["name"],
            contact_info=carrier["contact"],
            affected_shipment_ids=[si.shipment_id for si in impact.shipment_impacts],
            utility_score=0.0,  # Will be calculated
        )

    def _generate_delay(
        self,
        exposure: ExposureMatch,
        impact: TotalImpact,
        intelligence: CorrelatedIntelligence,
        context: CustomerContext,
    ) -> Optional[Action]:
        """
        Generate DELAY action.

        Hold shipment at origin until disruption clears.
        Only viable for shipments not yet departed.
        """
        # Filter to only BOOKED (not yet departed) shipments
        booked_shipments = [
            s for s in exposure.affected_shipments
            if s.status.value == "booked"
        ]

        if not booked_shipments:
            return None

        # Calculate delay cost (holding at origin is usually cheaper)
        # Typically 50% of in-transit holding cost
        holding_cost = sum(
            s.cargo_value_usd * 0.0005 * impact.total_delay_days_expected
            for s in booked_shipments
        )

        # Calculate benefit
        # We avoid the delay costs but still have holding costs
        # Benefit is the avoided reroute premium
        reroute_cost = sum(
            get_chokepoint_params(exposure.chokepoint_matched)["reroute_cost_per_teu"]
            * s.teu_count
            for s in booked_shipments
        )
        risk_mitigated = reroute_cost - holding_cost

        # Deadline is the ETD of earliest booked shipment
        earliest_etd = min(s.etd for s in booked_shipments)
        deadline = earliest_etd - timedelta(hours=24)

        # Check feasibility
        hours_until = (deadline - datetime.utcnow()).total_seconds() / 3600
        if hours_until < 12:
            feasibility = ActionFeasibility.LOW
            feasibility_notes = "Very close to departure"
        elif hours_until < 48:
            feasibility = ActionFeasibility.MEDIUM
            feasibility_notes = "Limited time before departure"
        else:
            feasibility = ActionFeasibility.HIGH
            feasibility_notes = None

        shipment_refs = [s.customer_reference or s.shipment_id for s in booked_shipments]

        return Action(
            action_id=f"act_dl_{uuid.uuid4().hex[:8]}",
            action_type=ActionType.DELAY,
            summary=f"Hold {len(booked_shipments)} shipment(s) at origin",
            description=(
                f"Delay departure until disruption clears. "
                f"Holding cost: ${holding_cost:,.0f}. "
                f"Decide by {deadline.strftime('%b %d, %H:%M UTC')}."
            ),
            steps=[
                f"Notify carrier to hold shipments: {', '.join(shipment_refs[:3])}",
                "Request new booking for post-disruption sailing",
                "Update customer ETAs",
                "Monitor signal for resolution timing",
            ],
            deadline=deadline,
            deadline_reason="Must decide before scheduled departure",
            cost_usd=round(holding_cost, 2),
            cost_breakdown={"holding_at_origin": round(holding_cost, 2)},
            risk_mitigated_usd=round(max(0, risk_mitigated), 2),
            delay_avoided_days=0,  # We're accepting the delay
            feasibility=feasibility,
            feasibility_notes=feasibility_notes,
            affected_shipment_ids=[s.shipment_id for s in booked_shipments],
            utility_score=0.0,
        )

    def _generate_insurance(
        self,
        exposure: ExposureMatch,
        impact: TotalImpact,
        context: CustomerContext,
    ) -> Optional[Action]:
        """
        Generate INSURE action.

        Buy additional cargo insurance to transfer risk.
        """
        total_value = exposure.total_exposure_usd

        # Calculate insurance premium
        premium = total_value * INSURANCE_PREMIUM_RATE

        # Calculate coverage
        coverage = impact.total_cost_usd * INSURANCE_COVERAGE_PCT

        # Net benefit = coverage - premium
        risk_mitigated = coverage - premium

        # Insurance can usually be bought up until departure
        if exposure.earliest_impact:
            deadline = exposure.earliest_impact - timedelta(hours=24)
        else:
            deadline = datetime.utcnow() + timedelta(hours=72)

        # Check if worth it
        if risk_mitigated <= 0:
            return None

        return Action(
            action_id=f"act_in_{uuid.uuid4().hex[:8]}",
            action_type=ActionType.INSURE,
            summary=f"Buy insurance for ${coverage:,.0f} coverage",
            description=(
                f"Purchase additional cargo insurance covering "
                f"{INSURANCE_COVERAGE_PCT*100:.0f}% of potential losses. "
                f"Premium: ${premium:,.0f}. Coverage: ${coverage:,.0f}."
            ),
            steps=[
                f"Contact insurance broker for quote on ${total_value:,.0f} cargo value",
                "Specify coverage for delay and disruption losses",
                f"Pay premium of approximately ${premium:,.0f}",
                "Obtain policy documentation before shipment departure",
            ],
            deadline=deadline,
            deadline_reason="Insurance must be in place before departure",
            cost_usd=round(premium, 2),
            cost_breakdown={"insurance_premium": round(premium, 2)},
            risk_mitigated_usd=round(coverage, 2),
            delay_avoided_days=0,  # Insurance doesn't avoid delay
            feasibility=ActionFeasibility.HIGH,
            feasibility_notes="Insurance typically available",
            affected_shipment_ids=[si.shipment_id for si in impact.shipment_impacts],
            utility_score=0.0,
        )

    def _generate_monitor(
        self,
        exposure: ExposureMatch,
        impact: TotalImpact,
        intelligence: CorrelatedIntelligence,
    ) -> Optional[Action]:
        """
        Generate MONITOR action.

        Watch the situation but don't act yet.
        Appropriate when confidence is low or impact is uncertain.
        """
        # Only suggest monitoring if confidence is moderate
        if intelligence.combined_confidence > 0.80:
            return None  # High confidence = act now

        # Monitor for 24-48 hours
        deadline = datetime.utcnow() + timedelta(hours=24)

        return Action(
            action_id=f"act_mn_{uuid.uuid4().hex[:8]}",
            action_type=ActionType.MONITOR,
            summary="Monitor situation for 24 hours",
            description=(
                f"Confidence is {intelligence.combined_confidence*100:.0f}%. "
                f"Watch for developments before committing to action. "
                f"Re-evaluate by {deadline.strftime('%b %d, %H:%M UTC')}."
            ),
            steps=[
                "Set alerts for signal updates",
                "Monitor carrier announcements",
                "Prepare reroute option as backup",
                f"Re-evaluate decision in 24 hours",
            ],
            deadline=deadline,
            deadline_reason="Situation may clarify within 24 hours",
            cost_usd=0,
            cost_breakdown={},
            risk_mitigated_usd=0,
            delay_avoided_days=0,
            feasibility=ActionFeasibility.HIGH,
            feasibility_notes="No commitment required",
            affected_shipment_ids=[si.shipment_id for si in impact.shipment_impacts],
            utility_score=0.0,
        )

    # ========================================================================
    # ACTION SCORING
    # ========================================================================

    def _score_actions(
        self,
        actions: list[Action],
        context: CustomerContext,
    ) -> list[Action]:
        """
        Score actions based on customer preferences and characteristics.

        Scoring factors:
        1. Net benefit (risk mitigated - cost)
        2. Customer risk tolerance
        3. Feasibility
        4. Time to deadline

        Args:
            actions: List of actions to score
            context: Customer context

        Returns:
            Actions with utility_score populated
        """
        scored_actions = []
        risk_tolerance = context.profile.risk_tolerance

        for action in actions:
            score = self._calculate_action_score(action, risk_tolerance)
            # Create new action with updated score
            scored_action = action.model_copy(update={"utility_score": score})
            scored_actions.append(scored_action)

        return scored_actions

    def _calculate_action_score(
        self,
        action: Action,
        risk_tolerance: RiskTolerance,
    ) -> float:
        """
        Calculate utility score for a single action.

        Args:
            action: The action
            risk_tolerance: Customer's risk tolerance

        Returns:
            Score from 0.0 to 1.0
        """
        score = 0.0

        # Factor 1: Net benefit (40% weight)
        # Normalize: negative = 0, >$50K benefit = 1.0
        if action.net_benefit_usd > 0:
            benefit_score = min(1.0, action.net_benefit_usd / 50000)
        else:
            benefit_score = 0.0
        score += 0.40 * benefit_score

        # Factor 2: Feasibility (25% weight)
        feasibility_scores = {
            ActionFeasibility.HIGH: 1.0,
            ActionFeasibility.MEDIUM: 0.6,
            ActionFeasibility.LOW: 0.3,
            ActionFeasibility.IMPOSSIBLE: 0.0,
        }
        score += 0.25 * feasibility_scores.get(action.feasibility, 0.5)

        # Factor 3: Risk tolerance alignment (20% weight)
        tolerance_boost = self._get_tolerance_boost(action, risk_tolerance)
        score += 0.20 * (0.5 + tolerance_boost)

        # Factor 4: Urgency/deadline (15% weight)
        # More time = higher score
        hours = action.hours_until_deadline
        if hours > 48:
            urgency_score = 1.0
        elif hours > 24:
            urgency_score = 0.8
        elif hours > 12:
            urgency_score = 0.6
        elif hours > 6:
            urgency_score = 0.4
        else:
            urgency_score = 0.2
        score += 0.15 * urgency_score

        return round(min(1.0, max(0.0, score)), 3)

    def _get_tolerance_boost(
        self,
        action: Action,
        risk_tolerance: RiskTolerance,
    ) -> float:
        """
        Get score boost/penalty based on risk tolerance alignment.

        Conservative: Prefer risk-reducing actions even at higher cost
        Balanced: Balance cost and risk
        Aggressive: Prefer cost-saving actions

        Returns:
            Score adjustment -0.3 to +0.3
        """
        action_type = action.action_type

        tolerance_preferences = {
            RiskTolerance.CONSERVATIVE: {
                ActionType.REROUTE: 0.3,
                ActionType.INSURE: 0.25,
                ActionType.DELAY: 0.1,
                ActionType.MONITOR: -0.1,
                ActionType.DO_NOTHING: -0.3,
            },
            RiskTolerance.BALANCED: {
                ActionType.REROUTE: 0.15,
                ActionType.INSURE: 0.1,
                ActionType.DELAY: 0.05,
                ActionType.MONITOR: 0.0,
                ActionType.DO_NOTHING: -0.1,
            },
            RiskTolerance.AGGRESSIVE: {
                ActionType.REROUTE: -0.1,
                ActionType.INSURE: -0.2,
                ActionType.DELAY: 0.0,
                ActionType.MONITOR: 0.15,
                ActionType.DO_NOTHING: 0.2,
            },
        }

        return tolerance_preferences.get(risk_tolerance, {}).get(action_type, 0.0)


# ============================================================================
# FACTORY
# ============================================================================


def create_action_generator() -> ActionGenerator:
    """Create default action generator instance."""
    return ActionGenerator()
