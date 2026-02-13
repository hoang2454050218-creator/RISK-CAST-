"""
Feature Flags System.

Provides:
- Feature flag management with percentage rollouts
- User/customer targeting
- A/B testing support
- Runtime configuration changes
- Metrics integration

Supports multiple backends:
- In-memory (development)
- Redis (production)
- Database (persistent)
"""

import random
import hashlib
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field

import structlog
from pydantic import BaseModel

logger = structlog.get_logger(__name__)


# ============================================================================
# MODELS
# ============================================================================


class FlagStatus(str, Enum):
    """Feature flag status."""
    ENABLED = "enabled"      # Always on
    DISABLED = "disabled"    # Always off
    PERCENTAGE = "percentage"  # Percentage rollout
    TARGETED = "targeted"    # Specific users/customers


class FlagVariant(BaseModel):
    """A variant for A/B testing."""
    name: str
    weight: int = 100  # Weight for selection
    config: Dict[str, Any] = {}


@dataclass
class FeatureFlag:
    """
    Feature flag definition.
    
    Supports:
    - Simple on/off
    - Percentage rollout
    - User targeting
    - A/B variants
    """
    key: str
    description: str
    status: FlagStatus = FlagStatus.DISABLED
    
    # Percentage rollout (0-100)
    percentage: int = 0
    
    # Targeting rules
    allowed_customers: List[str] = field(default_factory=list)
    blocked_customers: List[str] = field(default_factory=list)
    
    # A/B variants
    variants: List[FlagVariant] = field(default_factory=list)
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    owner: Optional[str] = None
    tags: List[str] = field(default_factory=list)


# ============================================================================
# FEATURE FLAG SERVICE
# ============================================================================


class FeatureFlagService:
    """
    Feature flag service with pluggable backends.
    """
    
    def __init__(self, backend: Optional["FlagBackend"] = None):
        self._backend = backend or InMemoryFlagBackend()
        self._overrides: Dict[str, bool] = {}  # For testing
        
    def is_enabled(
        self,
        flag_key: str,
        customer_id: Optional[str] = None,
        default: bool = False,
    ) -> bool:
        """
        Check if a feature flag is enabled.
        
        Args:
            flag_key: Feature flag key
            customer_id: Optional customer ID for targeting
            default: Default value if flag not found
            
        Returns:
            True if enabled
        """
        # Check testing overrides first
        if flag_key in self._overrides:
            return self._overrides[flag_key]
        
        flag = self._backend.get_flag(flag_key)
        if not flag:
            logger.debug("feature_flag_not_found", key=flag_key, default=default)
            return default
        
        result = self._evaluate(flag, customer_id)
        
        logger.debug(
            "feature_flag_evaluated",
            key=flag_key,
            enabled=result,
            customer_id=customer_id,
            status=flag.status,
        )
        
        return result
    
    def get_variant(
        self,
        flag_key: str,
        customer_id: Optional[str] = None,
        default_variant: str = "control",
    ) -> str:
        """
        Get the variant for an A/B test flag.
        
        Args:
            flag_key: Feature flag key
            customer_id: Customer ID for consistent assignment
            default_variant: Default if no variant found
            
        Returns:
            Variant name
        """
        flag = self._backend.get_flag(flag_key)
        if not flag or not flag.variants:
            return default_variant
        
        if not self._evaluate(flag, customer_id):
            return default_variant
        
        # Deterministic variant selection based on customer
        if customer_id:
            hash_input = f"{flag_key}:{customer_id}"
            hash_value = int(hashlib.sha256(hash_input.encode()).hexdigest()[:8], 16)
            total_weight = sum(v.weight for v in flag.variants)
            position = hash_value % total_weight
            
            cumulative = 0
            for variant in flag.variants:
                cumulative += variant.weight
                if position < cumulative:
                    return variant.name
        
        # Random selection if no customer
        total_weight = sum(v.weight for v in flag.variants)
        position = random.randint(0, total_weight - 1)
        
        cumulative = 0
        for variant in flag.variants:
            cumulative += variant.weight
            if position < cumulative:
                return variant.name
        
        return default_variant
    
    def get_config(
        self,
        flag_key: str,
        customer_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get configuration for a flag's variant.
        
        Useful for feature configuration beyond on/off.
        """
        flag = self._backend.get_flag(flag_key)
        if not flag or not flag.variants:
            return {}
        
        variant_name = self.get_variant(flag_key, customer_id)
        
        for variant in flag.variants:
            if variant.name == variant_name:
                return variant.config
        
        return {}
    
    def _evaluate(self, flag: FeatureFlag, customer_id: Optional[str]) -> bool:
        """Evaluate flag for a specific context."""
        # Check customer blocking
        if customer_id and customer_id in flag.blocked_customers:
            return False
        
        # Simple statuses
        if flag.status == FlagStatus.ENABLED:
            return True
        
        if flag.status == FlagStatus.DISABLED:
            return False
        
        # Targeted
        if flag.status == FlagStatus.TARGETED:
            return customer_id in flag.allowed_customers
        
        # Percentage rollout
        if flag.status == FlagStatus.PERCENTAGE:
            if customer_id:
                # Deterministic based on customer
                hash_input = f"{flag.key}:{customer_id}"
                hash_value = int(hashlib.sha256(hash_input.encode()).hexdigest()[:8], 16)
                return (hash_value % 100) < flag.percentage
            else:
                # Random for anonymous
                return random.randint(0, 99) < flag.percentage
        
        return False
    
    def set_override(self, flag_key: str, enabled: bool) -> None:
        """Set testing override for a flag."""
        self._overrides[flag_key] = enabled
    
    def clear_override(self, flag_key: str) -> None:
        """Clear testing override."""
        self._overrides.pop(flag_key, None)
    
    def clear_all_overrides(self) -> None:
        """Clear all testing overrides."""
        self._overrides.clear()
    
    # Flag management
    def create_flag(self, flag: FeatureFlag) -> None:
        """Create a new feature flag."""
        self._backend.set_flag(flag)
        logger.info("feature_flag_created", key=flag.key, status=flag.status)
    
    def update_flag(self, flag: FeatureFlag) -> None:
        """Update an existing flag."""
        flag.updated_at = datetime.utcnow()
        self._backend.set_flag(flag)
        logger.info("feature_flag_updated", key=flag.key, status=flag.status)
    
    def delete_flag(self, flag_key: str) -> None:
        """Delete a feature flag."""
        self._backend.delete_flag(flag_key)
        logger.info("feature_flag_deleted", key=flag_key)
    
    def list_flags(self) -> List[FeatureFlag]:
        """List all flags."""
        return self._backend.list_flags()


# ============================================================================
# BACKENDS
# ============================================================================


class FlagBackend:
    """Abstract backend interface."""
    
    def get_flag(self, key: str) -> Optional[FeatureFlag]:
        raise NotImplementedError
    
    def set_flag(self, flag: FeatureFlag) -> None:
        raise NotImplementedError
    
    def delete_flag(self, key: str) -> None:
        raise NotImplementedError
    
    def list_flags(self) -> List[FeatureFlag]:
        raise NotImplementedError


class InMemoryFlagBackend(FlagBackend):
    """In-memory backend for development."""
    
    def __init__(self):
        self._flags: Dict[str, FeatureFlag] = {}
        self._setup_defaults()
    
    def _setup_defaults(self) -> None:
        """Setup default feature flags."""
        defaults = [
            FeatureFlag(
                key="enable_decision_caching",
                description="Cache decisions in Redis",
                status=FlagStatus.ENABLED,
            ),
            FeatureFlag(
                key="enable_circuit_breaker",
                description="Enable circuit breaker for external calls",
                status=FlagStatus.ENABLED,
            ),
            FeatureFlag(
                key="enable_tracing",
                description="Enable distributed tracing",
                status=FlagStatus.PERCENTAGE,
                percentage=100,
            ),
            FeatureFlag(
                key="enable_ml_scoring",
                description="Enable ML-based confidence scoring",
                status=FlagStatus.DISABLED,
            ),
            FeatureFlag(
                key="new_impact_calculator",
                description="Use new impact calculation algorithm",
                status=FlagStatus.PERCENTAGE,
                percentage=0,
            ),
            FeatureFlag(
                key="enable_whatsapp_delivery",
                description="Enable WhatsApp alert delivery",
                status=FlagStatus.ENABLED,
            ),
        ]
        
        for flag in defaults:
            self._flags[flag.key] = flag
    
    def get_flag(self, key: str) -> Optional[FeatureFlag]:
        return self._flags.get(key)
    
    def set_flag(self, flag: FeatureFlag) -> None:
        self._flags[flag.key] = flag
    
    def delete_flag(self, key: str) -> None:
        self._flags.pop(key, None)
    
    def list_flags(self) -> List[FeatureFlag]:
        return list(self._flags.values())


class RedisFlagBackend(FlagBackend):
    """Redis backend for production."""
    
    def __init__(self, redis_client):
        self._redis = redis_client
        self._prefix = "ff:"
    
    def get_flag(self, key: str) -> Optional[FeatureFlag]:
        import json
        
        data = self._redis.get(f"{self._prefix}{key}")
        if not data:
            return None
        
        try:
            obj = json.loads(data)
            return FeatureFlag(**obj)
        except Exception:
            return None
    
    def set_flag(self, flag: FeatureFlag) -> None:
        import json
        
        data = {
            "key": flag.key,
            "description": flag.description,
            "status": flag.status,
            "percentage": flag.percentage,
            "allowed_customers": flag.allowed_customers,
            "blocked_customers": flag.blocked_customers,
            "variants": [v.model_dump() for v in flag.variants],
            "created_at": flag.created_at.isoformat(),
            "updated_at": flag.updated_at.isoformat(),
            "owner": flag.owner,
            "tags": flag.tags,
        }
        
        self._redis.set(f"{self._prefix}{flag.key}", json.dumps(data))
    
    def delete_flag(self, key: str) -> None:
        self._redis.delete(f"{self._prefix}{key}")
    
    def list_flags(self) -> List[FeatureFlag]:
        import json
        
        keys = self._redis.keys(f"{self._prefix}*")
        flags = []
        
        for key in keys:
            data = self._redis.get(key)
            if data:
                try:
                    obj = json.loads(data)
                    flags.append(FeatureFlag(**obj))
                except Exception:
                    pass
        
        return flags


# ============================================================================
# GLOBAL INSTANCE
# ============================================================================


_feature_flag_service: Optional[FeatureFlagService] = None


def get_feature_flags() -> FeatureFlagService:
    """Get global feature flag service."""
    global _feature_flag_service
    
    if _feature_flag_service is None:
        _feature_flag_service = FeatureFlagService()
    
    return _feature_flag_service


def feature_enabled(flag_key: str, default: bool = False) -> Callable:
    """
    Decorator to gate functions behind feature flags.
    
    @feature_enabled("new_algorithm")
    def calculate_impact(...):
        ...
    """
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            # Try to get customer_id from kwargs
            customer_id = kwargs.get("customer_id")
            
            if get_feature_flags().is_enabled(flag_key, customer_id, default):
                return func(*args, **kwargs)
            
            logger.debug(
                "feature_flag_blocked",
                key=flag_key,
                function=func.__name__,
            )
            return None
        
        return wrapper
    return decorator


# ============================================================================
# PREDEFINED FLAGS
# ============================================================================


class Flags:
    """Predefined feature flag keys for type safety."""
    
    # Decision Engine
    ENABLE_DECISION_CACHING = "enable_decision_caching"
    ENABLE_CIRCUIT_BREAKER = "enable_circuit_breaker"
    NEW_IMPACT_CALCULATOR = "new_impact_calculator"
    
    # ML Features
    ENABLE_ML_SCORING = "enable_ml_scoring"
    ENABLE_CONFIDENCE_CALIBRATION = "enable_confidence_calibration"
    
    # Delivery
    ENABLE_WHATSAPP_DELIVERY = "enable_whatsapp_delivery"
    ENABLE_EMAIL_DELIVERY = "enable_email_delivery"
    
    # Observability
    ENABLE_TRACING = "enable_tracing"
    ENABLE_DETAILED_METRICS = "enable_detailed_metrics"
    
    # Experimental
    EXPERIMENTAL_MULTI_CHOKEPOINT = "experimental_multi_chokepoint"
