"""
Baseline Strategies for Benchmark Comparison.

Implements various baseline strategies that RISKCAST is compared against.

Purpose:
- Demonstrate RISKCAST value-add over simple alternatives
- Establish upper/lower bounds on performance
- Support A/B testing framework
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from datetime import datetime

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


# ============================================================================
# BASE CLASS
# ============================================================================


class BaselineDecision(BaseModel):
    """Decision output from a baseline strategy."""
    
    action: str = Field(description="Recommended action")
    confidence: float = Field(ge=0, le=1)
    reasoning: str = Field(description="Why this action")
    
    # For evaluation
    would_act: bool = Field(description="Would this baseline recommend action?")


class Baseline(ABC):
    """
    Abstract base class for baseline strategies.
    
    Each baseline implements a simple decision rule that RISKCAST
    is compared against.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Baseline name."""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description."""
        pass
    
    @abstractmethod
    def decide(
        self,
        signal_probability: float,
        signal_confidence: float,
        exposure_usd: float,
        **context: Any,
    ) -> BaselineDecision:
        """
        Make a decision using this baseline strategy.
        
        Args:
            signal_probability: Probability of disruption (0-1)
            signal_confidence: Confidence in signal (0-1)
            exposure_usd: Dollar exposure at risk
            **context: Additional context
            
        Returns:
            BaselineDecision with action and reasoning
        """
        pass


# ============================================================================
# DO NOTHING BASELINE
# ============================================================================


class DoNothingBaseline(Baseline):
    """
    DO_NOTHING: Never recommend action.
    
    This is the lower bound - represents doing nothing and accepting
    whatever happens. Useful to show value of any proactive system.
    
    When this is optimal: When disruptions are rare and action costs
    exceed potential savings.
    """
    
    @property
    def name(self) -> str:
        return "do_nothing"
    
    @property
    def description(self) -> str:
        return "Never recommend action - accept all disruptions"
    
    def decide(
        self,
        signal_probability: float,
        signal_confidence: float,
        exposure_usd: float,
        **context: Any,
    ) -> BaselineDecision:
        return BaselineDecision(
            action="monitor",
            confidence=1.0,  # Very confident in doing nothing
            reasoning="Do-nothing baseline: never recommends action",
            would_act=False,
        )


# ============================================================================
# ALWAYS ACT BASELINE
# ============================================================================


class AlwaysActBaseline(Baseline):
    """
    ALWAYS_ACT: Always recommend action.
    
    This is a conservative strategy - always act regardless of signal.
    Avoids all potential losses but incurs unnecessary costs.
    
    When this is optimal: When action costs are low relative to
    potential losses, or when false negatives are very costly.
    """
    
    def __init__(self, action: str = "reroute"):
        """
        Initialize with default action.
        
        Args:
            action: Action to always recommend
        """
        self._action = action
    
    @property
    def name(self) -> str:
        return "always_act"
    
    @property
    def description(self) -> str:
        return f"Always recommend {self._action} - avoid all risk"
    
    def decide(
        self,
        signal_probability: float,
        signal_confidence: float,
        exposure_usd: float,
        **context: Any,
    ) -> BaselineDecision:
        return BaselineDecision(
            action=self._action,
            confidence=1.0,
            reasoning="Always-act baseline: recommends action regardless of signal",
            would_act=True,
        )


# ============================================================================
# THRESHOLD BASELINE
# ============================================================================


class ThresholdBaseline(Baseline):
    """
    SIMPLE_THRESHOLD: Act if signal probability > threshold.
    
    This is the naive ML baseline - uses only signal probability,
    ignores confidence, exposure, context.
    
    When this is optimal: When signals are well-calibrated and
    all disruptions have similar impact.
    """
    
    def __init__(
        self,
        probability_threshold: float = 0.5,
        action: str = "reroute",
    ):
        """
        Initialize with threshold.
        
        Args:
            probability_threshold: Act if signal > threshold
            action: Action to recommend when acting
        """
        self._threshold = probability_threshold
        self._action = action
    
    @property
    def name(self) -> str:
        return f"threshold_{int(self._threshold * 100)}"
    
    @property
    def description(self) -> str:
        return f"Act if signal probability > {self._threshold:.0%}"
    
    def decide(
        self,
        signal_probability: float,
        signal_confidence: float,
        exposure_usd: float,
        **context: Any,
    ) -> BaselineDecision:
        would_act = signal_probability >= self._threshold
        
        if would_act:
            return BaselineDecision(
                action=self._action,
                confidence=signal_probability,
                reasoning=f"Signal {signal_probability:.0%} >= threshold {self._threshold:.0%}",
                would_act=True,
            )
        else:
            return BaselineDecision(
                action="monitor",
                confidence=1 - signal_probability,
                reasoning=f"Signal {signal_probability:.0%} < threshold {self._threshold:.0%}",
                would_act=False,
            )


# ============================================================================
# EXPECTED VALUE BASELINE
# ============================================================================


class ExpectedValueBaseline(Baseline):
    """
    EXPECTED_VALUE: Act if expected value of action > 0.
    
    More sophisticated than threshold - considers exposure and action cost.
    
    Decision rule:
    - Expected loss = probability * exposure
    - Act if expected loss > action cost
    """
    
    def __init__(
        self,
        default_action_cost_rate: float = 0.05,  # 5% of exposure
    ):
        """
        Initialize expected value baseline.
        
        Args:
            default_action_cost_rate: Default action cost as % of exposure
        """
        self._cost_rate = default_action_cost_rate
    
    @property
    def name(self) -> str:
        return "expected_value"
    
    @property
    def description(self) -> str:
        return "Act if expected loss > action cost"
    
    def decide(
        self,
        signal_probability: float,
        signal_confidence: float,
        exposure_usd: float,
        action_cost_usd: Optional[float] = None,
        **context: Any,
    ) -> BaselineDecision:
        # Calculate expected loss
        expected_loss = signal_probability * exposure_usd
        
        # Action cost
        if action_cost_usd is None:
            action_cost_usd = exposure_usd * self._cost_rate
        
        would_act = expected_loss > action_cost_usd
        
        if would_act:
            return BaselineDecision(
                action="reroute",
                confidence=signal_probability,
                reasoning=f"Expected loss ${expected_loss:,.0f} > action cost ${action_cost_usd:,.0f}",
                would_act=True,
            )
        else:
            return BaselineDecision(
                action="monitor",
                confidence=1 - signal_probability,
                reasoning=f"Expected loss ${expected_loss:,.0f} <= action cost ${action_cost_usd:,.0f}",
                would_act=False,
            )


# ============================================================================
# CONFIDENCE-WEIGHTED BASELINE
# ============================================================================


class ConfidenceWeightedBaseline(Baseline):
    """
    CONFIDENCE_WEIGHTED: Act based on probability * confidence.
    
    Similar to threshold but weights by signal confidence.
    Closer to what RISKCAST actually does, but simpler.
    """
    
    def __init__(
        self,
        threshold: float = 0.45,
    ):
        """
        Initialize confidence-weighted baseline.
        
        Args:
            threshold: Act if (probability * confidence) > threshold
        """
        self._threshold = threshold
    
    @property
    def name(self) -> str:
        return "confidence_weighted"
    
    @property
    def description(self) -> str:
        return f"Act if (probability * confidence) > {self._threshold:.0%}"
    
    def decide(
        self,
        signal_probability: float,
        signal_confidence: float,
        exposure_usd: float,
        **context: Any,
    ) -> BaselineDecision:
        weighted_score = signal_probability * signal_confidence
        would_act = weighted_score >= self._threshold
        
        if would_act:
            return BaselineDecision(
                action="reroute",
                confidence=weighted_score,
                reasoning=f"Weighted score {weighted_score:.0%} >= {self._threshold:.0%}",
                would_act=True,
            )
        else:
            return BaselineDecision(
                action="monitor",
                confidence=1 - weighted_score,
                reasoning=f"Weighted score {weighted_score:.0%} < {self._threshold:.0%}",
                would_act=False,
            )


# ============================================================================
# PERFECT HINDSIGHT BASELINE
# ============================================================================


class PerfectHindsightBaseline(Baseline):
    """
    PERFECT_HINDSIGHT: Optimal decision with full information.
    
    This is the upper bound - represents having a time machine.
    Only acts when disruption actually occurs.
    
    Used to calculate how close RISKCAST is to theoretical optimum.
    """
    
    @property
    def name(self) -> str:
        return "perfect_hindsight"
    
    @property
    def description(self) -> str:
        return "Optimal decision (requires knowing future)"
    
    def decide(
        self,
        signal_probability: float,
        signal_confidence: float,
        exposure_usd: float,
        disruption_actually_occurred: bool = False,
        **context: Any,
    ) -> BaselineDecision:
        """
        NOTE: This baseline requires knowing the outcome.
        Only useful for historical evaluation, not real-time decisions.
        """
        if disruption_actually_occurred:
            return BaselineDecision(
                action="reroute",
                confidence=1.0,
                reasoning="Perfect hindsight: disruption occurred, should act",
                would_act=True,
            )
        else:
            return BaselineDecision(
                action="monitor",
                confidence=1.0,
                reasoning="Perfect hindsight: no disruption, should not act",
                would_act=False,
            )


# ============================================================================
# BASELINE REGISTRY
# ============================================================================


class BaselineRegistry:
    """
    Registry of available baselines.
    
    Use this to get baseline instances for benchmarking.
    """
    
    def __init__(self):
        self._baselines: Dict[str, Baseline] = {
            "do_nothing": DoNothingBaseline(),
            "always_act": AlwaysActBaseline(),
            "threshold_50": ThresholdBaseline(0.5),
            "threshold_30": ThresholdBaseline(0.3),
            "threshold_70": ThresholdBaseline(0.7),
            "expected_value": ExpectedValueBaseline(),
            "confidence_weighted": ConfidenceWeightedBaseline(),
            "perfect_hindsight": PerfectHindsightBaseline(),
        }
    
    def get(self, name: str) -> Optional[Baseline]:
        """Get baseline by name."""
        return self._baselines.get(name)
    
    def list_all(self) -> List[str]:
        """List all available baselines."""
        return list(self._baselines.keys())
    
    def get_core_baselines(self) -> List[Baseline]:
        """Get core baselines for standard benchmarking."""
        return [
            self._baselines["do_nothing"],
            self._baselines["always_act"],
            self._baselines["threshold_50"],
            self._baselines["perfect_hindsight"],
        ]
    
    def register(self, name: str, baseline: Baseline) -> None:
        """Register a custom baseline."""
        self._baselines[name] = baseline


# Global registry
baseline_registry = BaselineRegistry()
