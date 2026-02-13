"""
Tradeoff Analyzer — cost/benefit analysis comparing actions.

For each action, computes:
- Net value (benefit - cost)
- Risk-adjusted return
- Recommendation ranking
"""

import structlog

from riskcast.decisions.schemas import Action, ActionType, TradeoffAnalysis

logger = structlog.get_logger(__name__)


class TradeoffAnalyzer:
    """Analyze tradeoffs between available actions."""

    def analyze(
        self,
        actions: list[Action],
        inaction_cost: float = 0.0,
    ) -> TradeoffAnalysis:
        """
        Compare all actions and recommend the best one.

        Ranking formula:
          score = net_value × success_probability - (risk_penalty)

        Args:
            actions: Available actions from ActionGenerator
            inaction_cost: Expected cost of doing nothing
        """
        if not actions:
            return TradeoffAnalysis(
                recommended_action=ActionType.MONITOR,
                recommendation_reason="No actions available.",
                actions=[],
                do_nothing_cost=inaction_cost,
                best_net_value=0.0,
                confidence=0.0,
            )

        # Score each action
        scored: list[tuple[float, Action]] = []
        for action in actions:
            risk_adjusted_value = action.net_value * action.success_probability
            # Penalize slow actions (time pressure)
            time_penalty = min(0.1 * action.time_to_execute_hours, 20.0)
            score = risk_adjusted_value - time_penalty
            scored.append((score, action))

        # Sort by score (highest first)
        scored.sort(key=lambda x: x[0], reverse=True)

        best_score, best_action = scored[0]

        # If best action has negative net value and inaction_cost is low, recommend monitoring
        if best_action.net_value <= 0 and inaction_cost < 1000:
            recommended = ActionType.MONITOR
            reason = (
                f"All actions have negative net value. "
                f"Monitoring is recommended (inaction cost: ${inaction_cost:,.0f})."
            )
        else:
            recommended = best_action.action_type
            reason = (
                f"{best_action.action_type.value} is recommended with "
                f"net value ${best_action.net_value:,.0f} "
                f"({best_action.success_probability:.0%} success probability)."
            )

        # Confidence: higher when actions clearly differ
        if len(scored) > 1:
            gap = abs(scored[0][0] - scored[1][0])
            confidence = min(1.0, gap / max(abs(scored[0][0]), 1.0))
        else:
            confidence = 0.5

        return TradeoffAnalysis(
            recommended_action=recommended,
            recommendation_reason=reason,
            actions=actions,
            do_nothing_cost=round(inaction_cost, 2),
            best_net_value=round(best_action.net_value, 2),
            confidence=round(confidence, 4),
        )
