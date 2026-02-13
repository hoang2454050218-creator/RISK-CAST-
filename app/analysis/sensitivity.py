"""
Sensitivity Analysis Framework.

Identifies which inputs have the most impact on decisions.

Key questions answered:
- Which inputs, if changed, would flip the decision?
- How robust is the decision to uncertainty?
- What are the decision boundaries?

Methods:
1. One-at-a-time (OAT): Vary each input while holding others constant
2. Binary search for decision boundaries
3. Robustness scoring

Usage:
    analyzer = SensitivityAnalyzer(decision_function)
    
    robustness = await analyzer.analyze(
        base_inputs={"probability": 0.7, "exposure": 50000},
        input_ranges={"probability": (0, 1), "exposure": (0, 200000)},
    )
    
    print(f"Robustness: {robustness.robustness_score:.0%}")
    print(f"Key driver: {robustness.key_drivers[0].factor_name}")
"""

from datetime import datetime
from typing import Optional, Callable, Any, Tuple
from pydantic import BaseModel, Field
import structlog

logger = structlog.get_logger(__name__)


class SensitivityFactor(BaseModel):
    """Sensitivity of decision to a single factor."""
    
    factor_name: str = Field(description="Name of the input factor")
    current_value: float = Field(description="Current value of the factor")
    decision_boundary: Optional[float] = Field(
        default=None,
        description="Value at which decision flips (None if no boundary in range)"
    )
    headroom: float = Field(
        default=float('inf'),
        description="Distance to boundary as percentage of current value"
    )
    headroom_absolute: float = Field(
        default=float('inf'),
        description="Absolute distance to boundary"
    )
    direction: Optional[str] = Field(
        default=None,
        description="'up' or 'down' - which direction flips decision"
    )
    importance_rank: int = Field(
        default=0,
        description="Rank by importance (1 = most important)"
    )
    is_fragile: bool = Field(
        default=False,
        description="Whether this factor has low headroom (<20%)"
    )


class DecisionRobustness(BaseModel):
    """Overall robustness of a decision."""
    
    robustness_score: float = Field(
        ge=0,
        le=1,
        description="0=very fragile, 1=very robust"
    )
    base_decision: str = Field(description="The current decision")
    base_utility: float = Field(description="Utility of current decision")
    
    key_drivers: list[SensitivityFactor] = Field(
        default_factory=list,
        description="Top 3 factors that most affect the decision"
    )
    fragile_factors: list[SensitivityFactor] = Field(
        default_factory=list,
        description="Factors with headroom < 20%"
    )
    decision_boundaries: dict[str, float] = Field(
        default_factory=dict,
        description="Boundary values for each factor"
    )
    
    recommendation: str = Field(description="Human-readable recommendation")
    confidence_in_analysis: float = Field(
        default=0.8,
        ge=0,
        le=1,
        description="Confidence in the sensitivity analysis itself"
    )


class WhatIfResult(BaseModel):
    """Result of what-if analysis."""
    
    base: dict = Field(description="Base case decision and utility")
    changed: dict = Field(description="Changed case decision and utility")
    decision_changed: bool = Field(description="Whether decision flipped")
    utility_change: float = Field(description="Change in utility")
    utility_change_pct: Optional[float] = Field(
        default=None,
        description="Percentage change in utility"
    )
    changes_applied: dict[str, float] = Field(
        default_factory=dict,
        description="The input changes that were applied"
    )


class SensitivityAnalyzer:
    """
    Analyzes sensitivity of decisions to input changes.
    
    Finds decision boundaries and assesses robustness.
    
    The decision function should take a dict of inputs and return
    a tuple of (action: str, utility: float).
    """
    
    # Headroom thresholds
    FRAGILE_THRESHOLD = 0.20  # 20% headroom is considered fragile
    ROBUST_THRESHOLD = 0.70  # 70%+ average headroom is robust
    
    def __init__(
        self,
        decision_function: Callable[[dict], Tuple[str, float]],
        is_async: bool = True,
    ):
        """
        Initialize analyzer.
        
        Args:
            decision_function: Function that takes inputs dict and returns (action, utility)
                              Can be sync or async
            is_async: Whether decision_function is async
        """
        self._decide = decision_function
        self._is_async = is_async
    
    async def analyze(
        self,
        base_inputs: dict,
        input_ranges: dict[str, Tuple[float, float]],
    ) -> DecisionRobustness:
        """
        Perform sensitivity analysis.
        
        Args:
            base_inputs: Current input values
            input_ranges: Valid range for each input {name: (min, max)}
            
        Returns:
            DecisionRobustness with analysis results
        """
        logger.info(
            "sensitivity_analysis_started",
            input_count=len(base_inputs),
            range_count=len(input_ranges),
        )
        
        # Get base decision
        base_action, base_utility = await self._call_decision(base_inputs)
        
        # Find decision boundaries for each input
        factors = []
        boundaries = {}
        
        for input_name, (min_val, max_val) in input_ranges.items():
            if input_name not in base_inputs:
                continue
                
            current_val = base_inputs[input_name]
            
            # Search for boundary
            boundary = await self._find_boundary(
                base_inputs=base_inputs,
                input_name=input_name,
                current=current_val,
                min_val=min_val,
                max_val=max_val,
                base_action=base_action,
            )
            
            # Calculate headroom
            if boundary is not None:
                boundaries[input_name] = boundary
                
                if boundary > current_val:
                    headroom_abs = boundary - current_val
                    headroom_pct = headroom_abs / current_val if current_val != 0 else float('inf')
                    direction = "up"
                else:
                    headroom_abs = current_val - boundary
                    headroom_pct = headroom_abs / current_val if current_val != 0 else float('inf')
                    direction = "down"
                
                factors.append(SensitivityFactor(
                    factor_name=input_name,
                    current_value=current_val,
                    decision_boundary=boundary,
                    headroom=headroom_pct,
                    headroom_absolute=headroom_abs,
                    direction=direction,
                    importance_rank=0,  # Will be set after sorting
                    is_fragile=headroom_pct < self.FRAGILE_THRESHOLD,
                ))
            else:
                # No boundary found - very robust to this input
                factors.append(SensitivityFactor(
                    factor_name=input_name,
                    current_value=current_val,
                    decision_boundary=None,
                    headroom=float('inf'),
                    headroom_absolute=float('inf'),
                    direction=None,
                    importance_rank=0,
                    is_fragile=False,
                ))
        
        # Rank factors by importance (smallest headroom = most important)
        factors.sort(key=lambda f: f.headroom)
        for i, f in enumerate(factors):
            f.importance_rank = i + 1
        
        # Identify key drivers and fragile factors
        key_drivers = factors[:3] if len(factors) >= 3 else factors
        fragile_factors = [f for f in factors if f.is_fragile]
        
        # Calculate robustness score
        robustness = self._calculate_robustness(factors)
        
        # Generate recommendation
        recommendation = self._generate_recommendation(
            robustness, key_drivers, fragile_factors
        )
        
        logger.info(
            "sensitivity_analysis_complete",
            robustness=robustness,
            fragile_count=len(fragile_factors),
            boundary_count=len(boundaries),
        )
        
        return DecisionRobustness(
            robustness_score=robustness,
            base_decision=base_action,
            base_utility=base_utility,
            key_drivers=key_drivers,
            fragile_factors=fragile_factors,
            decision_boundaries=boundaries,
            recommendation=recommendation,
        )
    
    async def what_if(
        self,
        base_inputs: dict,
        changes: dict[str, float],
    ) -> WhatIfResult:
        """
        Analyze what happens if specific changes occur.
        
        Args:
            base_inputs: Current inputs
            changes: Dict of {input_name: new_value}
            
        Returns:
            Comparison of base vs changed decision
        """
        base_action, base_utility = await self._call_decision(base_inputs)
        
        changed_inputs = base_inputs.copy()
        changed_inputs.update(changes)
        
        new_action, new_utility = await self._call_decision(changed_inputs)
        
        utility_change = new_utility - base_utility
        utility_change_pct = (
            utility_change / base_utility if base_utility != 0 else None
        )
        
        return WhatIfResult(
            base={"action": base_action, "utility": base_utility},
            changed={"action": new_action, "utility": new_utility},
            decision_changed=base_action != new_action,
            utility_change=utility_change,
            utility_change_pct=utility_change_pct,
            changes_applied=changes,
        )
    
    async def find_threshold(
        self,
        base_inputs: dict,
        input_name: str,
        input_range: Tuple[float, float],
        target_action: str,
    ) -> Optional[float]:
        """
        Find the threshold value at which decision becomes target_action.
        
        Args:
            base_inputs: Current inputs
            input_name: Which input to vary
            input_range: (min, max) to search within
            target_action: The action we're looking for
            
        Returns:
            Threshold value, or None if not found
        """
        min_val, max_val = input_range
        
        # Binary search
        tolerance = (max_val - min_val) * 0.01  # 1% tolerance
        
        while max_val - min_val > tolerance:
            mid = (min_val + max_val) / 2
            
            test_inputs = base_inputs.copy()
            test_inputs[input_name] = mid
            
            action, _ = await self._call_decision(test_inputs)
            
            # Check if we found target
            if action == target_action:
                # Found it - narrow down
                max_val = mid
            else:
                min_val = mid
        
        # Verify final threshold
        test_inputs = base_inputs.copy()
        test_inputs[input_name] = (min_val + max_val) / 2
        action, _ = await self._call_decision(test_inputs)
        
        if action == target_action:
            return (min_val + max_val) / 2
        return None
    
    async def _call_decision(self, inputs: dict) -> Tuple[str, float]:
        """Call decision function (handles sync/async)."""
        if self._is_async:
            return await self._decide(inputs)
        else:
            return self._decide(inputs)
    
    async def _find_boundary(
        self,
        base_inputs: dict,
        input_name: str,
        current: float,
        min_val: float,
        max_val: float,
        base_action: str,
        tolerance: float = 0.01,
    ) -> Optional[float]:
        """
        Binary search for decision boundary.
        
        Returns the value at which decision changes, or None if no boundary in range.
        """
        # Check if extremes have same decision
        test_inputs = base_inputs.copy()
        
        test_inputs[input_name] = min_val
        min_action, _ = await self._call_decision(test_inputs)
        
        test_inputs[input_name] = max_val
        max_action, _ = await self._call_decision(test_inputs)
        
        # If same action at both extremes and same as base, no boundary
        if min_action == max_action == base_action:
            return None
        
        # Determine search direction
        if min_action != base_action:
            # Boundary is between min and current
            low, high = min_val, current
        else:
            # Boundary is between current and max
            low, high = current, max_val
        
        # Binary search
        abs_tolerance = tolerance * abs(current if current != 0 else 1)
        
        while high - low > abs_tolerance:
            mid = (low + high) / 2
            test_inputs[input_name] = mid
            mid_action, _ = await self._call_decision(test_inputs)
            
            if mid_action == base_action:
                if min_action != base_action:
                    high = mid
                else:
                    low = mid
            else:
                if min_action != base_action:
                    low = mid
                else:
                    high = mid
        
        return (low + high) / 2
    
    def _calculate_robustness(self, factors: list[SensitivityFactor]) -> float:
        """Calculate overall robustness score."""
        if not factors:
            return 1.0
        
        # Filter to factors with boundaries (meaningful sensitivity)
        bounded_factors = [f for f in factors if f.decision_boundary is not None]
        
        if not bounded_factors:
            return 1.0  # No boundaries = completely robust
        
        # Calculate average headroom (capped at 1.0 for inf values)
        headrooms = [min(f.headroom, 1.0) for f in bounded_factors]
        avg_headroom = sum(headrooms) / len(headrooms)
        
        # Penalize for fragile factors
        fragile_count = sum(1 for f in bounded_factors if f.is_fragile)
        fragile_penalty = fragile_count * 0.1
        
        robustness = max(0, min(1, avg_headroom - fragile_penalty))
        
        return robustness
    
    def _generate_recommendation(
        self,
        robustness: float,
        key_drivers: list[SensitivityFactor],
        fragile_factors: list[SensitivityFactor],
    ) -> str:
        """Generate human-readable recommendation."""
        if robustness >= self.ROBUST_THRESHOLD:
            return "Decision is robust. Safe to proceed."
        
        if not fragile_factors:
            if key_drivers:
                return f"Decision is moderately sensitive to {key_drivers[0].factor_name}. Monitor closely."
            return "Decision has moderate sensitivity. Proceed with monitoring."
        
        fragile_names = [f.factor_name for f in fragile_factors[:3]]
        
        if robustness < 0.3:
            return (
                f"Decision is fragile. Small changes in {', '.join(fragile_names)} "
                f"could flip decision. Strongly recommend human review."
            )
        elif robustness < 0.5:
            return (
                f"Decision is sensitive to {', '.join(fragile_names)}. "
                f"Consider human review for high-value decisions."
            )
        else:
            return (
                f"Decision is moderately robust but watch {fragile_names[0]}. "
                f"Only {fragile_factors[0].headroom:.0%} headroom."
            )


# ============================================================================
# FACTORY
# ============================================================================


def create_sensitivity_analyzer(
    decision_function: Callable[[dict], Tuple[str, float]],
    is_async: bool = True,
) -> SensitivityAnalyzer:
    """
    Factory function to create SensitivityAnalyzer.
    
    Args:
        decision_function: Function that takes inputs and returns (action, utility)
        is_async: Whether the decision function is async
        
    Returns:
        Configured SensitivityAnalyzer
    """
    return SensitivityAnalyzer(
        decision_function=decision_function,
        is_async=is_async,
    )
