"""
Layer 4: Counterfactual Reasoning.

Responsibilities:
- Generate alternative scenarios
- Perform regret analysis
- Find robust actions
- Calculate decision boundaries

This layer answers: "What if I recommended differently?"
"""

from datetime import datetime
from typing import Any, Optional
import structlog

from app.reasoning.schemas import (
    ReasoningLayer,
    CounterfactualLayerOutput,
    Scenario,
)

logger = structlog.get_logger(__name__)


class CounterfactualLayer:
    """
    Layer 4: Counterfactual Reasoning.
    
    Analyzes alternative futures:
    - What if the event doesn't happen?
    - What if it's worse than expected?
    - What if it's better?
    
    Uses scenario analysis and regret minimization.
    """
    
    # Standard action types
    ACTIONS = ["reroute", "delay", "insure", "monitor", "do_nothing"]
    
    # Scenario templates
    SCENARIO_TEMPLATES = {
        "base": {
            "name": "Base Case",
            "description": "Most likely scenario based on current evidence",
            "probability_factor": 1.0,
        },
        "optimistic": {
            "name": "Optimistic",
            "description": "Situation resolves faster than expected",
            "probability_factor": 0.7,  # Impact reduced by 30%
        },
        "pessimistic": {
            "name": "Pessimistic",
            "description": "Situation worse than expected",
            "probability_factor": 1.5,  # Impact 50% worse
        },
        "tail": {
            "name": "Tail Risk",
            "description": "Extreme scenario, low probability",
            "probability_factor": 2.5,  # Impact 150% worse
        },
        "non_event": {
            "name": "Non-Event",
            "description": "Predicted event does not occur",
            "probability_factor": 0.0,  # No impact
        },
    }
    
    async def execute(self, inputs: dict) -> CounterfactualLayerOutput:
        """
        Execute counterfactual reasoning layer.
        
        Args:
            inputs: Dict with 'factual', 'temporal', 'causal', 'context'
        """
        factual = inputs.get("factual")
        temporal = inputs.get("temporal")
        causal = inputs.get("causal")
        context = inputs.get("context")
        
        started_at = datetime.utcnow()
        
        # Get base probability from factual layer
        base_probability = self._get_base_probability(factual)
        
        # Generate scenarios
        scenarios = self._generate_scenarios(base_probability, factual, causal)
        
        # Build regret matrix
        regret_matrix = self._build_regret_matrix(scenarios, context)
        
        # Find robust action
        robust_action, robustness_score = self._find_robust_action(
            regret_matrix, scenarios
        )
        
        # Calculate decision boundaries
        decision_boundaries = self._calculate_boundaries(
            scenarios, regret_matrix, factual
        )
        
        # Find minimax regret action
        minimax_action = self._find_minimax_action(regret_matrix)
        
        completed_at = datetime.utcnow()
        
        # Calculate confidence
        confidence = self._calculate_confidence(scenarios, robustness_score)
        
        # Generate warnings
        warnings = self._generate_warnings(
            robustness_score, regret_matrix, scenarios
        )
        
        output = CounterfactualLayerOutput(
            layer=ReasoningLayer.COUNTERFACTUAL,
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=int((completed_at - started_at).total_seconds() * 1000),
            inputs={
                "base_probability": base_probability,
                "scenario_count": len(scenarios),
            },
            outputs={
                "robust_action": robust_action,
                "robustness_score": robustness_score,
                "boundary_count": len(decision_boundaries),
            },
            confidence=confidence,
            depends_on=[
                ReasoningLayer.FACTUAL,
                ReasoningLayer.TEMPORAL,
                ReasoningLayer.CAUSAL,
            ],
            scenarios=scenarios,
            regret_matrix=regret_matrix,
            robust_action=robust_action,
            robustness_score=robustness_score,
            decision_boundaries=decision_boundaries,
            minimax_regret_action=minimax_action,
            warnings=warnings,
        )
        
        logger.debug(
            "counterfactual_layer_complete",
            scenario_count=len(scenarios),
            robust_action=robust_action,
            robustness_score=robustness_score,
        )
        
        return output
    
    def _get_base_probability(self, factual: Any) -> float:
        """Extract base event probability from factual layer."""
        if not factual:
            return 0.5
        
        for fact in getattr(factual, "verified_facts", []):
            if fact.fact_type == "signal_probability":
                return fact.value
        
        return 0.5
    
    def _generate_scenarios(
        self,
        base_probability: float,
        factual: Any,
        causal: Any,
    ) -> list[Scenario]:
        """Generate alternative scenarios."""
        scenarios = []
        
        # Calculate scenario probabilities
        # Non-event probability = 1 - base_probability
        non_event_prob = 1 - base_probability
        
        # If event occurs, distribute among outcomes
        event_prob = base_probability
        base_share = 0.50
        optimistic_share = 0.20
        pessimistic_share = 0.20
        tail_share = 0.10
        
        scenario_configs = [
            ("non_event", non_event_prob),
            ("base", event_prob * base_share),
            ("optimistic", event_prob * optimistic_share),
            ("pessimistic", event_prob * pessimistic_share),
            ("tail", event_prob * tail_share),
        ]
        
        for scenario_key, probability in scenario_configs:
            template = self.SCENARIO_TEMPLATES[scenario_key]
            
            # Determine best action for this scenario
            best_action = self._best_action_for_scenario(
                scenario_key, template["probability_factor"]
            )
            
            scenarios.append(Scenario(
                name=template["name"],
                description=template["description"],
                probability=probability,
                assumptions=self._get_scenario_assumptions(scenario_key),
                outcomes=self._get_scenario_outcomes(
                    scenario_key, template["probability_factor"]
                ),
                best_action=best_action,
            ))
        
        return scenarios
    
    def _best_action_for_scenario(
        self,
        scenario_key: str,
        impact_factor: float,
    ) -> str:
        """Determine best action for a scenario."""
        if scenario_key == "non_event":
            return "do_nothing"  # If event doesn't happen, do nothing
        elif scenario_key == "optimistic":
            return "monitor"  # Light touch if situation improving
        elif scenario_key in ["pessimistic", "tail"]:
            return "reroute"  # Aggressive action if bad
        else:  # base
            return "reroute"  # Default to protective action
    
    def _get_scenario_assumptions(self, scenario_key: str) -> list[str]:
        """Get key assumptions for each scenario."""
        assumptions_map = {
            "non_event": [
                "Predicted event does not materialize",
                "Normal shipping operations continue",
            ],
            "base": [
                "Event occurs as predicted",
                "Standard mitigation effectiveness",
            ],
            "optimistic": [
                "Event less severe than predicted",
                "Quick resolution",
            ],
            "pessimistic": [
                "Event more severe than predicted",
                "Prolonged duration",
            ],
            "tail": [
                "Extreme disruption scenario",
                "Multiple compounding factors",
            ],
        }
        return assumptions_map.get(scenario_key, [])
    
    def _get_scenario_outcomes(
        self,
        scenario_key: str,
        impact_factor: float,
    ) -> dict:
        """Get expected outcomes for each scenario."""
        # Base outcomes (will be multiplied by factor)
        base_delay = 10  # days
        base_cost = 25000  # USD
        
        return {
            "delay_days": base_delay * impact_factor,
            "cost_impact_usd": base_cost * impact_factor,
            "impact_factor": impact_factor,
        }
    
    def _build_regret_matrix(
        self,
        scenarios: list[Scenario],
        context: Any,
    ) -> dict[str, dict[str, float]]:
        """
        Build regret matrix: action -> scenario -> regret.
        
        Regret = (cost of action + loss under scenario) - (best outcome in scenario)
        """
        matrix = {}
        
        # Action costs (simplified)
        action_costs = {
            "reroute": 8500,
            "delay": 2000,
            "insure": 3000,
            "monitor": 500,
            "do_nothing": 0,
        }
        
        for action in self.ACTIONS:
            matrix[action] = {}
            action_cost = action_costs.get(action, 0)
            
            for scenario in scenarios:
                # Calculate outcome for this action in this scenario
                scenario_loss = scenario.outcomes.get("cost_impact_usd", 0)
                
                # Action effectiveness at mitigating loss
                mitigation = self._action_effectiveness(action, scenario.name)
                mitigated_loss = scenario_loss * (1 - mitigation)
                
                # Total outcome = action cost + mitigated loss
                total_outcome = action_cost + mitigated_loss
                
                # Best possible outcome in this scenario
                best_outcome = min(
                    action_costs.get(scenario.best_action, 0) + 
                    scenario_loss * (1 - self._action_effectiveness(
                        scenario.best_action, scenario.name
                    )),
                    scenario_loss  # Can't be better than just taking the loss
                )
                
                # Regret = our outcome - best possible
                regret = max(0, total_outcome - best_outcome)
                matrix[action][scenario.name] = regret
        
        return matrix
    
    def _action_effectiveness(self, action: str, scenario_name: str) -> float:
        """Get effectiveness of action at mitigating scenario impact."""
        # Effectiveness matrix
        effectiveness = {
            "reroute": {
                "Base Case": 0.85,
                "Optimistic": 0.70,
                "Pessimistic": 0.75,
                "Tail Risk": 0.60,
                "Non-Event": 0.0,  # Unnecessary cost
            },
            "delay": {
                "Base Case": 0.40,
                "Optimistic": 0.60,
                "Pessimistic": 0.30,
                "Tail Risk": 0.20,
                "Non-Event": 0.0,
            },
            "insure": {
                "Base Case": 0.70,
                "Optimistic": 0.70,
                "Pessimistic": 0.70,
                "Tail Risk": 0.80,
                "Non-Event": 0.0,
            },
            "monitor": {
                "Base Case": 0.20,
                "Optimistic": 0.40,
                "Pessimistic": 0.10,
                "Tail Risk": 0.05,
                "Non-Event": 0.0,
            },
            "do_nothing": {
                "Base Case": 0.0,
                "Optimistic": 0.0,
                "Pessimistic": 0.0,
                "Tail Risk": 0.0,
                "Non-Event": 1.0,  # Perfect if nothing happens
            },
        }
        
        return effectiveness.get(action, {}).get(scenario_name, 0.0)
    
    def _find_robust_action(
        self,
        regret_matrix: dict,
        scenarios: list[Scenario],
    ) -> tuple[Optional[str], float]:
        """
        Find action that performs well across all scenarios.
        
        Returns (action, robustness_score)
        """
        # Calculate expected regret for each action
        expected_regrets = {}
        
        scenario_probs = {s.name: s.probability for s in scenarios}
        
        for action, scenario_regrets in regret_matrix.items():
            expected = sum(
                regret * scenario_probs.get(scenario, 0)
                for scenario, regret in scenario_regrets.items()
            )
            expected_regrets[action] = expected
        
        if not expected_regrets:
            return None, 0.0
        
        # Best action has lowest expected regret
        best_action = min(expected_regrets.keys(), key=lambda a: expected_regrets[a])
        min_regret = expected_regrets[best_action]
        
        # Calculate robustness score
        # High score if regret is similar across scenarios
        action_regrets = list(regret_matrix[best_action].values())
        if action_regrets:
            max_regret = max(action_regrets) if action_regrets else 0
            # Robustness = 1 - (variance in regret / max regret)
            if max_regret > 0:
                variance = sum((r - min_regret) ** 2 for r in action_regrets) / len(action_regrets)
                robustness = max(0, 1 - (variance ** 0.5) / max_regret)
            else:
                robustness = 1.0
        else:
            robustness = 0.5
        
        return best_action, min(robustness, 1.0)
    
    def _find_minimax_action(
        self,
        regret_matrix: dict,
    ) -> Optional[str]:
        """Find action that minimizes maximum regret."""
        max_regrets = {}
        
        for action, scenario_regrets in regret_matrix.items():
            max_regrets[action] = max(scenario_regrets.values()) if scenario_regrets else float('inf')
        
        if not max_regrets:
            return None
        
        return min(max_regrets.keys(), key=lambda a: max_regrets[a])
    
    def _calculate_boundaries(
        self,
        scenarios: list[Scenario],
        regret_matrix: dict,
        factual: Any,
    ) -> dict[str, float]:
        """Calculate input values at which decision would flip."""
        boundaries = {}
        
        # Find probability threshold where decision changes
        # Simplified: find probability where do_nothing becomes better than reroute
        reroute_cost = 8500  # Fixed cost
        base_loss = 25000   # Base case loss
        
        # At what probability does expected loss > reroute cost?
        # Expected loss = probability * loss
        # Threshold: p * loss = reroute_cost
        if base_loss > 0:
            prob_threshold = reroute_cost / base_loss
            boundaries["probability"] = min(prob_threshold, 1.0)
        
        # Exposure threshold
        # At what exposure does reroute become worth it?
        # If exposure < reroute_cost, don't reroute
        boundaries["exposure_usd"] = reroute_cost
        
        return boundaries
    
    def _calculate_confidence(
        self,
        scenarios: list[Scenario],
        robustness: float,
    ) -> float:
        """Calculate confidence in counterfactual analysis."""
        # Base confidence from robustness
        confidence = robustness * 0.7
        
        # Bonus for well-distributed scenario probabilities
        probs = [s.probability for s in scenarios]
        if probs:
            # Higher confidence if probabilities sum to ~1
            prob_sum = sum(probs)
            if 0.95 <= prob_sum <= 1.05:
                confidence += 0.2
            elif 0.8 <= prob_sum <= 1.2:
                confidence += 0.1
        
        return min(confidence + 0.1, 1.0)  # Base 0.1
    
    def _generate_warnings(
        self,
        robustness: float,
        regret_matrix: dict,
        scenarios: list[Scenario],
    ) -> list[str]:
        """Generate counterfactual warnings."""
        warnings = []
        
        if robustness < 0.3:
            warnings.append("Decision is highly sensitive to scenario assumptions")
        
        # Check for high regret in any scenario
        for action, scenario_regrets in regret_matrix.items():
            for scenario, regret in scenario_regrets.items():
                if regret > 50000:  # High regret threshold
                    warnings.append(
                        f"High regret (${regret:,.0f}) for {action} in {scenario}"
                    )
                    break
        
        return warnings[:3]  # Limit warnings
