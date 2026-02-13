"""
Tests for Feature Flags.

Tests:
- Flag evaluation
- Percentage rollouts
- Customer targeting
- A/B variants
"""

import pytest
from app.core.feature_flags import (
    FeatureFlag,
    FeatureFlagService,
    FlagStatus,
    FlagVariant,
    InMemoryFlagBackend,
    get_feature_flags,
)


class TestFeatureFlags:
    """Tests for feature flag service."""
    
    @pytest.fixture
    def service(self):
        """Create a feature flag service."""
        backend = InMemoryFlagBackend()
        return FeatureFlagService(backend)
    
    def test_enabled_flag(self, service):
        """Enabled flag returns True."""
        service.create_flag(FeatureFlag(
            key="test_feature",
            description="Test feature",
            status=FlagStatus.ENABLED,
        ))
        
        assert service.is_enabled("test_feature") is True
    
    def test_disabled_flag(self, service):
        """Disabled flag returns False."""
        service.create_flag(FeatureFlag(
            key="test_feature",
            description="Test feature",
            status=FlagStatus.DISABLED,
        ))
        
        assert service.is_enabled("test_feature") is False
    
    def test_unknown_flag_returns_default(self, service):
        """Unknown flag returns default value."""
        assert service.is_enabled("unknown", default=False) is False
        assert service.is_enabled("unknown", default=True) is True
    
    def test_percentage_rollout(self, service):
        """Percentage rollout works correctly."""
        service.create_flag(FeatureFlag(
            key="test_feature",
            description="Test feature",
            status=FlagStatus.PERCENTAGE,
            percentage=50,
        ))
        
        # With customer IDs, should get consistent results
        # Hash-based so some will be True, some False
        results = [
            service.is_enabled("test_feature", customer_id=f"customer_{i}")
            for i in range(100)
        ]
        
        # Should be roughly 50/50 (allow some variance)
        true_count = sum(results)
        assert 30 <= true_count <= 70
    
    def test_customer_targeting(self, service):
        """Targeted flag works for specific customers."""
        service.create_flag(FeatureFlag(
            key="beta_feature",
            description="Beta feature",
            status=FlagStatus.TARGETED,
            allowed_customers=["CUST-001", "CUST-002"],
        ))
        
        assert service.is_enabled("beta_feature", customer_id="CUST-001") is True
        assert service.is_enabled("beta_feature", customer_id="CUST-002") is True
        assert service.is_enabled("beta_feature", customer_id="CUST-003") is False
    
    def test_blocked_customers(self, service):
        """Blocked customers are excluded."""
        service.create_flag(FeatureFlag(
            key="feature",
            description="Feature",
            status=FlagStatus.ENABLED,
            blocked_customers=["BAD-001"],
        ))
        
        assert service.is_enabled("feature", customer_id="GOOD-001") is True
        assert service.is_enabled("feature", customer_id="BAD-001") is False
    
    def test_testing_override(self, service):
        """Testing override works."""
        service.create_flag(FeatureFlag(
            key="test_feature",
            description="Test feature",
            status=FlagStatus.DISABLED,
        ))
        
        # Before override
        assert service.is_enabled("test_feature") is False
        
        # Set override
        service.set_override("test_feature", True)
        assert service.is_enabled("test_feature") is True
        
        # Clear override
        service.clear_override("test_feature")
        assert service.is_enabled("test_feature") is False
    
    def test_variant_selection(self, service):
        """A/B variant selection works."""
        service.create_flag(FeatureFlag(
            key="ab_test",
            description="A/B test",
            status=FlagStatus.ENABLED,
            variants=[
                FlagVariant(name="control", weight=50),
                FlagVariant(name="treatment", weight=50),
            ],
        ))
        
        # With customer ID, should get consistent variant
        variant1 = service.get_variant("ab_test", customer_id="CUST-001")
        variant2 = service.get_variant("ab_test", customer_id="CUST-001")
        
        assert variant1 == variant2  # Consistent for same customer
        assert variant1 in ["control", "treatment"]
    
    def test_variant_config(self, service):
        """Variant configuration is accessible."""
        service.create_flag(FeatureFlag(
            key="ab_test",
            description="A/B test",
            status=FlagStatus.ENABLED,
            variants=[
                FlagVariant(
                    name="control",
                    weight=50,
                    config={"button_color": "blue"},
                ),
                FlagVariant(
                    name="treatment",
                    weight=50,
                    config={"button_color": "green"},
                ),
            ],
        ))
        
        config = service.get_config("ab_test", customer_id="CUST-001")
        
        assert "button_color" in config
        assert config["button_color"] in ["blue", "green"]
    
    def test_flag_crud(self, service):
        """Flag CRUD operations work."""
        # Create
        flag = FeatureFlag(
            key="new_feature",
            description="New feature",
            status=FlagStatus.DISABLED,
        )
        service.create_flag(flag)
        
        # Read
        assert service.is_enabled("new_feature") is False
        
        # Update
        flag.status = FlagStatus.ENABLED
        service.update_flag(flag)
        assert service.is_enabled("new_feature") is True
        
        # Delete
        service.delete_flag("new_feature")
        assert service.is_enabled("new_feature", default=False) is False
    
    def test_list_flags(self, service):
        """Can list all flags."""
        flags = service.list_flags()
        
        # Should have default flags from InMemoryFlagBackend
        assert len(flags) > 0
        assert all(isinstance(f, FeatureFlag) for f in flags)


class TestDefaultFlags:
    """Tests for default flags."""
    
    def test_default_flags_exist(self):
        """Default flags are configured."""
        service = get_feature_flags()
        
        # Check some default flags exist
        assert service.is_enabled("enable_decision_caching") is True
        assert service.is_enabled("enable_circuit_breaker") is True
