"""
Tests for Bayesian Uncertainty Quantification.

Tests cover:
- All numeric outputs have confidence intervals
- Uncertainty propagates through calculations
- Monte Carlo simulation produces valid results
- CI coverage validation
"""

import pytest
import math

from app.uncertainty.bayesian import (
    Distribution,
    DistributionType,
    UncertainValue,
    BayesianCalculator,
    create_bayesian_calculator,
)


# ============================================================================
# DISTRIBUTION TESTS
# ============================================================================


class TestDistribution:
    """Tests for Distribution class."""
    
    def test_normal_distribution_samples(self):
        """Normal distribution should produce valid samples."""
        dist = Distribution(
            type=DistributionType.NORMAL,
            parameters={"mean": 100, "std": 10}
        )
        
        samples = dist.sample(1000)
        
        assert len(samples) == 1000
        mean = sum(samples) / len(samples)
        # Mean should be close to 100
        assert 95 < mean < 105
    
    def test_beta_distribution_samples(self):
        """Beta distribution should produce samples in [0, 1]."""
        dist = Distribution(
            type=DistributionType.BETA,
            parameters={"alpha": 2, "beta": 5}
        )
        
        samples = dist.sample(1000)
        
        assert all(0 <= s <= 1 for s in samples)
    
    def test_uniform_distribution_samples(self):
        """Uniform distribution should produce samples in range."""
        dist = Distribution(
            type=DistributionType.UNIFORM,
            parameters={"low": 10, "high": 20}
        )
        
        samples = dist.sample(1000)
        
        assert all(10 <= s <= 20 for s in samples)
    
    def test_triangular_distribution_samples(self):
        """Triangular distribution should produce samples in range."""
        dist = Distribution(
            type=DistributionType.TRIANGULAR,
            parameters={"low": 5, "mode": 10, "high": 20}
        )
        
        samples = dist.sample(1000)
        
        assert all(5 <= s <= 20 for s in samples)
    
    def test_point_distribution(self):
        """Point distribution should produce constant value."""
        dist = Distribution(
            type=DistributionType.POINT,
            parameters={"value": 42}
        )
        
        samples = dist.sample(100)
        
        assert all(s == 42 for s in samples)
    
    def test_empirical_distribution(self):
        """Empirical distribution should sample from provided data."""
        original_samples = [1, 2, 3, 4, 5]
        dist = Distribution(
            type=DistributionType.EMPIRICAL,
            parameters={"samples": original_samples}
        )
        
        samples = dist.sample(100)
        
        assert all(s in original_samples for s in samples)
    
    def test_distribution_mean(self):
        """Distribution mean should be calculated correctly."""
        # Normal
        normal = Distribution(
            type=DistributionType.NORMAL,
            parameters={"mean": 50, "std": 10}
        )
        assert normal.mean() == 50
        
        # Uniform
        uniform = Distribution(
            type=DistributionType.UNIFORM,
            parameters={"low": 0, "high": 100}
        )
        assert uniform.mean() == 50
        
        # Triangular
        triangular = Distribution(
            type=DistributionType.TRIANGULAR,
            parameters={"low": 0, "mode": 50, "high": 100}
        )
        assert triangular.mean() == 50
    
    def test_confidence_interval(self):
        """Confidence interval should contain correct proportion of samples."""
        dist = Distribution(
            type=DistributionType.NORMAL,
            parameters={"mean": 100, "std": 10}
        )
        
        ci_90 = dist.confidence_interval(0.90)
        
        # CI should be centered around mean
        assert ci_90[0] < 100 < ci_90[1]
        
        # Width should be approximately 2 * 1.645 * std = ~33
        width = ci_90[1] - ci_90[0]
        assert 25 < width < 40


# ============================================================================
# UNCERTAIN VALUE TESTS
# ============================================================================


class TestUncertainValue:
    """Tests for UncertainValue class."""
    
    def test_from_normal(self):
        """UncertainValue from normal should have correct structure."""
        uv = UncertainValue.from_normal(mean=100, std=10, unit="usd")
        
        assert uv.point_estimate == 100
        assert uv.unit == "usd"
        assert uv.confidence_interval_90[0] < 100 < uv.confidence_interval_90[1]
        assert uv.confidence_interval_95[0] < uv.confidence_interval_90[0]
        assert uv.confidence_interval_95[1] > uv.confidence_interval_90[1]
    
    def test_from_range(self):
        """UncertainValue from range should have correct mean."""
        uv = UncertainValue.from_range(min_val=80, max_val=120)
        
        assert uv.point_estimate == 100  # Midpoint
        # CI should contain the original range
        assert uv.confidence_interval_90[0] <= 85
        assert uv.confidence_interval_90[1] >= 115
    
    def test_from_triangular(self):
        """UncertainValue from triangular should have correct structure."""
        uv = UncertainValue.from_triangular(low=50, mode=100, high=150)
        
        # Mean of triangular is (low + mode + high) / 3
        expected_mean = (50 + 100 + 150) / 3
        assert abs(uv.point_estimate - expected_mean) < 5
    
    def test_from_samples(self):
        """UncertainValue from samples should work correctly."""
        samples = [i for i in range(100)]  # 0-99
        uv = UncertainValue.from_samples(samples)
        
        assert abs(uv.point_estimate - 49.5) < 1  # Mean of 0-99
        assert uv.confidence_interval_90[0] < 10
        assert uv.confidence_interval_90[1] > 90
    
    def test_from_point(self):
        """UncertainValue from point should have zero uncertainty."""
        uv = UncertainValue.from_point(42)
        
        assert uv.point_estimate == 42
        assert uv.confidence_interval_90 == (42, 42)
        assert uv.confidence_interval_95 == (42, 42)
    
    def test_addition(self):
        """Adding uncertain values should propagate uncertainty."""
        uv1 = UncertainValue.from_normal(100, 10)
        uv2 = UncertainValue.from_normal(50, 5)
        
        result = uv1 + uv2
        
        # Mean should add
        assert abs(result.point_estimate - 150) < 1
        
        # CI should be wider than either input
        ci_width = result.confidence_interval_90[1] - result.confidence_interval_90[0]
        uv1_width = uv1.confidence_interval_90[1] - uv1.confidence_interval_90[0]
        assert ci_width > uv1_width
    
    def test_multiplication_by_scalar(self):
        """Multiplying by scalar should scale uncertainty."""
        uv = UncertainValue.from_normal(100, 10)
        
        result = uv * 2
        
        assert abs(result.point_estimate - 200) < 1
        
        # CI should also scale
        assert result.confidence_interval_90[0] < 180
        assert result.confidence_interval_90[1] > 220
    
    def test_multiplication_by_uncertain(self):
        """Multiplying uncertain values should propagate uncertainty."""
        uv1 = UncertainValue.from_normal(100, 10)
        uv2 = UncertainValue.from_normal(2, 0.2)
        
        result = uv1 * uv2
        
        # Mean should be approximately 200
        assert 190 < result.point_estimate < 210
    
    def test_clip(self):
        """Clipping should constrain values."""
        uv = UncertainValue.from_normal(100, 50)
        
        clipped = uv.clip(0, 150)
        
        assert clipped.point_estimate < uv.point_estimate  # Some values clipped
        assert clipped.confidence_interval_90[0] >= 0
        assert clipped.confidence_interval_90[1] <= 150
    
    def test_uncertainty_ratio(self):
        """Uncertainty ratio should reflect relative uncertainty."""
        narrow = UncertainValue.from_normal(100, 5)
        wide = UncertainValue.from_normal(100, 20)
        
        assert narrow.uncertainty_ratio < wide.uncertainty_ratio


# ============================================================================
# BAYESIAN CALCULATOR TESTS
# ============================================================================


class TestBayesianCalculator:
    """Tests for BayesianCalculator."""
    
    @pytest.fixture
    def calculator(self):
        return BayesianCalculator(n_samples=5000)
    
    def test_calculate_exposure(self, calculator):
        """Exposure calculation should propagate uncertainty."""
        cargo = UncertainValue.from_normal(150000, 5000, unit="usd")
        delay = UncertainValue.from_range(7, 14, unit="days")
        rate = UncertainValue.from_normal(0.001, 0.0002)  # 0.1% per day
        penalty = UncertainValue.from_point(1000, unit="usd")
        
        exposure = calculator.calculate_exposure(
            cargo_value=cargo,
            delay_days=delay,
            holding_cost_rate=rate,
            penalty_per_day=penalty,
            grace_period_days=3,
        )
        
        # Should have uncertainty
        assert exposure.confidence_interval_90[0] < exposure.point_estimate
        assert exposure.confidence_interval_90[1] > exposure.point_estimate
        
        # Should be positive
        assert exposure.point_estimate > 0
        assert exposure.confidence_interval_90[0] >= 0
    
    def test_calculate_confidence(self, calculator):
        """Confidence calculation should produce valid probabilities."""
        signal_prob = UncertainValue.from_normal(0.7, 0.1)
        correlation = UncertainValue.from_normal(0.8, 0.05)
        quality = UncertainValue.from_normal(0.75, 0.08)
        
        confidence = calculator.calculate_confidence(
            signal_probability=signal_prob,
            correlation_strength=correlation,
            data_quality=quality,
        )
        
        # Should be in [0, 1]
        assert 0 <= confidence.point_estimate <= 1
        assert confidence.confidence_interval_90[0] >= 0
        assert confidence.confidence_interval_90[1] <= 1
    
    def test_calculate_utility(self, calculator):
        """Utility calculation should handle negative values."""
        action_cost = UncertainValue.from_normal(5000, 500)
        risk_mitigated = UncertainValue.from_normal(20000, 3000)
        success_prob = UncertainValue.from_normal(0.8, 0.1)
        
        utility = calculator.calculate_utility(
            action_cost=action_cost,
            risk_mitigated=risk_mitigated,
            success_probability=success_prob,
        )
        
        # Expected: 0.8 * 20000 - 5000 = 11000
        assert 8000 < utility.point_estimate < 14000
    
    def test_calculate_delay_impact(self, calculator):
        """Delay impact should be non-negative."""
        base_delay = UncertainValue.from_normal(5, 1)
        reroute_additional = UncertainValue.from_range(7, 14)
        prob_event = UncertainValue.from_normal(0.6, 0.1)
        
        delay = calculator.calculate_delay_impact(
            base_delay=base_delay,
            reroute_additional=reroute_additional,
            probability_event=prob_event,
        )
        
        # Should be non-negative
        assert delay.point_estimate >= 0
        assert delay.confidence_interval_90[0] >= 0
        
        # Expected: 5 + 0.6 * 10.5 ≈ 11.3
        assert 8 < delay.point_estimate < 15


# ============================================================================
# CI COVERAGE VALIDATION
# ============================================================================


class TestCICoverage:
    """Tests to validate confidence interval coverage."""
    
    def test_90_ci_coverage(self):
        """90% CI should contain ~90% of samples drawn from the distribution."""
        import random
        
        # Create a known distribution
        true_mean = 100
        true_std = 10
        
        dist = Distribution(
            type=DistributionType.NORMAL,
            parameters={"mean": true_mean, "std": true_std}
        )
        ci = dist.confidence_interval(0.90)
        
        # Draw many samples and check how many fall within CI
        random.seed(42)  # For reproducibility
        n_samples = 1000
        samples = dist.sample(n_samples, seed=42)
        
        covered = sum(1 for s in samples if ci[0] <= s <= ci[1])
        coverage_rate = covered / n_samples
        
        # Should be close to 90% (allow some variance for sampling)
        assert 0.85 < coverage_rate < 0.95
    
    def test_uncertainty_increases_with_operations(self):
        """Uncertainty should grow when combining uncertain values."""
        uv1 = UncertainValue.from_normal(100, 10)
        uv2 = UncertainValue.from_normal(100, 10)
        
        # Sum
        summed = uv1 + uv2
        
        # Variance of sum = var1 + var2
        # So std of sum = sqrt(10^2 + 10^2) ≈ 14.14
        sum_width = summed.confidence_interval_90[1] - summed.confidence_interval_90[0]
        single_width = uv1.confidence_interval_90[1] - uv1.confidence_interval_90[0]
        
        # Sum width should be larger
        assert sum_width > single_width


# ============================================================================
# FACTORY TESTS
# ============================================================================


class TestFactory:
    """Tests for factory functions."""
    
    def test_create_calculator(self):
        """Should create calculator with specified samples."""
        calc = create_bayesian_calculator(n_samples=5000)
        
        assert calc is not None
        assert calc.n_samples == 5000
    
    def test_calculator_default_samples(self):
        """Default calculator should have 10000 samples."""
        calc = create_bayesian_calculator()
        
        assert calc.n_samples == 10000
