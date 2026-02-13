"""
Tests for Sensitivity Analysis Framework.

Tests cover:
- Decision boundaries found for all key inputs
- Robustness score accurately reflects sensitivity
- Fragile decisions flagged for review
- What-if analysis works correctly
"""

import pytest
from typing import Tuple

from app.analysis.sensitivity import (
    SensitivityFactor,
    DecisionRobustness,
    SensitivityAnalyzer,
    WhatIfResult,
    create_sensitivity_analyzer,
)


# ============================================================================
# MOCK DECISION FUNCTIONS
# ============================================================================


async def simple_decision_function(inputs: dict) -> Tuple[str, float]:
    """
    Simple decision function for testing.
    
    Decision rule:
    - If probability > 0.6 AND exposure > 30000: REROUTE
    - Else: MONITOR
    
    Utility = exposure * probability - action_cost
    """
    probability = inputs.get("probability", 0.5)
    exposure = inputs.get("exposure", 50000)
    
    if probability > 0.6 and exposure > 30000:
        action = "reroute"
        action_cost = 8500
    else:
        action = "monitor"
        action_cost = 500
    
    utility = exposure * probability - action_cost
    
    return action, utility


async def threshold_decision_function(inputs: dict) -> Tuple[str, float]:
    """
    Decision function with clear threshold.
    
    If value > 100: ACTION_A
    Else: ACTION_B
    """
    value = inputs.get("value", 50)
    
    if value > 100:
        return "action_a", value * 2
    else:
        return "action_b", value


async def multi_factor_decision(inputs: dict) -> Tuple[str, float]:
    """
    Decision function with multiple factors.
    
    score = probability * exposure - cost
    If score > 10000: PROCEED
    Else: WAIT
    """
    probability = inputs.get("probability", 0.5)
    exposure = inputs.get("exposure", 50000)
    cost = inputs.get("cost", 5000)
    
    score = probability * exposure - cost
    
    if score > 10000:
        return "proceed", score
    else:
        return "wait", score * 0.5


# ============================================================================
# SENSITIVITY ANALYZER TESTS
# ============================================================================


class TestSensitivityAnalyzer:
    """Tests for SensitivityAnalyzer class."""
    
    @pytest.mark.asyncio
    async def test_finds_decision_boundary(self):
        """Analyzer should find decision boundaries."""
        analyzer = SensitivityAnalyzer(
            decision_function=threshold_decision_function,
            is_async=True,
        )
        
        robustness = await analyzer.analyze(
            base_inputs={"value": 150},  # Currently action_a
            input_ranges={"value": (0, 200)},
        )
        
        # Should find boundary at ~100
        assert "value" in robustness.decision_boundaries
        boundary = robustness.decision_boundaries["value"]
        assert 95 < boundary < 105
    
    @pytest.mark.asyncio
    async def test_calculates_headroom(self):
        """Analyzer should calculate headroom correctly."""
        analyzer = SensitivityAnalyzer(
            decision_function=threshold_decision_function,
            is_async=True,
        )
        
        robustness = await analyzer.analyze(
            base_inputs={"value": 150},  # 50 units above boundary
            input_ranges={"value": (0, 200)},
        )
        
        # Headroom should be ~50/150 = ~33%
        value_factor = next(
            f for f in robustness.key_drivers if f.factor_name == "value"
        )
        assert 0.30 < value_factor.headroom < 0.40
    
    @pytest.mark.asyncio
    async def test_identifies_fragile_factors(self):
        """Analyzer should identify fragile factors."""
        analyzer = SensitivityAnalyzer(
            decision_function=threshold_decision_function,
            is_async=True,
        )
        
        # Value close to boundary (110, boundary at 100)
        robustness = await analyzer.analyze(
            base_inputs={"value": 110},  # Only 10% headroom
            input_ranges={"value": (0, 200)},
        )
        
        # Should be flagged as fragile
        assert len(robustness.fragile_factors) > 0
        assert robustness.fragile_factors[0].factor_name == "value"
    
    @pytest.mark.asyncio
    async def test_robustness_score_reflects_sensitivity(self):
        """Robustness score should be lower when close to boundary."""
        analyzer = SensitivityAnalyzer(
            decision_function=threshold_decision_function,
            is_async=True,
        )
        
        # Far from boundary
        far_result = await analyzer.analyze(
            base_inputs={"value": 180},
            input_ranges={"value": (0, 200)},
        )
        
        # Close to boundary
        close_result = await analyzer.analyze(
            base_inputs={"value": 105},
            input_ranges={"value": (0, 200)},
        )
        
        assert far_result.robustness_score > close_result.robustness_score
    
    @pytest.mark.asyncio
    async def test_no_boundary_when_always_same_decision(self):
        """Should report no boundary when decision is same across range."""
        async def always_same(inputs: dict) -> Tuple[str, float]:
            return "always", inputs.get("value", 0)
        
        analyzer = SensitivityAnalyzer(
            decision_function=always_same,
            is_async=True,
        )
        
        robustness = await analyzer.analyze(
            base_inputs={"value": 50},
            input_ranges={"value": (0, 100)},
        )
        
        # No boundaries should be found
        assert len(robustness.decision_boundaries) == 0
        assert robustness.robustness_score == 1.0
    
    @pytest.mark.asyncio
    async def test_multiple_inputs(self):
        """Analyzer should handle multiple inputs."""
        analyzer = SensitivityAnalyzer(
            decision_function=simple_decision_function,
            is_async=True,
        )
        
        robustness = await analyzer.analyze(
            base_inputs={"probability": 0.75, "exposure": 50000},
            input_ranges={
                "probability": (0, 1),
                "exposure": (0, 100000),
            },
        )
        
        # Should analyze both inputs
        assert len(robustness.key_drivers) >= 2
        
        # Should find boundaries
        factor_names = [f.factor_name for f in robustness.key_drivers]
        assert "probability" in factor_names or "exposure" in factor_names
    
    @pytest.mark.asyncio
    async def test_generates_recommendation(self):
        """Analyzer should generate human-readable recommendation."""
        analyzer = SensitivityAnalyzer(
            decision_function=threshold_decision_function,
            is_async=True,
        )
        
        robustness = await analyzer.analyze(
            base_inputs={"value": 150},
            input_ranges={"value": (0, 200)},
        )
        
        assert robustness.recommendation is not None
        assert len(robustness.recommendation) > 10


# ============================================================================
# WHAT-IF ANALYSIS TESTS
# ============================================================================


class TestWhatIfAnalysis:
    """Tests for what-if analysis."""
    
    @pytest.mark.asyncio
    async def test_what_if_detects_decision_change(self):
        """What-if should detect when decision changes."""
        analyzer = SensitivityAnalyzer(
            decision_function=threshold_decision_function,
            is_async=True,
        )
        
        result = await analyzer.what_if(
            base_inputs={"value": 150},  # action_a
            changes={"value": 50},       # Should become action_b
        )
        
        assert result.decision_changed is True
        assert result.base["action"] == "action_a"
        assert result.changed["action"] == "action_b"
    
    @pytest.mark.asyncio
    async def test_what_if_no_change(self):
        """What-if should correctly report no change."""
        analyzer = SensitivityAnalyzer(
            decision_function=threshold_decision_function,
            is_async=True,
        )
        
        result = await analyzer.what_if(
            base_inputs={"value": 150},  # action_a
            changes={"value": 180},      # Still action_a
        )
        
        assert result.decision_changed is False
    
    @pytest.mark.asyncio
    async def test_what_if_utility_change(self):
        """What-if should calculate utility change."""
        analyzer = SensitivityAnalyzer(
            decision_function=threshold_decision_function,
            is_async=True,
        )
        
        result = await analyzer.what_if(
            base_inputs={"value": 150},
            changes={"value": 200},
        )
        
        # Utility at 150: 300, Utility at 200: 400
        assert result.utility_change > 0
        assert result.changed["utility"] > result.base["utility"]


# ============================================================================
# THRESHOLD FINDING TESTS
# ============================================================================


class TestThresholdFinding:
    """Tests for finding specific thresholds."""
    
    @pytest.mark.asyncio
    async def test_find_threshold(self):
        """Should find threshold for specific action."""
        analyzer = SensitivityAnalyzer(
            decision_function=threshold_decision_function,
            is_async=True,
        )
        
        # Find threshold where decision becomes action_a
        threshold = await analyzer.find_threshold(
            base_inputs={"value": 50},  # Currently action_b
            input_name="value",
            input_range=(0, 200),
            target_action="action_a",
        )
        
        # Should find ~100
        assert threshold is not None
        assert 95 < threshold < 110


# ============================================================================
# SCHEMA TESTS
# ============================================================================


class TestSchemas:
    """Tests for sensitivity analysis schemas."""
    
    def test_sensitivity_factor_fields(self):
        """SensitivityFactor should have all required fields."""
        factor = SensitivityFactor(
            factor_name="probability",
            current_value=0.75,
            decision_boundary=0.60,
            headroom=0.25,
            headroom_absolute=0.15,
            direction="down",
            importance_rank=1,
            is_fragile=False,
        )
        
        assert factor.factor_name == "probability"
        assert factor.decision_boundary == 0.60
        assert factor.direction == "down"
    
    def test_decision_robustness_fields(self):
        """DecisionRobustness should have all required fields."""
        robustness = DecisionRobustness(
            robustness_score=0.75,
            base_decision="reroute",
            base_utility=15000,
            key_drivers=[],
            fragile_factors=[],
            decision_boundaries={},
            recommendation="Decision is robust.",
        )
        
        assert robustness.robustness_score == 0.75
        assert robustness.base_decision == "reroute"
    
    def test_what_if_result_fields(self):
        """WhatIfResult should have all required fields."""
        result = WhatIfResult(
            base={"action": "reroute", "utility": 15000},
            changed={"action": "monitor", "utility": 10000},
            decision_changed=True,
            utility_change=-5000,
            utility_change_pct=-0.333,
            changes_applied={"probability": 0.4},
        )
        
        assert result.decision_changed is True
        assert result.utility_change == -5000


# ============================================================================
# FACTORY TESTS
# ============================================================================


class TestFactory:
    """Tests for factory functions."""
    
    def test_create_analyzer(self):
        """Should create analyzer with provided function."""
        async def dummy(inputs):
            return "action", 0
        
        analyzer = create_sensitivity_analyzer(dummy, is_async=True)
        
        assert analyzer is not None
        assert analyzer._is_async is True


# ============================================================================
# EDGE CASE TESTS
# ============================================================================


class TestEdgeCases:
    """Tests for edge cases."""
    
    @pytest.mark.asyncio
    async def test_zero_current_value(self):
        """Should handle zero current value without division error."""
        async def decision(inputs: dict) -> Tuple[str, float]:
            if inputs.get("value", 0) > 0:
                return "positive", inputs["value"]
            return "zero", 0
        
        analyzer = SensitivityAnalyzer(decision, is_async=True)
        
        # Should not raise division by zero
        robustness = await analyzer.analyze(
            base_inputs={"value": 0},
            input_ranges={"value": (-10, 10)},
        )
        
        assert robustness is not None
    
    @pytest.mark.asyncio
    async def test_empty_ranges(self):
        """Should handle empty input ranges."""
        analyzer = SensitivityAnalyzer(
            decision_function=simple_decision_function,
            is_async=True,
        )
        
        robustness = await analyzer.analyze(
            base_inputs={"probability": 0.75},
            input_ranges={},  # Empty
        )
        
        assert robustness.robustness_score == 1.0
        assert len(robustness.key_drivers) == 0
    
    @pytest.mark.asyncio
    async def test_input_not_in_base(self):
        """Should skip inputs not in base_inputs."""
        analyzer = SensitivityAnalyzer(
            decision_function=simple_decision_function,
            is_async=True,
        )
        
        robustness = await analyzer.analyze(
            base_inputs={"probability": 0.75},
            input_ranges={
                "probability": (0, 1),
                "nonexistent": (0, 100),  # Not in base_inputs
            },
        )
        
        # Should only analyze probability
        assert len([f for f in robustness.key_drivers if f.decision_boundary is not None]) <= 1
