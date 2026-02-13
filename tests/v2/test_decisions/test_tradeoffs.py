"""
Tradeoff Analyzer Tests.
"""

import pytest

from riskcast.decisions.schemas import Action, ActionType
from riskcast.decisions.tradeoffs import TradeoffAnalyzer


def _action(atype: ActionType, net: float, prob: float = 0.8, hours: float = 4) -> Action:
    return Action(
        action_type=atype,
        description=f"Test {atype.value}",
        estimated_cost_usd=100,
        estimated_benefit_usd=100 + net,
        net_value=net,
        success_probability=prob,
        time_to_execute_hours=hours,
    )


class TestTradeoffAnalyzer:
    def setup_method(self):
        self.analyzer = TradeoffAnalyzer()

    def test_empty_actions(self):
        result = self.analyzer.analyze([])
        assert result.recommended_action == ActionType.MONITOR

    def test_single_positive_action(self):
        actions = [_action(ActionType.INSURE, 5000)]
        result = self.analyzer.analyze(actions, inaction_cost=10000)
        assert result.recommended_action == ActionType.INSURE

    def test_best_net_value_wins(self):
        actions = [
            _action(ActionType.INSURE, 5000, prob=0.9),
            _action(ActionType.REROUTE, 8000, prob=0.8),
        ]
        result = self.analyzer.analyze(actions, inaction_cost=10000)
        # Reroute has higher net_value × prob = 6400 vs 4500
        assert result.recommended_action == ActionType.REROUTE

    def test_negative_net_recommends_monitor(self):
        actions = [
            _action(ActionType.MONITOR, 0),
            _action(ActionType.INSURE, -500),
        ]
        result = self.analyzer.analyze(actions, inaction_cost=100)
        assert result.recommended_action == ActionType.MONITOR

    def test_do_nothing_cost_tracked(self):
        actions = [_action(ActionType.INSURE, 5000)]
        result = self.analyzer.analyze(actions, inaction_cost=50000)
        assert result.do_nothing_cost == 50000

    def test_recommendation_reason_present(self):
        actions = [_action(ActionType.INSURE, 5000)]
        result = self.analyzer.analyze(actions, inaction_cost=10000)
        assert len(result.recommendation_reason) > 0

    def test_time_penalty_favors_fast_actions(self):
        fast = _action(ActionType.INSURE, 5000, prob=0.8, hours=1)
        slow = _action(ActionType.REROUTE, 5000, prob=0.8, hours=72)
        result = self.analyzer.analyze([fast, slow], inaction_cost=10000)
        # Fast should be preferred (same net_value but less time penalty)
        assert result.recommended_action == ActionType.INSURE

    def test_confidence_higher_with_clear_winner(self):
        """Clear winner → higher confidence."""
        clear = self.analyzer.analyze([
            _action(ActionType.INSURE, 50000, prob=0.95),
            _action(ActionType.REROUTE, 100, prob=0.5),
        ], inaction_cost=100000)

        close = self.analyzer.analyze([
            _action(ActionType.INSURE, 5000, prob=0.8),
            _action(ActionType.REROUTE, 4900, prob=0.8),
        ], inaction_cost=100000)

        assert clear.confidence > close.confidence
