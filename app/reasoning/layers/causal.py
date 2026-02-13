"""
Layer 3: Causal Reasoning.

Responsibilities:
- Identify root causes of the situation
- Build causal chain from cause to impact
- Find intervention points
- Identify confounders

This layer answers: "WHY is this happening?"
"""

from datetime import datetime
from typing import Any, Optional
import structlog

from app.reasoning.schemas import (
    ReasoningLayer,
    CausalLayerOutput,
    CausalLink,
    InterventionPoint,
)

logger = structlog.get_logger(__name__)


class CausalLayer:
    """
    Layer 3: Causal Reasoning.
    
    Builds causal model to understand:
    - What caused the current situation?
    - How does cause lead to customer impact?
    - Where can customer intervene?
    
    Uses predefined causal templates for supply chain disruptions.
    """
    
    # Causal templates for common scenarios
    CAUSAL_TEMPLATES = {
        "red_sea_disruption": {
            "root_causes": [
                "Houthi attacks on commercial vessels",
                "Geopolitical conflict in Yemen",
                "Regional security instability",
            ],
            "chain": [
                {
                    "cause": "Houthi attacks on vessels",
                    "effect": "Shipping companies avoid Red Sea",
                    "strength": 0.95,
                    "mechanism": "Risk avoidance by carriers",
                },
                {
                    "cause": "Shipping companies avoid Red Sea",
                    "effect": "Vessels reroute via Cape of Good Hope",
                    "strength": 0.90,
                    "mechanism": "Alternative routing",
                },
                {
                    "cause": "Rerouting via Cape",
                    "effect": "Transit time increases 7-14 days",
                    "strength": 0.95,
                    "mechanism": "Longer route distance",
                },
                {
                    "cause": "Transit time increases",
                    "effect": "Delivery delays for customers",
                    "strength": 0.90,
                    "mechanism": "Downstream impact",
                },
                {
                    "cause": "Rerouting via Cape",
                    "effect": "Shipping costs increase $2000-3500/TEU",
                    "strength": 0.85,
                    "mechanism": "Higher fuel and operational costs",
                },
            ],
            "interventions": [
                {
                    "name": "Early rerouting",
                    "description": "Proactively reroute shipments before congestion",
                    "effectiveness": 0.80,
                    "cost_factor": 1.0,
                    "feasibility": "high",
                },
                {
                    "name": "Delay departure",
                    "description": "Wait for situation to stabilize",
                    "effectiveness": 0.30,
                    "cost_factor": 0.3,
                    "feasibility": "medium",
                },
                {
                    "name": "Air freight critical items",
                    "description": "Ship most urgent items by air",
                    "effectiveness": 0.95,
                    "cost_factor": 5.0,
                    "feasibility": "high",
                },
            ],
            "confounders": [
                "Global shipping capacity constraints",
                "Port congestion at alternatives",
                "Insurance premium changes",
                "Fuel price volatility",
            ],
        },
        "default": {
            "root_causes": ["Unknown supply chain disruption"],
            "chain": [
                {
                    "cause": "Supply chain disruption",
                    "effect": "Shipping delays",
                    "strength": 0.70,
                    "mechanism": "Various factors",
                },
            ],
            "interventions": [
                {
                    "name": "Monitor situation",
                    "description": "Continue monitoring for developments",
                    "effectiveness": 0.50,
                    "cost_factor": 0.1,
                    "feasibility": "high",
                },
            ],
            "confounders": ["Multiple unknown factors"],
        },
    }
    
    async def execute(self, inputs: dict) -> CausalLayerOutput:
        """
        Execute causal reasoning layer.
        
        Args:
            inputs: Dict with 'factual', 'signal'
        """
        factual = inputs.get("factual")
        signal = inputs.get("signal")
        
        started_at = datetime.utcnow()
        
        # Identify scenario type
        scenario = self._identify_scenario(signal, factual)
        
        # Get causal template
        template = self.CAUSAL_TEMPLATES.get(scenario, self.CAUSAL_TEMPLATES["default"])
        
        # Build root causes
        root_causes = self._identify_root_causes(template, signal, factual)
        
        # Build causal chain
        causal_chain = self._build_causal_chain(template, signal, factual)
        
        # Find intervention points
        interventions = self._find_interventions(template, factual)
        
        # Identify confounders
        confounders = self._identify_confounders(template, factual)
        
        completed_at = datetime.utcnow()
        
        # Calculate confidence
        confidence = self._calculate_confidence(causal_chain, factual)
        
        # Generate warnings
        warnings = self._generate_warnings(causal_chain, confounders)
        
        output = CausalLayerOutput(
            layer=ReasoningLayer.CAUSAL,
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=int((completed_at - started_at).total_seconds() * 1000),
            inputs={
                "scenario": scenario,
                "factual_confidence": factual.confidence if factual else 0,
            },
            outputs={
                "root_cause_count": len(root_causes),
                "chain_length": len(causal_chain),
                "intervention_count": len(interventions),
            },
            confidence=confidence,
            depends_on=[ReasoningLayer.FACTUAL],
            root_causes=root_causes,
            causal_chain=causal_chain,
            intervention_points=interventions,
            confounders=confounders,
            warnings=warnings,
        )
        
        logger.debug(
            "causal_layer_complete",
            scenario=scenario,
            chain_length=len(causal_chain),
            intervention_count=len(interventions),
        )
        
        return output
    
    def _identify_scenario(
        self,
        signal: Any,
        factual: Any,
    ) -> str:
        """Identify which causal scenario applies."""
        if not signal:
            return "default"
        
        # Check chokepoint
        chokepoint = getattr(signal, "chokepoint", None)
        event_type = getattr(signal, "event_type", "").lower()
        
        if chokepoint == "red_sea" or "red_sea" in event_type:
            return "red_sea_disruption"
        
        # Add more scenario detection as needed
        return "default"
    
    def _identify_root_causes(
        self,
        template: dict,
        signal: Any,
        factual: Any,
    ) -> list[str]:
        """Identify root causes from template and evidence."""
        causes = template.get("root_causes", [])
        
        # Add signal-specific causes
        if signal:
            event_type = getattr(signal, "event_type", "")
            if event_type and event_type not in " ".join(causes):
                causes.append(event_type)
            
            # Check evidence for additional causes
            for evidence in getattr(signal, "evidence", []):
                claim = getattr(evidence, "claim", "")
                if "cause" in claim.lower() or "due to" in claim.lower():
                    causes.append(claim[:100])  # Truncate
        
        return causes[:5]  # Limit to top 5
    
    def _build_causal_chain(
        self,
        template: dict,
        signal: Any,
        factual: Any,
    ) -> list[CausalLink]:
        """Build causal chain from template."""
        chain = []
        
        for link_data in template.get("chain", []):
            # Adjust strength based on signal probability
            strength = link_data.get("strength", 0.5)
            if signal:
                signal_prob = getattr(signal, "probability", 0.5)
                # Weight by signal probability
                strength = strength * (0.5 + 0.5 * signal_prob)
            
            chain.append(CausalLink(
                cause=link_data.get("cause", "Unknown"),
                effect=link_data.get("effect", "Unknown"),
                strength=min(strength, 1.0),
                evidence=[link_data.get("mechanism", "")],
                mechanism=link_data.get("mechanism"),
            ))
        
        return chain
    
    def _find_interventions(
        self,
        template: dict,
        factual: Any,
    ) -> list[InterventionPoint]:
        """Find intervention points from template."""
        interventions = []
        
        base_cost = 5000  # Default base cost for interventions
        
        for int_data in template.get("interventions", []):
            cost_factor = int_data.get("cost_factor", 1.0)
            
            interventions.append(InterventionPoint(
                name=int_data.get("name", "Unknown"),
                description=int_data.get("description", ""),
                effectiveness=int_data.get("effectiveness", 0.5),
                cost_estimate_usd=base_cost * cost_factor,
                feasibility=int_data.get("feasibility", "medium"),
            ))
        
        # Sort by effectiveness
        interventions.sort(key=lambda i: i.effectiveness, reverse=True)
        
        return interventions
    
    def _identify_confounders(
        self,
        template: dict,
        factual: Any,
    ) -> list[str]:
        """Identify confounding factors."""
        confounders = template.get("confounders", [])
        
        # Add data-quality-based confounders
        if factual and factual.data_gaps:
            confounders.extend([
                f"Data gap: {gap}" for gap in factual.data_gaps[:2]
            ])
        
        return confounders[:6]  # Limit
    
    def _calculate_confidence(
        self,
        chain: list[CausalLink],
        factual: Any,
    ) -> float:
        """Calculate confidence in causal analysis."""
        if not chain:
            return 0.5
        
        # Product of chain strengths (causal chains multiply)
        chain_confidence = 1.0
        for link in chain:
            chain_confidence *= link.strength
        
        # Weight by factual data quality
        data_quality = factual.data_quality_score if factual else 0.5
        
        # Combine
        return (chain_confidence + data_quality) / 2
    
    def _generate_warnings(
        self,
        chain: list[CausalLink],
        confounders: list[str],
    ) -> list[str]:
        """Generate causal reasoning warnings."""
        warnings = []
        
        # Weak links in chain
        weak_links = [link for link in chain if link.strength < 0.6]
        if weak_links:
            warnings.append(
                f"{len(weak_links)} weak causal links in chain"
            )
        
        # Many confounders
        if len(confounders) > 4:
            warnings.append(
                f"Many confounders ({len(confounders)}) may affect analysis"
            )
        
        return warnings
