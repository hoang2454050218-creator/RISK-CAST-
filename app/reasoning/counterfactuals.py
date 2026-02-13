"""
Temporal counterfactual analysis for RISKCAST decisions.

This module implements GAP A2.2: Temporal counterfactuals missing.
Analyzes "what if we had decided at a different time?" scenarios.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import structlog

logger = structlog.get_logger(__name__)


class CounterfactualType(str, Enum):
    """Types of counterfactual analysis."""
    EARLIER_ACTION = "earlier_action"     # What if acted earlier?
    LATER_ACTION = "later_action"         # What if waited?
    DIFFERENT_ACTION = "different_action" # What if chose differently?
    NO_ACTION = "no_action"               # What if did nothing?


@dataclass
class TimingScenario:
    """A hypothetical timing scenario for analysis."""
    scenario_id: str
    description: str
    hypothetical_time: datetime
    actual_time: datetime
    time_delta: timedelta
    
    @property
    def is_earlier(self) -> bool:
        return self.hypothetical_time < self.actual_time
    
    @property
    def is_later(self) -> bool:
        return self.hypothetical_time > self.actual_time
    
    @property
    def delta_hours(self) -> float:
        return self.time_delta.total_seconds() / 3600


@dataclass
class CostProjection:
    """Projected costs for a scenario."""
    base_cost_usd: float
    additional_delay_days: float
    rate_change_pct: float
    opportunity_cost_usd: float
    
    @property
    def total_cost_usd(self) -> float:
        return self.base_cost_usd + self.opportunity_cost_usd


@dataclass
class CounterfactualOutcome:
    """Outcome of a counterfactual scenario."""
    scenario: TimingScenario
    actual_outcome: Dict[str, Any]
    hypothetical_outcome: Dict[str, Any]
    cost_difference_usd: float
    delay_difference_days: float
    probability_of_success: float
    confidence: float
    reasoning: str


@dataclass
class TemporalCounterfactualAnalysis:
    """Complete temporal counterfactual analysis."""
    analysis_id: str
    decision_id: str
    created_at: datetime
    actual_decision_time: datetime
    actual_action: str
    actual_outcome: Dict[str, Any]
    
    # Counterfactual scenarios
    scenarios: List[CounterfactualOutcome] = field(default_factory=list)
    
    # Key insights
    optimal_timing: Optional[datetime] = None
    optimal_timing_savings_usd: float = 0.0
    timing_sensitivity: float = 0.0  # 0-1, how sensitive to timing
    
    # Recommendations
    recommendation: str = ""
    lessons_learned: List[str] = field(default_factory=list)


class TemporalCounterfactualEngine:
    """
    Analyzes temporal counterfactuals for decision timing optimization.
    
    Answers: "What if we had made this decision at a different time?"
    """
    
    def __init__(
        self,
        rate_volatility_model: Optional[Any] = None,
        delay_impact_model: Optional[Any] = None,
    ):
        self._rate_model = rate_volatility_model
        self._delay_model = delay_impact_model
        
        # Default parameters for Red Sea scenarios
        self._rate_params = {
            "base_rate_per_teu": 2500,
            "daily_volatility_pct": 2.5,
            "crisis_rate_multiplier": 3.0,
            "recovery_rate_per_day": 0.02,
        }
        
        self._delay_params = {
            "reroute_delay_days": 10,
            "holding_cost_per_day_pct": 0.1,
            "demurrage_rate_usd": 5000,
        }
    
    async def analyze(
        self,
        decision_id: str,
        actual_decision_time: datetime,
        actual_action: str,
        actual_cost_usd: float,
        actual_delay_days: float,
        event_timeline: List[Tuple[datetime, str, Dict[str, Any]]],
        shipment_value_usd: float,
        teu_count: float = 1.0,
    ) -> TemporalCounterfactualAnalysis:
        """
        Perform temporal counterfactual analysis.
        
        Args:
            decision_id: ID of the decision being analyzed
            actual_decision_time: When decision was actually made
            actual_action: What action was taken
            actual_cost_usd: Actual cost incurred
            actual_delay_days: Actual delay incurred
            event_timeline: List of (time, event_type, event_data)
            shipment_value_usd: Value of shipment
            teu_count: Number of TEUs
            
        Returns:
            TemporalCounterfactualAnalysis with scenarios
        """
        import uuid
        
        analysis = TemporalCounterfactualAnalysis(
            analysis_id=f"tcf_{uuid.uuid4().hex[:16]}",
            decision_id=decision_id,
            created_at=datetime.utcnow(),
            actual_decision_time=actual_decision_time,
            actual_action=actual_action,
            actual_outcome={
                "cost_usd": actual_cost_usd,
                "delay_days": actual_delay_days,
            },
        )
        
        # Generate timing scenarios
        scenarios = self._generate_timing_scenarios(
            actual_decision_time,
            event_timeline,
        )
        
        # Analyze each scenario
        for scenario in scenarios:
            outcome = await self._analyze_scenario(
                scenario=scenario,
                actual_action=actual_action,
                actual_cost_usd=actual_cost_usd,
                actual_delay_days=actual_delay_days,
                event_timeline=event_timeline,
                shipment_value_usd=shipment_value_usd,
                teu_count=teu_count,
            )
            analysis.scenarios.append(outcome)
        
        # Find optimal timing
        self._determine_optimal_timing(analysis)
        
        # Generate lessons learned
        self._extract_lessons(analysis)
        
        logger.info(
            "temporal_counterfactual_analysis_completed",
            analysis_id=analysis.analysis_id,
            decision_id=decision_id,
            scenarios_analyzed=len(analysis.scenarios),
            optimal_savings_usd=analysis.optimal_timing_savings_usd,
        )
        
        return analysis
    
    def _generate_timing_scenarios(
        self,
        actual_time: datetime,
        event_timeline: List[Tuple[datetime, str, Dict[str, Any]]],
    ) -> List[TimingScenario]:
        """Generate counterfactual timing scenarios."""
        scenarios = []
        
        # Standard timing offsets to analyze
        offsets = [
            (-48, "48 hours earlier"),
            (-24, "24 hours earlier"),
            (-12, "12 hours earlier"),
            (-6, "6 hours earlier"),
            (6, "6 hours later"),
            (12, "12 hours later"),
            (24, "24 hours later"),
            (48, "48 hours later"),
        ]
        
        for hours, description in offsets:
            hypothetical_time = actual_time + timedelta(hours=hours)
            delta = timedelta(hours=abs(hours))
            
            scenarios.append(TimingScenario(
                scenario_id=f"timing_{abs(hours)}h_{'earlier' if hours < 0 else 'later'}",
                description=description,
                hypothetical_time=hypothetical_time,
                actual_time=actual_time,
                time_delta=delta,
            ))
        
        # Add event-based scenarios
        for event_time, event_type, event_data in event_timeline:
            # Just before this event
            if event_time > actual_time - timedelta(hours=72):
                before_time = event_time - timedelta(hours=1)
                scenarios.append(TimingScenario(
                    scenario_id=f"before_{event_type}",
                    description=f"1 hour before {event_type}",
                    hypothetical_time=before_time,
                    actual_time=actual_time,
                    time_delta=abs(actual_time - before_time),
                ))
        
        return scenarios
    
    async def _analyze_scenario(
        self,
        scenario: TimingScenario,
        actual_action: str,
        actual_cost_usd: float,
        actual_delay_days: float,
        event_timeline: List[Tuple[datetime, str, Dict[str, Any]]],
        shipment_value_usd: float,
        teu_count: float,
    ) -> CounterfactualOutcome:
        """Analyze a single counterfactual scenario."""
        
        # Project costs at hypothetical time
        hypothetical_costs = self._project_costs_at_time(
            scenario.hypothetical_time,
            actual_action,
            event_timeline,
            shipment_value_usd,
            teu_count,
        )
        
        # Calculate differences
        cost_diff = actual_cost_usd - hypothetical_costs.total_cost_usd
        delay_diff = actual_delay_days - hypothetical_costs.additional_delay_days
        
        # Determine probability of success at that time
        success_prob = self._estimate_success_probability(
            scenario,
            event_timeline,
        )
        
        # Generate reasoning
        if scenario.is_earlier:
            if cost_diff > 0:
                reasoning = (
                    f"Acting {scenario.delta_hours:.0f}h earlier would have saved "
                    f"${cost_diff:,.0f} due to lower rates and better availability."
                )
            else:
                reasoning = (
                    f"Acting {scenario.delta_hours:.0f}h earlier would have cost "
                    f"${abs(cost_diff):,.0f} more - the later timing captured "
                    f"rate decreases."
                )
        else:
            if cost_diff < 0:
                reasoning = (
                    f"Waiting {scenario.delta_hours:.0f}h longer would have cost "
                    f"${abs(cost_diff):,.0f} more due to rate increases and "
                    f"capacity constraints."
                )
            else:
                reasoning = (
                    f"Waiting {scenario.delta_hours:.0f}h would have saved "
                    f"${cost_diff:,.0f} as rates stabilized."
                )
        
        # Confidence based on how much we know about that time period
        confidence = self._calculate_confidence(scenario, event_timeline)
        
        return CounterfactualOutcome(
            scenario=scenario,
            actual_outcome={
                "cost_usd": actual_cost_usd,
                "delay_days": actual_delay_days,
            },
            hypothetical_outcome={
                "cost_usd": hypothetical_costs.total_cost_usd,
                "delay_days": hypothetical_costs.additional_delay_days,
                "rate_change_pct": hypothetical_costs.rate_change_pct,
            },
            cost_difference_usd=cost_diff,
            delay_difference_days=delay_diff,
            probability_of_success=success_prob,
            confidence=confidence,
            reasoning=reasoning,
        )
    
    def _project_costs_at_time(
        self,
        hypothetical_time: datetime,
        action: str,
        event_timeline: List[Tuple[datetime, str, Dict[str, Any]]],
        shipment_value_usd: float,
        teu_count: float,
    ) -> CostProjection:
        """Project what costs would have been at a different time."""
        
        # Base cost from parameters
        base_rate = self._rate_params["base_rate_per_teu"] * teu_count
        
        # Find events that affect this time
        active_events = [
            (t, e, d) for t, e, d in event_timeline
            if t <= hypothetical_time
        ]
        
        # Calculate rate modifier based on active events
        rate_multiplier = 1.0
        for event_time, event_type, event_data in active_events:
            if event_type in ["crisis_start", "attack", "closure"]:
                # Rate increases during crisis
                days_since_event = (hypothetical_time - event_time).days
                crisis_factor = self._rate_params["crisis_rate_multiplier"]
                recovery = self._rate_params["recovery_rate_per_day"]
                rate_multiplier = max(
                    1.0,
                    crisis_factor * (1 - recovery * days_since_event)
                )
        
        # Apply rate modifier
        adjusted_rate = base_rate * rate_multiplier
        rate_change_pct = (rate_multiplier - 1) * 100
        
        # Calculate delay based on timing
        additional_delay = 0.0
        if action == "reroute":
            additional_delay = self._delay_params["reroute_delay_days"]
        
        # Opportunity cost from holding
        holding_cost = (
            shipment_value_usd 
            * self._delay_params["holding_cost_per_day_pct"] / 100
            * additional_delay
        )
        
        return CostProjection(
            base_cost_usd=adjusted_rate,
            additional_delay_days=additional_delay,
            rate_change_pct=rate_change_pct,
            opportunity_cost_usd=holding_cost,
        )
    
    def _estimate_success_probability(
        self,
        scenario: TimingScenario,
        event_timeline: List[Tuple[datetime, str, Dict[str, Any]]],
    ) -> float:
        """Estimate probability of successful action at hypothetical time."""
        
        # Base probability decreases further from optimal
        base_prob = 0.85
        
        # Check for blocking events
        for event_time, event_type, event_data in event_timeline:
            if event_type in ["closure", "blockage"]:
                if scenario.hypothetical_time >= event_time:
                    # Action after closure would fail
                    return 0.1
        
        # Timing penalty
        hours_from_actual = scenario.delta_hours
        if hours_from_actual > 24:
            base_prob *= 0.9
        if hours_from_actual > 48:
            base_prob *= 0.8
        
        return base_prob
    
    def _calculate_confidence(
        self,
        scenario: TimingScenario,
        event_timeline: List[Tuple[datetime, str, Dict[str, Any]]],
    ) -> float:
        """Calculate confidence in the counterfactual analysis."""
        
        # Higher confidence for times with more data
        base_confidence = 0.75
        
        # More events = more data = higher confidence
        relevant_events = [
            (t, e, d) for t, e, d in event_timeline
            if abs((t - scenario.hypothetical_time).total_seconds()) < 86400
        ]
        
        if len(relevant_events) > 3:
            base_confidence += 0.1
        
        # Less confidence for far-off scenarios
        if scenario.delta_hours > 48:
            base_confidence -= 0.15
        
        return max(0.3, min(0.95, base_confidence))
    
    def _determine_optimal_timing(
        self,
        analysis: TemporalCounterfactualAnalysis,
    ) -> None:
        """Determine optimal timing from scenarios."""
        
        if not analysis.scenarios:
            return
        
        # Find scenario with best outcome (lowest cost, accounting for success)
        best_scenario = None
        best_value = float('inf')
        
        for outcome in analysis.scenarios:
            # Expected value = cost * (1 + failure_penalty * (1 - success_prob))
            failure_penalty = 0.5  # 50% cost increase if fails
            expected_cost = outcome.hypothetical_outcome["cost_usd"] * (
                1 + failure_penalty * (1 - outcome.probability_of_success)
            )
            
            if expected_cost < best_value:
                best_value = expected_cost
                best_scenario = outcome
        
        if best_scenario and best_scenario.cost_difference_usd > 0:
            analysis.optimal_timing = best_scenario.scenario.hypothetical_time
            analysis.optimal_timing_savings_usd = best_scenario.cost_difference_usd
        
        # Calculate timing sensitivity
        cost_range = max(
            abs(o.cost_difference_usd) for o in analysis.scenarios
        ) if analysis.scenarios else 0
        
        actual_cost = analysis.actual_outcome.get("cost_usd", 1)
        if actual_cost > 0:
            analysis.timing_sensitivity = min(1.0, cost_range / actual_cost)
    
    def _extract_lessons(
        self,
        analysis: TemporalCounterfactualAnalysis,
    ) -> None:
        """Extract lessons learned from counterfactual analysis."""
        
        lessons = []
        
        # Lesson from optimal timing
        if analysis.optimal_timing_savings_usd > 0:
            hours_diff = (
                analysis.actual_decision_time - analysis.optimal_timing
            ).total_seconds() / 3600
            
            if hours_diff > 0:
                lessons.append(
                    f"Acting {abs(hours_diff):.0f}h earlier would have saved "
                    f"${analysis.optimal_timing_savings_usd:,.0f}."
                )
            else:
                lessons.append(
                    f"Waiting {abs(hours_diff):.0f}h would have saved "
                    f"${analysis.optimal_timing_savings_usd:,.0f}."
                )
        
        # Lesson from sensitivity
        if analysis.timing_sensitivity > 0.5:
            lessons.append(
                "This decision was highly time-sensitive. Consider faster "
                "decision protocols for similar situations."
            )
        elif analysis.timing_sensitivity < 0.1:
            lessons.append(
                "This decision had low time sensitivity. Spending more time "
                "on analysis would have been acceptable."
            )
        
        # Lesson from scenarios
        earlier_better = sum(
            1 for o in analysis.scenarios
            if o.scenario.is_earlier and o.cost_difference_usd > 0
        )
        later_better = sum(
            1 for o in analysis.scenarios
            if o.scenario.is_later and o.cost_difference_usd > 0
        )
        
        if earlier_better > later_better:
            lessons.append(
                "Earlier action generally led to better outcomes. "
                "Consider lowering decision thresholds."
            )
        elif later_better > earlier_better:
            lessons.append(
                "Waiting generally led to better outcomes. "
                "Consider gathering more information before acting."
            )
        
        analysis.lessons_learned = lessons
        
        # Generate recommendation
        if analysis.timing_sensitivity > 0.3 and earlier_better > later_better:
            analysis.recommendation = (
                "For similar events, act decisively when early signals emerge. "
                f"Optimal window appears to be within 24h of first alert."
            )
        elif analysis.timing_sensitivity < 0.2:
            analysis.recommendation = (
                "For similar events, timing is less critical. Focus on "
                "gathering complete information rather than speed."
            )
        else:
            analysis.recommendation = (
                "Balance speed with information gathering. Set clear "
                "decision deadlines to avoid analysis paralysis."
            )
