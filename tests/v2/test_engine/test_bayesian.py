"""
Bayesian Risk Scoring Engine Tests.

Includes property-based tests via Hypothesis.
"""

import pytest
from hypothesis import given, settings as hyp_settings, assume
from hypothesis import strategies as st

from riskcast.engine.bayesian import (
    BayesianRiskEngine,
    BetaPosterior,
    NormalPosterior,
    RiskScore,
    DEFAULT_PRIOR_ALPHA,
    DEFAULT_PRIOR_BETA,
    MIN_OBSERVATIONS,
)


class TestBetaUpdate:
    """Test Bayesian Beta-Binomial updates."""

    def setup_method(self):
        self.engine = BayesianRiskEngine()

    def test_prior_only(self):
        """With no data, posterior equals prior."""
        result = self.engine.beta_update(0, 0)
        expected_mean = DEFAULT_PRIOR_ALPHA / (DEFAULT_PRIOR_ALPHA + DEFAULT_PRIOR_BETA)
        assert abs(result.mean - expected_mean) < 1e-4
        assert result.n_observations == 0

    def test_data_shifts_posterior(self):
        """More bad outcomes → higher posterior mean."""
        low = self.engine.beta_update(1, 9)
        high = self.engine.beta_update(9, 1)
        assert high.mean > low.mean

    def test_more_data_narrows_interval(self):
        """More observations → narrower credible interval."""
        few = self.engine.beta_update(5, 5)
        many = self.engine.beta_update(50, 50)
        assert many.uncertainty_width < few.uncertainty_width

    def test_credible_interval_bounds(self):
        """CI lower <= mean <= CI upper, both in [0, 1]."""
        result = self.engine.beta_update(3, 7)
        assert 0 <= result.ci_lower <= result.mean <= result.ci_upper <= 1

    def test_is_reliable_threshold(self):
        """Reliability depends on observation count."""
        unreliable = self.engine.beta_update(1, 2)
        assert not unreliable.is_reliable

        reliable = self.engine.beta_update(3, 3)  # 6 >= MIN_OBSERVATIONS
        assert reliable.is_reliable

    def test_custom_prior(self):
        """Custom prior overrides defaults."""
        result = self.engine.beta_update(5, 5, prior_alpha=10.0, prior_beta=10.0)
        assert result.prior_alpha == 10.0
        assert result.prior_beta == 10.0

    def test_data_influence_zero_with_no_data(self):
        """No data → zero data influence."""
        result = self.engine.beta_update(0, 0)
        assert result.data_influence == 0.0

    def test_data_influence_increases(self):
        """More skewed data → higher data influence."""
        balanced = self.engine.beta_update(5, 5)
        skewed = self.engine.beta_update(10, 0)
        assert skewed.data_influence > balanced.data_influence


class TestNormalUpdate:
    """Test Normal-Normal conjugate update."""

    def setup_method(self):
        self.engine = BayesianRiskEngine()

    def test_no_data_returns_prior(self):
        """With no data, posterior = prior."""
        result = self.engine.normal_update(0, 0, 0, prior_mean=50, prior_std=25)
        assert result.mean == 50.0
        assert result.n_observations == 0

    def test_data_pulls_toward_mean(self):
        """Posterior mean is between prior and data."""
        result = self.engine.normal_update(80, 10, 20, prior_mean=50, prior_std=25)
        assert 50 < result.mean < 80

    def test_more_data_reduces_std(self):
        """More observations → smaller posterior std."""
        few = self.engine.normal_update(70, 10, 5, prior_mean=50, prior_std=25)
        many = self.engine.normal_update(70, 10, 100, prior_mean=50, prior_std=25)
        assert many.std < few.std


class TestRiskScore:
    """Test composite risk score computation."""

    def setup_method(self):
        self.engine = BayesianRiskEngine()

    def test_basic_risk_score(self):
        """Compute risk score with factors."""
        result = self.engine.compute_risk_score(
            entity_type="order",
            entity_id="test-123",
            bad_outcomes=3,
            good_outcomes=7,
            severity=60.0,
        )
        assert result.entity_type == "order"
        assert 0 <= result.risk_probability <= 1
        assert 0 <= result.expected_loss <= 100
        assert result.algorithm == "bayesian_beta_binomial"

    def test_no_outcomes_uses_prior(self):
        """No outcomes → risk from prior only."""
        result = self.engine.compute_risk_score(
            entity_type="customer",
            entity_id="test-456",
            bad_outcomes=0,
            good_outcomes=0,
            severity=50.0,
        )
        assert not result.is_reliable
        assert result.n_observations == 0

    def test_expected_loss_calculation(self):
        """expected_loss = risk_probability × severity."""
        result = self.engine.compute_risk_score(
            entity_type="route",
            entity_id="test-789",
            bad_outcomes=5,
            good_outcomes=5,
            severity=80.0,
        )
        expected = result.risk_probability * 80.0
        assert abs(result.expected_loss - expected) < 0.1


class TestPropertyBased:
    """Property-based tests using Hypothesis."""

    @given(
        successes=st.integers(min_value=0, max_value=1000),
        failures=st.integers(min_value=0, max_value=1000),
    )
    @hyp_settings(max_examples=100)
    def test_posterior_mean_in_unit_interval(self, successes, failures):
        """Posterior mean is always in [0, 1]."""
        engine = BayesianRiskEngine()
        result = engine.beta_update(successes, failures)
        assert 0 <= result.mean <= 1

    @given(
        successes=st.integers(min_value=0, max_value=500),
        failures=st.integers(min_value=0, max_value=500),
    )
    @hyp_settings(max_examples=100)
    def test_ci_always_valid(self, successes, failures):
        """CI is always valid: 0 <= lower <= mean <= upper <= 1."""
        engine = BayesianRiskEngine()
        result = engine.beta_update(successes, failures)
        assert 0 <= result.ci_lower <= result.mean <= result.ci_upper <= 1

    @given(
        successes=st.integers(min_value=0, max_value=500),
        failures=st.integers(min_value=0, max_value=500),
    )
    @hyp_settings(max_examples=50)
    def test_variance_non_negative(self, successes, failures):
        """Variance is always non-negative."""
        engine = BayesianRiskEngine()
        result = engine.beta_update(successes, failures)
        assert result.variance >= 0

    @given(
        severity=st.floats(min_value=0, max_value=100),
        bad=st.integers(min_value=0, max_value=100),
        good=st.integers(min_value=0, max_value=100),
    )
    @hyp_settings(max_examples=50)
    def test_expected_loss_bounded(self, severity, bad, good):
        """Expected loss is always between 0 and severity."""
        assume(not (severity != severity))  # Exclude NaN
        engine = BayesianRiskEngine()
        result = engine.compute_risk_score("order", "x", bad, good, severity)
        assert 0 <= result.expected_loss <= severity + 0.01
