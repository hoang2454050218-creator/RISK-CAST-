"""
Risk Decomposition Engine Tests.
"""

import pytest

from riskcast.engine.decomposition import DecompositionEngine


class TestRiskDecomposition:
    """Test risk score decomposition."""

    def setup_method(self):
        self.engine = DecompositionEngine()

    def test_basic_decomposition(self):
        """Decompose a composite score into factors."""
        result = self.engine.decompose(
            entity_type="order",
            entity_id="test-123",
            composite_score=65.0,
            confidence=0.8,
            factor_scores={"payment_risk": 80, "route_disruption": 50},
            factor_weights={"payment_risk": 0.6, "route_disruption": 0.4},
        )
        assert result.composite_score == 65.0
        assert len(result.factors) == 2

    def test_factors_sorted_by_contribution(self):
        """Factors are sorted by contribution (highest first)."""
        result = self.engine.decompose(
            entity_type="order",
            entity_id="test-123",
            composite_score=60.0,
            confidence=0.7,
            factor_scores={"payment_risk": 80, "route_disruption": 20},
            factor_weights={"payment_risk": 0.6, "route_disruption": 0.4},
        )
        assert result.factors[0].factor_name == "payment_risk"

    def test_primary_driver(self):
        """Primary driver is the top contributor."""
        result = self.engine.decompose(
            entity_type="customer",
            entity_id="test-456",
            composite_score=70.0,
            confidence=0.8,
            factor_scores={"payment_risk": 90, "customer_creditworthiness": 30},
            factor_weights={"payment_risk": 0.7, "customer_creditworthiness": 0.3},
        )
        assert result.primary_driver == "Payment Risk"

    def test_high_risk_summary(self):
        """High score → HIGH RISK in summary."""
        result = self.engine.decompose(
            entity_type="order",
            entity_id="test-789",
            composite_score=80.0,
            confidence=0.9,
            factor_scores={"payment_risk": 85},
            factor_weights={"payment_risk": 1.0},
        )
        assert "HIGH RISK" in result.summary

    def test_low_risk_summary(self):
        """Low score → LOW RISK in summary."""
        result = self.engine.decompose(
            entity_type="order",
            entity_id="test-000",
            composite_score=15.0,
            confidence=0.9,
            factor_scores={"payment_risk": 15},
            factor_weights={"payment_risk": 1.0},
        )
        assert "LOW RISK" in result.summary

    def test_data_gaps_reported(self):
        """Missing evidence is reported as data gaps."""
        result = self.engine.decompose(
            entity_type="order",
            entity_id="test-111",
            composite_score=50.0,
            confidence=0.5,
            factor_scores={"payment_risk": 50, "route_disruption": 50},
            factor_weights={"payment_risk": 0.5, "route_disruption": 0.5},
            factor_evidence={},  # No evidence provided
        )
        assert len(result.data_gaps) >= 2

    def test_explanation_uses_template(self):
        """Factors use the correct explanation template."""
        result = self.engine.decompose(
            entity_type="order",
            entity_id="test-222",
            composite_score=60.0,
            confidence=0.7,
            factor_scores={"payment_risk": 70},
            factor_weights={"payment_risk": 1.0},
            factor_evidence={"payment_risk": {"late_pct": 45, "avg_delay": 12}},
        )
        factor = result.factors[0]
        assert "45" in factor.explanation  # late_pct
        assert factor.display_name == "Payment Risk"

    def test_recommendation_provided(self):
        """Every factor has a recommendation."""
        result = self.engine.decompose(
            entity_type="order",
            entity_id="test-333",
            composite_score=50.0,
            confidence=0.7,
            factor_scores={"payment_risk": 80},
            factor_weights={"payment_risk": 1.0},
        )
        for factor in result.factors:
            assert len(factor.recommendation) > 0

    def test_unknown_factor_uses_default(self):
        """Unknown factor types use default template."""
        result = self.engine.decompose(
            entity_type="order",
            entity_id="test-444",
            composite_score=50.0,
            confidence=0.7,
            factor_scores={"exotic_risk_xyz": 65},
            factor_weights={"exotic_risk_xyz": 1.0},
        )
        assert len(result.factors) == 1
        assert result.factors[0].display_name == "Risk Factor"  # Default
