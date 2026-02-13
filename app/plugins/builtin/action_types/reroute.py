"""
Reroute Action Plugin.

Provides rerouting recommendations for cargo affected by disruptions.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List

import structlog

from app.plugins.base import (
    ActionTypePlugin,
    PluginMetadata,
    PluginType,
)

logger = structlog.get_logger(__name__)


# Route configuration
REROUTE_CONFIG = {
    "red_sea": {
        "original_route": ["suez", "mediterranean"],
        "alternative_route": ["cape_of_good_hope"],
        "delay_days_range": (7, 14),
        "cost_per_teu_range": (2000, 3500),
        "fuel_surcharge_pct": 0.15,
    },
    "panama": {
        "original_route": ["panama_canal"],
        "alternative_route": ["suez", "cape_of_good_hope"],
        "delay_days_range": (10, 21),
        "cost_per_teu_range": (1500, 2800),
        "fuel_surcharge_pct": 0.12,
    },
    "malacca": {
        "original_route": ["malacca_strait"],
        "alternative_route": ["lombok", "sunda"],
        "delay_days_range": (2, 5),
        "cost_per_teu_range": (500, 1200),
        "fuel_surcharge_pct": 0.05,
    },
}


class RerouteActionPlugin(ActionTypePlugin):
    """
    Reroute action plugin.
    
    Generates specific rerouting recommendations with:
    - Alternative routes
    - Carrier options
    - Cost estimates
    - Delay estimates
    - Deadline for decision
    """
    
    def __init__(self):
        super().__init__()
        self._carriers: List[str] = []
        self._generated_count = 0
    
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="reroute",
            version="1.0.0",
            plugin_type=PluginType.ACTION_TYPE,
            author="RISKCAST",
            description="Reroute cargo around disrupted areas",
            config_schema={
                "type": "object",
                "properties": {
                    "carriers": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of carriers to consider for rerouting",
                    },
                    "max_delay_tolerance_days": {
                        "type": "integer",
                        "default": 14,
                        "description": "Maximum acceptable delay in days",
                    },
                },
            },
        )
    
    async def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize with configuration."""
        self._config = config
        self._carriers = config.get("carriers", ["MSC", "Maersk", "CMA CGM", "Hapag-Lloyd"])
        
        logger.info(
            "reroute_plugin_initialized",
            carriers=self._carriers,
        )
    
    async def shutdown(self) -> None:
        """Cleanup on shutdown."""
        pass
    
    async def generate_action(
        self,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Generate reroute action recommendation."""
        chokepoint = context.get("chokepoint", "red_sea")
        shipment = context.get("shipment", {})
        severity = context.get("severity", "medium")
        
        config = REROUTE_CONFIG.get(chokepoint, REROUTE_CONFIG["red_sea"])
        
        # Calculate cost
        teu_count = shipment.get("teu_count", 1)
        cargo_value = shipment.get("cargo_value_usd", 50000)
        
        base_cost_per_teu = (config["cost_per_teu_range"][0] + config["cost_per_teu_range"][1]) / 2
        total_cost = teu_count * base_cost_per_teu
        
        # Calculate delay
        delay_min, delay_max = config["delay_days_range"]
        estimated_delay = (delay_min + delay_max) // 2
        
        # Select best carrier
        carrier = await self._select_best_carrier(chokepoint, context)
        
        # Calculate deadline
        deadline = self._calculate_deadline(context)
        
        action = {
            "action_type": "reroute",
            "action_id": f"reroute_{shipment.get('shipment_id', 'unknown')}_{datetime.utcnow().strftime('%Y%m%d%H%M')}",
            "summary": f"REROUTE via {', '.join(config['alternative_route'])} with {carrier}",
            "carrier": carrier,
            "original_route": config["original_route"],
            "alternative_route": config["alternative_route"],
            "estimated_cost_usd": round(total_cost, 2),
            "cost_breakdown": {
                "reroute_surcharge": round(total_cost * 0.7, 2),
                "fuel_surcharge": round(total_cost * config["fuel_surcharge_pct"], 2),
                "handling": round(total_cost * 0.15, 2),
            },
            "estimated_delay_days": estimated_delay,
            "delay_range": {"min": delay_min, "max": delay_max},
            "deadline": deadline.isoformat(),
            "shipment_id": shipment.get("shipment_id"),
            "chokepoint": chokepoint,
            "generated_at": datetime.utcnow().isoformat(),
        }
        
        self._generated_count += 1
        
        logger.info(
            "reroute_action_generated",
            action_id=action["action_id"],
            carrier=carrier,
            cost_usd=action["estimated_cost_usd"],
        )
        
        return action
    
    async def validate_action(
        self,
        action: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Validate reroute action."""
        errors = []
        warnings = []
        
        # Check required fields
        required_fields = ["carrier", "alternative_route", "estimated_cost_usd"]
        for field in required_fields:
            if field not in action:
                errors.append(f"Missing required field: {field}")
        
        # Check cost is reasonable
        cost = action.get("estimated_cost_usd", 0)
        if cost <= 0:
            errors.append("Cost must be positive")
        elif cost > 100000:
            warnings.append("Unusually high reroute cost - verify calculation")
        
        # Check delay is reasonable
        delay = action.get("estimated_delay_days", 0)
        max_tolerance = self._config.get("max_delay_tolerance_days", 14)
        if delay > max_tolerance:
            warnings.append(f"Delay ({delay} days) exceeds tolerance ({max_tolerance} days)")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }
    
    async def estimate_cost(
        self,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Estimate reroute cost without full action generation."""
        chokepoint = context.get("chokepoint", "red_sea")
        shipment = context.get("shipment", {})
        
        config = REROUTE_CONFIG.get(chokepoint, REROUTE_CONFIG["red_sea"])
        
        teu_count = shipment.get("teu_count", 1)
        cost_min = teu_count * config["cost_per_teu_range"][0]
        cost_max = teu_count * config["cost_per_teu_range"][1]
        
        return {
            "action_type": "reroute",
            "cost_estimate_usd": {
                "min": round(cost_min, 2),
                "max": round(cost_max, 2),
                "expected": round((cost_min + cost_max) / 2, 2),
            },
            "delay_estimate_days": {
                "min": config["delay_days_range"][0],
                "max": config["delay_days_range"][1],
            },
            "confidence": 0.75,
        }
    
    async def _select_best_carrier(
        self,
        chokepoint: str,
        context: Dict[str, Any],
    ) -> str:
        """Select best carrier for reroute."""
        # In production, this would query carrier APIs for availability
        # For now, use simple heuristic
        
        preferred_by_chokepoint = {
            "red_sea": ["MSC", "Maersk"],
            "panama": ["CMA CGM", "Hapag-Lloyd"],
            "malacca": ["MSC", "Evergreen"],
        }
        
        preferred = preferred_by_chokepoint.get(chokepoint, self._carriers)
        
        # Return first available carrier
        for carrier in preferred:
            if carrier in self._carriers:
                return carrier
        
        return self._carriers[0] if self._carriers else "MSC"
    
    def _calculate_deadline(self, context: Dict[str, Any]) -> datetime:
        """Calculate decision deadline."""
        from datetime import timedelta
        
        severity = context.get("severity", "medium")
        
        hours_by_severity = {
            "critical": 6,
            "high": 24,
            "medium": 48,
            "low": 72,
        }
        
        hours = hours_by_severity.get(severity, 48)
        return datetime.utcnow() + timedelta(hours=hours)


# For dynamic loading
Plugin = RerouteActionPlugin
