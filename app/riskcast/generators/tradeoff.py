"""Trade-off Analyzer - Analyze action trade-offs and inaction consequences.

The TradeOffAnalyzer answers: "What if I don't act?"

NOT vague warnings like "risk increases over time".
MUST be specific: "If wait 6h: +$15K. If wait 24h: booking closes. Total loss: $47K."

This module:
1. Compares all generated actions
2. Analyzes cost escalation over time
3. Identifies key deadlines
4. Provides urgency assessment
"""

from datetime import datetime, timedelta
from typing import Optional

import structlog

from app.oracle.schemas import CorrelatedIntelligence
from app.riskcast.constants import INACTION_ESCALATION
from app.riskcast.matchers.exposure import ExposureMatch
from app.riskcast.schemas.action import (
    Action,
    ActionSet,
    InactionConsequence,
    TimePoint,
    TradeOffAnalysis,
)
from app.riskcast.schemas.impact import TotalImpact

logger = structlog.get_logger(__name__)


# ============================================================================
# TRADE-OFF ANALYZER
# ============================================================================


class TradeOffAnalyzer:
    """
    Analyzes trade-offs between actions and consequences of inaction.

    This is critical for Q7: "What if I don't act?"

    NOT: "Risk increases over time"
    YES: "If wait 6h: +$15K. If wait 24h: booking closes. Total loss: $47K."
    """

    def __init__(
        self,
        escalation_factors: Optional[dict[int, float]] = None,
    ):
        """
        Initialize trade-off analyzer.

        Args:
            escalation_factors: Cost escalation factors by hours waited
        """
        self.escalation_factors = escalation_factors or INACTION_ESCALATION

    def analyze(
        self,
        action_set: ActionSet,
        impact: TotalImpact,
        exposure: ExposureMatch,
        intelligence: CorrelatedIntelligence,
    ) -> TradeOffAnalysis:
        """
        Analyze trade-offs and produce comprehensive analysis.

        Args:
            action_set: Generated actions
            impact: Calculated impact
            exposure: Exposure match
            intelligence: Intelligence context

        Returns:
            TradeOffAnalysis with inaction consequences
        """
        logger.debug(
            "analyzing_tradeoffs",
            customer_id=action_set.customer_id,
            signal_id=action_set.signal_id,
            action_count=len(action_set.actions),
        )

        # 1. Analyze inaction consequences
        inaction = self._analyze_inaction(action_set, impact, exposure)

        # 2. Determine recommended action and reason
        recommended = action_set.primary_action
        reason = self._generate_recommendation_reason(
            recommended, action_set, impact, inaction
        )

        # 3. Calculate urgency
        urgency, time_to_decide = self._calculate_urgency(
            action_set, inaction, intelligence
        )

        # 4. Calculate confidence
        confidence = self._calculate_confidence(impact, intelligence, action_set)

        analysis = TradeOffAnalysis(
            customer_id=action_set.customer_id,
            signal_id=action_set.signal_id,
            actions_compared=[a.action_id for a in action_set.actions],
            recommended_action=recommended.action_id,
            recommended_reason=reason,
            inaction=inaction,
            urgency=urgency,
            time_to_decide=time_to_decide,
            analysis_confidence=confidence,
        )

        logger.info(
            "tradeoffs_analyzed",
            customer_id=action_set.customer_id,
            signal_id=action_set.signal_id,
            urgency=urgency,
            time_to_decide_hours=analysis.time_to_decide_hours,
            recommended_action=recommended.action_type.value,
        )

        return analysis

    def _analyze_inaction(
        self,
        action_set: ActionSet,
        impact: TotalImpact,
        exposure: ExposureMatch,
    ) -> InactionConsequence:
        """
        Analyze what happens if customer does nothing.

        Produces specific, time-based cost projections.

        Args:
            action_set: The action set
            impact: Calculated impact
            exposure: Exposure match

        Returns:
            InactionConsequence with detailed timeline
        """
        base_cost = impact.total_cost_usd

        # Calculate escalated costs at time points
        cost_at_6h = base_cost * self.escalation_factors.get(6, 1.10)
        cost_at_24h = base_cost * self.escalation_factors.get(24, 1.30)
        cost_at_48h = base_cost * self.escalation_factors.get(48, 1.50)

        # Build timeline of key deadlines
        deadlines = self._build_deadline_timeline(action_set, base_cost)

        # Find point of no return (when best option becomes unavailable)
        ponr, ponr_reason = self._find_point_of_no_return(action_set)

        # Calculate worst case
        worst_cost = self._calculate_worst_case(impact, exposure)
        worst_scenario = self._describe_worst_case(impact, exposure)

        return InactionConsequence(
            immediate_cost_usd=round(base_cost, 2),
            cost_at_6h=round(cost_at_6h, 2),
            cost_at_24h=round(cost_at_24h, 2),
            cost_at_48h=round(cost_at_48h, 2),
            deadlines=deadlines,
            point_of_no_return=ponr,
            point_of_no_return_reason=ponr_reason,
            worst_case_cost_usd=round(worst_cost, 2),
            worst_case_scenario=worst_scenario,
        )

    def _build_deadline_timeline(
        self,
        action_set: ActionSet,
        base_cost: float,
    ) -> list[TimePoint]:
        """
        Build timeline of key deadlines and their consequences.

        Args:
            action_set: Available actions
            base_cost: Base inaction cost

        Returns:
            List of TimePoints sorted by time
        """
        now = datetime.utcnow()
        deadlines: list[TimePoint] = []

        # Add deadline for each action
        for action in action_set.actions:
            if action.deadline and action.deadline > now:
                hours_from_now = int(
                    (action.deadline - now).total_seconds() / 3600
                )

                # Calculate cost at this deadline
                escalation = 1.0
                for hours, factor in sorted(self.escalation_factors.items()):
                    if hours_from_now >= hours:
                        escalation = factor

                do_nothing_cost = base_cost * escalation

                deadline = TimePoint(
                    hours_from_now=hours_from_now,
                    timestamp=action.deadline,
                    description=f"Deadline for {action.action_type.value}: {action.summary[:50]}",
                    do_nothing_cost=round(do_nothing_cost, 2),
                    reroute_cost=action.cost_usd if action.action_type.value == "reroute" else 0,
                    what_changes=action.deadline_reason,
                    is_deadline=True,
                    deadline_type=f"{action.action_type.value}_closes",
                )
                deadlines.append(deadline)

        # Add standard time checkpoints (6h, 24h, 48h)
        standard_checkpoints = [
            (6, "6 hours", "Early warning - options still available"),
            (24, "24 hours", "Critical window - some options closing"),
            (48, "48 hours", "Late stage - limited options remaining"),
        ]

        for hours, description, what_changes in standard_checkpoints:
            checkpoint_time = now + timedelta(hours=hours)
            escalation = self.escalation_factors.get(hours, 1.0)

            # Check if this checkpoint is useful (not duplicating an action deadline)
            if not any(
                abs((d.timestamp - checkpoint_time).total_seconds()) < 3600
                for d in deadlines
            ):
                deadlines.append(
                    TimePoint(
                        hours_from_now=hours,
                        timestamp=checkpoint_time,
                        description=description,
                        do_nothing_cost=round(base_cost * escalation, 2),
                        reroute_cost=0,
                        what_changes=what_changes,
                        is_deadline=False,
                    )
                )

        # Sort by time
        deadlines.sort(key=lambda d: d.hours_from_now)

        return deadlines

    def _find_point_of_no_return(
        self,
        action_set: ActionSet,
    ) -> tuple[Optional[datetime], Optional[str]]:
        """
        Find the point after which options become severely limited.

        Typically when the best action's deadline passes.

        Args:
            action_set: Available actions

        Returns:
            Tuple of (timestamp, reason) or (None, None)
        """
        if not action_set.primary_action:
            return None, None

        primary = action_set.primary_action

        # PONR is when primary action becomes unavailable
        ponr = primary.deadline
        reason = (
            f"After this time, {primary.action_type.value} option closes. "
            f"{primary.deadline_reason}"
        )

        return ponr, reason

    def _calculate_worst_case(
        self,
        impact: TotalImpact,
        exposure: ExposureMatch,
    ) -> float:
        """
        Calculate worst case total cost.

        Args:
            impact: Calculated impact
            exposure: Exposure match

        Returns:
            Worst case cost in USD
        """
        # Worst case = base cost * 2 (doubling assumption)
        # Plus any penalties
        worst_cost = impact.total_cost_usd * 2

        # Add full penalty exposure
        if impact.has_penalty_risk:
            worst_cost += impact.total_penalty_usd * 1.5  # Extra penalty margin

        return worst_cost

    def _describe_worst_case(
        self,
        impact: TotalImpact,
        exposure: ExposureMatch,
    ) -> str:
        """
        Generate human-readable worst case description.

        Args:
            impact: Calculated impact
            exposure: Exposure match

        Returns:
            Worst case description (max 200 chars)
        """
        parts = []

        # Describe the delay
        delay = impact.total_delay_days_expected
        if delay > 0:
            parts.append(f"{delay*2}+ day total delay")

        # Describe penalties
        if impact.has_penalty_risk:
            parts.append(f"all {impact.shipments_with_penalties} shipments trigger penalties")

        # Describe cost
        if impact.total_cost_usd > 50000:
            parts.append("significant financial loss")
        else:
            parts.append("unexpected costs")

        # Combine
        description = ", ".join(parts)
        if len(description) > 200:
            description = description[:197] + "..."

        return description.capitalize()

    def _generate_recommendation_reason(
        self,
        recommended: Action,
        action_set: ActionSet,
        impact: TotalImpact,
        inaction: InactionConsequence,
    ) -> str:
        """
        Generate human-readable reason for the recommendation.

        Args:
            recommended: Recommended action
            action_set: All actions
            impact: Impact assessment
            inaction: Inaction consequences

        Returns:
            Recommendation reason (max 300 chars)
        """
        action_type = recommended.action_type.value

        if action_type == "do_nothing":
            return (
                f"Impact is manageable at ${impact.total_cost_usd:,.0f}. "
                f"Active intervention not cost-effective."
            )

        if action_type == "reroute":
            benefit = recommended.net_benefit_usd
            deadline = recommended.deadline.strftime("%b %d %H:%M")
            return (
                f"Rerouting saves ${benefit:,.0f} net benefit. "
                f"Book by {deadline} to secure capacity. "
                f"Waiting increases cost by ${inaction.cost_increase_24h:,.0f} in 24h."
            )

        if action_type == "delay":
            return (
                f"Holding shipments at origin avoids reroute premium. "
                f"Decide before departure time."
            )

        if action_type == "insure":
            coverage = recommended.risk_mitigated_usd
            premium = recommended.cost_usd
            return (
                f"Insurance provides ${coverage:,.0f} coverage for ${premium:,.0f} premium. "
                f"Good protection against worst-case scenario."
            )

        if action_type == "monitor":
            confidence = inaction.immediate_cost_usd / max(1, inaction.worst_case_cost_usd)
            return (
                f"Situation uncertain ({confidence:.0%} confidence). "
                f"Monitor for 24h and reassess. Prepare backup options."
            )

        return f"{action_type.title()} recommended based on cost-benefit analysis."

    def _calculate_urgency(
        self,
        action_set: ActionSet,
        inaction: InactionConsequence,
        intelligence: CorrelatedIntelligence,
    ) -> tuple[str, timedelta]:
        """
        Calculate urgency level and time to decide.

        Args:
            action_set: Available actions
            inaction: Inaction consequences
            intelligence: Intelligence context

        Returns:
            Tuple of (urgency level, time to decide)
        """
        now = datetime.utcnow()

        # Find earliest meaningful deadline
        earliest_deadline = None
        for action in action_set.actions:
            if action.deadline and action.deadline > now:
                if action.action_type.value not in ["monitor", "do_nothing"]:
                    if earliest_deadline is None or action.deadline < earliest_deadline:
                        earliest_deadline = action.deadline

        if earliest_deadline is None:
            # No real deadline, use PONR
            if inaction.point_of_no_return:
                earliest_deadline = inaction.point_of_no_return
            else:
                earliest_deadline = now + timedelta(days=7)

        hours_available = (earliest_deadline - now).total_seconds() / 3600
        time_to_decide = earliest_deadline - now

        # Determine urgency level
        if hours_available <= 6:
            urgency = "IMMEDIATE"
        elif hours_available <= 24:
            urgency = "HOURS"
        elif hours_available <= 72:
            urgency = "DAYS"
        else:
            urgency = "WEEKS"

        # Escalate based on signal probability
        if intelligence.signal.probability > 0.85 and urgency == "DAYS":
            urgency = "HOURS"
        elif intelligence.signal.probability > 0.95 and urgency in ["DAYS", "HOURS"]:
            urgency = "IMMEDIATE"

        return urgency, time_to_decide

    def _calculate_confidence(
        self,
        impact: TotalImpact,
        intelligence: CorrelatedIntelligence,
        action_set: ActionSet,
    ) -> float:
        """
        Calculate confidence in trade-off analysis.

        Args:
            impact: Impact assessment
            intelligence: Intelligence context
            action_set: Generated actions

        Returns:
            Confidence score 0-1
        """
        # Base: impact confidence
        base = impact.confidence

        # Boost if we have good action options
        if action_set.has_profitable_action:
            action_boost = 0.10
        else:
            action_boost = -0.05

        # Boost for intelligence clarity
        intel_boost = (intelligence.combined_confidence - 0.5) * 0.2

        combined = base + action_boost + intel_boost

        return round(max(0.0, min(0.99, combined)), 2)


# ============================================================================
# FACTORY
# ============================================================================


def create_tradeoff_analyzer() -> TradeOffAnalyzer:
    """Create default trade-off analyzer instance."""
    return TradeOffAnalyzer()
