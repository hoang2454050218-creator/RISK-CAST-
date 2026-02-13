"""
Delay Action Plugin.

Provides delay/hold recommendations for cargo during disruptions.
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any

import structlog

from app.plugins.base import (
    ActionTypePlugin,
    PluginMetadata,
    PluginType,
)

logger = structlog.get_logger(__name__)


# Holding cost configuration
HOLDING_COSTS = {
    "container_per_day_usd": 150,  # Per container per day
    "demurrage_per_day_usd": 200,  # Port demurrage
    "storage_per_day_usd": 50,     # Warehouse storage
    "insurance_per_day_pct": 0.0001,  # Insurance premium per day as % of cargo value
}


class DelayActionPlugin(ActionTypePlugin):
    """
    Delay/Hold action plugin.
    
    Generates recommendations to hold cargo until:
    - Disruption clears
    - Rates normalize
    - Risk decreases
    
    Calculates holding costs and optimal wait time.
    """
    
    def __init__(self):
        super().__init__()
        self._generated_count = 0
    
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="delay",
            version="1.0.0",
            plugin_type=PluginType.ACTION_TYPE,
            author="RISKCAST",
            description="Delay shipment until conditions improve",
            config_schema={
                "type": "object",
                "properties": {
                    "max_delay_days": {
                        "type": "integer",
                        "default": 30,
                        "description": "Maximum recommended delay in days",
                    },
                    "holding_cost_per_container_day": {
                        "type": "number",
                        "default": 150,
                    },
                },
            },
        )
    
    async def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize with configuration."""
        self._config = config
        logger.info("delay_plugin_initialized")
    
    async def shutdown(self) -> None:
        """Cleanup on shutdown."""
        pass
    
    async def generate_action(
        self,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Generate delay action recommendation."""
        shipment = context.get("shipment", {})
        disruption = context.get("disruption", {})
        
        # Calculate optimal delay duration
        expected_duration = disruption.get("expected_duration_days", 14)
        max_delay = self._config.get("max_delay_days", 30)
        recommended_delay = min(expected_duration, max_delay)
        
        # Calculate holding costs
        cargo_value = shipment.get("cargo_value_usd", 50000)
        container_count = shipment.get("container_count", 1)
        
        holding_cost = self._calculate_holding_cost(
            container_count=container_count,
            cargo_value=cargo_value,
            days=recommended_delay,
        )
        
        # Calculate savings vs rerouting
        reroute_cost = context.get("reroute_cost_estimate", recommended_delay * 2000)
        savings = max(0, reroute_cost - holding_cost["total"])
        
        # Calculate resume date
        resume_date = datetime.utcnow() + timedelta(days=recommended_delay)
        
        action = {
            "action_type": "delay",
            "action_id": f"delay_{shipment.get('shipment_id', 'unknown')}_{datetime.utcnow().strftime('%Y%m%d%H%M')}",
            "summary": f"HOLD shipment for {recommended_delay} days, resume {resume_date.strftime('%b %d')}",
            "recommended_delay_days": recommended_delay,
            "estimated_cost_usd": round(holding_cost["total"], 2),
            "cost_breakdown": holding_cost,
            "estimated_savings_vs_reroute_usd": round(savings, 2),
            "resume_date": resume_date.isoformat(),
            "review_date": (datetime.utcnow() + timedelta(days=recommended_delay // 2)).isoformat(),
            "conditions_for_release": [
                f"Disruption probability drops below 30%",
                f"Spot rates decrease by 15%+",
                f"Safe transit confirmed by 2+ vessels",
            ],
            "shipment_id": shipment.get("shipment_id"),
            "generated_at": datetime.utcnow().isoformat(),
        }
        
        self._generated_count += 1
        
        logger.info(
            "delay_action_generated",
            action_id=action["action_id"],
            delay_days=recommended_delay,
            holding_cost_usd=holding_cost["total"],
        )
        
        return action
    
    async def validate_action(
        self,
        action: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Validate delay action."""
        errors = []
        warnings = []
        
        # Check delay duration
        delay_days = action.get("recommended_delay_days", 0)
        max_delay = self._config.get("max_delay_days", 30)
        
        if delay_days <= 0:
            errors.append("Delay days must be positive")
        elif delay_days > max_delay:
            warnings.append(f"Delay ({delay_days}) exceeds max ({max_delay})")
        
        # Check resume date is in future
        resume_date = action.get("resume_date")
        if resume_date:
            try:
                resume_dt = datetime.fromisoformat(resume_date.replace("Z", "+00:00"))
                if resume_dt < datetime.utcnow():
                    errors.append("Resume date must be in the future")
            except ValueError:
                errors.append("Invalid resume date format")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }
    
    async def estimate_cost(
        self,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Estimate delay cost without full action generation."""
        shipment = context.get("shipment", {})
        delay_days = context.get("delay_days", 14)
        
        container_count = shipment.get("container_count", 1)
        cargo_value = shipment.get("cargo_value_usd", 50000)
        
        # Calculate range
        cost_per_day = self._calculate_holding_cost(
            container_count=container_count,
            cargo_value=cargo_value,
            days=1,
        )["total"]
        
        return {
            "action_type": "delay",
            "cost_estimate_usd": {
                "min": round(cost_per_day * delay_days * 0.8, 2),
                "max": round(cost_per_day * delay_days * 1.2, 2),
                "expected": round(cost_per_day * delay_days, 2),
            },
            "cost_per_day_usd": round(cost_per_day, 2),
            "confidence": 0.85,  # Higher confidence for delay costs
        }
    
    def _calculate_holding_cost(
        self,
        container_count: int,
        cargo_value: float,
        days: int,
    ) -> Dict[str, float]:
        """Calculate total holding cost breakdown."""
        container_cost = HOLDING_COSTS["container_per_day_usd"] * container_count * days
        demurrage_cost = HOLDING_COSTS["demurrage_per_day_usd"] * container_count * days
        storage_cost = HOLDING_COSTS["storage_per_day_usd"] * container_count * days
        insurance_cost = cargo_value * HOLDING_COSTS["insurance_per_day_pct"] * days
        
        return {
            "container_holding": round(container_cost, 2),
            "demurrage": round(demurrage_cost, 2),
            "storage": round(storage_cost, 2),
            "insurance_premium": round(insurance_cost, 2),
            "total": round(
                container_cost + demurrage_cost + storage_cost + insurance_cost,
                2,
            ),
        }


# For dynamic loading
Plugin = DelayActionPlugin
