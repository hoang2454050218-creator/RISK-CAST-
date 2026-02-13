"""
Action Generator — generates concrete actions from risk assessments.

Each action includes:
- Estimated cost and benefit
- Success probability
- Time to execute
- Requirements and risks
"""

from dataclasses import dataclass
from typing import Optional

import structlog

from riskcast.decisions.schemas import Action, ActionType, SeverityLevel
from riskcast.engine.risk_engine import RiskAssessment

logger = structlog.get_logger(__name__)

# ── Configuration ─────────────────────────────────────────────────────────

REROUTE_BASE_COST_USD: float = 5000.0
INSURANCE_RATE: float = 0.02         # 2% of exposure
HEDGE_RATE: float = 0.015            # 1.5% of exposure
DELAY_COST_PER_DAY_USD: float = 500.0
SPLIT_OVERHEAD_PCT: float = 0.15     # 15% overhead for splitting


class ActionGenerator:
    """Generate concrete actions based on risk assessment."""

    def generate_actions(
        self,
        assessment: RiskAssessment,
        exposure_usd: float = 0.0,
        delivery_days: float = 14.0,
    ) -> list[Action]:
        """
        Generate all viable actions for a risk assessment.

        Args:
            assessment: The risk assessment from the engine
            exposure_usd: Financial exposure in USD
            delivery_days: Expected delivery time in days
        """
        actions: list[Action] = []
        score = assessment.risk_score
        severity = assessment.severity_label

        # Always include monitor-only
        actions.append(self._monitor_action(assessment))

        if score >= 25:
            actions.append(self._insure_action(exposure_usd, score))

        if score >= 40:
            actions.append(self._reroute_action(exposure_usd, delivery_days, score))
            actions.append(self._hedge_action(exposure_usd, score))

        if score >= 50:
            actions.append(self._delay_action(exposure_usd, delivery_days, score))

        if score >= 60:
            actions.append(self._split_action(exposure_usd, score))

        if score >= 70 or not assessment.is_reliable:
            actions.append(self._escalate_action(assessment))

        # Sort by net value (highest first)
        actions.sort(key=lambda a: a.net_value, reverse=True)
        return actions

    def _monitor_action(self, assessment: RiskAssessment) -> Action:
        return Action(
            action_type=ActionType.MONITOR,
            description="Continue monitoring. No immediate action required.",
            estimated_cost_usd=0.0,
            estimated_benefit_usd=0.0,
            net_value=0.0,
            success_probability=1.0 - (assessment.risk_score / 100),
            time_to_execute_hours=0.0,
            requirements=["Active monitoring dashboard"],
            risks=["Risk may escalate if unaddressed"],
        )

    def _reroute_action(self, exposure: float, days: float, score: float) -> Action:
        cost = REROUTE_BASE_COST_USD + (exposure * 0.01)
        # Benefit: avoid X% of exposure based on risk score
        benefit = exposure * (score / 100) * 0.7
        return Action(
            action_type=ActionType.REROUTE,
            description=f"Reroute shipment via alternative route to avoid disruption.",
            estimated_cost_usd=round(cost, 2),
            estimated_benefit_usd=round(benefit, 2),
            net_value=round(benefit - cost, 2),
            success_probability=round(min(0.95, 0.6 + (score / 200)), 4),
            time_to_execute_hours=round(24 + days * 0.5, 1),
            requirements=["Alternative route available", "Carrier capacity"],
            risks=["New route may have its own risks", "Additional transit time"],
        )

    def _insure_action(self, exposure: float, score: float) -> Action:
        cost = exposure * INSURANCE_RATE
        benefit = exposure * (score / 100) * 0.9
        return Action(
            action_type=ActionType.INSURE,
            description=f"Purchase cargo insurance to cover potential loss.",
            estimated_cost_usd=round(cost, 2),
            estimated_benefit_usd=round(benefit, 2),
            net_value=round(benefit - cost, 2),
            success_probability=0.95,
            time_to_execute_hours=4.0,
            requirements=["Insurance provider available", "Policy terms acceptable"],
            risks=["Claim process may be slow", "Coverage may have exclusions"],
        )

    def _delay_action(self, exposure: float, days: float, score: float) -> Action:
        delay_days = max(1, round(days * 0.3))
        cost = delay_days * DELAY_COST_PER_DAY_USD
        benefit = exposure * (score / 100) * 0.5
        return Action(
            action_type=ActionType.DELAY,
            description=f"Delay shipment by {delay_days} days to wait for conditions to improve.",
            estimated_cost_usd=round(cost, 2),
            estimated_benefit_usd=round(benefit, 2),
            net_value=round(benefit - cost, 2),
            success_probability=round(0.4 + (score / 200), 4),
            time_to_execute_hours=0.0,
            deadline=None,
            requirements=["Customer agrees to delay", "Storage available"],
            risks=["Customer dissatisfaction", "Conditions may not improve"],
        )

    def _hedge_action(self, exposure: float, score: float) -> Action:
        cost = exposure * HEDGE_RATE
        benefit = exposure * (score / 100) * 0.6
        return Action(
            action_type=ActionType.HEDGE,
            description=f"Hedge financial exposure via forward contracts or options.",
            estimated_cost_usd=round(cost, 2),
            estimated_benefit_usd=round(benefit, 2),
            net_value=round(benefit - cost, 2),
            success_probability=0.85,
            time_to_execute_hours=8.0,
            requirements=["Treasury approval", "Hedging instrument available"],
            risks=["Basis risk", "Mark-to-market volatility"],
        )

    def _split_action(self, exposure: float, score: float) -> Action:
        cost = exposure * SPLIT_OVERHEAD_PCT
        benefit = exposure * (score / 100) * 0.8
        return Action(
            action_type=ActionType.SPLIT,
            description="Split shipment across multiple routes/carriers to diversify risk.",
            estimated_cost_usd=round(cost, 2),
            estimated_benefit_usd=round(benefit, 2),
            net_value=round(benefit - cost, 2),
            success_probability=0.80,
            time_to_execute_hours=48.0,
            requirements=["Multiple carriers available", "Goods are splittable"],
            risks=["Coordination complexity", "Higher logistics cost"],
        )

    def _escalate_action(self, assessment: RiskAssessment) -> Action:
        return Action(
            action_type=ActionType.ESCALATE,
            description="Escalate to human decision-maker for manual review.",
            estimated_cost_usd=0.0,
            estimated_benefit_usd=0.0,
            net_value=0.0,
            success_probability=0.90,
            time_to_execute_hours=2.0,
            requirements=["Available reviewer", "Decision authority"],
            risks=["Response time delay"],
        )
