"""
Insurance Action Plugin.

Provides insurance recommendations for at-risk cargo.
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

import structlog

from app.plugins.base import (
    ActionTypePlugin,
    PluginMetadata,
    PluginType,
)

logger = structlog.get_logger(__name__)


# Insurance rate configuration
INSURANCE_RATES = {
    "standard_coverage": {
        "premium_rate": 0.015,  # 1.5% of cargo value
        "deductible_rate": 0.05,  # 5% deductible
        "max_coverage_usd": 5_000_000,
    },
    "war_risk": {
        "premium_rate": 0.025,  # 2.5% of cargo value
        "deductible_rate": 0.02,  # 2% deductible
        "max_coverage_usd": 10_000_000,
    },
    "delay_coverage": {
        "premium_rate": 0.008,  # 0.8% of cargo value
        "deductible_rate": 0.10,  # 10% deductible
        "max_coverage_usd": 1_000_000,
    },
}

INSURANCE_PROVIDERS = [
    {"name": "Allianz Trade", "rating": "A+", "specialty": "marine cargo"},
    {"name": "Zurich Insurance", "rating": "AA", "specialty": "war risk"},
    {"name": "Lloyd's of London", "rating": "A+", "specialty": "specialty risks"},
    {"name": "AXA XL", "rating": "A+", "specialty": "supply chain"},
]


class InsureActionPlugin(ActionTypePlugin):
    """
    Insurance action plugin.
    
    Generates insurance recommendations including:
    - Coverage types (standard, war risk, delay)
    - Premium estimates
    - Provider recommendations
    - Coverage limits and deductibles
    """
    
    def __init__(self):
        super().__init__()
        self._generated_count = 0
    
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="insure",
            version="1.0.0",
            plugin_type=PluginType.ACTION_TYPE,
            author="RISKCAST",
            description="Add insurance coverage for at-risk cargo",
            config_schema={
                "type": "object",
                "properties": {
                    "preferred_providers": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Preferred insurance providers",
                    },
                    "max_premium_rate": {
                        "type": "number",
                        "default": 0.05,
                        "description": "Maximum acceptable premium rate",
                    },
                },
            },
        )
    
    async def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize with configuration."""
        self._config = config
        logger.info("insure_plugin_initialized")
    
    async def shutdown(self) -> None:
        """Cleanup on shutdown."""
        pass
    
    async def generate_action(
        self,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Generate insurance action recommendation."""
        shipment = context.get("shipment", {})
        risk_type = context.get("risk_type", "standard")
        severity = context.get("severity", "medium")
        
        cargo_value = shipment.get("cargo_value_usd", 100000)
        
        # Determine recommended coverage types
        coverage_types = self._recommend_coverage_types(risk_type, severity)
        
        # Calculate premiums for each coverage type
        coverages = []
        total_premium = 0
        
        for coverage_type in coverage_types:
            rate_config = INSURANCE_RATES.get(coverage_type, INSURANCE_RATES["standard_coverage"])
            premium = cargo_value * rate_config["premium_rate"]
            
            # Adjust premium based on severity
            severity_multiplier = {"critical": 1.5, "high": 1.25, "medium": 1.0, "low": 0.9}
            premium *= severity_multiplier.get(severity, 1.0)
            
            coverage = {
                "type": coverage_type,
                "premium_usd": round(premium, 2),
                "coverage_limit_usd": min(cargo_value, rate_config["max_coverage_usd"]),
                "deductible_usd": round(cargo_value * rate_config["deductible_rate"], 2),
                "effective_coverage_usd": round(
                    cargo_value * (1 - rate_config["deductible_rate"]),
                    2,
                ),
            }
            coverages.append(coverage)
            total_premium += premium
        
        # Select recommended provider
        provider = self._select_provider(coverage_types, context)
        
        # Calculate deadline (insurance needs lead time)
        deadline = datetime.utcnow() + timedelta(hours=48)
        
        action = {
            "action_type": "insure",
            "action_id": f"insure_{shipment.get('shipment_id', 'unknown')}_{datetime.utcnow().strftime('%Y%m%d%H%M')}",
            "summary": f"ADD {', '.join(coverage_types)} coverage via {provider['name']}",
            "recommended_provider": provider,
            "coverages": coverages,
            "total_premium_usd": round(total_premium, 2),
            "estimated_cost_usd": round(total_premium, 2),
            "cargo_value_usd": cargo_value,
            "effective_date": datetime.utcnow().isoformat(),
            "expiry_date": (datetime.utcnow() + timedelta(days=90)).isoformat(),
            "deadline": deadline.isoformat(),
            "shipment_id": shipment.get("shipment_id"),
            "application_steps": [
                "Submit cargo manifest and value declaration",
                "Provide current shipment location/status",
                "Review and sign coverage agreement",
                "Pay premium via wire transfer",
            ],
            "generated_at": datetime.utcnow().isoformat(),
        }
        
        self._generated_count += 1
        
        logger.info(
            "insure_action_generated",
            action_id=action["action_id"],
            coverage_types=coverage_types,
            premium_usd=total_premium,
        )
        
        return action
    
    async def validate_action(
        self,
        action: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Validate insurance action."""
        errors = []
        warnings = []
        
        # Check premium is reasonable
        premium = action.get("total_premium_usd", 0)
        cargo_value = action.get("cargo_value_usd", 0)
        
        if premium <= 0:
            errors.append("Premium must be positive")
        
        if cargo_value > 0:
            premium_rate = premium / cargo_value
            max_rate = self._config.get("max_premium_rate", 0.05)
            
            if premium_rate > max_rate:
                warnings.append(f"Premium rate ({premium_rate:.2%}) exceeds max ({max_rate:.2%})")
        
        # Check coverages
        coverages = action.get("coverages", [])
        if not coverages:
            errors.append("At least one coverage type required")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }
    
    async def estimate_cost(
        self,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Estimate insurance cost without full action generation."""
        shipment = context.get("shipment", {})
        risk_type = context.get("risk_type", "standard")
        
        cargo_value = shipment.get("cargo_value_usd", 100000)
        
        # Calculate range based on coverage types
        if risk_type == "war_risk":
            rate_min = 0.02
            rate_max = 0.035
        elif risk_type == "delay":
            rate_min = 0.006
            rate_max = 0.012
        else:
            rate_min = 0.01
            rate_max = 0.02
        
        return {
            "action_type": "insure",
            "cost_estimate_usd": {
                "min": round(cargo_value * rate_min, 2),
                "max": round(cargo_value * rate_max, 2),
                "expected": round(cargo_value * (rate_min + rate_max) / 2, 2),
            },
            "rate_range": {"min": rate_min, "max": rate_max},
            "confidence": 0.8,
        }
    
    def _recommend_coverage_types(
        self,
        risk_type: str,
        severity: str,
    ) -> List[str]:
        """Determine recommended coverage types."""
        coverages = ["standard_coverage"]
        
        if risk_type in ["war", "conflict", "red_sea"]:
            coverages.append("war_risk")
        
        if severity in ["high", "critical"]:
            coverages.append("delay_coverage")
        
        return coverages
    
    def _select_provider(
        self,
        coverage_types: List[str],
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Select best insurance provider."""
        preferred = self._config.get("preferred_providers", [])
        
        # Check if preferred provider matches
        for provider in INSURANCE_PROVIDERS:
            if provider["name"] in preferred:
                return provider
        
        # Select by specialty
        if "war_risk" in coverage_types:
            for provider in INSURANCE_PROVIDERS:
                if "war" in provider["specialty"]:
                    return provider
        
        # Default to highest rated
        return max(INSURANCE_PROVIDERS, key=lambda p: p["rating"])


# For dynamic loading
Plugin = InsureActionPlugin
